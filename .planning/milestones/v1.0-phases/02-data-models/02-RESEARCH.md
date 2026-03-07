# Phase 2: Data Models - Research

**Researched:** 2026-03-01
**Domain:** Pydantic v2 data modeling with camelCase alias serialization
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- All date fields typed as `datetime | None` (not raw strings); timezone-aware via Pydantic's `AwareDatetime`; `shouldUseFloatingTimeZone` stored as plain boolean; serialization: ISO 8601 strings (Pydantic default)
- Use Python `StrEnum` for status values; two separate enums: `TaskStatus` (Available, Blocked, Completed, Dropped, DueSoon, Next, Overdue) and `EntityStatus` (Active, Done, Dropped)
- Task `status` field is required (not nullable); Project has both `status` (EntityStatus) and `task_status` (TaskStatus); Tag/Folder `status` is `EntityStatus | None`
- `exclude_none=True` applied at serialization time (caller decides), not baked into model config; empty lists stay visible
- Inheritance hierarchy: `OmniFocusBaseModel` -> `OmniFocusEntity` (id, name) -> `ActionableEntity` (shared dates, flags, status for Task/Project)
- Tag and Folder extend `OmniFocusEntity` directly; `RepetitionRule` and `ReviewInterval` are standalone models; Perspective is standalone (id, name, builtin)

### Claude's Discretion
- Unknown enum value handling strategy (fail-fast validation error vs. fallback)
- Model file layout (one file per entity vs. consolidated)
- Exact field ordering within models
- Whether to add `py.typed` marker for type stub support
- Test fixture design (factories, builders, raw dicts)

### Deferred Ideas (OUT OF SCOPE)
- Bridge script simplification: replace `ts()` switch with `.name` property for task status -- Phase 8 (RealBridge)
- Empty list exclusion from serialization -- revisit if token density becomes a real concern
- TaskPaper serialization format -- Milestone 5+ (alternative output format for token reduction)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MODL-01 | Task model includes all fields from bridge script dump with snake_case names and camelCase aliases | Verified: all 32 bridge task fields round-trip through `snake_case -> to_camel` perfectly. `AwareDatetime \| None` for dates, `TaskStatus` StrEnum for status. |
| MODL-02 | Project model includes all fields from bridge script dump | Verified: all 31 bridge project fields round-trip. Project has both `status: EntityStatus \| None` and `task_status: TaskStatus`. Nested `RepetitionRule` and `ReviewInterval`. |
| MODL-03 | Tag model includes all fields from bridge script dump | Verified: all 9 bridge tag fields round-trip. Uses `EntityStatus \| None` for status. |
| MODL-04 | Folder model includes all fields from bridge script dump | Verified: all 8 bridge folder fields round-trip. Uses `EntityStatus \| None` for status. |
| MODL-05 | Perspective model includes id, name, and builtin flag | Verified: 3 fields. `id: str \| None` (builtin perspectives have `null` id), `name: str`, `builtin: bool`. |
| MODL-06 | DatabaseSnapshot model aggregates all entity collections | Verified: `DatabaseSnapshot` with `tasks`, `projects`, `tags`, `folders`, `perspectives` lists parses and round-trips correctly. |
| MODL-07 | All models share a base config with camelCase alias generation and `populate_by_name` | Verified: `OmniFocusBaseModel` with `ConfigDict(alias_generator=to_camel, validate_by_name=True, validate_by_alias=True)` propagates to all subclasses. `validate_by_name` is the modern replacement for `populate_by_name` (added in Pydantic 2.11). |
</phase_requirements>

## Summary

This phase creates typed Pydantic v2 models for every OmniFocus entity. The bridge script (`operatorBridgeScript.js`) is the schema source of truth -- every field name and type has been extracted and verified. Research confirms that Pydantic 2.12.5 (bundled with `mcp>=1.26.0`) provides everything needed out of the box: `alias_generator=to_camel` for camelCase serialization, `validate_by_name=True` for snake_case construction in tests, `AwareDatetime` for timezone-enforced dates, and native `StrEnum` validation.

