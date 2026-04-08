from difflib import SequenceMatcher

from pipeline.models import ScoredItem


class Deduplicator:
    def __init__(self, similarity_threshold: float = 0.82) -> None:
        self.similarity_threshold = similarity_threshold

    def apply(self, items: list[ScoredItem]) -> list[ScoredItem]:
        ranked_items = sorted(items, key=lambda item: item.signal_score, reverse=True)
        deduplicated: list[ScoredItem] = []

        for item in ranked_items:
            duplicate_of = self._find_duplicate(item, deduplicated)
            if duplicate_of is None:
                deduplicated.append(item)
                continue

            deduplicated.append(
                item.model_copy(
                    update={
                        "bucket": "noise",
                        "discard_reason": "duplicate",
                        "duplicate_of": duplicate_of.item.url,
                    }
                )
            )

        return deduplicated

    def _find_duplicate(self, item: ScoredItem, existing_items: list[ScoredItem]) -> ScoredItem | None:
        current_title = self._normalize_title(item.item.title)

        for existing in existing_items:
            existing_title = self._normalize_title(existing.item.title)
            similarity = SequenceMatcher(a=current_title, b=existing_title).ratio()
            if similarity >= self.similarity_threshold:
                return existing

        return None

    @staticmethod
    def _normalize_title(title: str) -> str:
        return " ".join(title.lower().split())
