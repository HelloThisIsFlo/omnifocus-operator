# Date Filter Database Validation -- Findings

> OmniFocus SQLite cache validated against v1.3.2 assumptions. 5 scripts, 3,277 tasks, 0 blockers. All core design decisions confirmed; two items flagged for implementation notes.

**Database snapshot:** 2026-04-07 18:03 UTC | 3,277 total tasks | 2,143 active

---

## 1. Flag Equivalences

### overdue (script 1)

- `overdue=1` **perfectly equivalent** to `effectiveDateDue < now`
- 570 matches, 0 mismatches across all 4 mismatch categories
- **Verdict:** Can use either form. v1.3.2 uses `effectiveDateDue < now_cf` for `"overdue"` shortcut -- validated.

### dueSoon (script 2)

- `dueSoon` does **NOT** include overdue tasks (0 overlap: `dueSoon=1 AND overdue=1 = 0`)
- Threshold bracketed at 4.4h -- 14.9h (gap in task distribution, not actual threshold edges)
- Settings table reveals: `DueSoonInterval = 86400` (24h), `DueSoonGranularity = 1`, `DefaultDueTime = 19:00:00`
- Likely interaction: OmniFocus computes dueSoon against DefaultDueTime boundaries, not a simple `now + 24h`

**v1.3.2 impact:**
- **NEVER use the `dueSoon` column.** OmniFocus's dueSoon excludes overdue; our `"soon"` shortcut must include overdue per spec (`due < now + threshold`).
- Configured threshold (default 24h) is computed server-side from `effectiveDateDue < now_cf + threshold_seconds` -- independent of OmniFocus's flag logic.
- `DueSoonInterval` from Settings table can seed the default configuration value (86400 = 24h).

### blockedByFutureStartDate (script 2)

- **Perfect equivalence** with `effectiveDateToStart > now`
- 84 agreements (flag=1, date>now), 2,784 agreements (flag=0, date<=now or NULL), 0 mismatches
- **Verdict:** Can use either form. v1.3.2 doesn't directly use this flag (uses `availability: "blocked"` for state questions, `defer` filter for timing questions), so this is informational.

---

## 2. Effective Date Inheritance

### Inheritance rates (active tasks)

| Date pair | Own date (A) | Inherited (B) | Neither (D) | Inheritance % |
|-----------|-------------|---------------|-------------|---------------|
| due | 165 | 337 | 1,641 | **67.1%** |
| defer (toStart) | 201 | 65 | 1,877 | 24.4% |
| planned | 26 | 5 | 2,112 | 16.1% |
| completed | 0 | 174 | 1,969 | 100.0% |
| hidden (dropped) | 0 | 0 | 2,143 | 0.0% |

- Category C (direct set, effective NULL) = **0 across all pairs** -- effective always includes direct. No orphan dates.
- Completed inheritance is 100% on active tasks (174 tasks in completed containers but not individually completed)
- Hidden is 0% on active tasks by definition (active = `effectiveDateHidden IS NULL`)

### Inheritance rates (all tasks)

| Date pair | Inheritance % |
|-----------|---------------|
| due | 57.9% |
| defer | 14.3% |
| planned | 18.9% |
| completed | 29.8% |
| hidden | **73.5%** |

### "45% miss rate" validation

- Overdue via `effectiveDateDue < now`: **570 tasks**
- Of those with `dateDue IS NULL` (inherited only): **316 tasks**
- **55.4% would be missed** without effective dates -- exceeds the spec's ~45% claim
- `dateDue < now_cf` returns **0 results** (text vs numeric comparison fails in SQLite -- see section 3)

**v1.3.2 impact:**
- **Effective dates are non-negotiable.** 67% of active due dates are inherited. Using direct dates would miss the majority of overdue tasks.
- Spec's ~45% figure should be updated to ~55% for accuracy (strengthens the case, no design change).

### Parent chain walks

- 10 sample inherited tasks traced successfully -- chains go 1-4 levels deep
- All sources found at a parent/ancestor task with `dateDue` set
- No broken chains or orphaned effective dates observed

---

## 3. Date Column Formats

### Type map

| Column | SQLite typeof | Format | Example |
|--------|--------------|--------|---------|
| `dateDue` | text | Naive local ISO | `2026-02-06T19:00:00.000` |
| `dateToStart` | text | Naive local ISO | `2026-04-07T08:00:00.000` |
| `datePlanned` | text | Naive local ISO | `2026-02-03T09:00:00.000` |
| `dateCompleted` | real | CF epoch float | `794676655.777` |
| `dateHidden` | real | CF epoch float | `793975019.043` |
| `dateAdded` | real (5 integer) | CF epoch float | `793459268.151` |
| `dateModified` | real | CF epoch float | `793986251.976` |
| `effectiveDateDue` | **integer** | CF epoch truncated | `793462867` |
| `effectiveDateToStart` | **integer** | CF epoch truncated | `791971200` |
| `effectiveDatePlanned` | **integer** | CF epoch truncated | `791802000` |
| `effectiveDateCompleted` | real | CF epoch float | `793459823.857` |
| `effectiveDateHidden` | real | CF epoch float | `793986251.456` |

