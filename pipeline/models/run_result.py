from datetime import datetime

from pydantic import BaseModel, Field

from pipeline.models.agent_output import ContradictionRecord


class TraceEntry(BaseModel):
    stage: str
    agent: str | None = None
    inputs_summary: str = ""
    outputs_summary: str = ""
    decision: str = ""
    tokens_used: int = 0
    duration_ms: int = 0
    timestamp: datetime


class TokenUsage(BaseModel):
    analyst_tokens: int = 0
    critic_tokens: int = 0
    query_tokens: int = 0
    total_tokens: int = 0


class KeySignal(BaseModel):
    title: str
    summary: str
    source: str
    confidence: str


class IgnoredSignal(BaseModel):
    title: str
    source: str
    reason: str


class ComparisonResult(BaseModel):
    summary: str = ""
    decision_clarity_score: float | None = None
    token_efficiency: float | None = None
    contradiction_detection_rate: float | None = None


class RunResult(BaseModel):
    run_id: str
    timestamp: datetime
    executive_summary: str
    key_signals: list[KeySignal] = Field(default_factory=list)
    ignored_signals: list[IgnoredSignal] = Field(default_factory=list)
    uncertainties: list[ContradictionRecord] = Field(default_factory=list)
    trace: list[TraceEntry] = Field(default_factory=list)
    baseline_comparison: ComparisonResult | None = None
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
