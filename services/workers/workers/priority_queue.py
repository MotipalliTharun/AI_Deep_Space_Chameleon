"""
Incoming task queue: a min-heap ordered by (priority, deadline, enqueued_at)
so the most urgent work always runs first. O(log n) insert and pop.
See docs/PRD.md §3 and §8 (priority boosts per escalation trigger).
"""

from __future__ import annotations

import heapq
import itertools
from dataclasses import dataclass, field
from typing import Any


@dataclass(order=True)
class _HeapItem:
    sort_key: tuple[int, float, int]
    task: Any = field(compare=False)


class TaskPriorityQueue:
    """Lower priority number = more urgent (matches heapq min-heap semantics)."""

    def __init__(self) -> None:
        self._heap: list[_HeapItem] = []
        self._counter = itertools.count()  # tie-breaker so equal keys stay FIFO-stable

    def push(self, task: Any, priority: int, deadline_epoch: float) -> None:
        key = (priority, deadline_epoch, next(self._counter))
        heapq.heappush(self._heap, _HeapItem(sort_key=key, task=task))

    def pop(self) -> Any:
        return heapq.heappop(self._heap).task

    def peek(self) -> Any:
        return self._heap[0].task

    def __len__(self) -> int:
        return len(self._heap)
