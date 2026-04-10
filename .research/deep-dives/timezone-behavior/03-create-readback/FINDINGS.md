# Create & Readback — Findings

> OmniFocus normalizes ALL date inputs to naive local time (floating). UTC, offsets, naive, date-only — everything becomes local wall clock time with no Z suffix. The UI displays exactly what's in `dateDue`.

**Date:** 2026-04-10
**Script:** `03-create-readback/03-create-and-readback.py`
**System timezone:** Europe/London, BST (UTC+1)

## Raw Output

```
Timezone Create & Readback Experiment
========================================

System time:  2026-04-10T18:16:52.102131+01:00
UTC offset:   +0100 (BST)

======================================================================
7. Side-by-Side Comparison
======================================================================

  Label  Input                          SQLite dateDue               SQLite effDue (UTC)      Bridge dueDate
  ------ ------------------------------ ---------------------------- ------------------------ ------------------------------
  A      2026-07-15T09:00:00Z           2026-07-15T10:00:00.000      2026-07-15T09:00:00 UTC  2026-07-15T09:00:00.000Z
  B      2026-12-15T09:00:00Z           2026-12-15T09:00:00.000      2026-12-15T09:00:00 UTC  2026-12-15T09:00:00.000Z
  C      2026-07-15T09:00:00            2026-07-15T09:00:00.000      2026-07-15T08:00:00 UTC  2026-07-15T08:00:00.000Z
  D      2026-07-15                     2026-07-15T01:00:00.000      2026-07-15T00:00:00 UTC  2026-07-15T00:00:00.000Z
  E      2026-07-15T09:00:00+05:30      2026-07-15T04:30:00.000      2026-07-15T03:30:00 UTC  2026-07-15T03:30:00.000Z
  F      2026-07-15T09:00:00Z→+05:30    2026-07-15T04:30:00.000      2026-07-15T03:30:00 UTC  2026-07-15T03:30:00.000Z
```

## UI Spot Check

| Task | UI shows | SQLite dateDue | Match |
|------|----------|---------------|-------|
| A | 10:00 AM Jul 15 | 10:00:00.000 | yes |
| B | 9:00 AM Dec 15 | 09:00:00.000 | yes |
| C | 9:00 AM Jul 15 | 09:00:00.000 | yes |
| D | 1:00 AM Jul 15 | 01:00:00.000 | yes |
| E | 4:30 AM Jul 15 | 04:30:00.000 | yes |
| F | 4:30 AM Jul 15 | 04:30:00.000 | yes |

UI displays exactly what's in `dateDue` — naive local time.

## Interpretation

### The normalization pipeline

Every date input goes through: `bridge JS → new Date(input) → OmniFocus stores as naive local time`

1. **JS `new Date()` parses the string** — handles UTC, offsets, naive, date-only per ECMA-262 rules
2. **OmniFocus receives a Date object** — a UTC moment internally
3. **OmniFocus stores it as naive local time** — converts the UTC moment to the system timezone, strips timezone info, writes text to `dateDue`
4. **All tasks are floating** — no Z suffix on any stored date

### Per-format behavior

- **Explicit UTC (`Z`)**: Correctly converted to local. Task A: `09:00Z` → `10:00` local (BST +1h). Task B: `09:00Z` → `09:00` local (December = GMT, no shift).
- **Naive (no Z)**: JS treats as **local time**. Task C: `09:00` → local 09:00 BST → stored as `09:00`. Effective = `08:00 UTC` (different from Task A's `09:00 UTC` despite same "09:00" in input).
- **Date-only**: JS quirk — `new Date("2026-07-15")` parses as **UTC midnight** (00:00Z), not local midnight. OmniFocus converts to local → `01:00` BST. Users sending date-only strings get 1am, not midnight.
- **Explicit offset**: Correctly normalized. Task E: `09:00+05:30` → `03:30 UTC` → `04:30 BST`.
- **Edit re-normalizes**: Task F created as `09:00Z` (= 10:00 local), then edited to `09:00+05:30` (= 04:30 local). The edit completely replaced the stored value.

### Bridge readback vs SQLite

- **Bridge** (`d()` → `.toISOString()`): Always returns UTC with Z suffix
- **SQLite** (`dateDue` text): Always stores naive local time without Z
- **Both are correct representations of the same moment** — just in different timezones
- `effectiveDateDue` (CF epoch float) = the UTC moment, matches bridge output

## Key Findings

- All inputs normalized to floating naive local time — OmniFocus does not preserve input timezone info
- Naive input (`09:00` no Z) ≠ UTC input (`09:00Z`) — they differ by the BST offset (1 hour)
- Date-only input is a gotcha: becomes UTC midnight, then local 1am in BST
- Editing a date fully replaces the stored value — no traces of original format
- Bridge `d()` and SQLite `dateDue` are consistent views (UTC vs local) of the same moment

## Surprises / Unexpected Results

- **Date-only quirk is significant**: `"2026-07-15"` → 1:00 AM, not midnight. This is a JS `new Date()` behavior, not an OmniFocus decision, but it flows through the bridge.
- **No fixed dates**: Even when the input was explicit UTC (`Z`), OmniFocus stored it as floating. The bridge's `new Date()` + assignment to `task.dueDate` always produces floating storage.

## Questions Answered

| Question | Answer | Evidence |
|----------|--------|----------|
| Q6 | All formats normalized to naive local time (floating). UTC→local shift applied. Naive=local. Date-only=UTC midnight→local. Offset→UTC→local. | Side-by-side table |
| Q2 (partial) | Creating via bridge always produces floating tasks. The bridge doesn't set `shouldUseFloatingTimeZone=false`. | All 6 tasks stored without Z suffix |

## Bonus Finding: OmniFocus Settings API

While investigating the date-only quirk, we discovered OmniFocus exposes user preferences via `settings.objectForKey()` / `settings.defaultObjectForKey()`.

### Date/time-relevant keys

| Key | Returns | Use case |
|-----|---------|----------|
| `DefaultDueTime` | `"17:00"` (HH:MM) | Default time when user sets a due date without specifying time |
| `DefaultStartTime` | `"00:00"` (HH:MM) | Default time for defer/start dates |
| `DefaultPlannedTime` | (v4.7+) | Default time for planned dates |
| `DefaultFloatingTimeZone` | ? | The database-level floating TZ default — directly relevant to Q2/Q7 |
| `DueSoonGranularity` | ? | Granularity of "due soon" threshold |
| `DueSoonInterval` | ? | How far ahead "due soon" looks |
| `DefaultScheduledNotificationTime` | ? | Default notification time |

### Implication for date-only handling

The bridge could use `DefaultDueTime` / `DefaultStartTime` to handle date-only inputs correctly:
1. Detect date-only string in bridge.js
2. Read `settings.objectForKey('DefaultDueTime')` (or `DefaultStartTime` for defer)
3. Build the Date using `Calendar.current.startOfDay()` + DateComponents with the user's configured hours/minutes

This would match OmniFocus UI behavior — when a user types just a date in the UI, OmniFocus applies the default time.

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
