Demo Script

“Hi, this is my submission for the Decision Intelligence Workflow
assignment.

This system is designed to solve a specific problem: when a large number
of AI and tech updates arrive from mixed sources, most of them are noisy,
repetitive, or not decision-relevant. Instead of treating all inputs
equally, this workflow ingests signals, filters them deterministically,
runs an Analyst and a Critic agent, and produces a structured,
uncertainty-aware result that can be reopened and queried later.

I’ll start with the architecture.

The system ingests data from three heterogeneous sources: Hacker News,
ArXiv RSS, and GitHub Trending. That gives us a mix of scraped web
content, feed-based academic content, and repository-level trend signals.

After ingestion, the system runs a deterministic scoring layer. This is
important because I did not want the LLM to see everything blindly. The
scoring stage applies source weighting, keyword-based relevance scoring,
metadata boosts, duplicate handling, and then buckets items into high,
medium, low, or noise. This is the first signal-versus-noise gate.

Then the agent layer begins.

The Analyst agent looks at the filtered candidate set and proposes the
top signals. The Critic agent then challenges those signals, looks for
contradictions, and surfaces uncertainty. The final synthesis step merges
those outputs into a structured result with an executive summary, key
signals, ignored signals, uncertainties, trace entries, and token usage.

All of this is persisted in SQLite, so every run is saved and can be
reopened later. Follow-up chat is also persisted, so the system supports
stored conversational exploration over previous analyses instead of
rerunning everything from scratch.

Now I’ll show the product.

Here on the main UI, I can click ‘Run Analysis’. While the pipeline
executes, the interface shows the current stage, such as ingestion,
scoring, analyst, critic, synthesis, and optional evaluation. This
progress is driven by a backend progress endpoint.

Once the run completes, the result is shown in a structured layout
instead of raw JSON. At the top is the executive summary. Then I have the
key signals the system believes are most decision-relevant. I also show
ignored signals, so the system is not a black box about what got filtered
out. Then I show uncertainties and contradictions surfaced by the Critic.
Finally, I show the trace, including stage timing and token usage, so the
workflow is inspectable.

On the left side, I can reopen previous saved runs. That demonstrates
persistence. If I select an older run, I get the saved result immediately
without recomputation.

Below that is the follow-up chat. I can ask questions against the saved
run context, for example: ‘What are the top risks here?’ or ‘What should
I monitor next week?’ These conversations are saved in the database and
reloaded when I reopen the run.

Next, I want to show the evaluation setup, because the assignment asked
for comparison against a simpler baseline.

The baseline is a naive single-call summarizer. It takes the same raw
corpus and asks Gemini for one simple summary, without deterministic
filtering, without Analyst/Critic separation, and without contradiction
handling.

My full system is compared against that baseline using lightweight
project metrics:
decision clarity, token efficiency, and contradiction surfacing.

I’ve already saved evaluation outputs as JSON artifacts. These show that
the full workflow consistently produces structured, critique-aware
outputs, while the baseline is just a flat summary. I describe this
honestly in the README: these are useful project metrics, but not a
formal benchmark.

To summarize the key design choices:
I used deterministic preprocessing before LLM calls to reduce noise.
I used a two-agent design to keep the workflow interpretable and
affordable.
I persisted runs and chats so the system supports iterative analysis.
And I built observability into the trace and progress flow so the user
can inspect what happened.

What’s still pending is mostly hardening work: more tests, fallback
behavior, and deployment polish. But the core assignment requirements are
implemented end-to-end: multiple sources, deterministic filtering, multi-
agent reasoning, uncertainty surfacing, persistence, follow-up Q&A, and
baseline comparison.

That’s the system. Thank you.”

Recommended Demo Order On Screen

1. Open UI home page
2. Click Run Analysis
3. Show live stage progress
4. Show completed result
5. Open a previous saved run from sidebar
6. Ask one follow-up chat question
7. Show README evaluation section or saved evaluation JSON filenames
8. Close on architecture/summary

Tips

- Don’t read too fast; 5 minutes is enough
- Show one successful run, not too many
- Avoid opening raw DB tables in the video unless asked
- Keep focus on:
    - signal vs noise
    - Analyst/Critic
    - persistence
    - evaluation vs baseline

If you want, I can turn this into a tighter teleprompter-style script
with timestamps like 0:00-0:30, 0:30-1:20, etc.