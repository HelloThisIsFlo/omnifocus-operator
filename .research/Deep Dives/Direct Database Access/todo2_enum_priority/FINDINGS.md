# TODO #2 Findings: Status Enum Priority & Degraded Mode Data Quality

**Date:** 2026-03-06
**Status:** Complete

---

## Abstract

OmniFocus represents task status differently depending on how you read it. The JS bridge (OmniFocus Automation API) returns a single-winner `taskStatus` enum — a task is Overdue OR Blocked, never both. The SQLite cache exposes independent boolean flags: `blocked`, `blockedByFutureStartDate`, `overdue`, `dueSoon`. Same data, different representations.

For OmniFocus Operator, we want to split status into **two independent axes**:

- **Urgency** (time-sensitive): overdue, due soon, no deadline
- **Availability** (actionable): available, blocked, blocked by future start, next, completed, dropped

Previously, reading through the JS bridge gave us a single collapsed enum. To separate it into two axes, we would have had to reimplement OmniFocus's internal blocking logic — walking parent chains, evaluating sequential ordering, checking defer dates. That's brittle and guaranteed to diverge over time.

**With SQLite as the primary read path, we get both axes for free.** OmniFocus itself computes `blocked`, `blockedByFutureStartDate`, `overdue`, and `dueSoon` as independent columns. We just read them. No reimplementation, no divergence risk. This is a massive win — our code becomes a thin mapping layer rather than a logic engine.

The remaining question was: **what about degraded mode?** When SQLite is unavailable and we fall back to the JS bridge, do we lose everything? The answer is no — and this is the key finding. The bridge's single-winner enum prioritizes urgency over availability (Overdue always beats Blocked). Since urgency is ~90% of real usage ("what's overdue? what's due soon?"), degraded mode still covers the primary use case. We lose independent availability filtering, but we don't need to reimplement it — we just honestly report it as unknown.

**Bottom line:** SQLite gives us both axes natively. Degraded mode preserves the axis that matters most. We don't need to reimplement OmniFocus logic for either path.

---

## Detailed Findings

### 1. Overdue always wins over Blocked

Confirmed empirically with 10 tasks that are both `blocked=1` AND `overdue=1` in SQLite. All 10 report `taskStatus: Overdue` via the OmniFocus Automation API. Zero exceptions.

**Priority order of the single-winner enum:**
1. Overdue (highest)
2. Blocked
3. DueSoon
4. Available / Next (lowest)

### 2. Context doesn't override urgency

- Tasks in **Blocked projects** still report `taskStatus: Overdue` if their due date has passed (6 of 10 test tasks).
- Tasks with **future defer dates** (`blockedByFutureStartDate=1`) still report Overdue if the due date has passed.
- Urgency (time-based) always wins over availability (structural).

### 3. Degraded mode preserves urgency — and that's the big win

**Key insight from walk conversation:** In ~90% of real usage, what matters is urgency — "what's overdue? what's due soon?" Availability filtering (blocked/not blocked) is nice-to-have but secondary.

Since Overdue beats Blocked in the single-winner enum, the JS bridge fallback **already preserves the urgency axis**. A task that's both blocked and overdue will correctly show as Overdue in degraded mode. The only loss is that you can't independently query availability.

**This means degraded mode is still highly useful**, not just a "better than nothing" fallback. It covers the primary use case.

### 4. SQLite gives the full picture (primary mode advantage)

With SQLite, both axes are independent columns:
- **Urgency:** `overdue`, `due_soon`
- **Availability:** `blocked`, `blocked_by_future_start_date`

A task can be both overdue AND blocked simultaneously — the agent gets the complete picture and can filter on either axis independently. This is strictly better than the single-winner enum.

---

## Supporting Data

### Flag relationships discovered

| Finding | Detail |
|---------|--------|
| `blockedByFutureStartDate` is a strict subset of `blocked` | 0 tasks have `bfs=1` and `blocked=0` |
| `overdue` and `dueSoon` are mutually exclusive | 0 tasks have both set |
| 148 completed tasks retain `overdue=1` | Must always filter by `dateCompleted IS NULL` |
| 173 active tasks are both blocked AND overdue | These are invisible in single-winner enum |

### Side-by-side verification (10 tasks)

| # | SQLite blocked | SQLite overdue | API taskStatus | Project Status |
|---|:-:|:-:|---|---|
| 1 | 1 | 1 | Overdue | Overdue |
| 2 | 1 | 1 | Overdue | Overdue |
| 3 | 1 | 1 | Overdue | **Blocked** |
| 4 | 1 | 1 | Overdue | **Blocked** |
| 5 | 1 | 1 | Overdue | **Blocked** |
| 6 | 1 | 1 | Overdue | **Blocked** |
| 7 | 1 | 1 | Overdue | **Blocked** |
| 8 | 1 | 1 | Overdue | Overdue |
| 9 | 1 | 1 | Overdue | **Blocked** |
| 10 | 1 | 1 | Overdue | Overdue |

---

## Implications for Implementation

1. **SQLite bridge (primary):** Expose all four flags as independent booleans on the Pydantic model. Agents get full urgency + availability.

2. **JS bridge fallback (degraded):** The single-winner enum already preserves urgency. Set `blocked` and `blocked_by_future_start_date` to `None` (unknown) rather than guessing. Be honest about what degraded mode can't provide.

3. **Queries must filter `dateCompleted IS NULL`:** Completed tasks retain stale status flags. Never trust flags without checking completion state first.

4. **Deriving `taskStatus` from SQLite flags** (if needed for backward compat): Check Overdue first, then Blocked, then DueSoon, then Available/Next.

---

## Scripts

- `test_enum_priority.py` — Flag distribution matrix, overlap analysis, subset relationships
- `verify_side_by_side.py` — Generates JS console snippet for side-by-side API comparison
- `FINDINGS_side_by_side.md` — Raw results from the side-by-side verification