### Key observations

- **Two type families:** Direct user-set dates (due/defer/planned) are **text** (naive local ISO strings). Everything else is **numeric** (CF epoch, integer or real).
- **effectiveDateDue/ToStart/Planned are integer, not real** -- truncated to whole seconds. User-set times (19:00, 08:00) don't have fractional seconds. SQLite handles `integer < real` comparisons correctly via numeric affinity.
- **dateAdded has 5 integer values** (out of 3,277) -- likely older tasks. No functional impact on comparisons.
- **Direct dates cannot be compared numerically with CF timestamps.** `dateDue < now_cf` always returns 0 (SQLite text > number in type affinity). This is why effective dates are required for SQL filtering.

**v1.3.2 impact:**
- All 7 filterable columns use numeric CF comparisons: `effectiveDateDue`, `effectiveDateToStart`, `effectiveDatePlanned`, `effectiveDateCompleted`, `effectiveDateHidden`, `dateAdded`, `dateModified`
- None of the 3 text-format direct date columns are used for filtering
- Integer vs real mixing in effective columns is transparent to SQLite -- no special handling needed

---

## 4. Null Date Distribution

### Active tasks (2,143)

| Column | NOT NULL | NULL | % NULL |
|--------|---------|------|--------|
| effectiveDateDue | 502 | 1,641 | 76.6% |
| effectiveDateToStart | 266 | 1,877 | 87.6% |
| effectiveDatePlanned | 31 | 2,112 | 98.6% |
| effectiveDateCompleted | 174 | 1,969 | 91.9% |
| effectiveDateHidden | 0 | 2,143 | 100.0% |
| **dateAdded** | **2,143** | **0** | **0.0%** |
| **dateModified** | **2,143** | **0** | **0.0%** |

### dateAdded / dateModified never-null confirmation

- **Confirmed across ALL 3,277 tasks** (not just active): 0 nulls for both columns
- Validates milestone assumption: `"none"` shortcut is invalid for `added`/`modified` fields

### effectiveDateCompleted on active tasks

- 174 active tasks have `effectiveDateCompleted` set despite `dateCompleted IS NULL`
- These are tasks in completed containers (projects/action groups) that weren't individually completed
- 100% of these are inherited (category B) -- no task has both `dateCompleted` set and is in the active scope

**v1.3.2 impact:**
- Null-exclusion rule works naturally: `effectiveDateDue < X` excludes tasks with no due date (76.6% of active tasks). SQL `NULL < X` evaluates to NULL/false.
- `"none"` shortcut (`IS NULL`) will match ~77% of active tasks for `due`, ~88% for `defer`, ~99% for `planned` -- useful for finding unscheduled tasks
- The 174 inherited-completion tasks need a design decision (see section 6)

---

## 5. Completed/Dropped Behavior

### Date completeness

| Category | Count | Detail |
|----------|-------|--------|
| Completed (dateCompleted set) | 409 | All 409 also have effectiveDateCompleted |
| Inherited completion | 174 | effectiveDateCompleted set, dateCompleted NULL |
| Effectively dropped | 725 | effectiveDateHidden set |
| Directly dropped | 192 | dateHidden set |
| Inherited drops | 533 | effectiveDateHidden from project/folder chain |

### Completed AND dropped overlap

- **0 tasks** have both `dateCompleted` and `effectiveDateHidden` set
- Mutually exclusive states in the database
- `completed: "any"` and `dropped: "any"` are clean disjoint sets

### Stale flags

| Flag | On completed tasks | On dropped tasks |
|------|-------------------|-----------------|
| overdue | **339** | **176** |
| dueSoon | 0 | 0 |
| blockedByFutureStartDate | 0 | 0 |
| blocked | 1 | 0 |

- OmniFocus clears `dueSoon` and `blockedByFutureStartDate` on completion/drop but does **NOT** clear `overdue`
- Confirms: never use boolean flags without also filtering by completion/drop status

### Date retention on completed tasks

- Completed tasks **retain all date fields**: 342 have effectiveDateDue, 128 have effectiveDateToStart
- Enables historical queries like `completed: {last: "1w"}` + `due: "overdue"` (tasks completed last week that were overdue when completed)

### Dropped project propagation

- All 10 sampled inherited drops trace to a project with `effectiveDateHidden` set
- The project itself often has `dateHidden IS NULL` -- drop cascades from folder level
- `effectiveDateHidden` captures the full chain regardless of depth

**v1.3.2 impact:**
- Default exclusion (`dateCompleted IS NULL`) correctly excludes directly completed tasks. The 174 inherited-completion tasks need clarification (see section 6).
- Stale `overdue` flag on 339 completed tasks is irrelevant -- implementation uses `effectiveDateDue < now_cf`, and completed tasks are excluded by default.
- Date retention enables rich historical queries -- no special handling needed.

