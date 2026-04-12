# Milestone v1.4 -- Response Shaping & Notes Append

## ⚠️ Pre-Planning Spike: CSV Output Format

**Before planning this milestone, run a deep dive on CSV serialization for list tools.**

JSON repeats field names for every item in a list — for 50 tasks with 8 fields, that's ~400 tokens of pure structural repetition. CSV eliminates this: one header row, then pure data. Estimated 1.5-2x token reduction on top of field selection, for ~5-6x total from raw JSON baseline.

**Why this matters for milestone scope:**
- If CSV lands, **null-stripping may be unnecessary** — an empty CSV cell is already zero overhead (no `"dueDate": null` syntax). The entire null-stripping feature might be subsumed.
- CSV + field selection is a natural pair: agent picks columns via `fields`, gets a clean table back.
- FastMCP may support a serialization hook/formatter — if so, CSV lives entirely at the output boundary with zero changes to service/repo layers.

**Spike should answer:**
- Does FastMCP support custom output formatters? What's the hook?
- How do nested objects flatten? (`parent.id` → `parent_id` column)
- How do multi-value fields serialize? (tags → pipe-delimited `"Planning|Urgent"`)
- Is CSV only for `list_*` tools, or also useful for `get_*` single-item tools?
- Does this make null-stripping redundant?
- Agent experience: does an LLM work better with CSV or JSON for list results?

**Outcome:** spike results determine whether this milestone is {field selection + CSV + notes append} or {field selection + null-stripping + notes append}.

---

## Goal

Agents get control over what data they receive and gain a new write capability. Field selection reduces token usage by controlling *which* fields appear. A compact output format (CSV or null-stripped JSON — see spike above) reduces structural overhead. Notes append enables incremental note updates without read-modify-write cycles. No new data paths — all within existing architecture.

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

### Compact Output Format (spike-dependent)

**Option A: CSV format** (preferred if spike validates)
- `format: "csv"` parameter on `list_*` tools
- One header row with field names, then one row per item
- Nested objects flatten: `parent.id` → `parent_id` column
- Multi-value fields join with delimiter: tags → `"Planning|Urgent"`
- Nulls are empty cells — no explicit representation needed
- JSON remains the default; CSV is opt-in

**Option B: Null-stripping** (fallback if CSV doesn't work out)
- Null fields omitted from JSON responses by default
- Orthogonal to field selection — compounds with it
- Open questions: parameter name, default behavior, strip empty lists too?

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
- Compact output reduces token usage for list results (CSV or null-stripping — spike determines which)
- Notes append adds text with newline separator to existing note
- Notes append on empty note sets the note (no leading newline)
- Validation error when both top-level `note` and `actions.note` are provided

## Tools After This Milestone

Eleven (unchanged from v1.3). No new tools — all enhancements to existing read and edit tools.
