# OmniFocus Timezone Behavior — Results

> All dates stored as 🌊 floating naive local time. Conversion formula proven across 430 tasks. Settings API exposes default times for date-only handling.

## 1. 🌊 Floating vs 📌 Fixed Timezone

Two modes for `shouldUseFloatingTimeZone`:

| | 🌊 Floating (`true`) | 📌 Fixed (`false`) |
|---|---|---|
| **Preserves** | Wall clock time | UTC moment |
| **SQLite encoding** | No Z suffix (naive local) | Z suffix (UTC) |
| **Real-world usage** | 100% — 3341 tasks, 379 projects | Zero in real data |

> [!important] Same-TZ invisibility
>
> - From the same timezone, 🌊 and 📌 are **identical** through the Date API
> - Difference only manifests when system timezone changes
> - Toggling re-encodes SQLite date text (naive local ↔ UTC+Z)

> [!warning] Order enforcement
>
> - Must set a date **before** `shouldUseFloatingTimeZone = false`
> - OmniFocus throws `"Set due or defer date to edit the time zone"` otherwise

### Cross-timezone proof

Two tasks with identical `dueDate = new Date("2026-07-15T10:00:00Z")`, created in BST:

| | BST (home, UTC+1) | EDT (New York, UTC-4) |
|---|---|---|
| 🌊 **Floating** | 11:00 BST | **11:00 EDT** — UTC shifted +5h |
| 📌 **Fixed** | 11:00 BST | **06:00 EDT** — UTC unchanged |

### OmniJS TimeZone API constraints

- **IANA names don't work** — `new TimeZone("Europe/London")` → null
- Only **abbreviations**: `"EST"`, `"UTC"`, `"PST"`, `"BST"`, `"GMT"`
- ⚠️ Abbreviations are **DST-aware** — `new TimeZone("EST")` → EDT in summer (UTC-4, not UTC-5)

## 2. Conversion Formula ✅

```
dateDue (naive local text) → effectiveDateDue (CF epoch float):
1. Parse naive text as datetime
2. Attach system timezone (ZoneInfo, handles DST)
3. Convert to UTC
4. CF_seconds = (utc_datetime - CF_EPOCH).total_seconds()
```

- ✅ **430 tasks** across BST and GMT — zero mismatches
- ✅ Same formula for all three date pairs (`due`, `start`, `planned`)
- ✅ `_parse_local_datetime()` in `hybrid.py` implements this correctly

## 3. Date Format Normalization

All inputs via bridge → `new Date(input)` → stored as 🌊 naive local time:

| Input format | Example | SQLite dateDue | Effective (UTC) | Notes |
|---|---|---|---|---|
| UTC (`Z`) summer | `09:00:00Z` | `10:00:00.000` | `09:00 UTC` | +1h BST shift |
| UTC (`Z`) winter | `09:00:00Z` | `09:00:00.000` | `09:00 UTC` | GMT = UTC |
| Naive (no Z) | `09:00:00` | `09:00:00.000` | `08:00 UTC` | JS treats as local |
| Date-only | `2026-07-15` | `01:00:00.000` | `00:00 UTC` | ⚠️ See below |
| Offset | `09:00:00+05:30` | `04:30:00.000` | `03:30 UTC` | Normalized via UTC |

> [!note] Bridge always produces 🌊
>
> - Creating tasks via bridge **never** sets `shouldUseFloatingTimeZone=false`
> - To create a 📌 fixed task: set `dueDate` first, then explicitly set `shouldUseFloatingTimeZone = false`
> - Currently irrelevant (100% floating), but documents the constraint

> [!warning] Date-only input quirk
>
> - `new Date("2026-07-15")` parses as **UTC midnight** (JS spec), not local midnight
> - OmniFocus converts to local → `01:00 BST` — user gets 1am, not midnight
> - JS `new Date()` behavior, not an OmniFocus decision

## 4. Codebase Impact

- ✅ **Confirmed correct** — `_parse_local_datetime()`, `_parse_timestamp()`, bridge `d()`, `AwareDatetime` write validation
- 🔧 **Date-only inputs** should use OmniFocus default times:
  - `settings.objectForKey('DefaultDueTime')` → `19:00:00` (user) / `17:00` (default)
  - `settings.objectForKey('DefaultStartTime')` → `08:00:00` (user) / `00:00` (default)
  - Domain logic, not bridge — service/date-resolution layer detects date-only and applies defaults
- 🔧 **DueSoon threshold** available from settings:
  - `DueSoonInterval` = `86400` (1 day, user-configured; OmniFocus default is 2 days)
  - `DueSoonGranularity` = `1` — could replace hardcoded thresholds

> [!tip] Settings API deep dive
>
> Full key list (66 keys) and all date/time values in [script 05 findings](05-settings-api/FINDINGS.md)

## Deep-Dive References

| Script | Covers | Findings |
|---|---|---|
| 01 (a/b/c/d) | API audit, 🌊 vs 📌, cross-TZ proof, SQLite encoding | [FINDINGS](01-api-audit/FINDINGS.md) |
| 02 | Conversion formula proof across DST | [FINDINGS](02-conversion-proof/FINDINGS.md) |
| 03 | Format normalization, settings API discovery | [FINDINGS](03-create-readback/FINDINGS.md) |
| 04 | 🌊 toggle behavior, order enforcement, DateComponents | [FINDINGS](04-floating-experiment/FINDINGS.md) |
| 05 | Settings API — all keys, date/time defaults | [FINDINGS](05-settings-api/FINDINGS.md) |
