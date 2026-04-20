# OmniFocus Operator

## What This Is

A Python MCP server that exposes OmniFocus (macOS task manager) as structured task infrastructure for AI agents. Reads via SQLite cache (~46ms), writes via OmniJS bridge. Eleven MCP tools: `get_all`, `get_task`, `get_project`, `get_tag`, `add_tasks`, `edit_tasks`, `list_tasks`, `list_projects`, `list_tags`, `list_folders`, `list_perspectives`. Agent-first design with educational warnings, typed query models, patch semantics, structured actions for tags/movement/lifecycle, and outline-ordered task responses.

## Core Value

Reliable, simple, debuggable access to OmniFocus data for AI agents -- executive function infrastructure that works at 7:30am.

## Current Milestone: v1.4.1 Task Property Surface & Subtree Retrieval

**Goal:** Expose OmniFocus task properties the server currently hides (auto-complete, parallel/sequential, presence of notes/repetition/attachments) and add a `parent` filter on `list_tasks` so agents can fetch a task's descendants in a single call. Strictly additive point release — same shape as v1.3.1/.2/.3; projects stay read-only (writes deferred to v1.5).

**Target features:**
- Writable `completesWithChildren: bool` and per-type `type` enum (`TaskType`: parallel/sequential; `ProjectType`: + singleActions) on tasks
- Derived presence flags on task default response: `hasNote`, `hasRepetition`, `hasAttachments`, `isSequential` (tasks-only), `dependsOnChildren` (tasks-only) — all strip-when-false
- Expanded `hierarchy` include group on tasks + projects: `hasChildren`, `type`, `completesWithChildren` (added to `NEVER_STRIP`)
- `parent` filter on `list_tasks` — name/ID resolution, `$inbox` supported, filter unification at repo layer via `collect_subtree` helper, `ListTasksRepoQuery.parent_ids`
- `OmniFocusPreferences` extended with `OFMCompleteWhenLastItemComplete` and `OFMTaskDefaultSequential` for create-defaults
- New warnings: filtered-subtree (verbatim text locked), parent-resolves-to-project, parent+project combined

**Key context:** Design locked 2026-04-19 after four-session interview + two pre-implementation spikes (SQLite cache coverage confirms all three read fields cache-backed; Python-filter benchmark confirms repo-layer unification viable at ≤1.30 ms p95 / 10K rows). No fields scoped out. Full spec: `.research/updated-spec/MILESTONE-v1.4.1.md`.

## Requirements

### Validated