---

## 6. Devil's Advocate Challenges & Responses

### WARNING: Inherited completion on "active" tasks

**Challenge:** 174 tasks pass `dateCompleted IS NULL` but have `effectiveDateCompleted` set (tasks in completed containers). Are they "active"?

**Response:** This is a pre-existing concern, not new to v1.3.2. The current active-task scope uses `dateCompleted IS NULL AND effectiveDateHidden IS NULL` -- it doesn't check `effectiveDateCompleted`. These 174 tasks appear as "active" in default queries.

**For v1.3.2 specifically:**
- The `completed` date filter should use `effectiveDateCompleted` per the spec's effective-dates rule
- When `completed: "today"` is used and a project was completed today, its child tasks (with inherited completion) will appear -- this is semantically correct ("what did I complete today?" includes project contents)
- For the default exclusion behavior, this is a broader question about active-task definition that predates v1.3.2. Document but don't block.

**Action:** Document in implementation notes. Consider whether `effectiveDateCompleted IS NULL` should be part of the active-task filter (broader scope than v1.3.2).

### WARNING: Never use dueSoon column

**Challenge:** OmniFocus `dueSoon` excludes overdue (0 overlap). v1.3.2's `"soon"` must include overdue.

**Response:** The implementation computes `effectiveDateDue < now_cf + threshold_seconds` directly -- the `dueSoon` column is never consulted. But an implementer unaware of this difference might be tempted to use the flag as an optimization.

**Action:** Add explicit implementation note: "Never use the `dueSoon` column. OmniFocus's dueSoon excludes overdue; our `"soon"` includes overdue per spec."

### NOTE: dueSoon threshold measurement inconclusive

**Challenge:** Threshold bracketed at 4.4h-14.9h despite DueSoonInterval=86400 (24h). Measurement reflects task distribution gaps, not actual threshold edges.

**Response:** Irrelevant to implementation. v1.3.2 computes its own threshold (`now + configured_value`), never reads OmniFocus's dueSoon flag. The DueSoonInterval setting is useful only as a default configuration seed.

### NOTE: Integer vs real effective dates

**Challenge:** effectiveDateDue is integer, effectiveDateCompleted is real. Inconsistency?

**Response:** User-set dates (due/defer/planned) have whole-second precision; system timestamps (completed/hidden) have fractional seconds. SQLite numeric comparison handles int/real mixing transparently. No code change needed. Truncation introduces at most 1-second boundary ambiguity on defer dates, which is negligible (defer dates are set to times like 08:00:00).

### NOTE: Single-snapshot limitation

**Challenge:** All data from one point in time. Could flag equivalences break at update boundaries?

**Response:** Implementation uses direct timestamp comparisons (`effectiveDateDue < now_cf`), not flags. Even if `effectiveDateDue` itself has a brief sync lag, it affects the flag-based approach equally. The timestamp comparison approach is inherently resilient.

### NOTE: Spec says ~45%, actual is 55.4%

**Challenge:** Spec understates inheritance impact.

**Response:** Direction is the same (use effective dates). Update spec from "~45%" to "~55%". Documentation fix only.

---

## Summary: v1.3.2 Design Decision Validation

| Decision | Status | Evidence |
|----------|--------|----------|
| Use effective dates for all filtering | **CONFIRMED** | 55.4% of overdue tasks have inherited-only dates |
| `effectiveDateDue < now_cf` for `"overdue"` | **CONFIRMED** | Perfect equivalence with overdue flag (570/570) |
| Compute `"soon"` as `effectiveDateDue < now + threshold` | **CONFIRMED** | Cannot use dueSoon column (excludes overdue) |
| Default due-soon threshold = 24h | **CONFIRMED** | DueSoonInterval=86400 in Settings table |
| All 7 filter columns are numeric CF timestamps | **CONFIRMED** | integer or real, all CF epoch, all comparable with `< ?` |
| `dateAdded`/`dateModified` never null | **CONFIRMED** | 0 nulls across 3,277 tasks |
| Null dates excluded from filter results | **CONFIRMED** | SQL-natural: `NULL < X` = false |
| Completed/dropped mutually exclusive | **CONFIRMED** | 0 overlap in database |
| Completed tasks retain date fields | **CONFIRMED** | 342 completed tasks have effectiveDateDue |

### Items requiring implementation notes

1. **Never use `dueSoon` column** -- OmniFocus excludes overdue, our `"soon"` includes it
2. **174 inherited-completion tasks** -- appear as "active" under current scope definition. `completed` filter should use `effectiveDateCompleted`. Document the broader active-task scope question.
3. **Stale overdue flag** -- 339 completed tasks have `overdue=1`. Irrelevant since we use timestamp comparison, but reinforces "don't use flags on non-active tasks."

### Confidence

**HIGH -- proceed with v1.3.2 as designed.** All core assumptions validated. No blockers. Two documentation items for implementation guidance.
