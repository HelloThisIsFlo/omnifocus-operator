---
phase: 52-same-container-move-fix
verified: 2026-04-12T17:00:00Z
status: passed
score: 9/9 must-haves verified
overrides_applied: 0
---

# Phase 52: Same-Container Move Fix Verification Report

**Phase Goal:** `moveTo beginning/ending` reliably reorders tasks even when already in the target container, with accurate no-op warnings
**Verified:** 2026-04-12
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                                                       | Status     | Evidence                                                                                                                                       |
|----|-----------------------------------------------------------------------------------------------------------------------------|------------|------------------------------------------------------------------------------------------------------------------------------------------------|
| 1  | `moveTo beginning` on the same container moves the task to first position (not silently ignored)                            | ✓ VERIFIED | `_process_container_move` calls `get_edge_child_id(effective_parent_id, "first")` and returns `{"position": "before", "anchor_id": first_child}` — OmniFocus bridge receives moveBefore, not the silent-no-op beginning |
| 2  | `moveTo ending` on the same container moves the task to last position (not silently ignored)                                | ✓ VERIFIED | Same translation path: `get_edge_child_id(effective_parent_id, "last")` -> `{"position": "after", "anchor_id": last_child}`                   |
| 3  | Moving to a different container via beginning/ending works as before (no regression)                                        | ✓ VERIFIED | Translation is unconditional (D-06 — no same-vs-different branching); full 2041-test suite passes                                              |
| 4  | Moving to an empty container works without translation (direct moveTo, no first/last child to reference)                   | ✓ VERIFIED | `get_edge_child_id` returns `None` for empty containers; code path returns `{"position": position, "container_id": resolved_id}` directly — tested by `test_move_beginning_empty_container_no_translation` and `test_move_ending_empty_container_no_translation` |
| 5  | The "same-container move not fully supported" warning is removed                                                            | ✓ VERIFIED | `MOVE_SAME_CONTAINER` is absent from all source files (`grep` on `src/` — no matches). Only present in historical planning docs. `MOVE_ALREADY_AT_POSITION` replaces it. |
| 6  | Moving the last child to "beginning" does NOT trigger a no-op warning (it would actually reorder)                          | ✓ VERIFIED | `get_edge_child_id("proj", "first")` returns the first child (not the last); last child anchor_id != task_id -> `_all_fields_match` returns `False`, no no-op. Tested by `test_anchor_id_different_from_task_id_not_noop`. |
| 7  | Moving the first child to "ending" does NOT trigger a no-op warning (it would actually reorder)                            | ✓ VERIFIED | Symmetric: `get_edge_child_id("proj", "last")` returns last child; first child anchor_id != task_id -> proceeds. Same test class covers this. |
| 8  | Moving the first child to "beginning" DOES trigger a no-op warning (already in position)                                   | ✓ VERIFIED | Translation: beginning -> before(first_child). If task IS first_child, anchor_id == task_id -> `_all_fields_match` appends `MOVE_ALREADY_AT_POSITION.format(position="beginning")`. Tested by `test_anchor_id_equals_task_id_beginning_is_noop`. |
| 9  | Moving the last child to "ending" DOES trigger a no-op warning (already in position)                                       | ✓ VERIFIED | Symmetric: ending -> after(last_child). If task IS last_child, anchor_id == task_id -> warning "already at the ending". Tested by `test_same_container_move_noop_detected` (integration) and `test_anchor_id_equals_task_id_ending_is_noop` (unit). |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact                                                          | Expected                                               | Status     | Details                                                                                                       |
|-------------------------------------------------------------------|--------------------------------------------------------|------------|---------------------------------------------------------------------------------------------------------------|
| `src/omnifocus_operator/contracts/protocols.py`                   | `get_edge_child_id` on Repository protocol             | ✓ VERIFIED | Lines 105-107: `async def get_edge_child_id(self, parent_id: str, edge: Literal["first", "last"]) -> str | None` |
| `src/omnifocus_operator/repository/hybrid/hybrid.py`              | SQL-based edge child lookup                            | ✓ VERIFIED | Lines 1135-1169: `_read_edge_child_id` uses `ORDER BY rank ASC/DESC LIMIT 1` with inbox-specific `WHERE parent IS NULL AND NOT EXISTS (SELECT 1 FROM ProjectInfo ...)` condition |
| `src/omnifocus_operator/repository/bridge_only/bridge_only.py`    | Snapshot-based edge child lookup                       | ✓ VERIFIED | Lines 351-373: Filters `get_all()` snapshot for direct children by parent_id, handles inbox via `SYSTEM_LOCATIONS["inbox"].id` |
| `src/omnifocus_operator/service/domain.py`                        | Translation logic in `_process_container_move`         | ✓ VERIFIED | Lines 762-803: Full translation logic with `effective_parent_id` and inbox-as-`$inbox` handling; import of `MOVE_ALREADY_AT_POSITION` at line 43 |
| `src/omnifocus_operator/agent_messages/warnings.py`               | `MOVE_ALREADY_AT_POSITION` present, `MOVE_SAME_CONTAINER` absent | ✓ VERIFIED | Lines 193-195: `MOVE_ALREADY_AT_POSITION` with `{position}` placeholder. `MOVE_SAME_CONTAINER` not in file. |

### Key Link Verification

