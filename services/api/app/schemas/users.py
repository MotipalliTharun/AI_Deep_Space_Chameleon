import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import Role


class UserCreateIn(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    role: Role = Role.AGENT
    # Temporary password shared out-of-band. Email invites replace this once
    # the notification service lands.
    password: str = Field(min_length=1, max_length=256)


class UserUpdateIn(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    role: Role | None = None
    is_active: bool | None = None


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    action: str
    target_type: str | None
    target_id: str | None
    ip_address: str
    details: dict[str, Any]
    created_at: datetime


class AuditPage(BaseModel):
    items: list[AuditEventOut]
    next_before: datetime | None
