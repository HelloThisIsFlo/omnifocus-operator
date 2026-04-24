# Milestones

## v1.4.1 Task Property Surface & Subtree Retrieval (Shipped: 2026-04-24)

**Phases completed:** 2 phases (56, 57), 14 plans (9 on Phase 56 including 2 gap-closure; 5 on Phase 57 including 2 gap-closure)
**Requirements:** 55/55 satisfied (51 original + 3 added during Phase 57 UAT gap-closure: UNIFY-07, UNIFY-08, WARN-06; + 1 added during milestone audit: GOLD-01)
**Tests:** 2,558 pytest at milestone completion (up from 2,167) | 97.52% coverage
**Timeline:** 7 days (2026-04-17 → 2026-04-24) | 167 commits
**LOC delta:** +9,869 / -334 across 68 Python + JS files
**Git range:** v1.4..v1.4.1

**Key accomplishments:**

1. **Task property surface** — writable `completesWithChildren: bool` and per-type `type` (`TaskType = "parallel" | "sequential"`) on tasks with `Patch[bool]` / `Patch[TaskType]` semantics; create-defaults resolved from `OmniFocusPreferences` (new keys: `OFMCompleteWhenLastItemComplete`, `OFMTaskDefaultSequential`); project writes rejected at tool surface (deferred to v1.5)
2. **Presence flags on default response** — tasks emit `hasNote`, `hasRepetition`, `hasAttachments`, `isSequential`, `dependsOnChildren`; projects emit `hasNote`, `hasRepetition`, `hasAttachments`, `isSequential` (all strip-when-false); `isSequential` hoisted to `ActionableEntity` so projects surface the same semantic (56-08 gap closure)
3. **Expanded `hierarchy` include group** — `hasChildren`, `type`, `completesWithChildren` on tasks + projects with no-suppression invariant (default + hierarchy emit independently); `completesWithChildren` added to `NEVER_STRIP`, `availability` removed as dead defensive entry
4. **`parent` filter on `list_tasks`** — single-ref resolution via three-step resolver (`$` prefix → exact ID → name substring), descendants at any depth, AND-composes with other filters, anchor preservation via repo-layer `pinned_task_ids` OR-clause (Option A), full `$inbox` / contradiction-rule parity with `project`
5. **Filter unification** — `project` and `parent` share one service helper (`service/subtree.py::get_tasks_subtree`) and one repo primitive (`ListTasksRepoQuery.candidate_task_ids`, renamed from `task_id_scope` in 57-04); byte-identical results when same entity resolved via either filter (cross-filter equivalence contract test)
6. **Six new warnings** — `FILTERED_SUBTREE_WARNING` (locked verbatim), `PARENT_PROJECT_COMBINED_WARNING`, `PARENT_RESOLVES_TO_PROJECT_WARNING`, `EMPTY_SCOPE_INTERSECTION_WARNING`, plus multi-match + inbox-substring via shared infrastructure; all warnings live in domain layer
7. **Gap closure (4 UAT-discovered gaps)** — G1 anchor preservation under AND composition (57-04), G2 empty-scope cross-path divergence (57-04 service short-circuit), G3 no-match resolver fallback unbundled from Phase 35.2 D-02e (57-04), G4 value-aware `availability` under-alerting in `FILTERED_SUBTREE_WARNING` (57-05)

**Delivered:** Agents can read + write the new task property surface end-to-end (cache-backed, no per-row bridge fallback), get a task's descendant subtree in a single `list_tasks(parent=...)` call, and combine `parent` with any other filter with full warning coverage for edge cases.

**Tech debt at close:** Minor — WR-01 duplicate preference-warning drain in `AddTaskResult` on bridge-failure path accepted as-is (cosmetic, bridge-failure-only). Two code-level items (IN-01 HIER-05 truth-table triplication, IN-03 adapter property-surface duplication) resolved during the milestone audit itself.

**Known deferred items at close:** 18 (1 false-positive UAT gap, 7 completed quick tasks awaiting archival, 5 todos carried forward to v1.7, 5 dormant seeds planted for v1.5/v1.6/v1.7 + landing-page milestone — see STATE.md Deferred Items)

---

## v1.4 Response Shaping & Batch Processing (Shipped: 2026-04-17)

**Phases completed:** 4 phases (53, 53.1, 54, 55), 15 plans
**Requirements:** 41/41 satisfied
**Tests:** 2,167 pytest at milestone completion (up from 2,086)
**Timeline:** 6 days (2026-04-12 → 2026-04-17) | 186 commits
**LOC:** ~12,438 Python (src/)
**Git range:** v1.3.3..v1.4

