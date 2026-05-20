# Agent Flow

This document explains what the `Analyst` and `Critic` agents currently receive, why they sometimes mention references like `#237` or `Item 447`, and how the final result is produced.

## Short Answer

- The `Analyst` does **not** receive all ingested items.
- The `Critic` currently **does** receive the full scored list.
- That is why the `Critic` can mention high index numbers like `#237` or `Item 447`.

## End-to-End Flow

1. Ingestion collects items from:
   - Hacker News
   - ArXiv
   - GitHub Trending

2. Scoring computes:
   - keyword-based TF-IDF style relevance
   - source weighting
   - metadata boosts
   - duplicate handling
   - buckets: `high`, `medium`, `low`, `noise`

3. Filtering applies the `max_agent_input` limit.
   - Current default: `20`
   - Items outside the top limit get:
     - `discard_reason = "outside_top_agent_input_limit"`

4. Analyst prompt construction:
   - Only items where:
     - `bucket in {"high", "medium"}`
     - `discard_reason is None`
   - So the Analyst sees only the top-ranked, kept items.

5. Critic prompt construction:
   - Receives:
     - the Analyst JSON output
     - the full `scored_items` list
   - This means the Critic can inspect far more than the top 20.

6. Synthesis:
   - merges Analyst + Critic output
   - builds:
     - executive summary
     - key signals
     - ignored signals
     - uncertainties
     - trace

## Current Code Behavior

### Analyst

The Analyst filters items before sending them to Gemini:

```python
candidate_items = [
    item for item in items
    if item.bucket in {"high", "medium"} and item.discard_reason is None
]
```

That means the Analyst sees only the top kept signals, not the entire corpus.

### Critic

The Critic currently gets the full scored list:

```python
user_prompt=(
    "Analyst output:\n"
    f"{analyst_output.model_dump_json(indent=2)}\n\n"
    "Scored items:\n"
    f"{self.build_context(items)}"
)
```

In the orchestrator, `items` here is the full `scored_items` list.

## Why You See `#237` or `Item 447`

The base agent formats prompt context as a numbered list:

```python
for index, item in enumerate(items, start=1):
    lines.append(
        f"{index}. {item.item.title} | source={item.item.source} | "
        f"score={item.signal_score} | bucket={item.bucket}"
    )
```

So when Gemini says:

- `#237`
- `Item 447`

it is not referring to:

- a database row ID
- a run ID
- a stable session ID

It is only referring to the temporary numbered position of that item in the prompt.

## Example With a 533-Item Run

Assume ingestion returns `533` raw items.

After scoring/filtering:

- all 533 become `scored_items`
- only the top kept `high`/`medium` items are eligible for the Analyst
- with `max_agent_input = 20`, the Analyst usually sees at most 20 items
- the Critic currently still sees all 533 scored items

So:

- Analyst trace can show:
  - `Inputs: candidate_items=20`
- Critic trace can show:
  - `Inputs: signals=4, scored_items=533`

This is why the Critic can refer to much larger prompt indices than the Analyst.

## Why the Critic Token Count Is Much Higher

In a run like:

- Analyst tokens: `3314`
- Critic tokens: `48936`

the likely reason is:

- Analyst prompt contains only the filtered candidate set
- Critic prompt contains:
  - the Analyst output
  - the entire scored list

So the Critic prompt is much larger.

## What Is Working Today

- Analyst is acting on a filtered shortlist of strong candidates
- Critic is acting as a broader reviewer over the larger scored corpus
- synthesis merges both outputs into the saved run result

## Current Weakness

The current Critic prompt is too large and too loose.

Effects:

- high token cost
- slower response
- references to unstable prompt indices
- more room for noisy contradictions from low-value items

## Recommended Next Improvement

The clean next step is:

1. limit the Critic to a controlled subset
   - for example top 20-40 items
   - or top kept items plus a few contradicter candidates

2. stop exposing numeric item references in prompts
   - use source + short title labels instead

3. explicitly instruct Gemini:
   - do not cite `Item N`
   - cite title/source instead

## Simple Mental Model

- Ingestion collects everything
- Scoring ranks everything
- Analyst reads the shortlist
- Critic currently reads almost everything
- Synthesiser writes the final decision package

