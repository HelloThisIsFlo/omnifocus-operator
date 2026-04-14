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

### Field group validation
- **D-05:** Valid `only` field names derived from union of all field groups (defaults + all opt-in groups). No separate "all fields" constant.
- **Enforcement test** guarantees every model field appears in exactly one group, and every group field exists on the model. Catches drift in both directions.
- Invalid `only` names → warning in response (not error). Invalid `include` group names → validation error.

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
- **D-10:** Brief tip in tool descriptions, full detail in Field descriptions.
  - Tool descriptions get 1-2 line notes about `include`/`only`, stripping, `limit: 0`.
  - `include` and `only` Field descriptions carry full detail: group names, contents, mutual interaction, stripping behavior.
  - All `effective*` references → `inherited*` in tool descriptions.
  - Add stripping note to all read tool descriptions: *"Null, empty, and default values are stripped — absent field means not set."*
  - Follows existing pattern: tool descriptions stay scannable, Field-level docs carry precision.

### Claude's Discretion
- Exact stripping function implementation (recursive dict walk, or key-by-key check)
- Whether `strip_entity` and `shape_list_response` are separate functions or composed from primitives
- Test organization for stripping/projection (unit tests on functions vs integration tests through tools)
- Exact wording of tool descriptions (follow existing `descriptions.py` patterns)

</decisions>

<specifics>
## Specific Ideas

- `only` field description should make two things explicit: (1) takes precedence over `include`, (2) stripping still applies even on explicitly-requested fields
- The enforcement test for field groups should verify bidirectional sync: every model field in exactly one group, every group field exists on the model
- When documenting stripping in tool descriptions, keep it to one line — don't over-explain

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
