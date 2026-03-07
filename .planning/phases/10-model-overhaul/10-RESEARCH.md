# Phase 10: Model Overhaul - Research

**Researched:** 2026-03-07
**Domain:** Pydantic model migration, enum refactoring, bridge adapter pattern
**Confidence:** HIGH

## Summary

Phase 10 replaces the single-winner status enums (`TaskStatus`, `ProjectStatus`) with a two-axis model (`Urgency` + `Availability`) and removes deprecated fields from all entity models. The codebase is well-structured for incremental migration: clear model hierarchy, centralized test factories in `conftest.py`, and a single data flow path (bridge -> models -> repository -> service -> server).

The main complexity is the blast radius: 182 pytest tests + 26 Vitest tests, with 67 occurrences of affected fields across 5 Python test files and 55 occurrences across 10 source files. The centralized factory functions (`make_task_dict`, `make_project_dict`, etc.) are the key leverage point -- updating them propagates changes to most tests automatically.

**Primary recommendation:** Migrate incrementally in this order: (1) add new enums, (2) add adapter layer, (3) update models to use new fields, (4) update factories/tests, (5) clean up bridge.js dead fields, (6) update Vitest tests, (7) remove old enums. Tests green at every commit.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- ALL enums switch to snake_case values: `"overdue"`, `"due_soon"`, `"available"`, `"on_hold"`, `"dropped"`, etc.
- JSON field names stay camelCase (MCP/JSON standard via Pydantic `to_camel` alias generator)
- Clean break, zero backward compatibility code -- no deprecation warnings, no dual fields
- Stay v1.1 (not v2.0)
- Bridge stays dumb: no new computation in bridge.js
- bridge.js keeps outputting old-format status enums; Python adapter maps old -> new
- InMemoryBridge uses new-shape fixtures directly (no adapter needed)
- Simulator data stays in sync with bridge.js output format
- Both SimulatorBridge and RealBridge go through the same Python adapter
- Remove ALL fields per research list -- no exceptions
- Incremental migration -- tests green at every commit
- UAT script in `uat/` folder, creates own test hierarchy, cleans up after

### Claude's Discretion
- Incremental migration granularity (one model at a time, one change type at a time, etc.)
- Exact adapter implementation pattern
- Loading skeleton for test migration ordering
- Vitest test update approach

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MODEL-01 | Task and Project expose `urgency` field (overdue/due_soon/none) | New `Urgency` StrEnum + adapter mapping from TaskStatus |
| MODEL-02 | Task and Project expose `availability` field (available/blocked/completed/dropped) | New `Availability` StrEnum + adapter mapping from TaskStatus/ProjectStatus |
| MODEL-03 | `TaskStatus` and `ProjectStatus` enums removed, replaced by shared `Urgency` and `Availability` | Delete enums from `enums.py`, remove from `__init__.py` exports and `_ns` dict |
| MODEL-04 | Fields `active`, `effective_active`, `completed` (bool), `sequential`, `completed_by_children`, `should_use_floating_time_zone` removed | Remove from `OmniFocusEntity` and `ActionableEntity` in `base.py` |
| MODEL-05 | `contains_singleton_actions` removed from Project, `allows_next_action` removed from Tag | Remove from `project.py` and `tag.py` |
| MODEL-06 | All existing tests and fixtures updated to reflect new model shape | Update conftest factories, test assertions, simulator data, Vitest mocks |

</phase_requirements>

## Architecture Patterns

### Current Model Hierarchy (what we're changing)
```
OmniFocusBaseModel (ConfigDict: camelCase aliases)
  +-- OmniFocusEntity (id, name, url, added, modified, active*, effective_active*)
      +-- ActionableEntity (note, completed*, completed_by_children*, flagged, ..., sequential*, should_use_floating_time_zone*)
          +-- Task (status: TaskStatus*, in_inbox, project, parent)
          +-- Project (status: ProjectStatus*, task_status: TaskStatus*, contains_singleton_actions*, ...)
      +-- Tag (status: TagStatus, allows_next_action*, ...)
      +-- Folder (status: FolderStatus, ...)
```
Fields marked `*` are being removed or replaced.

