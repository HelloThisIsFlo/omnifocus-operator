---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: Writes & Lookups
status: completed
stopped_at: Deferred work moved to milestone specs (v1.2.1, v1.2.2, v1.3.1), phases 17.1 and 18 removed from roadmap
last_updated: "2026-03-15"
last_activity: "2026-03-15 - Created milestone specs for deferred work, cleaned up roadmap"
progress:
  total_phases: 6
  completed_phases: 6
  total_plans: 21
  completed_plans: 21
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-12)

**Core value:** Reliable, simple, debuggable access to OmniFocus data for AI agents -- executive function infrastructure that works at 7:30am.
**Current focus:** All v1.2 phases complete. Deferred work moved to milestone specs. Pending milestone audit + completion.

## Current Position

Phase: 17 (Task Lifecycle)
Plan: 3 of 3
Status: All phases complete. Phases 17.1 and 18 removed from roadmap (moved to milestone specs v1.2.1, v1.2.2).
Last activity: 2026-03-15 - Created milestone specs for deferred work, cleaned up roadmap

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**
- Total plans completed: 21 (v1.2)
- Average duration: 3.6min
- Total execution time: 67min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 14 | 2/2 | 10min | 5min |
| 15 | 4/4 | 19min | 4.8min |
| 16 | 6/6 | 22min | 3.7min |
| 16.1 | 3/3 | 11min | 3.7min |
| 16.2 | 3/3 | 9min | 3min |
| 17 | 3/3 | 12min | 4min |

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
- [Phase 16.1]: Error assertion: 'Cannot use tags' -> 'Cannot use replace' to match TagActionSpec validator message
- [Phase 16.2]: Diff-based tag computation: _compute_tag_diff computes minimal (add, remove) sets from TagActionSpec
- [Phase 16.2]: No tagMode in payload -- empty diff = no tag keys = implicit no-op via len(payload) check
- [Phase 16.2]: Replace no-op warning when replace produces empty diff (tags already match)
- [Phase 16.2]: resolveTagIds helper inside handleEditTask scope for locality
- [Phase 16.2]: Stale-check pattern applied to all get-by-ID methods (get_task, get_project, get_tag)
- [Phase 16.2]: No-op warning uses append instead of conditional assignment for proper stacking
- [Phase 17]: Literal["complete", "drop"] for lifecycle -- Pydantic validates, no dedicated enum needed
- [Phase 17]: _process_lifecycle helper returns (should_call_bridge, warnings) tuple
- [Phase 17]: lifecycle_handled flag suppresses generic status warning (no contradictory messages)
- [Phase 17]: drop(false) universally in bridge.js -- handles both repeating and non-repeating tasks
- [Phase 17]: Lifecycle processed before status warning to control suppression flow
- [Phase 17]: Server tests verify lifecycle flows through InMemoryBridge at integration level
- [Phase 17]: Guard suppression via `not warnings` check -- action-specific warnings take priority over generic no-op warnings

### Roadmap Evolution

- Phase 16.1 inserted after Phase 16: Introduce actions grouping to edit_tasks (URGENT)
- Phase 16.2 inserted after Phase 16: Simplify bridge tag handling to diff-based approach (URGENT)
- Phase 18 added: Repetition rule write support: structured fields, not RRULE strings → moved to MILESTONE-v1.2.2.md
- Phase 17.1 inserted after Phase 17: Unify write interface at service-repository boundary (URGENT) → moved to MILESTONE-v1.2.1.md

### Pending Todos (14)

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
| 5 | Update move same-parent warning wording | 2026-03-10 | dc1c60f | [5-update-move-same-parent-warning-wording](./quick/5-update-move-same-parent-warning-wording/) |

### Blockers/Concerns

None currently.

## Session Continuity

Last session: 2026-03-15
Stopped at: Deferred work moved to milestone specs, pending milestone audit + completion
Resume file: N/A (milestone boundary)
