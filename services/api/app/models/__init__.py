"""Import every model here so Alembic autogenerate and `Base.metadata` see them."""

from app.models.audit import AuditEvent
from app.models.auth_session import AuthSession, RefreshToken
from app.models.tenant import Tenant
from app.models.user import Role, User

__all__ = ["AuditEvent", "AuthSession", "RefreshToken", "Role", "Tenant", "User"]
