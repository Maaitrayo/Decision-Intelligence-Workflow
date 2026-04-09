from pipeline.models import RawItem, ScoredItem
from pipeline.scoring.deduplicator import Deduplicator
from pipeline.scoring.signal_filter import SignalFilter
from pipeline.scoring.tfidf_scorer import TFIDFScorer


class ScoringService:
    def __init__(self) -> None:
        self.scorer = TFIDFScorer()
        self.deduplicator = Deduplicator()
        self.signal_filter = SignalFilter()

    def score(self, items: list[RawItem]) -> list[ScoredItem]:
        scored_items = self.scorer.score_items(items)
        deduplicated_items = self.deduplicator.apply(scored_items)
        return self.signal_filter.apply(deduplicated_items)
