# Phase 46: Pipeline & Query Paths - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire the Phase 45 date models (DateFilter, shortcut enums, resolver) into `list_tasks` so agents get correctly filtered results on both SQL and bridge paths. This phase delivers: service pipeline integration (date resolution step + lifecycle auto-include), SQL date predicates using effective CF epoch columns, bridge in-memory filtering with shared resolution logic, and DueSoonSetting retrieval from OmniFocus Settings table. No breaking changes, no cross-path equivalence tests, no tool description updates (those are Phase 47).

</domain>

<decisions>
## Implementation Decisions

### Due-soon Config Retrieval
- **D-01:** Add `get_due_soon_setting() -> DueSoonSetting | None` to the `Repository` protocol. `HybridRepository` reads `DueSoonInterval` + `DueSoonGranularity` from the OmniFocus SQLite Settings table. `BridgeOnlyRepository` reads `OPERATOR_DUE_SOON_THRESHOLD` env var and maps to a `DueSoonSetting` member.
- **D-02:** The pipeline calls `get_due_soon_setting()` **conditionally** — only when `due: "soon"` is detected in the query. No wasted I/O on the common case.
- **D-03:** If neither SQLite Settings table nor env var is available, `get_due_soon_setting()` returns `None`. The resolver fails fast with an educational error when `due: "soon"` is requested without config (already implemented in `resolve_dates.py`).

### Pipeline Date Resolution Step
- **D-04:** New `_resolve_date_filters()` method in `_ListTasksPipeline`, following the established Method Object grain (`_resolve_project`, `_resolve_tags` pattern). Called between `_resolve_tags()` and `_build_repo_query()` in the pipeline flow.
- **D-05:** `_resolve_date_filters()` captures `self._now = datetime.now()` once at the top — the single "now" snapshot per RESOLVE-05. All 7 date fields resolved against this same timestamp.
- **D-06:** For each date field, if set (not UNSET), calls `resolve_date_filter()` and stores the result as `self._<field>_after` / `self._<field>_before`.
- **D-07:** For `completed` and `dropped` fields: if ANY value is set (string shortcut OR DateFilter object), adds the corresponding `Availability` member to `self._lifecycle_availability_additions: list[Availability]`.
- **D-08:** `_build_repo_query()` merges `self._lifecycle_availability_additions` with the existing expanded availability list using set-union (prevents duplicates). Then sets all 14 `_after`/`_before` fields on the RepoQuery.

### Date Filter SQL Composition
- **D-09:** Date predicates are top-level AND conditions in the WHERE clause, consistent with all existing filters (flagged, project, tags, search, etc.). No special OR composition for lifecycle date filters.
- **D-10:** `completed: {last: "1w"}` naturally returns only completed tasks — available/blocked tasks are excluded because their `effectiveDateCompleted` is NULL, and `NULL >= ?` evaluates to false in SQL. This is the correct behavior: the agent asked about completed tasks and gets completed tasks.
- **D-11:** Combining lifecycle date filters with other date filters produces intersections: `completed: {last: "1w"}, due: "overdue"` = tasks that were BOTH completed last week AND overdue at time of query. Agents wanting unions make separate calls.

### Column Mapping (Confirmed by Database Research)
- **D-12:** All 7 date dimensions use effective columns where available. Never direct date columns. The agent-facing API never mentions "effective" — the system always does the right thing.

| Date dimension | SQL column | Type | Bridge model field |
|---|---|---|---|
| due | `effectiveDateDue` | integer (CF epoch) | `effective_due_date` |
| defer | `effectiveDateToStart` | integer (CF epoch) | `effective_defer_date` |
| planned | `effectiveDatePlanned` | integer (CF epoch) | `effective_planned_date` |
| completed | `effectiveDateCompleted` | real (CF epoch) | `effective_completion_date` |
| dropped | `effectiveDateHidden` | real (CF epoch) | `effective_drop_date` |
| added | `dateAdded` | real (CF epoch) | `added` |
| modified | `dateModified` | real (CF epoch) | `modified` |

- **D-13:** Direct date columns (dateDue, dateToStart, datePlanned) are text format — cannot be compared numerically with CF epoch. Only `effective*` columns work for SQL filtering.
- **D-14:** Integer vs real mixing in effective columns (effectiveDateDue is integer, effectiveDateCompleted is real) is transparent to SQLite — no special handling needed.

### Inherited Completion (Implementation Note)
- **D-15:** 174 tasks have `effectiveDateCompleted` set but `dateCompleted IS NULL` — they're in completed containers but weren't individually completed. Using `effectiveDateCompleted` for filtering means these appear in `completed` filter results. This is semantically correct: "what did I complete today?" includes project contents. The broader question of whether `effectiveDateCompleted IS NULL` should be part of the default active-task filter predates v1.3.2 — document, don't block.
- **D-16:** Never use the `dueSoon` column for filtering. OmniFocus's `dueSoon` excludes overdue tasks (0 overlap); our `"soon"` includes overdue per spec. Implementation computes `effectiveDateDue < threshold` directly.

