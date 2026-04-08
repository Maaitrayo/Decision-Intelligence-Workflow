from datetime import datetime, timezone
from time import perf_counter

from pipeline.agents.analyst_agent import AnalystAgent
from pipeline.agents.critic_agent import CriticAgent
from pipeline.ingestion.service import IngestionService
from pipeline.models import RunResult, TokenUsage, TraceEntry
from pipeline.scoring.service import ScoringService
from pipeline.synthesis.synthesiser import Synthesiser


class PipelineOrchestrator:
    def __init__(self) -> None:
        self.ingestion_service = IngestionService()
        self.scoring_service = ScoringService()
        self.analyst_agent = AnalystAgent()
        self.critic_agent = CriticAgent()
        self.synthesiser = Synthesiser()

    async def run(self, eval_mode: bool = False) -> RunResult:
        trace: list[TraceEntry] = []

        ingestion_started = perf_counter()
        raw_items = await self.ingestion_service.fetch_all()
        trace.append(
            self._build_trace_entry(
                stage="ingestion",
                inputs_summary="sources=3",
                outputs_summary=f"raw_items={len(raw_items)}",
                decision="Fetched items from configured sources.",
                duration_ms=self._duration_ms(ingestion_started),
            )
        )

        scoring_started = perf_counter()
        scored_items = self.scoring_service.score(raw_items)
        trace.append(
            self._build_trace_entry(
                stage="scoring",
                inputs_summary=f"raw_items={len(raw_items)}",
                outputs_summary=f"scored_items={len(scored_items)}",
                decision="Applied deterministic scoring, deduplication, and bucketing.",
                duration_ms=self._duration_ms(scoring_started),
            )
        )

        analyst_started = perf_counter()
        analyst_output = await self.analyst_agent.run(scored_items)
        analyst_duration_ms = self._duration_ms(analyst_started)
        analyst_tokens = self.analyst_agent.last_tokens_used
        trace.append(
            self._build_trace_entry(
                stage="analyst",
                agent="analyst",
                inputs_summary=f"candidate_items={len(scored_items)}",
                outputs_summary=f"signals={len(analyst_output.signals)}",
                decision=analyst_output.reasoning or "Analyst reviewed scored items.",
                tokens_used=analyst_tokens,
                duration_ms=analyst_duration_ms,
            )
        )

        critic_started = perf_counter()
        critic_output = await self.critic_agent.run(analyst_output, scored_items)
        critic_duration_ms = self._duration_ms(critic_started)
        critic_tokens = self.critic_agent.last_tokens_used
        trace.append(
            self._build_trace_entry(
                stage="critic",
                agent="critic",
                inputs_summary=f"signals={len(analyst_output.signals)}, scored_items={len(scored_items)}",
                outputs_summary=(
                    f"endorsements={len(critic_output.endorsements)}, "
                    f"contested={len(critic_output.contested_signals)}, "
                    f"contradictions={len(critic_output.contradictions)}"
                ),
                decision=critic_output.reasoning or "Critic challenged analyst output.",
                tokens_used=critic_tokens,
                duration_ms=critic_duration_ms,
            )
        )

        synthesis_started = perf_counter()
        result = self.synthesiser.merge(analyst_output, critic_output, scored_items)
        trace.append(
            self._build_trace_entry(
                stage="synthesis",
                inputs_summary=(
                    f"analyst_signals={len(analyst_output.signals)}, "
                    f"critic_contradictions={len(critic_output.contradictions)}"
                ),
                outputs_summary=f"key_signals={len(result.key_signals)}",
                decision="Merged analyst and critic outputs into final run result.",
                duration_ms=self._duration_ms(synthesis_started),
            )
        )

        total_tokens = analyst_tokens + critic_tokens
        result.trace = trace
        result.token_usage = TokenUsage(
            analyst_tokens=analyst_tokens,
            critic_tokens=critic_tokens,
            query_tokens=0,
            total_tokens=total_tokens,
        )
        return result

    @staticmethod
    def _duration_ms(started_at: float) -> int:
        return int((perf_counter() - started_at) * 1000)

    @staticmethod
    def _build_trace_entry(
        stage: str,
        inputs_summary: str,
        outputs_summary: str,
        decision: str,
        duration_ms: int,
        agent: str | None = None,
        tokens_used: int = 0,
    ) -> TraceEntry:
        return TraceEntry(
            stage=stage,
            agent=agent,
            inputs_summary=inputs_summary,
            outputs_summary=outputs_summary,
            decision=decision,
            tokens_used=tokens_used,
            duration_ms=duration_ms,
            timestamp=datetime.now(timezone.utc),
        )