All 83 bridge fields across 7 entity types (Task, Project, Tag, Folder, Perspective, RepetitionRule, ReviewInterval) round-trip perfectly through `snake_case -> to_camel` transformation. JSON round-trip parsing and serialization has been verified: bridge camelCase JSON parses into Python models with snake_case attributes, and serializes back to identical camelCase JSON.

**Primary recommendation:** Use `OmniFocusBaseModel` with `ConfigDict(alias_generator=to_camel, validate_by_name=True, validate_by_alias=True)` as the shared base. Use `StrEnum` with fail-fast validation (Pydantic default -- unknown values raise `ValidationError`). Use `AwareDatetime | None` for all date fields.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.12.5 | Data validation and serialization | Already bundled via `mcp>=1.26.0` -- no additional dependency |
| pydantic.alias_generators.to_camel | 2.12.5 | snake_case -> camelCase alias generation | Built-in, zero config, verified to match all bridge field names |
| pydantic.AwareDatetime | 2.12.5 | Timezone-aware datetime validation | Rejects naive datetimes, enforces ISO 8601, handles `Z` suffix |
| enum.StrEnum | stdlib 3.12 | String-valued enumerations | Python 3.12 stdlib, first-class Pydantic support, serializes to string values |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.0.2+ | Test framework | Unit tests for model validation, serialization, round-trip |
| mypy + pydantic.mypy plugin | 1.19.1+ | Static type checking | Already configured in pyproject.toml with strict mode |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `validate_by_name=True` | `populate_by_name=True` | `populate_by_name` still works in 2.12 but is pending deprecation for v3; `validate_by_name` is the forward-compatible replacement |
| `AwareDatetime` | `datetime` | Plain `datetime` accepts naive datetimes silently; `AwareDatetime` enforces the invariant that bridge dates always have timezone info |
| `StrEnum` | `Literal["Available", ...]` | `StrEnum` gives named members, iteration, IDE completion; `Literal` is simpler but less ergonomic |

**Installation:**
```bash
# No additional installation needed -- pydantic already bundled via mcp dependency
uv sync
```

## Architecture Patterns

### Recommended Project Structure
```
src/omnifocus_operator/
    models/
        __init__.py        # Public API: re-exports all models and enums
        _base.py           # OmniFocusBaseModel, OmniFocusEntity, ActionableEntity
        _enums.py          # TaskStatus, EntityStatus
        _task.py           # Task model
        _project.py        # Project model
        _tag.py            # Tag model
        _folder.py         # Folder model
        _perspective.py    # Perspective model
        _common.py         # RepetitionRule, ReviewInterval
        _snapshot.py       # DatabaseSnapshot
```

### Pattern 1: Inheritance Hierarchy with Shared Config
**What:** Single `OmniFocusBaseModel` carries the `ConfigDict`; all models inherit it.
**When to use:** Always -- the base config must be consistent across all models.
**Example:**
```python
# Source: verified with Pydantic 2.12.5 (Context7 + local testing)
from pydantic import AwareDatetime, BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

class OmniFocusBaseModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
    )

class OmniFocusEntity(OmniFocusBaseModel):
    id: str
    name: str

class ActionableEntity(OmniFocusEntity):
    """Shared fields for Task and Project (dates, flags, status)."""
    flagged: bool
    effective_flagged: bool
    sequential: bool
    due_date: AwareDatetime | None = None
    defer_date: AwareDatetime | None = None
    # ... remaining shared date/flag fields
```

### Pattern 2: StrEnum with Exact Bridge Values
**What:** Enum values match the exact strings the bridge script produces.
**When to use:** For `TaskStatus` and `EntityStatus` fields.
**Example:**
```python
# Source: verified against operatorBridgeScript.js ts() function and .status.name
from enum import StrEnum

class TaskStatus(StrEnum):
    AVAILABLE = "Available"
    BLOCKED = "Blocked"
    COMPLETED = "Completed"
    DROPPED = "Dropped"
    DUE_SOON = "DueSoon"
    NEXT = "Next"
    OVERDUE = "Overdue"

class EntityStatus(StrEnum):
    ACTIVE = "Active"
    DONE = "Done"
    DROPPED = "Dropped"
```

