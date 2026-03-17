# Milestone v1.4 -- Field Selection, Task Deletion & Notes Append

## Goal

Agents get control over what data they receive and gain two new write capabilities. Field selection reduces token usage by projecting only needed fields. Task deletion adds permanent removal. Notes append enables incremental note updates without read-modify-write cycles. No new data paths — all within existing architecture.

## What to Build

### Field Selection

Optional `fields` parameter (list of field name strings) on all `list_*` and `get_*` tools. When provided, only those fields plus `id` (always included) are returned.

**Rules:**
- `id` is always included, even if not listed
- Invalid field names are silently ignored with a server-side warning log
- Field names use snake_case (matching Pydantic model names)
- `availability` and `urgency` are independent top-level fields
- Nested objects (`review_interval`, `repetition_rule`) are atomic -- no sub-field selection
- Projection happens post-filter, pre-serialization. Filters run against full objects.
- Omitting `fields` returns everything (backward compatible)

### Task Deletion (Deferred from v1.2)

**`delete_tasks([...])`** -- permanently removes tasks by ID. Deleting a parent task removes all children. Returns `[{ success }]`.

The tool description must warn about permanent deletion.

### Notes Append (Field Graduation)

Extend `edit_tasks` to support notes append via the field graduation pattern (see architecture.md):

```json
{
  "id": "xyz",
  "actions": {
    "note": { "append": "Added during daily review on 2026-03-17" }
  }
}
```

**Semantics:**
- `"note": "new text"` (top-level) — replace entire note (existing behavior, unchanged)
- `"note": null` (top-level) — clear note (existing behavior, unchanged)
- `"actions.note.append"` — append text to existing note with newline separator
- `"actions.note.replace"` — same as top-level replace (for symmetry within actions block)
- If both top-level `note` and `actions.note` are provided, return a validation error

This is the second field graduation after tags (v1.2), following the same pattern documented in architecture.md.

## Key Acceptance Criteria

- Field projection works on all `list_*` and `get_*` tools
- `id` always included in projected output
- Projection doesn't affect filtering
- Task deletion is permanent and removes children
- Notes append adds text with newline separator to existing note
- Notes append on empty note sets the note (no leading newline)
- Validation error when both top-level `note` and `actions.note` are provided
- All existing tools work unchanged (backward compatible)

## Tools After This Milestone

Fourteen: all thirteen from v1.3, plus `delete_tasks`.
