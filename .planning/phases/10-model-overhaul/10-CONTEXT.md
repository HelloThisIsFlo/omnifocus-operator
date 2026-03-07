# Phase 10: Model Overhaul - Context

**Gathered:** 2026-03-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace single-winner status enums (TaskStatus, ProjectStatus) with two-axis model (Urgency + Availability). Remove deprecated fields from all entity models. Update bridge.js to remove dead fields. Update all tests and fixtures to new model shape. This is the most significant phase -- touching the core data model that everything builds on.

</domain>

<decisions>
## Implementation Decisions

### Enum value format
- ALL enums switch to snake_case values: `"overdue"`, `"due_soon"`, `"available"`, `"on_hold"`, `"dropped"`, etc.
- This applies to: Urgency, Availability, TagStatus, FolderStatus, ScheduleType, AnchorDateKey
- JSON field names stay camelCase (MCP/JSON standard via Pydantic `to_camel` alias generator)
- Example output: `{"urgency": "due_soon", "availability": "available", "dueDate": "2026-03-15T..."}`

### Breaking change stance
- Clean break, zero backward compatibility code
- No deprecation warnings, no dual fields, no migration path
- Stay v1.1 (not v2.0) -- no real users yet, reserve v2.0 for workflow logic
- Document changes in release notes only

### Bridge script approach
- **Bridge stays dumb**: No new computation or logic added to bridge.js
- bridge.js keeps outputting old-format status enums (TaskStatus, ProjectStatus)
- bridge.js DOES get cleaned up: remove dead fields that models no longer consume (active, effectiveActive, completed (bool), sequential, completedByChildren, shouldUseFloatingTimeZone, containsSingletonActions, allowsNextAction)
- **Python adapter in bridge layer**: RealBridge/SimulatorBridge run a transform step that maps old bridge status -> new urgency/availability before Pydantic parsing
- Availability is partial from bridge (no `blocked` distinction) -- this is expected and documented in research
- InMemoryBridge uses new-shape fixtures directly (no adapter needed)
- Vitest tests (26 tests) updated to match bridge.js field removals

### Field removal
- Remove ALL fields per research -- no exceptions:
  - From OmniFocusEntity: `active`, `effective_active`
  - From ActionableEntity: `completed` (bool), `sequential`, `completed_by_children`, `should_use_floating_time_zone`
  - From Project: `contains_singleton_actions`, `status` (ProjectStatus), `task_status` (TaskStatus)
  - From Task: `status` (TaskStatus)
  - From Tag: `allows_next_action`
- Enums deleted: `TaskStatus`, `ProjectStatus`
- Fields kept (confirmed): `estimated_minutes`, `has_children`
- Tag/Folder losing `active`/`effective_active` is fine -- their own status enums encode the same info

### Simulator data
- Simulator data (data.py) stays in sync with bridge.js output format
- When bridge.js removes dead fields, simulator data removes them too
- Both SimulatorBridge and RealBridge go through the same Python adapter
- Simulator tests validate the adapter path

### Test migration strategy
- Claude's Discretion on granularity, but MUST be incremental
- Tests green at every commit -- no big-bang migration
- 67 occurrences across 5 test files + 26 Vitest tests

### UAT approach
- Dedicated UAT script in existing `uat/` folder
- UAT creates its own test hierarchy in OmniFocus via JS script (tasks, projects with known statuses)
- Validates output through the full pipeline (RealBridge -> adapter -> new models)
- Cleans up created entities after validation
- Does NOT touch user's real data -- only validates entities it created
- Does NOT rely on specific values from user's database

### Claude's Discretion
- Incremental migration granularity (one model at a time, one change type at a time, etc.)
- Exact adapter implementation pattern
- Loading skeleton for test migration ordering
- Vitest test update approach

</decisions>

<specifics>
## Specific Ideas

- "This is maybe the most significant phase of the entire project because we're touching the core"
- "OmniFocus is extremely, extremely, extremely slow -- keep the bridge as dumb as possible. Any computation, put it in Python"
- "Use this as an opportunity to simplify and unify models" per research
- UAT pattern inspiration: research folder has examples of JS scripts that create tasks in OmniFocus and cleanly delete them afterwards
- Bridge rule: can change (remove fields, clean up) but must NOT gain new computation logic

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `OmniFocusBaseModel` with ConfigDict (camelCase aliases, validate_by_name) -- foundation stays
- `OmniFocusEntity` -> `ActionableEntity` hierarchy -- gets simplified (fields removed)
- `TYPE_CHECKING` + `model_rebuild` pattern for ruff TC + Pydantic compat -- keep using
- SimulatorBridge inherits RealBridge, overrides only `_trigger_omnifocus` -- adapter applies to both

### Established Patterns
- Fail-fast on unknown enum values at bridge boundary -- maintain this
- `StrEnum` for all enums -- continue with new Urgency/Availability
- Lazy cache hydration -- unaffected by model changes
- File-based IPC with atomic writes -- unaffected

### Integration Points
- `models/enums.py`: Add Urgency, Availability; delete TaskStatus, ProjectStatus; update TagStatus, FolderStatus, ScheduleType, AnchorDateKey values
- `models/base.py`: Remove fields from OmniFocusEntity and ActionableEntity
- `models/task.py`: Replace status with urgency + availability
- `models/project.py`: Replace status + task_status with urgency + availability; remove contains_singleton_actions
- `models/tag.py`: Remove allows_next_action
- `bridge/real.py` or new `bridge/adapter.py`: Python mapping from old bridge output -> new model shape
- `simulator/data.py`: Remove dead fields from fixture data
- `bridge.js`: Remove dead field emissions
- `tests/`: 67 occurrences across 5 files
- Vitest tests: 26 tests for bridge.js

</code_context>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 10-model-overhaul*
*Context gathered: 2026-03-07*