### Pattern 3: Standalone Nested Models
**What:** `RepetitionRule` and `ReviewInterval` are separate Pydantic models, not inner classes.
**When to use:** For nested objects in the bridge JSON.
**Example:**
```python
# Source: verified against operatorBridgeScript.js rr() and ri() functions
class RepetitionRule(OmniFocusBaseModel):
    rule_string: str        # serializes to "ruleString"
    schedule_type: str      # serializes to "scheduleType"

class ReviewInterval(OmniFocusBaseModel):
    steps: int
    unit: str
```

### Pattern 4: DatabaseSnapshot as Top-Level Aggregator
**What:** Single model holding all entity collections, matching the bridge `data` object shape.
**When to use:** As the return type for the `dump` operation.
**Example:**
```python
class DatabaseSnapshot(OmniFocusBaseModel):
    tasks: list[Task]
    projects: list[Project]
    tags: list[Tag]
    folders: list[Folder]
    perspectives: list[Perspective]
```

### Anti-Patterns to Avoid
- **Inventing fields not in the bridge script:** Models must match the dump exactly. Do not add computed fields, derived status, or convenience properties (those belong in the service layer in Phase 5).
- **Baking `exclude_none` into model config:** The caller decides serialization options at call time via `model_dump(exclude_none=True, by_alias=True)`. Model config should not include `serialize_by_alias=True` either -- keep serialization decisions explicit.
- **Using `use_enum_values=True`:** This converts enum fields to plain strings on the model instance, losing the `StrEnum` type. Without it, Pydantic stores the actual enum member, and `model_dump_json()` / `model_dump(mode="json")` correctly serialize to the string value. The enum type is preserved for pattern matching and IDE support.
- **Using `populate_by_name=True`:** This is the legacy name, pending deprecation in Pydantic v3. Use `validate_by_name=True` + `validate_by_alias=True` instead (available since Pydantic 2.11).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| camelCase conversion | Custom `alias` on every field | `alias_generator=to_camel` on base ConfigDict | 83 fields -- manual aliases are error-prone and tedious |
| Date parsing/serialization | Custom validators for ISO 8601 | `AwareDatetime` built-in type | Handles ISO 8601 with `Z` suffix, timezone validation, round-trip serialization |
| Enum validation | `@field_validator` with manual checks | `StrEnum` field type | Pydantic validates enum membership automatically, error messages list valid values |
| JSON serialization | Custom `dict()` / `json()` methods | `model_dump(by_alias=True)` / `model_dump_json(by_alias=True)` | Built-in, handles nested models, dates, enums correctly |
| Field exclusion | Custom serializer logic | `model_dump(exclude_none=True)` | Built-in parameter, works recursively on nested models |

**Key insight:** Pydantic v2 handles every serialization requirement out of the box. The entire phase is about correctly declaring field types and the base config -- zero custom serialization code is needed.

## Common Pitfalls

### Pitfall 1: validate_by_name vs. populate_by_name
**What goes wrong:** Using `populate_by_name=True` works today but will trigger deprecation warnings in Pydantic v3.
**Why it happens:** The CONTEXT.md and success criteria reference `populate_by_name` because it was the established name. Pydantic 2.11+ introduced `validate_by_name` as the replacement.
**How to avoid:** Use `validate_by_name=True, validate_by_alias=True` in the base ConfigDict. This is functionally identical to `populate_by_name=True` but forward-compatible.
**Warning signs:** Deprecation warnings when upgrading Pydantic.

### Pitfall 2: model_dump() Returns Enum Instances, Not Strings
**What goes wrong:** `model_dump()` (default Python mode) returns `<TaskStatus.AVAILABLE: 'Available'>` enum objects, not plain strings.
**Why it happens:** Pydantic preserves Python types in `model_dump()` by default. Only `model_dump(mode="json")` or `model_dump_json()` converts to string values.
**How to avoid:** Always use `model_dump_json(by_alias=True)` for JSON output, or `model_dump(mode="json", by_alias=True)` for a dict with JSON-compatible types. Do NOT add `use_enum_values=True` to fix this -- it destroys enum type information.
**Warning signs:** Downstream code receiving enum objects when it expects strings.

