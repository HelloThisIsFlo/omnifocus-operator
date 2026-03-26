# Future Ideas

Ideas worth pursuing eventually but not assigned to any milestone yet.

## Date Filtering Improvements

- **Calendar-aware month/year arithmetic** — Currently naive (~30d, ~365d). A date library (e.g., `python-dateutil`) could handle variable month lengths, Feb 28/29, and proper calendar math for `{last: "2m"}`. Low priority — naive is sufficient for most queries.
- **Non-local timezone support** — OmniFocus supports per-event timezone annotations. Currently ignored; all comparisons use naive local time. Could matter for users who travel across timezones or collaborate globally.
- **"More than N ago" shorthand** — Currently, "tasks overdue by more than 2 weeks" requires the agent to compute an ISO date: `due: {before: "2026-03-12"}`. A hypothetical `{more_than: "2w"}` could express this directly. Low priority — agents can compute dates.

## Notifications / reminders
- **What:** Read/write task notifications (due-date alerts, custom reminders, timing configuration)
- **Why future:** Bridge already extracts notification data (BRIDGE-SPEC Section 7, deferred). Could enhance agent-created tasks by setting reminders. Low priority but clearly useful.
