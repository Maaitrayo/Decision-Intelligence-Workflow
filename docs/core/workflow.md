# Signal vs Noise — Decision Intelligence Workflow
## Codebase Scaffold & Module Plans

---

## Repository Structure

```
signal-vs-noise/
│
├── api/                            # Vercel serverless Python backend
│   ├── index.py                    # FastAPI app entrypoint (Vercel handler)
│   └── routes/
│       ├── run.py                  # POST /run — trigger full pipeline
│       ├── query.py                # POST /query — follow-up Q&A
│       └── health.py               # GET /health
│
├── pipeline/                       # Core pipeline (pure Python, no framework coupling)
│   ├── __init__.py
│   ├── orchestrator.py             # Pipeline coordinator — wires all stages
│   │
│   ├── ingestion/                  # Stage 1: Data collection
│   │   ├── __init__.py
│   │   ├── base.py                 # Abstract base class: BaseIngestor
│   │   ├── hn_scraper.py           # Hacker News scraper (BeautifulSoup)
│   │   ├── arxiv_rss.py            # ArXiv RSS feed parser (feedparser)
│   │   └── github_trending.py      # GitHub Trending scraper
│   │
│   ├── scoring/                    # Stage 2: Deterministic signal scoring (NO LLM)
│   │   ├── __init__.py
│   │   ├── tfidf_scorer.py         # TF-IDF keyword relevance scorer
│   │   ├── source_weights.py       # Static source credibility weights
│   │   ├── deduplicator.py         # Near-duplicate detection (cosine sim on TF-IDF)
│   │   └── signal_filter.py        # Buckets items: HIGH / MEDIUM / LOW / NOISE
│   │
│   ├── agents/                     # Stage 3: LLM agents
│   │   ├── __init__.py
│   │   ├── base_agent.py           # Shared: prompt builder, token budget, retry
│   │   ├── analyst_agent.py        # Summarises high-signal items, flags weak claims
│   │   └── critic_agent.py         # Challenges analyst output, surfaces contradictions
│   │
│   ├── synthesis/                  # Stage 4: Final output assembly
│   │   ├── __init__.py
│   │   └── synthesiser.py          # Merges analyst + critic → structured RunResult
│   │
│   └── models/                     # Pydantic data models (shared across all stages)
│       ├── __init__.py
│       ├── raw_item.py             # RawItem: url, title, source, metadata
│       ├── scored_item.py          # ScoredItem: RawItem + signal_score + bucket
│       ├── agent_output.py         # AgentOutput: signals, contradictions, confidence
│       └── run_result.py           # RunResult: full structured pipeline output
│
├── baseline/                       # Naive baseline for evaluation comparison
│   ├── __init__.py
│   └── naive_summariser.py         # Single LLM call, all inputs treated equally
│
├── evaluation/                     # Evaluation metrics
│   ├── __init__.py
│   ├── metrics.py                  # Clarity score, token efficiency, contradiction rate
│   └── compare.py                  # Runs both pipeline + baseline, emits comparison
│
├── observability/                  # Tracing and logging
│   ├── __init__.py
│   └── trace_logger.py             # Structured JSON trace emitter (per-stage)
│
├── frontend/                       # Minimal Next.js UI
│   ├── package.json
│   ├── next.config.js
│   └── app/
│       ├── page.tsx                # Main UI: trigger button + results display
│       ├── components/
│       │   ├── RunButton.tsx       # Trigger button + loading state
│       │   ├── ExecutiveSummary.tsx
│       │   ├── SignalList.tsx      # HIGH signals with confidence badges
│       │   ├── NoiseList.tsx       # Discarded items + reason
│       │   ├── TracePanel.tsx      # Collapsible per-stage trace log
│       │   ├── UncertaintyBanner.tsx  # Surfaces contradictions
│       │   └── QAChat.tsx          # Follow-up Q&A chat
│       └── lib/
│           └── api.ts              # Typed API client
│
├── tests/
│   ├── unit/
│   │   ├── test_tfidf_scorer.py
│   │   ├── test_signal_filter.py
│   │   ├── test_deduplicator.py
│   │   └── test_models.py
│   └── integration/
│       ├── test_ingestion.py       # Live scraper smoke tests (skipped in CI)
│       └── test_pipeline_e2e.py    # Full pipeline run with fixture data
│
├── fixtures/                       # Static test data (no live network needed)
│   ├── hn_sample.json
│   ├── arxiv_sample.json
│   └── github_sample.json
│
├── vercel.json                     # Vercel routing config
├── requirements.txt
├── .env.example
└── README.md
```

---

## Module Plans

---

### M1 — Ingestion Layer (`pipeline/ingestion/`)

**Responsibility:** Fetch raw items from all three sources in parallel. Normalise into `RawItem`.

**Interface:**
```python
class BaseIngestor(ABC):
    async def fetch(self) -> list[RawItem]: ...
    def source_name(self) -> str: ...
```

**`hn_scraper.py`**
- Target: `https://news.ycombinator.com/news`
- Parse: title, url, points, comment_count, rank
- Deterministic metadata: `rank` and `points` feed directly into scorer
- Library: `httpx` (async) + `BeautifulSoup`
- Timeout: 8s. On failure: return cached fixture or empty list (never crash pipeline)

