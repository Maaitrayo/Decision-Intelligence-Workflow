from difflib import SequenceMatcher

from pipeline.models import ScoredItem


class Deduplicator:
    def __init__(self, similarity_threshold: float = 0.82) -> None:
        self.similarity_threshold = similarity_threshold

    def apply(self, items: list[ScoredItem]) -> list[ScoredItem]:
        ranked_items = sorted(items, key=lambda item: item.signal_score, reverse=True)
        deduplicated: list[ScoredItem] = []
        exact_title_index: dict[str, ScoredItem] = {}
        token_index: dict[str, list[ScoredItem]] = {}

        for item in ranked_items:
            normalized_title = self._normalize_title(item.item.title)
            duplicate_of = self._find_duplicate(item, normalized_title, exact_title_index, token_index)
            if duplicate_of is None:
                deduplicated.append(item)
                exact_title_index[normalized_title] = item
                for token in self._index_tokens(normalized_title):
                    token_index.setdefault(token, []).append(item)
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

    def _find_duplicate(
        self,
        item: ScoredItem,
        normalized_title: str,
        exact_title_index: dict[str, ScoredItem],
        token_index: dict[str, list[ScoredItem]],
    ) -> ScoredItem | None:
        exact_match = exact_title_index.get(normalized_title)
        if exact_match is not None:
            return exact_match

        candidate_pool = self._candidate_pool(normalized_title, token_index)
        if not candidate_pool:
            return None

        current_tokens = set(normalized_title.split())
        for existing in candidate_pool:
            existing_title = self._normalize_title(existing.item.title)
            if not self._titles_are_comparable(normalized_title, existing_title, current_tokens):
                continue

            similarity = SequenceMatcher(a=normalized_title, b=existing_title).ratio()
            if similarity >= self.similarity_threshold:
                return existing

        return None

    @staticmethod
    def _normalize_title(title: str) -> str:
        return " ".join(title.lower().split())

    @staticmethod
    def _index_tokens(normalized_title: str) -> list[str]:
        return [token for token in normalized_title.split() if len(token) >= 4][:6]

    def _candidate_pool(
        self,
        normalized_title: str,
        token_index: dict[str, list[ScoredItem]],
    ) -> list[ScoredItem]:
        candidates: dict[str, ScoredItem] = {}
        for token in self._index_tokens(normalized_title):
            for item in token_index.get(token, []):
                candidates[item.item.url] = item
        return list(candidates.values())

    @staticmethod
    def _titles_are_comparable(
        current_title: str,
        existing_title: str,
        current_tokens: set[str],
    ) -> bool:
        max_length = max(len(current_title), len(existing_title), 1)
        if abs(len(current_title) - len(existing_title)) > max_length * 0.35:
            return False

        existing_tokens = set(existing_title.split())
        overlap = len(current_tokens & existing_tokens)
        minimum_overlap = min(len(current_tokens), len(existing_tokens), 2)
        return overlap >= minimum_overlap
