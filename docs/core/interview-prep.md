# Decision Intelligence Workflow Interview Prep

This guide is written as if I were the interviewer for this assignment. It focuses on the questions most likely to come up in a technical discussion based on the current project in `DLW-docs/core` and the implemented codebase.

## 1. Start With Your 60-Second Explanation

Be able to say this clearly:

> This project is a decision-intelligence workflow for AI and tech signals. It ingests three heterogeneous sources, runs a deterministic scoring and filtering stage before any LLM call, uses an Analyst agent to extract important signals, uses a Critic agent to challenge those signals and surface contradictions, then synthesises a structured result with uncertainty, traceability, persistence, and follow-up Q&A over saved runs.

If they ask "what is the core value?", say:

> The core value is not summarising everything. It is filtering noise first, making uncertainty explicit, and preserving the full decision trail so the result can be reopened and queried later.

## 2. Questions You Are Very Likely To Be Asked

### Q1. What problem were you solving?

What they are testing:
- Whether you understand the product goal, not just the code.

Strong answer points:
- People get flooded with AI/tech updates.
- Most systems over-summarise raw inputs and hide uncertainty.
- This workflow tries to answer: what matters, what was ignored, where the system is uncertain, and what can be revisited later.

### Q2. Why did you choose these three sources?

Strong answer points:
- Hacker News gives high-signal engineering discourse plus ranking metadata.
- ArXiv RSS gives structured research input without scraping complexity.
- GitHub Trending reflects what engineers are actively building.
- Together they give social signal, research signal, and builder signal.
- I intentionally kept it to 3 sources to control complexity and satisfy the assignment constraint.

### Q3. Where is the deterministic non-LLM step, and why is it important?

Strong answer points:
- The deterministic stage is in scoring: keyword TF-IDF-style relevance, source weighting, metadata boosts, deduplication, and bucket filtering.
- It matters because it reduces token cost, improves auditability, and prevents low-value items from reaching agents.
- It also makes the pipeline more defensible because the model is not deciding relevance from scratch.

Code anchors:
- `pipeline/scoring/tfidf_scorer.py`
- `pipeline/scoring/deduplicator.py`
- `pipeline/scoring/signal_filter.py`

### Q4. Why did you use multiple agents instead of one prompt?

Strong answer points:
- One prompt tends to collapse into a single narrative and hide uncertainty.
- The Analyst extracts important signals.
- The Critic challenges those signals, checks for missed counter-evidence, and explicitly surfaces contradictions.
- This is the smallest useful multi-agent design. More agents would add cost and orchestration overhead without clear assignment benefit.

### Q5. What exactly does the Critic add?

Strong answer points:
- It prevents false confidence.
- It sees the analyst output plus the scored item set.
- It can contest importance, surface contradictions, and move uncertain claims out of the final "clean" narrative.
- This is the main mechanism that turns the system from a summariser into a decision-support workflow.

### Q6. How does the end-to-end flow work?

Give it in this order:
1. `POST /api/runs` triggers the orchestrator.
2. Ingestion fetches Hacker News, ArXiv, and GitHub Trending.
3. Scoring ranks and buckets items.
4. Analyst runs on ranked items.
5. Critic challenges the analyst output.
6. Synthesiser builds `RunResult`.
7. Result is saved to SQLite through SQLAlchemy.
8. UI can reopen the run and ask follow-up questions without recomputing.

Code anchors:
- `api/routes/run.py`
- `pipeline/orchestrator.py`
- `pipeline/repository.py`

### Q7. How do you handle persistence and why did you include it?

Strong answer points:
- Every run is saved with summary, key signals, ignored signals, uncertainties, trace entries, token usage, and chat sessions.
- Persistence makes the analysis auditable and lets the user reopen prior runs without rerunning ingestion or agents.
- It also enables grounded follow-up Q&A on saved state.

Code anchors:
- `pipeline/db_models.py`
- `pipeline/repository.py`
- `api/routes/query.py`

### Q8. How does follow-up Q&A work?

Strong answer points:
- `/api/query` loads a saved run from the database.
- It creates or resumes a chat session tied to that run.
- It sends saved run context plus recent chat history to Gemini.
- It does not rerun ingestion, scoring, or agents.
- This is cheaper, faster, and grounded in the saved result.

### Q9. Why did you choose SQLite and plain HTML/JS?

Strong answer points:
- SQLite is enough for local persistence and assignment scope.
- SQLAlchemy gives a migration path to Postgres later.
- Plain HTML/CSS/JS reduced frontend setup overhead and let me focus on pipeline behavior, persistence, and observability.
- This was a pragmatic trade-off, not an ideological one.

### Q10. How do you expose observability?

Strong answer points:
- The orchestrator creates trace entries for ingestion, scoring, analyst, critic, and synthesis.
- Each trace records stage, inputs summary, outputs summary, decision, tokens, duration, and timestamp.
- The frontend shows this as a trace panel, and progress is exposed through `/api/progress`.

Code anchors:
- `pipeline/orchestrator.py`
- `pipeline/models/run_result.py`
- `api/routes/progress.py`

### Q11. How did you evaluate the system?

Strong answer points:
- I added a naive baseline that treats all inputs equally in a single LLM call.
- I compare the pipeline against that baseline.
- Current metrics include token efficiency, contradiction count, and a decision-clarity proxy.
- The evaluation is useful, but I would describe it as first-pass, not final-grade rigorous.

Code anchors:
- `baseline/naive_summariser.py`
- `evaluation/compare.py`
- `evaluation/metrics.py`