### Target Model Hierarchy
```
OmniFocusBaseModel (ConfigDict: camelCase aliases) -- unchanged
  +-- OmniFocusEntity (id, name, url, added, modified) -- active/effective_active REMOVED
      +-- ActionableEntity (urgency: Urgency, availability: Availability, note, flagged, ..., dates, tags)
          +-- Task (in_inbox, project, parent) -- status REMOVED
          +-- Project (last_review_date, ..., folder) -- status, task_status, contains_singleton_actions REMOVED
      +-- Tag (status: TagStatus, children_are_mutually_exclusive, parent) -- allows_next_action REMOVED
      +-- Folder (status: FolderStatus, parent) -- active/effective_active REMOVED
```

### Bridge Adapter Pattern

The bridge outputs old-format data. A Python adapter transforms it before Pydantic parsing:

```python
def adapt_bridge_task(raw: dict) -> dict:
    """Map old bridge task dict -> new model shape."""
    # Extract urgency from TaskStatus
    old_status = raw.pop("status")
    urgency, availability = _map_task_status(old_status, raw.get("completed", False), raw.get("effectiveActive", True))

    # Remove dead fields
    for key in ("active", "effectiveActive", "completed", "completedByChildren",
                "sequential", "shouldUseFloatingTimeZone"):
        raw.pop(key, None)

    raw["urgency"] = urgency
    raw["availability"] = availability
    return raw
```

**Where the adapter lives:** New module `bridge/adapter.py` or inline in repository's `_refresh` method. The adapter runs between `bridge.send_command()` response and `DatabaseSnapshot.model_validate()`.

**Key constraint:** InMemoryBridge returns new-shape data directly (tests construct fixtures with `urgency`/`availability`). Only RealBridge/SimulatorBridge need the adapter.

### Adapter Placement Options

**Option A (recommended): Repository-level adapter**
- `OmniFocusRepository._refresh()` calls `adapt_snapshot(raw)` before `model_validate()`
- Adapter only runs when bridge type is RealBridge/SimulatorBridge
- InMemoryBridge data is already in new shape
- Clean separation: bridge knows nothing about model shape

**Option B: Bridge subclass adapter**
- Override `send_command` in RealBridge to adapt response
- Less clean -- mixes transport with data transformation

### Mapping Tables (from RESULTS_pydantic-model.md)

**TaskStatus -> Urgency + Availability:**

