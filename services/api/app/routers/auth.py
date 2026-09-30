"""Dashboard sign-in: login, signup, refresh, logout, sessions, password change."""

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    ACCESS_COOKIE,
    CSRF_COOKIE,
    REFRESH_COOKIE,
    Principal,
    client_ip,
    enforce_csrf,
    get_principal,
    get_rate_limiter,
)
from app.core.config import Settings, get_settings
from app.core.rate_limit import RateLimiter
from app.core.security import new_csrf_token
from app.db.base import utcnow
from app.db.session import get_db
from app.models import AuthSession
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordIn,
    LoginIn,
    MeResponse,
    SessionOut,
    SignupIn,
    TenantOut,
    UserOut,
)
from app.services import audit, auth_service
from app.services.auth_service import AuthError, IssuedTokens

router = APIRouter()

REFRESH_COOKIE_PATH = "/v1/auth"


def _error(err: AuthError) -> HTTPException:
    return HTTPException(err.status_code, detail={"code": err.code, "message": err.message})


def _set_auth_cookies(response: Response, issued: IssuedTokens, settings: Settings) -> str:
    csrf = new_csrf_token()
    cookies: list[tuple[str, str, int, bool, Literal["lax", "strict"], str]] = [
        (ACCESS_COOKIE, issued.access_token, settings.access_token_ttl_seconds, True, "lax", "/"),
        (
            REFRESH_COOKIE,
            issued.refresh_token,
            settings.refresh_token_ttl_seconds,
            True,
            "strict",
            REFRESH_COOKIE_PATH,
        ),
        # Readable by the dashboard JS so it can echo it in the X-CSRF-Token header.
        (CSRF_COOKIE, csrf, settings.refresh_token_ttl_seconds, False, "strict", "/"),
    ]
    for name, value, max_age, httponly, samesite, path in cookies:
        response.set_cookie(
            name,
            value,
            max_age=max_age,
            httponly=httponly,
            samesite=samesite,
            path=path,
            secure=settings.cookie_secure,
            domain=settings.cookie_domain,
        )
    return csrf


def _clear_auth_cookies(response: Response, settings: Settings) -> None:
    for name, path in (
        (ACCESS_COOKIE, "/"),
        (REFRESH_COOKIE, REFRESH_COOKIE_PATH),
        (CSRF_COOKIE, "/"),
    ):
        response.delete_cookie(
            name, path=path, domain=settings.cookie_domain, secure=settings.cookie_secure
        )


def _auth_response(response: Response, issued: IssuedTokens, settings: Settings) -> AuthResponse:
    csrf = _set_auth_cookies(response, issued, settings)
    response.headers["Cache-Control"] = "no-store"
    return AuthResponse(
        user=UserOut.model_validate(issued.user),
        tenant=TenantOut.model_validate(issued.tenant),
        csrf_token=csrf,
        access_token_expires_at=issued.access_expires_at,
    )


async def _check_login_rate(limiter: RateLimiter, settings: Settings, ip: str, email: str) -> None:
    per_email = settings.login_rate_limit_per_minute
    ok_email = await limiter.hit(f"login:email:{email.lower()}", per_email, 60)
    ok_ip = await limiter.hit(f"login:ip:{ip}", per_email * 5, 60)
    if not (ok_email and ok_ip):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "rate_limited", "message": "Too many attempts. Wait a minute."},
            headers={"Retry-After": "60"},
        )


