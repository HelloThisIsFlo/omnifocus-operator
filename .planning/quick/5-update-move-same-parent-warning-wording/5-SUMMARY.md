# Quick Task 5: Update move same-parent warning wording

**Status:** Complete

## What changed

Updated the move same-parent warning in `src/omnifocus_operator/service.py:291-295`.

**Before:**
> Task is already a child of this parent. Note: this check verifies the container, not ordinal position (first vs last child).

**After:**
> Task is already a child of this parent. The move was applied, but the server cannot yet confirm whether the task's position within the parent changed.

## Tests

All 15 move-related tests pass. Test assertions use substring matching on `"already a child of this parent"` so no test changes needed.
