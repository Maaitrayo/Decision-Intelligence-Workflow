# Evaluation Flow

This document explains how evaluation currently works in this project, what is being compared, how the metrics are calculated, where the result is stored, and how to run it.

## Purpose

The assignment asks for:

- compare the main system against a simpler baseline
- use 2 to 3 meaningful metrics

This project currently does that in a lightweight but clear way:

- **Main system**: full multi-stage pipeline
- **Baseline**: one simple Gemini summarisation pass over all raw items
- **Metrics**:
  - token efficiency
  - decision clarity proxy
  - contradiction count

## What Is Being Compared

### Main System

The main system is the full workflow:

1. ingestion
2. deterministic scoring
3. deduplication and bucketing
4. Analyst agent
5. Critic agent
6. synthesis

This produces a `RunResult` with:

- `executive_summary`
- `key_signals`
- `ignored_signals`
- `uncertainties`
- `trace`
- `token_usage`

### Baseline

The baseline is intentionally much simpler:

- no scoring
- no deduplication
- no signal-vs-noise filtering
- no Analyst/Critic split
- no contradiction pass

It simply sends all raw items to Gemini and asks for one concise summary.

Source: [naive_summariser.py](C:\Users\USER\work\PERCEPTECH\Personal\Assignment\Decision-Intelligence-Workflow\baseline\naive_summariser.py)

## Evaluation Architecture

```text
Raw Items
   |
   +------------------------------+
   |                              |
   v                              v
Main Pipeline                 Naive Baseline
   |                              |
   v                              v
RunResult                    baseline_summary
   |                              |
   +--------------+---------------+
                  |
                  v
         EvaluationComparer
                  |
                  v
   RunResult.baseline_comparison
```

## How the Evaluation Runs

Evaluation is only triggered when the orchestrator is called with:

```python
result = await PipelineOrchestrator().run(eval_mode=True)
```

If `eval_mode=False`, the normal run is produced and no baseline comparison is added.

## Code Path

### 1. Orchestrator

The orchestrator runs the full pipeline first.

Then, only when `eval_mode=True`, it runs the comparison:

```python
if eval_mode:
    progress_tracker.set_state("evaluation", "Running baseline comparison", True)
    self._log("Stage: evaluation started")
    result.baseline_comparison = await self.evaluation_comparer.compare(raw_items, result)
    self._log("Stage: evaluation completed")
```

Source: [orchestrator.py](C:\Users\USER\work\PERCEPTECH\Personal\Assignment\Decision-Intelligence-Workflow\pipeline\orchestrator.py)

### 2. Baseline Summariser

The baseline gets the full raw corpus and sends it to Gemini as a single summarisation task:

```python
response = await self.client.aio.models.generate_content(
    model=self.model,
    contents=(
        "You are a simple baseline summariser. "
        "Treat all inputs equally and produce a concise summary of what matters. "
        "Do not perform adversarial critique or explicit signal-vs-noise filtering.\n\n"
        f"{context}"
    ),
)
```

Key point:

- every raw item is treated equally
- no pre-filtering is applied

Source: [naive_summariser.py](C:\Users\USER\work\PERCEPTECH\Personal\Assignment\Decision-Intelligence-Workflow\baseline\naive_summariser.py)

### 3. Comparison Layer

The comparison layer runs the baseline and attaches metric values based on the **main system output**:

```python
return ComparisonResult(
    summary=(
        "Compared the multi-agent workflow against a naive single-call summary. "
        f"Baseline summary: {baseline_summary[:400]}"
    ),
    decision_clarity_score=decision_clarity_proxy(run_result),
    token_efficiency=token_efficiency(run_result),
    contradiction_detection_rate=float(contradiction_count(run_result)),
)
```

Source: [compare.py](C:\Users\USER\work\PERCEPTECH\Personal\Assignment\Decision-Intelligence-Workflow\evaluation\compare.py)

## Current Metrics

Source: [metrics.py](C:\Users\USER\work\PERCEPTECH\Personal\Assignment\Decision-Intelligence-Workflow\evaluation\metrics.py)

### 1. Token Efficiency

Definition:

```python
(len(run_result.key_signals) / total_tokens) * 1000
```

Interpretation:

- higher means the system is producing more surfaced signals per token consumed
- this is a rough efficiency proxy, not a formal cost-quality measure

Example:

- `key_signals = 4`
- `total_tokens = 50000`

Then:

```text
token_efficiency = (4 / 50000) * 1000 = 0.08
```

### 2. Decision Clarity Proxy

This is a lightweight heuristic based on:

