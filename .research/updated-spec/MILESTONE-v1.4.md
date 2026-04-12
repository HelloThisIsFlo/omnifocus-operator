# Milestone v1.4 -- Response Shaping, Batch Processing & Notes Append

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

**Problem:** List tool responses are bloated. Every task in a JSON array repeats all field names, includes ~8-10 null fields the agent doesn't care about, and returns fields the agent never asked for. A 50-task response wastes hundreds of tokens on structural noise.

**Fix:** Give agents control over response shape. Field selection picks *which* fields appear. A compact output format (CSV or null-stripped JSON — spike determines which) eliminates structural repetition. Together these can reduce response size 5-6x. Batch processing lifts the single-item constraint on write tools so agents can create/edit multiple tasks per call. Notes append enables incremental note updates without read-modify-write cycles.

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

### Batch Processing for Write Tools

Lift the single-item constraint on `add_tasks` and `edit_tasks`. Currently both tools accept an `items` array but enforce `len(items) == 1` at the handler level. The scaffolding for batch is already in place: error messages use `"Task {idx+1}: {field}"` format, progress reporting loops exist, and the service layer processes items sequentially.

**What changes:**
- Remove the `len(items) != 1` guard in both handlers
- Items are processed **serially within a batch** — one after the other, in order. This is controlled at the service layer.
- Each item gets its own result entry in the response
- No upper limit on batch size (bridge throughput is self-regulating)

**Hierarchy creation in batch: not supported.**
Batch items cannot reference other items in the same batch (no placeholder IDs, no "create parent then child in one call"). If an agent needs to create a 4-level hierarchy, it makes 4 sequential calls. This keeps the implementation simple and avoids a class of ordering/dependency bugs. The tool description should make this explicit.

**Open questions:**

**Partial failure semantics** — if item 3 of 5 fails:
- Option A: **Fail-fast** — stop at first error. Items 1-2 are already committed (bridge writes are immediate). Items 4-5 are skipped. Response includes results for 1-2 (success) and 3 (error), with a warning that 4-5 were not processed.
- Option B: **Best-effort** — continue processing 4-5 even after 3 fails. Response includes per-item success/error for all 5.
- Leaning toward fail-fast (simpler, predictable), but needs design discussion.

**Response format for batch results:**
- Array of per-item results, each with status (success/error) + data or error message
- How does this interact with the existing single-item response shape? Is it always an array now, even for batch-of-1?
- How does field selection apply to batch write responses?

**Serial execution across concurrent calls** — items within a single batch are serial (we control this). But what about two concurrent `edit_tasks` calls from different agent threads? The bridge processes osascript calls — is there an OS-level or OmniFocus-level serialization guarantee? If not, interleaved edits from separate batches could produce surprising results. This is flagged as a v1.6 concern (serial execution guarantee), but batch makes it more relevant. Document the limitation.

**Ordering guarantees within a batch** — serial execution means items are processed in array order. For `edit_tasks`, this means an agent could move task A, then move task B relative to A's new position — **but only if the second move re-queries** to find A's updated position. The current implementation already re-queries per operation (each pipeline instance reads fresh state). Document that array order is respected and edits see the results of prior items in the same batch.

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
- `add_tasks` and `edit_tasks` accept multiple items per call
- Batch items are processed serially in array order
- Batch response includes per-item result (success + data or error)
- Batch with cross-item references (hierarchy in one call) is rejected with a clear error — or documented as unsupported with guidance in the tool description
- Partial failure behavior is well-defined and documented (fail-fast or best-effort — open question)
- Notes append adds text with newline separator to existing note
- Notes append on empty note sets the note (no leading newline)
- Validation error when both top-level `note` and `actions.note` are provided

## Tools After This Milestone

Eleven (unchanged from v1.3). No new tools — all enhancements to existing read and edit tools.
