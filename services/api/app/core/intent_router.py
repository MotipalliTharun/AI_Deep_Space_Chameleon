"""
Classifies a raw customer message into one of three lanes:
  - "question": answer directly via RAG
  - "action":   becomes a Task run by the engine (queue -> stack -> DAG -> undo)
  - "human":    straight to the escalation queue

Sprint 1 will replace this heuristic stub with a small routing-model call.
"""

from dataclasses import dataclass
from typing import Literal

IntentKind = Literal["question", "action", "human"]

_HUMAN_PHRASES = ("talk to a human", "talk to an agent", "speak to someone", "human please")
_ACTION_VERBS = ("return", "exchange", "cancel", "change my", "update my address")


@dataclass
class Intent:
    kind: IntentKind
    confidence: float


def classify_intent(text: str) -> Intent:
    lowered = text.lower()

    if any(phrase in lowered for phrase in _HUMAN_PHRASES):
        return Intent(kind="human", confidence=1.0)

    if any(verb in lowered for verb in _ACTION_VERBS):
        return Intent(kind="action", confidence=0.8)

    return Intent(kind="question", confidence=0.6)
