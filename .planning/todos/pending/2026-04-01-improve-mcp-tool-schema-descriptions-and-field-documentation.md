---
created: 2026-04-01T20:26:48.828Z
title: Improve MCP tool schema descriptions and field documentation
area: server
files:
  - src/omnifocus_operator/descriptions.py
---

## Problem

Agent-facing MCP tool schemas have several documentation gaps and inconsistencies that reduce agent usability. Found during a full schema review of add_tasks and edit_tasks.

### Semantic gaps

- **`schedule` enum unexplained**: `"regularly"`, `"regularly_with_catch_up"`, `"from_completion"` have no description beyond `"Repetition schedule type."` — agents unfamiliar with OmniFocus can't distinguish them. Add a one-liner per value.
- **`basedOn` too vague**: `"Anchor date for repetition rules"` doesn't explain what it concretely controls. Something like `"Which date field the repetition interval is calculated from"` would be clearer.
- **`on` leaks internal terminology**: `"Write-side ordinal-weekday model..."` — "Write-side" is an implementation detail. Should say something like `"Ordinal weekday pattern for monthly recurrence (e.g., first monday, last friday)"`.
- **`onDays` scope unclear**: Says `"Days of the week for weekly recurrence"` but doesn't say it's rejected for non-weekly types. Add a note.
- **`on`/`onDates` mutual exclusivity not on fields**: Only in tool description, not on the field-level descriptions. Cross-reference on at least one.
- **Empty `on: {}` / omitted `onDays` undocumented**: These are valid patterns (e.g., weekly without onDays = "every week from anchor"). Worth clarifying that sub-fields are optional constraints, not required refinements.

### Missing descriptions

- `estimatedMinutes` — no description (confirm units)
- `flagged` — no description (what does it mean semantically?)
- `name` — no description (minor)
- `note` — no description (minor)
- `id` (edit_tasks) — no description (minor)

### Schema edge case

- `onDates` allows 0 (`minimum: -1, maximum: 31`) — 0 is not a valid day of month. Should be minimum 1 with -1 as special value.

### Redundancy (address if hitting length limits)

- Timezone requirement repeated 3x per tool across date fields — could centralize to tool description only.
- Tag description repeated across tool description and field descriptions — could centralize.

### Read tools

- `get_all` should signal it's a last-resort/debugging tool once list/filter tools are wired in.

## Solution

Address in a single pass through `descriptions.py` and the relevant model docstrings/descriptions. Prioritize semantic gaps and missing descriptions first; redundancy cleanup is optional unless hitting length limits.