- Three-layer architecture: MCP Server -> Service Layer -> Repository — v1.0
- Bridge interface with pluggable implementations (InMemory, Simulator, Real) — v1.0
- Full database snapshot loaded into memory from bridge dump — v1.0
- File-based IPC with atomic writes (`.tmp` -> rename) — v1.0
- Pydantic models derived from bridge script output shape — v1.0
- Snapshot freshness via `.ofocus` directory mtime check — v1.0
- Deduplication lock preventing parallel dump storms — v1.0
- Mock simulator as standalone Python script for IPC testing — v1.0
- Timeout handling with clear error messages — v1.0
- Error-serving degraded mode (startup errors -> actionable tool responses) — v1.0
- BRIDGE-SPEC alignment: fail-fast enums, per-entity status resolvers — v1.0
- Two-axis status model (Urgency + Availability) replacing single-winner enums — v1.1
- Pydantic model overhaul: deprecated fields removed, shared enums — v1.1
- SQLite cache as primary read path (~46ms full snapshot, OmniFocus not needed) — v1.1
- WAL-based read-after-write freshness detection (50ms poll, 2s timeout) — v1.1
- Repository protocol abstracting read path (HybridRepository, BridgeRepository, InMemoryRepository) — v1.1
- Error-serving degraded mode when SQLite unavailable (manual fallback via env var) — v1.1
- ✓ Unified parent model (`parent: {type, id} | null`), `get_all` renamed from `list_all` — v1.2
- ✓ Get-by-ID tools (`get_task`, `get_project`, `get_tag`) with dedicated SQLite queries — v1.2
- ✓ Write pipeline: MCP → Service → Repository → Bridge → OmniFocus with write-through guarantee — v1.2
- ✓ Task creation (`add_tasks`) with parent/tag resolution, validation, per-item results — v1.2
- ✓ Task editing (`edit_tasks`) with UNSET sentinel patch semantics, actions block (tags/move/lifecycle) — v1.2
- ✓ Diff-based tag computation in Python service layer, bridge receives only addTagIds/removeTagIds — v1.2
- ✓ Task lifecycle (complete/drop) with no-op detection and educational warnings — v1.2
- ✓ Bridge script write commands (add_task, edit_task) with request file payloads — v1.2
- ✓ Write model strictness: `extra="forbid"` catches unknown agent fields at validation time — v1.2.1
- ✓ FastMCP v3 dependency swap: `fastmcp>=3.1.1` replaces `mcp>=1.26.0`, native imports, `ctx.lifespan_context` shorthand — v1.2.2
- ✓ Progress reporting in batch write tools via `ctx.report_progress()` — v1.2.2
- ✓ Test client migration: 10-line `Client(server)` fixture replacing 65-line `_ClientSessionProxy`, `pytest.raises(ToolError)` pattern — v1.2.2
- ✓ ToolLoggingMiddleware: automatic entry/exit/error logging for all tools via FastMCP middleware API — v1.2.2
- ✓ Dual-handler logging: `StreamHandler(stderr)` + 5MB `RotatingFileHandler` with `__name__` convention across all modules — v1.2.2
- ✓ Warning string consolidation into agent_messages/ package with AST integrity tests — v1.2.1
- ✓ Three-layer model taxonomy (Command/RepoPayload/RepoResult/Result) in contracts/ package — v1.2.1
- ✓ Write pipeline unification: symmetric add/edit signatures, BridgeWriteMixin, exclude_unset — v1.2.1
- ✓ Service decomposition: service.py → service/ package (Resolver, DomainLogic, PayloadBuilder, orchestrator) — v1.2.1
- ✓ SimulatorBridge removed from exports, bridge factory eliminated, PYTEST guard in RealBridge — v1.2.1
- ✓ All test doubles relocated from src/ to tests/doubles/ with structural import barrier — v1.2.1
- ✓ Patch[T]/PatchOrClear[T] type aliases make patch semantics self-documenting in annotations — v1.2.1
- ✓ InMemoryRepository deleted; stateful InMemoryBridge exercises real serialization in tests — v1.2.1
- ✓ StubBridge extracted as canned-response double; InMemoryBridge is purely stateful — v1.2.1
- ✓ @pytest.mark.snapshot marker + fixture composition eliminates test boilerplate — v1.2.1
- ✓ Golden master contract testing: 43 scenarios proving InMemoryBridge ≡ RealBridge equivalence — v1.2.1
- ✓ 9 fields graduated from VOLATILE/UNCOMPUTED to verified via ancestor-chain inheritance — v1.2.1
- ✓ Structured RepetitionRule read model: frequency (9 discriminated-union types), schedule, basedOn, end — replaces raw ruleString — v1.2.3
- ✓ Single rrule/ module (parse_rrule, build_rrule) shared by both SQLite and bridge read paths — v1.2.3
- ✓ parse/build round-trip correctness for all 9 frequency types — v1.2.3
- ✓ Repetition rule write support: add/edit tasks with structured frequency fields, partial updates, type-change detection — v1.2.3
- ✓ Flat Frequency model (6 types) with type-optional edits and educational validation errors — v1.2.3
- ✓ Output schema regression guards: jsonschema validates all 6 tools' serialized output against MCP outputSchema — v1.2.3
- ✓ Anchor date warnings: proactive guidance when basedOn references an unset date — v1.2.3
- ✓ Description centralization: all ~60 agent-visible Field(description=) strings, class docstrings, and 6 MCP tool descriptions centralized in agent_messages/descriptions.py with enforcement tests — v1.3 (Phase 36.3)
- ✓ SQL filtering for tasks (10 filters) and projects (6 filters) with parameterized query builder — v1.3
- ✓ List tags, folders with status filter; list perspectives (built-in + custom) — v1.3
- ✓ Substring search across all 5 entity types — v1.3
- ✓ 5 list MCP tools with typed query models and rich inputSchema — v1.3
- ✓ Name-to-ID resolution cascade at service boundary with "did you mean?" warnings — v1.3
- ✓ Write tool schema migration: ValidationReformatterMiddleware, 52+ schema entries per tool — v1.3
- ✓ Read-side contract boundary split (RepoQuery/RepoResult) with per-use-case package structure — v1.3
- ✓ Cross-path equivalence: 32 parametrized tests proving SQL and bridge paths identical — v1.3
- ✓ Type constraint boundary: Literal/Annotated reserved for contracts, plain types on core models, AST enforcement — v1.3
- ✓ Fixed effectiveCompletionDate ghost tasks in availability mappers and SQL clauses — v1.3
- ✓ System location namespace (`$` prefix) with reserved-prefix constants and three-step resolver — v1.3.1 (Phase 39-40)
- ✓ `resolve_container` handles `$inbox` → None, unknown `$` names → error, names → fuzzy match — v1.3.1 (Phase 40)
- ✓ PatchOrNone eliminated; MoveAction fields use `Patch[str]` with null-rejection validators and per-field descriptions — v1.3.1 (Phase 41)
- ✓ `AddTaskCommand.parent` converted to `Patch[str]` with UNSET (inbox) and null-rejection validator — v1.3.1 (Phase 41)
- ✓ `$inbox` supported in add_tasks (parent) and edit_tasks (moveTo beginning/ending) — v1.3.1 (Phase 41)
- ✓ Tagged parent discriminator (`{project: {id,name}}` / `{task: {id,name}}`), never null — v1.3.1 (Phase 42)
- ✓ Task.project field with containing project at any depth, `$inbox` for inbox tasks — v1.3.1 (Phase 42)
- ✓ All cross-entity refs enriched to `{id, name}` objects (Project.folder, Project.next_task, Tag.parent, Folder.parent) — v1.3.1 (Phase 42)
- ✓ inInbox field removed from Task output; ParentRef model replaced with tagged wrapper — v1.3.1 (Phase 42)
- ✓ `list_tasks(project="$inbox")` normalizes to `in_inbox=True` via `resolve_inbox` before pipeline resolution — v1.3.1 (Phase 43)
- ✓ Contradictory filter detection for all inbox/project combinations with locked error strings — v1.3.1 (Phase 43)
- ✓ `get_project("$inbox")` guard, `list_projects` search warning for inbox-related terms — v1.3.1 (Phase 43)
- ✓ Bridge-only `adapt_snapshot` filters project root tasks (parity with SQL `LEFT JOIN ProjectInfo`) — v1.3.1 (Phase 43)
- ✓ List query filter fields migrated to `Patch[T]` — null eliminated from agent-facing schemas, UNSET→None at repo boundary — v1.3.1 (Phase 44)
- ✓ True inherited fields: `inherited*` on tasks reflect genuine ancestry (parent hierarchy walk), not OmniFocus self-echoes — v1.4 (Phase 53.1)
- ✓ Projects have zero `inherited*` fields — structurally impossible via model surgery (fields moved from ActionableEntity to Task) — v1.4 (Phase 53.1)
- ✓ Batch processing: add_tasks/edit_tasks accept up to 50 items per call with per-item status/error reporting — v1.4 (Phase 54)
- ✓ add_tasks best-effort: processes all items regardless of failures, per-item `status: "success"|"error"` — v1.4 (Phase 54)
- ✓ edit_tasks fail-fast: stops at first error, remaining items `status: "skipped"` with warning referencing failing item — v1.4 (Phase 54)
- ✓ Flat result model: `status: Literal["success","error","skipped"]` with optional `id`/`name`/`error`/`warnings` — v1.4 (Phase 54)
- ✓ `AvailabilityFilter` enums with `ALL` shorthand, empty-list rejection, mixed `["all", "available"]` warning — v1.3.1 (Phase 44)
- ✓ Date filtering on list_tasks — 7 date fields (due, defer, planned, completed, dropped, added, modified) with string shortcuts, shorthand periods, and absolute bounds — v1.3.2
- ✓ Calendar-aware period arithmetic with day clamping (`{last: "1m"}` uses proper calendar math) — v1.3.2
- ✓ Type-safe DateFilter discriminated union (ThisPeriodFilter, LastPeriodFilter, NextPeriodFilter, AbsoluteRangeFilter) — v1.3.2
- ✓ Naive-local datetime contract — all date inputs use `str` type, aware datetimes converted to local — v1.3.2
- ✓ OmniFocus settings API integration — due-soon threshold and default times via OmniJS `settings.objectForKey()` — v1.3.2
- ✓ Filter cleanup: `urgency` removed, `completed` boolean → date filter, `availability` trimmed (`COMPLETED`/`DROPPED` removed) — v1.3.2
- ✓ Defer vs availability hints — educational guidance when defer filter implies availability equivalents — v1.3.2
- ✓ Task `order` field — read-only integer reflecting outline position within parent via recursive CTE (rank-based) — v1.3.3
- ✓ Inbox-first ordering — inbox tasks sort before project tasks in get_all/list_tasks responses — v1.3.3
- ✓ Same-container move fix — `moveTo beginning/ending` translates to `moveBefore`/`moveAfter` via `get_edge_child_id` when container has children — v1.3.3
- ✓ Position-specific no-op detection — `anchor_id == task_id` self-reference check with `MOVE_ALREADY_AT_POSITION` warning — v1.3.3
- ✓ Task property surface — writable `completesWithChildren`, per-type `type` enum on tasks with `Patch[bool]` / `Patch[TaskType]` semantics + create-default resolution from OF preferences — v1.4.1 Phase 56
- ✓ Task presence flags — `hasNote`, `hasRepetition`, `hasAttachments`, `isSequential`, `dependsOnChildren` on default response, stripped-when-false — v1.4.1 Phase 56
- ✓ Expanded `hierarchy` include group — `hasChildren`, `type`, `completesWithChildren` on tasks + projects with no-suppression invariant (default + hierarchy emit independently) — v1.4.1 Phase 56
- ✓ `OmniFocusPreferences` extension — `OFMCompleteWhenLastItemComplete` / `OFMTaskDefaultSequential` via existing bridge-based lazy-load-once pattern — v1.4.1 Phase 56

