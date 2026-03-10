# Architecture Overview

## Layer Diagram

```
MCP Tools (get_all, get_task, get_project, get_tag, add_tasks, edit_tasks)
    |
OperatorService              -- validation, parent/tag resolution, delegation
    |
Repository (protocol)        -- async reads + writes -> AllEntities, Task, etc.
    |
    +-- HybridRepository     (production: SQLite reads + Bridge writes)
    +-- BridgeRepository     (fallback: Bridge for both reads and writes)
    +-- InMemoryRepository   (testing: in-memory snapshot, synthetic writes)
```

## Package Structure

```
omnifocus_operator/
    bridge/          -- OmniFocus communication (IPC, in-memory, simulator)
    repository/      -- Data access protocol + implementations + factory
    models/          -- Pydantic models (entities, enums, read/write specs)
    simulator/       -- Mock OmniFocus simulator for IPC testing
    server.py        -- FastMCP tool registration + wiring
    service.py       -- Validation, resolution, delegation to repository
```

## Repository Protocol

Structural typing (no inheritance required). Current contract:

- `get_all()` -> `AllEntities` -- full snapshot (tasks, projects, folders, tags)
- `get_task(id)` / `get_project(id)` / `get_tag(id)` -> single entity or None
- `add_task(spec, resolved_tag_ids)` -> `TaskCreateResult`
- `edit_task(spec, ...)` -> `TaskEditResult` (Phase 16, planned)

Three implementations: HybridRepository (production), BridgeRepository (fallback), InMemoryRepository (tests).

## Method Naming Convention

- `get_all()` -> `AllEntities`: structured container with all entity types
- `get_*` by ID -> single entity lookup
- `list_*(filters)` -> flat list of one entity type (e.g., `list_tasks(status=...)`) -- planned for v1.3
- `add_*` / `edit_*` -> write operations
- `get_*` = heterogeneous structured return; `list_*` = homogeneous filtered collection
- `AllEntities` (not `DatabaseSnapshot`) -- no caching/snapshot semantics at the protocol level

## Why Repository, Not DataSource

- Repository implies querying/filtering -- `list_tasks(filters)` in v1.3
- DataSource implies raw data access -- too thin an abstraction
- Repository is the richer contract for how consumers interact with data

## Why Flat Packages (bridge/ and repository/ as peers)

- Bridge is a general OmniFocus communication channel, not just data access
- Future milestones: perspective switching, UI actions -- all via Bridge directly
- Write operations go through Bridge (repository delegates)
- `repository/` depends on `bridge/` (never reverse)
- Keeping them as siblings avoids false nesting (`repository/bridge/` would imply ownership)

## Dependency Direction

- `service.py` -> `Repository` protocol (never concrete implementations)
- `server.py` -> concrete `HybridRepository` + `BridgeRepository` + `Bridge` + `MtimeSource` (wiring only)
- `repository/hybrid.py` -> `bridge/` package (Bridge for writes, SQLite for reads)
- `repository/bridge.py` -> `bridge/` package (Bridge protocol, MtimeSource, adapter)
- `repository/in_memory.py` -> `models/` only (zero bridge dependency)

## Caching & Read Path

- **HybridRepository** (default, primary read path): SQLite cache (~46ms full snapshot, OmniFocus not required)
  - WAL-based freshness detection: 50ms poll, 2s timeout after writes
  - No caching layer on top -- 46ms is fast enough
  - Marks stale after writes; next read waits for fresh WAL mtime
- **BridgeRepository** (fallback via `OMNIFOCUS_REPOSITORY=bridge`): OmniJS bridge dump
  - mtime-based cache invalidation; checks file mtime before each read, serves cached snapshot if unchanged
  - Concurrent reads coalesce into a single bridge dump
- **InMemoryRepository** (tests): no caching (returns constructor snapshot as-is)

## Write Pipeline (v1.2)

- Writes flow: MCP Tool -> Service (validate) -> Repository -> Bridge (execute) -> invalidate cache
- Service validates before bridge execution: task/parent exists, tags exist, name non-empty
- Tag resolution in service: case-insensitive name match, ID fallback, ambiguity error with IDs
- Parent resolution in service: try `get_project` first, then `get_task` -- **project takes precedence** (intentional, deterministic)
- Bridge returns minimal result; service wraps into typed result model
- HybridRepository marks stale after write; BridgeRepository clears cache

## Patch Semantics (edit_tasks)

- Three-way field distinction: omit = no change, null = clear, value = set
- Pydantic sentinel pattern (UNSET) distinguishes "not provided" from "explicitly null"
- Clearable fields: dates, note, estimated_minutes. Value-only: name, flagged
- Bridge payload only includes non-UNSET fields; bridge.js uses `hasOwnProperty()` to detect presence

## Task Movement (moveTo)

