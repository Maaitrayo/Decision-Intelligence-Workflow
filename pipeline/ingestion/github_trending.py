from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from pipeline.ingestion.base import BaseIngestor
from pipeline.models import RawItem


class GitHubTrendingIngestor(BaseIngestor):
    trending_url = "https://github.com/trending/python?since=daily"
    base_url = "https://github.com"

    def source_name(self) -> str:
        return "github_trending"

    async def fetch(self) -> list[RawItem]:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(self.trending_url)
            response.raise_for_status()

        return self._parse_items(response.text)

    def _parse_items(self, html: str) -> list[RawItem]:
        soup = BeautifulSoup(html, "html.parser")
        repo_articles = soup.select("article.Box-row")
        items: list[RawItem] = []

        for article in repo_articles:
            title_link = article.select_one("h2 a")
            if title_link is None:
                continue

            repo_name = " ".join(title_link.get_text(strip=True).split())
            description_node = article.select_one("p")
            language_node = article.select_one('[itemprop="programmingLanguage"]')
            stars_today_node = article.select_one("span.d-inline-block.float-sm-right")

            items.append(
                RawItem(
                    source="github_trending",
                    title=repo_name.replace(" / ", "/"),
                    url=urljoin(self.base_url, title_link.get("href", "")),
                    summary=description_node.get_text(" ", strip=True) if description_node is not None else "",
                    metadata={
                        "language": language_node.get_text(strip=True) if language_node is not None else "",
                        "stars_today": self._parse_stars_today(
                            stars_today_node.get_text(" ", strip=True) if stars_today_node is not None else ""
                        ),
                    },
                )
            )

        return items

    @staticmethod
    def _parse_stars_today(raw_value: str) -> int:
        if not raw_value:
            return 0

        digits = "".join(char for char in raw_value if char.isdigit())
        return int(digits) if digits else 0
