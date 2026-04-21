# Milestone v1.4 -- Response Shaping, Batch Processing & Notes Graduation

## Goal

**Problem:** List tool responses are bloated. Every task in a JSON array repeats all field names, includes ~8-10 null fields the agent doesn't care about, and returns fields the agent never asked for. A 50-task response wastes hundreds of tokens on structural noise. Write tools are limited to one item per call. Notes can only be fully replaced, requiring read-modify-write for appends.

**Fix:** Give agents control over response shape. Field groups (`include`) let agents opt into extra detail. Individual field selection (`only`) enables surgical precision for high-volume queries. Universal stripping eliminates null/empty/falsy noise from every response. Batch processing lifts the single-item constraint on write tools. Notes graduate to the `actions` block, gaining append semantics.

## What to Build

### Response Stripping (Universal)

**Always on, no toggle, all tool responses.** Stripped values:
- `null` (any field)
- `[]` (empty arrays, e.g. tags)
- `""` (empty strings, e.g. note)
- `false` (booleans: `flagged`, `inheritedFlagged`, `hasChildren`)
- `"none"` (urgency)

Stripping applies to **entity fields only** — not to result envelope fields (`hasMore`, `total`, `status`, etc.).

**Never stripped:** `availability` — always informative, even when `"available"`.

Absent field = not set / default / empty. No parameter needed.

**Rationale:** ~10-12 null fields per task x 80 tasks = 800+ wasted tokens. No list-query use case needs explicit nulls/falsy values. With aggressive stripping, the default field set can be generous — most fields are stripped for most tasks.

### Inherited Field Rename (Universal)

`effective*` fields renamed to `inherited*` across all tools:
- `effectiveDueDate` → `inheritedDueDate`
- `effectiveDeferDate` → `inheritedDeferDate`
- `effectivePlannedDate` → `inheritedPlannedDate`
- `effectiveFlagged` → `inheritedFlagged`
- `effectiveCompletionDate` → `inheritedCompletionDate`
- `effectiveDropDate` → `inheritedDropDate`

"Inherited" = value from anywhere above in the **hierarchy** (parent task, project, folder — not just direct parent).

**Three states per field** (e.g. due date):
- `dueDate` present → set directly on this task
- `inheritedDueDate` present (no `dueDate`) → inherited from hierarchy
- Neither present → no due date at all
- Both can coexist (they may differ — the sooner one applies)

Read/write symmetry: `dueDate` = what you'd edit; `inheritedDueDate` = what the hierarchy imposes (read-only).

### Field Selection (`include` and `only`)

Two top-level parameters on `list_tasks` and `list_projects` only. Not on `get_*` tools (always return full stripped entities), not on `get_all`.

#### `include` — Semantic Field Groups

Additive on top of defaults. Agent opts into extra detail by group name.

**Default fields — tasks** (always returned):
`id`, `name`, `availability`, `order`, `project`, `dueDate`, `inheritedDueDate`, `deferDate`, `inheritedDeferDate`, `plannedDate`, `inheritedPlannedDate`, `flagged`, `inheritedFlagged`, `urgency`, `tags`

**Default fields — projects** (additionally):
`folder`

**Opt-in groups** (`include` is additive on top of defaults):
- **`notes`** — `note`
- **`metadata`** — `added`, `modified`, `completionDate`, `dropDate`, `inheritedCompletionDate`, `inheritedDropDate`, `url`
- **`hierarchy`** — `parent`, `hasChildren`
- **`time`** — `estimatedMinutes`, `repetitionRule`
- **`review`** — `nextReviewDate`, `reviewInterval`, `lastReviewDate`, `nextTask` (**projects only** — not available on `list_tasks`)
- **`*`** — everything, all groups

Available groups differ per tool: `list_tasks` has `notes`, `metadata`, `hierarchy`, `time`, `*`. `list_projects` additionally has `review`.

**Invalid group names → validation error** (fail-fast). Small fixed set — a typo is likely a real mistake.

Group definitions centralized in `config.py`.

#### `only` — Individual Field Selection

Precise field-level control for targeted queries on large result sets. Uses camelCase field names (matching JSON output).

- `only` always includes `id` regardless of what's listed
- Mutually exclusive with `include` — providing both is a validation error
- **Invalid field names → warning in response** (unlike `include` which errors). Larger field set — typos are more likely and the agent may be exploring available fields.
- Should be used sparingly — prefer `include` for most queries

**Examples:**
```json
// Daily review triage: defaults are enough
{}

// Project review: defaults + notes + review info
{"include": ["notes", "review"]}

// Targeted: just project membership for 200 tasks
{"only": ["project"]}

// Everything
{"include": ["*"]}
```

**Documentation strategy:** Field-level JSON Schema descriptions on `include` and `only` explain what each does and their interaction. Tool description gets a brief tip: prefer `include`, use `only` for targeted high-volume queries.

#### Scope

- `list_tasks`, `list_projects` — support `include` and `only`
- `list_tags`, `list_folders`, `list_perspectives` — no field selection (already compact)
- `get_task`, `get_project`, `get_tag` — always return full stripped entities
- `get_all` — no field selection (snapshot tool), stripping applies

#### Architecture

Projection is a **presentation concern** — lives at the server layer, not service. Service returns full Pydantic models; the server's projection layer does `model_dump(include=...)` and returns a plain dict. This sidesteps `outputSchema` drift (MCP clients strip outputSchema anyway; available fields documented in tool description).

