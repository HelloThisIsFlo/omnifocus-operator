# Future Ideas

Ideas worth pursuing eventually but not assigned to any milestone yet.

## Date Filtering Improvements

- **Calendar-aware month/year arithmetic** — Currently naive (~30d, ~365d). A date library (e.g., `python-dateutil`) could handle variable month lengths, Feb 28/29, and proper calendar math for `{last: "2m"}`. Low priority — naive is sufficient for most queries.
- **Non-local timezone support** — OmniFocus supports per-event timezone annotations. Currently ignored; all comparisons use naive local time. Could matter for users who travel across timezones or collaborate globally.
- **"More than N ago" shorthand** — Currently, "tasks overdue by more than 2 weeks" requires the agent to compute an ISO date: `due: {before: "2026-03-12"}`. A hypothetical `{more_than: "2w"}` could express this directly. Low priority — agents can compute dates.

## Notifications / reminders
- **What:** Read/write task notifications (due-date alerts, custom reminders, timing configuration)
- **Why future:** Bridge already extracts notification data (BRIDGE-SPEC Section 7, deferred). Could enhance agent-created tasks by setting reminders. Low priority but clearly useful.

## Project folder moves
- **What:** Move projects between folders via `edit_projects({ folder })`.
- **Why deferred from v1.5:** Folder-to-folder movement is meaningfully more complex than task moves (folders are a distinct container type, not a project-as-parent) and the review workflow that drives v1.5 Project Writes does not depend on it. `add_projects` still accepts a folder at creation time — only `edit_projects({ folder })` is excluded.
- **When to revisit:** If agent-driven project reorganization becomes a real workflow, or when we touch folder semantics for another reason.