### Q12. What would you improve next?

Strong answer points:
- Add fixture-backed ingestion fallback behavior.
- Add proper unit and integration tests around scoring, synthesis, and `/api/query`.
- Improve evaluation quality beyond heuristic metrics.
- Move to Postgres if deployment scale or concurrency increases.
- Tighten token usage, especially around the critic and query flow.

## 3. Questions That Probe Technical Depth

### Q13. Why score before deduplication in the implemented code?

Good answer:
- In the current implementation, items are scored first so duplicates can be resolved by keeping the higher-scoring item.
- That gives the deduplicator a ranking signal.
- A refinement would be to separate pure textual duplicate clustering from final ranking if we wanted a cleaner design.

### Q14. How does deduplication actually work here?

Be precise:
- The current implementation uses normalized titles, token-based candidate pruning, and `SequenceMatcher` similarity with a threshold.
- That is simpler than cosine similarity over TF-IDF vectors and cheaper to implement quickly.
- It is good enough for assignment scope but I would call it heuristic, not robust semantic deduplication.

Important honesty point:
- The planning docs mention TF-IDF/cosine-based near-duplicate detection, but the implemented code uses `SequenceMatcher`.
- If asked, do not hide that difference.

### Q15. How are confidence levels assigned?

Good answer:
- Confidence is adjusted in synthesis.
- Analyst output provides initial candidate signals.
- If the Critic endorses a signal, confidence becomes high.
- If the Critic contests it, confidence is reduced to medium.
- Contradictions are surfaced separately as uncertainties.

Code anchor:
- `pipeline/synthesis/synthesiser.py`

### Q16. What are the current failure modes?

Mention these directly:
- External sources can fail or change markup.
- The ingestion fallback behavior is still a known gap.
- LLM output may fail JSON parsing.
- Query answers depend on saved run quality; they do not independently re-verify sources.
- Current evaluation metrics are still heuristic.

### Q17. What are the biggest scalability limits?

Strong answer points:
- SQLite is fine for local/demo use but limited for concurrent production workloads.
- Query and agent prompts can become large if run context grows.
- Scraping-based sources are brittle.
- The current progress tracker is simple polling, not event streaming.

### Q18. Why not let the LLM do relevance scoring too?

Strong answer:
- Because that would be more expensive, less reproducible, and harder to debug.
- A deterministic stage gives predictable filtering and preserves assignment-required non-LLM logic.
- The LLM should spend tokens on interpretation and critique, not basic triage.

## 4. Questions About Design Trade-offs

### Q19. Why not use more than two agents?

Good answer:
- Two agents already provide adversarial review.
- More agents would increase latency, token cost, and orchestration complexity.
- For an assignment, I wanted the minimal structure that still demonstrates multi-agent reasoning and contradiction handling.

### Q20. Why is synthesis deterministic instead of another LLM call?

Good answer:
- It keeps the final merge auditable and cheap.
- Once Analyst and Critic outputs exist, merging confidence and contradictions is deterministic business logic.
- A final LLM layer could reintroduce hallucinated framing.

### Q21. Why does `/api/query` not rerun the full pipeline?

Good answer:
- Because the query is about a saved analysis, not about fresh ingestion.
- Recomputing would be slower, costlier, and could produce drift relative to the original run.
- Using persisted context preserves session continuity.

## 5. Questions You Should Answer Carefully

### Q22. What parts are incomplete or less production-ready?

Say this plainly:
- Tests are not yet complete for the most important paths.
- Fallback handling for source failures is still incomplete.
- Evaluation is still early and partly proxy-based.
- SQLite is a local-first choice, not the final production database.
- Some planning docs describe ideal behavior that is only partially implemented.

### Q23. What is one implementation mismatch between plan and code?

Good examples:
- Planned deduplication described TF-IDF/cosine similarity, but implemented deduplication uses `SequenceMatcher`.
- Planned frontend direction mentioned Next.js in docs, but actual implementation is plain HTML/CSS/JS.
- Query flow currently stores chat messages but does not appear to persist query token usage back into the run totals.

This is a strong interview answer because it shows you actually know your own system.

## 6. Fast Mock Interview Round

Practice answering these out loud in 30-60 seconds each:

1. Why is this a decision-intelligence system and not just a news summariser?
2. What does the deterministic stage do, exactly?
3. Why is the Critic necessary?
4. How do you surface uncertainty to the user?
5. Why persist ignored signals?
6. How do follow-up queries stay grounded?
7. What are the weakest parts of the current implementation?
8. If I remove the Critic, what gets worse?
9. If you had one more day, what would you improve first?
10. If you had to deploy this for real, what would you change in the storage and observability layers?

## 7. Best Way To Present Yourself In The Interview

Do:
- Explain the workflow stage by stage.
- Be explicit about what is deterministic vs LLM-driven.
- Be honest about assignment trade-offs and unfinished hardening.
- Show that persistence and uncertainty were deliberate design choices, not extras.

Do not:
- Claim the evaluation is fully rigorous.
- Pretend the scraper-based sources are production-stable.
- Hide differences between the original plan and the current implementation.

## 8. Final Closing Answer You Can Reuse

If they ask for a closing summary, say:

> The strongest parts of this project are the deterministic signal filtering, the adversarial Analyst-Critic pattern, and the persistence layer that makes results auditable and reusable. The main gaps are test coverage, fallback hardening, and stronger evaluation. So I would position it as a solid assignment-quality system with clear architecture and good reasoning about trade-offs, rather than as a fully production-hardened platform.
