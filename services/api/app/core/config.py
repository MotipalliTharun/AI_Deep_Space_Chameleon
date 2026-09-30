"""
Typed runtime settings, loaded from environment variables / `.env`.

Secrets are `SecretStr` so they never end up in logs or reprs. Outside
development the app refuses to start with a weak or default JWT secret.
"""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_JWT_SECRET = "dev-only-insecure-jwt-secret-change-me-0000"  # noqa: S105


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"), env_file_encoding="utf-8", extra="ignore"
    )

    environment: Literal["development", "test", "staging", "production"] = "development"

    database_url: str = "postgresql+asyncpg://chameleon:chameleon@localhost:5432/chameleon"
    redis_url: str = "redis://localhost:6379/0"

    # Auth tokens
    jwt_secret: SecretStr = SecretStr(_DEV_JWT_SECRET)
    jwt_issuer: str = "space-chameleon"
    jwt_audience: str = "space-chameleon-dashboard"
    access_token_ttl_seconds: int = 15 * 60
    refresh_token_ttl_seconds: int = 30 * 24 * 60 * 60
    # A refresh token replayed within this window is treated as a benign race
    # (two tabs refreshing at once), not as theft.
    refresh_reuse_grace_seconds: int = 10

    # Cookies
    cookie_secure: bool = False
    cookie_domain: str | None = None

    # Sign-in hardening
    allow_self_signup: bool = True
    login_rate_limit_per_minute: int = 10
    max_failed_logins: int = 10
    lockout_minutes: int = 15

    cors_origins: list[str] = ["http://localhost:5173"]

    @model_validator(mode="after")
    def _check_production_safety(self) -> "Settings":
        if self.environment in ("staging", "production"):
            secret = self.jwt_secret.get_secret_value()
            if secret == _DEV_JWT_SECRET or len(secret) < 32:
                raise ValueError("JWT_SECRET must be set to a random value of 32+ characters")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true outside development")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
