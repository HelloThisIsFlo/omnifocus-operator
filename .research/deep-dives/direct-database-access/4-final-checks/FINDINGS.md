# Final Check Findings: SQLite Field Coverage Verification

**Date:** 2026-03-06 (initial), 2026-03-07 (OmniJS cross-check verified)
**Status:** Complete — all 6 failures verified and resolved

---

## Abstract

Verified every field in the proposed Pydantic model against the actual OmniFocus SQLite schema. **46 of 52 fields map directly.** The 6 failures have all been **verified via OmniJS cross-check** — 5 are solvable from SQLite with corrected column mappings, 1 (`shouldUseFloatingTimeZone`) requires the OmniJS bridge.

**Bottom line:** 51/52 fields readable from SQLite. Only `shouldUseFloatingTimeZone` requires the bridge.

---

## Results: 46/52 PASS

### Passing entities (no issues)

- **OmniFocusEntity** (base): 5/5 — `persistentIdentifier`, `name`, `dateAdded`, `dateModified`, URL constructed from ID
- **ActionableEntity (status)**: 4/4 — `overdue`, `dueSoon`, `blocked`, `dateCompleted` all present
- **ActionableEntity (relationships)**: 5/5 — `TaskToTag` join works, all 4 RepetitionRule fields present: `repetitionRuleString`, `repetitionScheduleTypeString`, `repetitionAnchorDateKey` (`dateDue`/`dateToStart`), `catchUpAutomatically` (0/1)
- **Task**: 3/3 — `inInbox`, `containingProjectInfo`, `parent` all present
- **Project**: 5/5 — `lastReviewDate`, `nextReviewDate`, `reviewRepetitionString`, `nextTask`, `folder` all present

### 6 Failed fields and resolutions

| Field | Expected Column | Actual Situation | Resolution | Verified |
|---|---|---|---|---|
| `drop_date` | `Task.dateDropped` | Column doesn't exist | **`Task.dateHidden`** = drop date. All tasks with `dateHidden` set confirmed as `taskStatus: Dropped` via OmniJS | ✅ |
| `effective_drop_date` | `Task.effectiveDateDropped` | Column doesn't exist | **`Task.effectiveDateHidden`** = effective drop date. Tasks in dropped projects inherit via this column (own `dateHidden` stays NULL) | ✅ |
| `should_use_floating_time_zone` | `Task.shouldUseFloatingTimeZone` | Column doesn't exist, no similar column found | **Bridge-only.** Property exists on tasks (returns `true`/`false`), but has no SQLite column. Must read via OmniJS bridge | ✅ |
| `Tag.status` | `Context.active` | Column doesn't exist | **`allowsNextAction`**: `0` = OnHold, `1` = Active. Dropped tags use `dateHidden` (same pattern as tasks) | ✅ |
| `Folder.status` | `Folder.active` | Column doesn't exist | **`Folder.dateHidden`**: NULL = Active, non-NULL = Dropped. Confirmed via OmniJS `folder.status` | ✅ |
| `Perspective.name` | `Perspective.name` | Column doesn't exist | **Parse from `Perspective.valueData`** plist blob — `name` key present in all 50 perspectives. Verified names match OmniFocus | ✅ |

---

## Key Observations

### Column name corrections (vs. initial assumptions)

- `repetitionMethodString` is actually `repetitionScheduleTypeString`
- `reviewInterval` is actually `reviewRepetitionString`
- There is no `active` column on Task, Context, or Folder tables

### Dropped detection — VERIFIED

- **`dateHidden` = drop date** across all entity types (Task, Folder). No separate `dateDropped` column exists.
- `effectiveDateHidden` = inherited drop date (e.g., tasks in a dropped project get this set while their own `dateHidden` stays NULL)
- `ProjectInfo.effectiveStatus` contains literal `'dropped'` strings — confirms project-level drop status
- Same `dateHidden` pattern applies to Folders and Tags

### Timestamp format inconsistency

- Some columns store CF epoch floats: `792956116.902`
- Others store ISO 8601 strings: `2026-02-16T22:00:00.000`
- Parser must handle both formats

### Two-axis status validation

- 173 tasks are both `blocked=1` AND `overdue=1` — confirms these are independent dimensions
- 586 overdue tasks total, 995 blocked tasks total (out of 2829)
- 0 tasks currently `dueSoon` (likely time-of-day dependent)

### Review interval format

- Compact string format: `@1w` (fixed schedule), `~2m` (flexible schedule)
- Prefix: `@` = fixed, `~` = flexible
- Suffix: standard duration abbreviations (`d`, `w`, `m`, `y`)
- Most common: `~2w` (49 projects), `@1w` (42), `~3w` (36)

### Perspective `valueData` plist contents — VERIFIED

- Only 5 columns in Perspective table: `persistentIdentifier`, `creationOrdinal`, `dateAdded`, `dateModified`, `valueData`
- `valueData` is a binary plist blob containing all perspective config:
  - `name` — perspective name (verified against all 50 perspectives)
  - `iconNameInBundle` — icon identifier
  - `tintColor` — RGBA color string
  - `filterRules` — JSON query language for filtering (complex, not implementing now)
  - `topLevelFilterAggregation` — "all" / "any" for combining filter rules
  - `useSavedColumns`, `useSavedExpansion`, `useSavedFocus` — layout booleans
  - `viewState` — view mode, sort order, sidebar filter, collation
  - `version` — perspective format version
- Built-in perspectives identifiable by human-readable IDs (e.g., `ProcessCompleted`, `ProcessRecentChanges`)
- **For now:** only `name` is needed. `filterRules` could enable perspective-aware queries in the far future.

---

## Script

- `verify_field_coverage.py` — Opens SQLite in read-only mode (`?mode=ro`). Runs 6 phases: schema discovery, field-by-field verification against model contract, two-axis status deep dive, relationship join verification, tricky field investigation, and coverage summary. All queries are SELECT/PRAGMA only.
- `verify_failed_fields.py` — Investigates the 6 failed fields. Queries SQLite (read-only) for evidence, then generates a JS snippet for manual OmniJS cross-check in OmniFocus Automation Console.
