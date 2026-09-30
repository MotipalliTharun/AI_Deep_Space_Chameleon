"""
Sign-up, sign-in, session and refresh-token lifecycle.

Routers stay thin (docs/CODING_STANDARDS.md): they translate `AuthError` into
HTTP responses and set cookies; all rules live here.
"""

import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.password_policy import password_problems
from app.core.security import (
    AccessClaims,
    create_access_token,
    hash_password,
    hash_token,
    new_refresh_token,
    password_needs_rehash,
    verify_password,
)
from app.db.base import utcnow
from app.models import AuthSession, RefreshToken, Role, Tenant, User
from app.services import audit


class AuthError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


INVALID_CREDENTIALS = AuthError(401, "invalid_credentials", "Invalid email or password.")


@dataclass
class IssuedTokens:
    access_token: str
    access_expires_at: datetime
    refresh_token: str
    session: AuthSession
    user: User
    tenant: Tenant


def normalize_email(email: str) -> str:
    return email.strip().lower()


def ensure_password_ok(password: str, email: str) -> None:
    problems = password_problems(password, email)
    if problems:
        raise AuthError(422, "weak_password", "Password " + "; ".join(problems) + ".")


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:48]
    return slug or "tenant"


async def _unique_slug(db: AsyncSession, name: str) -> str:
    base = _slugify(name)
    slug = base
    while await db.scalar(select(Tenant.id).where(Tenant.slug == slug)) is not None:
        slug = f"{base}-{secrets.token_hex(3)}"
    return slug


async def email_taken(db: AsyncSession, email: str) -> bool:
    return await db.scalar(select(User.id).where(User.email == email)) is not None


EMAIL_TAKEN = AuthError(409, "email_taken", "An account with this email already exists.")


async def add_user(db: AsyncSession, user: User) -> None:
    """Insert a user; a concurrent insert of the same email becomes a 409, not a 500."""
    try:
        async with db.begin_nested():
            db.add(user)
            await db.flush()
    except IntegrityError:
        raise EMAIL_TAKEN from None


async def signup(
    db: AsyncSession,
    *,
    company_name: str,
    full_name: str,
    email: str,
    password: str,
    ip: str,
) -> User:
    email = normalize_email(email)
    ensure_password_ok(password, email)
    if await email_taken(db, email):
        raise EMAIL_TAKEN

    tenant = Tenant(name=company_name.strip(), slug=await _unique_slug(db, company_name))
    db.add(tenant)
    await db.flush()
    user = User(
        tenant_id=tenant.id,
        email=email,
        full_name=full_name.strip(),
        role=Role.OWNER,
        password_hash=hash_password(password),
        password_changed_at=utcnow(),
        last_login_at=utcnow(),  # sign-up signs the owner straight in
    )
    await add_user(db, user)
    audit.record(
        db,
        "tenant.created",
        tenant_id=tenant.id,
        actor_user_id=user.id,
        target_type="tenant",
        target_id=tenant.id,
        ip_address=ip,
    )
    return user


async def authenticate(
    db: AsyncSession, settings: Settings, *, email: str, password: str, ip: str
) -> User:
    email = normalize_email(email)
    user = await db.scalar(select(User).where(User.email == email))
    now = utcnow()

    if user is None:
        verify_password(password, None)  # equalise timing
        raise INVALID_CREDENTIALS

    if user.locked_until is not None and user.locked_until > now:
        audit.record(
            db,
            "auth.login_blocked",
            tenant_id=user.tenant_id,
            actor_user_id=user.id,
            ip_address=ip,
            details={"reason": "locked"},
        )
        await db.commit()
        raise AuthError(
            423, "account_locked", "Too many failed attempts. Try again later or contact an admin."
        )

    if not verify_password(password, user.password_hash):
        user.failed_login_count += 1
        details: dict[str, object] = {"failed_count": user.failed_login_count}
        if user.failed_login_count >= settings.max_failed_logins:
            user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
            user.failed_login_count = 0
            details["locked_until"] = user.locked_until.isoformat()
        audit.record(
            db,
            "auth.login_failed",
            tenant_id=user.tenant_id,
            actor_user_id=user.id,
            ip_address=ip,
            details=details,
        )
        await db.commit()
        raise INVALID_CREDENTIALS

    tenant = await db.get(Tenant, user.tenant_id)
    if not user.is_active or tenant is None or not tenant.is_active:
        # Same response as a bad password: do not reveal account state.
        raise INVALID_CREDENTIALS

    if user.password_hash and password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    audit.record(db, "auth.login", tenant_id=user.tenant_id, actor_user_id=user.id, ip_address=ip)
    return user


