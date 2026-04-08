from pipeline.agents.base_agent import BaseAgent
from pipeline.models import AgentOutput, AgentSignal, ScoredItem


class AnalystAgent(BaseAgent):
    async def run(self, items: list[ScoredItem]) -> AgentOutput:
        candidate_items = [item for item in items if item.bucket in {"high", "medium"} and item.discard_reason is None]
        top_items = candidate_items[:5]

        signals = [
            AgentSignal(
                title=item.item.title,
                summary=self._build_signal_summary(item),
                source=item.item.source,
                confidence=self._confidence_for_bucket(item.bucket),
            )
            for item in top_items
        ]

        weak_claims = [item.item.title for item in candidate_items if item.bucket == "medium"]

        return AgentOutput(
            signals=signals,
            weak_claims=weak_claims,
            reasoning=f"Selected {len(signals)} signals from {len(candidate_items)} candidate items.",
        )

    @staticmethod
    def _build_signal_summary(item: ScoredItem) -> str:
        if item.item.summary:
            return item.item.summary
        return f"{item.item.title} surfaced with score {item.signal_score} from {item.item.source}."

    @staticmethod
    def _confidence_for_bucket(bucket: str) -> str:
        if bucket == "high":
            return "high"
        if bucket == "medium":
            return "medium"
        return "low"
