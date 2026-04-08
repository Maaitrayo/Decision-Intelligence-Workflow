from fastapi import FastAPI

from api.routes.run import router as run_router
from pipeline.db_init import init_db


app = FastAPI(
    title="Decision Intelligence Workflow API",
    version="0.1.0",
)


@app.on_event("startup")
async def on_startup() -> None:
    init_db()


app.include_router(run_router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": app.version}
