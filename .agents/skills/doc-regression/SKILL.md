---
name: doc-regression
description: Regression-test whether MCP tool documentation (descriptions + JSON Schema) is clear enough for LLMs to construct correct payloads. Give a model ONLY the tool docs + a tricky scenario prompt, grade the output. Trigger on "doc regression", "run doc tests", "test tool docs", "schema regression", "add doc scenarios", "brainstorm scenarios", "new doc test cases".
---

# Doc Regression

Test whether the tool documentation (description + inputSchema) is clear enough for LLMs to construct correct JSON payloads, without access to source code.

## Critical Rule: Never Read Source Code

The whole point is testing docs as agents see them. Tool knowledge comes ONLY from `ToolSearch` queries. Never read `server.py`, model files, or any `.py` source. This applies during scenario creation, test execution, AND grading.

## Modes

### Mode 1: Run Tests

**Trigger:** "doc regression", "run doc tests", "test tool docs", "schema regression"

Run scenario suites against models and produce a scorecard.

**Invocation patterns:**
- `doc regression edit-tasks` — all scenarios, all 3 models
- `doc regression add-tasks sonnet` — one suite, one model
- `doc regression edit-tasks scenario 3 haiku` — one scenario, one model
- `doc regression all` — all suites, all models

### Mode 2: Add / Brainstorm Scenarios

**Trigger:** "add doc scenarios", "brainstorm scenarios", "new doc test cases"

Collaboratively brainstorm and add new scenarios. Flow:
1. Query the tool via ToolSearch to understand current capabilities
2. Read existing scenarios to identify coverage gaps
3. Help the user invent tricky new scenarios
4. Write scenarios in the correct format, append to appropriate file

---

## Execution Flow (Run Mode)

### Step 1: Parse Invocation

Determine from the user's message:
- **Suite(s):** which scenario file(s) to load (e.g., `edit-tasks`, `add-tasks`, `all`)
- **Model(s):** which models to test (`haiku`, `sonnet`, `opus`, or all three)
- **Scenario filter:** specific scenario number, or all

### Step 2: Fetch Live Tool Docs

**This is the most important step.** Use `ToolSearch` to fetch the CURRENT description + schema for the tools needed by the suite:
- `edit-tasks` suite → fetch both `edit_tasks` AND `add_tasks` (multi-tool scenarios)
- `add-tasks` suite → fetch both `add_tasks` AND `edit_tasks` (multi-tool scenarios)

Search query: `omnifocus` (broad enough to find all tools). Extract the `description` and full `parameters` schema for each tool.

Format the tool docs as a clean reference block to include in the exam prompt:
```
## Tool: add_tasks

**Description:**
[full description text]

**Input Schema:**
[full JSON Schema]

---

## Tool: edit_tasks

**Description:**
[full description text]

**Input Schema:**
[full JSON Schema]
```

### Step 3: Load Scenarios

Read the scenario file from `scenarios/` (relative to this skill file). Parse each `### Scenario` section, extracting:
- Prompt (the exam question)
- Trap (human-only context, never sent to model)
- Expected tool + payload (reference answer)
- Grading criteria

### Step 4: Construct Exam Prompt

For each scenario, build this prompt (NEVER include Trap or Grading):

```
You are being tested on how well you can construct MCP tool call payloads from a tool definition.

Here are the tools with their descriptions and input schemas:

---
{tool docs from Step 2}
---

Today's date is {current date in YYYY-MM-DD format}.

Produce the correct JSON payload for this task. Output ONLY the tool name and JSON payload.
If multiple tool calls are needed, show each one in order and note dependencies.

Task: {scenario prompt}
```

### Step 5: Run Models

Spawn **one Agent per model** — each agent receives ALL scenarios as a single exam and answers every one. With 2 models that's 2 agents; with 3 models, 3 agents. Launch all model agents in parallel.

Construct the agent prompt by concatenating ALL scenario exam prompts (from Step 4) into one message, separated by `---`. The agent answers each scenario in order. Agent prompt is exactly the combined exam — nothing more.

### Step 6: Grade