**`arxiv_rss.py`**
- Target: `http://rss.arxiv.org/rss/cs.AI+cs.CV`
- Parse: title, abstract (first 200 chars), arxiv_id, published_date
- Library: `feedparser` (sync, wrap in `asyncio.to_thread`)
- Filter: last 48h only (reduces noise from backlog)

**`github_trending.py`**
- Target: `https://github.com/trending/python?since=daily`
- Parse: repo name, description, stars_today, language
- `stars_today` is strong quantitative signal — feeds scorer directly

**Parallelism:** All three fetches run via `asyncio.gather`. Total budget: 10s wall time.

**Output:** `list[RawItem]` — unranked, unfiltered, raw.

---

### M2 — Deterministic Scorer (`pipeline/scoring/`)

**Responsibility:** Score and bucket every `RawItem` without touching an LLM.
This is the required non-LLM deterministic step.

**Pipeline within M2:**
```
RawItem list
    → deduplicator.py       (remove near-duplicates, keep highest-scored copy)
    → tfidf_scorer.py       (keyword relevance score: 0.0–1.0)
    → source_weights.py     (multiply by source credibility: HN=0.9, ArXiv=1.0, GH=0.85)
    → signal_filter.py      (bucket: HIGH ≥0.65, MEDIUM 0.35–0.64, LOW 0.15–0.34, NOISE <0.15)
```

**`tfidf_scorer.py`**
- Corpus: all fetched titles + descriptions in this run (dynamic)
- Keyword boost list: configurable via env var `SIGNAL_KEYWORDS`
  (default: `"agent,multimodal,vision,safety,robotics,deployment,benchmark"`)
- Additional numeric boosts:
  - HN: `log(points+1) * 0.1` added to TF-IDF score
  - GitHub: `log(stars_today+1) * 0.12`
  - ArXiv: recency boost `1.0 - (age_hours / 48) * 0.2`
- Output: `float` score per item

**`deduplicator.py`**
- Vectorise titles with TF-IDF (same vectoriser, no re-fit)
- Cosine similarity threshold: 0.82
- Keep item with higher score; attach `duplicate_of` field to discarded item

**`signal_filter.py`**
- Assigns `SignalBucket` enum: `HIGH | MEDIUM | LOW | NOISE`
- Hard rule: NOISE items never reach agents (token budget protection)
- Passes top-20 scored items to agents (configurable via `MAX_AGENT_INPUT`)

**Output:** `list[ScoredItem]`, sorted by score descending.

---

### M3 — Agent Layer (`pipeline/agents/`)

**Responsibility:** Two adversarial LLM agents operating on pre-filtered signals.

**Token budget per run:** ~3,000 tokens total across both agents (Sonnet).

**`analyst_agent.py`**
- Input: top-N `ScoredItem` objects (HIGH + MEDIUM buckets)
- Task:
  1. Identify 3–5 key signals worth acting on
  2. Flag any claim it considers weak or low-confidence
  3. Draft preliminary "what this means" per signal
- Output: `AgentOutput(signals=[], weak_claims=[], reasoning=str)`
- Prompt constraint: "Be concise. Do not explain what you are doing. Output only the signals."

**`critic_agent.py`**
- Input: `AgentOutput` from analyst + original scored items (including MEDIUM/LOW)
- Task:
  1. Challenge each analyst signal — is it actually significant or recency bias?
  2. Check if any MEDIUM/LOW item contradicts a HIGH signal
  3. Flag contradictions explicitly
- Output: `AgentOutput(contested_signals=[], contradictions=[], endorsements=[])`
- Design note: Critic sees the full scored list so it can surface items the analyst missed

**`base_agent.py`** (shared)
- Builds prompt from template + data
- Enforces `max_tokens` per call
- Retry: 1 retry on rate limit, then fail fast
- Logs: full prompt + response to `TraceLogger`

---

### M4 — Synthesiser (`pipeline/synthesis/`)

**Responsibility:** Merge analyst + critic outputs into a final `RunResult`. No LLM call.

**Logic:**
```
For each analyst signal:
    if critic endorsed → confidence = HIGH
    if critic challenged but not contradicted → confidence = MEDIUM, note added
    if critic contradicted → moved to UNCERTAINTY section

For each critic contradiction:
    surfaced as ContradictionRecord(signal_a, signal_b, description)
```

**Output schema (`RunResult`):**
```python
@dataclass
class RunResult:
    run_id: str
    timestamp: datetime
    executive_summary: str          # 2-3 sentences, written by analyst
    key_signals: list[Signal]       # confidence-weighted, max 5
    ignored_signals: list[IgnoredItem]  # with discard reason
    uncertainties: list[ContradictionRecord]
    trace: list[TraceEntry]         # full observability log
    baseline_comparison: ComparisonResult | None
    token_usage: TokenUsage
```

---

### M5 — Baseline (`baseline/`)

**Responsibility:** Naive single-call summariser for evaluation comparison.

