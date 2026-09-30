import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEvent


def record(
    db: AsyncSession,
    action: str,
    *,
    tenant_id: uuid.UUID | None,
    actor_user_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: uuid.UUID | str | None = None,
    ip_address: str = "",
    details: dict[str, Any] | None = None,
) -> None:
    """Stage an audit event in the caller's transaction (committed with the change)."""
    db.add(
        AuditEvent(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            ip_address=ip_address,
            details=details or {},
        )
    )
