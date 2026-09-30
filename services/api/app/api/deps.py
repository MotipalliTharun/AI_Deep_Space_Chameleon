"""Request-scoped dependencies: settings, client IP, current user, role checks."""

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.rate_limit import RateLimiter
from app.core.security import InvalidTokenError, decode_access_token, tokens_match
from app.db.base import utcnow
from app.db.session import get_db
from app.models import AuthSession, Role, Tenant, User

ACCESS_COOKIE = "sc_access"
REFRESH_COOKIE = "sc_refresh"
CSRF_COOKIE = "sc_csrf"
CSRF_HEADER = "X-CSRF-Token"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def client_ip(request: Request) -> str:
    # Behind a load balancer, run uvicorn with --proxy-headers --forwarded-allow-ips
    # so request.client reflects the real client address.
    return request.client.host if request.client else ""


def get_rate_limiter(request: Request) -> RateLimiter:
    limiter: RateLimiter = request.app.state.rate_limiter
    return limiter


def enforce_csrf(request: Request) -> None:
    """Double-submit check for cookie-authenticated state-changing requests."""
    if request.method in SAFE_METHODS:
        return
    cookie = request.cookies.get(CSRF_COOKIE)
    header = request.headers.get(CSRF_HEADER)
    if not cookie or not header or not tokens_match(cookie, header):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="CSRF token missing or invalid.")


@dataclass
class Principal:
    user: User
    tenant: Tenant
    session_id: uuid.UUID


_UNAUTHENTICATED = HTTPException(
    status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated.",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_principal(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Principal:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
    else:
        token = request.cookies.get(ACCESS_COOKIE, "")
        if token:
            enforce_csrf(request)
    if not token:
        raise _UNAUTHENTICATED

    try:
        claims = decode_access_token(token, settings)
    except InvalidTokenError:
        raise _UNAUTHENTICATED from None

    row = (
        await db.execute(
            select(User, Tenant, AuthSession)
            .join(Tenant, Tenant.id == User.tenant_id)
            .join(AuthSession, AuthSession.user_id == User.id)
            .where(User.id == claims.user_id, AuthSession.id == claims.session_id)
        )
    ).one_or_none()
    if row is None:
        raise _UNAUTHENTICATED
    user, tenant, session = row
    if (
        not user.is_active
        or not tenant.is_active
        or session.revoked_at is not None
        or session.expires_at <= utcnow()
        # Role changed since the token was minted: force a refresh.
        or user.role.value != claims.role
    ):
        raise _UNAUTHENTICATED
    return Principal(user=user, tenant=tenant, session_id=session.id)


def require_roles(*roles: Role) -> Callable[..., Awaitable[Principal]]:
    allowed = frozenset(roles)

    async def checker(principal: Principal = Depends(get_principal)) -> Principal:
        if principal.user.role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Insufficient permissions.")
        return principal

    return checker


require_admin = require_roles(Role.OWNER, Role.ADMIN)
