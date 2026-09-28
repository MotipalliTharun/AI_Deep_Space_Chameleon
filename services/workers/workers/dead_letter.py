"""
Steps that fail after retries land here instead of being silently lost.
Ops can inspect and replay. See docs/PRD.md §3 and §10 (alert: >10 dead
letters/hour).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class DeadLetter:
    task_step_id: str
    reason: str
    payload: dict[str, Any]
    failed_at: datetime


class DeadLetterQueue:
    def __init__(self) -> None:
        self._items: list[DeadLetter] = []

    def add(self, task_step_id: str, reason: str, payload: dict[str, Any]) -> None:
        self._items.append(
            DeadLetter(
                task_step_id=task_step_id,
                reason=reason,
                payload=payload,
                failed_at=datetime.now(timezone.utc),
            )
        )

    def list_unresolved(self) -> list[DeadLetter]:
        return list(self._items)
