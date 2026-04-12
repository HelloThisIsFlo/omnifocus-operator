# Milestone v1.4 -- Field Selection, Null-Stripping & Notes Append

## Goal

Agents get control over what data they receive and gain a new write capability. Field selection and null-stripping reduce token usage — projection limits *which* fields appear, null-stripping limits *which values* appear. Notes append enables incremental note updates without read-modify-write cycles. No new data paths — all within existing architecture.

## What to Build

### Field Selection

`fields` parameter on all `list_*` and `get_*` tools. Controls which fields appear in the response.

**Rules:**
- `id` is always included, even if not listed
- Invalid field names are silently ignored with a server-side warning log
- Field names use snake_case (matching Pydantic model names)
- `availability` and `urgency` are independent top-level fields
- Nested objects (`review_interval`, `repetition_rule`) are atomic -- no sub-field selection
- Projection happens post-filter, pre-serialization. Filters run against full objects.
- Omitting `fields` returns a **curated default set** of the most commonly used fields — not everything. This keeps responses compact by default.
- The tool description lists all available fields so agents can opt in to more when needed.

**Open questions:**
- What is the curated default field set? (per entity type — tasks, projects, tags)
- Should `fields` accept the string `"all"` (or `["*"]`) as an escape hatch to return everything? If so, which syntax?
- Should `fields` accept either a list of strings or a single string value (for the `"all"` case)?

### Null-Stripping

Null fields are omitted from responses by default. This is orthogonal to field selection and compounds with it — field selection controls *which* fields, null-stripping controls *which values*.

A typical task has ~8-10 null fields (`dueDate`, `deferDate`, `completionDate`, `dropDate`, `estimatedMinutes`, `repetitionRule`, etc.) that carry no information. Stripping them reduces response size significantly across bulk reads.

**Open questions:**
- Parameter name? (`exclude_null`, `strip_null`, `omit_null`?)
- Default `true` (nulls omitted unless explicitly requested) — or always on with no toggle?
- Should this also strip empty lists (`tags: []`) and/or false-y defaults (`flagged: false`)? Or strictly just `null`?
- Interaction with field selection: if an agent explicitly requests a field via `fields` and it's null, should it still be omitted? (Likely yes — the agent asked for the field "if it has a value", not "always include it".)

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
- Omitting `fields` returns curated default set, not everything
- Projection doesn't affect filtering
- Null fields omitted from responses by default
- Notes append adds text with newline separator to existing note
- Notes append on empty note sets the note (no leading newline)
- Validation error when both top-level `note` and `actions.note` are provided

## Tools After This Milestone

Eleven (unchanged from v1.3). No new tools — all enhancements to existing read and edit tools.
