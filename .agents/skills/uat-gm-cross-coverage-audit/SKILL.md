---
name: uat-gm-cross-coverage-audit
description: Audit coverage gaps between golden master contract tests and UAT regression suites. Use when the user says "audit test coverage", "cross-reference tests", "reconcile UAT and golden master", "coverage gaps", "test coverage audit", "what's missing from UAT", "what's missing from golden master", "GM vs UAT", "bridge coverage", or wants to find untested behaviors across test systems.
---

# Test Coverage Audit

Bidirectional coverage audit between the golden master (GM) contract tests and the UAT regression suites. Finds behaviors that could silently diverge because neither system asserts on them.

## When to use

- After adding GM scenarios — check if UAT covers the new behaviors
- After adding UAT suites — check if GM captures the bridge operations
- Periodic health check — are the two systems drifting apart?
- After modifying `normalize.py` strip lists — did we start/stop comparing something?

## Layer distinction — critical context

The two test systems operate at **different layers** and overlap only partially:

| System | Layer | Tests via | Scope |
|--------|-------|-----------|-------|
| **Golden Master** | Bridge | `InMemoryBridge` vs `RealBridge` snapshots | Bridge operations: `add_task`, `edit_task`, `move_task`, `add_tag_ids`, `remove_tag_ids`, `complete`, `drop`, `reopen`. Field-level fidelity of InMemoryBridge. |
| **UAT Regression** | MCP Tool | MCP tools via live OmniFocus | Agent-facing behavior: `add_tasks`, `edit_tasks`, `get_task`, `get_all`. Includes service-layer logic (tag resolution, no-op detection, warnings, validation, batch limits, circular ref checks). |

**Overlap zone:** Bridge operations that both systems exercise (add, edit, move, tags, lifecycle).
**GM-only:** Field-level snapshot fidelity, InMemoryBridge faithful reproduction.
**UAT-only:** Service-layer logic, warning text, validation errors, agent UX.

## What counts as a gap

### GM gap
A bridge operation that InMemoryBridge should faithfully reproduce but no GM scenario captures.

**The test:** "Could InMemoryBridge silently diverge here and no contract test would catch it?"

Examples: a field transition not exercised (e.g., setting `estimatedMinutes` then clearing it), a lifecycle edge case (drop a repeating task), a tag operation variant (remove last tag).

### UAT gap
A behavioral state or field value the GM captures that UAT doesn't verify from the agent's perspective.

**The test:** "Could an agent rely on this field/behavior and get a wrong answer, even though GM would catch a bridge divergence?"

Examples: GM verifies `completionDate` is set after complete, but UAT never checks the date field in `get_task` response. GM exercises inheritance, but UAT has no tests for inherited dates showing up correctly.

### NOT a gap (false positives)
- Service-layer logic that the GM should NOT test: tag resolution by name, no-op detection, warnings, validation errors, batch limits, circular ref detection — these are UAT-only concerns
- Fields already compared by GM contract tests (check `state_after` snapshots + `normalize.py`)
- Fields in `normalize.py` strip lists that are intentionally not compared
- **Combinatorial completeness concerns:** If a gap applies equally to N other fields/operations that also aren't tested (e.g., "tags survive move" is no different from "notes survive move" or "estimatedMinutes survive move"), it's a combinatorial completeness concern, not a specific gap. Classify as nice-to-have unless there's a reason this particular combination is more fragile than the others (e.g., tags use a different storage mechanism, or there's a known bug history).

## Workflow

### Phase 1 — Scoping

Ask the user **two questions** (no more):

1. **Scope:** Full audit or focused area? (e.g., "just lifecycle", "just tag operations", "everything") — "full" includes all domains including inheritance.
2. **Strictness:** Strict first pass (only obvious, high-confidence gaps) or broad (include nice-to-haves)?

Defaults if user says "just run it": full scope, strict first pass.

### Phase 2 — Parallel analysis

Launch **2 parallel subagents** (use Agent tool):

#### Agent 1: GM → UAT direction
**Task:** For each GM scenario, check if UAT exercises the same behavior from the agent's perspective.

Instructions for agent:
1. Read all GM scenario folders in `tests/golden_master/snapshots/` — each numbered folder has an `actions.json` (what was done) and `state_after.json` (resulting state)
2. Read all UAT suite files in `.claude/skills/uat-regression/tests/*.md`
3. For each GM scenario, ask: "Does any UAT test exercise this same operation and verify the result?"
4. A GM scenario is "covered" if a UAT test triggers the same bridge operation AND checks the relevant output fields
5. A GM scenario is "partially covered" if a UAT test triggers the operation but doesn't check key fields that GM verifies
6. A GM scenario is "uncovered" if no UAT test exercises this operation at all
7. **Don't treat UAT infrastructure limitations as hard walls.** UAT runs against live OmniFocus with a human operator — manual precondition steps (e.g., "first create a project with these properties") are valid. A gap is only "untestable in UAT" if it requires something truly impossible, not just a manual setup step.
8. Output a structured table: `| GM Scenario | Operation | UAT Coverage | Gap Description |`

#### Agent 2: UAT → GM direction
**Task:** For each UAT test that exercises bridge-level behavior, check if a GM scenario captures it.

