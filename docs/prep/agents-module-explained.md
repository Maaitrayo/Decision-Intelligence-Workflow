# Pipeline Agents Module Explained

This document explains, technically and with examples, how every file inside `pipeline/agents` works.

The `pipeline/agents` module is the LLM-driven reasoning layer of the project. It sits after deterministic scoring and before deterministic synthesis.

Its job is:

1. Turn ranked scored items into a compact set of important signals.
2. Challenge those signals.
3. Surface contradictions, contested claims, and endorsements.

Unlike `pipeline/scoring`, this module is not deterministic because it depends on Gemini responses. The code is designed to constrain the model into structured JSON so later stages can still operate predictably.

## 1. Big Picture

The flow across the agents layer is:

```text
list[ScoredItem]
  -> AnalystAgent.run(...)
  -> AgentOutput

AgentOutput + list[ScoredItem]
  -> CriticAgent.run(...)
  -> AgentOutput
```

The two agent outputs are then consumed by synthesis.

## 2. Data Models Used By The Agents Module

The agents module relies mainly on:

- `ScoredItem`
- `AgentSignal`
- `ContradictionRecord`
- `AgentOutput`

### `ScoredItem`

Input shape from the scoring module:

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
    item=RawItem(
        source="hacker_news",
        title="Robotics agent reaches multimodal benchmark",
        url="https://example.com/a",
        summary="Vision and robotics agent system performs well.",
        metadata={"points": 150},
    ),
    signal_score=0.7537,
    bucket="high",
    discard_reason=None,
    duplicate_of=None,
)
```

### `AgentSignal`

This represents one signal extracted by the Analyst:

```python
class AgentSignal(BaseModel):
    title: str
    summary: str
    source: str
    confidence: str | None = None
```

Example:

```python
AgentSignal(
    title="Efficiency-first multimodal robotics systems are gaining traction",
    summary="Multiple items indicate a shift toward deployable robotics agents rather than only larger models.",
    source="hacker_news",
    confidence="high",
)
```

### `ContradictionRecord`

This is how the Critic surfaces conflicts:

```python
class ContradictionRecord(BaseModel):
    signal_a: str
    signal_b: str
    description: str
```

Example:

```python
ContradictionRecord(
    signal_a="Edge-efficient robotics systems are becoming practical",
    signal_b="Reasoning-heavy systems still require larger inference budgets",
    description="The scored set suggests deployment efficiency is improving, but several items imply reasoning quality still depends on larger models."
)
```

### `AgentOutput`

This is the main structured output used by both agents:

```python
class AgentOutput(BaseModel):
    signals: list[AgentSignal] = Field(default_factory=list)
    weak_claims: list[str] = Field(default_factory=list)
    contested_signals: list[str] = Field(default_factory=list)
    contradictions: list[ContradictionRecord] = Field(default_factory=list)
    endorsements: list[str] = Field(default_factory=list)
    reasoning: str = ""
```

Important detail:
- The same `AgentOutput` model is used for both Analyst and Critic.
- But each agent fills different fields.

Typical Analyst output:
- `signals`
- `weak_claims`
- `reasoning`

Typical Critic output:
- `contested_signals`
- `contradictions`
- `endorsements`
- `reasoning`

## 3. File-by-File Explanation

## `pipeline/agents/__init__.py`

Code:

```python
__all__: list[str] = []
```

What it does:
- Like the scoring package `__init__.py`, this file is minimal.
- It does not export any public symbols.
- It mainly marks `pipeline/agents` as a package.

Why it matters:
- It allows imports like `from pipeline.agents.base_agent import BaseAgent`.
- It gives a future place to expose a stable public API if needed.

Current practical behavior:
- No runtime logic.
- No data transformation.
- No direct inputs or outputs.

## `pipeline/agents/base_agent.py`

This is the shared infrastructure file used by both `AnalystAgent` and `CriticAgent`.

It is not used directly by the orchestrator. Instead, the orchestrator uses subclasses that inherit from it.

### Responsibilities

`BaseAgent` does four important things:

1. Creates the Gemini client.
2. Builds a text context from `ScoredItem` objects.
3. Sends a prompt to Gemini and expects JSON back.
4. Parses token usage metadata from the response.

### Step 1: Initialization

Code behavior:

```python
settings = get_settings()
if not settings.gemini_api_key:
    raise ValueError("GEMINI_API_KEY is required to run LLM-backed agents.")

