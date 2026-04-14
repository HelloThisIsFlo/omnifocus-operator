---
status: complete
phase: 53-response-shaping
source: 53-01-SUMMARY.md, 53-02-SUMMARY.md, 53-03-SUMMARY.md, 53-04-SUMMARY.md, 53-05-SUMMARY.md
started: 2026-04-14T14:30:00Z
updated: 2026-04-14T17:00:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

[testing complete]

## Tests

### 1. Inherited Field Names in Output
expected: Call `get_task` for any known task. Fields previously named `effectiveFlagged`, `effectiveDueDate`, etc. should now appear as `inheritedFlagged`, `inheritedDueDate`, `inheritedDeferDate`, `inheritedPlannedDate`, `inheritedDropDate`, `inheritedCompletionDate`. No `effective*` field names in the response.
result: pass

### 2. Response Stripping on Read Tools
expected: Call `get_task` for a task. Fields that are null, empty list `[]`, empty string `""`, `false`, or `"none"` should be absent from the response. The `availability` field should always be present even when its value would normally be stripped. Compare with what you'd expect — fewer fields = stripping is working.
result: pass

### 3. Default Field Selection on list_tasks
expected: Call `list_tasks` (no include/only params). Response items should contain only the default field set (id, name, availability, order, project, dueDate, inheritedDueDate, deferDate, inheritedDeferDate, plannedDate, inheritedPlannedDate, flagged, inheritedFlagged, urgency, tags). Notes, metadata extras, and hierarchy details should NOT appear unless they have non-empty values.
result: issue
reported: "When include/only are omitted (None), projection is skipped entirely — all fields with values appear. With include: [] it works correctly. The None vs [] distinction causes the bug."
severity: major

### 4. Include Notes Group
expected: Call `list_tasks` with `include: ["notes"]`. Each task in the response should now include the `note` field (if non-empty). All default fields remain present.
result: pass

### 5. Include Review Group (Projects Only)
expected: Call `list_projects` with `include: ["review"]`. Each project should include review-related fields: `nextReviewDate`, `reviewInterval`, `lastReviewDate`, `nextTask`. Calling `list_tasks` with `include: ["review"]` should fail with an educational error (review is project-only).
result: pass

### 6. Include All Fields
expected: Call `list_tasks` with `include: ["*"]`. Response items should contain ALL available fields (notes, metadata, hierarchy, time groups all included). This is the "give me everything" escape hatch.
result: pass

### 7. Invalid Include Group Error
expected: Call `list_tasks` with `include: ["bogus"]`. Should return an error with an educational message listing the valid group names (notes, metadata, hierarchy, time, *).
result: pass

### 8. Count-Only Mode
expected: Call `list_tasks` with `limit: 0`. Response should be `{items: [], total: <count>, hasMore: true}` — zero items returned but `total` shows the actual count. This enables "how many tasks match?" without fetching any data.
result: pass

### 9. Tool Description Content
expected: Inspect the `list_tasks` tool description (visible in Claude Desktop tool list or via MCP inspector). Should mention: include groups (notes, metadata, hierarchy, time), default fields, inherited field names, stripping behavior ("empty values omitted"), and count-only tip (limit: 0).
result: pass

### 10. Only Field Selection
expected: Call `list_tasks` with `only: ["name", "dueDate"]`. Response should contain only id (always), name, and dueDate. No other fields. Combining include + only should produce a warning and only should win.
result: pass

### 11. Input Schema Review (Agent Perspective)
expected: Review the input schema for list_tasks and list_projects as seen by the agent. include/only should be clearly documented, not confusing, no redundancy. Schema types should match intended behavior.
result: pass

### 12. Descriptions Fragment Reuse Audit
expected: Review descriptions.py for fragment reuse — shared text should be extracted into private fragments, no copy-paste repetition across tool descriptions.
result: pass

### 13. get_all Stripping
expected: Call `get_all`. All entities (tasks, projects, tags, folders, perspectives) should have null/empty/false values stripped. Spot-check a few entities across types. This uses `strip_all_entities` — a separate code path from get_task.
result: pass

### 14. get_project and get_tag Stripping
expected: Call `get_project` for a known project and `get_tag` for a known tag. Both should have stripping applied (no nulls, empties, false). These are separate handler paths from get_task.
result: pass

### 15. list_tags / list_folders / list_perspectives Stripping
expected: Call `list_tags`, `list_folders`, and `list_perspectives` (small limit). All should have stripping applied. These use `shape_list_response_strip_only()` — a different shaping function from list_tasks/list_projects.
result: pass

### 16. Case-Insensitive Field Matching in only
expected: Call `list_tasks` with `only: ["Name", "DueDate"]` (capitalized). Should work identically to `only: ["name", "dueDate"]` — case-insensitive matching is a documented feature.
result: pass

### 17. Multiple Include Groups Combined
expected: Call `list_tasks` with `include: ["notes", "time"]`. Response should include fields from both groups (note + estimatedMinutes/repetitionRule) on top of defaults. Common agent pattern — combining groups.
result: pass

### 18. only with Invalid Field Name
expected: Call `list_tasks` with `only: ["name", "nonExistentField"]`. What happens — warning? Silent ignore? Error? Verify the behavior is agent-friendly.
result: pass

### 19. Default Projection on list_projects
expected: Call `list_projects` with `include: []`. Response should contain only default project fields (id, name, availability, dueDate, inheritedDueDate, deferDate, inheritedDeferDate, plannedDate, inheritedPlannedDate, flagged, inheritedFlagged, urgency, tags). No review, metadata, hierarchy (folder, hasChildren), or other fields unless they have values.
result: pass

## Summary

total: 19
passed: 17
issues: 2
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "inherited* fields should only appear when the value actually comes from the parent hierarchy, not when OmniFocus echoes the task's own direct value"
  status: deferred
  reason: "OmniFocus always fills effective* (now inherited*) with the resolved value, even when nothing is inherited. The rename from effective→inherited made this semantically wrong."
  severity: major
  test: 1
  disposition: "Deferred to standalone todo. Will be a proper feature: walk the parent hierarchy to determine true inheritance (same infrastructure as cycle detection) rather than heuristic strip-when-equal. Avoids edge cases with booleans (flagged) where coincidental equality is common."

- truth: "Default field projection should apply when include/only are omitted — only default fields returned"
  status: failed
  reason: "User reported: When include/only are omitted (None), projection is skipped entirely — all fields with values appear. With include: [] it works correctly. The None vs [] distinction causes the bug."
  severity: major
  test: 3
  root_cause: "include/only default to None on the query contract. Projection logic likely checks truthiness (if include:) which treats both None and [] as falsy, skipping projection for both. But None (omitted) should still trigger default projection."
  artifacts:
    - path: "src/omnifocus_operator/contracts/use_cases/list/tasks.py"
      issue: "include defaults to None instead of []"
    - path: "src/omnifocus_operator/contracts/use_cases/list/projects.py"
      issue: "include defaults to None instead of []"
    - path: "src/omnifocus_operator/server/projection.py"
      issue: "resolve_fields or shape_list_response likely skips projection when include is None"
  missing:
    - "Change include/only defaults from None to [] on ListTasksQuery and ListProjectsQuery so projection always runs"
  debug_session: ""
