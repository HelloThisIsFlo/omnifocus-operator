# Quick Task 260317-lgu: Fix D-6b: Suppress status warning when edit is a no-op - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Task Boundary

Fix D-6b: Suppress status warning when edit is a no-op. When `edit_tasks` receives a no-op field edit on a completed/dropped task, the status warning ("your changes were applied") should be suppressed and only the no-op warning ("No changes detected") should fire.

</domain>

<decisions>
## Implementation Decisions

### No-op priority logic
- When no-op is detected on a completed/dropped task, **replace** the status warning with the no-op warning entirely
- The status warning must not co-exist with the no-op warning — since no changes were applied, claiming "your changes were applied" is misleading
- Only the no-op warning (`EDIT_NO_CHANGES_DETECTED`) should be returned

### Test strategy
- **Update existing tests** (`test_stacked_warnings_completed_noop` and `test_stacked_warnings_dropped_noop`) to assert the corrected behavior
- **Rename tests and update docstrings/comments** — "stacked warnings" is no longer accurate since the no-op now takes priority rather than stacking
- Clean up any outdated comments that reference the old behavior

### Claude's Discretion
- None — both areas were discussed

</decisions>

<specifics>
## Specific Ideas

- The fix is in `service.py` Stage 5 (no-op detection, around line 367): when `is_noop` is true, clear the warnings list before adding `EDIT_NO_CHANGES_DETECTED`, or specifically remove the status warning
- Two test methods need updating: `test_stacked_warnings_completed_noop` (line 920) and `test_stacked_warnings_dropped_noop` (line 937)

</specifics>
