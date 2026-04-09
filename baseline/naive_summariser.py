from google import genai

from pipeline.config import get_settings
from pipeline.models import RawItem


class NaiveSummariser:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required to run the baseline summariser.")

        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = "gemini-3-flash-preview"

    async def run(self, items: list[RawItem]) -> str:
        context = self._build_context(items)
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=(
                "You are a simple baseline summariser. "
                "Treat all inputs equally and produce a concise summary of what matters. "
                "Do not perform adversarial critique or explicit signal-vs-noise filtering.\n\n"
                f"{context}"
            ),
        )
        return (response.text or "").strip()

    @staticmethod
    def _build_context(items: list[RawItem]) -> str:
        if not items:
            return "No input items were provided."

        lines: list[str] = []
        for index, item in enumerate(items, start=1):
            lines.append(f"{index}. [{item.source}] {item.title}")
            if item.summary:
                lines.append(f"   {item.summary}")
        return "\n".join(lines)
