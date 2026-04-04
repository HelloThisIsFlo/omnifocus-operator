---
status: complete
phase: 37-server-registration-and-integration-was-phase-38
source: [37-01-SUMMARY.md, 37-02-SUMMARY.md]
started: 2026-04-03T14:30:00Z
updated: 2026-04-04T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running MCP server. Start fresh. Server boots without errors and responds to a basic tool call.
result: pass

### 2. List Tasks (no filters)
expected: Calling list_tasks with no arguments returns a structured result containing your OmniFocus tasks. Response uses camelCase field names and includes pagination info.
result: pass

### 3. List Tasks (search filter)
expected: Calling list_tasks with a search term (e.g., a word you know is in a task name or note) returns only tasks matching that term. Case-insensitive.
result: pass

### 4. List Projects (no filters)
expected: Calling list_projects with no arguments returns your OmniFocus projects as structured data with camelCase fields.
result: pass

### 5. List Projects (search filter)
expected: Calling list_projects with a search term returns only projects whose name or notes contain that term. Case-insensitive.
result: pass

### 6. List Tags (no filters)
expected: Calling list_tags with no arguments returns all your OmniFocus tags as structured data.
result: pass

### 7. List Tags (search filter)
expected: Calling list_tags with a search term returns only tags whose name matches. Case-insensitive.
result: pass

### 8. List Folders (no filters)
expected: Calling list_folders with no arguments returns your OmniFocus folders as structured data.
result: pass

### 9. List Folders (search filter)
expected: Calling list_folders with a search term returns only folders whose name matches. Case-insensitive.
result: pass

### 10. List Perspectives
expected: Calling list_perspectives with no arguments returns your OmniFocus perspectives (both built-in and custom) as structured data.
result: issue
reported: "Only custom perspectives showing, built-in perspectives missing"
severity: major

### 11. List Perspectives (search filter)
expected: Calling list_perspectives with a search term returns only perspectives whose name matches. Case-insensitive, name-only (no notes field on perspectives).
result: pass

## Summary

total: 11
passed: 10
issues: 1
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "list tools should have a sensible default pagination limit"
  status: resolved
  reason: "User reported: list_tasks({}) returned 1.8M characters (2,174 tasks), exceeding token limit. No default limit on any list tool."
  severity: major
  test: post-UAT-feedback
  resolution: "Fixed in phase 37-03. DEFAULT_LIST_LIMIT=50 applied to all 5 list tools. limit/offset added to tags, folders, perspectives query models. Tool descriptions derive limit from constant."
  fixed_by: [aad3688, 2281b23, 5139263]

- truth: "LIST_TASKS_TOOL_DOC documents that project filter uses substring matching"
  status: resolved
  reason: "User reported: project filter uses substring matching but tool description doesn't mention this."
  severity: minor
  test: post-UAT-feedback
  resolution: "Fixed in phase 37-03. Entity-reference resolution cascade documented in tool descriptions and Field(description=...) on query model fields."
  fixed_by: [aad3688]

## Deferred Gaps (not phase 37 — discovered during UAT)

- built-in perspectives missing: SQLite Perspective table only has custom perspectives; built-in ones (Inbox, Projects, Tags, Forecast, Flagged, Review) only available via OmniJS bridge. Needs separate phase — interface change, requires discussion. Debug session: .planning/debug/perspectives-missing-builtin.md
- inbox hierarchy: inInbox: true only returns root tasks, not children. Consistency gap with project queries which return full hierarchy. Pre-existing repo/service behavior.
- effectiveCompletionDate/availability: tasks with effectiveCompletionDate still report availability: "available". Pre-existing data layer bug causing ghost tasks in default queries.
- path field: add hierarchical path string for folders/projects/tasks. Feature request.
- disambiguation warnings: warn when entity names are ambiguous. Feature request.
- ambiguous tag error message: append resolution guidance to error. Enhancement to write operations.
- inbox as first-class value: replace null-as-inbox overloading with explicit inbox value across move, project filter, inInbox. Design effort. (project:null + search confirmed not a bug — user confusion from search behavior.)
- edit_tasks doc: document that lifecycle/move/tags actions are combinable. Not phase 37.
- edit_tasks doc: clarify null=inbox in move semantics. Not phase 37.
