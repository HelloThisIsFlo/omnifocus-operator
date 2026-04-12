---
phase: 52-same-container-move-fix
reviewed: 2026-04-12T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - src/omnifocus_operator/contracts/protocols.py
  - src/omnifocus_operator/repository/hybrid/hybrid.py
  - src/omnifocus_operator/repository/bridge_only/bridge_only.py
  - src/omnifocus_operator/service/domain.py
  - src/omnifocus_operator/agent_messages/warnings.py
  - tests/test_service_domain.py
  - tests/test_service.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 52: Code Review Report

**Reviewed:** 2026-04-12
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Phase 52 introduces the same-container move fix: `beginning`/`ending` moves to a container the task already belongs to are now detected as no-ops via the `anchor_id == task_id` invariant (D-12/D-13), rather than being silently executed by OmniFocus as a no-op without returning an error. The core logic is in `_all_fields_match` (domain.py) and the translation in `_process_container_move` (domain.py). Supporting tests land in both `test_service_domain.py` and `test_service.py`.

The feature itself is logically sound. Three warnings and two info items are noted below; none are blocking unless WR-02 turns out to be reachable in practice.

---

## Warnings

### WR-01: `_warn_already_on` / `_warn_not_on` silently drop warnings when resolved_ids list is shorter than input_names

**File:** `src/omnifocus_operator/service/domain.py:682-700`

**Issue:** Both `_warn_already_on` and `_warn_not_on` use the guard `if i < len(resolved_ids)`, so if the resolver returns fewer IDs than input names (e.g. duplicate tag names collapse to one ID, or a resolver implementation returns a short list), warnings for the trailing input names are silently dropped. This is not introduced by phase 52, but the invariant isn't documented and a future resolver change could quietly suppress warnings.

```python
for i, name in enumerate(input_names):
    if i < len(resolved_ids) and resolved_ids[i] in current_ids:  # silent skip if len mismatch
```

**Fix:** Add an assertion or raise at the call site if `len(resolved_ids) != len(input_names)`, or document the invariant explicitly. The callers (`_apply_add`, `_apply_remove`, `_apply_add_remove`) all call `resolve_tags` which is expected to return one ID per input, so the contract can be codified:

```python
assert len(resolved_ids) == len(input_names), (
    f"resolve_tags must return one ID per input; "
    f"got {len(resolved_ids)} for {len(input_names)} inputs"
)
```

---

### WR-02: `_process_container_move` cycle check fires before edge-child lookup — task can still be its own edge child

**File:** `src/omnifocus_operator/service/domain.py:788-800`

**Issue:** The cycle check (`check_cycle`) only runs when the target container is a task (line 789–791), and it raises before the edge-child lookup. However, the cycle check walks the ancestor chain and terminates when `t.parent.task is None` (line 729–731) — it does not explicitly handle the case where the task being moved _is_ the only child of the container and would therefore be returned as the edge child. In that case the translation produces `anchor_id == task_id`, which is correctly caught as a no-op by `_all_fields_match`. So the existing no-op path handles this correctly for the same-container scenario. The concern is narrower: if `check_cycle` is the *only* guard before the edge-child lookup and OmniFocus's data model can produce a task whose ancestor chain terminates at a non-task (project) container before `task_id` is encountered, a cross-project cycle might theoretically bypass the check. This is a documentation gap more than a confirmed bug, but worth verifying.

**Fix:** Add a comment documenting the invariant:

```python
# check_cycle terminates at project-level parents (t.parent.task is None),
# so it correctly guards against task-under-task cycles.
# Cross-container cycles (task A moved to project B that contains A's ancestor)
# are structurally impossible: OmniFocus does not allow project nesting.
```

---

### WR-03: `_all_fields_match` ignores `move_to` when `move.position` is `"before"` or `"after"` and `anchor_id` is None

**File:** `src/omnifocus_operator/service/domain.py:940-943`

**Issue:** Lines 940–943 contain the comment "Direct before/after without anchor_id should not happen after translation, but if it does, we can't detect no-op" and return `False` (not a no-op). However, the method's invariant isn't enforced — if a `MoveToRepoPayload` is ever constructed with `position="before"/"after"` and `anchor_id=None`, the edit proceeds to the bridge silently. The comment acknowledges this but doesn't assert or log.

```python
else:
    # Direct before/after without anchor_id should not happen after translation,
    # but if it does, we can't detect no-op
    return False
```

**Fix:** Either add an assertion that this branch is unreachable (to catch bugs early), or add a `logger.warning` so the anomaly surfaces in logs:

```python
else:
    # This branch should be unreachable after translation.
    logger.warning(
        "_all_fields_match: unexpected before/after move with no anchor_id "
        "(payload.id=%s); cannot detect no-op, proceeding",
        payload.id,
    )
    return False
```

---

## Info

### IN-01: `MOVE_ALREADY_AT_POSITION` warning constant is defined after all other warning groups

**File:** `src/omnifocus_operator/agent_messages/warnings.py:193-195`

**Issue:** `MOVE_ALREADY_AT_POSITION` is placed at the bottom of the file, after the availability filter constants and after `FILTER_DID_YOU_MEAN`, which breaks the topical grouping pattern used throughout the file. All other edit-related constants are in the `--- Edit ---` block at the top.

**Fix:** Move `MOVE_ALREADY_AT_POSITION` to the `--- Edit: No-op ---` section (after `EDIT_NO_CHANGES_DETECTED`, around line 26) to keep the file scannable by domain.

---

### IN-02: `_read_edge_child_id` (hybrid.py) uses string interpolation for `ORDER` direction instead of a mapping

**File:** `src/omnifocus_operator/repository/hybrid/hybrid.py:1138,1151,1158`

**Issue:** The SQL `ORDER BY rank {order}` injects the `order` variable via f-string. The variable is derived from `edge == "first"` so it can only be `"ASC"` or `"DESC"`, making SQL injection impossible here. However, the pattern looks unsafe at a glance and a reviewer or future maintainer may not realize it's safe. The `bridge_only.py` implementation (line 373) uses array indexing `children[0]` / `children[-1]` which doesn't have this appearance.

**Fix:** Replace with an explicit mapping to make the safety obvious:

```python
_ORDER = {"first": "ASC", "last": "DESC"}
order = _ORDER[edge]  # KeyError if invalid, not silent injection
```

---

_Reviewed: 2026-04-12_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
