# Phase 53: Response Shaping - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

All tool responses are leaner and agents control which fields list tools return. Ships stripping, inherited rename, field selection (`include`/`only`), and count-only mode as one coherent response-shaping layer in a new `server/` package. Service layer returns full Pydantic models unchanged — all shaping is a presentation concern.

</domain>

<decisions>
## Implementation Decisions

### Inherited field rename
- **D-01:** Full Python rename — `effective_*` → `inherited_*` at the model level (`ActionableEntity`, `Task`). `to_camel` alias generator produces `inheritedDueDate` etc. automatically. No serialization alias tricks.
- Mechanical find-and-replace across models, mappers (hybrid + bridge_only), service, tests, golden master normalization.
- Pre-release, no compat — no migration concern.
- Description constants renamed: `EFFECTIVE_FLAGGED` → `INHERITED_FLAGGED`, etc.

### Server package restructure
- **D-02:** Moderate split. `server.py` → `server/` package:
  - `server/__init__.py` — `create_server()` + exports
  - `server/handlers.py` — all 11 tool handlers
  - `server/lifespan.py` — `app_lifespan` context manager
  - `server/projection.py` — stripping + field selection logic

### Response stripping
- **D-03:** Entity-level stripping. Each entity dict (Task, Project, Tag, Folder, Perspective) is stripped individually after serialization. Envelope fields (`total`, `hasMore`, `warnings`, `status`, `success`) are structurally outside stripping scope.
- Stripped values: `null`, `[]`, `""`, `false`, `"none"`. Never stripped: `availability`.
- Stripping applies to: `get_*` tools, `get_all`, all `list_*` tools (on items).
- **No stripping on write results** — `AddTaskResult`, `EditTaskResult` are result envelopes, not entities.
- **No stripping exception for `only`** — stripping is universal, even when fields are explicitly requested. Agent knows its field list; absence is unambiguous.
- Strip on `get_*` tools too — absent field means not set. Tool descriptions document available fields so agents know what *could* be there.

### Field group definitions
- **D-04:** Field group definitions live in `config.py` (per spec). Pure data constants — group names mapped to field name sets. `server/projection.py` imports and applies them.
- Groups: `notes`, `metadata`, `hierarchy`, `time`, `review` (projects only), `*` (everything).
- Default fields defined per entity type (tasks, projects).

### Separate include types per tool
- **D-04b:** `include` parameter uses different Literal types per tool — `TaskFieldGroup` and `ProjectFieldGroup`. Projects additionally support `"review"`. This means two separate query model fields, not a shared type.
  ```python
  TaskFieldGroup = Literal["notes", "metadata", "hierarchy", "time", "*"]
  ProjectFieldGroup = Literal["notes", "metadata", "hierarchy", "time", "review", "*"]
  ```
- The `include` Field description is shared (one constant) — group details are in the tool description, not the field description.

### Field group validation
- **D-05:** Valid `only` field names derived from union of all field groups (defaults + all opt-in groups). No separate "all fields" constant.
- **Enforcement test** guarantees every model field appears in exactly one group, and every group field exists on the model. Catches drift in both directions.
- Invalid `only` names → warning in response (not error). Invalid `include` group names → validation error (via Literal type — Pydantic rejects unknown values automatically).
- **Case-insensitive matching** on `only` field names — more resilient, not documented to agents (implementation detail).

### `include` + `only` conflict handling
- **D-06:** ~~Validation error~~ → **Warning with `only` taking precedence**.
  - **MILESTONE SPEC CHANGE:** Original spec says "mutually exclusive — validation error." Changed to: apply `only`, ignore `include`, add educational warning.
  - **Rationale (round-trip cost):** An error wastes a full round trip (agent retries). A warning teaches equally well but the agent still gets results. The warning is not silent — it's explicit: *"include and only are mutually exclusive. include was ignored because only was provided. Use one or the other."*
  - Consistent with existing patterns: `["all", "available"]` in availability → warning, not error.

### Stripping and projection ordering
- **D-07:** Strip then project. Clean the entity first (remove falsy values), then select requested fields. The result is identical either way, but strip-then-project is the natural pipeline order. Stripping doesn't need to know about field selection.

### `limit: 0` (count-only mode)
- **D-08:** Pass through naturally. No special-casing at any layer. SQL `LIMIT 0` is valid and returns no rows. The repo count query still runs. `ListRepoResult(items=[], total=N, has_more=N > 0)` comes back naturally. Currently no `ge=1` constraint on `limit` — `0` is already valid at the Pydantic level.
- Update `LIMIT_DESC` to mention count-only behavior.

### Response shaping application pattern
- **D-09:** Explicit per handler, not middleware. Each tool handler calls the appropriate shaping function from `server/projection.py`:
  - `get_*` tools → `strip_entity()`
  - `get_all` → `strip_all_entities()`
  - `list_tasks`, `list_projects` → `shape_list_response()` (project + strip)
  - `list_tags`, `list_folders`, `list_perspectives` → strip items only (no field selection per spec)
  - `add_tasks`, `edit_tasks` → return as-is (no shaping)
