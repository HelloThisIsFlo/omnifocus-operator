---
created: 2026-03-09T19:32:00.000Z
title: Introduce actions grouping and field graduation to edit_tasks
area: api-design
priority: high
files:
  - src/omnifocus_operator/models/
  - src/omnifocus_operator/service/
  - src/omnifocus_operator/bridge/
---

## Problem

The edit API currently mixes idempotent field setters and stateful operations at the same level (`name`, `addTags`, `removeTags`, `moveTo` are all top-level). This becomes worse when adding `complete`/`drop` lifecycle transitions — they don't fit as field setters.

## Solution

Split edit_tasks into two levels:

**Top-level**: idempotent setters (name, flagged, note, dates, estimatedMinutes)

**`actions` block**: operations that modify state relative to current values:
```json
{
  "id": "xyz",
  "name": "Renamed",
  "flagged": true,
  "actions": {
    "tags": {
      "add": ["c"],
      "remove": ["d"]
    },
    "move": {
      "after": "sibling-id"
    },
    "lifecycle": "complete"
  }
}
```

### Details

- `actions.tags`: three modes — `add`, `remove` (combinable), or `replace` (standalone, mutually exclusive with add/remove)
- `actions.move`: "key IS the position" — exactly one of `after`, `before`, `beginning`, `ending`. Null value for `beginning`/`ending` means inbox.
- `actions.lifecycle`: `"complete"` and `"drop"` (and potentially `"reopen"` later) — lifecycle is a later phase (not part of this todo's scope, just showing the design slot)
- Top-level `tags` setter is REMOVED — tag replacement is now `actions.tags.replace`

### Field Graduation Pattern

Any field can "graduate" from top-level setter to action group when it needs more than replacement. Migration: remove from top-level, add under `actions` with `replace` + new operations. Tags are the first field to graduate. Each graduation is independent. Already documented in `docs/architecture.md`.

### Warning Alignment

- Setters: generic no-op warning ("No changes detected")
- Actions: action-specific warnings ("Tag already on task", "Already in this location")

### Implementation Notes

- Do this NOW, before implementing lifecycle transitions — restructure the API shape first as its own phase (e.g., 16.1), then lifecycle comes in a subsequent phase
- Priority is HIGH — easier to set conventions now than after more code depends on current shape
- Update warning messages to match new field names (e.g., `addTags` → `actions.tags.add`)
- Breaking change to `edit_tasks`, but no external consumers yet so no migration concern

### Supersedes

- `.planning/todos/done/2026-03-08-unify-position-concept-across-create-edit-get-apis.md` — position unification is achieved through coherent per-verb design, not structural sameness
