from sqlalchemy.orm import Session, selectinload

from pipeline.db_models import (
    IgnoredSignalRecord,
    KeySignalRecord,
    RunRecord,
    TraceEntryRecord,
    UncertaintyRecord,
)
from pipeline.models import IgnoredSignal, KeySignal, RunResult, TraceEntry


class RunRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def save_run(self, run_result: RunResult) -> RunRecord:
        run = RunRecord(
            id=run_result.run_id,
            created_at=run_result.timestamp,
            executive_summary=run_result.executive_summary,
            baseline_summary=run_result.baseline_comparison.summary if run_result.baseline_comparison else None,
            analyst_tokens=run_result.token_usage.analyst_tokens,
            critic_tokens=run_result.token_usage.critic_tokens,
            query_tokens=run_result.token_usage.query_tokens,
            total_tokens=run_result.token_usage.total_tokens,
        )
        self.db.add(run)
        self.db.flush()

        for signal in run_result.key_signals:
            self.db.add(
                KeySignalRecord(
                    run_id=run.id,
                    title=signal.title,
                    summary=signal.summary,
                    source=signal.source,
                    confidence=signal.confidence,
                )
            )

        for signal in run_result.ignored_signals:
            self.db.add(
                IgnoredSignalRecord(
                    run_id=run.id,
                    title=signal.title,
                    source=signal.source,
                    reason=signal.reason,
                )
            )

        for uncertainty in run_result.uncertainties:
            self.db.add(
                UncertaintyRecord(
                    run_id=run.id,
                    signal_a=uncertainty.signal_a,
                    signal_b=uncertainty.signal_b,
                    description=uncertainty.description,
                )
            )

        for entry in run_result.trace:
            self.db.add(
                TraceEntryRecord(
                    run_id=run.id,
                    stage=entry.stage,
                    agent=entry.agent,
                    inputs_summary=entry.inputs_summary,
                    outputs_summary=entry.outputs_summary,
                    decision=entry.decision,
                    tokens_used=entry.tokens_used,
                    duration_ms=entry.duration_ms,
                    created_at=entry.timestamp,
                )
            )

        self.db.commit()
        self.db.refresh(run)
        return run

    def list_runs(self) -> list[RunRecord]:
        return self.db.query(RunRecord).order_by(RunRecord.created_at.desc()).all()

    def get_run(self, run_id: str) -> RunRecord | None:
        return (
            self.db.query(RunRecord)
            .options(
                selectinload(RunRecord.key_signals),
                selectinload(RunRecord.ignored_signals),
                selectinload(RunRecord.uncertainties),
                selectinload(RunRecord.trace_entries),
            )
            .filter(RunRecord.id == run_id)
            .one_or_none()
        )


def run_record_to_summary(record: RunRecord) -> dict[str, str]:
    return {
        "run_id": record.id,
        "timestamp": record.created_at.isoformat(),
        "executive_summary": record.executive_summary,
    }


def key_signal_record_to_model(record: KeySignalRecord) -> KeySignal:
    return KeySignal(
        title=record.title,
        summary=record.summary,
        source=record.source,
        confidence=record.confidence,
    )


def ignored_signal_record_to_model(record: IgnoredSignalRecord) -> IgnoredSignal:
    return IgnoredSignal(
        title=record.title,
        source=record.source,
        reason=record.reason,
    )


def trace_entry_record_to_model(record: TraceEntryRecord) -> TraceEntry:
    return TraceEntry(
        stage=record.stage,
        agent=record.agent,
        inputs_summary=record.inputs_summary,
        outputs_summary=record.outputs_summary,
        decision=record.decision,
        tokens_used=record.tokens_used,
        duration_ms=record.duration_ms,
        timestamp=record.created_at,
    )
