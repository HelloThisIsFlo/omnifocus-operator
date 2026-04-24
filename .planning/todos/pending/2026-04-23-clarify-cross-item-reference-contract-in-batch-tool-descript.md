---
created: 2026-04-23T22:16:52.837Z
updated: 2026-04-24
title: Promote cross-item name-ref to officially supported batch behaviour
area: server
files:
  - src/omnifocus_operator/agent_messages/descriptions.py (_BATCH_CROSS_ITEM_NOTE)
  - .planning/milestones/v1.4-phases/54-batch-processing/54-CONTEXT.md (BATCH-09 decision text)
  - tests/ (NEW unit/integration tests for batch cross-item name-ref + ambiguity edge cases)
  - .claude/skills/uat-regression/tests/batch-processing.md (Test 2i — aligned to observed reality; may tighten once supported-behaviour contract is locked)
---

## Problem

The `add_tasks` / `edit_tasks` tool descriptions overstate the "items are independent" limitation.

Current `_BATCH_CROSS_ITEM_NOTE` says:

> "Items are independent: batch items cannot reference other items created or edited in the same batch. For hierarchies (parent-child), use sequential calls."

**Observed reality (live-verified 2026-04-23 during Chunk 6 UAT-suite-updater self-verification):** because items are processed serially and name resolution runs per-item at execution time (after prior items commit), a later item CAN successfully reference an earlier item **by name** — as long as the name resolves uniquely. Only **ID-refs** genuinely don't work (the ID doesn't exist yet in the response).

Proof:
```json
{"items": [
  {"name": "UAT-A7-StringRef-Parent"},
  {"name": "UAT-A7-StringRef-Child", "parent": "UAT-A7-StringRef-Parent"}
]}
```
Both items succeeded and the child was parented under the just-created sibling (verified via `get_task` — `parent.task.id` matched item 1's returned id).

**Original rationale** (Flo, on discovery): "Originally I put this as a requirement that they cannot reference each other for a simplicity reason — I didn't want to add a temporary ID system. If the name is specific enough, I didn't even think of it."

## Framing

Not documentation drift — **contract promotion**. The implementation already supports cross-item name-refs via per-item serial resolution; we want to codify this as an officially supported batch behaviour with test coverage that protects it from regression. The runtime change is minimal (the behaviour already works); the deliverable is the contract + tests + docs.

## Solution

### 1. Tool description rewrite

Rewrite `_BATCH_CROSS_ITEM_NOTE` so agents understand the real contract:

1. **ID-refs NOT supported** — the ID doesn't exist until the creating item commits, and response IDs aren't propagated back into the batch input.
2. **Name-refs ARE supported** when the name resolves uniquely — serial execution + per-item name resolution makes this work. Use this for creating hierarchies in one batch.
3. **Ambiguity rule** — if a referenced name collides with any other task (inside or outside the batch), the standard ambiguous-name error applies and the referencing item is skipped (or errored, per the tool's batch fail-mode).
4. **Recommendation**: prefer unique-enough names for hierarchies; fall back to sequential calls if collisions with existing tasks are likely.

### 2. New unit / integration tests (InMemoryBridge or SimulatorBridge)

Happy path:
- **Batch hierarchy via name-ref** — 2-item batch creates parent then child referencing parent by name; assert child's `parent.task.id == parent_item.id` in the response.
- **Multi-level hierarchy** — 3-item batch (grandparent → parent → child), all by name. Assert full chain stitches correctly.
- **Multiple children** — 3-item batch (parent + two children both referencing the parent by name). Assert both children parented under the created parent.

Edge cases:
- **Ambiguous name (collision with existing task)** — pre-existing task `"Alpha"` in the DB; batch is `[{name: "Alpha"}, {name: "Child", parent: "Alpha"}]`. Expected: child resolves ambiguously → item 2 skipped (`add_tasks` best-effort) with a proper ambiguous-name error referencing the two candidates. Item 1 still succeeds.
- **Ambiguous name (collision inside the batch)** — batch creates two identically-named parents before the child: `[{name: "Alpha"}, {name: "Alpha"}, {name: "Child", parent: "Alpha"}]`. Expected: child's resolution sees two candidates (both batch-created), same ambiguity error, item 3 skipped.
- **Unresolvable name (typo / no match)** — `[{name: "Parent"}, {name: "Child", parent: "PArnet"}]`. Expected: standard parent-not-found error on item 2, item 1 still succeeds.
- **ID-ref regression guard** — `[{name: "Parent"}, {name: "Child", parent: <id-that-doesnt-exist-yet>}]`. Expected: ID-refs to in-batch items still fail (this is the contract boundary we're preserving — document why).
- **Edit-side counterpart (if applicable)** — `edit_tasks` batch where one item moves another just-edited task's child by name-ref. Edit-side is fail-fast, so the sequential-commit semantics are load-bearing here too; needs at least one test.
- **Order matters (child before parent)** — child item appears earlier in the batch array than the parent it references: e.g. `[{name: "Child", parent: "Parent"}, {name: "Parent"}]`. Expected behaviour TBD during implementation (likely parent-not-found or resolves to pre-existing task if name collides externally) — discuss when the tests are written. Point of the test: document the "sequence matters" contract explicitly so agents don't assume order-independence.

Test placement TBD during execution — likely alongside existing batch-processing test module in `tests/` (mirror wherever Phase 54's pipeline/service tests live). **Never touch** `RealBridge` per SAFE-01.

### 3. Context doc follow-up

`.planning/milestones/v1.4-phases/54-batch-processing/54-CONTEXT.md` — BATCH-09 decision text framed cross-item refs as "not supported, use sequential calls." Add a follow-up note: "Post-ship clarification (2026-04-24): name-refs are a supported sub-case; ID-refs remain unsupported. See this todo's deliverables for the tested contract."

### 4. UAT suite tightening

`.claude/skills/uat-regression/tests/batch-processing.md` Test 2i — already updated during Chunk 6 to match observed reality. Once the automated tests + tool doc are in place, consider adding a UAT scenario for the ambiguous-collision case (complements the automated coverage with a real-OmniFocus run).

### 5. Related artifact

The README schema examples (lines 115-142) were concurrently fixed to match the current string-based parent/actions schema — unrelated to this todo but worth mentioning since it was part of the same Chunk 6 cleanup pass.

## Why expanded

Original todo framed this as doc-only ("suite and README already reflect reality"). Re-scoping to promote the behaviour to an officially supported contract with tests — because:
- Agents are currently being told "don't do this" about something that works well and saves them a round-trip
- Encoding it with tests makes the contract load-bearing (can't silently regress)
- Ambiguity edge cases especially need tests; the behaviour of "skip on ambiguity" is currently observed, not guaranteed
