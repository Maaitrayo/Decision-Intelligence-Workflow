## Decision Intelligence Workflow - Idea

**Domain: AI/Tech Industry Pulse Tracker**

A system that monitors the AI/tech landscape and tells you: *"What actually matters right now, what's hype, and what action (if any) should you take?"*

Every pipeline run is saved so you can reopen previous analyses, inspect how each result was produced, and continue follow-up Q&A on top of stored context instead of losing everything after one session.

---

### Data Sources (3)

| # | Source | Method | Why |
|---|--------|---------|-----|
| 1 | Hacker News (`news.ycombinator.com/news`) | **Web scraping** | High signal-to-noise ratio for tech; deterministic ranking metadata available |
| 2 | ArXiv RSS (`cs.CV / cs.AI`) | **RSS feed** | Structured, low-latency, academic signal |
| 3 | GitHub Trending API (or scrape) | **Scraping / API** | Reveals what engineers are *actually building*, not just talking about |

Justified discard: Twitter/X, Reddit - too noisy, rate-limited, require auth.

---

### Architecture

```
[Trigger: Button / POST /run]
        |
  +------+------+
  |  Ingestor   |  <- Scraper + RSS parser + GitHub fetch (async, parallel)
  +------+------+
         |
  +------+---------------+
  | Deterministic Filter |  <- Non-LLM: TF-IDF / keyword scoring + source
  |   (Signal Scorer)    |     credibility weights -> rank & bucket items
  +------+---------------+
         |
  +------+---------------+
  |   Analyst Agent      |  <- LLM: summarises top signals, flags contradictions,
  |                      |     identifies weak or uncertain claims
  +------+---------------+
         |
  +------+---------------+
  |   Critic Agent       |  <- LLM: challenges the analyst's conclusions,
  |                      |     surfaces counter-signals from discarded items
  +------+---------------+
         |
  +------+---------------+
  |  Synthesiser Agent   |  <- Produces final structured output with confidence
  +------+---------------+
         |
  +------+---------------+
  |   Persistence Layer  |  <- Saves runs, signals, trace logs, and chat history
  |      (Database)      |     so past analyses can be reopened and queried
  +------+---------------+
         |
   [UI Output + Run History + Q&A]
```

**Two agents** (Analyst + Critic) is the minimum viable multi-agent design - avoids over-engineering while satisfying the adversarial and uncertainty requirement.

---

### Key Design Decisions

**Deterministic step:** TF-IDF scoring + source credibility weighting assigns a numeric signal score *before* any LLM is invoked. This controls token budget by only passing top-N items to agents.

**Uncertainty handling:** If Analyst and Critic disagree on a signal's importance, the Synthesiser surfaces it as a *contested signal* rather than forcing a conclusion.

**Observability:** Each stage emits a structured trace log (JSON) visible in the UI as a collapsible "How we got here" panel.

**Persistence:** Every run is written to a database with ranked signals, ignored items, uncertainty records, token usage, and full trace output. This makes the system auditable and lets users reopen previous runs without repeating ingestion or analysis.

**Chat continuity:** Follow-up Q&A is stored per run or chat session. A user can return later, reopen a saved result, and continue asking grounded questions against the original run plus prior conversation history.

**Baseline comparison:** A naive "summarise all inputs equally" single-prompt call. Metrics: *Decision Clarity Score* (human eval, 1-5), *Token Efficiency* (tokens/insight), *Contradiction Detection Rate*.

---

### Output Structure

```
Executive Summary       -> 3-sentence actionable brief
Key Signals (Top 3-5)   -> with source + confidence score
Ignored Signals         -> with reason (low score / off-topic / duplicate)
Uncertainty/Conflicts   -> contested claims, surfaced explicitly
Traceability Panel      -> per-agent reasoning chain
Run History             -> saved analyses that can be reopened later
Follow-up Q&A           -> chat interface over the run's context with stored history
```

---

### Stack

- **Backend:** Python + FastAPI (Vercel serverless via `@vercel/python`)
- **Scraping:** `httpx` + `BeautifulSoup`
- **RSS:** `feedparser`
- **LLM:** Gemini API (Fee tier)
- **Database:** relational DB layer for runs, trace logs, signals, and chat history
- **Frontend:** Minimal Next.js or plain HTML served from FastAPI

---

**Core bet:** Most "decision intelligence" systems drown you in summaries. This one defaults to *silence on noise* and speaks only when signal crosses a threshold - the Critic agent is what makes this defensible. Persistence makes the system useful across sessions because each decision trail remains available for review, reopening, and follow-up.
