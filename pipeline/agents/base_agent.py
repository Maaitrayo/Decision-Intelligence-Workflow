from abc import ABC, abstractmethod

from pipeline.models import AgentOutput, ScoredItem


class BaseAgent(ABC):
    @abstractmethod
    async def run(self, items: list[ScoredItem]) -> AgentOutput:
        """Execute the agent against scored items."""

    @staticmethod
    def build_context(items: list[ScoredItem]) -> str:
        lines: list[str] = []
        for index, item in enumerate(items, start=1):
            lines.append(
                f"{index}. {item.item.title} | source={item.item.source} | "
                f"score={item.signal_score} | bucket={item.bucket}"
            )
            if item.item.summary:
                lines.append(f"   summary={item.item.summary}")

        return "\n".join(lines)
