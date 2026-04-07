---
status: diagnosed
phase: 43-filters-project-tools
source: 43-01-SUMMARY.md, 43-02-SUMMARY.md
started: 2026-04-07T12:00:00Z
updated: 2026-04-07T12:01:00Z
---

## Current Test

[testing complete]

## Tests

### 1. list_tasks with $inbox resolves to inbox tasks
expected: Calling list_tasks with project="$inbox" returns only tasks that live in the inbox (not assigned to any project). The $inbox token is consumed and replaced with in_inbox=True filtering.
result: pass
notes: Works correctly. Pre-existing observation: both in_inbox=True and $inbox return only root inbox tasks (no hierarchy). Not a phase 43 regression. Tested on hybrid repo; bridge-only testing deferred.

### 2. Contradictory inbox+project filter returns error
expected: Calling list_tasks with project="$inbox" AND in_inbox=false (or project="$inbox" combined with a real project) returns an error with an educational message explaining the contradiction.
result: pass

### 3. get_project rejects $inbox with educational error
expected: Calling get_project with id="$inbox" returns an error explaining that $inbox is a virtual location, not a real project, and suggests using list_tasks with project="$inbox" instead.
result: pass

### 4. list_projects warns on inbox-related search terms
expected: Calling list_projects with a search term like "inbox" or "Inbox" returns results normally but includes a warning that the inbox is a virtual location and won't appear in project listings.
result: pass
notes: Minor tweak applied during UAT — changed "The inbox" to "The '$inbox'" in both warnings.py and errors.py for consistency with the $inbox token syntax.

## Summary

total: 4
passed: 4
issues: 1
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "Bridge-only mode should not return projects as task entries in list_tasks results"
  status: failed
  reason: "In bridge-only mode, list_tasks returns projects as task entries with self-referencing parents (parent.project.id === task.id). Affects any project-scoped query. Does not occur in hybrid mode. Pre-existing bug, not a phase 43 regression."
  severity: major
  test: bridge-only extended testing (Tests 6B, 12B)
  root_cause: "OmniFocus flattenedTasks includes project root tasks (every project has an underlying Task object). SQLite path excludes them via LEFT JOIN ProjectInfo WHERE pi.task IS NULL. Bridge-only path has no equivalent filter."
  artifacts:
    - path: "src/omnifocus_operator/repository/bridge_only/bridge_only.py"
      lines: "152-200"
      issue: "list_tasks missing project-root-task exclusion"
    - path: "src/omnifocus_operator/repository/hybrid/query_builder.py"
      lines: "34-39"
      issue: "SQL correctly excludes project root tasks (reference)"
    - path: "src/omnifocus_operator/repository/bridge_only/adapter.py"
      lines: "372-374"
      issue: "adapt_snapshot builds project_names but doesn't filter tasks"
  missing:
    - "Filter project root tasks in adapt_snapshot: exclude tasks whose ID appears in project_names dict. Fixes list_tasks and get_all in one place."
