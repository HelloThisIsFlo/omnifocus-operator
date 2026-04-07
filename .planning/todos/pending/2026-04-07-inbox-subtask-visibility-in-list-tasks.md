# Inbox subtask visibility in list_tasks

## Problem

`list_tasks` with `inInbox=true` or `project="$inbox"` returns only root-level inbox tasks. Subtasks nested under inbox action groups are excluded.

Two related issues:
1. **Hybrid mode**: Inbox subtasks excluded from `inInbox=true` results but visible via `inInbox=false` (they fall into a no-man's land — excluded from inbox queries but tagged with `project: $inbox`)
2. **Bridge-only mode**: Inbox subtasks are fully unreachable — not returned by `inInbox=true`, `inInbox=false`, or `project="$inbox"`. Only accessible via direct ID lookup.

## Expected behavior

Inbox subtask visibility should match project query behavior: `list_tasks` with `project="SomeProject"` returns a flat list including both root tasks and subtasks, with hierarchy reconstructable via the `parent` field. The same should apply to inbox queries.

## Context

- Discovered during phase 43 UAT (extended bridge-only testing, Tests 3-5, 14, 14B)
- Pre-existing issue, not a phase 43 regression
- Root cause likely in the SQL query (hybrid) and OmniJS query (bridge) for inbox filtering
