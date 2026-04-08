from pydantic import BaseModel, Field
from fastapi import APIRouter


router = APIRouter(prefix="/api/query", tags=["query"])


class QueryRequest(BaseModel):
    run_id: str
    session_id: str | None = None
    question: str = Field(min_length=1)


class QueryResponse(BaseModel):
    run_id: str
    session_id: str | None = None
    answer: str


@router.post("")
async def query_run(request: QueryRequest) -> QueryResponse:
    return QueryResponse(
        run_id=request.run_id,
        session_id=request.session_id,
        answer="Query handling is not implemented yet.",
    )
