"""
python scripts/test_ingestion.py
"""

import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.ingestion.service import IngestionService


async def main():
    print("Starting ingestion test...\n")

    service = IngestionService()

    items = await service.fetch_all()

    print(f"Total items fetched: {len(items)}\n")

    # Print first few items for inspection
    for i, item in enumerate(items[:1000]):
        print(f"{i+1}. [{item.source}] {item.title}")
        print(f"   URL: {item.url}")
        print(f"   Metadata: {item.metadata}")
        print()

    print("Ingestion test completed.")


if __name__ == "__main__":
    asyncio.run(main())