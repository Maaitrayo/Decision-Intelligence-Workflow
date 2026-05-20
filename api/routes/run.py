from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from pipeline.db import get_db_session
from pipeline.orchestrator import PipelineOrchestrator
from pipeline.repository import RunRepository, run_record_to_model, run_record_to_summary


router = APIRouter(prefix="/api/runs", tags=["runs"])


class RunRequest(BaseModel):
    eval: bool = False
    signal_keywords: str | None = None


@router.get("")
async def list_runs(db: Session = Depends(get_db_session)) -> list[dict[str, str]]:
    repository = RunRepository(db)
    return [run_record_to_summary(run) for run in repository.list_runs()]


@router.get("/{run_id}")
async def get_run(run_id: str, db: Session = Depends(get_db_session)) -> dict:
    repository = RunRepository(db)
    run = repository.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    return run_record_to_model(run).model_dump(mode="json")


@router.post("")
async def create_run(request: RunRequest, db: Session = Depends(get_db_session)) -> dict:
    print(
        "Run request received | "
        f"eval={request.eval} | "
        f"signal_keywords={request.signal_keywords!r}"
    )

    orchestrator = PipelineOrchestrator()
    result = await orchestrator.run(
        eval_mode=request.eval,
        signal_keywords=request.signal_keywords,
    )

    repository = RunRepository(db)
    repository.save_run(result)

    return result.model_dump(mode="json")