| Old TaskStatus | Urgency | Availability |
|---|---|---|
| Available | `none` | `available` |
| Next | `none` | `available` |
| Blocked | `none` | `blocked` |
| DueSoon | `due_soon` | `available` (fallback -- can't determine blocked from bridge) |
| Overdue | `overdue` | `available` (fallback -- can't determine blocked from bridge) |
| Completed | `none` | `completed` |
| Dropped | `none` | `dropped` |

**ProjectStatus -> Availability:**

| Old ProjectStatus | Availability |
|---|---|
| Active | `available` |
| OnHold | `blocked` |
| Done | `completed` |
| Dropped | `dropped` |

**Note on DueSoon/Overdue:** For bridge path (fallback mode), urgency is fully derivable but availability for DueSoon/Overdue tasks defaults to `available` -- the `blocked` distinction requires SQLite (Phase 12). This is documented and expected.

### Enum Value Format Change

All enums move to snake_case. This affects TagStatus, FolderStatus, ScheduleType, AnchorDateKey too:

| Enum | Old Values | New Values |
|------|-----------|------------|
| TagStatus | `Active`, `OnHold`, `Dropped` | `active`, `on_hold`, `dropped` |
| FolderStatus | `Active`, `Dropped` | `active`, `dropped` |
| ScheduleType | `Regularly`, `FromCompletion`, `None` | `regularly`, `from_completion`, `none` |
| AnchorDateKey | `DueDate`, `DeferDate`, `PlannedDate` | `due_date`, `defer_date`, `planned_date` |

**Impact:** The adapter must also map old bridge enum strings to new snake_case values.

### model_rebuild Namespace Updates

`models/__init__.py` maintains a `_ns` dict and calls `model_rebuild()` on each model. Changes needed:
- Remove `TaskStatus`, `ProjectStatus` from `_ns`
- Add `Urgency`, `Availability` to `_ns`
- Remove from `__all__` exports
- Update `model_rebuild()` calls (same models, different namespace)

### Field Count Changes

| Model | Current Fields | New Fields | Delta |
|-------|---------------|------------|-------|
| Task | 32 | 25 | -7 (removed: active, effectiveActive, status, completed, completedByChildren, sequential, shouldUseFloatingTimeZone; added: urgency, availability) |
| Project | 36 | 28 | -8 (same removals + status, taskStatus, containsSingletonActions; added: urgency, availability) |
| Tag | 11 | 8 | -3 (removed: active, effectiveActive, allowsNextAction) |
| Folder | 9 | 7 | -2 (removed: active, effectiveActive) |

Tests assert exact field counts -- these assertions must be updated.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Status mapping logic | Complex if/elif chains | Simple dict lookup tables | Mapping is static; dict is clearer and faster |
| Enum validation | Custom validation code | Pydantic StrEnum + `model_validate` | Pydantic handles validation and error messages |
| camelCase serialization | Manual field renaming | `ConfigDict(alias_generator=to_camel)` | Already in place, just works |

## Common Pitfalls

### Pitfall 1: Big-Bang Migration
**What goes wrong:** Changing models + tests + bridge.js in one commit breaks everything; hard to debug
**Why it happens:** Temptation to "just do it all at once"
**How to avoid:** Strict incremental approach -- each commit touches one concern. Add new enums first (no breakage). Add adapter (no breakage). Update models one at a time.
**Warning signs:** More than ~3 files changed in a single commit during the model transition

### Pitfall 2: Factory Functions Not Updated First
**What goes wrong:** Tests fail en masse because `make_task_dict()` still returns old-shape data
**Why it happens:** Updating model code without updating the factory that feeds test data
**How to avoid:** Update `conftest.py` factories IN THE SAME commit as the corresponding model change. The factories are the single source of test data shape.
**Warning signs:** Dozens of test failures instead of a handful

### Pitfall 3: Forgetting model_rebuild Namespace
**What goes wrong:** `PydanticUndefinedAnnotation` at import time
**Why it happens:** TYPE_CHECKING imports + forward references require explicit namespace in `model_rebuild()`
**How to avoid:** When adding Urgency/Availability or removing TaskStatus/ProjectStatus, update `_ns` dict in `models/__init__.py` in the same commit
**Warning signs:** Import errors mentioning unresolved forward references

### Pitfall 4: Adapter Not Mapping Existing Enum Values
**What goes wrong:** TagStatus "Active" still arrives from bridge but new enum expects "active"
**Why it happens:** Forgetting that ALL enums change to snake_case, not just the new ones
**How to avoid:** The adapter must map ALL enum string values from bridge format to snake_case
**Warning signs:** `ValidationError` on TagStatus or FolderStatus fields

### Pitfall 5: Simulator Data / InMemoryBridge Shape Mismatch
**What goes wrong:** Simulator tests pass but InMemoryBridge tests fail (or vice versa)
**Why it happens:** Simulator data (`data.py`) uses bridge-format (old shape) while InMemoryBridge test fixtures use new shape
**How to avoid:** Simulator data stays in bridge-format (adapter transforms it). InMemoryBridge fixtures use new-shape directly. These are two different data flows.
**Warning signs:** Tests passing for one bridge type but failing for another

### Pitfall 6: Vitest Mock Data Out of Sync with bridge.js
**What goes wrong:** Vitest tests pass but they're testing fields that bridge.js no longer outputs
**Why it happens:** Removing fields from bridge.js `handleSnapshot()` but not updating Vitest mock globals
**How to avoid:** Update Vitest mocks and assertions in the same commit as bridge.js changes
**Warning signs:** Vitest tests checking for `active` or `effectiveActive` on entities after those fields are removed from handleSnapshot

## Code Examples

### New Enums (to add to enums.py)

```python
class Urgency(StrEnum):
    """Time pressure axis -- is this pressing?"""
    OVERDUE = "overdue"
    DUE_SOON = "due_soon"
    NONE = "none"

class Availability(StrEnum):
    """Work readiness axis -- can this be worked on?"""
    AVAILABLE = "available"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    DROPPED = "dropped"
```

### Updated TagStatus (snake_case values)

```python
class TagStatus(StrEnum):
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    DROPPED = "dropped"
```

### Adapter Function Pattern

```python
_TASK_STATUS_MAP: dict[str, tuple[str, str]] = {
    "Available": ("none", "available"),
    "Next": ("none", "available"),
    "Blocked": ("none", "blocked"),
    "DueSoon": ("due_soon", "available"),
    "Overdue": ("overdue", "available"),
    "Completed": ("none", "completed"),
    "Dropped": ("none", "dropped"),
}

_PROJECT_STATUS_MAP: dict[str, str] = {
    "Active": "available",
    "OnHold": "blocked",
    "Done": "completed",
    "Dropped": "dropped",
}

_TAG_STATUS_MAP: dict[str, str] = {
    "Active": "active",
    "OnHold": "on_hold",
    "Dropped": "dropped",
}

_FOLDER_STATUS_MAP: dict[str, str] = {
    "Active": "active",
    "Dropped": "dropped",
}

def adapt_snapshot(raw: dict[str, Any]) -> dict[str, Any]:
    """Transform bridge-format snapshot to new model shape."""
    for task in raw.get("tasks", []):
        _adapt_task(task)
    for project in raw.get("projects", []):
        _adapt_project(project)
    for tag in raw.get("tags", []):
        _adapt_tag(tag)
    for folder in raw.get("folders", []):
        _adapt_folder(folder)
    return raw
```

### Updated Factory (conftest.py pattern)

```python
def make_task_dict(**overrides: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "id": "task-001",
        "name": "Test Task",
        "url": "omnifocus:///task/task-001",
        "note": "",
        "added": "2024-01-15T10:30:00.000Z",
        "modified": "2024-01-15T10:30:00.000Z",
        "urgency": "none",
        "availability": "available",
        # ... (no active, effectiveActive, completed, sequential, etc.)
        "flagged": False,
        "effectiveFlagged": False,
        "hasChildren": False,
        "inInbox": True,
        # ... dates, tags, relationships
    }
    return {**defaults, **overrides}
```

## Incremental Migration Strategy

Recommended commit ordering (each commit keeps all tests green):

### Wave 1: Foundation (no test breakage)
1. **Add new enums** -- `Urgency`, `Availability` to `enums.py`. No model uses them yet. Zero breakage.
2. **Add adapter module** -- `bridge/adapter.py` with mapping functions. Not wired yet. Zero breakage.

### Wave 2: Model Migration (coordinated model + factory + test changes)
3. **Update OmniFocusEntity** -- remove `active`, `effective_active`. Update `make_tag_dict`, `make_folder_dict` factories. Update Tag/Folder model tests. Update simulator data for tags/folders. Wire adapter for tag/folder status mapping.
4. **Update ActionableEntity** -- remove `completed`, `completed_by_children`, `sequential`, `should_use_floating_time_zone`. Update factories. Update test assertions.
5. **Update Task model** -- replace `status: TaskStatus` with `urgency: Urgency` + `availability: Availability`. Update factory. Update task tests.
6. **Update Project model** -- replace `status: ProjectStatus` + `task_status: TaskStatus` + `contains_singleton_actions`. Update factory. Update project tests.
7. **Update Tag model** -- remove `allows_next_action`. Update factory. Update tag tests.

### Wave 3: Wiring + Cleanup
8. **Wire adapter into repository** -- `OmniFocusRepository._refresh()` calls `adapt_snapshot()` before `model_validate()`. SimulatorBridge integration tests verify adapter path.
9. **Update models/__init__.py** -- remove `TaskStatus`, `ProjectStatus` from exports and `_ns`. Add `Urgency`, `Availability`. Delete old enum classes.
10. **Clean up bridge.js** -- remove dead field emissions (`active`, `effectiveActive`, `completed`, `completedByChildren`, `sequential`, `shouldUseFloatingTimeZone`, `containsSingletonActions`, `allowsNextAction`). Keep `status` and `taskStatus` (adapter consumes them).
11. **Update Vitest tests** -- update mock globals, remove assertions for deleted fields, update field counts.
12. **Update simulator data** -- remove dead fields from `SIMULATOR_SNAPSHOT` in `data.py`.

### Wave 4: UAT + Enum Cleanup
13. **Update remaining enum values** -- `TagStatus`, `FolderStatus`, `ScheduleType`, `AnchorDateKey` to snake_case. Adapter maps old bridge strings.
14. **Create UAT script** -- `uat/test_model_overhaul.py` that validates through full pipeline.

**Alternative granularity:** Steps 3-7 could be combined into fewer commits if the implementer is confident, but never into a single commit. The key invariant is: tests pass after every commit.

## Scope Audit

### Files That Must Change

**Source (10 files):**
- `models/enums.py` -- add Urgency, Availability; update TagStatus, FolderStatus, ScheduleType, AnchorDateKey values; delete TaskStatus, ProjectStatus
- `models/base.py` -- remove fields from OmniFocusEntity and ActionableEntity
- `models/task.py` -- replace status with urgency + availability
- `models/project.py` -- replace status, task_status, contains_singleton_actions with urgency + availability
- `models/tag.py` -- remove allows_next_action
- `models/folder.py` -- no field changes (active/effective_active removed from parent)
- `models/__init__.py` -- update exports, _ns dict, model_rebuild calls
- `bridge/adapter.py` -- NEW: mapping functions
- `repository.py` -- wire adapter call in _refresh
- `simulator/data.py` -- remove dead fields from fixture data

**Bridge (1 file):**
- `bridge/bridge.js` -- remove dead field emissions from handleSnapshot

**Tests (6 files):**
- `tests/conftest.py` -- update all factory functions
- `tests/test_models.py` -- update all model tests (53 occurrences)
- `tests/test_server.py` -- update inline fixture data (5 occurrences)
- `tests/test_ipc_engine.py` -- minimal (2 occurrences, likely just imports)
- `tests/test_simulator_integration.py` -- minimal (1 occurrence, unrelated "sequential")
- `bridge/tests/bridge.test.js` -- update Vitest mocks and assertions

**UAT (1 new file):**
- `uat/test_model_overhaul.py` -- NEW: UAT validation script

### Files That Do NOT Change
- `bridge/real.py` -- transport only, no model knowledge
- `bridge/simulator.py` -- inherits from RealBridge, no model knowledge
- `bridge/in_memory.py` -- returns raw dict, no model knowledge
- `bridge/protocol.py` -- protocol definition, no model types
- `bridge/factory.py` -- bridge creation, minimal enum usage (factory type string, not model enums)
- `service.py` -- passes through, no model field access
- `server.py` -- uses DatabaseSnapshot type but doesn't access fields (except inline test fixture in test_server.py)
- `models/common.py` -- TagRef, RepetitionRule, ReviewInterval unchanged
- `models/perspective.py` -- not an OmniFocusEntity descendant affected
- `models/snapshot.py` -- aggregator, field types change but code doesn't

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + vitest |
| Config file | `pyproject.toml` (pytest section) + `vitest.config.js` |
| Quick run command | `uv run pytest tests/test_models.py -x` |
| Full suite command | `uv run pytest && cd bridge && npx vitest run` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MODEL-01 | Task/Project expose urgency field | unit | `uv run pytest tests/test_models.py::TestTaskModel -x` | Yes (needs update) |
| MODEL-02 | Task/Project expose availability field | unit | `uv run pytest tests/test_models.py::TestTaskModel -x` | Yes (needs update) |
| MODEL-03 | Old enums removed, new enums used | unit | `uv run pytest tests/test_models.py -x` | Yes (needs update) |
| MODEL-04 | Deprecated fields removed from entities | unit | `uv run pytest tests/test_models.py -x` | Yes (needs update) |
| MODEL-05 | contains_singleton_actions + allows_next_action removed | unit | `uv run pytest tests/test_models.py::TestTagModel tests/test_models.py::TestProjectModel -x` | Yes (needs update) |
| MODEL-06 | All tests pass with new shape | integration | `uv run pytest && cd bridge && npx vitest run` | Yes (needs update) |

### Sampling Rate
- **Per task commit:** `uv run pytest -x` (quick fail on first error)
- **Per wave merge:** `uv run pytest && cd bridge && npx vitest run` (full suite)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `bridge/adapter.py` -- new module for bridge-to-model mapping
- [ ] `uat/test_model_overhaul.py` -- new UAT script

## Sources

### Primary (HIGH confidence)
- Codebase inspection: all source files, test files, bridge.js read directly
- `.research/deep-dives/direct-database-access/RESULTS_pydantic-model.md` -- authoritative model spec
- `10-CONTEXT.md` -- locked user decisions

### Secondary (MEDIUM confidence)
- Pydantic v2 StrEnum + model_rebuild behavior -- verified against existing working code in `models/__init__.py`

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all stdlib + Pydantic patterns already in use
- Architecture: HIGH -- adapter pattern is simple and well-understood; data flow is linear
- Pitfalls: HIGH -- derived from direct codebase analysis, not speculation
- Migration strategy: MEDIUM -- ordering is sound but exact granularity may need adjustment during implementation

**Research date:** 2026-03-07
**Valid until:** 2026-04-07 (stable domain, no external dependencies changing)