### Count-Only Mode

No dedicated parameter — use `limit: 0`. Returns `{"items": [], "total": N, "hasMore": <total > 0>}`. Document this in the tool description.

### Batch Processing for Write Tools

Lift the single-item constraint on `add_tasks` and `edit_tasks`. The scaffolding is already in place: error messages use `"Task {idx+1}: {field}"` format, progress reporting loops exist, and the service layer processes items sequentially.

**What changes:**
- Remove the `len(items) != 1` guard in both handlers
- Items processed **serially within a batch** in array order
- Hard limit: **50 items** per call, enforced via Pydantic model validator (`maxItems`), configurable in `config.py`
- Input shape unchanged — `items: [{...}]` as before

**Hierarchy creation in batch: not supported.** Batch items cannot reference other items in the same batch. If an agent needs to create a 4-level hierarchy, it makes 4 sequential calls. Document in tool description.

#### Failure Semantics

Different strategy per tool:

**`add_tasks` — best-effort.** Every item is processed regardless of earlier failures. Each item produces `"success"` or `"error"`. Rationale: created tasks are always independent.

**`edit_tasks` — fail-fast.** Stop at first error. Earlier items are already committed (bridge writes are immediate). Later items get `"skipped"` status. Rationale: moves can create implicit ordering dependencies — if item 2's move fails, item 3's positional reference may resolve against stale state.

**Same-task in batch:** Allowed. Array order applies — edits to the same task are processed sequentially and each sees the prior's result.

#### Response Shape

Flat array of per-item results. `status` enum replaces `success: bool`:

```json
// add_tasks (best-effort) — item 2 fails, item 3 still processed
[
  {"status": "success", "id": "abc", "name": "Buy milk", "warnings": ["Tag already on task"]},
  {"status": "error", "error": "Invalid tag 'Foo'"},
  {"status": "success", "id": "ghi", "name": "Call dentist"}
]

// edit_tasks (fail-fast) — item 2 fails, items 3-4 skipped
[
  {"status": "success", "id": "abc", "name": "Buy milk"},
  {"status": "error", "id": "def", "error": "Task not found"},
  {"status": "skipped", "id": "ghi", "warnings": ["Skipped: item 2 failed"]},
  {"status": "skipped", "id": "jkl", "warnings": ["Skipped: item 2 failed"]}
]
```

- `name` present on success only — absent on error/skipped
- `id` present on success and edit errors/skips (known from input). Absent on failed `add_tasks` items (no OmniFocus ID exists yet)
- `warnings` array available on all status types
- Existing per-item warnings (tag guidance, lifecycle notes, etc.) preserved on success items

#### Concurrency

Concurrent batch calls from separate agent threads are not serialized at the server level. Items within a single batch are serial; interleaving across batches is possible. Document as a known limitation — serial execution guarantee is a v1.7 concern.

### Notes Graduation

Notes graduate from top-level setter to `actions.note` block — second field graduation after tags (v1.2), following the pattern documented in architecture.md.

**Top-level `note` field removed from `edit_tasks`.** Only the actions block remains. `add_tasks` keeps its top-level `note` field — initial note content is a simple setter, not a graduated operation.

```json
{
  "id": "xyz",
  "actions": {
    "note": { "append": "Added during daily review on 2026-03-17" }
  }
}
```

**Operations:**
- `actions.note.append` — append text to existing note with `\n\n` separator (paragraph break)
- `actions.note.replace` — replace entire note

**Type conventions** (following tag action pattern):
- `append`: `Patch[str]` — null rejected by type, `""` is a no-op
- `replace`: `PatchOrClear[str]` — null and `""` both clear the note

**Edge cases:**
- Append on empty/whitespace-only note → set directly (no leading separator)
- Whitespace-only existing note treated as empty (strip and check)
- Note action alone is valid — no tags/move required in the actions block

## Key Acceptance Criteria

**Response shaping:**
- Universal stripping active on all tool responses (null, `[]`, `""`, `false`, `"none"`)
- `availability` never stripped
- `inherited*` rename applied universally
- `include` groups additive on curated defaults (`list_tasks`, `list_projects`)
- `only` field-level selection with `id` always included
- `include` and `only` mutually exclusive (validation error)
- Invalid group names → validation error
- `include: ["*"]` returns all fields
- Projection doesn't affect filtering (post-filter, pre-serialization)
- `limit: 0` returns count-only (`{items: [], total: N, hasMore: <total > 0>}`)
- Invalid `only` field names → warning in response
- Group definitions centralized in `config.py`

**Batch processing:**
- `add_tasks` and `edit_tasks` accept up to 50 items (Pydantic `maxItems`)
- `add_tasks`: best-effort — all items processed, per-item success/error
- `edit_tasks`: fail-fast — stop at first error, remaining items skipped
- Flat array response with `status: "success" | "error" | "skipped"`
- `name` on success only, absent on error/skipped
- `warnings` array on all result types
- Array order respected, edits see results of prior items
- Cross-item references not supported (documented in tool description)
- Concurrency limitation documented

**Notes graduation:**
- Top-level `note` removed from `edit_tasks`
- `actions.note.append` adds text with `\n\n` separator
- `actions.note.replace` replaces entire note
- null/`""` on replace clears the note
- Append on empty/whitespace-only note sets directly (no leading separator)

## Tools After This Milestone

Eleven (unchanged from v1.3). No new tools — all enhancements to existing tools.
