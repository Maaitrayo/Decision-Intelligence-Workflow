from __future__ import annotations

from collections import Counter
from math import log
from re import findall
from datetime import datetime, timezone

from pipeline.config import get_settings
from pipeline.models import RawItem, ScoredItem
from pipeline.scoring.source_weights import get_source_weight


class TFIDFScorer:
    def __init__(self) -> None:
        settings = get_settings()
        self.keywords = [keyword.strip().lower() for keyword in settings.signal_keywords.split(",") if keyword.strip()]

    def score_items(self, items: list[RawItem]) -> list[ScoredItem]:
        if not items:
            return []

        documents = [self._document_text(item) for item in items]
        document_frequencies = self._compute_document_frequencies(documents)
        scored_items: list[ScoredItem] = []

        for item, document in zip(items, documents, strict=True):
            base_score = self._keyword_tfidf_score(document, document_frequencies, len(documents))
            weighted_score = base_score * get_source_weight(item)
            boosted_score = weighted_score + self._metadata_boost(item)

            scored_items.append(
                ScoredItem(
                    item=item,
                    signal_score=round(boosted_score, 4),
                    bucket="low",
                )
            )

        return scored_items

    def _keyword_tfidf_score(
        self,
        document: str,
        document_frequencies: dict[str, int],
        total_documents: int,
    ) -> float:
        if not document or not self.keywords:
            return 0.0

        terms = self._tokenize(document)
        if not terms:
            return 0.0

        term_counts = Counter(terms)
        total_terms = len(terms)
        score = 0.0

        for keyword in self.keywords:
            count = term_counts.get(keyword, 0)
            if count == 0:
                continue

            tf = count / total_terms
            idf = log((1 + total_documents) / (1 + document_frequencies.get(keyword, 0))) + 1
            score += tf * idf

        return score

    def _compute_document_frequencies(self, documents: list[str]) -> dict[str, int]:
        frequencies = {keyword: 0 for keyword in self.keywords}

        for document in documents:
            terms = set(self._tokenize(document))
            for keyword in self.keywords:
                if keyword in terms:
                    frequencies[keyword] += 1

        return frequencies

    def _document_text(self, item: RawItem) -> str:
        if item.summary:
            return f"{item.title} {item.summary}".strip().lower()
        return item.title.strip().lower()

    def _metadata_boost(self, item: RawItem) -> float:
        if item.source == "hacker_news":
            points = int(item.metadata.get("points", 0) or 0)
            return log(points + 1) * 0.1

        if item.source == "github_trending":
            stars_today = int(item.metadata.get("stars_today", 0) or 0)
            return log(stars_today + 1) * 0.12

        if item.source == "arxiv" and item.published_at is not None:
            published_at = item.published_at
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=timezone.utc)

            age_hours = max((datetime.now(timezone.utc) - published_at).total_seconds() / 3600, 0)
            return max(1.0 - (age_hours / 48) * 0.2, 0.0)

        return 0.0

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return findall(r"[a-z0-9]+", text.lower())
