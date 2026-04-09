import asyncio

from pipeline.ingestion.arxiv_rss import ArxivRssIngestor
from pipeline.ingestion.github_trending import GitHubTrendingIngestor
from pipeline.ingestion.hn_scraper import HackerNewsIngestor
from pipeline.models import RawItem


class IngestionService:
    def __init__(self) -> None:
        self.ingestors = [
            HackerNewsIngestor(),
            ArxivRssIngestor(),
            GitHubTrendingIngestor(),
        ]

    async def fetch_all(self) -> list[RawItem]:
        results = await asyncio.gather(
            *(ingestor.fetch() for ingestor in self.ingestors),
            return_exceptions=True,
        )

        items: list[RawItem] = []
        for result in results:
            if isinstance(result, Exception):
                continue
            items.extend(result)

        return items
