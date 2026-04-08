from baseline.naive_summariser import NaiveSummariser
from evaluation.metrics import contradiction_count, decision_clarity_proxy, token_efficiency
from pipeline.models import ComparisonResult, RawItem, RunResult


class EvaluationComparer:
    def __init__(self) -> None:
        self.baseline = NaiveSummariser()

    async def compare(self, raw_items: list[RawItem], run_result: RunResult) -> ComparisonResult:
        baseline_summary = await self.baseline.run(raw_items)
        return ComparisonResult(
            summary=(
                "Compared the multi-agent workflow against a naive single-call summary. "
                f"Baseline summary: {baseline_summary[:400]}"
            ),
            decision_clarity_score=decision_clarity_proxy(run_result),
            token_efficiency=token_efficiency(run_result),
            contradiction_detection_rate=float(contradiction_count(run_result)),
        )
