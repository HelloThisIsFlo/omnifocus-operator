---
created: 2026-04-23T22:16:52.837Z
title: Clarify cross-item reference contract in batch tool descriptions
area: server
files:
  - src/omnifocus_operator/agent_messages/descriptions.py (_BATCH_CROSS_ITEM_NOTE)
  - .planning/milestones/v1.4-phases/54-batch-processing/54-CONTEXT.md (BATCH-09 decision text)
  - .claude/skills/uat-regression/tests/batch-processing.md (Test 2i — updated to match observed reality, may want another pass once tool doc is rewritten)
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

So this is **documentation drift**, not a bug to fix in code. The implementation already supports name-refs via per-item serial resolution; the public contract just under-sells what's possible.

## Solution

Rewrite `_BATCH_CROSS_ITEM_NOTE` so agents understand the real contract:

1. **ID-refs NOT supported** — the ID doesn't exist until the creating item commits, and response IDs aren't propagated back into the batch input.
2. **Name-refs ARE supported** when the name resolves uniquely in the OmniFocus database — serial execution + per-item name resolution makes this work.
3. **Recommendation**: prefer unique-enough names for hierarchies; fall back to sequential calls if name collisions with existing tasks are likely.

Likely surfaces to touch:
- `_BATCH_CROSS_ITEM_NOTE` constant in `src/omnifocus_operator/agent_messages/descriptions.py` (primary)
- Both `add_tasks` and `edit_tasks` tool description assemblies (they both include this note)
- `.planning/milestones/v1.4-phases/54-batch-processing/54-CONTEXT.md` — BATCH-09 decision text may need a follow-up note
- UAT regression suite `.claude/skills/uat-regression/tests/batch-processing.md` Test 2i — has been updated to match observed reality; can be tightened once tool doc is rewritten

Related artifact: the README schema examples (lines 115-142) were concurrently fixed to match the current string-based parent/actions schema, separate from this drift.

Not urgent — suite and README already reflect reality. This todo closes the loop on the public tool contract.
