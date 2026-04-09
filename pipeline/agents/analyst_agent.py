from pipeline.agents.base_agent import BaseAgent
from pipeline.models import AgentOutput, AgentSignal, ScoredItem


class AnalystAgent(BaseAgent):
    async def run(self, items: list[ScoredItem]) -> AgentOutput:
        candidate_items = [item for item in items if item.bucket in {"high", "medium"} and item.discard_reason is None]
        payload = await self.generate_json(
            system_prompt=(
                "You are the Analyst agent in a decision intelligence workflow. "
                "Identify the most important signals from the provided scored items. "
                "Return strict JSON with keys: signals, weak_claims, reasoning. "
                "Each signal must contain title, summary, source, confidence."
            ),
            user_prompt=(
                "Analyze these scored items and identify 3 to 5 actionable signals.\n\n"
                f"{self.build_context(candidate_items)}"
            ),
        )

        signals = [
            AgentSignal(
                title=signal.get("title", ""),
                summary=signal.get("summary", ""),
                source=signal.get("source", ""),
                confidence=self._normalize_confidence(signal.get("confidence")),
            )
            for signal in payload.get("signals", [])
            if signal.get("title")
        ]

        return AgentOutput(
            signals=signals,
            weak_claims=[claim for claim in payload.get("weak_claims", []) if isinstance(claim, str)],
            reasoning=str(payload.get("reasoning", "")),
        )

    @staticmethod
    def _normalize_confidence(value: object) -> str:
        if isinstance(value, str):
            return value.lower()

        if isinstance(value, (int, float)):
            if value >= 0.8:
                return "high"
            if value >= 0.5:
                return "medium"
            return "low"

        return "medium"
