# OmniFocus Timezone Behavior — Results

> All dates are stored as floating naive local time. The conversion formula is proven. The settings API gives us default due/defer times for date-only handling.

## 1. Floating vs Fixed Timezone

- **Floating** (`shouldUseFloatingTimeZone=true`): Wall clock preserved. "Due at 11:00" = 11:00 wherever you are.
- **Fixed** (`shouldUseFloatingTimeZone=false`): UTC moment preserved. Wall clock shifts with travel.
- **100% of real tasks (3341) and projects (379) are floating=true**
- SQLite encoding: no Z suffix = floating, Z suffix = fixed
- From the same TZ, both look identical — difference only manifests on TZ change
- Must set a date before `floating=false` — OmniFocus throws otherwise
- Toggling re-encodes the SQLite date text (naive local ↔ UTC+Z)

### Cross-timezone proof

Two tasks with identical `dueDate = new Date("2026-07-15T10:00:00Z")`, created in BST:

| | BST (home, UTC+1) | EDT (New York, UTC-4) |
|---|---|---|
| **Floating** | 11:00 BST | **11:00 EDT** (UTC shifted +5h) |
| **Fixed** | 11:00 BST | **06:00 EDT** (UTC unchanged) |

## 2. Conversion Formula (proven)

```
dateDue (naive local text) → effectiveDateDue (CF epoch float):
1. Parse naive text as datetime
2. Attach system timezone (ZoneInfo, handles DST)
3. Convert to UTC
4. CF_seconds = (utc_datetime - CF_EPOCH).total_seconds()
```

Verified against 430 tasks across BST and GMT. Zero mismatches. Same formula for all three date pairs (due, start, planned). `_parse_local_datetime()` in hybrid.py implements this correctly.

## 3. Date Format Normalization

All inputs via bridge → `new Date(input)` → stored as naive local time (floating):

| Input format | Example | SQLite dateDue (local) | Effective (UTC) | Notes |
|-------------|---------|----------------------|-----------------|-------|
| UTC (`Z`) summer | `09:00:00Z` | `10:00:00.000` | `09:00 UTC` | +1h BST shift |
| UTC (`Z`) winter | `09:00:00Z` | `09:00:00.000` | `09:00 UTC` | GMT = UTC |
| Naive (no Z) | `09:00:00` | `09:00:00.000` | `08:00 UTC` | JS treats as local |
| Date-only | `2026-07-15` | `01:00:00.000` | `00:00 UTC` | JS quirk: date-only = UTC midnight → 1am BST |
| Offset | `09:00:00+05:30` | `04:30:00.000` | `03:30 UTC` | Normalized via UTC |

## 4. Codebase Impact

**Confirmed correct**: `_parse_local_datetime()`, `_parse_timestamp()`, bridge `d()`, `AwareDatetime` write validation. Details in per-script findings.

**Actionable — date-only inputs should use OmniFocus default times:**
- `settings.objectForKey('DefaultDueTime')` → e.g. `"17:00"`
- `settings.objectForKey('DefaultStartTime')` → e.g. `"00:00"`
- Domain logic, not bridge — service/date-resolution layer detects date-only and applies defaults
- Full settings API details in [script 03 findings](03-create-readback/FINDINGS.md)

**Actionable — DueSoon threshold from settings:**
- `DueSoonGranularity` + `DueSoonInterval` — could replace hardcoded thresholds

## Deep-Dive References

| Script | Covers | Findings |
|--------|--------|----------|
| 01 (a/b/c/d) | API audit, floating vs fixed, cross-TZ proof, SQLite encoding | [FINDINGS](01-api-audit/FINDINGS.md) |
| 02 | Conversion formula proof across DST | [FINDINGS](02-conversion-proof/FINDINGS.md) |
| 03 | Format normalization, settings API discovery | [FINDINGS](03-create-readback/FINDINGS.md) |
| 04 | Floating toggle behavior, order enforcement, DateComponents | [FINDINGS](04-floating-experiment/FINDINGS.md) |
| 05 | OmniFocus settings API — all keys, date/time defaults | [FINDINGS](05-settings-api/FINDINGS.md) |
