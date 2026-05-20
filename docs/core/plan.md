# Decision Intelligence Workflow - Implementation Plan

This plan translates `docs/idea.md` and `docs/workflow.md` into delivery phases. It treats persistent storage as core scope so every run, trace, and follow-up conversation can be reopened and viewed later.

## Build Goals

- Ingest high-signal AI and tech inputs from Hacker News, ArXiv, and GitHub Trending.
- Rank and filter items deterministically before invoking any LLM.
- Run Analyst and Critic agents on the filtered set and synthesise a structured result.
- Persist runs, signals, ignored items, uncertainties, traces, and chat history in a database.
- Let the user reopen previous runs and continue follow-up Q&A without rerunning the full pipeline.

## Phase 1 - Foundation and Project Setup
Status: Completed

### Deliverables

- Repository scaffold aligned with the architecture in `docs/workflow.md`
- FastAPI entrypoint and base route structure
- Shared config, environment handling, and base models
- Local development setup for backend, plain HTML/CSS/JS frontend, and tests

### Todo

- [x] Create backend app structure under `api/`
- [x] Create pipeline package skeleton under `pipeline/`
- [x] Create shared models for raw items, scored items, agent outputs, and run results
- [x] Add config loading for API keys, thresholds, and timeouts
- [x] Add backend runtime dependencies
- [x] Add base frontend app scaffold

## Phase 2 - Ingestion Layer
Status: In progress

### Deliverables

- Async ingestion for Hacker News, ArXiv RSS, and GitHub Trending
- Normalised `RawItem` output for all sources
- Fallback behavior on source failures

### Todo

- [x] Implement `BaseIngestor`
- [x] Implement Hacker News scraper
- [x] Implement ArXiv RSS parser
- [x] Implement GitHub Trending fetcher
- [x] Run all ingestors in parallel with timeout controls
- [ ] Add fixture-backed fallback behavior and ingestion tests

## Phase 3 - Deterministic Scoring and Filtering
Status: In progress

### Deliverables

- Deduplication, TF-IDF scoring, source weighting, and bucket assignment
- Top-N filtering to protect token budget
- Ignored item reasoning for auditability

### Todo

- [x] Implement duplicate detection
- [x] Implement TF-IDF relevance scoring
- [x] Apply source credibility weighting and metadata boosts
- [x] Bucket items into HIGH, MEDIUM, LOW, and NOISE
- [x] Keep ignored item reasons for storage and UI display
- [ ] Add unit tests for scorer, deduplicator, and filter logic

## Phase 4 - Agent and Synthesis Layer
Status: In progress

### Deliverables

- Analyst and Critic agent execution over filtered items
- Structured synthesis into a final `RunResult`
- Confidence and uncertainty handling

### Todo

- [x] Implement shared agent client and prompt builder
- [x] Implement Analyst agent
- [x] Implement Critic agent
- [x] Implement synthesiser logic without a final LLM call
- [x] Track token usage and per-stage timing
- [ ] Add tests for synthesis and contradiction handling

## Phase 5 - Persistence Layer and Reopenable History
Status: In progress

### Deliverables

- Database layer for runs, outputs, traces, and chat history
- Read and write APIs that allow old runs to be reopened
- Stable retrieval of prior results across restarts

### Todo

- [x] Choose relational database strategy and define schema
- [x] Add persistence models or repository layer
- [x] Save completed `RunResult` data after each run
- [x] Save scored items, ignored items, uncertainties, and trace entries
- [x] Add API support to fetch run history and a single saved run
- [x] Ensure previous processes can be reopened and viewed without recomputation

## Phase 6 - Follow-up Q&A with Stored Chat History
Status: In progress

### Deliverables

- Query flow grounded in stored run context
- Chat sessions and messages persisted in the database
- Resume previous conversations tied to a run

### Todo

- [x] Define chat session and chat message schema
- [x] Persist each user question and assistant answer
- [x] Load relevant run context and prior chat turns for `/api/query`
- [x] Support resuming a chat for an older run
- [x] Prevent `/api/query` from rerunning ingestion or scoring
- [ ] Add integration tests for persisted Q&A history

## Phase 7 - Observability, Evaluation, and Progress Tracking
Status: In progress

### Deliverables

- Structured trace logging per stage
- Baseline evaluation flow
- Visible stage progress in the UI and implementation tracker

