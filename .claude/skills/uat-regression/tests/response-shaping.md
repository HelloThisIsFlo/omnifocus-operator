---
suite: response-shaping
display: Response Shaping
test_count: 14

discovery:
  needs:
    - type: project
      label: proj-a
      filters: [active]

setup: |
  ### Tasks
  UAT-ResponseShaping (inbox parent)
    T1-Minimal                 (no tags, no due/defer/planned, not flagged, no note, no estimated minutes)
    T2-WithNote                (note: "brief")
    T3-WithDue                 (dueDate: 2099-01-01T10:00:00)

  Create via a single `add_tasks` call:
  ```json
  {"items": [
    {"name": "UAT-ResponseShaping"},
    {"name": "T1-Minimal",  "parent": {"task": {"name": "UAT-ResponseShaping"}}},
    {"name": "T2-WithNote", "parent": {"task": {"name": "UAT-ResponseShaping"}}, "note": "brief"},
    {"name": "T3-WithDue",  "parent": {"task": {"name": "UAT-ResponseShaping"}}, "dueDate": "2099-01-01T10:00:00"}
  ]}
  ```

  Record the 4 IDs from the response — `T1.id`, `T2.id`, `T3.id`, and the parent `UAT-ResponseShaping.id`.
---

# Response Shaping Test Suite

Cross-cutting contract tests for Phase 53 response shaping — universal stripping, `include`/`only` field selection, `limit: 0` count-only mode, and batch per-item absence semantics. Every list/get tool participates in these contracts; this suite uses a representative sample rather than retesting every tool.

## Conventions

- **Inbox only** for task setup. T1/T2/T3 live under `UAT-ResponseShaping`.
- **Behavioral assertions for warnings/errors.** Even where the spec locks verbatim text (e.g., `include`+`only` conflict per D-06), we assert only that the message is **present**, **fluent from an agent's perspective**, and **leaks no internals** (`type=`, `pydantic`, `input_value`, `_Unset`). If the text feels awkward, file a separate todo — don't encode exact strings here.
- **Absence vs null.** The contract is that unset fields are **absent from the response**, not set to `null`/`false`/`""`/`[]`. Never assert `field: null` — assert `"field" not in entity`.
- **`availability` is never stripped.** Every entity that has an `availability` field emits it, even when all other fields are stripped. This is the one explicit exception to universal stripping.
- **Stripping applies to read responses only.** `add_tasks` / `edit_tasks` return typed write-result envelopes with their own per-item absence rules (Test 6 covers this).

## Tests

### 1. Universal Stripping

#### Test 1a: list_tasks strips null/empty/false on task items
1. `list_tasks` with `{"search": "T1-Minimal", "limit": 5}`
2. Locate the item where `name == "T1-Minimal"` in the response `items` array.
3. PASS if:
   - `"tags"` key is **absent** from the item (not `tags: []`)
   - `"flagged"` key is **absent** (not `flagged: false`)
   - `"dueDate"` / `"deferDate"` / `"plannedDate"` keys are **absent** (not `null`)
   - `"inheritedDueDate"` / `"inheritedDeferDate"` / `"inheritedPlannedDate"` / `"inheritedFlagged"` keys are **absent** (T1 has no ancestor setting these)
   - `"urgency"` key is **absent** (`"none"` is stripped)

#### Test 1b: list_projects strips null/empty/false on project items
1. `list_projects` with `{"search": "<proj-a.name substring>", "limit": 5}`
2. Locate the item matching `proj-a`.
3. PASS if: for every field the project has unset (inspect the item — whatever `proj-a` has set will vary), those keys are **absent** rather than `null`/`false`/`[]`. Concretely verify at least TWO of the following that are unset on your `proj-a`: `flagged`, `tags`, `dueDate`, `inheritedDueDate`, `deferDate`, `completionDate`, `dropDate`.

