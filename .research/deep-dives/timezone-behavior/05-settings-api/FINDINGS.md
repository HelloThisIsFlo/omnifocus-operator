# OmniFocus Settings API — Findings

> `settings.objectForKey(key)` and `settings.defaultObjectForKey(key)` expose the full OmniFocus preferences via OmniJS. Discovered during script 03 create-and-readback.

**Date:** 2026-04-10
**Script:** `05-settings-api/05-list-settings-keys.js`

## Raw Output

```
=== 05: OmniFocus Settings API ===

--- All Settings Keys ---

ContextModeShowsParents
DefaultDueTime
DefaultFloatingTimeZone
DefaultPasteKind
DefaultPlannedTime
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
ForecastSectionedListPlannedSectionCustomOrder
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
_FeatureTipsEnabled
_ForecastAddToSetTheDateField
_ForecastAllowCustomOrder
_ForecastBlessedTagIdentifier
_ForecastHidesSummaryDots
_ForecastIncludeDeferredItems
_ForecastIncludeItemsWithScheduledNotifications
_ForecastIncludePlannedItems
_ForecastIncludesInboxEvenWhenFocused
_ForecastIncludesOnHoldItems
_ForecastIsOrganizedIntoGroups
_ForecastShouldPreserveHierarchy
_ForecastStatusBadgeCountsOnlyDueItems
_ForecastTodayIncludesFlaggedItems

--- Date/Time Settings (values) ---

  DefaultDueTime:
    value:   19:00:00
    default: 17:00
  DefaultStartTime:
    value:   08:00:00
    default: 00:00
  DefaultPlannedTime:
    value:   09:00
    default: 09:00
  DefaultFloatingTimeZone:
    value:   true
    default: true
  DefaultScheduledNotificationTime:
    value:   14:00
    default: 14:00
  DueSoonGranularity:
    value:   1
    default: 1
  DueSoonInterval:
    value:   86400
    default: 172800

=== END ===
```

## Date/Time-Relevant Keys

| Key | Value | Default | Use case |
|-----|-------|---------|----------|
| `DefaultDueTime` | `19:00:00` | `17:00` | Default time for due dates without time component |
| `DefaultStartTime` | `08:00:00` | `00:00` | Default time for defer/start dates |
| `DefaultPlannedTime` | `09:00` | `09:00` | Default time for planned dates |
| `DefaultFloatingTimeZone` | `true` | `true` | Database-level floating TZ default |
| `DefaultScheduledNotificationTime` | `14:00` | `14:00` | Default notification time |
| `DueSoonGranularity` | `1` | `1` | Granularity of "due soon" threshold |
| `DueSoonInterval` | `86400` (1 day) | `172800` (2 days) | How far ahead "due soon" looks |

## Actionable for Codebase

### Date-only input handling

When a date-only input arrives (no time component), the system should apply the user's configured default time instead of falling back to midnight. This matches OmniFocus UI behavior.

- Detect date-only string at the service layer (bridge stays a pass-through)
- Read `DefaultDueTime` / `DefaultStartTime` via bridge
- Construct full datetime using the user's configured hours/minutes

### DueSoon threshold

- `DueSoonInterval` = `86400` seconds = 1 day (user-configured; OmniFocus default is 2 days)
- `DueSoonGranularity` = `1` (day-level granularity)
- Could replace hardcoded thresholds to match OmniFocus's exact behavior

## Other Notable Keys

- `DefaultFloatingTimeZone` = `true` — confirms floating is the database-level default
- `OFMTaskDefaultSequential` — whether new tasks default to sequential
- `OFMCompleteWhenLastItemComplete` — completedByChildren default
- `InboxIsActive` — whether inbox items count as "available"
- `_ForecastTodayIncludesFlaggedItems` — forecast view behavior

## Full Settings Key List (66 keys, OmniFocus 4)

```
ContextModeShowsParents
DefaultDueTime
DefaultFloatingTimeZone
DefaultPasteKind
DefaultPlannedTime
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
ForecastSectionedListPlannedSectionCustomOrder
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
_FeatureTipsEnabled
_ForecastAddToSetTheDateField
_ForecastAllowCustomOrder
_ForecastBlessedTagIdentifier
_ForecastHidesSummaryDots
_ForecastIncludeDeferredItems
_ForecastIncludeItemsWithScheduledNotifications
_ForecastIncludePlannedItems
_ForecastIncludesInboxEvenWhenFocused
_ForecastIncludesOnHoldItems
_ForecastIsOrganizedIntoGroups
_ForecastShouldPreserveHierarchy
_ForecastStatusBadgeCountsOnlyDueItems
_ForecastTodayIncludesFlaggedItems
```
