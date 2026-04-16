---
phase: 55-notes-graduation
reviewed: 2026-04-16T00:00:00Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - src/omnifocus_operator/agent_messages/descriptions.py
  - src/omnifocus_operator/agent_messages/errors.py
  - src/omnifocus_operator/agent_messages/warnings.py
  - src/omnifocus_operator/contracts/shared/actions.py
  - src/omnifocus_operator/contracts/use_cases/edit/tasks.py
  - src/omnifocus_operator/service/domain.py
  - src/omnifocus_operator/service/payload.py
  - src/omnifocus_operator/service/service.py
  - tests/test_contracts_type_aliases.py
  - tests/test_models.py
  - tests/test_output_schema.py
  - tests/test_service.py
  - tests/test_service_domain.py
  - tests/test_service_payload.py
findings:
  critical: 0
  warning: 0
  info: 3
  total: 3
status: issues_found
---

# Phase 55: Code Review Report

**Reviewed:** 2026-04-16
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found (info only — no bugs, no security issues)

## Summary

Phase 55 graduates the `note` field on `EditTaskCommand` from a top-level setter to an `actions.note` action block, mirroring the existing `TagAction` precedent. The implementation is clean, consistent with project conventions, and well-tested.

Key correctness verifications:

- **`NoteAction` @model_validator correctly rejects `{}`, `{append, replace}`, and `{append: None}`** — confirmed in `contracts/shared/actions.py:77-87` and `TestNoteAction` (4 tests in `test_service_domain.py:659-691`). The `{append: None}` case is caught by `Patch[str]` type machinery before `_validate_incompatible_note_edit_modes` runs, per D-02.
- **`process_note_action` 14-branch decision tree** — complete coverage in `TestProcessNoteAction` (15 tests, `test_service_domain.py:2446-2648`), including the important N3-beats-N2 ordering (branch 13, line 2623).
- **Pipeline integration** — `_apply_note_action` sits between `_apply_move` and `_build_payload` (`service.py:680-682`), and `self._note_warns` is aggregated into `_all_warnings` alongside `_lifecycle_warns`, `_status_warns`, `_repetition_warns`, `_tag_warns` (`service.py:971-978`). Consistent with other action warning flows.
- **`note_value: str | _Unset = UNSET` kwarg on `build_edit`** — correctly keyword-only, and only adds `note` to payload kwargs when `is_set(note_value)` (`payload.py:82-83`). UNSET path ensures N1/N2/N3 no-ops don't appear in `payload.model_fields_set`, which is what `_is_empty_edit` keys off.
- **`EditTaskCommand` JSON schema no longer has top-level `note`** — verified by `test_edit_task_command_has_no_top_level_note` (`test_output_schema.py:685-694`) and `test_edit_command_schema_nullable_fields` (`test_models.py:1162-1168`).
- **`AddTaskCommand.note` still top-level** — NOTE-05 boundary preserved (`add/tasks.py:81`, `payload.py:56-57`).
- **No stale references to `NOTE_EDIT_COMMAND`** — grep confirms 0 matches in `src/` and `tests/` (only planning artifacts).
- **`DomainLogic.normalize_clear_intents` dead `command.note` branch removed** — method now only handles `tags.replace` normalization (`domain.py:477-493`).
- **`EDIT_TASKS_TOOL_DOC` byte size: 2004 bytes** — within DESC-08 2048-byte limit.
- **SAFE-01/SAFE-02 compliance** — no `RealBridge` literal references introduced; docstrings continue to use "the real Bridge" idiom where needed.

No Critical or Warning findings. Three Info items covering minor code-style inconsistencies and defensive-dead-code opportunities.

## Info

### IN-01: `_apply_note_action` inconsistent with sibling `_apply_*` methods