For each model response:
1. Parse the JSON payload from the response (be lenient about surrounding text)
2. Identify which tool was called
3. Evaluate each grading criterion:
   - **MUST** — hard fail if not met
   - **MUST NOT** — hard fail if present
   - **SHOULD** — warning, not a fail
4. Result is **PASS** if all MUST/MUST NOT assertions pass, **FAIL** otherwise

**Grading notes:**
- For date fields, accept any reasonable timezone offset (Z, +00:00, +01:00, etc.)
- For fuzzy dates (e.g., "MUST be a date in June 2026"), check month and year, not exact day
- For "MUST NOT be present", the field must be absent from the JSON entirely (not just null)
- For multi-tool scenarios, grade each call separately. Both must pass.
- When multiple valid approaches are listed (Option A / Option B), pass if ANY option's criteria are met

### Step 7: Produce Scorecard

Output the report using the format below.

---

## Scenario File Format

Each scenario file uses this markdown structure:

```markdown
### Scenario N: Short descriptive name

**Prompt:**
> Natural language task request as an agent would receive it.

**Trap:** What makes this tricky (human-only, NEVER sent to model).

**Expected:** `tool_name`
\```json
{ ... }
\```

**Grading:**
- `items[0].field` MUST equal "value"
- `items[0].other` MUST NOT be present
- `items[0].field` SHOULD contain "text"
```

**Rules:**
- **Trap** = human documentation only
- **MUST** = hard fail | **SHOULD** = warning only | **MUST NOT** = hard fail if present
- Multi-tool: Expected line says `add_tasks then edit_tasks`, show both payloads
- Fuzzy dates: `MUST be a date in [month] [year]`
- Multiple valid approaches: list Option A / Option B, pass if ANY match

---

## Report Format

Use emoji for results: ✅ = pass, ❌ = fail, ⚠️ = pass with warnings.

Group scenarios by category with bold header rows for visual scanning.
Keep the table tight — trap column should be 3-5 words max.

When only one model is tested, omit the other model columns.

```
# 📋 Doc Regression — {suite_name}

> **Date:** {date}
> **Docs:** fetched live via ToolSearch
> **Models:** Haiku · Sonnet · Opus

---

## Results

| # | Scenario | Trap | 🟣 Haiku | 🔵 Sonnet | 🟠 Opus |
|--:|----------|------|:--------:|:---------:|:-------:|
|   | **Patch Semantics** | | | | |
| 1 | Surgical null/omit/value | estimatedMinutes omit | ✅ | ✅ | ✅ |
| 2 | Mass clear | all fields + tags | ❌ | ✅ | ✅ |
|   | **Date Fields** | | | | |
| 5 | Hide from lists | defer not planned | ✅ | ⚠️ | ✅ |
...

---

## Scoreboard

| Model | ✅ | ❌ | Score |
|-------|:--:|:--:|:-----:|
| 🟣 Haiku | 20 | 2 | **20/22** |
| 🔵 Sonnet | 18 | 4 | **18/22** |
| 🟠 Opus | 22 | 0 | **22/22** |

---

## ❌ Failures

### Scenario 2 — Mass clear (Haiku)
**Trap:** all fields + tags
**Expected:** `actions.tags.replace: null`
**Got:** `actions.tags.remove: ["all"]` — used remove mode instead of replace
**Root cause:** Docs don't explicitly say "replace with null/[] to clear all"

### Scenario 5 — Hide from lists (Sonnet) ⚠️
**Trap:** defer not planned
**Note:** Used correct field (deferDate) but also set plannedDate — harmless but unnecessary

---

## 📝 Doc Improvement Notes

Patterns from failures that suggest documentation could be clearer:

- **[Pattern]:** N/M models failed scenario X — [suggested doc improvement]
```

**Section rules:**
- **Scoreboard** is always present, even with perfect scores (quick confirmation)
- **Failures** section: only present if there are failures. Each failure gets its own subsection with trap, expected vs got, and root cause analysis
- **Doc Improvement Notes**: only present if failures suggest doc improvements. Focus on actionable suggestions, not just "model got it wrong"
- **Warnings (⚠️)**: include in Failures section with the ⚠️ marker, but clearly note they passed. These are "technically correct but suspicious" results worth documenting
