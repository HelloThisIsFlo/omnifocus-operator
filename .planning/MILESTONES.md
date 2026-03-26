# Milestones

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