### Active

- [ ] Subtree retrieval — `parent` filter on `list_tasks` with `collect_subtree` helper, repo-layer filter unification (v1.4.1 Phase 57)
- [ ] Project writes — add_projects, edit_projects (v1.5)
- [ ] UI & Perspectives — show/get perspective, open_task, live UI reads (v1.6)
- [ ] Production hardening — retry, crash recovery, serial execution (v1.7)

### Out of Scope

- Workflow-specific logic (daily review, prioritization) -- server is a general-purpose bridge; workflow lives in the agent
- Custom exception hierarchy -- use standard Python exceptions, refine when real error patterns emerge
- Task reactivation (markIncomplete) — OmniJS API unreliable, deferred
- Tag writes, folder writes, task reordering, undo/dry run — future milestones
- Mobile/iOS support -- OmniFocus desktop only (macOS)
- TaskPaper output format -- future milestone
- Production hardening (retry logic, crash recovery, idempotency) -- future milestone
- MCP Prompts -- workflow-specific; server exposes primitives only
- WebSocket/SSE transport -- stdio only, local server
- AppleScript/osascript bridge -- file-based IPC is the differentiator
- Real-time file watching for snapshot -- mtime check on read is sufficient
- Automatic SQLite-to-OmniJS failover -- silent fallback hides broken state; user must know which path is active
- SQLite write path -- OmniFocus owns the database; writing to its cache corrupts state
- Caching layer on top of SQLite -- 46ms full snapshot is fast enough
- `next` availability value -- not present in SQLite or OmniJS
- Schema migration / version detection -- OmniFocus SQLite schema stable since OF1

