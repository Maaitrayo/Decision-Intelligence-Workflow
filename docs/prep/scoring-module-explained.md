# Pipeline Scoring Module Explained

This document explains, technically and with examples, how every file inside `pipeline/scoring` works.

The scoring module is the deterministic non-LLM stage of the project. Its job is to take raw ingested items and turn them into ranked, filtered, explainable `ScoredItem` objects before any agent sees them.

## 1. Big Picture

The scoring flow is:

```text
list[RawItem]
  -> TFIDFScorer.score_items()
  -> Deduplicator.apply()
  -> SignalFilter.apply()
  -> list[ScoredItem]
```

This flow is orchestrated by `pipeline/scoring/service.py`.

The module exists to answer four questions deterministically:

1. How relevant is this item to the system's target topics?
2. Does the source deserve more or less trust?
3. Is this item just a duplicate of something stronger?
4. Should this item reach the agents, or should it be filtered out?

## 2. Data Types Used By The Module

The scoring code depends on two models from `pipeline/models/`.

### `RawItem`

This is the input to the scoring stage.

```python
class RawItem(BaseModel):
    source: Literal["hacker_news", "arxiv", "github_trending"]
    title: str
    url: str
    summary: str = ""
    published_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
```

Example:

```python
RawItem(
    source="hacker_news",
    title="New robotics agent learns multimodal planning",
    url="https://example.com/post-1",
    summary="A robotics system combines vision and agent planning.",
    metadata={"points": 210}
)
```

### `ScoredItem`

This is the output carried between scoring steps.

```python
class ScoredItem(BaseModel):
    item: RawItem
    signal_score: float
    bucket: Literal["high", "medium", "low", "noise"]
    discard_reason: str | None = None
    duplicate_of: str | None = None
```

Example:

```python
ScoredItem(
    item=raw_item,
    signal_score=1.0873,
    bucket="high",
    discard_reason=None,
    duplicate_of=None
)
```

## 3. File-by-File Explanation

## `pipeline/scoring/__init__.py`

Code:

```python
__all__: list[str] = []
```

What it does:
- Right now, effectively nothing functional.
- It does not export public scoring symbols.
- It mainly marks the directory as a Python package.

Why it exists:
- Without it, Python package imports can become less predictable depending on environment and packaging style.
- It gives a future place to expose stable public APIs like:
  - `TFIDFScorer`
  - `Deduplicator`
  - `SignalFilter`
  - `ScoringService`

Practical note:
- In the current repo, the module imports concrete files directly, so this file is intentionally minimal.

## `pipeline/scoring/source_weights.py`

Code summary:

```python
SOURCE_CREDIBILITY_WEIGHTS = {
    "hacker_news": 0.9,
    "arxiv": 1.0,
    "github_trending": 0.85,
}

def get_source_weight(item: RawItem) -> float:
    return SOURCE_CREDIBILITY_WEIGHTS.get(item.source, 1.0)
```

What it does:
- Assigns a credibility multiplier by source.
- This multiplier is used inside `TFIDFScorer`.
- The score from keyword relevance is multiplied by this weight before metadata boosts are added.

Why it exists:
- Not all sources should contribute equally.
- ArXiv is treated as the most credible source in this design, so it gets `1.0`.
- Hacker News gets `0.9`.
- GitHub Trending gets `0.85`.

Important detail:
- The weights only affect the base keyword score.
- Metadata boosts are added afterward, so a high-HN-points item can still score very strongly.

Example:

Assume two items have the same keyword relevance score `0.20`.

```text
ArXiv item:
0.20 * 1.00 = 0.20

Hacker News item:
0.20 * 0.90 = 0.18

GitHub Trending item:
0.20 * 0.85 = 0.17
```

That means the same textual relevance is treated slightly differently depending on source credibility.

## `pipeline/scoring/tfidf_scorer.py`

This is the main ranking engine.

### What the class does

`TFIDFScorer` converts `RawItem` objects into initial `ScoredItem` objects by combining:

1. Keyword TF-IDF-style relevance
2. Source credibility weighting
3. Source-specific metadata boosts

### Step 1: Load keywords from config

In `__init__`, the class reads:

```python
signal_keywords = "agent,multimodal,vision,safety,robotics"
```

This becomes:

```python
["agent", "multimodal", "vision", "safety", "robotics"]
```

These are the terms the system cares about most.

### Step 2: Build one text document per item

The method `_document_text(item)` creates a lowercase text blob:

- If `summary` exists, it returns `title + summary`
- Otherwise, it returns `title`

Example:

```python
title = "New robotics agent learns multimodal planning"
summary = "A robotics system combines vision and agent planning."
```

Document text becomes:

```text
new robotics agent learns multimodal planning a robotics system combines vision and agent planning.
```

### Step 3: Compute document frequency for each keyword

`_compute_document_frequencies(documents)` counts in how many documents each keyword appears.

Why this matters:
- A keyword that appears in almost every document is less informative.
- A keyword that appears in fewer documents is more discriminative.

Example corpus:

```text
Doc 1: "robotics agent vision"
Doc 2: "multimodal vision benchmark"
Doc 3: "robotics safety deployment"
```

Document frequencies:

```text
agent -> 1
multimodal -> 1
vision -> 2
safety -> 1
robotics -> 2
```

### Step 4: Tokenize and compute keyword TF-IDF-style score

`_tokenize(text)` uses this regex:

```python
findall(r"[a-z0-9]+", text.lower())
```

So punctuation is removed and only alphanumeric tokens remain.

Then `_keyword_tfidf_score(...)` computes:

```text
score += tf * idf
```

Where:
- `tf = count_of_keyword_in_document / total_terms`
- `idf = log((1 + total_documents) / (1 + document_frequency)) + 1`

### Worked example

Suppose the document is:

```text
"robotics agent multimodal robotics vision"
```

Token counts:

```text
robotics -> 2
agent -> 1
multimodal -> 1
vision -> 1
total_terms -> 5
```

Suppose in the full corpus:

```text
total_documents = 10
df(robotics) = 4
df(agent) = 2
df(multimodal) = 3
df(vision) = 6
```

Then:

```text
tf(robotics)   = 2/5 = 0.4
idf(robotics)  = log(11/5) + 1

tf(agent)      = 1/5 = 0.2
idf(agent)     = log(11/3) + 1

tf(multimodal) = 1/5 = 0.2
idf(multimodal)= log(11/4) + 1

tf(vision)     = 1/5 = 0.2
idf(vision)    = log(11/7) + 1
```

The final keyword score is the sum of those four `tf * idf` values.

This is not a full general-purpose TF-IDF ranker over all words. It is a keyword-targeted TF-IDF-style scorer over only the configured signal terms.

### Step 5: Apply source weighting

After keyword score is computed:

```python
weighted_score = base_score * get_source_weight(item)
```

So if the base score is `0.30` and the source is Hacker News:

```text
weighted_score = 0.30 * 0.9 = 0.27
```

### Step 6: Add metadata boosts

This is where the file becomes more domain-specific.

#### Hacker News boost

```python
log(points + 1) * 0.1
```

Example:

```text
points = 210
boost = log(211) * 0.1 ~= 0.535
```

This means even a moderately relevant HN item can move up if it has strong community traction.

#### GitHub Trending boost

```python
log(stars_today + 1) * 0.12
```

Example:

```text
stars_today = 900
boost = log(901) * 0.12 ~= 0.816
```

This strongly rewards repositories that are actively trending.

#### ArXiv recency boost

```python
1.0 - (age_hours / 48) * 0.2
```

clamped to a minimum of `0.0`.

What this means:
- A fresh ArXiv paper gets almost a full `+1.0` boost.
- As it approaches 48 hours old, the boost declines toward `+0.8`.
- Older papers still get a non-negative boost, but freshness matters.

Example:

```text
age_hours = 12
boost = 1.0 - (12/48)*0.2
      = 1.0 - 0.05
      = 0.95
```

### Step 7: Return `ScoredItem`

The scorer creates:

```python
ScoredItem(
    item=item,
    signal_score=round(boosted_score, 4),
    bucket="low",
)
```

Important detail:
- Every item initially gets bucket `"low"`.
- This is only a placeholder.
- Real bucket assignment happens later in `signal_filter.py`.

### Full example

Input item:

```python
RawItem(
    source="hacker_news",
    title="Robotics agent reaches new multimodal benchmark",
    url="https://example.com/a",
    summary="Vision and robotics agent system performs well.",
    metadata={"points": 150}
)
```

Suppose:

```text
base keyword score = 0.28
source weight      = 0.9
metadata boost     = log(151) * 0.1 ~= 0.5017
```

Then:

```text
weighted_score = 0.28 * 0.9 = 0.252
final_score    = 0.252 + 0.5017 = 0.7537
```

Returned object:

```python
ScoredItem(
    item=...,
    signal_score=0.7537,
    bucket="low"
)
```

This item will later become `high` in the filter stage because `0.7537 >= 0.65`.

## `pipeline/scoring/deduplicator.py`

This file removes near-duplicates after scoring.