self.client = genai.Client(api_key=settings.gemini_api_key)
self.model = "gemini-3-flash-preview"
self.last_tokens_used = 0
```

#### Input

- Environment/config from `pipeline/config.py`
- Specifically `gemini_api_key`

#### Output

- An initialized agent object with:
  - authenticated Gemini client
  - model name
  - token counter

#### Example

If `.env` contains:

```text
GEMINI_API_KEY=abc123
```

Then:

```python
agent = BaseAgentSubclass()
```

will successfully create a Gemini client.

If the key is missing:

```python
agent = BaseAgentSubclass()
```

raises:

```text
ValueError: GEMINI_API_KEY is required to run LLM-backed agents.
```

### Step 2: `build_context(items)`

This method converts structured `ScoredItem` objects into a plain-text prompt context.

Code behavior:

```python
for index, item in enumerate(items, start=1):
    lines.append(
        f"{index}. {item.item.title} | source={item.item.source} | "
        f"score={item.signal_score} | bucket={item.bucket}"
    )
    if item.item.summary:
        lines.append(f"   summary={item.item.summary}")
```

#### Input

```python
list[ScoredItem]
```

#### Output

A single string formatted like:

```text
1. Robotics agent reaches multimodal benchmark | source=hacker_news | score=0.7537 | bucket=high
   summary=Vision and robotics agent system performs well.
2. Safety benchmark reveals hidden failure modes | source=arxiv | score=0.6921 | bucket=high
   summary=A recent paper highlights failure patterns in multimodal systems.
```

#### Why this matters

Gemini does not directly consume Python objects here. It receives a flattened textual representation of each scored item.

This is the bridge from deterministic scoring data to promptable agent context.

#### Example

Input:

```python
[
    ScoredItem(
        item=RawItem(
            source="hacker_news",
            title="Robotics agent reaches multimodal benchmark",
            url="https://a.com",
            summary="Vision and robotics agent system performs well.",
        ),
        signal_score=0.7537,
        bucket="high",
    ),
    ScoredItem(
        item=RawItem(
            source="arxiv",
            title="Safety benchmark reveals hidden failure modes",
            url="https://b.com",
            summary="A recent paper highlights failure patterns in multimodal systems.",
        ),
        signal_score=0.6921,
        bucket="high",
    ),
]
```

Output:

```text
1. Robotics agent reaches multimodal benchmark | source=hacker_news | score=0.7537 | bucket=high
   summary=Vision and robotics agent system performs well.
2. Safety benchmark reveals hidden failure modes | source=arxiv | score=0.6921 | bucket=high
   summary=A recent paper highlights failure patterns in multimodal systems.