### Pitfall 3: Forgetting by_alias=True
**What goes wrong:** `model_dump()` and `model_dump_json()` use snake_case field names by default, even when `alias_generator` is configured.
**Why it happens:** Pydantic defaults `by_alias=False` for backward compatibility.
**How to avoid:** Always pass `by_alias=True` when serializing for external consumers (bridge responses, MCP tool output). Internal Python code uses snake_case naturally.
**Warning signs:** JSON output with snake_case keys where camelCase is expected.

### Pitfall 4: AwareDatetime Rejecting Naive Datetimes
**What goes wrong:** `AwareDatetime` raises `ValidationError` with type `timezone_aware` if given a datetime without timezone info.
**Why it happens:** The bridge always outputs ISO 8601 with `Z` suffix, so this is correct behavior. But test fixtures using `datetime.now()` (naive) will fail.
**How to avoid:** Test fixtures must use `datetime.now(timezone.utc)` or ISO strings like `"2024-01-15T10:30:00Z"`.
**Warning signs:** `timezone_aware` validation errors in tests.

### Pitfall 5: Perspective id Can Be None
**What goes wrong:** Assuming `id` is always a non-null string across all entities.
**Why it happens:** The bridge script uses `p.identifier || null` for perspectives -- builtin perspectives have no identifier, returning `null`.
**How to avoid:** Perspective model defines `id: str | None` (unlike other entities which have `id: str`). Perspective should NOT inherit from `OmniFocusEntity` since it breaks the `id: str` contract.
**Warning signs:** Validation errors when parsing builtin perspectives from the bridge dump.

### Pitfall 6: Tags Field Contains Names, Not IDs
**What goes wrong:** Assuming `tags` is a list of tag IDs (primary keys).
**Why it happens:** Most reference fields (project, parent, folder) use primary keys. But the bridge maps tags to `g.name`, not `g.id.primaryKey`.
**How to avoid:** Task and Project models define `tags: list[str]` where strings are tag names, not IDs. Add a docstring/comment clarifying this.
**Warning signs:** Tag lookups by ID failing when the field contains names.

## Code Examples

Verified patterns from local testing against Pydantic 2.12.5:

### Complete Base Model Configuration
```python
# Source: verified locally with Pydantic 2.12.5
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

class OmniFocusBaseModel(BaseModel):
    """Base model for all OmniFocus entities.

    Configures camelCase alias generation for JSON serialization
    and allows construction using either snake_case (Python) or
    camelCase (bridge JSON) field names.
    """
    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
    )
```

### Bridge JSON Round-Trip
```python
# Source: verified locally -- full parse -> serialize -> re-parse cycle
import json

bridge_json = '{"id":"abc123","name":"Buy groceries","status":"Available","dueDate":"2024-01-15T10:30:00.000Z","tags":["errands"]}'

# Parse from camelCase bridge JSON
task = Task.model_validate_json(bridge_json)
assert task.id == "abc123"
assert task.due_date is not None
assert task.due_date.tzinfo is not None  # AwareDatetime enforces this

# Serialize back to camelCase JSON
output = task.model_dump_json(by_alias=True)
reparsed = Task.model_validate_json(output)
assert task.id == reparsed.id
assert task.due_date == reparsed.due_date
```

### Test Fixture Construction (snake_case, no alias juggling)
```python
# Source: verified locally -- validate_by_name allows snake_case construction
from datetime import datetime, timezone

task = Task(
    id="test-1",
    name="Test task",
    note="",
    added=datetime(2024, 1, 1, tzinfo=timezone.utc),
    modified=datetime(2024, 1, 1, tzinfo=timezone.utc),
    active=True,
    effective_active=True,
    status=TaskStatus.AVAILABLE,      # StrEnum member or string "Available"
    completed=False,
    completed_by_children=False,
    flagged=False,
    effective_flagged=False,
    sequential=False,
    estimated_minutes=None,
    has_children=False,
    in_inbox=True,
    should_use_floating_time_zone=False,
    repetition_rule=None,
    project=None,
    parent=None,
    assigned_container=None,
    tags=[],
)
```

