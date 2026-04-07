# DueSoon Spike — Findings

> Mapped all 7 OmniFocus "due soon" UI settings to their database representation. Discovered two distinct modes controlled by `DueSoonGranularity`. All three spike questions answered definitively.

**Date:** 2026-04-07 ~22:25 BST | **Method:** 8 test tasks with strategic due dates, cycled through all UI settings, read SQLite after each change.

---

## 1. Complete Setting → Database Mapping

| UI Setting | DueSoonInterval | DueSoonGranularity | Mode |
|------------|----------------|-------------------|------|
| Today | 86400 | **1** | Calendar-aligned |
| 24 hours | 86400 | **0** | Rolling |
| 2 days | 172800 | 1 | Calendar-aligned |
| 3 days | 259200 | 1 | Calendar-aligned |
| 4 days | 345600 | 1 | Calendar-aligned |
| 5 days | 432000 | 1 | Calendar-aligned |
| 1 week | 604800 | 1 | Calendar-aligned |

- `DueSoonInterval` = threshold in seconds. Always `N * 86400`.
- `DueSoonGranularity` = mode flag. `0` = rolling from now. `1` = snap to midnight boundaries.
- "Today" and "24 hours" share the same interval (86400) — only granularity differs.
- No "1 day" option exists in the UI. "Today" (calendar) and "24 hours" (rolling) cover that slot.

---

## 2. Is "Today" Calendar-Aligned or Rolling?

**Calendar-aligned.** Proven by two tasks 2 minutes apart straddling midnight:

| Task | Due (BST) | dueSoon (setting: Today) | dueSoon (setting: 24h) |
|------|-----------|--------------------------|------------------------|
| Pre-midnight | Apr 7 23:59 | **YES** | YES |
| Post-midnight | Apr 8 00:01 | **NO** | YES |

With "today": only the pre-midnight task is flagged. With "24 hours": both are flagged (both within 24h rolling window). Definitive.

---

## 3. Does Changing the Setting Update SQLite Immediately?

**Yes.** All 7 setting changes reflected in the database within seconds. No restart, no sync delay. Both `DueSoonInterval` and `DueSoonGranularity` update atomically, and OmniFocus recomputes the `dueSoon` column on all tasks immediately.

---

## 4. Threshold Computation Formula

### Granularity = 0 (rolling, "24 hours" only)

```
threshold_cf = now_cf + DueSoonInterval
dueSoon = effectiveDateDue < threshold_cf
```

Boundary analysis confirmed: threshold bracketed at 23.6h–24.8h from now (gap due to task distribution, not ambiguity).

### Granularity = 1 (calendar-aligned, all other options)

```
threshold_cf = start_of_today_cf + DueSoonInterval
dueSoon = effectiveDateDue < threshold_cf
```

Where `start_of_today_cf` = midnight (00:00) local time today, as CF epoch seconds.

**Worked example (2026-04-07, "2 days" = 172800):**
- start_of_today = 00:00 BST Apr 7
- threshold = 00:00 BST Apr 7 + 172800s = 00:00 BST Apr 9
- Task due Apr 8 23:10 → YES (before Apr 9 midnight)
- Task due Apr 9 23:10 → NO (after Apr 9 midnight)

---

## 5. v1.3.2 Resolver Implications

### What the resolver needs to read
- `DueSoonInterval` — threshold in seconds
- `DueSoonGranularity` — `0` = rolling, `1` = calendar-aligned

### Resolver logic (pseudocode)
```python
if granularity == 0:
    # Rolling: "24 hours" mode
    threshold = now_cf + interval
else:
    # Calendar-aligned: "today", "2 days", ..., "1 week"
    midnight_today = local_midnight_as_cf()
    threshold = midnight_today + interval
```

### Design note
The original plan was to compute `effectiveDateDue < now + threshold` uniformly. The spike reveals this is only correct for `granularity=0`. For `granularity=1`, the anchor is midnight, not now. This is a meaningful difference — at 11 PM, "today" means "within 1 hour" (midnight), not "within 24 hours."

### Recommendation
Match OmniFocus behavior exactly. Users chose "today" for a reason — they expect the same boundary they see in OmniFocus's Forecast view. Using a rolling window when they configured calendar-aligned would create confusing mismatches.

---

## 6. Cleanup

8 test tasks created in Inbox with `[SPIKE-DS]` prefix. Delete manually when done:
- `[SPIKE-DS] Due 23:59 tonight (pre-midnight)`
- `[SPIKE-DS] Due 00:01 tomorrow (post-midnight)`
- `[SPIKE-DS] Due +6h (04:10 tomorrow)`
- `[SPIKE-DS] Due +20h (tomorrow 18:10 = near DefaultDueTime)`
- `[SPIKE-DS] Due +25h (past 24h boundary)`
- `[SPIKE-DS] Due +49h (past 2d boundary)`
- `[SPIKE-DS] Due +73h (past 3d boundary)`
- `[SPIKE-DS] Due +169h (past 7d boundary)`