### Why deduplication happens after scoring

The implementation sorts items by `signal_score` descending before checking duplicates.

That means:
- The strongest version of a repeated story is processed first.
- Later similar items are marked as duplicates of the stronger item.

This is useful because duplicates are not all equal. If two titles describe the same story, the higher-scoring one should survive as the main representative.

### Core behavior

`Deduplicator.apply(items)`:

1. Sorts scored items from highest to lowest score.
2. Keeps indexes of previously accepted titles.
3. For each new item, checks whether it matches a previous stronger item.
4. If yes, it marks the item as:
   - `bucket="noise"`
   - `discard_reason="duplicate"`
   - `duplicate_of=<url of original item>`
5. If not, it keeps the item unchanged.

### Exact-title fast path

The deduplicator first checks normalized exact title match:

```python
"  New Robot Agent  " -> "new robot agent"
```

If the normalized title already exists, the item is immediately treated as a duplicate.

### Token-based candidate pruning

Instead of comparing every title with every previous title, `_candidate_pool(...)` narrows candidates using index tokens:

```python
return [token for token in normalized_title.split() if len(token) >= 4][:6]
```

This means:
- Only tokens of length 4 or more are indexed.
- Only the first 6 such tokens are used.

Example title:

```text
"new robotics agent reaches multimodal benchmark"
```

Indexed tokens:

```text
["robotics", "agent", "reaches", "multimodal", "benchmark"]
```

This makes duplicate lookup much cheaper than comparing against every previously kept title.

### Comparability check before similarity

Before running `SequenceMatcher`, the code checks:

1. Are the title lengths reasonably close?
2. Do they share enough token overlap?

This avoids spending work on obviously unrelated titles.

### Similarity check

Actual fuzzy matching uses:

```python
SequenceMatcher(a=normalized_title, b=existing_title).ratio()
```

Threshold:

```python
0.82
```

If similarity is at least `0.82`, the item is treated as a duplicate.

### Example 1: Duplicate detected

Item A:

```text
Title: "Robotics agent reaches multimodal benchmark"
Score: 0.81
URL:   https://site-a.com
```

Item B:

```text
Title: "Robotics agent hits multimodal benchmark"
Score: 0.62
URL:   https://site-b.com
```

Flow:

1. Item A comes first because it has higher score.
2. Item A is kept.
3. Item B shares enough tokens with A.
4. `SequenceMatcher` similarity is high enough.
5. Item B is converted into:

```python
ScoredItem(
    item=item_b,
    signal_score=0.62,
    bucket="noise",
    discard_reason="duplicate",
    duplicate_of="https://site-a.com"
)
```

### Example 2: Not a duplicate

Item A:

```text
"Robotics agent reaches multimodal benchmark"
```

Item B:

```text
"Safety benchmark reveals hidden failure modes"
```

These items do not have enough token overlap, so they are never treated as duplicates.

### Important implementation note

This is heuristic deduplication, not semantic deduplication.

Strengths:
- Fast
- Easy to reason about
- Good enough for titles that are very similar

Limitations:
- It can miss duplicates phrased very differently
- It can falsely merge very similar titles that actually refer to different stories

## `pipeline/scoring/signal_filter.py`

This file is the final gatekeeper for scored items.

### What it does

`SignalFilter.apply(items)`:

1. Sorts items by score descending
2. Assigns a bucket based on score thresholds
3. Assigns discard reasons for:
   - items below threshold
   - items outside the top agent input limit

### Thresholds come from config

From `pipeline/config.py`:

```python
score_threshold_high = 0.65
score_threshold_medium = 0.35
score_threshold_low = 0.15
max_agent_input = 20
```

### Bucket logic

```text
score >= 0.65 -> high
score >= 0.35 -> medium
score >= 0.15 -> low
otherwise     -> noise
```

### Why buckets matter

They encode priority:

- `high`: strongest signals
- `medium`: relevant but less certain
- `low`: weak relevance
- `noise`: not worth agent attention

### Discard reasons

The filter adds one of these reasons:

#### `below_signal_threshold`

If the bucket becomes `noise`, the item is considered too weak.

Example:

```text
signal_score = 0.08
bucket = noise
discard_reason = below_signal_threshold
```

#### `outside_top_agent_input_limit`

If the item is not `noise`, but its rank index is beyond `max_agent_input`, the item is still preserved but marked as excluded from the agent input window.

Example:

Suppose:
- `max_agent_input = 20`
- An item has score `0.51`
- It ranks 24th overall

Then:

```text
bucket = medium
discard_reason = outside_top_agent_input_limit
```