@router.post("/login", response_model=AuthResponse)
async def login(
    body: LoginIn,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> AuthResponse:
    ip = client_ip(request)
    await _check_login_rate(limiter, settings, ip, body.email)
    try:
        user = await auth_service.authenticate(
            db, settings, email=body.email, password=body.password, ip=ip
        )
        issued = await auth_service.start_session(
            db, settings, user, user_agent=request.headers.get("User-Agent", ""), ip=ip
        )
    except AuthError as err:
        raise _error(err) from None
    await db.commit()
    return _auth_response(response, issued, settings)


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    body: SignupIn,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> AuthResponse:
    if not settings.allow_self_signup:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Self sign-up is disabled.")
    ip = client_ip(request)
    if not await limiter.hit(f"signup:ip:{ip}", 5, 3600):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many sign-ups.")
    try:
        user = await auth_service.signup(
            db,
            company_name=body.company_name,
            full_name=body.full_name,
            email=body.email,
            password=body.password,
            ip=ip,
        )
        issued = await auth_service.start_session(
            db, settings, user, user_agent=request.headers.get("User-Agent", ""), ip=ip
        )
    except AuthError as err:
        raise _error(err) from None
    await db.commit()
    return _auth_response(response, issued, settings)


@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthResponse | JSONResponse:
    enforce_csrf(request)
    raw = request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise _error(AuthError(401, "invalid_refresh", "Session expired. Please sign in again."))
    try:
        issued = await auth_service.rotate_refresh_token(db, settings, raw, ip=client_ip(request))
    except AuthError as err:
        if err.code == "refresh_race":
            raise _error(err) from None
        failed = JSONResponse(
            status_code=err.status_code,
            content={"detail": {"code": err.code, "message": err.message}},
        )
        _clear_auth_cookies(failed, settings)
        return failed
    await db.commit()
    return _auth_response(response, issued, settings)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Always succeeds and clears cookies, even if the session was already gone."""
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    try:
        principal = await get_principal(request, db, settings)
    except HTTPException:
        _clear_auth_cookies(response, settings)
        return response
    session = await db.get(AuthSession, principal.session_id)
    if session is not None:
        await auth_service.revoke_session(db, session, reason="logout")
    audit.record(
        db,
        "auth.logout",
        tenant_id=principal.tenant.id,
        actor_user_id=principal.user.id,
        ip_address=client_ip(request),
    )
    await db.commit()
    _clear_auth_cookies(response, settings)
    return response


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    request: Request,
    principal: Principal = Depends(get_principal),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    await auth_service.revoke_user_sessions(db, principal.user.id, reason="logout_all")
    audit.record(
        db,
        "auth.logout_all",
        tenant_id=principal.tenant.id,
        actor_user_id=principal.user.id,
        ip_address=client_ip(request),
    )
    await db.commit()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_auth_cookies(response, settings)
    return response


@router.get("/me", response_model=MeResponse)
async def me(principal: Principal = Depends(get_principal)) -> MeResponse:
    return MeResponse(
        user=UserOut.model_validate(principal.user),
        tenant=TenantOut.model_validate(principal.tenant),
    )


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordIn,
    request: Request,
    principal: Principal = Depends(get_principal),
    db: AsyncSession = Depends(get_db),
) -> None:
    try:
        await auth_service.change_password(
            db,
            principal.user,
            current_password=body.current_password,
            new_password=body.new_password,
            current_session_id=principal.session_id,
            ip=client_ip(request),
        )
    except AuthError as err:
        raise _error(err) from None
    await db.commit()


@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(
    principal: Principal = Depends(get_principal),
    db: AsyncSession = Depends(get_db),
) -> list[SessionOut]:
    rows = await db.scalars(
        select(AuthSession)
        .where(
            AuthSession.user_id == principal.user.id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > utcnow(),
        )
        .order_by(AuthSession.last_used_at.desc())
    )
    out = []
    for s in rows:
        item = SessionOut.model_validate(s)
        item.current = s.id == principal.session_id
        out.append(item)
    return out


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: uuid.UUID,
    request: Request,
    principal: Principal = Depends(get_principal),
    db: AsyncSession = Depends(get_db),
) -> None:
    session = await db.get(AuthSession, session_id)
    if session is None or session.user_id != principal.user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Session not found.")
    await auth_service.revoke_session(db, session, reason="revoked_by_user")
    audit.record(
        db,
        "auth.session_revoked",
        tenant_id=principal.tenant.id,
        actor_user_id=principal.user.id,
        target_type="session",
        target_id=session_id,
        ip_address=client_ip(request),
    )
    await db.commit()