async def _issue(
    db: AsyncSession, settings: Settings, user: User, session: AuthSession
) -> IssuedTokens:
    tenant = await db.get(Tenant, user.tenant_id)
    if tenant is None:  # pragma: no cover - FK guarantees it
        raise AuthError(401, "invalid_credentials", "Account not found.")
    raw_refresh = new_refresh_token()
    db.add(
        RefreshToken(
            session_id=session.id,
            token_hash=hash_token(raw_refresh),
            expires_at=session.expires_at,
        )
    )
    access = create_access_token(
        AccessClaims(
            user_id=user.id, tenant_id=user.tenant_id, role=user.role.value, session_id=session.id
        ),
        settings,
    )
    return IssuedTokens(
        access_token=access,
        access_expires_at=utcnow() + timedelta(seconds=settings.access_token_ttl_seconds),
        refresh_token=raw_refresh,
        session=session,
        user=user,
        tenant=tenant,
    )


async def start_session(
    db: AsyncSession, settings: Settings, user: User, *, user_agent: str, ip: str
) -> IssuedTokens:
    session = AuthSession(
        id=uuid.uuid4(),
        user_id=user.id,
        expires_at=utcnow() + timedelta(seconds=settings.refresh_token_ttl_seconds),
        user_agent=user_agent[:512],
        ip_address=ip,
    )
    db.add(session)
    await db.flush()
    return await _issue(db, settings, user, session)


async def rotate_refresh_token(
    db: AsyncSession, settings: Settings, raw_token: str, *, ip: str
) -> IssuedTokens:
    """
    Exchange a refresh token for a new pair. Each refresh token works once;
    presenting a used one outside the grace window means it was copied, so the
    whole session is revoked (OAuth 2.0 Security BCP, refresh token rotation).
    """
    unauthorized = AuthError(401, "invalid_refresh", "Session expired. Please sign in again.")
    token = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_token))
    )
    if token is None:
        raise unauthorized
    session = await db.get(AuthSession, token.session_id)
    now = utcnow()
    if session is None or session.revoked_at is not None or session.expires_at <= now:
        raise unauthorized

    user = await db.get(User, session.user_id)
    tenant = await db.get(Tenant, user.tenant_id) if user else None
    if user is None or not user.is_active or tenant is None or not tenant.is_active:
        await revoke_session(db, session, reason="user_inactive")
        await db.commit()
        raise unauthorized

    if token.used_at is not None:
        if (now - token.used_at).total_seconds() <= settings.refresh_reuse_grace_seconds:
            # Concurrent refresh from another tab: that tab already got the new cookie.
            raise AuthError(409, "refresh_race", "Refresh already in progress; retry.")
        await revoke_session(db, session, reason="refresh_reuse")
        audit.record(
            db,
            "auth.refresh_reuse_detected",
            tenant_id=user.tenant_id,
            actor_user_id=user.id,
            target_type="session",
            target_id=session.id,
            ip_address=ip,
        )
        await db.commit()
        raise unauthorized

    if token.expires_at <= now:
        raise unauthorized

    token.used_at = now
    session.last_used_at = now
    session.ip_address = ip
    return await _issue(db, settings, user, session)


async def revoke_session(db: AsyncSession, session: AuthSession, *, reason: str) -> None:
    if session.revoked_at is None:
        session.revoked_at = utcnow()
        session.revoke_reason = reason


async def revoke_user_sessions(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    reason: str,
    keep_session_id: uuid.UUID | None = None,
) -> None:
    stmt = (
        update(AuthSession)
        .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=utcnow(), revoke_reason=reason)
    )
    if keep_session_id is not None:
        stmt = stmt.where(AuthSession.id != keep_session_id)
    await db.execute(stmt)


async def change_password(
    db: AsyncSession,
    user: User,
    *,
    current_password: str,
    new_password: str,
    current_session_id: uuid.UUID,
    ip: str,
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise AuthError(400, "wrong_password", "Current password is incorrect.")
    ensure_password_ok(new_password, user.email)
    if verify_password(new_password, user.password_hash):
        raise AuthError(422, "weak_password", "New password must differ from the current one.")
    user.password_hash = hash_password(new_password)
    user.password_changed_at = utcnow()
    await revoke_user_sessions(
        db, user.id, reason="password_changed", keep_session_id=current_session_id
    )
    audit.record(
        db, "auth.password_changed", tenant_id=user.tenant_id, actor_user_id=user.id, ip_address=ip
    )
