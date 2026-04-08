"""
python scripts/test_arxiv_ingestor.py
"""

import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.ingestion.arxiv_rss import ArxivRssIngestor


async def main() -> None:
    ingestor = ArxivRssIngestor()
    items = await ingestor.fetch()

    preview = [item.model_dump(mode="json") for item in items[:5]]
    print(json.dumps({"count": len(items), "items": preview}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
