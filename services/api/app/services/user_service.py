"""Tenant user management with role-hierarchy rules."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.base import utcnow
from app.models import Role, User
from app.services import audit
from app.services.auth_service import (
    EMAIL_TAKEN,
    AuthError,
    add_user,
    email_taken,
    ensure_password_ok,
    normalize_email,
    revoke_user_sessions,
)


def _can_manage(actor: User, target_role: Role) -> bool:
    """Owners manage anyone; admins manage admins and agents but never owners."""
    return actor.role == Role.OWNER or (actor.role == Role.ADMIN and target_role != Role.OWNER)


async def _active_owner_count(db: AsyncSession, tenant_id: uuid.UUID) -> int:
    count = await db.scalar(
        select(func.count())
        .select_from(User)
        .where(User.tenant_id == tenant_id, User.role == Role.OWNER, User.is_active.is_(True))
    )
    return int(count or 0)


async def list_users(db: AsyncSession, tenant_id: uuid.UUID) -> list[User]:
    rows = await db.scalars(
        select(User).where(User.tenant_id == tenant_id).order_by(User.created_at)
    )
    return list(rows)


async def get_tenant_user(db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID) -> User:
    user = await db.get(User, user_id)
    # 404 (not 403) for other tenants' users so ids cannot be probed.
    if user is None or user.tenant_id != tenant_id:
        raise AuthError(404, "not_found", "User not found.")
    return user


async def create_user(
    db: AsyncSession,
    actor: User,
    *,
    email: str,
    full_name: str,
    role: Role,
    password: str,
    ip: str,
) -> User:
    if not _can_manage(actor, role):
        raise AuthError(403, "forbidden", "You cannot create a user with that role.")
    email = normalize_email(email)
    ensure_password_ok(password, email)
    if await email_taken(db, email):
        raise EMAIL_TAKEN
    user = User(
        tenant_id=actor.tenant_id,
        email=email,
        full_name=full_name.strip(),
        role=role,
        password_hash=hash_password(password),
        password_changed_at=utcnow(),
    )
    await add_user(db, user)
    audit.record(
        db,
        "user.created",
        tenant_id=actor.tenant_id,
        actor_user_id=actor.id,
        target_type="user",
        target_id=user.id,
        ip_address=ip,
        details={"email": email, "role": role.value},
    )
    return user


async def update_user(
    db: AsyncSession,
    actor: User,
    target: User,
    *,
    full_name: str | None,
    role: Role | None,
    is_active: bool | None,
    ip: str,
) -> User:
    if not _can_manage(actor, target.role):
        raise AuthError(403, "forbidden", "You cannot modify this user.")
    changes: dict[str, object] = {}

    if full_name is not None and full_name.strip() != target.full_name:
        target.full_name = full_name.strip()
        changes["full_name"] = target.full_name

    if role is not None and role != target.role:
        if target.id == actor.id:
            raise AuthError(400, "self_change", "You cannot change your own role.")
        if not _can_manage(actor, role):
            raise AuthError(403, "forbidden", "You cannot grant that role.")
        if target.role == Role.OWNER and await _active_owner_count(db, target.tenant_id) <= 1:
            raise AuthError(400, "last_owner", "A workspace needs at least one owner.")
        changes["role"] = {"from": target.role.value, "to": role.value}
        target.role = role

    if is_active is not None and is_active != target.is_active:
        if target.id == actor.id:
            raise AuthError(400, "self_change", "You cannot deactivate yourself.")
        if (
            not is_active
            and target.role == Role.OWNER
            and await _active_owner_count(db, target.tenant_id) <= 1
        ):
            raise AuthError(400, "last_owner", "A workspace needs at least one owner.")
        target.is_active = is_active
        if not is_active:
            await revoke_user_sessions(db, target.id, reason="user_deactivated")
        else:
            target.failed_login_count = 0
            target.locked_until = None
        changes["is_active"] = is_active

    if changes:
        audit.record(
            db,
            "user.updated",
            tenant_id=actor.tenant_id,
            actor_user_id=actor.id,
            target_type="user",
            target_id=target.id,
            ip_address=ip,
            details=changes,
        )
    return target
