from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes.progress import router as progress_router
from api.routes.query import router as query_router
from api.routes.run import router as run_router
from pipeline.db_init import init_db


app = FastAPI(
    title="Decision Intelligence Workflow API",
    version="0.1.0",
)
frontend_dir = Path(__file__).resolve().parents[1] / "frontend"


@app.on_event("startup")
async def on_startup() -> None:
    init_db()


app.include_router(run_router)
app.include_router(query_router)
app.include_router(progress_router)
app.mount("/frontend", StaticFiles(directory=frontend_dir), name="frontend")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": app.version}


@app.get("/")
async def root() -> FileResponse:
    return FileResponse(frontend_dir / "index.html")
