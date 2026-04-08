import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.routes.query import QueryRequest, query_run
from pipeline.db import SessionLocal
from pipeline.db_init import init_db
from pipeline.orchestrator import PipelineOrchestrator
from pipeline.repository import RunRepository, run_record_to_model


async def main() -> None:
    init_db()

    orchestrator = PipelineOrchestrator()
    run_result = await orchestrator.run()

    db = SessionLocal()
    try:
        repository = RunRepository(db)
        repository.save_run(run_result)

        request = QueryRequest(
            run_id=run_result.run_id,
            question="What are the top risks or uncertainties I should watch in this run?",
        )
        response = await query_run(request=request, db=db)
        saved_run = repository.get_run(run_result.run_id)

        print(
            json.dumps(
                {
                    "run": run_record_to_model(saved_run).model_dump(mode="json") if saved_run else None,
                    "query_response": response.model_dump(mode="json"),
                },
                indent=2,
            )
        )
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
