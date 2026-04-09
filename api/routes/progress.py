from fastapi import APIRouter

from pipeline.progress import progress_tracker


router = APIRouter(prefix="/api/progress", tags=["progress"])


@router.get("")
async def get_progress() -> dict[str, str | bool]:
    return progress_tracker.get_state()
