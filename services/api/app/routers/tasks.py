"""Task engine gateway: inspect/replay task state for the dashboard (PRD §5, §9)."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/{task_id}")
async def get_task(task_id: str) -> dict[str, str]:
    # TODO(sprint-2): read task + task_steps from Postgres (docs/DATA_MODEL.md)
    return {"task_id": task_id, "state": "TODO"}
