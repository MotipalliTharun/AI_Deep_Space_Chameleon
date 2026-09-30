"""
AI Space Chameleon API entrypoint.

Routes each customer message per docs/ARCHITECTURE.md:
  - plain question       -> RAG (routers/rag.py)
  - "do something" intent -> task engine gateway (routers/tasks.py)
  - "human please"       -> escalation queue (routers/escalation.py)

Dashboard users sign in through routers/auth.py (cookie sessions, RBAC).
Streams answers over SSE/WebSocket for a sub-1.5s first token (NFR, PRD §5).
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.rate_limit import InMemorySlidingWindowLimiter
from app.db.session import dispose_engine
from app.routers import auth, chat, escalation, health, tasks, users


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AI Space Chameleon API",
        version="0.1.0",
        description="Intent router, RAG, task engine gateway, escalation and dashboard auth API.",
        lifespan=lifespan,
        docs_url=None if settings.environment == "production" else "/docs",
        redoc_url=None,
    )
    app.state.rate_limiter = InMemorySlidingWindowLimiter()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
    )

    @app.middleware("http")
    async def security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if settings.cookie_secure:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=63072000; includeSubDomains"
            )
        return response

    app.include_router(health.router)
    app.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
    app.include_router(users.router, prefix="/v1/users", tags=["users"])
    app.include_router(users.audit_router, prefix="/v1/audit-events", tags=["audit"])
    app.include_router(chat.router, prefix="/v1/chat", tags=["chat"])
    app.include_router(tasks.router, prefix="/v1/tasks", tags=["tasks"])
    app.include_router(escalation.router, prefix="/v1/escalation", tags=["escalation"])
    return app


app = create_app()
