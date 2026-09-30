import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from pydantic import ValidationError

from app.core.password_policy import password_problems
from app.core.rate_limit import InMemorySlidingWindowLimiter
from app.core.security import (
    AccessClaims,
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from tests.conftest import make_settings


def test_password_hash_roundtrip() -> None:
    h = hash_password("a long enough passphrase")
    assert h.startswith("$argon2id$")
    assert verify_password("a long enough passphrase", h)
    assert not verify_password("wrong", h)
    assert not verify_password("anything", None)
    assert not verify_password("anything", "not-a-hash")


def test_access_token_roundtrip_and_tamper() -> None:
    settings = make_settings()
    claims = AccessClaims(uuid.uuid4(), uuid.uuid4(), "admin", uuid.uuid4())
    token = create_access_token(claims, settings)
    assert decode_access_token(token, settings) == claims
    with pytest.raises(InvalidTokenError):
        decode_access_token(token + "x", settings)
    other = make_settings(jwt_audience="someone-else")
    with pytest.raises(InvalidTokenError):
        decode_access_token(token, other)


def test_expired_and_alg_none_tokens_rejected() -> None:
    settings = make_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(uuid.uuid4()),
        "tid": str(uuid.uuid4()),
        "sid": str(uuid.uuid4()),
        "role": "owner",
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now - timedelta(hours=1),
        "exp": now - timedelta(minutes=1),
    }
    expired = jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm="HS256")
    with pytest.raises(InvalidTokenError):
        decode_access_token(expired, settings)
    payload["exp"] = now + timedelta(hours=1)
    unsigned = jwt.encode(payload, None, algorithm="none")
    with pytest.raises(InvalidTokenError):
        decode_access_token(unsigned, settings)


def test_password_policy() -> None:
    assert password_problems("correct horse battery staple") == []
    assert password_problems("short")
    assert password_problems("x" * 200)
    assert password_problems("jane.doe-rocks-1234", "jane.doe@x.com")


async def test_sliding_window_limiter() -> None:
    limiter = InMemorySlidingWindowLimiter()
    assert await limiter.hit("k", 2, 60)
    assert await limiter.hit("k", 2, 60)
    assert not await limiter.hit("k", 2, 60)
    assert await limiter.hit("other", 2, 60)
    await limiter.reset("k")
    assert await limiter.hit("k", 2, 60)


def test_production_requires_strong_secret_and_secure_cookies() -> None:
    with pytest.raises(ValidationError):
        make_settings(environment="production")
    with pytest.raises(ValidationError):
        make_settings(environment="production", jwt_secret="x" * 40)
    ok = make_settings(environment="production", jwt_secret="x" * 40, cookie_secure=True)
    assert ok.environment == "production"