#### Test 1c: get_task strips on single-entity form
1. `get_task` with `T1.id`
2. PASS if: same absence pattern as Test 1a — no `tags`, no `flagged`, no date keys, no `urgency` on the returned entity (no `items` wrapper; `get_task` returns the entity directly).

#### Test 1d: availability always present (never stripped)
1. `list_tasks` with `{"search": "T1-Minimal", "limit": 5}`, then `get_task(T1.id)`.
2. PASS if: **both** responses include `"availability"` on T1 with a non-empty string value (e.g., `"available"`). `availability` is the sole member of `NEVER_STRIP` — even when every other falsy/empty field is absent, this one remains.

### 2. `include` Parameter

#### Test 2a: include: ["notes"] adds note-related fields
1. `list_tasks` with `{"search": "T2-WithNote", "include": ["notes"], "limit": 5}`
2. PASS if: the matching item includes `"note": "brief"`. (Default response omits `note`; `include: ["notes"]` is what makes it appear.)

#### Test 2b: include: ["*"] returns the full field set
1. `list_tasks` with `{"search": "T2-WithNote", "include": ["*"], "limit": 5}`
2. PASS if: the matching item includes non-default fields on top of the defaults — at minimum assert presence of `"note"` AND at least one of `"added"` / `"modified"` / `"url"`. (Stripping still applies, so fields with null/falsy values remain absent — that's expected. The test is that `*` expands the field superset, not that every field appears.)

#### Test 2c: include: ["invalid_group"] errors with a fluent, agent-friendly message
Run INDIVIDUALLY (will error):
1. `list_tasks` with `{"include": ["invalid_group"], "limit": 5}`
2. PASS if:
   - Call errors (validation error raised by the server).
   - Error message is **fluent** — reads as a direct explanation to an agent, not a raw Pydantic dump.
   - Error message **names the offending value** (`"invalid_group"`) so the agent can correct its input.
   - Error message **leaks no internals** — no `type=`, `pydantic`, `input_value`, `_Unset`, `Literal[...]` raw expansion.

### 3. `only` Parameter

#### Test 3a: only: ["id", "dueDate"] returns only those fields
1. `list_tasks` with `{"search": "T3-WithDue", "only": ["id", "dueDate"], "limit": 5}`
2. PASS if: the matching item has exactly `id` and `dueDate` as its keys (no `name`, no `availability`, no `project`, no other default fields). `id` is always included per FSEL-05, and `dueDate` was explicitly requested.

#### Test 3b: only: ["invalid_field"] succeeds with a warning
1. `list_tasks` with `{"search": "T1-Minimal", "only": ["invalid_field"], "limit": 5}`
2. PASS if:
   - Call **succeeds** (no error).
   - Response contains a `warnings` entry (behavioral assertion — **present, fluent, names `"invalid_field"`**, no pydantic internals).
   - The matching item returns `{id}` only (invalid field ignored, `id` still always included).

#### Test 3c: only does not prevent stripping
1. `list_tasks` with `{"search": "T1-Minimal", "only": ["dueDate"], "limit": 5}`
2. PASS if: the matching item has **no `dueDate` key** (T1-Minimal has `dueDate: null`, so stripping omits it) and only `{id}` remains. Proves: strip happens regardless of whether the field was explicitly requested — absence means not set, even under `only`.

### 4. `include` + `only` Conflict

#### Test 4: both specified → warning, `only` wins
1. `list_tasks` with `{"search": "T2-WithNote", "include": ["notes"], "only": ["name"], "limit": 5}`
2. PASS if:
   - Call **succeeds**.
   - Response contains a warning (behavioral assertion — **present, fluent**, names both `include` and `only`, explains which one wins; no internals leak).
   - The matching item has **exactly `{id, name}`** — no `note` (which `include: ["notes"]` would have added, but `only` overrode it).

### 5. `limit: 0` Count-Only Mode

#### Test 5a: list_tasks with limit: 0 returns count-only
1. `list_tasks` with `{"flagged": true, "limit": 0}` (any filter — the test is about envelope shape, not which tasks match).
2. PASS if:
   - `items` is `[]` (empty array).
   - `total` is present and is an integer ≥ 0.
   - `hasMore` is present and reflects `total > 0`.
   - No data rows returned even if `total` is large.

#### Test 5b: envelope fields always present on empty items
1. `list_tasks` with `{"search": "ZZZ-nothing-matches-this-XYZ", "limit": 10}` (a query guaranteed to match zero tasks).
2. PASS if: response still includes `items: []`, `total: 0`, `hasMore: false`. Envelope fields (`total`, `hasMore`) are never stripped regardless of whether items is empty.

### 6. Batch Per-Item Absence Semantics

#### Test 6: add_tasks batch with one failing item — per-item shape uses absence, not null
1. Locate a tag name that definitively does NOT exist in the OmniFocus database (pick something like `"UAT-nonexistent-tag-xyz-999"` — do NOT create this tag first). This will cause the item using it to fail.
2. `add_tasks` with a 3-item batch:
   ```json
   {"items": [
     {"name": "T6-BatchA", "parent": {"task": {"name": "UAT-ResponseShaping"}}},
     {"name": "T6-BatchB", "parent": {"task": {"name": "UAT-ResponseShaping"}}, "tags": ["UAT-nonexistent-tag-xyz-999"]},
     {"name": "T6-BatchC", "parent": {"task": {"name": "UAT-ResponseShaping"}}}
   ]}
   ```
3. Inspect the response array (expected shape: 3 per-item result envelopes).
4. PASS if:
   - Item 1 (`status: "success"`): has `id` and `name` keys; **no** `error` key; **no** `warnings` key (or `warnings: []` absent).
   - Item 2 (`status: "error"`): has `error` key; **no** `id` key (nothing was created, so there's no OmniFocus ID to return — field is **absent**, not `id: null`); **no** `name` key (or equivalent minimal presence per the contract — absence preferred over null).
   - Item 3 (`status: "success"`): same absence pattern as item 1.
   - Cleanup: T6-BatchA and T6-BatchC are created in inbox under `UAT-ResponseShaping` — they'll be consolidated by the umbrella cleanup.

## Report Table Rows

| # | Test | Description | Result |
|---|------|-------------|--------|
| 1a | Strip: list_tasks | T1-Minimal item omits `tags`/`flagged`/date keys (absent, not null/false/[]) | |
| 1b | Strip: list_projects | `proj-a` item omits its unset fields (keys absent, not null/false/[]) | |
| 1c | Strip: get_task | Single-entity form follows same stripping as list items | |
| 1d | availability never stripped | `list_tasks` AND `get_task` emit `availability` on T1 even when everything else is stripped | |
| 2a | include: notes | `include: ["notes"]` surfaces `note` field not in defaults | |
| 2b | include: * | `include: ["*"]` expands to full field superset (note + metadata fields appear) | |
| 2c | include: invalid_group | Invalid group → fluent validation error, names offending value, no pydantic internals | |
| 3a | only: id + dueDate | `only: ["id", "dueDate"]` returns exactly `{id, dueDate}`; no other defaults | |
| 3b | only: invalid_field | Invalid field → call succeeds with fluent warning; naming the invalid field, no internals leak | |
| 3c | only doesn't bypass strip | `only: ["dueDate"]` on unset-due task still omits `dueDate` (strip before project) | |
| 4 | include + only conflict | Both specified → fluent warning, `only` wins, response = `{id, name}` | |
| 5a | limit: 0 count-only | `{items: [], total: N, hasMore}` — no data rows even when matches exist | |
| 5b | envelope on empty items | Zero-match query still emits `items: []`, `total: 0`, `hasMore: false` | |
| 6 | Batch per-item absence | Success items omit `error`/`warnings`; failed item omits `id`/`name` (absence, not null) | |