```

### Step 3: `generate_json(system_prompt, user_prompt)`

This is the core LLM call helper.

Code behavior:

```python
response = await self.client.aio.models.generate_content(
    model=self.model,
    contents=f"{system_prompt}\n\n{user_prompt}",
)
self.last_tokens_used = self._extract_tokens_used(response)
text = response.text or "{}"
return self._parse_json_response(text)
```

#### Input

- `system_prompt: str`
- `user_prompt: str`

#### Output

- Parsed Python `dict` created from the model's JSON output

#### Important behavior

- The code concatenates system prompt and user prompt into one text block.
- It expects Gemini to return strict JSON.
- It stores token usage in `self.last_tokens_used`.

#### Example

Input:

```python
system_prompt = "Return strict JSON with keys: signals, weak_claims, reasoning."
user_prompt = "Analyze these items:\n\n1. Robotics agent reaches multimodal benchmark ..."
```

Possible Gemini text response:

```json
{
  "signals": [
    {
      "title": "Robotics systems are becoming more deployable",
      "summary": "Several items suggest an efficiency-first trend in robotics agents.",
      "source": "hacker_news",
      "confidence": "high"
    }
  ],
  "weak_claims": [
    "Some claims about general reasoning ability remain weakly supported."
  ],
  "reasoning": "The strongest recurring signals involve robotics deployment and multimodal efficiency."
}
```

Output returned by `generate_json(...)`:

```python
{
    "signals": [
        {
            "title": "Robotics systems are becoming more deployable",
            "summary": "Several items suggest an efficiency-first trend in robotics agents.",
            "source": "hacker_news",
            "confidence": "high",
        }
    ],
    "weak_claims": [
        "Some claims about general reasoning ability remain weakly supported."
    ],
    "reasoning": "The strongest recurring signals involve robotics deployment and multimodal efficiency.",
}
```

### Step 4: `_parse_json_response(text)`

This method tries to make Gemini output usable even if it wraps JSON in markdown code fences.

#### Input

- Raw response text from Gemini

#### Output

- Parsed Python `dict`

#### Behavior

If response is:

` ```json { "signals": [] } ``` `

the method strips the backticks and then runs `json.loads(...)`.

If response is invalid JSON:

```text
Here is my analysis: signal 1 is important...
```

it raises:

```text
ValueError: Gemini returned non-JSON content.
```

This is a key robustness guard because later code expects structured fields.

### Step 5: `_extract_tokens_used(response)`

This method reads token usage from Gemini response metadata.

#### Input

- Gemini response object

#### Output

- Integer token count

#### Behavior

It tries these fields in order:

```python
total_token_count
total_tokens
candidates_token_count
```

If none exist, it returns `0`.

Why this matters:
- The orchestrator later uses `last_tokens_used` for trace entries and total token accounting.

### Summary of `base_agent.py`

#### Input to the file

- Config and API key
- `list[ScoredItem]`
- Prompt strings

#### Output from the file

- Prompt-ready text context
- Parsed JSON dicts from Gemini
- Token usage for observability

## `pipeline/agents/analyst_agent.py`

This file implements the first LLM role: the Analyst.

The Analyst's job is to look at the best candidate items and propose 3 to 5 important signals.

### Core method: `run(items)`

#### Input

```python
list[ScoredItem]
```

These are the scored items returned from `pipeline/scoring/service.py`.

#### Step 1: Filter candidate items

Code behavior:

```python
candidate_items = [
    item for item in items
    if item.bucket in {"high", "medium"} and item.discard_reason is None
]
```

What this means:
- Only `high` and `medium` items are given to the Analyst.
- Anything with a discard reason is excluded.

So the Analyst does not see:
- `low`
- `noise`
- duplicates
- items outside the top agent input limit

This is the first token-control decision inside the agents layer.

#### Example input to `run(items)`

```python
[
    {"title": "A", "signal_score": 0.91, "bucket": "high", "discard_reason": None},
    {"title": "B", "signal_score": 0.54, "bucket": "medium", "discard_reason": None},
    {"title": "C", "signal_score": 0.19, "bucket": "low", "discard_reason": None},
    {"title": "D", "signal_score": 0.50, "bucket": "medium", "discard_reason": "outside_top_agent_input_limit"},
    {"title": "E", "signal_score": 0.02, "bucket": "noise", "discard_reason": "below_signal_threshold"},
]
```

Actual candidate items sent to the model:

```python
["A", "B"]
```

#### Step 2: Build the Analyst prompt

System prompt:

```text
You are the Analyst agent in a decision intelligence workflow.
Identify the most important signals from the provided scored items.
Return strict JSON with keys: signals, weak_claims, reasoning.
Each signal must contain title, summary, source, confidence.
```

User prompt:

```text
Analyze these scored items and identify 3 to 5 actionable signals.