```python
async def run_baseline(raw_items: list[RawItem]) -> str:
    # Concatenate all titles + descriptions
    # Single Claude call: "Summarise what matters"
    # No scoring, no filtering, no agents
    ...
```

Used only in evaluation mode (`POST /run?eval=true`).

---

### M6 — Evaluation (`evaluation/`)

**Metrics:**

| Metric | Definition | Measurement |
|--------|-----------|-------------|
| Decision Clarity Score | Does the output tell you what to do? | Human eval 1–5 (prompted rubric) |
| Token Efficiency | Useful signals per 1000 tokens spent | `len(key_signals) / total_tokens * 1000` |
| Contradiction Detection Rate | % of seeded contradictions surfaced | Inject known conflicting items in fixture runs |

`compare.py` runs both systems on the same fixture data and emits a side-by-side JSON comparison.

---

### M7 — Observability (`observability/`)

Every stage emits a `TraceEntry`:

```python
@dataclass
class TraceEntry:
    stage: str          # "ingestion" | "scoring" | "analyst" | "critic" | "synthesis"
    agent: str | None
    inputs_summary: str # what was fed in (counts, not full data)
    outputs_summary: str
    decision: str       # key decision made at this stage
    tokens_used: int
    duration_ms: int
    timestamp: datetime
```

Traces stored in `RunResult.trace`. Surfaced in UI as collapsible `TracePanel`.

---

### M8 — API Layer (`api/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/run` | POST | Trigger full pipeline. Body: `{eval: bool}`. Returns `RunResult` |
| `/api/query` | POST | Follow-up Q&A. Body: `{run_id, question}`. Returns answer grounded in that run's signals |
| `/api/health` | GET | Returns `{status: ok, version}` |

**`/api/query` design:** Passes `RunResult.key_signals + uncertainties` as context to a single Claude call. Does not re-run the pipeline. Token-efficient.

---

### M9 — Frontend (`frontend/`)

Single-page UI, three states:

**State 1 — Idle:** Large "Run Analysis" button. Timestamp of last run.

**State 2 — Running:** Progress indicator showing current stage name (streamed via SSE or polling).

**State 3 — Results:**
```
┌─ Executive Summary ──────────────────────────────┐
│  2-3 sentence brief                               │
└───────────────────────────────────────────────────┘
┌─ Key Signals ─────────────────────────────────────┐
│  [HIGH] Signal title          Source · Confidence │
│  [MED]  Signal title          Source · Confidence │
└───────────────────────────────────────────────────┘
┌─ Uncertainty / Contradictions ───────────────────┐
│  ⚠ Signal A contradicts Signal B                 │
└───────────────────────────────────────────────────┘
┌─ Ignored Signals ─────────────────────────────────┐
│  Collapsed by default. Click to expand.           │
└───────────────────────────────────────────────────┘
┌─ How we got here (Trace) ─────────────────────────┐
│  Collapsible per-stage trace log                  │
└───────────────────────────────────────────────────┘
┌─ Ask a follow-up ─────────────────────────────────┐
│  [input field]  [Send]                            │
└───────────────────────────────────────────────────┘
```

---

## Data Flow (End-to-End)

```
POST /api/run
    │
    ▼
Orchestrator.run()
    ├── asyncio.gather(hn.fetch(), arxiv.fetch(), github.fetch())  → list[RawItem]
    ├── Deduplicator.run(items)                                    → list[RawItem] (deduped)
    ├── TFIDFScorer.score(items)                                   → list[ScoredItem]
    ├── SignalFilter.bucket(items)                                 → {HIGH, MEDIUM, LOW, NOISE}
    ├── AnalystAgent.run(HIGH + MEDIUM items)                      → AgentOutput
    ├── CriticAgent.run(analyst_output, all_scored_items)          → AgentOutput
    └── Synthesiser.merge(analyst_output, critic_output)           → RunResult
    │
    ▼
RunResult → JSON response
```

---

## Environment Variables

```bash
GEMINI_API_KEY=
MAX_AGENT_INPUT=20          # Max items passed to agents
SIGNAL_KEYWORDS=agent,multimodal,vision,safety,robotics
HN_TIMEOUT=8
ARXIV_MAX_AGE_HOURS=48
SCORE_THRESHOLD_HIGH=0.65
SCORE_THRESHOLD_MEDIUM=0.35
SCORE_THRESHOLD_LOW=0.15
```

---

## Key Trade-offs

| Decision | Alternative | Reason chosen |
|----------|------------|---------------|
| TF-IDF scorer (not LLM) | LLM-based relevance | Deterministic, zero tokens, fast, auditable |
| 2 agents (not 3+) | More specialised agents | Minimal multi-agent overhead; Critic covers contradiction without extra calls |
| Analyst sees only HIGH+MED | Analyst sees all | Token budget; noise items already handled by scorer |
| Critic sees full scored list | Critic sees only analyst output | Ensures Critic can surface items analyst missed |
| Single `/query` call (no re-run) | Re-run pipeline per question | Latency and token efficiency |
| Next.js frontend | React SPA / plain HTML | Vercel-native; easier API routing |