| From                                    | To                                    | Via                                              | Status     | Details                                                                        |
|-----------------------------------------|---------------------------------------|--------------------------------------------------|------------|--------------------------------------------------------------------------------|
| `service/domain.py`                     | `contracts/protocols.py`              | `self._repo.get_edge_child_id()`                | ✓ WIRED    | Line 795: `edge_child_id = await self._repo.get_edge_child_id(effective_parent_id, edge)` |
| `service/domain.py`                     | `contracts/use_cases/edit/tasks.py`   | `anchor_id` in returned dict                    | ✓ WIRED    | Line 800: `return {"position": translated_position, "anchor_id": edge_child_id}` |
| `service/domain.py`                     | `agent_messages/warnings.py`          | `MOVE_ALREADY_AT_POSITION` import               | ✓ WIRED    | Line 43: imported; used at lines 926 and 939 with `.format(position=...)` |
| `service/domain.py` `_all_fields_match` | `contracts/use_cases/edit/tasks.py`   | `move.anchor_id != payload.id` check            | ✓ WIRED    | Lines 918-926: full anchor_id == task_id no-op detection for translated moves |

### Data-Flow Trace (Level 4)

Not applicable — this phase adds service layer translation logic and a repository lookup method, not rendering/UI components. The data flow is: agent request -> service -> `_process_container_move` -> `get_edge_child_id` (repo) -> translated MoveToRepoPayload -> bridge. This is plumbing, not data display.

### Behavioral Spot-Checks

| Behavior                                          | Check                                                                     | Result                | Status |
|---------------------------------------------------|---------------------------------------------------------------------------|-----------------------|--------|
| Full test suite passes (2041 tests)               | `uv run pytest tests/ -x -q`                                              | 2041 passed           | ✓ PASS |
| Mypy strict clean across 74 source files          | `uv run mypy src/omnifocus_operator/ --strict`                            | No issues             | ✓ PASS |
| `MOVE_SAME_CONTAINER` absent from source          | `grep -r MOVE_SAME_CONTAINER src/`                                        | No matches            | ✓ PASS |
| `MOVE_ALREADY_AT_POSITION` imported in domain.py  | Grep for import                                                           | Line 43 confirmed     | ✓ PASS |
| All 5 phase commits present in git log            | `git log --oneline` check of 9e03780c, d6bedd3c, b3feb9c7, 9d1c97c6, 07dbacbe | All 5 confirmed  | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description                                                              | Status      | Evidence                                                                                    |
|-------------|-------------|--------------------------------------------------------------------------|-------------|---------------------------------------------------------------------------------------------|
| MOVE-01     | 52-01       | `moveTo beginning` on same container reorders to first position           | ✓ SATISFIED | `_process_container_move` translates to `before(first_child)` via `get_edge_child_id`        |
| MOVE-02     | 52-01       | `moveTo ending` on same container reorders to last position               | ✓ SATISFIED | `_process_container_move` translates to `after(last_child)` via `get_edge_child_id`          |
| MOVE-03     | 52-01       | Service translates to `moveBefore`/`moveAfter` when target container has children | ✓ SATISFIED | Translation logic in `_process_container_move` lines 793-800                           |
| MOVE-04     | 52-01       | Move to empty container works without translation (direct `moveTo`)       | ✓ SATISFIED | `get_edge_child_id` returns `None` for empty containers; lines 802-803 return direct payload |
| MOVE-05     | 52-01       | Move to different container works as before (no regression)               | ✓ SATISFIED | Translation is unconditional (D-06); full 2041-test suite passes with no regressions        |
| MOVE-06     | 52-01, 52-02 | Remove the "same-container move not fully supported" warning             | ✓ SATISFIED | `MOVE_SAME_CONTAINER` absent from all source files; replaced by `MOVE_ALREADY_AT_POSITION`   |
| WARN-01     | 52-02       | No-op warning only fires when task is already in the requested position   | ✓ SATISFIED | `anchor_id == task_id` check in `_all_fields_match` lines 921-926; SC6/SC7 confirmed not triggered for non-edge children |
| WARN-02     | 52-01, 52-02 | "beginning" position check uses `MIN(rank)` among siblings              | ✓ SATISFIED | Hybrid SQL uses `ORDER BY rank ASC LIMIT 1` (line 1158); bridge-only uses `children[0]` by display order |
| WARN-03     | 52-01, 52-02 | "ending" position check uses `MAX(rank)` among siblings                 | ✓ SATISFIED | Hybrid SQL uses `ORDER BY rank DESC LIMIT 1` (line 1158); bridge-only uses `children[-1]` by display order |

**Coverage:** 9/9 requirements for Phase 52 satisfied. REQUIREMENTS.md shows all as "Pending" (document not updated post-execution, but codebase evidence confirms all are complete).

### Anti-Patterns Found

None detected. Scanned `domain.py`, `hybrid.py`, `bridge_only.py`, `warnings.py` for TODO/FIXME/placeholder patterns — all clean.

### Human Verification Required

None — all behavioral correctness is verifiable from code. The actual OmniFocus reordering (does the bridge call land correctly in the database) is UAT scope per SAFE-01/02, but the translation logic from service to bridge is fully covered by 2041 automated tests including dedicated integration tests for same-container no-op detection.

### Gaps Summary

No gaps. All 9 roadmap success criteria verified against actual codebase, all 9 requirements satisfied, full test suite green (2041 tests), mypy strict clean.

---

_Verified: 2026-04-12_
_Verifier: Claude (gsd-verifier)_
