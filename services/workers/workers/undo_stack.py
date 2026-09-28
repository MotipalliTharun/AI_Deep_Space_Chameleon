"""
Every side-effecting task step pushes its compensating action onto this
stack. If a later step fails, we pop and run compensations in reverse
(saga pattern) so no half-done work is left behind. See docs/PRD.md §3,
worked example: exchange rolls back the return label if size-9 is out of stock.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class Compensation:
    step_name: str
    undo: Callable[[], None]


class UndoStack:
    def __init__(self) -> None:
        self._stack: list[Compensation] = []

    def push(self, step_name: str, undo: Callable[[], None]) -> None:
        self._stack.append(Compensation(step_name=step_name, undo=undo))

    def rollback_all(self) -> list[str]:
        """Pop and run every compensation in reverse order. Returns step names undone."""
        undone: list[str] = []
        while self._stack:
            compensation = self._stack.pop()
            compensation.undo()
            undone.append(compensation.step_name)
        return undone

    def __len__(self) -> int:
        return len(self._stack)