### DatabaseSnapshot Parsing
```python
# Source: verified locally
bridge_response = {
    "success": True,
    "data": {
        "tasks": [...],
        "projects": [...],
        "tags": [...],
        "folders": [...],
        "perspectives": [...]
    }
}
# Note: DatabaseSnapshot matches the shape of bridge_response["data"], not the full response
snapshot = DatabaseSnapshot.model_validate(bridge_response["data"])
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `populate_by_name=True` | `validate_by_name=True, validate_by_alias=True` | Pydantic 2.11 (2025) | Forward-compatible; `populate_by_name` pending deprecation in v3 |
| `class Config:` inner class | `model_config = ConfigDict(...)` | Pydantic 2.0 (2023) | Already using v2 style -- no migration needed |
| `Field(alias="camelCase")` per field | `alias_generator=to_camel` on base | Pydantic 2.0 (2023) | Single config line replaces 83 manual aliases |
| `Optional[datetime]` | `datetime \| None` | Python 3.10+ / PEP 604 | Using Python 3.12 -- use the modern syntax |

**Deprecated/outdated:**
- `populate_by_name=True`: Still works in 2.12 but replaced by `validate_by_name=True` + `validate_by_alias=True` in 2.11+
- `class Config:` inner class: Replaced by `model_config = ConfigDict(...)` in Pydantic v2
- `schema_extra`: Replaced by `json_schema_extra` in Pydantic v2

## Discretion Recommendations

### Unknown Enum Value Handling: Use Fail-Fast (Pydantic Default)
**Recommendation:** Do not add any fallback handling. Pydantic's default behavior with `StrEnum` raises a `ValidationError` with a clear error message listing all valid values (e.g., "Input should be 'Available', 'Blocked', 'Completed', 'Dropped', 'DueSoon', 'Next' or 'Overdue'").
**Rationale:** An unknown status value means either (a) OmniFocus added a new status (rare, intentional API change) or (b) a bug in the bridge script. Both cases should surface loudly. A fallback would silently mask data integrity issues. Fail-fast is the safer choice for "executive function infrastructure that works at 7:30am."

### Model File Layout: Separate Files with Underscore Prefix
**Recommendation:** One file per entity type, underscore-prefixed (`_task.py`, `_project.py`, etc.) to signal internal modules. Public API in `__init__.py` re-exports everything.
**Rationale:** Separate files keep diffs clean (changing Task doesn't touch Project), enable targeted imports during development, and match the natural domain boundaries. The `_` prefix follows Python convention for internal modules while `__init__.py` provides the stable public API.

### Field Ordering: Group by Semantic Category
**Recommendation:** Order fields within models as: identity (id, name, note) -> lifecycle (added, modified, active, status) -> dates (due, defer, planned, drop, completion + effective variants) -> flags (flagged, sequential, completed) -> relationships (project, parent, tags) -> metadata (estimated_minutes, repetition_rule, etc.).
**Rationale:** Groups related fields for readability. Matches the general order in the bridge script.

### py.typed Marker: Already Present
**Observation:** `py.typed` already exists in `src/omnifocus_operator/`. No action needed for this phase.

### Test Fixture Design: Raw Dict Factories
**Recommendation:** Use factory functions returning `dict[str, Any]` that represent bridge JSON, plus convenience functions that return model instances. Raw dicts test the validation path; model instances test construction convenience.
**Rationale:** Factories are simpler than builder patterns for this domain. Raw dicts verify that the model correctly parses bridge JSON. Model-instance factories verify snake_case construction works (the `validate_by_name` requirement). Both are needed for comprehensive testing.

Example:
```python
def make_task_dict(**overrides: Any) -> dict[str, Any]:
    """Factory for bridge-format task JSON (camelCase keys)."""
    defaults = {
        "id": "task-1",
        "name": "Test Task",
        "note": "",
        "status": "Available",
        # ... all required fields with sensible defaults
    }
    return {**defaults, **overrides}

def make_task(**overrides: Any) -> Task:
    """Factory for Task model instances (snake_case keys)."""
    defaults = {
        "id": "task-1",
        "name": "Test Task",
        "note": "",
        "status": TaskStatus.AVAILABLE,
        # ... all required fields with sensible defaults
    }
    return Task(**{**defaults, **overrides})
