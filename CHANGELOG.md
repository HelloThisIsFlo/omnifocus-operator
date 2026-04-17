# Changelog

All notable changes to OmniFocus Operator are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/). Versions follow semantic versioning.

## [Unreleased]

### Added
- PyPI publishing via `uvx omnifocus-operator`
- Dynamic versioning with `hatch-vcs` (git tags as source of truth)
- Platform check — non-macOS prints clear error and exits

## [1.4] - Response Shaping & Batch Processing

### Added
- Response stripping — null/`[]`/`""`/`false`/`"none"` auto-removed from entity fields; `availability` and envelope fields always preserved
- `include` on `list_tasks` / `list_projects` — add field groups to defaults: `notes`, `metadata`, `hierarchy`, `time`, `*` (projects also: `review`)
- `only` on `list_tasks` / `list_projects` — return exactly named fields; `id` always included; mutually exclusive with `include`
- `limit: 0` returns count-only: `{items: [], total: N, hasMore: ...}`
- Batch processing — `add_tasks` / `edit_tasks` accept up to 50 items per call with per-item `status` / `warnings`; `add_tasks` best-effort, `edit_tasks` fail-fast
- `actions.note.append` on `edit_tasks` — appends text with `\n` separator; whitespace-only is a no-op
- `actions.note.replace` on `edit_tasks` — replaces full note; `null` or `""` clears

### Changed
- `effective*` → `inherited*` across all tool responses (6 fields: dueDate, deferDate, plannedDate, flagged, dropDate, completionDate) — **breaking rename**
- `inherited*` fields now only appear when truly inherited from an ancestor — self-values stripped; per-field aggregation: min (dueDate), max (deferDate), OR (flagged), first-found (others)
- Top-level `note` removed from `edit_tasks` input — use `actions.note.append` / `actions.note.replace` — **breaking**

## [1.3.3] - Ordering & Move Fix

### Added
- `order` field on task responses — 1-based integer reflecting outline order within parent

### Fixed
- `moveTo beginning/ending` on same container no longer silently ignored
- Move no-op warning now checks ordinal position, not just container membership

## [1.3.2] - Date Filtering

### Added
- Date filters on `list_tasks`: `due`, `defer`, `planned`, `completed`, `dropped`, `added`, `modified`
- String shortcuts: `"today"`, `"overdue"`, `"soon"`, `"any"`, `"none"`
- Shorthand periods: `{this: "w"}`, `{last: "3d"}`, `{next: "1m"}`
- Absolute bounds: `{after: "...", before: "..."}`
- Configurable due-soon threshold (`OPERATOR_DUE_SOON`)

### Changed
- `urgency` filter removed — absorbed into `due: "overdue"` and `due: "soon"`
- `completed` boolean filter replaced by `completed` date filter

## [1.3.1] - First-Class References

### Added
- `$inbox` system location — explicit inbox representation across all API surfaces
- Name-based entity resolution: `parent: "My Project"`, `ending: "Work"` (case-insensitive substring match)
- Rich `{id, name}` references on all output models
- `project` field on Task output — containing project at any nesting depth

### Changed
- `parent` field on Task changed from `ParentRef` to tagged `{"project": {...}}` or `{"task": {...}}`
- Inbox tasks use `ProjectRef(id="$inbox", name="Inbox")` — parent is never null
- `inInbox` removed from Task output (derivable from `project.id == "$inbox"`)

## [1.3.0] - Read Tools

### Added
- `list_tasks` — filter by inbox, flagged, project, tags, availability, search, with pagination
- `list_projects` — filter by status, folder, review schedule, flags
- `list_tags` — filter by status
- `list_folders` — filter by status
- `list_perspectives` — list all perspectives
- SQL WHERE clause filtering against SQLite cache (<6ms filtered queries)

## [1.2.3] - Repetition Rules

### Added
- Repetition rule support on `add_tasks` and `edit_tasks`
- 8 structured frequency types: daily, weekly, monthly variants, yearly
- Partial update semantics for rule modifications

### Changed
- Read model returns structured frequency fields instead of raw `ruleString`

## [1.2.2] - FastMCP v3 Migration

### Added
- Progress reporting for batch operations
- Dual-handler logging: stderr + `~/Library/Logs/omnifocus-operator.log`
- `ToolLoggingMiddleware` for automatic tool call logging

### Changed
- Migrated from `mcp.server.fastmcp` to standalone `fastmcp>=3`
- Test client simplified via `async with Client(server)`

## [1.2.1] - Architectural Cleanup

### Changed
- Unified service-repository write interface
- Service layer decomposed into orchestration + extracted modules
- Write models reject unknown fields (`extra="forbid"`)

## [1.2.0] - Writes & Lookups

### Added
- `get_task` — single task lookup by ID with computed fields
- `get_project` — single project lookup by ID
- `get_tag` — single tag lookup by ID
- `add_tasks` — create tasks with full field control
- `edit_tasks` — patch semantics (omit = no change, null = clear, value = set)
- Tag editing modes: replace, add, remove
- Task movement and lifecycle changes (complete/drop/reactivate)

## [1.1.0] - Performance

### Added
- `HybridRepository` — reads from OmniFocus SQLite cache (~46ms full snapshot, 30–60x faster)
- WAL-based read-after-write freshness detection
- Repository protocol with pluggable implementations

### Changed
- Two-axis status model (Urgency + Availability) replacing single-winner enums

## [1.0.0] - Foundation

### Added
- `get_all` tool — full OmniFocus database snapshot as structured data
- Three-layer architecture: MCP Server → Service → Repository
- Pluggable bridge abstraction: InMemoryBridge, SimulatorBridge, RealBridge
- File-based IPC engine with OmniJS bridge script
- Error-serving degraded mode for headless servers
