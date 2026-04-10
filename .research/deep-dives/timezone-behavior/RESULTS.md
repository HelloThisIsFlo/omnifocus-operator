# OmniFocus Timezone Behavior — Results

> All dates are stored as floating naive local time. The conversion formula is proven. The settings API gives us default due/defer times for date-only handling.

**Status:** Scripts 01-03 complete, 04 pending.

## TL;DR

| Question | Answer |
|----------|--------|
| Q1: Timezone properties on Task? | Only `shouldUseFloatingTimeZone` (bool). No per-task timezone object. |
| Q2: Can you set floating=false? What changes? | Yes. Same TZ: no visible difference. Different TZ: floating preserves wall clock, fixed preserves UTC moment. |
| Q3: Hidden timezone columns in SQLite? | No separate column. Floating encoded as Z-suffix on date text: no Z = floating, Z = fixed. |
| Q4: How does OmniFocus compute effectiveDateDue? | `CF_seconds = (naive_local_as_tz(system_tz) → UTC - CF_EPOCH).total_seconds()` |
| Q5: Does conversion hold across DST? | Yes — proven across 430 tasks, both BST (summer) and GMT (winter), max delta <1s. |
| Q6: What does OmniFocus store for each date format? | All normalized to naive local time. See [normalization table](#3-date-format-normalization). |
| Q7: What happens when floating is toggled? | Immediate. Reinterpretation happens when system TZ changes. |
| Q8: Can you create dates with specific timezones? | `new TimeZone("EST")` works (abbreviations only, not IANA). IANA names like "Europe/London" return null. |

## 1. Floating vs Fixed Timezone

- **Floating** (`shouldUseFloatingTimeZone=true`): Wall clock time preserved. "Due at 11:00" means 11:00 wherever you are. UTC moment recalculated per timezone.
- **Fixed** (`shouldUseFloatingTimeZone=false`): UTC moment preserved. "Due at 10:00 UTC" stays 10:00 UTC. Wall clock shifts with travel.
- **100% of real tasks (3341) and projects (379) are floating=true**
- In SQLite: floating = no Z suffix on date text, fixed = Z suffix
- From the same timezone, both look identical — difference only manifests when system timezone changes

### Cross-timezone proof (script 01b/01c)

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

- Verified against 430 tasks across BST and GMT periods
- Max delta: <1 second (rounding)
- Zero mismatches
- Same formula works for dateToStart↔effectiveDateToStart, datePlanned↔effectiveDatePlanned
- `_parse_local_datetime()` in hybrid.py implements this correctly

## 3. Date Format Normalization

All inputs via bridge → `new Date(input)` → OmniFocus stores as naive local time (floating):

| Input format | Example | SQLite dateDue (local) | Effective (UTC) | Notes |
|-------------|---------|----------------------|-----------------|-------|
| UTC (`Z`) summer | `09:00:00Z` | `10:00:00.000` | `09:00 UTC` | +1h BST shift |
| UTC (`Z`) winter | `09:00:00Z` | `09:00:00.000` | `09:00 UTC` | GMT = UTC, no shift |
| Naive (no Z) | `09:00:00` | `09:00:00.000` | `08:00 UTC` | JS treats as local → different UTC than Z |
| Date-only | `2026-07-15` | `01:00:00.000` | `00:00 UTC` | JS quirk: date-only = UTC midnight → 1am BST |
| Offset | `09:00:00+05:30` | `04:30:00.000` | `03:30 UTC` | Correctly normalized via UTC |
| Edit re-normalize | Z → +05:30 | `04:30:00.000` | `03:30 UTC` | Edit fully replaces stored value |

## Impact on Codebase

### Confirmed correct
- `_parse_local_datetime()` in hybrid.py — correctly interprets naive SQLite text as local time
- `_parse_timestamp()` — correctly handles CF epoch floats
- Bridge `d()` using `.toISOString()` — correctly outputs UTC
- `AwareDatetime` on write contracts — rejects date-only strings at Pydantic layer

### Actionable: Date-only inputs should use OmniFocus default times

When a date-only input arrives (no time component), the system should apply the user's configured default time from OmniFocus settings instead of falling back to midnight. This matches what the OmniFocus UI does when a user types just a date.

Available settings keys via `settings.objectForKey()`:
- `DefaultDueTime` — e.g., `"17:00"` — for due dates
- `DefaultStartTime` — e.g., `"00:00"` — for defer dates
- `DefaultPlannedTime` — for planned dates (v4.7+)

This is domain logic — the bridge stays a pass-through. The service or a date resolution layer should detect date-only inputs and construct the full datetime using these settings.

### Actionable: DueSoon threshold from settings

- `DueSoonGranularity` — granularity of "due soon" calculation
- `DueSoonInterval` — how far ahead "due soon" looks

Could replace hardcoded thresholds to match OmniFocus's exact behavior.

## Bonus Finding: OmniFocus Settings API

`settings.objectForKey(key)` and `settings.defaultObjectForKey(key)` expose the full OmniFocus preferences. This is accessible from OmniJS (bridge).

### Full settings key list (OmniFocus 4.3)

```
ContextModeShowsParents
DefaultDueTime
DefaultFloatingTimeZone
DefaultPlannedTime (v4.7)
DefaultScheduledNotificationTime
DefaultStartTime
DueSoonGranularity
DueSoonInterval
ForecastAllowCustomOrder
ForecastFlatListCustomOrder
ForecastSectionedListCustomAlarmsSectionCustomOrder
ForecastSectionedListDeferSectionCustomOrder
ForecastSectionedListDueSectionCustomOrder
ForecastSectionedListFlaggedSectionCustomOrder
InboxIsActive
MacGlobalLayoutSettings
MacInspectorConfigurationState
MacQuickEntryLayoutSettings
NearbyShowMapViewFirst
OFMAutomaticallyHideCompletedItems
OFMCompleteWhenLastItemComplete
OFMDefaultSingletonProjectPersistentIdentifier
OFMRemoteNotificationGroupID
OFMRemoteNotificationGroupIDLastRegenerationDate
OFMRemoteNotificationsDisabled
OFMRequiredRelationshipToProcessInboxItem
OFMStandardModePerspectiveIdentifierChanged
OFMStandardModePerspectiveIdentifierCompleted
OFMTaskDefaultSequential
PadGlobalLayoutSettings
PadInspectorConfigurationState
PadQuickEntryLayoutSettings
PerspectiveOrder_v3
PhoneGlobalLayoutSettings
PhoneInspectorConfigurationState
PhoneQuickEntryLayoutSettings
ProcessFlaggedItemsv2
ProcessForecastv2
ProcessInboxv2
ProcessNearbyv4
ProcessProjectsv2
ProcessReviewv2
ProcessTagsv3
ProjectInfoReviewRepetitionString
ReminderCalendarAlarmIndex
ReminderCalendarExportEnabled
UseNewHomeScreenAnimations
VisionGlobalLayoutSettings
VisionInspectorConfigurationState
VisionQuickEntryLayoutSettings
XMLVersionUpgradeLog
_ForecastAllowCustomOrder
_ForecastBlessedTagIdentifier
_ForecastIncludeDeferredItems
_ForecastIncludeItemsWithScheduledNotifications
_ForecastIncludesInboxEvenWhenFocused
_ForecastIncludesOnHoldItems
_ForecastIsOrganizedIntoGroups
_ForecastShouldPreserveHierarchy
_ForecastTodayIncludesFlaggedItems
```

Notable keys beyond date/time:
- `DefaultFloatingTimeZone` — the database-level floating TZ default
- `OFMTaskDefaultSequential` — whether new tasks default to sequential
- `OFMCompleteWhenLastItemComplete` — completedByChildren default
- `InboxIsActive` — whether inbox items count as "available"
- `_ForecastTodayIncludesFlaggedItems` — forecast view behavior

## Deep-Dive References

| Script | What it covers | Link |
|--------|---------------|------|
| 01-tz-api-audit.js + 01b/01c/01d | API audit, floating vs fixed, cross-TZ proof, SQLite storage | [FINDINGS](01-api-audit/FINDINGS.md) |
| 02-date-conversion-proof.py | Conversion formula proof across DST | [FINDINGS](02-conversion-proof/FINDINGS.md) |
| 03-create-and-readback.py | Format normalization, settings API discovery | [FINDINGS](03-create-readback/FINDINGS.md) |
| 04-floating-tz-experiment.js | Floating flag behavior (pending) | [FINDINGS](04-floating-experiment/FINDINGS.md) |