"Key IS the position" design -- `moveTo` object has exactly one key:

```json
{"moveTo": {"ending": "proj-123"}}       -- last child of container
{"moveTo": {"beginning": "proj-123"}}    -- first child of container
{"moveTo": {"after": "task-sibling"}}    -- after this sibling (parent inferred)
{"moveTo": {"before": "task-sibling"}}   -- before this sibling (parent inferred)
{"moveTo": {"beginning": null}}          -- move to inbox
```

- One key = one position + one reference. Invalid combos are structurally impossible.
- Maps directly to OmniJS position API: `container.beginning`, `container.ending`, `task.before`, `task.after`
- Full cycle validation via SQLite parent chain walk before bridge call

## Educational Warnings

- Write results include optional `warnings` array for no-ops
- Hints teach agents patch semantics: "Tag 'X' was not on this task -- omit remove_tags to skip"
- Design principle: LLMs learn in-context from tool responses, so warnings serve as runtime documentation

## Field Graduation Pattern

The edit API separates **setters** (top-level fields) from **actions** (operations that modify state):

```json
{
  "id": "xyz",
  "name": "Renamed",        // setter -- simple field replacement
  "flagged": true,           // setter
  "actions": {               // actions -- operations with richer semantics
    "tags": { "add": [...], "remove": [...] },   // or "replace": [...]
    "move": { "after": "sibling-id" },
    "lifecycle": "complete"
  }
}
```

Design principles:
- **Setters** are idempotent field replacements (top-level). Generic no-op warning when value unchanged.
- **Actions** are operations that modify relative to current state (nested under `actions`). Action-specific warnings (e.g., "Tag 'X' is already on this task").
- **Any field can graduate** from setter to action group when it needs more than simple replacement.
  - Migration path:
    1. Remove the field from top-level setters
    2. Add it as an action group under `actions` with `replace` + new operations
  - Example: `note` could graduate to `actions.note: { replace: "...", append: "..." }` when append-note is needed.
- **Tags are the first graduated field** — top-level `tags` (replace-only) becomes `actions.tags` with `add`/`remove`/`replace` modes.
- **Each graduation is independent** — migrate one field at a time as use cases emerge.

## Two-Axis Status Model

- Urgency: `overdue`, `due_soon`, `none` -- time-based, computed from dates
- Availability: `available`, `blocked`, `completed`, `dropped` -- lifecycle state
- Replaces single-winner status enum from v1.0; matches OmniFocus internal representation

## Repetition Rule: Structured Fields, Not RRULE Strings

The read and write models expose repetition as decomposed structured fields — not the raw ICS RRULE string.

```python
RepetitionRule:
  freq: "daily" | "weekly" | "monthly" | "yearly"
  interval: int | None
  byday: list[str] | None          # ["MO", "WE", "FR"]
  bymonthday: int | None           # 1-31 or negative
  bysetpos: int | None             # nth weekday (requires byday)
  count: int | None
  until: str | None                # "20261231T000000Z"
  schedule_type: "regularly" | "from_completion"
  anchor_date_key: "due_date" | "defer_date" | "planned_date"
  catch_up_automatically: bool
```

**Read model** — agent reads a task and gets structured fields:
```json
{
  "repetitionRule": {
    "freq": "monthly",
    "bymonthday": 1,
    "count": 12,
    "scheduleType": "regularly",
    "anchorDateKey": "due_date",
    "catchUpAutomatically": false
  }
}
```

**Edit model** — agent sends back the same shape (modified or as-is):
```json
{
  "id": "task-123",
  "repetitionRule": {
    "freq": "weekly",
    "interval": 2,
    "byday": ["TU", "TH"],
    "until": "20261231T000000Z",
    "scheduleType": "from_completion",
    "anchorDateKey": "defer_date",
    "catchUpAutomatically": true
  }
}
```

**Clear** — standard patch semantics: `"repetitionRule": null`

Why structured fields instead of raw RRULE strings:
- Agents shouldn't need to know ICS RRULE syntax (`FREQ=WEEKLY;BYDAY=MO,WE,FR`) — structured fields are discoverable via JSON schema and natural to work with
- Read and write use the same shape — agents can read a repetition rule, modify a field, and send it back without format conversion
- Validation happens server-side with a zero-dep parser/builder — we don't trust OmniFocus to reject bad input gracefully or return clear errors
- The RRULE string becomes an internal serialization detail between the service layer and bridge

Why top-level (not inside `actions`):
- Setting a repetition rule is idempotent — same input always produces the same result, regardless of current state
- Follows the same pattern as `due_date`, `note` — set, clear, or leave unchanged

Research spike: `.research/deep-dives/rrule-validator/` (parser + builder + 79 tests)

## Deferred Decisions

- Multi-repository coordination in OperatorService (if needed)
