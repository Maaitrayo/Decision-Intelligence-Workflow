from abc import ABC
import json

from google import genai

from pipeline.config import get_settings
from pipeline.models import ScoredItem


class BaseAgent(ABC):
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required to run LLM-backed agents.")

        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = "gemini-3-flash-preview"
        self.last_tokens_used = 0

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
        self.last_tokens_used = self._extract_tokens_used(response)
        text = response.text or "{}"
        return self._parse_json_response(text)

    @staticmethod
    def _parse_json_response(text: str) -> dict:
        candidate = text.strip()

        if candidate.startswith("```"):
            lines = candidate.splitlines()
            if lines:
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            candidate = "\n".join(lines).strip()

        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Gemini returned non-JSON content. "
                f"Raw response: {text[:1000]}"
            ) from exc

    @staticmethod
    def _extract_tokens_used(response: object) -> int:
        usage_metadata = getattr(response, "usage_metadata", None)
        if usage_metadata is None:
            return 0

        candidates = [
            getattr(usage_metadata, "total_token_count", None),
            getattr(usage_metadata, "total_tokens", None),
            getattr(usage_metadata, "candidates_token_count", None),
        ]
        for value in candidates:
            if isinstance(value, int):
                return value

        return 0
