# Phase 44: Migrate list query filters to Patch semantics -- Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

All agent-facing list query filter fields migrate from `T | None = None` to `Patch[T] = UNSET`, so agents never see `null` as a valid filter input. Add `AvailabilityFilter` enums with `ALL` shorthand for ergonomic "include everything" queries. Add empty-list rejection. Normalize offset to `int = 0`. Repo-level queries are untouched.

</domain>

<decisions>
## Implementation Decisions

### Migration Rules
- **D-01:** Filter fields where null = omit = "no filter" (redundant) migrate to `Patch[T] = UNSET`. Schema shows only the base type, null becomes a validation error.
- **D-02:** `limit: int | None = DEFAULT_LIST_LIMIT` stays unchanged. Null = "no limit" is a genuinely distinct meaning from omit = "use default 50."
- **D-03:** `offset: int | None = None` becomes `int = 0`. Zero = "start from beginning" (always set, never null, never UNSET).
- **D-04:** `availability` fields keep their list type and real defaults. They do NOT become Patch fields.

### Error Message Templates (2 types)
- **D-05:** Filter-like fields (tags, search, project, etc.): `"'{field}' cannot be null. To skip this filter, simply omit the field."`
- **D-06:** Availability fields: `"'{field}' cannot be empty. Use 'all' to include every status, or omit for the default filter."`
- **D-07:** Generic empty-list for tags: `"'{field}' cannot be empty. To ignore this filter, simply omit the field."`

### Null Rejection -- Shared Helper
- **D-08:** New `reject_null_filters(data: dict, field_names: list[str])` helper in `_validators.py` alongside existing `validate_offset_requires_limit`. Rejects null on Patch fields before Pydantic sees them (avoids `_Unset` leak in error messages).
- **D-09:** Each query model calls `reject_null_filters` from a `model_validator(mode="before")` with its explicit list of Patch field names.
- **D-10:** Error template from D-05. One generic message for all filter-type Patch fields.
- **D-11:** `ValidationReformatterMiddleware` already filters `_Unset` from Pydantic errors as defense-in-depth (confirmed in `middleware.py` lines 95-123). The shared helper is the primary defense; middleware is the safety net.

### AvailabilityFilter with ALL Shorthand (new scope, folded in)
- **D-12:** New filter enums: `AvailabilityFilter`, `TagAvailabilityFilter`, `FolderAvailabilityFilter`. Each mirrors its core enum (`Availability`, `TagAvailability`, `FolderAvailability`) plus adds `ALL` value. Lives in new file `contracts/use_cases/list/_enums.py`.
- **D-13:** Query model fields change from `list[Availability]` to `list[AvailabilityFilter]` (and equivalents for Tag/Folder). Defaults stay the same (e.g., `[AvailabilityFilter.AVAILABLE, AvailabilityFilter.BLOCKED]`).
- **D-14:** `ALL` string value is lowercase `"all"` in the enum.
- **D-15:** Empty-list rejection via field_validator on each availability field, using error template from D-06.
- **D-16:** ALL expansion happens in the **service pipeline**, not the field_validator. Validator handles validation only (valid enum members, non-empty). Service handles business logic (expand ALL, emit warning, map to core enum for repo query).
- **D-17:** Mixed usage (`["all", "available"]`): accept, treat ALL as dominant (expand to full list), add **warning**: educational message telling the agent to just send `["all"]` by itself.
- **D-18:** Service maps `AvailabilityFilter` values to core `Availability` values when building repo query. Repo queries stay on core enums.