This is an important design choice:
- The item is still known to be a medium-quality signal.
- But it is excluded from the expensive LLM stage.

### Example with five items

Suppose sorted scores are:

```text
1. 0.91
2. 0.70
3. 0.41
4. 0.19
5. 0.06
```

Buckets become:

```text
0.91 -> high
0.70 -> high
0.41 -> medium
0.19 -> low
0.06 -> noise
```

If item 3 were ranked 27th instead of 3rd:

```text
bucket = medium
discard_reason = outside_top_agent_input_limit
```

If item 5 remains `0.06`:

```text
bucket = noise
discard_reason = below_signal_threshold
```

### Why this file matters

This file is the last deterministic budget-control step before the agent layer.

It ensures:
- weak signals do not consume tokens
- lower-priority but still relevant signals are preserved for auditability
- the system can later explain why something did not reach the Analyst/Critic

## `pipeline/scoring/service.py`

This file coordinates the full scoring pipeline.

Code summary:

```python
class ScoringService:
    def __init__(self) -> None:
        self.scorer = TFIDFScorer()
        self.deduplicator = Deduplicator()
        self.signal_filter = SignalFilter()

    def score(self, items: list[RawItem]) -> list[ScoredItem]:
        scored_items = self.scorer.score_items(items)
        deduplicated_items = self.deduplicator.apply(scored_items)
        return self.signal_filter.apply(deduplicated_items)
```

### What it does

This is the entry point the rest of the pipeline uses.

Instead of the orchestrator needing to know about:
- keyword scoring
- source weighting
- metadata boosts
- duplicate marking
- bucket assignment

it just calls:

```python
scoring_service.score(raw_items)
```

### Why this wrapper is useful

It centralizes scoring behavior in one place.

Benefits:
- easier orchestration
- easier testing
- easier replacement of individual steps later

For example, if you later replace `Deduplicator` with embedding-based dedupe, only this composition point needs to change.

### End-to-end example

Input:

```python
items = [
    RawItem(
        source="hacker_news",
        title="Robotics agent reaches multimodal benchmark",
        url="https://a.com",
        summary="Vision and robotics agent system performs well.",
        metadata={"points": 150},
    ),
    RawItem(
        source="github_trending",
        title="robotics agent reaches multimodal benchmark",
        url="https://b.com",
        summary="Trending robotics repository.",
        metadata={"stars_today": 320},
    ),
    RawItem(
        source="arxiv",
        title="A survey of database indexing",
        url="https://c.com",
        summary="General data systems paper.",
    ),
]
```

Flow:

1. `TFIDFScorer` gives each item a score.
2. `Deduplicator` sees that the first two titles are near-duplicates.
3. The lower-ranked duplicate is marked `noise` with reason `duplicate`.
4. `SignalFilter` buckets the rest.
5. The unrelated database paper likely receives a very low keyword score and becomes `noise` with reason `below_signal_threshold`.

Possible final result:

```text
Item 1 -> high, discard_reason=None
Item 2 -> noise, discard_reason=duplicate, duplicate_of=https://a.com
Item 3 -> noise, discard_reason=below_signal_threshold
```

## 4. Design Strengths Of The Scoring Module

### Deterministic

Every decision in this module is reproducible for the same inputs and config.

### Cheap

No LLM calls happen here, so this stage controls cost.

### Explainable

Each later ignored item can be tied back to concrete reasons:
- duplicate
- below threshold
- outside top agent input limit

### Token-budget aware

The module explicitly protects the agent stage from noisy or excessive input.

## 5. Limitations And Interview-Worthy Caveats

### The scorer is keyword-targeted, not semantic

If a relevant article avoids the configured keywords, it may get under-scored.

Example:
- "Embodied planners for real-world manipulation" may be relevant to robotics
- But if it does not mention `robotics`, `agent`, `vision`, `multimodal`, or `safety`, it may score weakly

### Metadata boosts can dominate

Because boosts are additive, a very popular HN or GitHub item can score strongly even if textual relevance is only moderate.

That is intentional, but it is a trade-off.

### ArXiv gets a strong freshness advantage

The ArXiv recency boost can be large relative to base keyword score, which makes fresh research highly competitive.

### Deduplication is title-based

It does not understand deep semantic equivalence. It only approximates duplication through title normalization, token overlap, and string similarity.

## 6. One-Line Summary For Interview Use

If asked to summarize the scoring module in one line:

> The `pipeline/scoring` module is a deterministic triage layer that ranks raw inputs using keyword relevance, source credibility, and source-specific metadata, then removes duplicates and assigns filter buckets so only the best candidate signals reach the LLM agents.
