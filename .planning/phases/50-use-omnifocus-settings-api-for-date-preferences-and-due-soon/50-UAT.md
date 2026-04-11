---
status: complete
phase: 50-use-omnifocus-settings-api-for-date-preferences-and-due-soon
source: [50-01-SUMMARY.md, 50-02-SUMMARY.md, 50-HUMAN-UAT.md]
started: 2026-04-11T15:00:00Z
updated: 2026-04-11T17:05:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Server boots with preferences module
expected: Restart the MCP server connection. Server starts without errors. A basic list_tasks call returns data normally — no crash or timeout from the new OmniFocusPreferences lifespan initialization.
result: pass

### 2. Tool descriptions document date-default behavior
expected: Read the add_tasks tool description. It should include a note explaining that date-only inputs (no time component) will use the user's configured default time from OmniFocus Preferences, and that the "due soon" threshold comes from OmniFocus preferences.
result: pass

### 3. Bridge reads real OmniFocus preferences
expected: The server reads actual OmniFocus preference values (DefaultDueTime, DueSoonInterval, etc.) — not factory defaults. Verify by checking that the due-soon threshold or default time in behavior matches what you have configured in OmniFocus Preferences.
result: pass
verified: Created task with date-only dueDate "2026-04-15" → returned 2026-04-15T18:00:00Z (19:00 BST = 7 PM, matching user's configured DefaultDueTime). Factory default is 17:00/5 PM — the 7 PM value proves real preferences are read.

### 4. Date-only dueDate applies user's default due time
expected: Create a task via add_tasks with a date-only dueDate. Check that the due time matches the user's configured DefaultDueTime, not midnight 00:00:00.
result: pass
verified: All three date fields confirmed — due 7 PM (not factory 5 PM), defer 8 AM, planned 9 AM. All match user's OmniFocus Preferences → Dates & Times settings exactly.

### 5. DueSoon threshold from OmniFocus preferences
expected: Use list_tasks with due "soon". The threshold should reflect the user's OmniFocus preference. User's DueSoon = "today".
result: pass
verified: Created "[UAT-50] Due today" and "[UAT-50] Due tomorrow". Soon filter returned only the today task (urgency "due_soon"). Tomorrow task excluded. Confirms DueSoon threshold = today, matching user's OmniFocus preference.

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