<context string from build_context(candidate_items)>
```

#### Input to Gemini at this step

- System prompt with task constraints
- User prompt with candidate scored items rendered as text

#### Output expected from Gemini

JSON shaped like:

```json
{
  "signals": [
    {
      "title": "Multi-agent robotics is becoming more practical",
      "summary": "Multiple high-ranked items point to deployable robotics systems with multimodal capabilities.",
      "source": "hacker_news",
      "confidence": "high"
    }
  ],
  "weak_claims": [
    "Claims of general autonomous reliability are still weak."
  ],
  "reasoning": "The highest-ranked items converge on robotics deployment and multimodal efficiency."
}
```

#### Step 3: Convert raw JSON into `AgentSignal` objects

Code behavior:

```python
signals = [
    AgentSignal(
        title=signal.get("title", ""),
        summary=signal.get("summary", ""),
        source=signal.get("source", ""),
        confidence=self._normalize_confidence(signal.get("confidence")),
    )
    for signal in payload.get("signals", [])
    if signal.get("title")
]
```

What this does:
- Keeps only signals that actually have a title
- Creates strongly typed `AgentSignal` objects
- Normalizes confidence values

#### Step 4: Normalize confidence

The helper `_normalize_confidence(value)` supports:

- strings
- numbers
- unknown values

Behavior:

```text
"HIGH"    -> "high"
"Medium"  -> "medium"
0.9       -> "high"
0.6       -> "medium"
0.2       -> "low"
None      -> "medium"
```

This makes downstream logic more stable because synthesis expects a normalized confidence label.

#### Step 5: Return `AgentOutput`

Output from `AnalystAgent.run(...)`:

```python
AgentOutput(
    signals=[...],
    weak_claims=[...],
    reasoning="..."
)
```

Fields typically left empty by the Analyst:

```python
contested_signals=[]
contradictions=[]
endorsements=[]
```

### Full worked example

#### Input to `AnalystAgent.run(...)`

```python
[
    ScoredItem(
        item=RawItem(
            source="hacker_news",
            title="Robotics agent reaches multimodal benchmark",
            url="https://a.com",
            summary="Vision and robotics agent system performs well.",
        ),
        signal_score=0.7537,
        bucket="high",
        discard_reason=None,
    ),
    ScoredItem(
        item=RawItem(
            source="arxiv",
            title="Safety benchmark reveals hidden failure modes",
            url="https://b.com",
            summary="A recent paper highlights failure patterns in multimodal systems.",
        ),
        signal_score=0.6921,
        bucket="high",
        discard_reason=None,
    ),
]
```

#### Output from `AnalystAgent.run(...)`

```python
AgentOutput(
    signals=[
        AgentSignal(
            title="Robotics systems are becoming more deployable",
            summary="High-ranked items suggest a shift toward practical multimodal robotics systems.",
            source="hacker_news",
            confidence="high",
        ),
        AgentSignal(
            title="Safety evaluation remains a major unresolved issue",
            summary="Recent research highlights persistent hidden failure modes in multimodal systems.",
            source="arxiv",
            confidence="high",
        ),
    ],
    weak_claims=[
        "General autonomy claims appear stronger than the evidence provided by the scored set."
    ],
    contested_signals=[],
    contradictions=[],
    endorsements=[],
    reasoning="The strongest items converge on deployability and safety risk."
)
```

## `pipeline/agents/critic_agent.py`

This file implements the second LLM role: the Critic.

The Critic's job is not to generate fresh primary signals from scratch. Its job is to challenge, endorse, and find contradictions relative to the Analyst's output and the broader scored set.

### Core method: `run(analyst_output, items)`

#### Input

1. `analyst_output: AgentOutput`
2. `items: list[ScoredItem]`

This is an important difference from the Analyst:
- The Analyst only receives scored items.
- The Critic receives both the Analyst's interpretation and the scored items themselves.

#### Step 1: Build the Critic prompt

System prompt:

```text
You are the Critic agent in a decision intelligence workflow.
Challenge the analyst's proposed signals, identify contested signals,
endorse strong ones, and surface contradictions from the broader scored set.
Return strict JSON with keys: contested_signals, contradictions, endorsements, reasoning.
Each contradiction must contain signal_a, signal_b, description.
```

User prompt:

```text
Analyst output:
<analyst_output as JSON>

