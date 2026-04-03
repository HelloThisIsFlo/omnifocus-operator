---
status: diagnosed
phase: 37-server-registration-and-integration-was-phase-38
source: [37-01-SUMMARY.md, 37-02-SUMMARY.md]
started: 2026-04-03T14:30:00Z
updated: 2026-04-03T15:15:00Z
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

- truth: "list_perspectives returns both built-in and custom perspectives"
  status: failed
  reason: "User reported: Only custom perspectives showing, built-in perspectives missing"
  severity: major
  test: 10
  root_cause: "SQLite Perspective table only contains custom perspectives. Built-in perspectives (Inbox, Projects, Tags, Forecast, Flagged, Review) are application-level constructs only exposed via OmniJS Perspective.all. Hybrid repo reads exclusively from SQLite, so built-in perspectives are never returned."
  artifacts:
    - path: "src/omnifocus_operator/repository/hybrid/hybrid.py"
      issue: "_PERSPECTIVES_SQL reads from SQLite which lacks built-in perspectives; _map_perspective_row cannot produce null ids"
    - path: "src/omnifocus_operator/bridge/bridge.js"
      issue: "Perspective.all returns both built-in and custom -- this is the only source for built-ins"
  missing:
    - "Supplement SQLite perspectives with built-in perspectives from bridge, or fall back to bridge for perspectives entirely"
  debug_session: ".planning/debug/perspectives-missing-builtin.md"

- truth: "project: null combined with search should return matching tasks (null ignored)"
  status: inconclusive
  reason: "User reported: list_tasks({project: null, search: 'GM-'}) returns 0 tasks, but {search: 'GM-'} alone returns results. Null silently breaks the search filter."
  severity: major
  test: post-UAT-feedback
  root_cause: "Investigation inconclusive. All code paths (service, query builder, hybrid repo, bridge-only repo, full MCP protocol) tested correctly in automated tests. project=None is correctly treated as 'no filter' at every layer. Most likely cause: LLM sent different arguments than expected during live UAT (e.g., string 'null', extra constraining filter, or availability interaction with real data)."
  artifacts:
    - path: "src/omnifocus_operator/service/service.py"
      issue: "No bug found -- _resolve_project correctly skips when project is None"
    - path: "src/omnifocus_operator/repository/hybrid/query_builder.py"
      issue: "No bug found -- SQL correctly omits project filter when project_ids is None"
  missing:
    - "Reproduce manually with server logs showing exact tool arguments received (ToolLoggingMiddleware logs at INFO level)"
    - "If confirmed, add cross-path equivalence test combining project_ids=None with search"
  debug_session: ".planning/debug/project-null-search-interaction.md"

- truth: "list tools should have a sensible default pagination limit"
  status: failed
  reason: "User reported: list_tasks({}) returned 1.8M characters (2,174 tasks), exceeding token limit. No default limit on any list tool."
  severity: major
  test: post-UAT-feedback
  root_cause: "Two-part problem: (1) Tasks/Projects query models have limit: int | None = None with no default -- service passes None through, query builder skips LIMIT clause, unbounded SQL returns all rows. (2) Tags/Folders/Perspectives query models have NO limit/offset fields at all -- repos fetch all rows into Python lists and hardcode has_more=False. Pagination is structurally impossible for these 3 entity types."
  artifacts:
    - path: "src/omnifocus_operator/contracts/use_cases/list/tasks.py"
      issue: "limit defaults to None, no cap"
    - path: "src/omnifocus_operator/contracts/use_cases/list/projects.py"
      issue: "limit defaults to None, no cap"
    - path: "src/omnifocus_operator/contracts/use_cases/list/tags.py"
      issue: "No limit/offset fields at all"
    - path: "src/omnifocus_operator/contracts/use_cases/list/folders.py"
      issue: "No limit/offset fields at all"
    - path: "src/omnifocus_operator/contracts/use_cases/list/perspectives.py"
      issue: "No limit/offset fields at all"
    - path: "src/omnifocus_operator/repository/hybrid/hybrid.py"
      issue: "Tags/folders/perspectives hardcode has_more=False"
  missing:
    - "Add default limit (e.g., 50) to all 5 query models"
    - "Add limit/offset fields to tags, folders, perspectives query models"
    - "Implement Python-side pagination slicing for tags/folders/perspectives in hybrid repo"
  debug_session: ".planning/debug/no-default-pagination-limit.md"

- truth: "LIST_TASKS_TOOL_DOC documents that project filter uses substring matching"
  status: failed
  reason: "User reported: project filter uses substring matching (e.g. filtering by 'TestProject' also matches 'TestProject2') but tool description doesn't mention this."
  severity: minor
  test: post-UAT-feedback
  root_cause: "Entity-reference filters (project, tags, folder) use a 3-step resolution cascade in Resolver.resolve_filter() -- (1) exact ID match, (2) case-insensitive substring match on name, (3) no match with did-you-mean warning -- but this is not documented. LIST_TASKS_TOOL_DOC only documents search as substring. Query model fields have code comments but no Field(description=...), so invisible in MCP schemas."
  artifacts:
    - path: "src/omnifocus_operator/agent_messages/descriptions.py"
      issue: "LIST_TASKS_TOOL_DOC and LIST_PROJECTS_TOOL_DOC missing entity-reference filter semantics"
    - path: "src/omnifocus_operator/contracts/use_cases/list/tasks.py"
      issue: "project and tags fields lack Field(description=...) documenting resolution behavior"
    - path: "src/omnifocus_operator/contracts/use_cases/list/projects.py"
      issue: "folder field lacks Field(description=...) documenting resolution behavior"
  missing:
    - "Add Field(description=...) to project, tags, folder fields explaining 'accepts ID or name; names use case-insensitive substring matching'"
    - "Add resolution cascade summary to LIST_TASKS_TOOL_DOC and LIST_PROJECTS_TOOL_DOC"
  debug_session: ".planning/debug/project-substring-undocumented.md"

## Deferred Gaps (not phase 37 — discovered during UAT)

- inbox hierarchy: inInbox: true only returns root tasks, not children. Consistency gap with project queries which return full hierarchy. Pre-existing repo/service behavior.
- effectiveCompletionDate/availability: tasks with effectiveCompletionDate still report availability: "available". Pre-existing data layer bug causing ghost tasks in default queries.
- path field: add hierarchical path string for folders/projects/tasks. Feature request.
- disambiguation warnings: warn when entity names are ambiguous. Feature request.
- ambiguous tag error message: append resolution guidance to error. Enhancement to write operations.
- inbox as first-class value: replace null-as-inbox overloading with explicit inbox value across move, project filter, inInbox. Design effort.
- edit_tasks doc: document that lifecycle/move/tags actions are combinable. Not phase 37.
- edit_tasks doc: clarify null=inbox in move semantics. Not phase 37.
