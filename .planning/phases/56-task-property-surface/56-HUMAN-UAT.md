---
status: partial
phase: 56-task-property-surface
source: [56-VERIFICATION.md]
started: 2026-04-19T22:30:00Z
updated: 2026-04-19T22:30:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. FLAG-07 behavioral meaning in live MCP client
expected: The `list_tasks` tool description mentions `isSequential: only the next-in-line child is available` and `dependsOnChildren: real task waiting on children` with behavioral meaning — not just field presence.
result: [pending]

### 2. Create-default resolution writes explicit preference value
expected: Adding a task via `add_tasks` while omitting `completesWithChildren` and `type`, then reading it back via `get_task`, returns values matching the user's actual OmniFocus preferences (`OFMCompleteWhenLastItemComplete` / `OFMTaskDefaultSequential`) — NOT OmniFocus's implicit defaults.
result: [pending]

### 3. No-suppression invariant via live round-trip
expected: `list_tasks` with `include=['hierarchy']` on a sequential task that has children and does NOT complete with children returns BOTH the default-response derived flags (`isSequential: true`, `dependsOnChildren: true`) AND the hierarchy group fields (`type: 'sequential'`, `hasChildren: true`, `completesWithChildren: false`) independently — both pipelines emit, no de-duplication.
result: [pending]

### 4. `singleActions` rejection error rendering
expected: `add_tasks` with `type='singleActions'` surfaces a generic Pydantic enum error in the live MCP client — not a custom educational message, no mention of "project only".
result: [pending]

### 5. Capture the golden master baseline
expected: `tests/golden_master/snapshots/task_property_surface_baseline.json` committed with the normalized serialized output of `list_tasks(include=['hierarchy'])` for a fully-loaded task. Procedure documented in `tests/golden_master/snapshots/README.md`. **Agents must NOT run `GOLDEN_MASTER_CAPTURE=1` — human-only per CLAUDE.md.**
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
