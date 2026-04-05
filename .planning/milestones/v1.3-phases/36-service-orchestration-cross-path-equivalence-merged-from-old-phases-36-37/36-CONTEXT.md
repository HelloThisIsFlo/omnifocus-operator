# Phase 36: Service Orchestration + Cross-Path Equivalence - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Service layer adds validation, defaults, and duration parsing to existing list pipelines; cross-path equivalence tests prove BridgeRepository matches SQL path for all 5 entity types.

**Requirements:** INFRA-03 (cross-path equivalence), INFRA-06 (educational error messages)

### What this phase delivers

1. **Input validation** on query models via `@model_validator` / `@field_validator` — offset-requires-limit, review_due_within format
2. **ReviewDueFilter** — `<noun>Filter` value object that parses duration strings ("1w", "2m", "now") on the model, expanded to datetime in the pipeline
3. **Educational error messages** for invalid filter values — ToolError with valid-values list, following existing `agent_messages/errors.py` pattern
4. **Cross-path equivalence tests** — parametrized repo fixture proving BridgeRepository and SqliteRepository return identical results for the same queries

### NOT in scope

- Status shorthands (remaining, available, all) — **killed in Phase 34 D-03b**: agents pass concrete enum values only
- Display order / deterministic ordering for pagination — separate concern, captured as todo
- Default completed/dropped exclusion logic — already handled by model defaults (Phase 34 D-02a: `availability` defaults to `[available, blocked]`)
- Pass-throughs for tags/folders/perspectives — already delivered in Phase 35.2

</domain>

<decisions>
## Implementation Decisions

### Validation Placement (D-01)

Three-layer validation, per `docs/architecture.md` (lines 631-635) and `docs/structure-over-discipline.md` (lines 39-42):

- **D-01a:** Pydantic structural validation on the model (`@field_validator`, `@model_validator`) for: enum values (already handled by StrEnum), offset-requires-limit (cross-field), review_due_within format
- **D-01b:** Validators call pure functions in `service/validate.py` — same pattern as `FrequencyAddSpec._validate_type()` → `_validate_frequency_type()`
- **D-01c:** `@model_validator(mode="after")` on `ListTasksQuery` and `ListProjectsQuery` for offset-requires-limit — same shape as `FrequencyAddSpec._check_cross_type_fields`
- **D-01d:** No validation in the pipeline `_validate()` step for these checks — they're structural, not semantic
- **D-01e:** Only `ListTasksQuery` and `ListProjectsQuery` have limit/offset — tags, folders, perspectives don't need this validator

### ReviewDueFilter (D-02)

Follows `<noun>Filter` taxonomy pattern (Scenario F: DateFilter in `docs/model-taxonomy.md`):

- **D-02a:** `ReviewDueFilter` — value object inheriting `QueryModel`, lives in `contracts/use_cases/list/`
- **D-02b:** Fields: `amount: int | None` (None for "now"), `unit: DurationUnit | None` (None for "now")
- **D-02c:** `DurationUnit` — small `StrEnum` with values `d`, `w`, `m`, `y`
- **D-02d:** `@field_validator(mode="before")` on `ListProjectsQuery.review_due_within` parses `"1w"` → `ReviewDueFilter(amount=1, unit="w")`. "Parse, don't validate" — if it constructs, the duration is valid
- **D-02e:** Pipeline expands `ReviewDueFilter` to `datetime` in service layer (domain computation: amount + unit + now → threshold)
- **D-02f:** `ListProjectsRepoQuery` gets `review_due_before: datetime | None` — concrete, repo-ready
- **D-02g:** Invalid format raises `ValueError` with educational error from `agent_messages/errors.py`

### Educational Errors (D-03)

- **D-03a:** Invalid filter values → `ToolError` (via `ValueError`), not warnings. Matches write-side precedent (`LIFECYCLE_INVALID_VALUE`, `REPETITION_INVALID_FREQUENCY_TYPE`)
- **D-03b:** Warnings (`ListResult.warnings`) reserved for runtime ambiguity (resolution failures, did-you-mean) — not schema violations
- **D-03c:** Error message format: `"Invalid {thing} '{value}' -- valid values: {list}"` — follow existing template pattern in `agent_messages/errors.py`
- **D-03d:** New error constants added to `agent_messages/errors.py`, referenced by validators. Server's `_format_validation_errors()` passes them through automatically