- Different tools clearly apply different transforms. 3-4 lines per handler.

### Tool description updates
- **D-10:** `include` groups are documented **in the tool description** (one line per group, with field contents). `only` is documented **only in its Field description** — it's straightforward enough that the field-level docs suffice. `include` is more complex and benefits from being visible in the tool description alongside group contents.
  - All `effective*` references → `inherited*` in tool descriptions.
  - Stripping note added to all read tool descriptions.
  - `inherited*` explanation added: "value inherited from hierarchy, both direct and inherited can coexist, inherited fields are read-only."
  - Count-only tip: "use limit: 0 to get {items: [], total: N} without fetching data."
  - Follows existing pattern: tool descriptions stay scannable, Field-level docs carry precision.

### Agent-facing description text (verbatim)
- **D-11:** Agreed verbatim text for new/updated description constants:

  **`INCLUDE_FIELD_DESC`** (shared, used on both `ListTasksQuery.include` and `ListProjectsQuery.include`):
  ```
  Add field groups to the response, on top of defaults.
  See tool description for available groups.
  ```

  **`ONLY_FIELD_DESC`** (shared):
  ```
  Return only these fields (plus id, always included).
  Mutually exclusive with include.
  Use case: targeted high-volume queries (prefer include for most use cases).
  Null/empty values are still stripped — absent field means not set.
  ```

  **`INHERITED_FIELD_DESC`** (one shared constant for all 6 inherited fields):
  ```
  Inherited from parent hierarchy when not set directly on this entity.
  ```

  **`LIMIT_DESC`** (updated):
  ```
  Max items to return. Pass null to return all. Tip: pass 0 for count only.
  ```

  **`_STRIPPING_NOTE`** (fragment for tool descriptions):
  ```
  Response stripping: null values, empty arrays, empty strings,
  false booleans, and "none" urgency are omitted. Absent field = not set.
  ```

  **Principle:** Use reusable fragments (`_STRIPPING_NOTE`, `_DATE_INPUT_NOTE`, etc.) wherever there is opportunity for reuse across tool descriptions. Easier to maintain.

- **D-11b:** Draft tool descriptions for `list_tasks` and `list_projects` exist — see Specific Ideas section for the full drafts. These are the target output; the planner/executor should implement descriptions that match this structure.

### Claude's Discretion
- Exact stripping function implementation (recursive dict walk, or key-by-key check)
- Whether `strip_entity` and `shape_list_response` are separate functions or composed from primitives
- Test organization for stripping/projection (unit tests on functions vs integration tests through tools)
- Exact wording of `get_*` tool descriptions (follow existing `descriptions.py` patterns, update `effective*` → `inherited*`)
- Fragment extraction opportunities beyond `_STRIPPING_NOTE` — find and extract reusable fragments

</decisions>

<specifics>
## Specific Ideas

- The enforcement test for field groups should verify bidirectional sync: every model field in exactly one group, every group field exists on the model
- When documenting stripping in tool descriptions, keep it to one line — don't over-explain
- Use reusable fragments everywhere there's opportunity — `_STRIPPING_NOTE`, `_DATE_INPUT_NOTE`, inherited explanation, etc. Extract aggressively.

### Draft tool descriptions (target output)

These drafts are the target structure. The planner/executor should produce descriptions matching this format.

**list_tasks:**
```
List and filter tasks. All filters combine with AND logic.

Response stripping: null values, empty arrays, empty strings, false booleans, and "none" urgency are omitted. Absent field = not set.

include: optional array of field groups, additive on top of defaults.
  - "notes" — note
  - "metadata" — added, modified, completionDate, dropDate, url
  - "hierarchy" — parent, hasChildren
  - "time" — estimatedMinutes, repetitionRule
  - "*" — all fields
Default fields (always returned): id, name, availability, order, project, dueDate, inheritedDueDate, deferDate, inheritedDeferDate, plannedDate, inheritedPlannedDate, flagged, inheritedFlagged, urgency, tags.

Count-only: use limit: 0 to get {items: [], total: N} without fetching data.

All dates use local time. Timezone offsets are accepted. Date-only inputs (no time) use your OmniFocus default time for that field.

Returns a flat list. Reconstruct hierarchy using order (dotted notation, e.g. '2.3.1') and project {id, name}. Filtered results may have sparse order values because non-matching siblings are omitted. Inbox tasks use project id="$inbox".

inherited* fields: value inherited from the hierarchy (parent task, project, folder). Both direct and inherited can coexist — the sooner date applies. inherited fields are read-only; to edit, use the direct field (dueDate, not inheritedDueDate).

Response: {items, total, hasMore, warnings?}

Filters use inherited (effective) values — tasks inherit dates and flags from parent hierarchy.

completed/dropped filters include those lifecycle states in results (excluded by default). All other filters only restrict.
The 'soon' shortcut uses your OmniFocus due-soon threshold preference.

availability vs defer: 'available'/'blocked' answers 'can I act on this?' (covers all blocking reasons). defer answers 'what becomes available when?' (timing only).
```