**Key accomplishments:**

1. Universal response stripping — null, `[]`, `""`, `false`, `"none"` stripped from all entity fields automatically; `availability` and envelope fields (`hasMore`/`total`/`status`) always preserved; `server.py` → `server/` package with dedicated `projection.py`
2. `effective*` → `inherited*` rename across all 6 field pairs in all tool responses; `include`/`only` field selection on list tools; `limit: 0` count-only mode
3. True inheritance walk — `inherited*` fields computed from genuine ancestor chain with per-field aggregation (min due, max defer, first-found planned/drop/completion, any-True flagged); projects structurally excluded via model surgery
4. Batch processing — add_tasks best-effort + edit_tasks fail-fast, up to 50 items per call; flat result array with `status`/`id`/`name`/`error`/`warnings` per item; batch result stripping via `strip_batch_results`
5. Notes graduation — `actions.note.append`/`actions.note.replace` in edit_tasks; `\n` separator; whitespace-only N1 no-op; top-level `note` removed from edit_tasks input schema

**Delivered:** Agents receive clean, minimal responses by default. Multi-item writes in a single call. Full note editing with semantic actions. Genuine inherited field values from ancestor hierarchy.

**Tech debt at close:** Pre-existing Phase 30 TODO in handlers.py (unrelated carry-over). MCP progress-notification transport disconnect root-caused as Claude Code CLI 2.1.105+ regression — progress notifications disabled server-side via `PROGRESS_NOTIFICATIONS_ENABLED=False` pending upstream fix (#47378).

---

## v1.3.3 Ordering & Move Fix (Shipped: 2026-04-12)

**Phases completed:** 2 phases, 4 plans, 6 tasks

**Key accomplishments:**

- Added order: str | None field to Task model with dotted notation description, bridge degraded-mode handling, and cross-path test exclusion
- Recursive CTE with three-anchor sort_path produces exact OmniFocus outline order; Python computes dotted ordinals (1.2.3) for all read paths
- get_edge_child_id on both repo implementations, _process_container_move translates beginning/ending to before/after when container has children, no-op detection via anchor_id == task_id
- MOVE_ALREADY_AT_POSITION warning with position placeholder replaces generic no-op message for same-container move detection

---

## v1.3.2 Date Filtering (Shipped: 2026-04-11)

**Phases:** 6 (45-50) | **Plans:** 23 executed
**Requirements:** 56/56 satisfied (3 scoped out, 2 superseded)
**Tests:** 1,951 pytest at milestone completion (up from 1,693)
**Timeline:** 5 days (2026-04-07 → 2026-04-11) | 351 commits
**LOC:** ~11,472 Python (src/)
**Git range:** v1.3.1..v1.3.2

**Key accomplishments:**

1. Full date filtering on 7 dimensions — agents can filter tasks by due, defer, planned, completed, dropped, added, and modified dates using string shortcuts (`"today"`, `"overdue"`, `"soon"`), shorthand periods (`{this: "w"}`, `{last: "2d"}`), or absolute bounds (`{after: "2026-04-01"}`)
2. Calendar-aware period arithmetic — `{last: "1m"}` and `{next: "1y"}` use proper calendar math with day clamping (Jan 31 + 1m → Feb 28), unified `add_duration` helper across date filters and `review_due_within`
3. Type-safe discriminated union — DateFilter refactored into 4 concrete models (ThisPeriodFilter, LastPeriodFilter, NextPeriodFilter, AbsoluteRangeFilter) with callable discriminator routing — invalid input shapes caught at parse time
4. Naive-local datetime contract — all date inputs use `str` type (no `format: "date-time"` in JSON Schema), aware datetimes silently converted to local — aligns API with OmniFocus's naive-local storage model
5. OmniFocus settings API integration — due-soon threshold and default times (due, defer, planned) read from OmniJS settings API, replacing fragile SQLite plist parsing — date-only inputs enriched with user's configured default times
6. Cross-path equivalence proof — 20 parametrized tests proving SQL and bridge paths produce identical date filter results, including tasks with inherited effective dates
7. Agent-first input guidance — educational errors guide agents from intuitive-but-wrong inputs (like `completed: true` or `urgency`) to the correct date filter syntax — self-teaching API surface

**Delivered:** Complete date filtering infrastructure for all 7 date dimensions. Agents can filter by calendar-aligned periods, rolling windows, or absolute bounds. Naive-local datetime contract matches OmniFocus storage model. OmniFocus user preferences (default times, due-soon threshold) integrated via OmniJS settings API

---

## v1.3.1 First-Class References (Shipped: 2026-04-07)

**Phases:** 6 (39-44) | **Plans:** 15 executed
**Requirements:** 61/61 satisfied
**Tests:** 1,693 pytest at milestone completion (up from 1,528)
**Timeline:** 3 days (2026-04-05 → 2026-04-07) | 204 commits
**LOC:** ~9,947 Python (src/)
**Git range:** v1.3..v1.3.1

**Key accomplishments:**

1. System location namespace (`$` prefix) with `$inbox` constant, three-step resolver cascade, and reserved-prefix error handling for unknown `$`-prefixed strings
2. Name-based resolution for all write fields — case-insensitive substring matching with fuzzy "did you mean?" for projects, tasks, tags, and containers
3. `$inbox` write support in add_tasks/edit_tasks, PatchOrNone elimination, null-rejection validators on all MoveAction fields
4. Tagged parent discriminator (`{project: {id,name}}` / `{task: {id,name}}`), Task.project field, and rich `{id, name}` references on all cross-entity output fields
5. `$inbox` filter integration — `list_tasks(project="$inbox")`, contradictory filter detection, `get_project("$inbox")` guard
6. Patch query filter migration — null eliminated from all agent-facing list query schemas, AvailabilityFilter enums with `ALL` shorthand

**Delivered:** Explicit inbox representation (`$inbox`) across the entire API surface — reads, writes, and filters. Rich `{id, name}` references on all cross-entity output fields. Name-based resolution for all write fields. Null eliminated from agent-facing schemas.

---

## v1.3 Read Tools (Shipped: 2026-04-05)

**Phases:** 12 (34-38 including 7 decimal insertions) | **Plans:** 26 executed
**Requirements:** 80/80 satisfied
**Tests:** 1,528 pytest at milestone completion (up from 1,113)
**Timeline:** 7 days (2026-03-29 → 2026-04-05) | ~70 commits
**LOC:** ~9,021 Python (src/)
**Git range:** Phase 34 → Phase 38

**Key accomplishments:**

1. Parameterized SQL filtering engine — query builder for tasks (10 filters) and projects (6 filters) with compound availability clauses, tag IN expansion, and LIKE search via `?` placeholders
2. 5 new MCP list tools (`list_tasks`, `list_projects`, `list_tags`, `list_folders`, `list_perspectives`) with typed query models, rich inputSchema, and DEFAULT_LIST_LIMIT=50
3. Name-to-ID resolution cascade at service boundary — agents pass names or IDs, service resolves uniformly with fuzzy "did you mean?" warnings on zero-match
4. Write tool schema migration — ValidationReformatterMiddleware producing clean agent-facing `ToolError` with "Task N:" prefix, 52+ schema entries per tool
5. Description centralization — 60 agent-visible constants in `descriptions.py` with 5 AST-based enforcement tests preventing regression
6. Cross-path equivalence — 32 parametrized tests proving BridgeRepository and HybridRepository return identical results across all 5 entity types
7. Type constraint boundary — Literal/Annotated types reserved for contract models, plain types on core models, with AST enforcement
8. Fixed effectiveCompletionDate ghost tasks — availability mappers and SQL clauses use effective date columns

**Delivered:** Complete read+filter+search MCP interface for OmniFocus entities — agents can list, filter, search, and paginate tasks, projects, tags, folders, and perspectives with typed query models, educational error messages, and agent-friendly documentation.

---

## v1.2.3 Repetition Rule Write Support (Shipped: 2026-03-29)

**Phases completed:** 4 phases, 15 plans, 30 tasks

**Key accomplishments:**

- Structured RepetitionRule read model — RRULE parser/builder with round-trip validation, ruleString replaced by frequency/schedule/basedOn/end on both read paths
- Output schema regression guards — jsonschema validates all 6 tools' serialized output, union erasure guards, naming convention enforcement
- Full repetition rule write pipeline — add/edit support with partial updates, same-type merge, type-change detection, educational errors
- Flat Frequency model — 9-subtype discriminated union refactored to single flat model with 6 types, type-optional edits, clean validation errors
- Anchor date warnings — proactive guidance when basedOn references an unset date, with creation-date fallback explanation

**Stats:** 211 commits, 214 files changed, +89k/-1.3k lines, 3 days (2026-03-26 → 2026-03-29)
**Tests:** 1,113 pytest at milestone completion (up from 708)

---

## v1.2.2 FastMCP v3 Migration (Shipped: 2026-03-26)

**Phases completed:** 3 phases, 6 plans, 12 tasks

**Key accomplishments:**

- Swapped mcp>=1.26.0 for fastmcp>=3.1.1, migrated all src/ imports to native FastMCP v3 patterns, fixed test infrastructure for lifespan compatibility
- ctx.report_progress() scaffolding in batch write handlers + all docs updated from mcp>=1.26.0 to fastmcp>=3.1.1
- Replaced 65-line _ClientSessionProxy with 10-line Client fixture, migrated 40+ fixture-based tests to snake_case fields, ToolError assertions, and flat list_tools()
- ToolLoggingMiddleware replaces manual log_tool_call() -- automatic entry/exit/error logging for all 6 tools via FastMCP middleware API
- Dual-handler logging (stderr + 5MB rotating file) with __name__ convention across all 10 modules for per-module log granularity

---

## v1.2.1 Architectural Cleanup (Shipped: 2026-03-23)

**Phases completed:** 11 phases, 27 plans, 46 tasks

**Key accomplishments:**

- WriteModel base with extra=forbid on all 5 write specs, improved server error handler naming unknown fields, 518 tests green at 94% coverage
- All 11 agent-facing warning strings extracted to warnings.py with integrity tests preventing inline regression
- Removed all test doubles from production package exports and factory, migrated 10 test files to direct module imports, all 517 tests green
- Seven-file contracts/ package with three-layer model taxonomy (Command/RepoPayload/RepoResult/Result), consolidated Service/Repository/Bridge protocols, and renamed value objects (TagAction, MoveAction, EditTaskActions)
- Atomic switch from old paths to contracts/: all source+test imports migrated, typed repo payloads with null-means-clear semantics, three old files deleted
- Symmetric kwargs dict -> model_validate() payload construction for both add_task and edit_task, eliminating camelCase roundtrip and _payload_to_repo mapping
- BridgeWriteMixin extracted with _send_to_bridge helper, all repos on explicit Repository protocol, serialization standardized on exclude_unset=True
- Converted 669-line monolithic service.py into 4-module service/ package with DI-based Resolver, DomainLogic, PayloadBuilder and thin orchestrator
- 57 unit tests proving Resolver, DomainLogic, and PayloadBuilder work independently of OperatorService with stub/real fixtures matching dependency strategy
- Split validation from resolution into separate module, route entity existence checks through Resolver boundary
- DomainLogic.normalize_clear_intents centralizes note=None and tags.replace=None normalization, PayloadBuilder simplified to pure construction
- PYTEST safety guard migrated to RealBridge._guard_automated_testing(), bridge factory deleted, repository factory simplified to create RealBridge directly
- Relocated all 5 test doubles (InMemoryBridge, BridgeCall, SimulatorBridge, ConstantMtimeSource, InMemoryRepository) from src/ to tests/doubles/, creating structural import barrier between production and test code
- Patch[T]/PatchOrClear[T]/PatchOrNone[T] aliases and changed_fields() on CommandModel, all command model annotations migrated with identical JSON schema output
- Stateful InMemoryBridge with add_task/edit_task dict-level handlers, deep-copy get_all, and backward-compatible stub fallback
- All test files migrated from InMemoryRepository to BridgeRepository + InMemoryBridge; InMemoryRepository deleted; write tests now exercise real serialization path
- StubBridge extracted as canned-response test double, InMemoryBridge cleaned of dual-mode auto-detection; 12 hybrid repo + 10 bridge test usages migrated
- @pytest.mark.snapshot marker with bridge/repo/service fixture chain; TestOperatorService (8 methods) and TestAddTask (16 methods) converted to declarative fixture injection
- All 68 TestEditTask methods converted to @pytest.mark.snapshot + fixture injection, eliminating 320 lines of inline bridge/repo/service boilerplate
- Fixed InMemoryBridge parent/tag resolution gaps and created tests/golden/ normalization package for contract test comparison
- 17/17 contract scenarios pass. Two gaps in the golden master testing approach discovered during checkpoint.
- InMemoryBridge._handle_get_all returns raw bridge format with reverse status maps, parent chain walk for containing-project reconstruction, and adapter round-trip verification
- 20 contract tests verifying InMemoryBridge raw output against re-captured golden master with VOLATILE/UNCOMPUTED field normalization and parent disambiguation scenarios
- Ancestor-chain inheritance for effective fields, 9 fields graduated from VOLATILE/UNCOMPUTED, presence-check sentinel normalization, subfolder-aware contract test discovery
- 43-scenario capture script across 7 numbered categories (01-add through 07-inheritance) with subfolder fixture layout, 3-project setup, and anchor/inheritance coverage

---

## v1.2 Writes & Lookups (Shipped: 2026-03-16)

**Phases:** 6 (14-17 including 16.1, 16.2) | **Plans:** 21 executed
**Requirements:** 28/29 satisfied (LIFE-03 reactivation intentionally deferred)
**Tests:** 501 pytest (up from 313)
**Timeline:** 9 days (2026-03-07 → 2026-03-15) | 295 commits
**LOC:** ~20,189 Python (+7,222 / -323 vs v1.1)
**Git range:** `v1.1..v1.2`

**Key accomplishments:**

1. Unified parent model (`parent: {type, id} | null`) replacing separate project/parent fields; `get_all` renamed from `list_all`
2. Get-by-ID tools (`get_task`, `get_project`, `get_tag`) with dedicated SQLite queries and clear not-found errors
3. Full write pipeline (MCP → Service → Repository → Bridge → OmniFocus) with snapshot invalidation and write-through guarantee
4. Task creation (`add_tasks`) — name-only minimum, parent/tag resolution, per-item results, validation before write
5. Task editing (`edit_tasks`) — UNSET sentinel for patch semantics, actions block grouping (tags/move/lifecycle), diff-based tag computation
6. Task lifecycle — complete/drop via `edit_tasks` with no-op detection, educational warnings, and repeating-task awareness

**Delivered:** Complete read+write MCP interface for OmniFocus tasks — agents can look up entities by ID, create tasks with full field control, edit tasks with patch semantics and structured actions, and manage task lifecycle (complete/drop).

**Known Gaps:**

- LIFE-03: Task reactivation deferred — OmniJS `markIncomplete()` API unreliable
- REQUIREMENTS.md descriptions stale for EDIT-03 through EDIT-08 (reference pre-actions-block field names)
- Mutually exclusive tags not enforced at server level (OmniJS allows it; UI-only enforcement)

---

## v1.1 HUGE Performance Upgrade (Shipped: 2026-03-07)

**Phases:** 4 (10-13) | **Plans:** 11 executed
**Requirements:** 18/18 satisfied
**Tests:** 313 pytest, 26 Vitest, UAT passed (all phases)
**Timeline:** 1 day (2026-03-07) | 88 commits
**LOC:** ~14,144 Python (+13,192 / -2,252 vs v1.0)
**Git range:** `v1.0..v1.1`

**Key accomplishments:**

1. Two-axis status model (Urgency + Availability) replacing single-winner TaskStatus/ProjectStatus enums across all entities
2. Repository protocol abstracting read path -- BridgeRepository, InMemoryRepository, and HybridRepository are swappable
3. HybridRepository reading all 5 entity types directly from OmniFocus SQLite cache (~46ms full snapshot)
4. WAL-based read-after-write freshness detection (50ms poll, 2s timeout, fallback to .db mtime)
5. Repository factory with OMNIFOCUS_REPOSITORY env var routing (sqlite default, bridge fallback)
6. Error-serving degraded mode when SQLite unavailable with actionable fix instructions

**Delivered:** Direct SQLite cache access as primary read path, eliminating OmniFocus process dependency for reads and providing dramatically faster, more accurate data retrieval with a richer status model.

---

## v1.0 Foundation (Shipped: 2026-03-07)

**Phases:** 11 (1-9 including 8.1, 8.2) | **Plans:** 22 executed (1 skipped)
**Requirements:** 42/42 satisfied (35 original + 7 ERR-*)
**Tests:** 177+ pytest, 26 Vitest, UAT passed (all phases)
**Timeline:** 14 days (2026-02-21 to 2026-03-07) | 234 commits
**LOC:** ~5,943 Python | ~215k JS (bridge + deps) | ~28k TS (tests)
**Git range:** initial commit to `81700ba`

**Key accomplishments:**

1. Full MCP server with `list_all` tool -- three-layer architecture (MCP -> Service -> Repository) returning structured Pydantic data
2. Pluggable bridge abstraction -- InMemoryBridge, SimulatorBridge, and RealBridge swappable via config with zero code changes
3. File-based IPC engine -- atomic writes, async polling, 10s timeout, orphan sweep, OmniFocus sandbox-aware
4. JavaScript bridge script (OmniJS) running inside OmniFocus, completing the end-to-end IPC pipeline
5. BRIDGE-SPEC alignment -- per-entity status resolvers, RepetitionRule redesign, fail-fast enums validated against live OmniFocus
6. Error-serving degraded mode -- fatal startup errors served as actionable MCP tool responses instead of silent crashes

**Known Tech Debt:**

- Missing VERIFICATION.md for phases 08 and 08.1 (UAT evidence exists)
- Plan 08.1-04 (Makefile unified test) skipped
- SUMMARY.md files lack requirements_completed frontmatter

---
