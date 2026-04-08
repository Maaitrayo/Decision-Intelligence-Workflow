from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from pipeline.db import get_db_session
from pipeline.repository import RunRepository, run_record_to_summary


router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get("")
async def list_runs(db: Session = Depends(get_db_session)) -> list[dict[str, str]]:
    repository = RunRepository(db)
    return [run_record_to_summary(run) for run in repository.list_runs()]


@router.get("/{run_id}")
async def get_run(run_id: str, db: Session = Depends(get_db_session)) -> dict[str, str]:
    repository = RunRepository(db)
    run = repository.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    return run_record_to_summary(run)
