from abc import ABC, abstractmethod
import json

from google import genai

from pipeline.config import get_settings
from pipeline.models import AgentOutput, ScoredItem


class BaseAgent(ABC):
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required to run LLM-backed agents.")

        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = "gemini-2.5-flash"

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

    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=f"{system_prompt}\n\n{user_prompt}",
        )
        text = response.text or "{}"
        return json.loads(text)
