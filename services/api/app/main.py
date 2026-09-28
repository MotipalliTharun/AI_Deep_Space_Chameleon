"""
AI Space Chameleon API entrypoint.

Routes each customer message per docs/ARCHITECTURE.md:
  - plain question       -> RAG (routers/rag.py)
  - "do something" intent -> task engine gateway (routers/tasks.py)
  - "human please"       -> escalation queue (routers/escalation.py)

Streams answers over SSE/WebSocket for a sub-1.5s first token (NFR, PRD §5).
"""

from fastapi import FastAPI

from app.routers import chat, tasks, escalation, health

app = FastAPI(
    title="AI Space Chameleon API",
    version="0.0.1",
    description="Intent router, RAG, task engine gateway and escalation API.",
)

app.include_router(health.router)
app.include_router(chat.router, prefix="/v1/chat", tags=["chat"])
app.include_router(tasks.router, prefix="/v1/tasks", tags=["tasks"])
app.include_router(escalation.router, prefix="/v1/escalation", tags=["escalation"])
