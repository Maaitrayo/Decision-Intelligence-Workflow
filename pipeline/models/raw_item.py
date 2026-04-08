from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


SourceName = Literal["hacker_news", "arxiv", "github_trending"]


class RawItem(BaseModel):
    source: SourceName
    title: str
    url: str
    summary: str = ""
    published_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