```

## Open Questions

1. **Bridge response wrapper**
   - What we know: The bridge writes `{"success": true, "data": {...}}`. `DatabaseSnapshot` models the inner `data` object.
   - What's unclear: Should Phase 2 also model the `BridgeResponse` wrapper (`success: bool`, `data: DatabaseSnapshot | None`, `error: str | None`)? Or defer to Phase 3 (Bridge)?
   - Recommendation: Defer to Phase 3. Phase 2 scope is entity models only. The bridge response wrapper belongs with the bridge protocol.

2. **ActionableEntity shared field completeness**
   - What we know: Task and Project share many fields (dates, flags, etc.). The CONTEXT.md prescribes `ActionableEntity` as an intermediate class.
   - What's unclear: The exact boundary of which fields go on `ActionableEntity` vs. remain entity-specific. For example, `note` appears on both Task and Project but not on Tag/Folder -- does it go on `OmniFocusEntity` or `ActionableEntity`?
   - Recommendation: `note` goes on `ActionableEntity` since Tag and Folder don't have it. The planner should enumerate the exact field split when creating implementation tasks.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2+ with pytest-asyncio 1.3.0+ (auto mode) |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_models.py -x` |
| Full suite command | `uv run pytest --timeout=10` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MODL-01 | Task model parses all 32 bridge fields, snake_case + camelCase aliases | unit | `uv run pytest tests/test_models.py::test_task_from_bridge_json -x` | Wave 0 |
| MODL-02 | Project model parses all 31 bridge fields, nested RepetitionRule/ReviewInterval | unit | `uv run pytest tests/test_models.py::test_project_from_bridge_json -x` | Wave 0 |
| MODL-03 | Tag model parses all 9 bridge fields | unit | `uv run pytest tests/test_models.py::test_tag_from_bridge_json -x` | Wave 0 |
| MODL-04 | Folder model parses all 8 bridge fields | unit | `uv run pytest tests/test_models.py::test_folder_from_bridge_json -x` | Wave 0 |
| MODL-05 | Perspective model: id (nullable), name, builtin | unit | `uv run pytest tests/test_models.py::test_perspective_from_bridge_json -x` | Wave 0 |
| MODL-06 | DatabaseSnapshot aggregates all collections, round-trips | unit | `uv run pytest tests/test_models.py::test_database_snapshot_round_trip -x` | Wave 0 |
| MODL-07 | Base config: alias_generator=to_camel, validate_by_name, validate_by_alias | unit | `uv run pytest tests/test_models.py::test_base_config_aliases -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_models.py -x`
- **Per wave merge:** `uv run pytest --timeout=10`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_models.py` -- covers MODL-01 through MODL-07 (all model validation, serialization, round-trip)
- [ ] `tests/conftest.py` -- add fixture factories (`make_task_dict`, `make_project_dict`, etc.) for reuse across phases
- [ ] `src/omnifocus_operator/models/` -- entire models package (does not exist yet)

## Sources

### Primary (HIGH confidence)
- Context7 `/llmstxt/pydantic_dev_llms-full_txt` -- alias_generator, ConfigDict, validate_by_name, model_dump, AliasGenerator
- Context7 `/pydantic/pydantic` -- AwareDatetime validation, StrEnum handling, timezone_aware error
- Local verification with Pydantic 2.12.5 -- all 83 field names round-trip tested, model inheritance verified, JSON round-trip confirmed

### Secondary (MEDIUM confidence)
- [Pydantic v2.11 Release Announcement](https://pydantic.dev/articles/pydantic-v2-11-release) -- validate_by_name introduction, populate_by_name deprecation timeline
- [Pydantic Configuration API](https://docs.pydantic.dev/latest/api/config/) -- ConfigDict parameter reference, validate_by_name/validate_by_alias semantics

### Tertiary (LOW confidence)
- None -- all findings verified through Context7 or local testing

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- Pydantic 2.12.5 already installed, all features verified locally
- Architecture: HIGH -- inheritance pattern, alias_generator, round-trip all tested with working code
- Pitfalls: HIGH -- each pitfall discovered through actual testing (enum serialization, AwareDatetime, validate_by_name)

**Research date:** 2026-03-01
**Valid until:** 2026-04-01 (Pydantic v2 is stable; no breaking changes expected)
