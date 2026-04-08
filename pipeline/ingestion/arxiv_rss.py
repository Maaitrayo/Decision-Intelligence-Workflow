from datetime import datetime, timedelta, timezone

import feedparser

from pipeline.config import get_settings
from pipeline.ingestion.base import BaseIngestor
from pipeline.models import RawItem


class ArxivRssIngestor(BaseIngestor):
    feed_url = "https://rss.arxiv.org/rss/cs.AI+cs.CV"

    def __init__(self) -> None:
        self.settings = get_settings()

    def source_name(self) -> str:
        return "arxiv"

    async def fetch(self) -> list[RawItem]:
        feed = await self._load_feed()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.settings.arxiv_max_age_hours)
        items: list[RawItem] = []

        for entry in feed.entries:
            published_at = self._parse_published_at(entry)
            if published_at is not None and published_at < cutoff:
                continue

            summary = getattr(entry, "summary", "") or ""
            items.append(
                RawItem(
                    source="arxiv",
                    title=getattr(entry, "title", "").strip(),
                    url=getattr(entry, "link", "").strip(),
                    summary=self._clean_summary(summary),
                    published_at=published_at,
                    metadata={
                        "arxiv_id": self._extract_arxiv_id(getattr(entry, "id", "") or getattr(entry, "link", "")),
                    },
                )
            )

        return items

    async def _load_feed(self):
        return await __import__("asyncio").to_thread(feedparser.parse, self.feed_url)

    @staticmethod
    def _parse_published_at(entry) -> datetime | None:
        published_parsed = getattr(entry, "published_parsed", None)
        if published_parsed is None:
            return None

        return datetime(
            year=published_parsed.tm_year,
            month=published_parsed.tm_mon,
            day=published_parsed.tm_mday,
            hour=published_parsed.tm_hour,
            minute=published_parsed.tm_min,
            second=published_parsed.tm_sec,
            tzinfo=timezone.utc,
        )

    @staticmethod
    def _clean_summary(summary: str) -> str:
        return " ".join(summary.split())[:200]

    @staticmethod
    def _extract_arxiv_id(raw_value: str) -> str:
        return raw_value.rstrip("/").split("/")[-1]
