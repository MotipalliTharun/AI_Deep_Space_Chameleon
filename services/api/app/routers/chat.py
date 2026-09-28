"""
Chat endpoint: classifies each incoming message into an intent, then either
answers directly via RAG or hands the message to the task engine / escalation
queue. See docs/PRD.md §3 ("AI Stacks and Queues: how a request runs").
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.intent_router import classify_intent

router = APIRouter()


class ChatMessageIn(BaseModel):
    conversation_id: str
    site_id: str
    text: str


class ChatMessageOut(BaseModel):
    reply: str
    sources: list[str] = []
    task_id: str | None = None


@router.post("", response_model=ChatMessageOut)
async def post_message(message: ChatMessageIn) -> ChatMessageOut:
    intent = classify_intent(message.text)

    if intent.kind == "human":
        # TODO(sprint-3): enqueue onto the escalation priority queue (app/core/escalation.py)
        return ChatMessageOut(reply="Connecting you to a person.")

    if intent.kind == "action":
        # TODO(sprint-2): create a Task, push its plan onto the step stack (app/core/task_engine.py)
        return ChatMessageOut(reply="Working on that.", task_id="TODO")

    # TODO(sprint-1): retrieve from pgvector, generate a grounded answer with sources
    return ChatMessageOut(reply="TODO: RAG answer", sources=[])