### Status Shorthands — Killed (D-04)

- **D-04a:** Phase 34 D-03b decided: "No shorthands — agents pass concrete enum values only"
- **D-04b:** Roadmap SC#3 updated to remove shorthand expansion references
- **D-04c:** Original milestone spec deviation documented in Phase 34 deferred ideas

### Cross-Path Equivalence Tests (D-05)

- **D-05a:** Parametrized repo fixture — single test body runs against both SqliteRepository and BridgeRepository
- **D-05b:** Two seed adapters translate neutral test data to each repo's input format (SQLite rows vs bridge-format dicts). One-time infrastructure cost, then every test gets it for free
- **D-05c:** All 5 entity types covered: tasks, projects, tags, folders, perspectives
- **D-05d:** Results sorted by ID before comparison — no deterministic ordering exists yet (see deferred: ordering todo)
- **D-05e:** Test data defined once in neutral format (model instances or model-format dicts), seed adapters handle the translation

### Default Completed/Dropped Exclusion — Already Done (D-06)

- **D-06a:** `ListTasksQuery.availability` defaults to `[AVAILABLE, BLOCKED]` on the model (Phase 34 D-02a)
- **D-06b:** No pipeline logic needed — the model default is sufficient
- **D-06c:** SC#2's "default completed/dropped exclusion" is satisfied by the existing model default

### Claude's Discretion

- Exact structure of seed adapters (helper functions, fixtures, conftest organization)
- Internal pipeline step organization for ReviewDueFilter expansion
- Test case selection for cross-path equivalence (which filter combinations to cover)
- Whether ReviewDueFilter expansion helper lives in `validate.py` (pure computation) or `domain.py` (context-dependent)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & Design Principles
- `docs/architecture.md` -- Three-layer validation (lines 631-635), agent message centralization (lines 432-442), "Dumb Bridge, Smart Python" principle
- `docs/structure-over-discipline.md` -- Module boundaries: `validate.py` vs `domain.py` (lines 39-42)
- `docs/model-taxonomy.md` -- `<noun>Filter` pattern (Scenario F: DateFilter), QueryModel base class, service boundary principle

### Prior Phase Decisions (MUST read)
- `.planning/phases/34-contracts-and-query-foundation/34-CONTEXT.md` -- D-02 (defaults on model, expansion in service), D-03 (no shorthands, concrete enum values only)
- `.planning/phases/35.2-uniform-name-vs-id-resolution-at-service-boundary-for-all-list-filters/35.2-CONTEXT.md` -- D-01c (Phase 36 enriches existing pipelines)

### Existing Code Patterns (follow these)
- `src/omnifocus_operator/contracts/shared/repetition_rule.py` -- `@field_validator` / `@model_validator` pattern: validators call `validate.py` helpers, raise `ValueError` with `agent_messages/errors.py` constants
- `src/omnifocus_operator/agent_messages/errors.py` -- Educational error template pattern (`LIFECYCLE_INVALID_VALUE`, `REPETITION_INVALID_FREQUENCY_TYPE`)
- `src/omnifocus_operator/server.py` -- `_format_validation_errors()` (line 117): catches Pydantic `ValidationError`, extracts agent-friendly messages
- `src/omnifocus_operator/service/service.py` -- `_ListTasksPipeline` (line 261), `_ListProjectsPipeline` (line 329), `_ReadPipeline` base (line 223)

### Test Infrastructure
- `tests/test_hybrid_repository.py` -- `create_test_db()`, `_minimal_task()`, `@pytest.mark.hybrid_db` pattern for SQLite seeding
- `tests/conftest.py` -- `make_task_dict()`, `make_snapshot_dict()` for bridge seeding via `InMemoryBridge`
- `tests/doubles/bridge.py` -- `InMemoryBridge` implementation

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `FrequencyAddSpec._validate_type()` / `_check_cross_type_fields()`: Exact pattern for query model validators — thin wrappers calling `validate.py` helpers
- `_format_validation_errors()` in `server.py`: Already catches `ValidationError` and extracts educational messages — new validators flow through automatically
- `LIFECYCLE_INVALID_VALUE` / `REPETITION_INVALID_FREQUENCY_TYPE`: Template for new error constants
- `_ReadPipeline._build_warning()`: Existing warning infrastructure for resolution failures (not used for validation errors)

