---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: Writes & Lookups
status: in-progress
stopped_at: Completed 16.1-01-PLAN.md
last_updated: "2026-03-09T21:12:54Z"
last_activity: "2026-03-09 - Completed plan 16.1-01: actions grouping models + service refactor"
progress:
  total_phases: 5
  completed_phases: 3
  total_plans: 15
  completed_plans: 13
  percent: 87
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-07)

**Core value:** Reliable, simple, debuggable access to OmniFocus data for AI agents -- executive function infrastructure that works at 7:30am.
**Current focus:** Phase 16.1 - Introduce actions grouping to edit_tasks

## Current Position

Phase: 16.1 (Actions Grouping) -- inserted after Phase 16
Plan: 1 of 3 (complete)
Status: Plan 01 complete (models + service), plans 02-03 remaining (test rewrites)
Last activity: 2026-03-09 - Completed plan 16.1-01: actions grouping models + service refactor

Progress: [████████░░] 87%

## Performance Metrics

**Velocity:**
- Total plans completed: 12 (v1.2)
- Average duration: 4.3min
- Total execution time: 43min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 14 | 2/2 | 10min | 5min |
| 15 | 4/4 | 19min | 4.8min |
| 16 | 6/6 | 22min | 3.7min |
| 16.1 | 1/3 | 3min | 3min |

## Accumulated Context

### Decisions

- Unified `parent` field on read model (ParentRef with type + id, null = inbox) replaces separate project + parent fields
- Write model takes plain ID for parent (server resolves type), null = move to inbox
- CQRS split: rich read model, simple write model
- NAME-01 bundled with Phase 14 (model changes + lookups)
- Parent task takes precedence over containing project in ParentRef (subtask case)
- Bridge adapter uses empty string for name when bridge doesn't send name fields
- [Phase 14]: HybridRepository uses dedicated single-entity SQLite queries for get-by-ID (not filtering _read_all)
- [Phase 14]: Not-found raises ValueError -> MCP SDK wraps as isError: true response
- [Phase 15]: Write models inherit OmniFocusBaseModel for consistent camelCase serialization
- [Phase 15]: Bridge.js handleAddTask receives tag IDs (not names) -- resolution stays in Python service layer
- [Phase 15]: Repository.add_task takes resolved_tag_ids kwarg -- tag resolution in service layer
- [Phase 15]: Factory uses create_bridge() for SAFE-01 compliance in hybrid mode
- [Phase 15]: BridgeRepository invalidates cache (sets _cached=None) on write
- [Phase 15]: items parameter is list[dict] not list[TaskCreateSpec] -- MCP clients send raw JSON, model_validate handles camelCase
- [Phase 15]: plainTextNote column for notes, _parse_local_datetime with ZoneInfo for DST-aware date columns
- [Phase 16]: UNSET sentinel with __get_pydantic_core_schema__ (is_instance_schema) for Pydantic v2 union types
- [Phase 16]: model_json_schema override strips _Unset from JSON schema for clean MCP tool schemas
- [Phase 16]: Bridge tagMode dispatch: replace/add/remove/add_remove with removals-first ordering
- [Phase 16]: Bridge moveTo shape: {position, containerId, anchorId} -- service translates from MoveToSpec
- [Phase 16]: Repository.edit_task takes pre-built dict payload -- service does intelligence, repo does transport
- [Phase 16]: Cycle detection walks parent chain via get_all task map
- [Phase 16]: Assert isinstance for mypy type narrowing after boolean UNSET checks
- [Phase 16]: ValidationError caught at model_validate boundaries, re-raised as clean ValueError
- [Phase 16]: null-means-clear mapping in Python service layer (not bridge.js) -- business logic belongs in Python
- [Phase 16]: Generic no-op detection via field_comparisons dict before bridge delegation
- [Phase 16]: Tag architecture simplification DEFERRED (keep 4-mode approach per user decision)
- [Phase 16]: UTC timestamp comparison for timezone-aware date no-op detection
- [Phase 16]: Same-container move detection limited to beginning/ending positions
- [Phase 16.1]: TagActionSpec/ActionsSpec nested models with field graduation pattern
- [Phase 16.1]: Lifecycle fail-fast before any tag/move resolution work
- [Phase 16.1]: Tasks 1+2 committed together due to mypy requiring consistent model+service state

### Roadmap Evolution

- Phase 16.1 inserted after Phase 16: Introduce actions grouping to edit_tasks (URGENT)
- Phase 16.2 inserted after Phase 16: Simplify bridge tag handling to diff-based approach (URGENT)

### Pending Todos

Carried from v1.0:
1. Add retry logic for OmniFocus bridge timeouts (v1.5)
2. Investigate macOS App Nap impact on OmniFocus responsiveness (v1.5)
3. Make UAT folder discoverable for verification agents

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 1 | Remove eager cache hydration on startup, lazy populate on first tool call | 2026-03-06 | bab6ae6 | [1-remove-eager-cache-hydration-on-startup-](./quick/1-remove-eager-cache-hydration-on-startup-/) |
| 2 | Simplify file layout: drop _ prefixes, collapse server/service/repository packages | 2026-03-07 | b15b42b | [2-simplify-file-layout-drop-prefixes-colla](./quick/2-simplify-file-layout-drop-prefixes-colla/) |
| 3 | Fix skill script enum references (TagStatus->TagAvailability, FolderStatus->FolderAvailability) | 2026-03-07 | c98da9a | [3-fix-deferred-items-from-phase-10-update-](./quick/3-fix-deferred-items-from-phase-10-update-/) |
| 4 | Fix tag warning to resolve name when caller passes an ID (UAT test 71) | 2026-03-09 | 298a704 | [4-fix-tag-warning-to-resolve-name-when-cal](./quick/4-fix-tag-warning-to-resolve-name-when-cal/) |

### Blockers/Concerns

None currently.

## Session Continuity

Last session: 2026-03-09T21:12:54Z
Stopped at: Completed 16.1-01-PLAN.md
Next action: Execute 16.1-02-PLAN.md (test rewrites)
