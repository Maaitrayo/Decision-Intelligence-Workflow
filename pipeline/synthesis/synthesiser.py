from datetime import datetime, timezone
from uuid import uuid4

from pipeline.models import (
    AgentOutput,
    ComparisonResult,
    IgnoredSignal,
    KeySignal,
    RunResult,
    ScoredItem,
    TokenUsage,
)


class Synthesiser:
    def merge(
        self,
        analyst_output: AgentOutput,
        critic_output: AgentOutput,
        scored_items: list[ScoredItem],
    ) -> RunResult:
        key_signals: list[KeySignal] = []
        contested_titles = set(critic_output.contested_signals)
        endorsed_titles = set(critic_output.endorsements)

        for signal in analyst_output.signals:
            confidence = signal.confidence or "medium"
            if signal.title in contested_titles:
                confidence = "medium"
            if signal.title in endorsed_titles:
                confidence = "high"

            key_signals.append(
                KeySignal(
                    title=signal.title,
                    summary=signal.summary,
                    source=signal.source,
                    confidence=confidence,
                )
            )

        ignored_signals = [
            IgnoredSignal(
                title=item.item.title,
                source=item.item.source,
                reason=item.discard_reason or "not_selected",
            )
            for item in scored_items
            if item.discard_reason is not None or item.bucket == "noise"
        ]

        executive_summary = self._build_executive_summary(key_signals, critic_output)

        return RunResult(
            run_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc),
            executive_summary=executive_summary,
            key_signals=key_signals,
            ignored_signals=ignored_signals,
            uncertainties=critic_output.contradictions,
            trace=[],
            baseline_comparison=ComparisonResult(),
            token_usage=TokenUsage(),
        )

    @staticmethod
    def _build_executive_summary(key_signals: list[KeySignal], critic_output: AgentOutput) -> str:
        if not key_signals:
            return "No strong signals were identified in this run."

        lead_titles = ", ".join(signal.title for signal in key_signals[:3])
        if critic_output.contradictions:
            return (
                f"Top signals centered on {lead_titles}. "
                f"The critic flagged {len(critic_output.contradictions)} uncertainties that need review before action."
            )

        return f"Top signals centered on {lead_titles}. No major contradictions were surfaced by the critic."
