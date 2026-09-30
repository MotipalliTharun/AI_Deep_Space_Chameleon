"""Tenant user management and audit log (owners and admins only)."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Principal, client_ip, require_admin
from app.db.session import get_db
from app.models import AuditEvent
from app.schemas.auth import UserOut
from app.schemas.users import AuditEventOut, AuditPage, UserCreateIn, UserUpdateIn
from app.services import user_service
from app.services.auth_service import AuthError

router = APIRouter()
audit_router = APIRouter()


def _error(err: AuthError) -> HTTPException:
    return HTTPException(err.status_code, detail={"code": err.code, "message": err.message})


@router.get("", response_model=list[UserOut])
async def list_users(
    principal: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[UserOut]:
    users = await user_service.list_users(db, principal.tenant.id)
    return [UserOut.model_validate(u) for u in users]


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreateIn,
    request: Request,
    principal: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    try:
        user = await user_service.create_user(
            db,
            principal.user,
            email=body.email,
            full_name=body.full_name,
            role=body.role,
            password=body.password,
            ip=client_ip(request),
        )
    except AuthError as err:
        raise _error(err) from None
    await db.commit()
    return UserOut.model_validate(user)


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdateIn,
    request: Request,
    principal: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    try:
        target = await user_service.get_tenant_user(db, principal.tenant.id, user_id)
        user = await user_service.update_user(
            db,
            principal.user,
            target,
            full_name=body.full_name,
            role=body.role,
            is_active=body.is_active,
            ip=client_ip(request),
        )
    except AuthError as err:
        raise _error(err) from None
    await db.commit()
    return UserOut.model_validate(user)


@audit_router.get("", response_model=AuditPage)
async def list_audit_events(
    principal: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    action: str | None = Query(default=None, max_length=64),
    before: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> AuditPage:
    stmt = select(AuditEvent).where(AuditEvent.tenant_id == principal.tenant.id)
    if action:
        stmt = stmt.where(AuditEvent.action == action)
    if before:
        stmt = stmt.where(AuditEvent.created_at < before)
    rows = list(await db.scalars(stmt.order_by(AuditEvent.created_at.desc()).limit(limit + 1)))
    items = rows[:limit]
    return AuditPage(
        items=[AuditEventOut.model_validate(e) for e in items],
        next_before=items[-1].created_at if len(rows) > limit else None,
    )
