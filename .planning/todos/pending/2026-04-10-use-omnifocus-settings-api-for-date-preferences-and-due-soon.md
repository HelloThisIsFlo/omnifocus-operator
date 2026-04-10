---
created: "2026-04-10T20:15:00.000Z"
title: Use OmniFocus settings API for date preferences and due-soon threshold
area: service
files:
  - src/omnifocus_operator/repository/hybrid/hybrid.py
  - src/omnifocus_operator/bridge/bridge.js
  - src/omnifocus_operator/service/
  - src/omnifocus_operator/contracts/protocols.py
---

## Problem

Two related issues with how the server handles OmniFocus user preferences:

1. **DueSoon threshold** is currently read from the SQLite `Setting` table by parsing plist-encoded blobs. This works but is fragile — it depends on the internal schema of the Setting table and plist binary encoding. The OmniJS `settings.objectForKey()` API provides the same values as clean primitives.

2. **Date-only write inputs** (e.g., agent sends `"2026-07-15"` without a time) currently have no mechanism to apply the user's preferred default times. OmniFocus has configurable defaults:
   - `DefaultDueTime` — user: `19:00:00`, OmniFocus default: `17:00`
   - `DefaultStartTime` — user: `08:00:00`, OmniFocus default: `00:00`
   - `DefaultPlannedTime` — user: `09:00`, OmniFocus default: `09:00`

   When the OmniFocus UI receives a date-only input, it applies these defaults automatically. Our API should do the same — a date-only due date should become `2026-07-15T19:00:00` (using the user's preference), not midnight or some arbitrary time.

Both require the same infrastructure: a bridge path to read OmniFocus settings, and service-layer logic to apply them.

> [!tip] Evidence
>
> The OmniFocus settings API was discovered and documented during the timezone deep-dive — see `.research/deep-dives/timezone-behavior/05-settings-api/FINDINGS.md` for the full key list (66 keys), actual user values, and the OmniJS script that reads them.

## Solution

### Step 1: Bridge settings command

Add a bridge command (e.g., `get_settings`) that reads date-related preferences via `settings.objectForKey()`:
- `DueSoonInterval` (integer, seconds)
- `DueSoonGranularity` (integer)
- `DefaultDueTime` (string, `HH:MM:SS` or `HH:MM`)
- `DefaultStartTime` (string)
- `DefaultPlannedTime` (string)

Return as a clean dict — no plist parsing needed, the OmniJS API returns native types.

### Step 2: Apply preferences in the service layer

- **DueSoon**: Replace the current SQLite plist-parsing path with the bridge settings command. The `DueSoonSetting` enum and `_SETTING_MAP` lookup can stay — just change the data source from SQLite blobs to bridge response.
- **Date-only defaults**: When the service layer detects a date-only input on a write operation, combine the date with the appropriate default time from settings:
  - `dueDate: "2026-07-15"` → `"2026-07-15T19:00:00"` (using `DefaultDueTime`)
  - `deferDate: "2026-07-15"` → `"2026-07-15T08:00:00"` (using `DefaultStartTime`)
  - `plannedDate: "2026-07-15"` → `"2026-07-15T09:00:00"` (using `DefaultPlannedTime`)

This matches OmniFocus UI behavior — the user's configured defaults are respected.

> [!note] Dependency
>
> The date-only default-time application depends on the naive-local datetime todo (`2026-04-10-implement-naive-local-datetime-contract-for-all-date-inputs.md`) — date-only inputs must first be accepted by the contract before they can be enriched with default times.
