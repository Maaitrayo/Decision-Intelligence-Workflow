from pipeline.models import RunResult


def token_efficiency(run_result: RunResult) -> float:
    total_tokens = run_result.token_usage.total_tokens
    if total_tokens <= 0:
        return 0.0
    return round((len(run_result.key_signals) / total_tokens) * 1000, 4)


def contradiction_count(run_result: RunResult) -> int:
    return len(run_result.uncertainties)


def decision_clarity_proxy(run_result: RunResult) -> float:
    summary_length = len((run_result.executive_summary or "").split())
    signal_count = len(run_result.key_signals)

    if summary_length == 0:
        return 0.0

    score = min(signal_count, 5) * 0.8
    if summary_length <= 60:
        score += 1.0
    elif summary_length <= 100:
        score += 0.5

    return round(min(score, 5.0), 2)