**list_projects:**
```
List and filter projects. All filters combine with AND logic.

Response stripping: null values, empty arrays, empty strings, false booleans, and "none" urgency are omitted. Absent field = not set.

include: optional array of field groups, additive on top of defaults.
  - "notes" — note
  - "metadata" — added, modified, completionDate, dropDate, url
  - "hierarchy" — hasChildren
  - "time" — estimatedMinutes, repetitionRule
  - "review" — nextReviewDate, reviewInterval, lastReviewDate, nextTask
  - "*" — all fields
Default fields (always returned): id, name, availability, folder, dueDate, inheritedDueDate, deferDate, inheritedDeferDate, plannedDate, inheritedPlannedDate, flagged, inheritedFlagged, urgency, tags.

Count-only: use limit: 0 to get {items: [], total: N} without fetching data.

All dates use local time. Timezone offsets are accepted. Date-only inputs (no time) use your OmniFocus default time for that field.

inherited* fields: value inherited from the hierarchy (folder). Both direct and inherited can coexist — the sooner date applies. inherited fields are read-only; to edit, use the direct field (dueDate, not inheritedDueDate).

Response: {items, total, hasMore, warnings?}

nextTask (in review group): first available (unblocked) task — useful for identifying what to work on next.

Filters use inherited (effective) values — projects inherit dates and flags from parent folders.

completed/dropped filters include those lifecycle states in results (excluded by default). All other filters only restrict.
The 'soon' shortcut uses your OmniFocus due-soon threshold preference.
```

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone spec
- `.research/updated-spec/MILESTONE-v1.4.md` — Full spec for response stripping, inherited rename, field selection, count-only mode. **Note:** D-06 overrides the "validation error" decision for include+only conflict — use warning instead.

### Architecture
- `docs/architecture.md` — Three-layer architecture, write pipeline, method object pattern, field graduation pattern, service layer conventions
- `docs/architecture.md` §Field graduation — Pattern for notes graduation (Phase 55), tag actions precedent
- `docs/model-taxonomy.md` — Model naming conventions, base class hierarchy, decision tree for new models

### Current implementation (key files)
- `src/omnifocus_operator/server.py` — Current server module (will become `server/` package)
- `src/omnifocus_operator/config.py` — Where field group definitions will live (D-04)
- `src/omnifocus_operator/models/actionable_entity.py` — `effective_*` fields that become `inherited_*`
- `src/omnifocus_operator/models/task.py` — Task model with `effective_completion_date`
- `src/omnifocus_operator/agent_messages/descriptions.py` — All agent-facing description constants (rename `EFFECTIVE_*` → `INHERITED_*`)
- `src/omnifocus_operator/middleware.py` — Existing middleware pattern (reference, not modified)
- `src/omnifocus_operator/contracts/use_cases/list/common.py` — `ListResult[T]` envelope structure

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `middleware.py` — existing `ToolLoggingMiddleware` and `ValidationReformatterMiddleware` as reference for cross-cutting patterns (though D-09 chose explicit per-handler for stripping)
- `config.py` — established pattern for centralized constants (`DEFAULT_LIST_LIMIT`, `SYSTEM_LOCATIONS`, fuzzy match params)
- `descriptions.py` — all agent-facing text centralized with AST enforcement tests. New `include`/`only`/stripping descriptions follow same pattern.
- `to_camel` alias generator on `OmniFocusBaseModel` — handles `inherited_*` → `inheritedDueDate` automatically after Python rename

### Established Patterns
- **Service returns full models, server shapes** — D-09 establishes this as the explicit contract. Service layer unchanged by this phase.
- **AST enforcement tests** — existing tests check Literal types on contracts, inline descriptions on agent-facing models. New field group sync test follows same structural-test-as-coupling-guarantee pattern.
- **`model_dump(by_alias=True)`** — standard serialization to camelCase dicts. Projection layer will use this to serialize entities before stripping/selecting fields.
- **ListResult envelope** — `items`, `total`, `has_more`, `warnings`. Projection layer extracts `items`, shapes them, reassembles the response dict.

### Integration Points
- **Tool handlers** — each handler in `server/handlers.py` calls projection functions. Return type changes from Pydantic model to `dict` for shaped responses.
- **Field group definitions in `config.py`** — consumed by `server/projection.py`, validated by enforcement test against model fields.
- **`descriptions.py`** — updated constants for inherited rename, new constants for `include`/`only` field descriptions, stripping note added to tool descriptions.

</code_context>

<deferred>
## Deferred Ideas

- Batch processing response shape (Phase 54) — `status: "success" | "error" | "skipped"` replaces `success: bool`. Stripping decisions here don't affect that.
- Notes graduation (Phase 55) — `actions.note.append`/`replace`. Separate phase, no interaction with response shaping.

</deferred>

---

*Phase: 53-response-shaping*
*Context gathered: 2026-04-14*