### Claude's Discretion
- CF epoch conversion strategy (where Python datetime → CF epoch float conversion happens — likely in query_builder)
- `OPERATOR_DUE_SOON_THRESHOLD` env var format for BridgeOnlyRepository (member names, duration strings, etc.)
- InMemoryBridge `get_due_soon_setting()` implementation for tests (configurable setting)
- Exact signature of `_resolve_date_filters()` (internal method, follows established patterns)
- Bridge path filtering order/optimization (straightforward list comprehensions matching SQL semantics)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone & Requirements
- `.research/updated-spec/MILESTONE-v1.3.2.md` — full milestone spec (NOTE: success criterion #3 about pre-computed columns is superseded by D-12/D-16)
- `.planning/REQUIREMENTS.md` — requirements (NOTE: RESOLVE-11/12 revised per Phase 45 D-04; DATE-07/08/EXEC-08 scoped out per D-13)

### Database Research (CRITICAL)
- `.research/deep-dives/direct-database-access-date-filters/FINDINGS.md` — column type map (section 3), inheritance rates (section 2), null distribution (section 4), stale flag warnings (section 5), inherited-completion ghost tasks (section 6)
- `.research/deep-dives/direct-database-access-date-filters/6-due-soon-spike/FINDINGS.md` — DueSoonGranularity discovery, two-mode threshold formula, complete UI-to-database mapping

### Phase 45 Outputs (Upstream Dependencies)
- `src/omnifocus_operator/contracts/use_cases/list/_date_filter.py` — DateFilter contract model (flat, 5 optional keys, mutual exclusion validators)
- `src/omnifocus_operator/contracts/use_cases/list/_enums.py` — DueDateShortcut, LifecycleDateShortcut, DueSoonSetting enums
- `src/omnifocus_operator/contracts/use_cases/list/tasks.py` — ListTasksQuery (7 date fields) + ListTasksRepoQuery (14 _after/_before datetime fields)
- `src/omnifocus_operator/service/resolve_dates.py` — pure `resolve_date_filter()` function
- `src/omnifocus_operator/config.py` — `Settings(BaseSettings)` with `get_settings()` singleton, `week_start` field

### Integration Points
- `src/omnifocus_operator/service/service.py` — `_ListTasksPipeline` (add `_resolve_date_filters()` step)
- `src/omnifocus_operator/repository/hybrid/query_builder.py` — `build_list_tasks_sql()` (add date WHERE clauses)
- `src/omnifocus_operator/repository/hybrid/hybrid.py` — `HybridRepository` (add `get_due_soon_setting()`)
- `src/omnifocus_operator/repository/bridge_only/bridge_only.py` — `BridgeOnlyRepository` (add `get_due_soon_setting()` + date filtering in `list_tasks`)

### Architecture & Conventions
- `docs/model-taxonomy.md` — model naming rules
- `docs/architecture.md` — three-layer architecture, method object pattern

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `resolve_date_filter()` in `service/resolve_dates.py` — pure resolver accepting DueSoonSetting, already tested
- `DueSoonSetting(Enum)` in `_enums.py` — 7-member enum with `.days` and `.calendar_aligned` domain properties
- `Settings(BaseSettings)` in `config.py` — singleton pattern for env var reading, extensible
- `_expand_availability()` in `service/service.py` — existing availability expansion helper, merge target for lifecycle additions
- `build_list_tasks_sql()` in `query_builder.py` — conditions/params pattern for adding WHERE clauses

### Established Patterns
- **Method Object grain:** `_resolve_project()`, `_resolve_tags()` → accumulate into `self._*` attributes → consumed by `_build_repo_query()`. Date resolution follows the same pattern.
- **SQL query builder:** conditions list + params list, parameterized `?` placeholders, no string interpolation
- **Bridge fallback:** fetch-all + sequential list comprehensions matching SQL semantics
- **Repository protocol:** structural typing, swappable implementations (Hybrid, BridgeOnly, InMemory)

### Integration Points
- `_ListTasksPipeline.execute()` flow: resolve_inbox → check_inbox_warning → resolve_project → resolve_tags → **_resolve_date_filters()** → build_repo_query → delegate
- `build_list_tasks_sql()` adds conditions/params after existing filters — date predicates follow same pattern
- `BridgeOnlyRepository.list_tasks()` adds sequential filtering after existing filters

</code_context>

<specifics>
## Specific Ideas

- The pipeline's `_resolve_date_filters()` conditionally calls `self._repository.get_due_soon_setting()` only when `due: "soon"` is in the query — zero overhead for the 95%+ of queries that don't use "soon."
- CF epoch conversion: Python `datetime.now()` → CF epoch float for SQL parameters. The query builder is the natural place for this conversion (it already handles all parameter preparation).
- The bridge path doesn't need "now" separately — it receives resolved `_after`/`_before` datetime values on the RepoQuery and compares against Task model datetime fields.
- InMemoryBridge for tests should accept a configurable `DueSoonSetting` so tests can exercise the "soon" shortcut path.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 46-pipeline-query-paths*
*Context gathered: 2026-04-08*
