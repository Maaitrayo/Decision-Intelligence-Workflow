from google import genai
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from pipeline.config import get_settings
from pipeline.db import get_db_session
from pipeline.repository import RunRepository, run_record_to_model


router = APIRouter(prefix="/api/query", tags=["query"])


class QueryRequest(BaseModel):
    run_id: str
    session_id: str | None = None
    question: str = Field(min_length=1)


class QueryResponse(BaseModel):
    run_id: str
    session_id: str | None = None
    answer: str


class ChatMessageResponse(BaseModel):
    role: str
    content: str


class ChatSessionResponse(BaseModel):
    run_id: str
    session_id: str | None = None
    messages: list[ChatMessageResponse]


@router.post("")
async def query_run(
    request: QueryRequest,
    db: Session = Depends(get_db_session),
) -> QueryResponse:
    repository = RunRepository(db)
    run = repository.get_run(request.run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    if request.session_id:
        session = repository.get_chat_session(request.session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Chat session not found")
    else:
        session = repository.create_chat_session(request.run_id, title=request.question[:80])

    repository.add_chat_message(session.id, "user", request.question)

    settings = get_settings()
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is required to run follow-up queries.")

    run_result = run_record_to_model(run)
    chat_history = repository.get_chat_session(session.id)
    history_text = ""
    if chat_history is not None and chat_history.messages:
        history_text = "\n".join(
            f"{message.role}: {message.content}"
            for message in chat_history.messages[-10:]
        )

    client = genai.Client(api_key=settings.gemini_api_key)
    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=(
            "You are answering a follow-up question about a saved decision intelligence run. "
            "Use only the provided run context and prior chat history. "
            "Do not claim you reran the pipeline.\n\n"
            f"Run context:\n{run_result.model_dump_json(indent=2)}\n\n"
            f"Chat history:\n{history_text}\n\n"
            f"User question:\n{request.question}"
        ),
    )
    answer = response.text or "No answer generated."
    repository.add_chat_message(session.id, "assistant", answer)

    return QueryResponse(
        run_id=request.run_id,
        session_id=session.id,
        answer=answer,
    )


@router.get("/{run_id}")
async def get_run_chat_history(
    run_id: str,
    db: Session = Depends(get_db_session),
) -> ChatSessionResponse:
    repository = RunRepository(db)
    run = repository.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    session = repository.get_latest_chat_session_for_run(run_id)
    if session is None:
        return ChatSessionResponse(run_id=run_id, session_id=None, messages=[])

    return ChatSessionResponse(
        run_id=run_id,
        session_id=session.id,
        messages=[
            ChatMessageResponse(role=message.role, content=message.content)
            for message in session.messages
        ],
    )
