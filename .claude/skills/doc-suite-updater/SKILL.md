---
name: doc-suite-updater
description: Create or update doc-regression scenario suites for OmniFocus Operator. Two-phase workflow — initialization (deep research → seed file) then collaborative worker (pick up chunk → co-write scenarios with user). Use when the user says "update doc scenarios", "doc suite update", "update doc regression", "doc gap analysis", "new doc scenarios for [tool]", "doc-suite-updater", "pick up doc chunk", "initialize doc analysis", "doc scenario seed", "run doc chunk", or wants to add/expand doc-regression coverage after shipping a milestone. Also handles ad-hoc single-suite edits.
---

# Doc Suite Updater

Two-phase workflow for updating doc-regression scenario suites after shipping a milestone: **initialize** (deep research → seed file) then **collaborative worker** (pick up chunks → co-write scenarios with user).

## Doc-Clarity Principle

These scenarios are **documentation clarity tests** — "can an LLM construct the correct payload from the tool docs alone?" They are NOT derived from reading source code. They are NOT testing whether the code works (that's UAT).

The question each scenario answers: *"If a model has never seen this codebase, only the tool description and JSON Schema, would it construct the right payload for this request?"*

**Allowed sources** (for both seed generation and workers):
- **Live tool documentation**: fetched via `ToolSearch` — descriptions + inputSchema as agents see them. This is the primary source.
- **Milestone specs**: `.research/updated-spec/MILESTONE-v{X}.md` — what was built, what fields were added/changed
- **Per-phase documents** in `.planning/phases/{N}-{name}/`:
  - `{N}-CONTEXT.md` — phase requirements and scope
  - `{N}-DISCUSSION-LOG.md` — decision resolutions
  - `{N}-VERIFICATION.md` — did we build what was planned?
  - `{N}-{NN}-SUMMARY.md` — what each sub-plan delivered
- **Project-level**: `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md`
- **Archived milestones**: `.planning/milestones/v{X}-ROADMAP.md`, `v{X}-REQUIREMENTS.md`, `v{X}-phases/`
- **Architecture docs**: `docs/architecture.md`, `docs/model-taxonomy.md`, `docs/omnifocus-concepts.md`
- **Existing scenario files** in `.claude/skills/doc-regression/scenarios/`
- **Previous doc-regression results**: if the user has saved scorecard output from earlier runs, those failures are valuable inputs for identifying where docs are weak

The agent should explore these locations autonomously — the list above is guidance, not exhaustive. The only hard rule is: **never read `.py` files or automated test files**.

**Never read**: `.py` source files, automated test files, or any implementation code. If you read code to understand field behavior, you already know too much — you're no longer testing what the *docs* communicate. That's the whole point.

**Trap quality**: the value of a scenario comes from its *trap* — the thing that makes it tricky. A scenario without a meaningful trap ("create a task called X") is wasted coverage. Every scenario should test a genuine documentation ambiguity, a field confusion risk, or a subtle semantic distinction that models commonly get wrong.

**Regression meaning**: once a scenario suite passes across models, running it later should still pass — unless the documentation was deliberately changed. The updater's job is to update scenarios when the *tool docs* evolve, not when the code changes.

## Mode Detection

Always run this first. Determines which mode to enter.

1. Look for `DOC-SUITE-ANALYSIS.md` at repo root
2. **Not found** → Initialization Mode
3. **Found** → read the `## Progress` section:
   - Unchecked content chunks exist → **Worker Mode**
   - All content chunks checked (only "Delete this file" unchecked) → **Completion Mode**
4. **Override**: if the user names a specific suite + specific change (e.g., "just add a repetition scenario to add-tasks.md"), skip mode detection → **Ad-hoc Override**
5. **Re-seed override**: if a seed file exists with unchecked chunks BUT the user explicitly asks to re-analyze or regenerate (e.g., "run it again", "re-seed", "fresh analysis"), ask: "Found existing seed with N unchecked chunks. Archive the old seed and generate a fresh analysis?" On confirmation, archive to `.research/doc-suite-seeds/` and enter Initialization Mode.

**Idempotency**: this workflow is safe to re-run. Initialization always compares current tool docs against current scenario coverage. If suites are already up to date, the gap analysis will find fewer or no gaps.

## Initialization Mode

Deep research session that produces a seed file coordinating future collaborative worker sessions.

**Precondition**: verify this session is running in a git worktree (`git rev-parse --show-toplevel` vs `git worktree list`). Hard stop if not — the seed file and chunk work should happen on a branch, not main.

### Step 1 — Determine milestone scope

- Read `.planning/STATE.md` (frontmatter: `milestone`, `milestone_name`)
- Read `.planning/ROADMAP.md` for phase ranges
- List git tags (`git tag --list`)
- Ask user: **current milestone or archived?**
  - Current → `.planning/ROADMAP.md` + `.planning/phases/`
  - Archived → `.planning/milestones/v{X}-ROADMAP.md` + `v{X}-phases/`
- Determine git diff range from consecutive tags (e.g., `v1.3..v1.3.1`)

### Step 2 — Deep exploration (parallel agents)

Spawn four agents in parallel:

- **Agent A — Tool documentation inventory**: Use `ToolSearch` to fetch current descriptions + schemas for ALL OmniFocus Operator tools. For each tool, catalog every field, its description, type, constraints, and semantic meaning. This is the "what agents actually see" baseline.
- **Agent B — What changed this milestone**: read phase CONTEXT files, verification reports, and milestone spec. Identify: new tools added, new fields on existing tools, changed field semantics, new validation rules, changed descriptions. Group by tool.
- **Agent C — Existing scenario review**: read all scenario files in `.claude/skills/doc-regression/scenarios/`. For each scenario, record: which tool, which fields tested, what the trap is, what grading criteria exist. Build a coverage matrix: tool × field → scenario numbers.
- **Agent D — Planning context + doc decisions**: read milestone ROADMAP, phase CONTEXT files, and any documentation-specific decisions (e.g., "we changed the deferDate description to say X"). Look for explicit doc improvement notes from previous doc-regression runs if any exist.

### Step 3 — Gap analysis

Cross-reference the tool documentation inventory (Agent A) against scenario coverage (Agent C) to find:

- **Uncovered tools**: tools with no scenario file at all → flag for new suite creation
- **Uncovered fields**: fields on existing tools with no scenario testing them
- **Stale scenarios**: existing scenarios whose Expected payload or Grading references fields/behaviors that changed this milestone
- **Documentation improvements**: if tool descriptions were improved this milestone, existing traps may no longer be valid (e.g., a trap was "docs don't mention X" but now they do)
- **New feature gaps**: features shipped this milestone (Agent B) that create doc-clarity testing opportunities

**Known gaps**: distinguish between "not yet implemented" and "should be testable":
  - If a tool/field belongs to a phase that hasn't been executed yet → skip it, no scenario needed yet
  - If a feature is shipped but has no scenario → gap to fill

### Step 4 — Identify trap opportunities

This is the creative analysis step. For each gap identified in Step 3, brainstorm trap concepts:

**Trap categories** (use as a checklist):
1. **Field confusion**: two fields with similar names/purposes that models mix up (deferDate vs plannedDate, on vs onDates)
2. **Implicit requirements**: field A requires field B, but it's only mentioned in the description (all 3 repetitionRule root fields required for new rules)
3. **Semantic subtlety**: natural language maps to a non-obvious field ("by Friday" = plannedDate when context says "not urgent")
4. **Structural traps**: different tools use different structures for the same concept (flat `tags` in add_tasks vs `actions.tags` in edit_tasks)
5. **Null semantics**: null vs omit vs false vs empty array have different meanings
6. **Multi-tool**: operations requiring two tool calls that models try to do in one
7. **Buried information**: task details scattered in conversational prose that models must extract
8. **Edge cases**: computed dates, ambiguous language, format requirements
9. **Mode conflicts**: mutually exclusive options where models pick the wrong one (add/remove vs replace for tags)
10. **Default confusion**: when changing type triggers creation defaults, losing existing values

For each trap concept, record:
- Which tool/field it tests
- The trap idea (one sentence)
- Why it matters (what real-world mistake it catches)
- Estimated difficulty for models (easy/medium/hard)

### Step 5 — Chunk the work

- Group by suite affinity (same tool / related trap themes)
- **Proportional sizing**: ~5-8 new scenarios + ~3-5 updates max per chunk. These are collaborative — each scenario involves discussion, so chunks must be smaller than UAT chunks.
- **New suite creation**: when a chunk creates a NEW scenario file, that same chunk MUST include:
  1. A header matching the existing format (`# {Tool Name} — Doc Regression Scenarios`)
  2. An opening line describing what the scenarios test
  - The doc-regression skill discovers scenario files automatically from the `scenarios/` directory — no registration step needed (unlike UAT suites)
- Always end with a "Delete this file" checkbox

### Step 6 — Write seed file

- Write `DOC-SUITE-ANALYSIS.md` at repo root following the **Seed File Template** section below
- **No scenario editing in this mode** — the seed file IS the deliverable

### Step 7 — Ambiguity gate

Before committing, present all ambiguities encountered during research. The user will NOT review the seed itself — this is their only chance to catch misinterpretations before they get baked into chunk instructions.

**Resolution hierarchy** (when sources conflict):
1. Live tool documentation (ToolSearch) is the ultimate truth for "what does the agent see?"
2. Updated spec in `.research/updated-spec/` supersedes original spec for "what was intended"
3. Phase discussion logs contain explicit "we decided X" resolutions
4. Later phase CONTEXT files supersede earlier ones on the same topic
5. If clearly documented → not an ambiguity, just use it
6. If NOT clearly documented → flag it

**Present each ambiguity** with:
   - What was unclear
   - What you chose and why
   - Confidence level (high / medium / low)

**Wait for user confirmation.** If corrections needed, update the seed file and re-present. On confirmation: commit `docs: add doc-regression gap analysis for v{version}`.

If no ambiguities were found, say so explicitly and proceed to commit.

### No gaps found (expected outcome on re-runs)

If research shows scenario suites are already up to date, say so with evidence (which tools/fields are covered, which traps exist). Don't produce an empty seed file — this is a successful result.

## Worker Mode

Pick up the next chunk from the seed file and **co-write scenarios with the user**.

This is fundamentally collaborative. Unlike UAT suite updates where the worker writes tests and asks for sign-off, doc-regression scenarios require creative input — the trap must be genuine, the prompt must sound natural, the grading must be precise. The worker proposes, the user shapes.

### Step 1 — Orient

- Read `DOC-SUITE-ANALYSIS.md`, find first unchecked content chunk
- **Version check**: compare version in seed title against `.planning/STATE.md` — warn if mismatched
- Read the doc-regression skill (`.claude/skills/doc-regression/SKILL.md`) silently to internalize conventions
- Read the specific scenario files being updated in this chunk

### Step 2 — Targeted research

- Use `ToolSearch` to fetch current tool docs for the specific tools in this chunk
- Re-read relevant planning docs (phase CONTEXT files) for the specific changes in this chunk
- Don't re-research the whole milestone — the seed has that context
- **Scenario number drift**: verify existing scenario numbers against current state (earlier chunks may have shifted them)

### Step 3 — Present trap concepts

For each gap/trap identified in the seed's chunk instructions, present to the user:

**Format per trap:**
```
### Trap: {one-line concept}

**Tests:** {tool_name} — {field(s) involved}
**Why it matters:** {what real-world mistake this catches}
**Difficulty:** {easy/medium/hard for models}

**Rough prompt idea:**
> {draft natural-language prompt — conversational, as an agent would receive it}

**The trick:** {what makes this confusing — why a model might get it wrong}
```

Present all trap concepts for this chunk, then **wait for user feedback**:
- User may approve, modify, reject, or add new trap ideas
- User may reorder priorities ("do this one first, skip that one")
- User may suggest prompt rewording ("make it more conversational", "bury the detail deeper")

**Do NOT write finished scenarios yet** — this step is about aligning on *what* to test.

### Step 4 — Co-write scenarios

For each approved trap, draft a complete scenario:

1. Write the full scenario (Prompt, Trap, Expected, Grading) following doc-regression conventions
2. Present it to the user for review
3. User may:
   - Approve as-is
   - Adjust the prompt wording
   - Tighten/loosen grading criteria
   - Add edge cases ("what if the model also sets X?")
   - Split into multiple scenarios
4. Finalize and move to the next scenario

**Iterate per scenario, not per batch.** The creative discussion is the valuable part — don't rush through a list.

### Step 5 — Review existing scenarios for staleness

If the seed flagged existing scenarios that may need updates (changed field semantics, obsolete traps):

1. Show each flagged scenario with what changed and why it might be stale
2. Propose specific updates (new Expected payload, adjusted Grading, updated Trap description)
3. Wait for user approval per scenario

### Step 6 — Validation (optional)

After all scenarios for this chunk are written/updated:

1. **Offer to run doc-regression**: "Want me to test these new scenarios against the models to see if the traps actually work?"
2. **If user approves**: invoke the doc-regression skill on just the new/modified scenarios. This tests whether:
   - The trap actually catches model mistakes (at least one model should struggle)
   - The grading criteria correctly distinguish pass/fail
   - The prompt is clear enough that the right answer IS right
3. **If results reveal issues**: discuss with user and adjust scenarios
4. **If user declines**: proceed to Step 7

**Note**: validation is genuinely optional here — unlike UAT where live verification catches spec-vs-reality gaps, doc-regression scenarios are internally consistent. Validation is about trap quality, not correctness.

### Step 7 — Completion protocol

1. **Summarize**: files modified, scenarios added, scenarios updated, validation results if applicable
2. **Wait for user sign-off** — user reviews the changes
3. **On approval**:
   - Commit scenario changes: `test(doc): {description of what was added/changed}`
   - Mark chunk done in separate commit: `chore: mark chunk N complete in doc suite analysis`
4. **If all content chunks now done**: inform user, suggest triggering this skill again for Completion mode

### Edge case — Concurrent workers

The checkbox mechanism isn't atomic. If a chunk was just checked by another session, move to the next unchecked chunk.

## Completion Mode

All content chunks are done. Archive the seed file and wrap up.

1. Create `.research/doc-suite-seeds/` directory if it doesn't exist
2. Archive: `git mv DOC-SUITE-ANALYSIS.md .research/doc-suite-seeds/v{version}.md`
3. Commit: `chore: archive doc suite analysis for v{version}`
4. Remind user to merge the worktree branch to main and clean up the worktree

## Ad-hoc Override

If the user names a specific suite and a specific change ("just add a repetition edge case to edit-tasks.md"), skip mode detection entirely. Read the target suite, follow doc-regression conventions, co-write the scenario with the user. No seed file involved.

## Seed File Template

The seed file must follow this exact structure.

```markdown
# Doc Suite Analysis — v{version} "{milestone_name}"

## How to Use This File

This file is the output of a research session that analyzed what v{version} changed in tool documentation vs what existing doc-regression scenarios cover. It contains everything a fresh agent needs to co-write new scenarios with the user without re-doing the research.

**Workflow:** Run `/doc-suite-updater` in a new session. The skill auto-detects this file and enters Worker mode — it will find the next unchecked chunk, present trap concepts, co-write scenarios with the user, and mark the chunk done.

**Important:** Worker sessions are collaborative — the agent proposes trap concepts and drafts scenarios, but the user shapes the final content. The seed provides starting points, not prescriptive instructions.

---

## Progress

- [ ] Chunk 1 — {title}
- [ ] Chunk 2 — {title}
- [ ] ...
- [ ] **Delete this file** (all chunks done, everything merged)

---

## Chunks — Task List

### Chunk completion protocol

After co-writing the scenarios for a chunk, the agent does NOT commit. Instead:

1. **Summarize changes** — list every file modified, scenarios added, scenarios updated
2. **Offer validation** — "Want me to run these new scenarios through doc-regression to test if the traps work?"
3. **Wait for sign-off** — user reviews the changes (and validation results if applicable)
4. **On approval**: commit the scenario changes, then update the Progress checklist above (check the box)

---

### Chunk 1: {title}

**Suites:** {list of scenario files}

**Trap concepts to explore:**
- {trap idea — one line each, referencing entries in the Trap Idea Bank below}
- {trap idea}

**Stale scenarios to review:**
- {scenario reference — what changed and why it might be stale}

**Est. scope:** ~N new scenarios + ~M updates.

---

{repeat for each chunk}

---

## Reference Material

Everything below is research output — the chunks above reference it.

---

## What v{version} Changed in Tool Documentation

{Organized by tool — what fields were added, what descriptions changed, what new behaviors exist}

---

## Tool Documentation Inventory

Current state of every tool's documentation, with scenario coverage status.

### {tool_name}

**Description summary:** {one-line summary of what the tool does}

| Field | Type | Covered by Scenario(s) | Notes |
|-------|------|----------------------|-------|
| {field} | {type} | {scenario numbers or "none"} | {any notes about tricky semantics} |
| ... | ... | ... | ... |

---

{repeat for each tool}

---

## Gap Analysis by Suite

### {suite name} ({N} scenarios) — {NEEDS UPDATES | UP TO DATE | NEW SUITE NEEDED}

**Uncovered fields/behaviors:**

| Field/Behavior | Why it needs a scenario | Trap potential |
|---------------|----------------------|----------------|
| ... | ... | ... |

**Stale scenarios:**
- Scenario N: {what changed — old assumption vs new reality}

---

{repeat for each suite}

### Suites that DON'T need changes

| Suite | Why it's fine |
|-------|---------------|
| ... | ... |

---

## Trap Idea Bank

Creative trap concepts organized by category. Workers use these as starting points for collaborative scenario writing.

### Field Confusion
| ID | Trap Concept | Tool | Fields | Difficulty | Why It Matters |
|----|-------------|------|--------|------------|---------------|
| FC-01 | ... | ... | ... | medium | ... |

### Implicit Requirements
| ID | Trap Concept | Tool | Fields | Difficulty | Why It Matters |
|----|-------------|------|--------|------------|---------------|
| IR-01 | ... | ... | ... | hard | ... |

### Semantic Subtlety
| ID | Trap Concept | Tool | Fields | Difficulty | Why It Matters |
|----|-------------|------|--------|------------|---------------|
| SS-01 | ... | ... | ... | medium | ... |

### Structural Traps
| ID | Trap Concept | Tool | Fields | Difficulty | Why It Matters |
|----|-------------|------|--------|------------|---------------|
| ST-01 | ... | ... | ... | hard | ... |

### Null Semantics
| ID | Trap Concept | Tool | Fields | Difficulty | Why It Matters |
|----|-------------|------|--------|------------|---------------|
| NS-01 | ... | ... | ... | medium | ... |

### Multi-Tool
| ID | Trap Concept | Tool | Fields | Difficulty | Why It Matters |
|----|-------------|------|--------|------------|---------------|
| MT-01 | ... | ... | ... | hard | ... |

### Other
| ID | Trap Concept | Tool | Fields | Difficulty | Why It Matters |
|----|-------------|------|--------|------------|---------------|
| OT-01 | ... | ... | ... | ... | ... |

{Only include categories that have entries. Omit empty categories.}

---

## Summary of Work

| Suite | Action | New Scenarios | Updates |
|-------|--------|--------------|---------|
| ... | ... | ... | ... |
| **Total** | | **~N** | **~M** |

---

## Final Cleanup

Once ALL chunks are complete and committed, and the user has validated everything:

1. Run `/doc-suite-updater` one more time — it will enter Completion mode and archive this file
2. The worktree branch is now ready for the user to review and merge to main
```

## Scenario Conventions

Workers must follow these conventions when writing or updating scenario files. Read at least one existing suite in `.claude/skills/doc-regression/scenarios/` to internalize the patterns.

### Scenario file structure

```markdown
# {Tool Name} — Doc Regression Scenarios

Scenarios testing whether LLMs can construct correct `{tool_name}` payloads from tool documentation alone.

---

### Scenario N: Short descriptive name

**Prompt:**
> Natural language task request as an agent would receive it.

**Trap:** What makes this tricky (human-only, NEVER sent to model).

**Expected:** `tool_name`
```json
{ ... }
```

**Grading:**
- `items[0].field` MUST equal "value"
- `items[0].other` MUST NOT be present
- `items[0].field` SHOULD contain "text"

---
```

### Key conventions

- **Prompt** is conversational — written as a real user would speak to an agent. Never robotic or formulaic.
- **Trap** is human-only context — explains why this is tricky. NEVER included in the exam prompt sent to models.
- **Expected** shows the reference-correct payload.
- **Grading** uses three severity levels:
  - `MUST` — hard fail if not met
  - `MUST NOT` — hard fail if present
  - `SHOULD` — warning, not a fail
- For date fields, accept any reasonable timezone offset
- For fuzzy dates, check month and year, not exact day
- Multi-tool scenarios: Expected line says `tool_a then tool_b`, show both payloads
- Multiple valid approaches: list Option A / Option B, pass if ANY match
- Scenarios are numbered sequentially within each file
- Each scenario is separated by `---`

### What makes a good trap

The trap is the heart of each scenario. Good traps:
- Test a **genuine ambiguity** in the documentation, not an obscure edge case
- Reflect **real-world phrasing** — how would a user actually say this?
- Have a **clear right answer** derivable from the docs (if the docs are good)
- Catch **common model mistakes** — not contrived gotchas

Bad traps:
- Test knowledge that only comes from reading the code
- Are so obscure that no real user would encounter them
- Have ambiguous correct answers (if the docs genuinely don't specify, that's a doc issue to fix, not a scenario to write)

### Coverage cross-reference

The single most important gap-finding mechanism. Take the tool documentation inventory and check each field against existing scenarios. For every field with no scenario exercising it, consider whether a meaningful trap is possible. Not every field needs a scenario — `name` is straightforward, for instance — but every field with non-obvious semantics should have at least one.

Pay special attention to:
- **Cross-tool confusion**: fields that exist on multiple tools with different semantics (tags on add_tasks vs actions.tags on edit_tasks)
- **Patch semantics**: null vs omit vs value distinctions
- **Dependent fields**: fields that require other fields to be present
- **Mode-specific behavior**: same field behaving differently based on context (new rule vs existing rule)
