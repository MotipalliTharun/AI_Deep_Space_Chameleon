"""Escalation queue API: handoff packet creation and agent claim (PRD §8)."""

from fastapi import APIRouter

router = APIRouter()


@router.post("/{conversation_id}/claim")
async def claim_escalation(conversation_id: str) -> dict[str, str]:
    # TODO(sprint-3): atomic claim so two agents never take the same chat
    return {"conversation_id": conversation_id, "claimed_by": "TODO"}
