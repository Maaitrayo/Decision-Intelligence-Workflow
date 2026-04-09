# Decision Intelligence Workflow

Signal vs Noise is a decision-intelligence system that ingests a small set of external AI and tech signals, separates meaningful developments from noise, surfaces uncertainty instead of forcing false certainty, and supports saved follow-up Q&A over prior runs.

## Current Status

Implemented today:

- Multi-source ingestion from Hacker News, ArXiv RSS, and GitHub Trending
- Deterministic scoring, bucketing, deduplication, and ignored-signal handling
- Gemini-backed Analyst and Critic agents
- Structured synthesis into a saved `RunResult`
- Run persistence, reopen flow, and stored follow-up chat sessions
- Baseline single-call summariser plus first-pass evaluation metrics
- Live pipeline progress endpoint for UI polling
- Plain HTML/CSS/JS frontend served by FastAPI with:
  - run trigger
  - structured result display
  - run history sidebar
  - reopen flow
  - persisted follow-up chat

Still pending for full assignment completion:

- Vercel deployment
- Fallback hardening for ingestion failures
- Automated tests across ingestion, scoring, synthesis, query, and end-to-end flows
- Persistence validation across restarts
- Final README sample-run section polish
- Walkthrough video

## Architecture Overview

The system is organized into a staged workflow:

1. Ingestion
   Pulls signals from three sources:
   - Hacker News via scraping
   - ArXiv via RSS
   - GitHub Trending via scraping

2. Deterministic Scoring
   Applies a non-LLM scoring pipeline:
   - source credibility weighting
   - keyword-based TF-IDF-style relevance scoring
   - metadata boosts
   - duplicate filtering
   - bucket assignment into `high`, `medium`, `low`, `noise`

3. Agent Layer
   - Analyst agent identifies key signals and weak claims
   - Critic agent challenges the analyst, surfaces contradictions, and flags contested signals

4. Synthesis
   Merges agent outputs into a final `RunResult` with:
   - executive summary
   - key signals
   - ignored signals
   - uncertainties
   - trace entries
   - token usage

5. Persistence and Query
   - saves each run in SQLite through SQLAlchemy
   - supports reopening saved runs
   - stores follow-up chat sessions and messages
   - answers grounded follow-up queries using saved run context

6. Baseline and Evaluation
   - naive baseline summariser treats all raw inputs equally in a single Gemini call
   - evaluation layer computes first-pass comparison metrics

7. Frontend
   - plain HTML/CSS/JS UI served by FastAPI
   - session sidebar
   - structured analysis workspace
   - trace and uncertainty views
   - follow-up chat interface

## Architecture Diagram

```text
                   +-----------------------------+
                   | Trigger                     |
                   | UI button / POST /api/runs |
                   +-------------+---------------+
                                 |
                                 v
                   +-------------+---------------+
                   | Ingestion Service           |
                   | HN scrape + ArXiv RSS +    |
                   | GitHub Trending scrape     |
                   +-------------+---------------+
                                 |
                                 v
                   +-------------+---------------+
                   | Deterministic Scoring       |
                   | weighting + TFIDF-style    |
                   | score + dedupe + buckets   |
                   +-------------+---------------+
                                 |
                     +-----------+-----------+
                     |                       |
                     v                       v
        +------------+---------+   +---------+------------+
        | Analyst Agent        |   | Critic Agent         |
        | identify signals     |   | challenge / contest  |
        | weak claims          |   | contradictions       |
        +------------+---------+   +---------+------------+
                     \                       /
                      \                     /
                       v                   v
                   +---+-------------------+---+
                   | Synthesiser               |
                   | build final RunResult     |
                   +---+-------------------+---+
                       |                   |
                       |                   +----------------------+
                       v                                          |
             +---------+------------+                             |
             | Persistence Layer    |                             |
             | runs + trace + chat  |<--------------------+       |
             +---------+------------+                     |       |
                       |                                  |       |
                       v                                  |       |
             +---------+------------+                     |       |
             | UI / Reopen / Query  |---------------------+       |
             | structured analysis  |   follow-up Q&A             |
             +----------------------+                             |
                                                                  |
             +----------------------------------------------------+
             | Baseline + Evaluation (optional eval mode)         |
             | naive single-call summary + comparison metrics     |
             +----------------------------------------------------+
```

## Data Flow

```text
POST /api/runs
  -> IngestionService.fetch_all()
  -> ScoringService.score()
  -> AnalystAgent.run()
  -> CriticAgent.run()
  -> Synthesiser.merge()
  -> RunRepository.save_run()
  -> JSON response + saved run

GET /api/runs
  -> list saved runs

GET /api/runs/{run_id}
  -> load full saved RunResult

POST /api/query
  -> load saved run
  -> create/resume chat session
  -> store user message
  -> Gemini answer over stored run context
  -> store assistant message

GET /api/query/{run_id}
  -> load latest stored chat session for that run

GET /api/progress
  -> return current orchestrator stage
```

## Main Flow

`POST /api/runs`
- runs ingestion
- scores and filters signals
- runs Analyst and Critic
- synthesizes a final result
- persists the result

`GET /api/runs`
- lists saved runs

`GET /api/runs/{run_id}`
- reopens a saved run

`POST /api/query`
- answers follow-up questions using stored run context and saved chat history

`GET /api/query/{run_id}`
- loads the latest stored chat session for a run

