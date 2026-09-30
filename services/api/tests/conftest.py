"""
Test fixtures. Runs against in-memory SQLite by default; set
TEST_DATABASE_URL=postgresql+asyncpg://... to run the same suite on Postgres.
"""

import os
from collections.abc import AsyncIterator, Callable
from typing import Any

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
STRONG_PASSWORD = "correct horse battery staple"


def make_settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = {
        "environment": "test",
        "database_url": TEST_DATABASE_URL,
        "refresh_reuse_grace_seconds": 0,
        "max_failed_logins": 3,
        "login_rate_limit_per_minute": 100,
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[call-arg]


@pytest.fixture
def settings_overrides() -> dict[str, Any]:
    return {}


@pytest.fixture
def settings(settings_overrides: dict[str, Any]) -> Settings:
    return make_settings(**settings_overrides)


@pytest.fixture
async def sessionmaker() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    kwargs: dict[str, Any] = {}
    if TEST_DATABASE_URL.startswith("sqlite"):
        kwargs = {"poolclass": StaticPool, "connect_args": {"check_same_thread": False}}
    engine = create_async_engine(TEST_DATABASE_URL, **kwargs)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def client_factory(
    settings: Settings, sessionmaker: async_sessionmaker[AsyncSession]
) -> AsyncIterator[Callable[[], httpx.AsyncClient]]:
    application = create_app()

    async def _db() -> AsyncIterator[AsyncSession]:
        async with sessionmaker() as session:
            yield session

    application.dependency_overrides[get_db] = _db
    application.dependency_overrides[get_settings] = lambda: settings
    clients: list[httpx.AsyncClient] = []

    def make() -> httpx.AsyncClient:
        c = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application), base_url="http://testserver"
        )
        clients.append(c)
        return c

    yield make
    for c in clients:
        await c.aclose()


@pytest.fixture
def client(client_factory: Callable[[], httpx.AsyncClient]) -> httpx.AsyncClient:
    return client_factory()


def csrf(client: httpx.AsyncClient) -> dict[str, str]:
    return {"X-CSRF-Token": client.cookies.get("sc_csrf") or ""}


async def signup(
    client: httpx.AsyncClient,
    email: str = "owner@acme.com",
    company: str = "Acme Inc",
    password: str = STRONG_PASSWORD,
) -> httpx.Response:
    res = await client.post(
        "/v1/auth/signup",
        json={
            "company_name": company,
            "full_name": "Olive Owner",
            "email": email,
            "password": password,
        },
    )
    assert res.status_code == 201, res.text
    return res


async def login(
    client: httpx.AsyncClient, email: str, password: str = STRONG_PASSWORD
) -> httpx.Response:
    return await client.post("/v1/auth/login", json={"email": email, "password": password})
