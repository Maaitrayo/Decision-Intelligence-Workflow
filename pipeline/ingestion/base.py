from abc import ABC, abstractmethod

from pipeline.models import RawItem


class BaseIngestor(ABC):
    @abstractmethod
    async def fetch(self) -> list[RawItem]:
        """Fetch raw items from a source."""

    @abstractmethod
    def source_name(self) -> str:
        """Return the canonical source name."""