Scored items:
<context string from build_context(items)>
```

#### Input to Gemini at this step

- The Analyst's structured output, serialized with `model_dump_json(indent=2)`
- The scored item list converted to text context

This gives the Critic two things:
- the claims to challenge
- the evidence pool to use while challenging them

#### Example input to `CriticAgent.run(...)`

```python
analyst_output = AgentOutput(
    signals=[
        AgentSignal(
            title="Robotics systems are becoming more deployable",
            summary="High-ranked items suggest a shift toward practical multimodal robotics systems.",
            source="hacker_news",
            confidence="high",
        ),
        AgentSignal(
            title="Safety evaluation remains a major unresolved issue",
            summary="Recent research highlights persistent hidden failure modes in multimodal systems.",
            source="arxiv",
            confidence="high",
        ),
    ],
    weak_claims=["General autonomy claims appear stronger than the evidence provided by the scored set."],
    reasoning="The strongest items converge on deployability and safety risk.",
)

items = [
    ScoredItem(... bucket="high" ...),
    ScoredItem(... bucket="medium" ...),
    ScoredItem(... bucket="low" ...),
]
```

#### Output expected from Gemini

```json
{
  "contested_signals": [
    "Robotics systems are becoming more deployable"
  ],
  "contradictions": [
    {
      "signal_a": "Robotics systems are becoming more deployable",
      "signal_b": "Reasoning-heavy systems still require large inference budgets",
      "description": "The scored evidence suggests deployment efficiency is improving, but some items imply that deeper reasoning still depends on large models."
    }
  ],
  "endorsements": [
    "Safety evaluation remains a major unresolved issue"
  ],
  "reasoning": "The safety signal is strongly supported, but the deployability signal may overstate practical readiness."
}
```

#### Step 2: Convert contradictions into typed records

Code behavior:

```python
contradictions = [
    ContradictionRecord(
        signal_a=entry.get("signal_a", ""),
        signal_b=entry.get("signal_b", ""),
        description=entry.get("description", ""),
    )
    for entry in payload.get("contradictions", [])
    if entry.get("signal_a") and entry.get("signal_b")
]
```

What this does:
- Keeps only contradictions that contain both endpoints
- Converts them into structured `ContradictionRecord` objects

#### Step 3: Build final `AgentOutput`

Output from `CriticAgent.run(...)`:

```python
AgentOutput(
    contested_signals=[...],
    contradictions=[...],
    endorsements=[...],
    reasoning="..."
)
```

Fields usually left empty by the Critic:

```python
signals=[]
weak_claims=[]
```

### Full worked example

#### Input to `CriticAgent.run(...)`

```python
analyst_output = AgentOutput(
    signals=[
        AgentSignal(
            title="Robotics systems are becoming more deployable",
            summary="High-ranked items suggest a shift toward practical multimodal robotics systems.",
            source="hacker_news",
            confidence="high",
        ),
        AgentSignal(
            title="Safety evaluation remains a major unresolved issue",
            summary="Recent research highlights persistent hidden failure modes in multimodal systems.",
            source="arxiv",
            confidence="high",
        ),
    ],
    weak_claims=["General autonomy claims appear stronger than the evidence provided by the scored set."],
    reasoning="The strongest items converge on deployability and safety risk.",
)

