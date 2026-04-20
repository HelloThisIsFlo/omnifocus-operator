---
phase: 56
scope: gaps-only
depth: quick
reviewed: 2026-04-20T00:00:00Z
plans_covered:
  - 56-08 (is_sequential hoist to ActionableEntity)
  - 56-09 (golden master scaffolding)
files_reviewed: 7
files_reviewed_list:
  - src/omnifocus_operator/models/common.py
  - src/omnifocus_operator/models/task.py
  - src/omnifocus_operator/service/domain.py
  - src/omnifocus_operator/service/service.py
  - src/omnifocus_operator/config.py
  - src/omnifocus_operator/agent_messages/descriptions.py
  - uat/capture_golden_master.py
findings:
  critical: 0
  high: 1
  medium: 0
  low: 0
  total: 1
status: issues_found
---

# Phase 56 Gap-Closure Review (Plans 56-08 and 56-09)

**Reviewed:** 2026-04-20
**Depth:** quick (pattern-matching + targeted reads)
**Scope:** Plans 56-08 and 56-09 only — not a re-review of 56-01..07
**Files Reviewed:** 7

## Summary

Plans 56-08 and 56-09 are cleanly implemented. The `is_sequential` hoist to `ActionableEntity` is single-source-of-truth, the enrichment method is defined once and called from all three project read paths, `PROJECT_DEFAULT_FIELDS` is correctly updated, tool docs reflect the cross-entity scope, and the `GOLDEN_MASTER_CAPTURE` env-var is fully purged from executable source. SAFE-01/02 compliance holds throughout: no test touches the real Bridge, and the capture script is human-only infrastructure unchanged in that regard.

One bug found: the retry loop inside `_check_leftover_tasks` in `uat/capture_golden_master.py` is missing the `known_task_ids` exclusion that the initial check already applies. When the human pre-seeds `GM-Phase56-Attached` and runs the script, the retry loop will permanently flag the preserved attached task as "still found", trapping the operator in an infinite loop they can only escape with Ctrl+C.

---

## High

### H-01: `_check_leftover_tasks` retry loop omits `known_task_ids` exclusion — infinite loop on first human capture run

**File:** `uat/capture_golden_master.py:2590`

**Issue:** The _initial_ leftover check (lines 2569-2572) correctly excludes both `known_project_ids` and `known_task_ids` from the "leftover" list. The retry loop that runs after the human cleans up OmniFocus (lines 2587-2591) only excludes `known_project_ids`. Because `GM_PHASE56_ATTACHED_TASK_ID` is registered in `known_task_ids` (and `_preserved_task_ids`) at line 2546, the initial check will never flag it — but if any other leftover tasks were present and the human deletes them, the retry loop will still see the pre-seeded attached task (prefixed `🧪 GM-`) and report `remaining` as non-empty. The human cannot proceed past the retry prompt without Ctrl+C.

```python
# CURRENT (line 2587-2591) — missing known_task_ids exclusion:
remaining = [
    t
    for t in state.get("tasks", [])
    if t.get("name", "").startswith(("GM-", "🧪 GM-")) and t["id"] not in known_project_ids
]

# FIX — mirror the same two-set exclusion as the initial check:
remaining = [
    t
    for t in state.get("tasks", [])
    if t.get("name", "").startswith(("GM-", "🧪 GM-"))
    and t["id"] not in known_project_ids
    and t["id"] not in known_task_ids
]
```

This is UAT-only infrastructure (`uat/` is excluded from CI and pytest discovery), so no automated test is at risk — but the bug will block the human on first capture.

---

## No medium or low findings

The following items were specifically checked and found clean:

- **Single-source-of-truth for `is_sequential`:** exactly one `Field(...)` declaration in `models/common.py:135`; zero Field declarations in `models/task.py` (only a cross-reference comment at line 45); `Project` inherits cleanly via `ActionableEntity` with no override.
- **`enrich_project_presence_flags` wiring:** 1 definition (`domain.py:339`) + 3 callsites (`service.py:154`, `service.py:175`, `service.py:546`) — all three project read paths covered.
- **`PROJECT_DEFAULT_FIELDS`:** `"isSequential"` present (`config.py:145`) alongside `hasNote`, `hasRepetition`, `hasAttachments`; correct comment attribution to Phase 56-08.
- **`IS_SEQUENTIAL_DESC`:** "Tasks-only." prefix removed (`descriptions.py:158`). `DEPENDS_ON_CHILDREN_DESC` still correctly carries the tasks-only qualifier (line 161).
- **`_PROJECT_BEHAVIORAL_FLAGS_NOTE`:** present at `descriptions.py:89-91`, covers `isSequential` only, as designed.
- **SAFE-01/02:** `GOLDEN_MASTER_CAPTURE` env var is fully absent from all executable source (`src/`, `tests/`, `uat/`, `conftest.py`) — only survives in historical planning docs. `RealBridge` usage in `uat/capture_golden_master.py` is pre-existing and appropriate; no new real-Bridge entry points introduced in plan 56-08 or 56-09.
- **Method Object convention:** no new pipeline class introduced; enrichment is inline inside `_ListProjectsPipeline._delegate` (service.py:542-548), mirroring `_ListTasksPipeline._delegate` exactly.
- **Pydantic model taxonomy:** no `@model_serializer` or `@field_serializer` added in models during these plans; `is_sequential` hoist is a plain field declaration. Output schema is not perturbed beyond the intended addition of `isSequential` to the Project schema.
- **No references to deleted artifacts:** `GOLDEN_MASTER_CAPTURE`, `test_task_property_surface_golden`, and `task_property_surface_baseline` produce zero matches in executable source.
- **Scenario coverage in `uat/capture_golden_master.py`:** all 8 scenarios are present under `09-task-property-surface/`; scenario 08 correctly chains `add_task` → `edit_task` via `params_fn` and `TASK_IDS[...]`. The `_phase_2b_phase56_setup` helper validates Inspector-only flags with a re-poll loop before proceeding.

---

_Reviewed: 2026-04-20_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: quick_