### Established Patterns
- **Model validates own invariants, service handles cross-model**: `@model_validator` for structural cross-field checks, service for semantic/state-dependent checks
- **Validators are thin wrappers**: `@field_validator` calls `validate.py` function, raises `ValueError(ERROR_CONSTANT)`. One line per validator
- **`<noun>Filter` as nested value object**: `DateFilter` (Scenario F) — agent-friendly input, service resolves to concrete repo values
- **Error/warning boundary**: `ToolError` for schema violations (can't proceed), `ListResult.warnings` for runtime ambiguity (results still meaningful)

### Integration Points
- `contracts/use_cases/list/tasks.py`: Add `@model_validator` for offset-requires-limit on `ListTasksQuery`
- `contracts/use_cases/list/projects.py`: Add `@model_validator` for offset-requires-limit on `ListProjectsQuery`, change `review_due_within` field type to `ReviewDueFilter | None` with `@field_validator(mode="before")`
- `contracts/use_cases/list/projects.py`: `ListProjectsRepoQuery.review_due_within: str | None` → `review_due_before: datetime | None`
- `service/validate.py`: Add `validate_offset_requires_limit()`, `parse_review_due_within()` helpers
- `agent_messages/errors.py`: Add new educational error constants
- `repository/query_builder.py`: Update project query builder for `review_due_before` datetime field

</code_context>

<specifics>
## Specific Ideas

### ReviewDueFilter Flow

```
Agent sends          Model parses              Service expands           Repo receives
-----------         ------------------        ------------------       ---------------
"1w"            ->  ReviewDueFilter            ->  now + 7 days      ->  review_due_before: datetime
                     amount=1, unit="w"

"2m"            ->  ReviewDueFilter            ->  now + 2 months    ->  review_due_before: datetime
                     amount=2, unit="m"

"now"           ->  ReviewDueFilter            ->  now               ->  review_due_before: datetime
                     amount=None, unit=None

"banana"        ->  ValueError (educational error from agent_messages/errors.py)
```

### Cross-Path Equivalence Test Structure

```
                    Neutral test data (model-format dicts)
                           /                  \
              seed_bridge_repo()        seed_hybrid_repo()
              (camelCase, ISO,          (CF epoch, int bools,
               inline tags)              join tables)
                    |                         |
              BridgeRepository        SqliteRepository
                    |                         |
              list_tasks(query)       list_tasks(query)
                    |                         |
                    +------- sorted by ID ----+
                    |                         |
                    assert results identical
```

</specifics>

<deferred>
## Deferred Ideas

### Ordering Bug (TODO)
- Pagination (limit/offset) without deterministic ordering is nondeterministic — same query can return different pages. Both SQL and bridge paths need a stable ORDER BY. Display order (matching OmniFocus UI arrangement) is the ideal sort key but requires investigation into rank columns / bridge ordering. Captured as todo after this discussion.

### Status Shorthands (reviewed, not implemented)
- Phase 34 D-03b killed shorthands. Noted in deferred ideas there: "Could be reconsidered if agents frequently need to type [available, blocked] and it becomes friction."

### Reviewed Todos (not folded)
- "Enforce mutually exclusive tags at service layer" — write-path, not relevant
- "Fix same-container move by translating to moveBefore/moveAfter" — write-path, not relevant
- "Return full task object in edit_tasks response" — write-path, not relevant
- "Move no-op warning check ordinal position" — write-path, not relevant
- "Migrate write tools to typed params with validation middleware" — server layer, not relevant
- "Reorganize test suite" — infrastructure, not relevant
- "Add search tool for projects" — new capability, not relevant

</deferred>

---

*Phase: 36-service-orchestration-cross-path-equivalence-merged-from-old-phases-36-37*
*Context gathered: 2026-03-31*