Instructions for agent:
1. Read all UAT suite files in `.claude/skills/uat-regression/tests/*.md`
2. Read all GM scenario folders in `tests/golden_master/snapshots/`
3. Read `tests/golden_master/normalize.py` to understand what GM compares vs strips
4. For each UAT test, determine if it exercises a bridge-level operation (vs pure service-layer logic)
5. For bridge-level UAT tests, ask: "Is there a GM scenario that would catch InMemoryBridge diverging on this behavior?"
6. **Filter out service-layer-only tests** — these are NOT gaps. Service-layer behaviors include:
   - Tag resolution by name (bridge uses IDs only)
   - No-op detection and warnings
   - Validation errors (batch limits, invalid fields, circular refs)
   - `setTagIds` decomposition into add/remove (bridge has `addTagIds`/`removeTagIds`, not `setTagIds`)
   - Warning text and agent guidance
7. Output a structured table: `| UAT Test | Bridge Operation | GM Coverage | Gap Description |`

### Phase 3 — Synthesize and validate

After both agents return:

1. **Merge results** into a single gap list, deduplicating overlaps
2. **False positive check** for each gap:
   - If a field is flagged as a GM gap: check if it's already in `state_after` snapshots AND not in `normalize.py` strip lists (VOLATILE, UNCOMPUTED, PRESENCE_CHECK). If it IS already compared, it's not a gap.
   - If an operation is flagged as a UAT gap: check if it's purely service-layer behavior. If yes, remove it.
   - If a transition is flagged: check if it's a combination of existing scenarios that would implicitly catch divergence.
3. **Categorize** remaining gaps by **risk**, not actionability:
   - **High:** There's a specific mechanism by which this could break (e.g., a code path that handles this case differently, a known fragile area, a storage mechanism that diverges from the norm)
   - **Medium:** Theoretically possible divergence but no known mechanism — the gap is real but the risk is speculative
   - **Low / nice-to-have:** Combinatorial completeness, marginal coverage improvement, no specific risk mechanism

### Phase 4 — Report

Write the report to `.sandbox/test-coverage-audit-<YYYY-MM-DD>.md` with this structure:

```markdown
# Test Coverage Audit — <date>

## Scope
- Areas audited: ...
- Strictness: strict/broad

## Summary
- GM scenarios analyzed: N
- UAT tests analyzed: N
- Gaps found: N (X high, Y medium, Z low)
- False positives filtered: N

## GM → UAT Gaps (GM captures it, UAT doesn't verify it)

### High Confidence
| # | GM Scenario | Operation | What's Missing in UAT | Suggested Fix |
|---|-------------|-----------|----------------------|---------------|

### Medium Confidence
...

### Low Confidence / Nice-to-Have
...

## UAT → GM Gaps (UAT exercises it, GM doesn't capture it)

### High Confidence
| # | UAT Test | Bridge Operation | What's Missing in GM | Suggested Fix |
|---|----------|-----------------|---------------------|---------------|

### Medium Confidence
...

### Low Confidence / Nice-to-Have
...

## False Positives Filtered
| # | Initially Flagged | Why It's Not a Gap |
|---|-------------------|--------------------|

## Recommended Actions
1. ...
```

Present the report to the user and wait for review.

### Phase 5 — Recommendations (after human review)

**This phase is gated on explicit user approval.** Never skip to recommendations.

The user will review the report and decide which gaps to lock in. For each approved gap, produce **structured recommendations** — do NOT directly edit UAT suites or GM scripts.

- **UAT gap → produce a description block** that the user can feed to the `uat-suite-updater` skill. Format it as a fenced code block containing: the test name, what it verifies, the MCP tool calls involved, preconditions (including manual setup steps if needed), and expected assertions. The user will copy-paste this into a `/uat-suite-updater` invocation.
- **GM gap → suggest capture script additions** for `uat/capture_golden_master.py`. Since there's no dedicated skill for GM edits, describe the scenario in enough detail that the user can decide how to implement it (or ask you to implement it directly).

The audit skill's job is analysis, not test authoring. Leave UAT suite writing to the dedicated skill.

## Lessons from first audit (2026-03-23)

These patterns were discovered during the first manual audit run. The skill encodes them so future runs don't rediscover them:

- **`setTagIds` doesn't exist at bridge level.** The bridge uses `addTagIds`/`removeTagIds`. The service layer decomposes `replace` into diff-based add/remove operations. When analyzing UAT tag tests, classify `setTagIds`-based tests as service-layer-only — they're not GM gaps.
- **GM `state_after` grows cumulatively.** Adding new scenarios means all subsequent snapshots grow to include new entities from prior scenarios. This is expected, not a bug — don't flag "extra entities in state_after" as issues.
- **Many "gaps" are false positives.** Fields like `inInbox`, `hasChildren`, `project` are already in GM `state_after` and compared by contract tests. A field existing in GM snapshots ≠ a gap. The gap is when UAT doesn't assert the field, or when no GM scenario exercises a specific *transition* of that field.
- **`normalize.py` strip lists are the source of truth** for what GM compares. VOLATILE fields are stripped entirely, UNCOMPUTED fields are stripped, PRESENCE_CHECK fields use sentinels. Everything else is exact-matched. Always check these before flagging a field as unverified.
- **Two-pass approach works well.** First pass strict (only obvious gaps), second pass broad (nice-to-haves). User triage between passes. This matches the scoping question in Phase 1.

## File locations

| What | Where |
|------|-------|
| GM scenarios | `tests/golden_master/snapshots/` (numbered subfolders: `01-add`, `02-edit`, etc.) |
| GM normalization | `tests/golden_master/normalize.py` |
| GM capture script | `uat/capture_golden_master.py` |
| UAT suites | `.claude/skills/uat-regression/tests/*.md` |
| UAT skill | `.claude/skills/uat-regression/SKILL.md` |
| Bridge JS | `src/omnifocus_operator/bridge/bridge.js` |
| Report output | `.sandbox/test-coverage-audit-<date>.md` |
