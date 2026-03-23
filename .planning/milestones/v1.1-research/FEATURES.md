# Feature Landscape

**Domain:** SQLite cache read path + two-axis status model for OmniFocus MCP server
**Researched:** 2026-03-07

## Table Stakes

Features the milestone promises. Missing = milestone is incomplete.

| Feature | Why Expected | Complexity | Dependencies |
|---------|--------------|------------|--------------|
| SQLite cache reader | Core deliverable -- 46ms snapshots, no OmniFocus process needed | High | New module, DB path discovery, SQLite queries |
| Two-axis status enums (`Urgency` + `Availability`) | Fixes single-winner masking bug where Overdue hides Blocked | Low | Enum definitions only, no external deps |
| Pydantic model overhaul | Models must match new data source; 6 fields removed, 2 enums replace 2, hierarchy restructured | High | Enums, ActionableEntity, Task, Project, Tag, Folder, OmniFocusEntity all touched |
| WAL-based read-after-write freshness | Writes go through OmniJS bridge; reads must see latest data after a write | Med | WAL file path discovery, mtime polling loop |
| Error-serving when SQLite unavailable | Headless MCP server -- crashes invisible. Must serve actionable error with path fix instructions | Low | Existing pattern from v1.0 ErrorOperatorService |
| OmniJS bridge fallback via `OMNIFOCUS_BRIDGE=omnijs` env var | Escape hatch when SQLite path changes or OmniFocus version breaks | Med | Existing bridge infra, reduced availability mapping |
| Status mapping in fallback mode | OmniJS bridge returns single-winner enum; must map to two-axis with known limitations (`blocked` never returned) | Med | Fallback mode active, mapping logic, documented limitations |

## Differentiators

Features that go beyond "it works" into "it works well."

| Feature | Value Proposition | Complexity | Dependencies |
|---------|-------------------|------------|--------------|
| `active`/`effective_active` removal from OmniFocusEntity | Cleaner API -- status now per-entity-type, not a universal bool. Reduces agent confusion | Med | Ripple through all models, tests, serialization |
| Field removals (`sequential`, `completed_by_children`, `should_use_floating_time_zone`, `contains_singleton_actions`, `allows_next_action`, `completed` bool) | Leaner API surface -- only expose what agents use. OmniFocus internals stay internal | Med | Each removal needs test updates, snapshot fixtures |
| New date fields (`planned_date`, `effective_planned_date`, `drop_date`, `effective_drop_date`) | Richer scheduling data only available from SQLite, not from OmniJS bridge | Low | SQLite column mapping only |
| Repository layer abstraction (SQLite vs Bridge) | Clean swap between data sources without service layer knowing | Med | Protocol/interface design, DI wiring |

## Anti-Features

Features to explicitly NOT build in this milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Automatic SQLite-to-OmniJS failover | Silent fallback hides broken state; user must know which path is active | Error-serve with instructions; manual `OMNIFOCUS_BRIDGE=omnijs` switch |
| SQLite write path | OmniFocus owns the database; writing to its cache corrupts state or gets overwritten | Keep OmniJS bridge as sole write path |
| Caching layer on top of SQLite | 46ms full snapshot is fast enough; caching adds complexity for no measurable gain | Read directly from SQLite on every `get_snapshot()` |
| `next` availability value (first available in sequential project) | Not present in SQLite or OmniJS; niche use case | Omit; add later if contributor demonstrates concrete agent workflow |
| Partial/incremental SQLite reads | Full snapshot is 46ms / ~1.5MB; incremental adds complexity with no user-visible benefit at current scale | Always read full snapshot |
| Schema migration / version detection | OmniFocus SQLite schema stable since OF1 (2008) through OF4 (2023); breakage is path changes, not schema changes | Detect missing DB file and error-serve with path update instructions |
| `completed` boolean alongside `availability` | Redundant -- `availability == completed` and `completion_date is not None` both cover it | Remove; derive from `availability` if needed |

## Feature Dependencies

```
Two-axis enums (Urgency + Availability)
  --> Pydantic model overhaul (models consume new enums)
    --> SQLite cache reader (populates models from SQLite columns)
    --> OmniJS fallback mapping (maps old single-winner to new two-axis)
      --> Error-serving when SQLite unavailable (triggers fallback path)

SQLite cache reader
  --> WAL-based read-after-write (needs SQLite path to find WAL file)
  --> Repository abstraction (SQLite reader implements same protocol as bridge)

Field removals (active, sequential, etc.)
  --> Pydantic model overhaul (same change set)

New date fields (planned_date, drop_date, etc.)
  --> SQLite cache reader (fields only available from SQLite)
```

**Critical path:** Enums --> Model overhaul --> SQLite reader --> WAL freshness

## MVP Recommendation

**Phase 1 -- Model foundation:**
1. Two-axis enums (`Urgency`, `Availability`)
2. Pydantic model overhaul (field adds/removes, hierarchy changes)
3. Update all existing tests and fixtures to new model shape

**Phase 2 -- SQLite read path:**
4. SQLite cache reader (path discovery, query, model population)
5. Repository abstraction (protocol both SQLite and bridge implement)
6. WAL-based read-after-write freshness

**Phase 3 -- Fallback and integration:**
7. OmniJS bridge fallback with reduced availability mapping
8. Error-serving when SQLite unavailable
9. `OMNIFOCUS_BRIDGE=omnijs` env var wiring

**Defer:** Nothing -- all features are in scope for v1.1 per PROJECT.md.

**Ordering rationale:**
- Models first because everything depends on the new shape -- SQLite reader, fallback mapper, and tests all need the target types defined
- SQLite reader before fallback because it's the primary path; fallback adapts existing bridge to new model
- WAL freshness needs SQLite reader to exist first (same DB path)
- Error-serving and env var wiring are integration concerns that layer on top

## Existing Code Impact

Key files that change, with scope of change:

| File | Change Scope | Notes |
|------|-------------|-------|
| `models/enums.py` | `TaskStatus` and `ProjectStatus` deleted; `Urgency` and `Availability` added | `TagStatus`, `FolderStatus`, `ScheduleType`, `AnchorDateKey` unchanged |
| `models/base.py` | `OmniFocusEntity` loses `active`/`effective_active`; `ActionableEntity` loses `completed`/`completed_by_children`/`sequential`/`should_use_floating_time_zone`, gains `urgency`/`availability` | Largest model change |
| `models/task.py` | `status: TaskStatus` removed (now on ActionableEntity as two axes) | Simpler after change |
| `models/project.py` | `status`/`task_status`/`contains_singleton_actions` removed | Simpler after change |
| `models/tag.py` | `allows_next_action` removed (redundant with `status`) | Minor |
| `repository.py` | Must support both SQLite and bridge data sources | New protocol or refactored class |
| All test fixtures | Every fixture producing Task/Project/Tag/Folder snapshots needs updating | High volume, mechanical |

## Sources

- `.research/deep-dives/direct-database-access/RESULTS.md` -- architecture, benchmarks, WAL design
- `.research/deep-dives/direct-database-access/RESULTS_pydantic-model.md` -- field-level contract, removal rationales
- `.planning/PROJECT.md` -- milestone scope and requirements
- Existing codebase: `src/omnifocus_operator/models/`, `src/omnifocus_operator/repository.py`
