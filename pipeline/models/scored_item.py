from typing import Literal

from pydantic import BaseModel

from pipeline.models.raw_item import RawItem


SignalBucket = Literal["high", "medium", "low", "noise"]


class ScoredItem(BaseModel):
    item: RawItem
    signal_score: float
    bucket: SignalBucket
    discard_reason: str | None = None
    duplicate_of: str | None = None