`GET /api/progress`
- exposes current pipeline stage for UI polling

## Trade-offs and Decisions

- Two-agent design instead of a larger agent graph
  Keeps the workflow understandable and cheaper while still supporting adversarial review.

- Deterministic filtering before LLM calls
  Reduces token usage and avoids treating all inputs equally.

- Plain HTML/CSS/JS frontend instead of Next.js
  Keeps the UI simple to host from the FastAPI app and reduces setup overhead.

- SQLite-first persistence
  Good enough for local development and assignment demonstration; can be swapped later.

- First-pass evaluation metrics are heuristic
  Useful for comparison flow now, but still need hardening for stronger assignment-quality claims.

- Progress is exposed through polling rather than streaming
  Simpler to integrate quickly, but less responsive than SSE or websockets.

## Repository Layout

- `api/` FastAPI app and routes
- `pipeline/` ingestion, scoring, agents, synthesis, persistence, progress tracking, orchestration
- `baseline/` naive baseline summariser
- `evaluation/` comparison and metrics
- `frontend/` plain HTML/CSS/JS UI
- `scripts/` local scripts for pipeline and query testing
- `docs/` planning, assignment notes, and run artifacts

## Running Locally

Install dependencies and make sure `GEMINI_API_KEY` is available in `.env` or the environment.

Run the API:

```powershell
uvicorn api.index:app --reload
```

Open:

```text
http://127.0.0.1:8000/
```

Useful scripts:

```powershell
python scripts\run_pipeline.py
python scripts\test_query_flow.py
python scripts\test_hn_ingestor.py
python scripts\test_arxiv_ingestor.py
python scripts\test_github_ingestor.py
```

## Assignment Checklist Alignment

Implemented:

- multiple heterogeneous sources
- web scraping
- deterministic non-LLM filtering
- multi-agent workflow
- signal vs noise handling
- uncertainty and contradiction surfacing
- traceability
- manual trigger via UI and API
- saved follow-up Q&A
- baseline comparison against a simpler system
- first-pass evaluation metrics

Still outstanding:

- deployment on Vercel
- fallback hardening
- automated test coverage
- persistence validation across restarts
- sample runs section with logs and traces
- final submission polish
- walkthrough video

## Sample Runs and Walkthrough Assets

Current repo artifacts already available:

- `assets/result1.json`
- UI screenshots under `assets/images/` if present in your local workspace

### Sample Run 1

Source artifact:

- `assets/result1.json`

Run metadata:

- Run ID: `69e8bdbe-173d-4757-95ef-dc70a2aeb67d`
- Timestamp: `2026-04-08T20:20:18.347575`
- Raw items ingested: `550`
- Total tokens used: `53,656`

Executive summary:

> Top signals centered on multi-agent robotics, efficient VLA systems, and emerging safety vulnerabilities. The critic surfaced 3 uncertainties that should block overconfident action.

Top signals:

1. Multi-agent systems converging with embodied robotics
   - Evidence cluster spanned both ArXiv and GitHub.
   - The signal was driven by projects and papers around coordinated agents, robotics simulation, and embodied environments.

2. Efficiency-first shift in VLA models
   - The run surfaced a push toward lighter, faster, deployment-oriented multimodal systems.
   - The emphasis was on inference efficiency and edge deployment rather than only scaling raw model size.

3. Emotional and sub-symbolic safety vulnerabilities
   - The run identified safety weaknesses in current alignment methods.
   - The critic preserved this as a major concern rather than treating alignment as solved.

4. Agent-native personalized learning
   - The system flagged a trend toward continuous tutor/partner style products.
   - This signal was later challenged by contradiction evidence around “surface compliance” and weak genuine reasoning.

Examples of ignored signals:

- `MARL-GPT: Foundation Model for Multi-Agent Reinforcement Learning`
- `COSMO-Agent: Tool-Augmented Agent for Closed-loop Optimization,Simulation,and Modeling Orchestration`
- `ClawsBench: Evaluating Capability and Safety of LLM Productivity Agents in Simulated Workspaces`

Why they were ignored:

- They were not necessarily unimportant in absolute terms.
- They fell outside the top agent input limit after deterministic scoring and ranking.

Uncertainties surfaced:

1. Efficiency vs reasoning depth
   - The run surfaced a conflict between edge-efficient VLA design and the growing need for larger inference-time reasoning budgets.

2. Robotics optimism vs grounding gap
   - The critic challenged whether reasoning-heavy multimodal systems are actually grounded enough for reliable embodied execution.

3. Personalized learning vs surface compliance
   - The critic found evidence that educational agent optimism may be undermined by shallow or decorative reasoning behavior.

Trace snapshot:

| Stage | Duration | Tokens | Key output |
|------|---------:|-------:|-----------|
| Ingestion | 1,492 ms | 0 | `raw_items=550` |
| Scoring | 31,555 ms | 0 | `scored_items=550` |
| Analyst | 20,605 ms | 3,651 | `signals=4` |
| Critic | 14,595 ms | 50,005 | `contradictions=3` |
| Synthesis | 1 ms | 0 | `key_signals=4` |

Follow-up Q&A sample:

- Question: `Based on this run, what are the top risks and uncertainties to watch?`
- The saved follow-up answer focused on:
  - the deployment paradox between efficiency and reasoning depth
  - alignment gaps in multimodal systems
  - the risk of surface compliance in personalized educational agents