## Context

Shipped v1.4 with ~12,438 LOC Python (src/), ~215k LOC JS (bridge + deps), ~28k TS (tests).
Tech stack: Python 3.12, uv, Pydantic v2, FastMCP v3 (`fastmcp>=3.1.1`), pydantic-settings, OmniJS bridge, SQLite3 (stdlib).
2,167 pytest tests, 26 Vitest tests, UAT passed on all phases.
Real OmniFocus database: ~2,400 tasks, ~363 projects, ~64 tags, ~79 folders.
Read path: SQLite (default, ~46ms for full snapshot, <6ms for filtered queries). Write path: OmniJS bridge with write-through guarantee.
11 MCP tools: get_all, get_task, get_project, get_tag, add_tasks, edit_tasks, list_tasks, list_projects, list_tags, list_folders, list_perspectives.
Architecture: service/ package (Resolver, DomainLogic, PayloadBuilder, orchestrator + read pipelines), contracts/ package (per-use-case packages: list/, add/, edit/), server/ package (handlers, lifespan, projection), tests/doubles/ (InMemoryBridge, StubBridge, SimulatorBridge).
Response shaping: universal null/empty/false stripping via projection.py; field groups (notes/metadata/hierarchy/time/*) in config.py; include/only on list tools; count-only via limit:0.
Inherited fields: 6 inherited* fields (dueDate, deferDate, plannedDate, flagged, dropDate, completionDate) on Task only; computed from ancestor chain with per-field aggregation (min/max/first-found/any-True).
Batch writes: add_tasks best-effort (up to 50), edit_tasks fail-fast (up to 50); per-item status/id/name/error/warnings; batch result stripping via strip_batch_results.
Note editing: actions.note.append (\\n separator, whitespace-only no-op) / actions.note.replace on edit_tasks; top-level note on add_tasks only.
Query infrastructure: typed query models → service resolution cascade → parameterized SQL builder → repository → ListResult[T] with total_count and warnings.
Date filtering: 7-dimension date filters with discriminated union (ThisPeriod, LastPeriod, NextPeriod, AbsoluteRange), calendar-aware arithmetic, naive-local datetime contract.
OmniFocus preferences: OmniFocusPreferences module reads user settings via OmniJS `settings.objectForKey()`, lazy-loaded with factory-default fallback.
Agent-facing docs: all descriptions centralized in agent_messages/descriptions.py with AST enforcement tests.
RRULE: rrule/ module (parse_rrule, build_rrule) shared by both read paths, flat Frequency model with 6 types, FrequencyAddSpec/FrequencyEditSpec command models.
Golden master: 43 scenarios in 7 categories, contract tests verify InMemoryBridge matches RealBridge.
Logging: ToolLoggingMiddleware + ValidationReformatterMiddleware for automatic tool call logging and error formatting, dual-handler (stderr + rotating file) under `omnifocus_operator.*` namespace.
System locations: `$inbox` system location with `$` prefix namespace, three-step resolver cascade (system location → ID → name). All output refs enriched to `{id, name}` objects.
Patch semantics: all write fields and list query filters use `Patch[T]` — null eliminated from agent-facing schemas everywhere.
Known upstream issue: MCP progress-notification transport disconnect (Claude Code CLI 2.1.105+ regression, #47378) — progress notifications disabled via `PROGRESS_NOTIFICATIONS_ENABLED=False` in config.py pending upstream fix.

## Constraints

- **Language**: Python 3.12+ with async, Pydantic models, MCP SDK
- **Platform**: macOS only -- OmniFocus is a macOS application
- **Runtime deps**: `fastmcp>=3.1.1` only -- zero new deps in v1.1 (stdlib sqlite3)
- **IPC directory**: `~/Library/Containers/com.omnigroup.OmniFocus4/Data/Documents/omnifocus-operator/` (configurable for dev/test)
- **SQLite path**: `~/Library/Group Containers/34YW5A3IGP.com.omnigroup.OmniFocus/com.omnigroup.OmniFocus4/OmniFocusDatabase.db`
- **Field naming**: JSON from OmniFocus is camelCase; Pydantic uses snake_case with camelCase aliases for serialization
- **Dev commands**: Run tests: `uv run pytest`. Run Python: `uv run python`. Always use `uv run` — never bare `pytest` or `python`.
- **GOLD-01**: Any phase that adds or modifies bridge operations must re-capture the golden master (`uat/capture_golden_master.py`) and add contract test coverage for the new behavior. Golden master = source of truth for "what OmniFocus actually does."

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Dumb bridge, smart Python | Bridge is a relay, not a brain. ALL validation, resolution, diff computation, and business logic lives in Python. Bridge receives pre-validated payloads and executes without interpretation. OmniJS freezes the UI and has sharp edges — minimize time there | Good -- bridge is ~400 lines of relay; ~14,000 lines of tested Python |
| Three-layer architecture (MCP -> Service -> Repository) | Clear separation of concerns; service layer is thin in M1 but reserves space for filtering in M2 | Good -- clean boundaries, easy to test each layer independently |
| File-based IPC via OmniFocus sandbox | Benchmarked as most efficient; works within OmniFocus sandbox constraints | Good -- reliable, debuggable, atomic |
| Full snapshot in memory, no partial invalidation | Database is small (~1.5MB); sub-millisecond filtering; simplicity over complexity | Good -- no performance issues at 2,400 tasks |
| Workflow-agnostic server | Expose primitives, not opinions; workflow logic belongs in the agent | Good -- keeps server scope minimal |
| Fail-fast on unknown enum values | Pydantic ValidationError with clear listing of valid values; no silent fallback | Good -- caught real data issues during UAT |
| Error-serving degraded mode | MCP servers are headless; crashes are invisible. Serve errors as tool responses | Good -- agent discovers errors on first call with clear message |
| Two-axis status model (Urgency + Availability) | Matches OmniFocus internal representation; single-winner enums lost information | Good -- richer status semantics, cleaner model |
| SQLite cache as primary read path | 46ms vs multi-second bridge round-trip; no OmniFocus process needed | Good -- massive perf improvement, simpler architecture |
| Repository protocol (structural typing) | Swappable implementations without inheritance coupling | Good -- HybridRepository, BridgeRepository, InMemoryRepository all interchangeable |
| Dict-based adapter mapping tables | Static mapping = dict lookup, not if/elif; in-place modification for zero-copy | Good -- fast, readable, easily extensible |
| WAL mtime for freshness detection | WAL updates on every write; mtime_ns gives nanosecond precision | Good -- reliable read-after-write consistency |
| Manual bridge fallback via env var | Silent automatic failover hides broken state; user must know which path is active | Good -- explicit is better than implicit |
| Project-first parent resolution | When resolving a parent ID, try `get_project` before `get_task`. Project takes precedence. In practice IDs don't collide, but the order is intentional and deterministic | ✓ Good — v1.2 |
| Patch semantics via sentinel pattern | Edit models use UNSET sentinel to distinguish "not provided" from "null" (clear) from "value" (set). Pydantic can't distinguish omitted from None natively, sentinel solves the three-way | ✓ Good — clean API, no ambiguity |
| moveTo "key IS the position" design | Task movement expressed as `{"moveTo": {"ending": "parentId"}}` -- the key (beginning/ending/before/after) IS the position, the value IS the reference. Exactly one key allowed. Makes illegal states unrepresentable | ✓ Good — maps directly to OmniJS position API |
| Educational warnings in write responses | Write results include optional `warnings` array for no-ops with hints. Teaches agents patch semantics in-context | ✓ Good — LLMs learn from tool responses |
| Actions block grouping | edit_tasks separates idempotent field setters (top-level) from stateful operations (actions: tags/move/lifecycle). Clean semantic boundary | ✓ Good — extensible design |
| Diff-based tag computation | _compute_tag_diff in Python service, bridge receives only addTagIds/removeTagIds. Replaced 4-branch JS dispatch with ~4 lines | ✓ Good — simpler bridge, logic in Python |
| Lifecycle via Literal type | `lifecycle: Literal["complete", "drop"]` — Pydantic validates, no dedicated enum needed | ✓ Good — minimal surface area |
| Write-through guarantee | `@_ensures_write_through` decorator ensures writes block until SQLite confirms; reads never wait | ✓ Good — consistent read-after-write |
| "Add" verb for creation tools | Tool names use `add_*` (not `create_*`). "Add" is domain-native (OmniJS, task management UX), matches natural voice ("add a task"), and forms coherent verb system (add/edit/delete). Tool descriptions use natural language freely for discoverability. Write-side model names align: `AddTask*`, `EditTask*` | Decision locked pre-publish — rename `CreateTask*` → `AddTask*` pending |
| Service as package with DI | service.py → service/ with Resolver, DomainLogic, PayloadBuilder injected into orchestrator. Each module independently testable | ✓ Good — v1.2.1, enables targeted testing and clear boundaries |
| Method Object pattern for use cases | Every use case gets a `_VerbNounPipeline` class; created, executed, discarded in one call. Mutable self is fine | ✓ Good — v1.2.1, clean pipeline pattern |
| Golden master for contract testing | Capture RealBridge behavior via UAT, commit as fixtures, verify InMemoryBridge matches in CI. Source of truth = OmniFocus actual behavior | ✓ Good — v1.2.1, 43 scenarios, catches drift automatically |
| Structural import barrier for test doubles | Test doubles in tests/doubles/, production code in src/. Structural impossibility of importing test code in production | ✓ Good — v1.2.1, eliminates a class of mistakes |
| Patch[T]/PatchOrClear[T] type aliases | Make three-way semantics (unset/null/value) visible in annotations. Identical JSON schema, pure readability gain | ✓ Good — v1.2.1, self-documenting models |
| FastMCP v3 standalone package | Migrated from `mcp.server.fastmcp` to `fastmcp>=3.1.1` standalone. Native imports, `ctx.lifespan_context` shorthand, `Client(server)` test pattern | ✓ Good — v1.2.2, cleaner API, simpler tests |
| ToolLoggingMiddleware via cross-cutting concern | FastMCP Middleware base class with injected logger. Zero per-tool wiring needed — new tools get logging automatically | ✓ Good — v1.2.2, eliminated 6 manual log_tool_call() sites |
| Dual-handler logging (stderr + rotating file) | StreamHandler(stderr) for Claude Desktop visibility + 5MB RotatingFileHandler for persistent debugging. `__name__` convention across all 10 modules | ✓ Good — v1.2.2, observable in both contexts |
| ToolAnnotations stays at mcp.types | FastMCP doesn't re-export `ToolAnnotations`. Intentional residual `from mcp.types import ToolAnnotations` with TODO | — Pending — revisit when fastmcp re-exports |
| Custom RRULE parser over python-dateutil | Purpose-built for OmniFocus RRULE subset, 79 spike tests, zero new deps. Round-trip validated against 15 golden master strings | ✓ Good — v1.2.3, precise and dependency-free |
| Flat Frequency model over discriminated union | 9-subtype union made type-optional edits impossible (Pydantic requires discriminator). Single flat model with optional specialization fields solves merge cleanly | ✓ Good — v1.2.3, enabled the entire edit merge flow |
| @field_validator over Field(ge=1) for interval/occurrences | Custom validators produce clean educational errors; Field constraints generate opaque Pydantic messages | ✓ Good — v1.2.3, agent-facing error quality |
| FrequencyEditSpec as pure patch container | No validators on edit spec — validation fires on Frequency construction from merged result. Keeps edit path flexible | ✓ Good — v1.2.3, clean separation of patch vs validation |
| Output schema regression via jsonschema | Test serialized output with same JSON Schema validator MCP clients use, not Pydantic. Catches @model_serializer schema erasure | ✓ Good — v1.2.3, caught real regression during development |
| Parameterized SQL builder as pure functions | Query builder returns `SqlQuery(sql, params)` NamedTuple — no string interpolation, testable without database | ✓ Good — v1.3, zero injection surface, easy to unit test |
| Fetch-all + Python filter for small collections | Tags/folders/perspectives use full fetch + Python filtering instead of SQL — collections are small, code is simpler | ✓ Good — v1.3, avoids over-engineering |
| Name-to-ID resolution at service boundary | Service resolves all entity names to IDs before repository. RepoQuery is IDs-only. Prevents SQL/in-memory drift | ✓ Good — v1.3, clean boundary, single resolution point |
| ValidationReformatterMiddleware for error formatting | Middleware catches Pydantic ValidationError and reformats to agent-friendly ToolError before logging middleware sees it | ✓ Good — v1.3, clean error surface across all tools |
| Description centralization in agent_messages/ | All agent-visible Field(description=) and class docstrings use constants from descriptions.py with AST enforcement | ✓ Good — v1.3, single source of truth, prevents drift |
| Literal/Annotated reserved for contract models | Core models use plain types; schema-level constraints only on contract boundary. AST enforcement test prevents regression | ✓ Good — v1.3, clean taxonomy boundary |
| DEFAULT_LIST_LIMIT=50 on all list tools | Prevents unbounded responses (1.8M chars for full DB). Agent can override with limit=None | ✓ Good — v1.3, protects agent context windows |
| Cross-path equivalence as hard requirement | 32 parametrized tests prove SQL and bridge paths return identical results. Mandatory for any new filter | ✓ Good — v1.3, catches drift automatically |
| `$` prefix namespace for system locations | `$inbox` is an ID-level convention, not a display name. Three-step resolver: system location → ID → name. Extensible to future system locations | ✓ Good — v1.3.1, clean separation of API convention from display |
| Tagged parent discriminator over nullable union | `{"project": {id,name}}` / `{"task": {id,name}}` instead of `{type, id} | null`. Inbox = `{project: {id: "$inbox", name: "Inbox"}}`. Never null | ✓ Good — v1.3.1, self-describing, no null ambiguity |
| Rich `{id, name}` refs on all cross-entity fields | Every foreign reference is an object, not a bare ID. Agents never need a second lookup to know what a reference points to | ✓ Good — v1.3.1, eliminates entire class of follow-up calls |
| Null elimination from agent-facing schemas | All write fields and list query filters use `Patch[T]` with UNSET default. Null rejected with educational error. Service translates UNSET→None at repo boundary | ✓ Good — v1.3.1, clean three-way semantics everywhere |
| AvailabilityFilter enums with ALL shorthand | `["all"]` expands to full `list(Availability)` at service layer. Mixed `["all", "available"]` accepted with warning | ✓ Good — v1.3.1, ergonomic for agents |
| DateFilter contract model | Duration (`3d`), this (`w`), absolute (`before`/`after`) forms with dedicated error constants per input type | ✓ Good — v1.3.2, educational errors guide agents |
| DueSoonSetting enum over raw SQLite ints | 7-member enum with `.days` and `.calendar_aligned` domain properties replaces leaked storage format | ✓ Good — v1.3.2, clean domain API |
| pydantic-settings Settings class | All 7 OPERATOR_* env vars consolidated from 5 scattered files into single BaseSettings class with `get_settings()` singleton | ✓ Good — v1.3.2, single source of truth for config |
| OmniFocusPreferences module via bridge settings | Lazy-loaded singleton reading OmniJS `settings.objectForKey()`, domain-typed output (DueSoonSetting enum, normalized time strings), factory-default fallback with warning | ✓ Good — v1.3.2, single source of truth for OmniFocus preferences |
| Field-aware date normalization | `normalize_date_input(value, default_time)` — caller provides default time from preferences, keeps domain.py pure/sync. Each date field gets its configured default | ✓ Good — v1.3.2, matches OmniFocus UI behavior |
| Recursive CTE for outline ordering | Three-anchor CTE (project roots, inbox roots, recursive children) with rank-based sort_path. Python computes dotted ordinals from sorted rows (avoids SQLite ROW_NUMBER() in recursive CTEs) | ✓ Good — v1.3.3, exact OmniFocus outline order |
| Full CTE for sparse ordinals | list_tasks runs full unfiltered CTE to compute orders, then filtered query for results. Preserves original ordinals (1, 3) when filters remove siblings | ✓ Good — v1.3.3, consistent ordering across filtered views |
| Always-translate move pattern | `_process_container_move` always translates beginning/ending to before/after when container has children. No same-vs-different branching | ✓ Good — v1.3.3, simpler code path, fixes OmniFocus API quirk |
| Move translation in domain.py | Translation lives in domain.py per architecture litmus test — product decision to fix OmniFocus API limitation, not universal plumbing | ✓ Good — v1.3.3, correct layer placement |
| Position-specific no-op via self-reference | `anchor_id == task_id` detects no-op after translation. MOVE_ALREADY_AT_POSITION with `{position}` placeholder shows "already at beginning/ending" | ✓ Good — v1.3.3, actionable agent guidance |
| `_is_strip_value` helper for STRIP_VALUES | `frozenset` can't contain `list` (unhashable). Pure `isinstance` check before frozenset lookup. `projection.py` is pure dict-transform on `model_dump(by_alias=True)` output | ✓ Good — v1.4, server-only concern, zero model coupling |
| `ancestor_vals` dict for inheritance walk | Tracks actual computed values (dates/bools), not presence booleans. Strategy constants (`_MIN_FIELDS`, `_MAX_FIELDS`, `_FIRST_FOUND_FIELDS`) as frozensets for O(1) lookup | ✓ Good — v1.4, explicit per-field semantics, matches OmniFocus empirical behavior |
| NoteAction mirrors TagAction exactly | Same file, same `model_validator`, same constant-family style. Exclusivity validator prevents append+replace in same call | ✓ Good — v1.4, consistent actions block pattern |
| Batch result stripping via `strip_batch_results` | Separate helper from `strip_entity` — batch items are flat dicts not full entities; `status` always preserved | ✓ Good — v1.4, correct projection boundary, closed stripping asymmetry |
| `\\n` separator in note append (not `\\n\\n`) | Minimal-useful-separator principle — agent can prepend own `\\n` for paragraph break; `\\n\\n` default couldn't be reduced. OmniFocus renders `\\n` as visible soft break | ✓ Good — v1.4, agent-controllable with sensible default |

---
## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-19 — Phase 56 (Task Property Surface) complete. Read + write surfaces shipped end-to-end for `completesWithChildren`, per-type `type`, presence flags, expanded `hierarchy` include group, no-suppression invariant, `OmniFocusPreferences` extension. 2 gaps logged in `56-HUMAN-UAT.md` for follow-up: (G1) hoist `isSequential` to projects + ActionableEntity, (G2) golden master via canonical `uat/capture_golden_master.py` pattern instead of 56-07's InMemoryBridge baseline. Phase 57 (Subtree retrieval) is next in this milestone.*
