from pipeline.config import get_settings
from pipeline.models import ScoredItem


class SignalFilter:
    def __init__(self) -> None:
        self.settings = get_settings()

    def apply(self, items: list[ScoredItem]) -> list[ScoredItem]:
        ranked_items = sorted(items, key=lambda item: item.signal_score, reverse=True)
        filtered_items: list[ScoredItem] = []

        for index, item in enumerate(ranked_items):
            bucket = self._bucket_for_score(item.signal_score)
            discard_reason = None

            if bucket == "noise":
                discard_reason = "below_signal_threshold"
            elif index >= self.settings.max_agent_input:
                discard_reason = "outside_top_agent_input_limit"

            filtered_items.append(
                item.model_copy(
                    update={
                        "bucket": bucket,
                        "discard_reason": discard_reason,
                    }
                )
            )

        return filtered_items

    def _bucket_for_score(self, score: float) -> str:
        if score >= self.settings.score_threshold_high:
            return "high"
        if score >= self.settings.score_threshold_medium:
            return "medium"
        if score >= self.settings.score_threshold_low:
            return "low"
        return "noise"