### Service Layer Translation (UNSET --> None)
- **D-19:** New `unset_to_none(value: T | _Unset) -> T | None` utility in `contracts/base.py` alongside `is_set()`. Returns None for UNSET, passes through everything else.
- **D-20:** Pipeline resolution methods (e.g., `_resolve_tags`, `_resolve_project`, `_resolve_folder`) change guard from `if field is None: return` to `if not is_set(field): return`.
- **D-21:** `_build_repo_query()` methods use `unset_to_none()` for pass-through fields: `flagged=unset_to_none(self._query.flagged)`, etc.
- **D-22:** `resolve_inbox` signature stays `(bool | None, str | None)`. Pipeline translates before calling: `unset_to_none(self._query.in_inbox)`, `unset_to_none(self._query.project)`. Resolver never learns about UNSET.
- **D-23:** Repo-level queries (`ListTasksRepoQuery`, etc.) are completely untouched. They remain `T | None` internal contracts.

### review_due_within Validator Simplification
- **D-24:** Remove `v is None` passthrough (null is no longer valid). Remove `isinstance(v, ReviewDueFilter)` guard (redundant -- falls through to Pydantic which accepts it).
- **D-25:** Tighten to catch-all: if not a string or dict/ReviewDueFilter, raise educational ValueError. This prevents null, numbers, booleans, arrays from hitting Pydantic's union resolver.
- **D-26:** UNSET never arrives at the validator (Pydantic doesn't call `mode="before"` validators for default values when `validate_default` is False, which is the project default).

### Offset Validator Update
- **D-27:** `validate_offset_requires_limit` changes from `if offset is not None and limit is None` to `if offset > 0 and limit is None`. Offset is now always an int (default 0).

### Integration Gotcha -- matches_inbox_name
- **D-28:** `_ListProjectsPipeline._check_inbox_search_warning()` passes `self._query.search` directly to `matches_inbox_name()`. After migration, an omitted search is UNSET (not None). The function's `if value is None: return False` guard would NOT catch UNSET, causing a crash on `.lower()`. Must wrap with `unset_to_none()` or add `is_set()` guard before calling. Same pattern applies anywhere query fields are accessed outside `_build_repo_query` or resolution methods.

### Claude's Discretion
- Internal naming of the availability expansion helper methods in service pipelines
- Whether the three AvailabilityFilter enums share a base or are standalone
- Test organization for the new validators and ALL expansion logic
- Exact wording of the mixed-ALL warning message

### Folded Todos
- **Migrate list query filters to Patch semantics** (from `.planning/todos/pending/2026-04-07-migrate-list-query-filters-to-patch-semantics-eliminate-null.md`): This todo IS the design spec for the phase. Contains the full per-field inventory and migration rules. All decisions here build on its foundation.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design Spec (primary)
- `.planning/todos/pending/2026-04-07-migrate-list-query-filters-to-patch-semantics-eliminate-null.md` -- Full per-field inventory, migration rule table, per-model breakdown. The authoritative field-by-field spec.

### Architecture & Patterns
- `docs/architecture.md` -- Three-layer architecture, method object pattern for service pipelines
- `docs/model-taxonomy.md` -- Model naming conventions. `<noun>Filter` convention for query-side concepts. Patch/PatchOrClear semantics. QueryModel vs CommandModel base classes.
- `docs/structure-over-discipline.md` -- Schema = documentation philosophy

### Contract Layer (modification targets)
- `src/omnifocus_operator/contracts/base.py` -- `Patch`, `UNSET`, `is_set()`. Add `unset_to_none()` here.
- `src/omnifocus_operator/contracts/use_cases/list/tasks.py` -- `ListTasksQuery` (6 fields migrating)
- `src/omnifocus_operator/contracts/use_cases/list/projects.py` -- `ListProjectsQuery` (4 fields migrating)
- `src/omnifocus_operator/contracts/use_cases/list/tags.py` -- `ListTagsQuery` (1 field migrating)
- `src/omnifocus_operator/contracts/use_cases/list/folders.py` -- `ListFoldersQuery` (1 field migrating)
- `src/omnifocus_operator/contracts/use_cases/list/perspectives.py` -- `ListPerspectivesQuery` (1 field migrating)
- `src/omnifocus_operator/contracts/use_cases/list/_validators.py` -- Add `reject_null_filters()` and `validate_non_empty_list()` here

### Service Layer (translation targets)
- `src/omnifocus_operator/service/service.py` -- All 5 list pipelines. Translation points: resolution guards, `_build_repo_query`, `matches_inbox_name` calls.
- `src/omnifocus_operator/service/resolve.py` -- `resolve_inbox` signature stays `(bool | None, str | None)`. No changes.

### Error Messages
- `src/omnifocus_operator/agent_messages/errors.py` -- Add new templates here (filter null, availability empty, mixed ALL warning)

### Existing Patterns (reference for consistency)
- `src/omnifocus_operator/contracts/use_cases/add/tasks.py` -- AddTaskCommand.parent null rejection pattern (field_validator, mode="before")
- `src/omnifocus_operator/contracts/shared/actions.py` -- MoveAction null rejection pattern (shared validator for multiple fields)
- `src/omnifocus_operator/middleware.py` -- ValidationReformatterMiddleware `_Unset` filtering (lines 95-123)
- `src/omnifocus_operator/models/enums.py` -- Core Availability, TagAvailability, FolderAvailability enums

### Prior Phase Context
- `.planning/phases/41-write-pipeline-inbox-in-add-edit/41-CONTEXT.md` -- Established Patch pattern, null rejection, PatchOrNone elimination
- `.planning/phases/43-filters-project-tools/43-CONTEXT.md` -- Deferred this phase; resolve_inbox integration points

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Patch[T]`, `UNSET`, `is_set()` in `contracts/base.py` -- core Patch infrastructure, already battle-tested on write side
- `validate_offset_requires_limit()` in `_validators.py` -- established shared validator pattern, new helpers go alongside it
- `ValidationReformatterMiddleware._format_validation_errors()` -- already filters `_Unset` from Pydantic errors using context-based detection
- Write-side null rejection validators (`_reject_null_parent`, `_reject_null_container`) -- established `mode="before"` pattern to follow

### Established Patterns
- Method Object pipeline: `execute() -> _resolve_*() -> _build_repo_query() -> _delegate()`
- Resolution methods check `if field is None: return` to skip -- becomes `if not is_set(field): return`
- Warnings accumulated on `self._warnings` list, included in ListResult response
- Error templates in `agent_messages/errors.py` with `{field}` placeholders

### Integration Points
- All 5 `_build_repo_query()` methods -- translate Patch fields via `unset_to_none()`
- `_ListTasksPipeline._resolve_tags()` and `_resolve_project()` -- `is_set()` guards
- `_ListProjectsPipeline._resolve_folder()` and `_check_inbox_search_warning()` -- `is_set()` guards
- `_ListProjectsPipeline._build_repo_query()` -- `review_due_within` translation via `is_set()` check
- Service availability expansion -- new step in each pipeline that has availability fields (4 of 5)

</code_context>

<specifics>
## Specific Ideas

- ALL value is lowercase `"all"` in the AvailabilityFilter enums -- consistent with existing enum values
- The mixed-ALL warning follows the project's established warning pattern: educate, don't error. Accept the input, return results, include the warning in the response.
- `unset_to_none()` is the UNSET-to-None counterpart of `is_set()` -- both serve the service/repo boundary
- `review_due_within` validator becomes a catch-all: string parsing + reject anything that isn't str/dict/ReviewDueFilter. Prevents any Pydantic leak for that field.
- `matches_inbox_name` trap (D-28) is an example of a broader pattern: any service code that accesses `self._query.<patch_field>` directly (outside resolution methods or `_build_repo_query`) must use `unset_to_none()` or `is_set()`. The executor should grep for direct query field access.

</specifics>

<deferred>
## Deferred Ideas

### Reviewed Todos (not folded)
- **Null-stripping for read tool responses** (area: service) -- tangentially related (both about null in read paths) but different scope. Targets v1.4.

### Other
None -- discussion stayed within phase scope.

</deferred>

---

*Phase: 44-migrate-list-query-filters-to-patch-semantics-eliminate-null*
*Context gathered: 2026-04-07*