items = [
    ScoredItem(
        item=RawItem(
            source="hacker_news",
            title="Robotics agent reaches multimodal benchmark",
            url="https://a.com",
            summary="Vision and robotics agent system performs well.",
        ),
        signal_score=0.7537,
        bucket="high",
    ),
    ScoredItem(
        item=RawItem(
            source="arxiv",
            title="Larger inference budgets still dominate complex reasoning",
            url="https://b.com",
            summary="A new paper argues smaller efficient systems still lag on deeper reasoning tasks.",
        ),
        signal_score=0.6112,
        bucket="medium",
    ),
    ScoredItem(
        item=RawItem(
            source="arxiv",
            title="Safety benchmark reveals hidden failure modes",
            url="https://c.com",
            summary="A recent paper highlights failure patterns in multimodal systems.",
        ),
        signal_score=0.6921,
        bucket="high",
    ),
]
```

#### Output from `CriticAgent.run(...)`

```python
AgentOutput(
    signals=[],
    weak_claims=[],
    contested_signals=[
        "Robotics systems are becoming more deployable"
    ],
    contradictions=[
        ContradictionRecord(
            signal_a="Robotics systems are becoming more deployable",
            signal_b="Reasoning-heavy systems still require large inference budgets",
            description="Efficiency gains are real, but the scored evidence suggests deeper reasoning still depends on larger systems."
        )
    ],
    endorsements=[
        "Safety evaluation remains a major unresolved issue"
    ],
    reasoning="The safety signal is strongly supported, but claims about practical deployability are partly overstated."
)
```

## 4. Input and Output of Every Step

This section compresses the entire module into stepwise I/O form.

### Step A: Deterministic scoring hands over `list[ScoredItem]`

Input:

```python
list[ScoredItem]
```

Output:

Passed into `AnalystAgent.run(items)`

### Step B: `BaseAgent.build_context(items)`

Input:

```python
list[ScoredItem]
```

Output:

```python
str
```

Example output:

```text
1. Robotics agent reaches multimodal benchmark | source=hacker_news | score=0.7537 | bucket=high
   summary=Vision and robotics agent system performs well.
```

### Step C: `AnalystAgent.run(items)`

Input:

```python
list[ScoredItem]
```

Internal filtered input sent to LLM:

```python
list[ScoredItem] where bucket in {"high", "medium"} and discard_reason is None
```

Output:

```python
AgentOutput(
    signals=[AgentSignal, ...],
    weak_claims=[str, ...],
    reasoning=str,
)
```

### Step D: `BaseAgent.generate_json(system_prompt, user_prompt)`

Input:

```python
system_prompt: str
user_prompt: str
```

Output:

```python
dict
```

Side output:

```python
self.last_tokens_used: int
```

### Step E: `CriticAgent.run(analyst_output, items)`

Input:

```python
analyst_output: AgentOutput
items: list[ScoredItem]
```

Output:

```python
AgentOutput(
    contested_signals=[str, ...],
    contradictions=[ContradictionRecord, ...],
    endorsements=[str, ...],
    reasoning=str,
)
```

### Step F: Token accounting

Input:

- Gemini response metadata

Output:

```python
last_tokens_used: int
```

This is later consumed by the orchestrator for traces and total token usage.

## 5. Design Strengths Of The Agents Module

### Structured outputs instead of free-form text

The agents are constrained to JSON, which makes synthesis and persistence much easier.

### Separation of roles

- Analyst extracts candidate signals.
- Critic challenges and validates those signals.

This is more reliable than one model trying to both advocate and attack the same conclusion in one pass.

### Deterministic boundary on both sides

- Before agents: deterministic scoring controls what they see.
- After agents: deterministic synthesis controls how their outputs are merged.

This keeps the LLM role narrow and easier to defend.

## 6. Limitations And Interview-Worthy Caveats

### JSON compliance is not guaranteed

The code expects strict JSON. If Gemini returns prose, the agent call fails with a parse error.

### Prompt context is flattened text

The scored items are converted into a simple string format, which is easy to implement but less semantically rich than a fully structured tool-based interaction.

### Critic sees all scored items

This is good for contradiction detection, but it can increase prompt size and token cost.

### No retry or fallback logic yet

If the model returns malformed JSON or the API fails, there is no additional recovery logic in this layer.

## 7. One-Line Summary For Interview Use

If asked to summarize the agents module in one line:

> The `pipeline/agents` module takes filtered scored items, asks an Analyst agent to propose structured signals, asks a Critic agent to challenge those signals using the broader scored set, and returns typed JSON outputs that downstream synthesis can merge deterministically.
