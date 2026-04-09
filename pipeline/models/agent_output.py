from pydantic import BaseModel, Field


class AgentSignal(BaseModel):
    title: str
    summary: str
    source: str
    confidence: str | None = None


class ContradictionRecord(BaseModel):
    signal_a: str
    signal_b: str
    description: str


class AgentOutput(BaseModel):
    signals: list[AgentSignal] = Field(default_factory=list)
    weak_claims: list[str] = Field(default_factory=list)
    contested_signals: list[str] = Field(default_factory=list)
    contradictions: list[ContradictionRecord] = Field(default_factory=list)
    endorsements: list[str] = Field(default_factory=list)
    reasoning: str = ""