### Todo

- [ ] Implement trace logger and trace persistence
- [x] Expose stage progress for frontend polling or streaming
- [x] Implement baseline summariser
- [x] Implement evaluation metrics and comparison mode
- [ ] Validate token efficiency and contradiction detection reporting
- [ ] Keep this plan updated with phase and todo status during implementation

## Phase 8 - Frontend Experience
Status: In progress

### Deliverables

- Plain HTML/CSS/JS analysis trigger UI
- Results view with executive summary, signals, uncertainties, ignored items, and trace
- Run history list and reopen flow
- Follow-up chat UI backed by stored messages

### Todo

- [x] Build initial run screen
- [x] Build running state with current pipeline stage
- [x] Build results screen for saved runs
- [x] Add run history browser
- [x] Add reopen flow for previous analyses
- [x] Add persisted chat UI for follow-up Q&A

## Phase 9 - Final Hardening
Status: Pending

### Deliverables

- End-to-end stability across ingestion, scoring, persistence, and chat
- Test coverage for core behavior
- Deployment-ready configuration

### Todo

- [ ] Add end-to-end tests for `POST /api/run` and `POST /api/query`
- [ ] Validate persistence across app restarts
- [ ] Review failure handling for partial source outages
- [ ] Review DB migration and seed strategy
- [ ] Review deployment configuration and secrets handling
- [ ] Close remaining gaps in docs and implementation tracker

## Execution Order

1. Phase 1
2. Phase 2
3. Phase 3
4. Phase 4
5. Phase 5
6. Phase 6
7. Phase 7
8. Phase 8
9. Phase 9

## Progress Update Rule

- Keep phase `Status` current as work moves forward.
- Mark todos as done as each implementation step lands.
- After every file change, stop for review and state what was implemented and what comes next.

## Current Progress Snapshot

- Implemented FastAPI app entrypoint and health route in `api/index.py`
- Implemented shared settings in `pipeline/config.py`
- Implemented shared pipeline models in `pipeline/models/`
- Implemented pipeline package scaffold and orchestrator contract
- Implemented DB engine/session setup, schema models, and DB initialization
- Implemented run history API endpoints for listing and fetching saved runs
- Implemented all three ingestion sources and parallel ingestion service
- Implemented deterministic scoring, filtering, and first-pass deduplication
- Implemented Gemini-backed Analyst and Critic agents, synthesis, and end-to-end orchestration
- Implemented pipeline execution and full saved-run retrieval through the API
- Implemented run trace and token usage capture across pipeline stages
- Implemented persisted follow-up Q&A with stored run context and resumable chat sessions
- Implemented the initial plain HTML/CSS/JS frontend scaffold and run screen
- Implemented saved-run browsing and reopen flow in the plain frontend
- Implemented a structured analysis workspace UI with collapsible session sidebar and follow-up chat
- Implemented baseline comparison and first-pass evaluation metrics
- Implemented live progress polling from the backend into the frontend
- Implemented README architecture, trade-offs, data flow, and first curated sample run

## Assignment Completion Checklist

### Core Assignment Requirements

- [x] Ingest and process multiple external inputs
- [x] Use 3 or fewer heterogeneous sources
- [x] Include web scraping as an ingestion method
- [x] Include at least one additional non-scraped source type
- [x] Use multiple agents
- [x] Include at least one deterministic non-LLM step
- [x] Prioritise meaningful signals and filter noise
- [x] Surface ignored signals and why they were discarded
- [x] Surface uncertainty, contradictions, and weak signals
- [x] Support follow-up queries or drill-down
- [x] Provide traceability into how conclusions were formed
- [x] Provide a manual trigger via UI and API

### Still Required For Assignment Completion

- [ ] Deploy the app on Vercel
- [x] Implement baseline comparison against a simpler system
- [x] Implement 2-3 meaningful evaluation metrics
- [x] Add live/progressive observability in the UI
- [ ] Add fallback behavior for ingestion failures
- [ ] Add ingestion, scoring, synthesis, and query integration tests
- [ ] Add end-to-end tests for `POST /api/run` and `POST /api/query`
- [ ] Validate persistence across app restarts
- [x] Create README with architecture overview
- [x] Document trade-offs and design decisions in README
- [ ] Include at least 2 sample runs with logs/traces
- [ ] Prepare walkthrough video