- how many key signals exist
- how concise the executive summary is

Logic:

```python
score = min(signal_count, 5) * 0.8
if summary_length <= 60:
    score += 1.0
elif summary_length <= 100:
    score += 0.5
```

Interpretation:

- more signals can improve clarity
- shorter executive summaries are rewarded
- capped at `5.0`

This is not a human-evaluation rubric. It is only a practical project metric.

### 3. Contradiction Detection Rate

Current implementation:

```python
len(run_result.uncertainties)
```

Interpretation:

- more surfaced contradictions means the system is doing more uncertainty reporting
- right now this is actually a contradiction **count**, even though the field name says `rate`

This is useful for assignment reporting, but the naming is looser than ideal.

## Important Limitation

The current comparison is **not** a perfect head-to-head metric comparison between main system and baseline.

Why:

- the baseline currently returns only a text summary
- the metrics are computed from `RunResult`, which belongs to the main system
- the baseline summary is embedded into the comparison text, but it is not parsed into the same structured schema

So the current evaluation is:

- main system structured metrics
- plus baseline summary as a qualitative reference

That is acceptable for the assignment as a first pass, but it is important to describe it honestly.

## What Gets Stored

Evaluation is stored inside the run result itself:

```python
class RunResult(BaseModel):
    ...
    baseline_comparison: ComparisonResult | None = None
```

And the comparison shape is:

```python
class ComparisonResult(BaseModel):
    summary: str = ""
    decision_clarity_score: float | None = None
    token_efficiency: float | None = None
    contradiction_detection_rate: float | None = None
```

Source: [run_result.py](C:\Users\USER\work\PERCEPTECH\Personal\Assignment\Decision-Intelligence-Workflow\pipeline\models\run_result.py)

That means:

- evaluation is saved with the run
- it is not stored in a separate evaluation table
- if a run is persisted, its evaluation travels with it

## How to Run Evaluation

### Option 1: Python Script

Use:

```powershell
python scripts\run_evaluation.py
```

That script:

1. runs the orchestrator with `eval_mode=True`
2. saves the full JSON result in `assets/`

Source: [run_evaluation.py](C:\Users\USER\work\PERCEPTECH\Personal\Assignment\Decision-Intelligence-Workflow\scripts\run_evaluation.py)

### Option 2: API

Run the server:

```powershell
uvicorn api.index:app --reload
```

Then call:

```powershell
curl -X POST http://127.0.0.1:8000/api/runs ^
  -H "Content-Type: application/json" ^
  -d "{\"eval\": true}"
```

## Example Output Shape

A saved evaluation run will contain a section like:

```json
{
  "baseline_comparison": {
    "summary": "Compared the multi-agent workflow against a naive single-call summary. Baseline summary: ...",
    "decision_clarity_score": 3.7,
    "token_efficiency": 0.081,
    "contradiction_detection_rate": 3.0
  }
}
```

## Example Interpretation

Suppose a run gives:

- `decision_clarity_score = 3.7`
- `token_efficiency = 0.081`
- `contradiction_detection_rate = 3.0`

A reasonable interpretation is:

- the system produced a moderately clear decision package
- the token cost was substantial relative to the number of final surfaced signals
- the Critic did surface multiple tensions instead of giving a one-sided summary

In the README, this can be explained as:

- the baseline is simpler and cheaper conceptually
- the full system is more structured, more critique-aware, and more decision-oriented

## Concrete Example: Main vs Baseline

### Main System

Input:

- 533 raw items

Output:

- 4 key signals
- explicit ignored signals
- 3 uncertainties
- trace entries
- token accounting

### Baseline

Input:

- same 533 raw items

Output:

- one plain summary paragraph

### Difference

The main system is trying to answer:

- what are the strongest signals?
- what was ignored?
- what is uncertain or contradicted?

The baseline is only trying to answer:

- what seems important overall?

That difference is the core point of the evaluation.

## Recommended README Framing

A good short framing is:

> We compare the full decision-intelligence pipeline against a naive single-call summariser over the same raw corpus. The full system is evaluated on token efficiency, decision clarity, and contradiction surfacing. These are lightweight project metrics rather than formal human-eval benchmarks, but they show the tradeoff between a simpler summary baseline and a structured, critique-aware workflow.

## What To Improve Later

If you want a stronger evaluation later, improve these areas:

1. compute comparable metrics for the baseline too
2. rename `contradiction_detection_rate` to `contradiction_count` or make it a true rate
3. add small human evaluation notes for a few sample runs
4. compare latency in addition to tokens