**File:** `src/omnifocus_operator/service/service.py:947-954`
**Issue:** `_resolve_actions` assigns `self._note_action` (line 725), matching the pattern used for `self._lifecycle_action`, `self._tag_actions`, `self._move_action`. Every sibling `_apply_*` method short-circuits on `if self._<action>_action is None: return` (see `_apply_lifecycle` line 730, `_apply_tag_diff` line 926, `_apply_move` line 940). `_apply_note_action` does NOT use `self._note_action` at all — it passes `self._command` directly to `process_note_action`, which re-derives the action from `command.actions.note`. It works correctly because `process_note_action` handles the "no action" case internally (`domain.py:552-556`), but the asymmetry is a readability speed-bump for future maintainers who have to check whether the `self._note_action` assignment is load-bearing (it isn't).
**Fix:** Either (a) short-circuit for consistency:
```python
def _apply_note_action(self) -> None:
    self._note_value: str | _Unset = UNSET
    self._note_warns: list[str] = []
    if self._note_action is None:
        return
    value, _skip, self._note_warns = self._domain.process_note_action(
        self._command,
        self._task,
    )
    self._note_value = value
```
Or (b) change `process_note_action`'s signature to take `note_action: NoteAction` + `task: Task` (instead of the whole `command`), and drop the redundant `self._note_action` assignment from `_resolve_actions`. Option (b) is a cleaner domain contract (the domain method shouldn't need to know about `EditTaskCommand`), but is a slightly bigger refactor.

### IN-02: `_skip` return value from `process_note_action` is structurally redundant with UNSET sentinel

**File:** `src/omnifocus_operator/service/domain.py:531-591`, `src/omnifocus_operator/service/service.py:950`
**Issue:** `process_note_action` returns `(str | _Unset, bool, list[str])`. In every code path, `value is UNSET` iff `should_skip_bridge is True` (UNSET branch at line 553 returns `True`; UNSET branch at line 556 returns `True`; N1 at line 568 returns `True`; N2 at line 588 returns `True`; N3 at line 583 returns `True`; all non-UNSET returns pass `False`). The caller `_apply_note_action` assigns `_skip` (with underscore prefix indicating unused) and never reads it (`service.py:950`). This is a minor API-surface redundancy: consumers already infer skip from `isinstance(value, _Unset)`, and carrying both in the tuple invites divergence if future branches accidentally desync them.
**Fix:** Consider returning `(str | _Unset, list[str])` — a 2-tuple. Drop `_skip` from the return signature, update the docstring, and let callers use `isinstance(value, _Unset)` or `is_set(value)` for the skip check. This also aligns with `process_lifecycle` which returns `(bool, list[str])` where the bool IS the primary signal (not a derived tautology of the value).

### IN-03: Defensive dead code in `_all_fields_match` note comparison

**File:** `src/omnifocus_operator/service/domain.py:1088-1109` (specifically line 1090 and the loop at 1102-1109 for `note`)
**Issue:** With Phase 55's architecture, the `note` comparison in `_all_fields_match` is structurally unreachable as a no-op detector:
- `process_note_action` already returns UNSET for identical-content cases (N2) and clear-on-empty cases (N3), meaning `note` will not be in `payload.model_fields_set` for no-op scenarios.
- When `process_note_action` returns a non-UNSET value, that value is guaranteed to differ from `task.note` (append always prepends with `\n\n` separator or replaces empty; replace only reaches non-UNSET path when content differs).

The field_comparisons entry `"note": task.note` (line 1090) and its iteration (line 1102-1109) can never contribute a `False` return — the check is dead. This is defensive and harmless; leaving it prevents a latent bug if the note pipeline is ever refactored to allow identical-note values to reach `build_edit`. But it's worth a short comment or an assertion so future readers don't assume this is a load-bearing check.
**Fix:** Add a one-line comment above line 1090 noting that note no-ops are caught upstream in `process_note_action` and this comparison is defensive belt-and-suspenders. Alternatively, an assertion:
```python
# Defensive: process_note_action already filters note no-ops (N1/N2/N3).
# This comparison only fires if that contract is broken.
```

---

_Reviewed: 2026-04-16_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
