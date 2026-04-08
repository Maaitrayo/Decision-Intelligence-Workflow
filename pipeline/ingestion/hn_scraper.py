from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from pipeline.config import get_settings
from pipeline.ingestion.base import BaseIngestor
from pipeline.models import RawItem


class HackerNewsIngestor(BaseIngestor):
    base_url = "https://news.ycombinator.com/"
    news_path = "news"

    def __init__(self) -> None:
        self.settings = get_settings()

    def source_name(self) -> str:
        return "hacker_news"

    async def fetch(self) -> list[RawItem]:
        timeout = httpx.Timeout(self.settings.hn_timeout)

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(urljoin(self.base_url, self.news_path))
            response.raise_for_status()

        return self._parse_items(response.text)

    def _parse_items(self, html: str) -> list[RawItem]:
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select("tr.athing")
        items: list[RawItem] = []

        for row in rows:
            title_link = row.select_one("span.titleline > a")
            if title_link is None:
                continue

            subtext_row = row.find_next_sibling("tr")
            score_text = ""
            comments_text = ""

            if subtext_row is not None:
                score = subtext_row.select_one("span.score")
                subline_links = subtext_row.select("span.subline > a")
                score_text = score.get_text(strip=True) if score is not None else ""
                comments_text = subline_links[-1].get_text(strip=True) if subline_links else ""

            title = title_link.get_text(strip=True)
            url = urljoin(self.base_url, title_link.get("href", ""))
            rank = row.select_one("span.rank")

            items.append(
                RawItem(
                    source="hacker_news",
                    title=title,
                    url=url,
                    metadata={
                        "rank": self._parse_rank(rank.get_text(strip=True) if rank is not None else ""),
                        "points": self._parse_points(score_text),
                        "comment_count": self._parse_comments(comments_text),
                    },
                )
            )

        return items

    @staticmethod
    def _parse_rank(raw_rank: str) -> int | None:
        value = raw_rank.rstrip(".")
        return int(value) if value.isdigit() else None

    @staticmethod
    def _parse_points(raw_points: str) -> int:
        if not raw_points:
            return 0

        value = raw_points.split()[0]
        return int(value) if value.isdigit() else 0

    @staticmethod
    def _parse_comments(raw_comments: str) -> int:
        if not raw_comments:
            return 0
        if raw_comments == "discuss":
            return 0

        value = raw_comments.split()[0]
        return int(value) if value.isdigit() else 0
