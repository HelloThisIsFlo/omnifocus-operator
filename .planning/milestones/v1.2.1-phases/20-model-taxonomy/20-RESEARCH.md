# Phase 20: Model Taxonomy - Research

**Researched:** 2026-03-18
**Domain:** Pydantic model refactoring, module reorganization, protocol consolidation
**Confidence:** HIGH

## Summary

Phase 20 is a pure internal refactoring: rename write-side models to follow CQRS/DDD naming, create new typed RepoPayload/RepoResult models, reorganize into a `contracts/` package, consolidate protocols into one file, and delete the old locations. No behavioral changes, no new tools.

The codebase is well-understood. All decisions are locked in CONTEXT.md with a complete rename map, field-by-field spec, and target module layout. The risk is mechanical: ~108 import sites across 4 test files, plus 8 source files need updating. The `model_rebuild()` forward reference pattern in `models/__init__.py` needs careful handling when write models move out.

**Primary recommendation:** Execute as a sequence of small, independently-testable waves: (1) create contracts/ package with new models, (2) update source imports + protocols, (3) update test imports, (4) delete old files. Run `uv run pytest tests/ -x` after every wave.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Naming convention**: Verb-first for write-side (`CreateTask___`, `EditTask___`), noun-only for read-side
- **Seven suffixes**: `___Command`, `___Result`, `___RepoPayload`, `___RepoResult`, `___Action`, `___Spec` (future), no suffix (read)
- **Complete rename map**: See CONTEXT.md `### Complete rename map` — every model has an exact target name and location
- **Typed payloads**: Per-operation models at every boundary (not shared WriteResult). `CreateTaskRepoPayload`, `EditTaskRepoPayload`, etc.
- **Module organization**: `contracts/` package at `omnifocus_operator/contracts/` with `protocols.py`, `base.py`, `common.py`, `use_cases/`
- **Protocol consolidation**: Service, Repository, Bridge protocols ALL in `contracts/protocols.py`
- **New Service protocol**: Added (currently doesn't exist)
- **Backward compatibility**: Zero. Clean break, update all call sites. No aliases. `models/write.py` deleted.
- **`___Spec` reserved**: No models get this suffix in Phase 20
- **Phase 21 asymmetry**: CreateTaskRepoPayload may still need minor key manipulation in repo; EditTaskRepoPayload is fully bridge-ready. Each payload honestly reflects how its operation works today.

### Claude's Discretion
- Import convenience: whether `contracts/__init__.py` re-exports all models or consumers import from submodules directly
- Whether `contracts/use_cases/__init__.py` re-exports or not
- Exact ordering of model definitions within each use_cases module
- Whether `_clean_unset_from_schema` stays in base.py or gets its own utility module
- How to handle `models/__init__.py` forward reference rebuilding (`model_rebuild`) after write models move out
- Test file import migration ordering and approach

### Deferred Ideas (OUT OF SCOPE)
- `___Spec` suffix usage (first user: RepetitionRuleSpec, future)
- Write pipeline unification (Phase 21)
- Service decomposition (Phase 22)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MODL-01 | Three-layer model taxonomy established: Request (user intent), Domain (entities), Payload (bridge format) | Complete rename map with seven suffixes. `contracts/` package structure with `use_cases/` submodules. Architecture patterns section shows exact module layout. |
| MODL-02 | Write-side request models renamed to follow consistent convention | Rename map: `TaskCreateSpec` -> `CreateTaskCommand`, `TaskEditSpec` -> `EditTaskCommand`, `WriteModel` -> `CommandModel`. All in `contracts/` package. |
| MODL-03 | Typed bridge payload models replace `dict[str, Any]` at service-repository boundary | New models: `CreateTaskRepoPayload`, `CreateTaskRepoResult`, `EditTaskRepoPayload`, `MoveToRepoPayload`, `EditTaskRepoResult`. Field specs in `.sandbox/phase-20-model-taxonomy-spec.md`. |
| MODL-04 | All write-side sub-models renamed to indicate their layer | `TagActionSpec` -> `TagAction`, `MoveToSpec` -> `MoveAction`, `ActionsSpec` -> `EditTaskActions`. All move to `contracts/common.py` or `contracts/use_cases/edit_task.py`. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pydantic | 2.12.5 | Model definitions, validation, serialization | Already used throughout project, `model_dump()` / `by_alias` / `exclude_none` / `exclude_unset` patterns established |
| pydantic-core | (bundled) | `CoreSchema`, `core_schema.is_instance_schema` for _Unset sentinel | Already in use for `_Unset.__get_pydantic_core_schema__` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| mypy | 1.19.1+ | Strict type checking with pydantic plugin | Run after every change — `uv run mypy src/` |
| ruff | 0.15.0+ | Linting + formatting | Pre-commit hook, checks import ordering |
| pytest | 9.0.2+ | Test suite (517 tests, 94% coverage) | After every wave of changes |

**No new dependencies.** This phase uses only what's already in the project.

## Architecture Patterns

### Target Package Structure
```
omnifocus_operator/
    contracts/                     # NEW: typed boundaries
        __init__.py                # Re-exports (Claude's discretion)
        protocols.py               # Service, Repository, Bridge protocols
        base.py                    # CommandModel, UNSET, _Unset, _clean_unset_from_schema
        common.py                  # TagAction, MoveAction
        use_cases/
            __init__.py
            create_task.py         # CreateTaskCommand, CreateTaskRepoPayload, CreateTaskRepoResult, CreateTaskResult
            edit_task.py           # EditTaskCommand, EditTaskActions, EditTaskRepoPayload, MoveToRepoPayload, EditTaskRepoResult, EditTaskResult
    models/                        # Read-side ONLY after migration
        __init__.py                # Re-exports read models only, model_rebuild for read models
        base.py                    # OmniFocusBaseModel (unchanged)
        common.py, task.py, ...    # Unchanged
    bridge/                        # protocol.py DELETED (moved to contracts)
    repository/                    # protocol.py DELETED (moved to contracts)
    service.py                     # Import paths change, method signatures change
    server.py                      # Import paths change
```

### Pattern 1: CommandModel Base Class
**What:** Renamed `WriteModel` -> `CommandModel`, lives in `contracts/base.py`
**When to use:** All command-layer models (`___Command`, `___Action`, `___RepoPayload`)
**Key behavior:** `extra="forbid"` rejects unknown fields. Inherits from `OmniFocusBaseModel` so it gets `alias_generator=to_camel` + `validate_by_name/alias`.

### Pattern 2: Per-Operation Use Case Modules
**What:** Each write operation gets its own module under `contracts/use_cases/`
**When to use:** `ls contracts/use_cases/` shows every operation at a glance
**Key benefit:** Each module is self-contained: Command, RepoPayload, RepoResult, Result

### Pattern 3: Protocol Consolidation
**What:** All three protocols (Service, Repository, Bridge) in one file: `contracts/protocols.py`
**When to use:** "Open ONE file, see the full typed flow" — human-readable system contract
**Key detail:** Service protocol is NEW (doesn't exist yet). Repository protocol signature changes from `add_task(spec, resolved_tag_ids)` to `add_task(payload: CreateTaskRepoPayload)`.

### Pattern 4: model_rebuild Forward References
**What:** `models/__init__.py` currently calls `model_rebuild(_types_namespace=_ns)` on all models including write models
**After migration:** Write model rebuild calls move to `contracts/__init__.py` (or each use_case module). Read models keep their rebuild in `models/__init__.py`.
**Critical detail:** The `_ns` dict must include all types referenced by the models being rebuilt. Write models reference `AwareDatetime` from TYPE_CHECKING — this must be in the namespace dict.

### Anti-Patterns to Avoid
- **Partial migration:** Never leave a state where some imports use old paths and others use new — breaks at runtime
- **Forgetting model_rebuild:** Models with `from __future__ import annotations` + TYPE_CHECKING imports MUST have `model_rebuild()` called somewhere at import time, or schema generation fails
- **Re-export from both old and new:** Don't add re-exports to `models/__init__.py` pointing at `contracts/` — clean break per decision

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| camelCase JSON keys | Manual key mapping | Pydantic `alias_generator=to_camel` + `by_alias=True` | Already works, proven pattern |
| UNSET sentinel | New sentinel or Optional tricks | Existing `_Unset` + `__get_pydantic_core_schema__` | Battle-tested, 517 tests rely on it |
| Schema cleanup | New schema generator | `_clean_unset_from_schema()` utility | Moves as-is to `contracts/base.py` |
| Import migration | Manual find-and-replace | IDE-assisted or systematic grep-and-update | 108 import sites in tests alone |

## Common Pitfalls

### Pitfall 1: model_rebuild Ordering
**What goes wrong:** Pydantic models with forward references (via `from __future__ import annotations`) fail at schema generation time if `model_rebuild()` hasn't been called with the right namespace.
**Why it happens:** Moving models to new modules breaks the existing `models/__init__.py` rebuild chain.
**How to avoid:** Ensure every module that defines models with forward refs calls `model_rebuild()` at import time, or create a central `contracts/__init__.py` that imports all contracts models and rebuilds them.
**Warning signs:** `PydanticUndefinedAnnotation` errors at test time.

### Pitfall 2: Circular Imports
**What goes wrong:** `contracts/protocols.py` imports domain models (Task, Project, etc.) for read signatures AND contracts models for write signatures. If contracts models import from models/ which imports from contracts/, circular import.
**Why it happens:** Protocol definitions reference types from both packages.
**How to avoid:** Use `TYPE_CHECKING` guards for all type annotations in protocols. The protocol file should have zero runtime imports from contracts models — only `if TYPE_CHECKING:` imports. Domain model imports from `models/` can also be TYPE_CHECKING-guarded.
**Warning signs:** `ImportError: cannot import name X from partially initialized module`.

### Pitfall 3: Server Runtime Imports
**What goes wrong:** `server.py` has a critical comment: "AllEntities MUST be a runtime import (not TYPE_CHECKING) because FastMCP introspects the return type annotation at registration time." Same applies to `TaskCreateResult`, `TaskEditResult`, `TaskCreateSpec`, `TaskEditSpec` (renamed versions).
**Why it happens:** FastMCP uses `get_type_hints()` which resolves string annotations against module namespace.
**How to avoid:** Keep runtime imports in `server.py` for all types used in tool function signatures. After rename: `CreateTaskCommand`, `CreateTaskResult`, `EditTaskCommand`, `EditTaskResult` must be runtime imports.
**Warning signs:** FastMCP tool registration fails silently or raises NameError.

### Pitfall 4: InMemoryRepository Edit Payload Shape
**What goes wrong:** `InMemoryRepository.edit_task()` currently takes `dict[str, Any]` and does camelCase key mapping internally. After Phase 20, it will take `EditTaskRepoPayload` — but the InMemoryRepository must still mutate its in-memory snapshot.
**Why it happens:** The InMemoryRepository has its own mutation logic (tag add/remove, lifecycle, moveTo) that operates on the dict keys.
**How to avoid:** InMemoryRepository.edit_task must accept `EditTaskRepoPayload`, call `model_dump()` to get the dict, then apply its existing mutation logic on the dict. Alternatively, access fields directly from the typed payload.
**Warning signs:** Test failures in service tests that use InMemoryRepository.

### Pitfall 5: Service edit_task Dict Building
**What goes wrong:** `service.py` `edit_task` currently builds a `dict[str, Any]` manually (lines 180-292). After Phase 20, it must build `EditTaskRepoPayload` instead.
**Why it happens:** The service currently does: build dict -> pass to repo. Now it must: build typed payload -> pass to repo.
**How to avoid:** Construct `EditTaskRepoPayload(id=..., name=..., ...)` with only the fields that changed. Use `model_dump(exclude_unset=True)` in the repository.
**Warning signs:** KeyError or missing fields in bridge calls.

### Pitfall 6: Test Import Volume
**What goes wrong:** 108 import statements across 4 test files reference `omnifocus_operator.models.write`. Missing even one causes ImportError.
**Why it happens:** Tests use inline imports (`from omnifocus_operator.models.write import TaskCreateSpec`) inside each test method.
**How to avoid:** Use systematic grep to find ALL imports, update in batches per file, run tests after each file.
**Warning signs:** Import errors at collection time.

## Code Examples

### contracts/base.py — CommandModel + UNSET (moved from models/write.py)
```python
# Source: models/write.py (current), moves to contracts/base.py
from omnifocus_operator.models.base import OmniFocusBaseModel

class CommandModel(OmniFocusBaseModel):
    """Base for all command-layer models. Rejects unknown fields."""
    model_config = ConfigDict(extra="forbid")

# _Unset, UNSET, _clean_unset_from_schema — moved verbatim
```

### contracts/protocols.py — All boundaries in one file
```python
# Source: docs/architecture.md + .sandbox/phase-20-model-taxonomy-spec.md
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from omnifocus_operator.contracts.use_cases.create_task import (
        CreateTaskCommand, CreateTaskRepoPayload, CreateTaskRepoResult, CreateTaskResult,
    )
    from omnifocus_operator.contracts.use_cases.edit_task import (
        EditTaskCommand, EditTaskRepoPayload, EditTaskRepoResult, EditTaskResult,
    )
    from omnifocus_operator.models import AllEntities, Project, Tag, Task

class Service(Protocol):
    async def get_all_data(self) -> AllEntities: ...
    async def add_task(self, command: CreateTaskCommand) -> CreateTaskResult: ...
    async def edit_task(self, command: EditTaskCommand) -> EditTaskResult: ...
    # ... reads

class Repository(Protocol):
    async def get_all(self) -> AllEntities: ...
    async def add_task(self, payload: CreateTaskRepoPayload) -> CreateTaskRepoResult: ...
    async def edit_task(self, payload: EditTaskRepoPayload) -> EditTaskRepoResult: ...
    # ... reads

class Bridge(Protocol):
    async def send_command(self, operation: str, params: dict[str, Any] | None = None) -> dict[str, Any]: ...
```

### Service add_task — Before vs After
```python
# BEFORE (current service.py):
async def add_task(self, spec: TaskCreateSpec) -> TaskCreateResult:
    ...
    return await self._repository.add_task(spec, resolved_tag_ids=resolved_tag_ids)

# AFTER (Phase 20):
async def add_task(self, command: CreateTaskCommand) -> CreateTaskResult:
    ...
    payload = CreateTaskRepoPayload(
        name=command.name,
        parent=command.parent,
        tag_ids=resolved_tag_ids,
        # dates serialized to ISO strings
        due_date=command.due_date.isoformat() if command.due_date else None,
        ...
    )
    repo_result = await self._repository.add_task(payload)
    return CreateTaskResult(success=True, id=repo_result.id, name=repo_result.name)
```

### Repository add_task — Before vs After
```python
# BEFORE (current hybrid.py):
async def add_task(self, spec: TaskCreateSpec, *, resolved_tag_ids=None) -> TaskCreateResult:
    payload = spec.model_dump(by_alias=True, exclude_none=True, mode="json")
    payload.pop("tags", None)
    if resolved_tag_ids: payload["tagIds"] = resolved_tag_ids
    result = await self._bridge.send_command("add_task", payload)
    return TaskCreateResult(success=True, id=result["id"], name=result["name"])

# AFTER (Phase 20):
async def add_task(self, payload: CreateTaskRepoPayload) -> CreateTaskRepoResult:
    raw = payload.model_dump(by_alias=True, exclude_none=True)
    # Note: tag_ids field still needs "tags" -> "tagIds" key handling (Phase 21 fixes this)
    result = await self._bridge.send_command("add_task", raw)
    return CreateTaskRepoResult(id=result["id"], name=result["name"])
```

## Affected Files — Complete Inventory

### Source files (8 files)
| File | Changes |
|------|---------|
| `models/write.py` | **DELETED** — all contents move to contracts/ |
| `models/__init__.py` | Remove write model imports/re-exports/model_rebuild calls. Keep read-side only. |
| `bridge/protocol.py` | **DELETED** — Bridge protocol moves to contracts/protocols.py |
| `repository/protocol.py` | **DELETED** — Repository protocol moves to contracts/protocols.py |
| `service.py` | Import paths change. `add_task` parameter: `TaskCreateSpec` -> `CreateTaskCommand`. `edit_task` builds `EditTaskRepoPayload` instead of `dict[str, Any]`. |
| `server.py` | Import paths change: `TaskCreateSpec` -> `CreateTaskCommand`, etc. |
| `repository/hybrid.py` | Method signatures change to typed payloads/results |
| `repository/bridge.py` | Method signatures change to typed payloads/results |
| `repository/in_memory.py` | Method signatures change to typed payloads/results |
| `repository/__init__.py` | Import `Repository` from `contracts.protocols` instead of `repository.protocol` |
| `bridge/__init__.py` | Import `Bridge` from `contracts.protocols` instead of `bridge.protocol` |

### New files (7 files)
| File | Contents |
|------|----------|
| `contracts/__init__.py` | Re-exports + model_rebuild for contracts models |
| `contracts/protocols.py` | Service, Repository, Bridge protocols |
| `contracts/base.py` | CommandModel, _Unset, UNSET, _clean_unset_from_schema |
| `contracts/common.py` | TagAction, MoveAction |
| `contracts/use_cases/__init__.py` | (possibly re-exports) |
| `contracts/use_cases/create_task.py` | CreateTaskCommand, CreateTaskRepoPayload, CreateTaskRepoResult, CreateTaskResult |
| `contracts/use_cases/edit_task.py` | EditTaskCommand, EditTaskActions, EditTaskRepoPayload, MoveToRepoPayload, EditTaskRepoResult, EditTaskResult |

### Test files (4 files, ~108 import lines)
| File | Import Count | Models Referenced |
|------|-------------|-------------------|
| `tests/test_service.py` | ~90 lines | TaskCreateSpec, TaskEditSpec, ActionsSpec, TagActionSpec, MoveToSpec, TaskCreateResult, _Unset |
| `tests/test_models.py` | ~11 lines | ActionsSpec, TaskEditSpec, MoveToSpec, TagActionSpec, TaskEditResult, _Unset |
| `tests/test_hybrid_repository.py` | ~2 lines | TaskCreateSpec, TaskCreateResult |
| `tests/test_repository.py` | ~5 lines | TaskCreateSpec, TaskCreateResult |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `TaskCreateSpec` (noun-first) | `CreateTaskCommand` (verb-first) | Phase 20 | All write model names change |
| `dict[str, Any]` at repo boundary | Typed `___RepoPayload` / `___RepoResult` | Phase 20 | Repository signatures become typed |
| Protocols scattered (bridge/, repository/) | All protocols in `contracts/protocols.py` | Phase 20 | Single file for all boundaries |
| No service protocol | `Service` protocol in contracts | Phase 20 | Formal typed contract |

## Open Questions

1. **`contracts/__init__.py` re-export strategy**
   - What we know: Consumer patterns vary — server.py uses `from omnifocus_operator.models import ...`, tests use inline `from omnifocus_operator.models.write import ...`
   - What's unclear: Should `contracts/__init__.py` re-export everything for convenience, or should consumers import from submodules?
   - Recommendation: Re-export the most commonly used symbols (commands, results, UNSET) from `contracts/__init__.py`. Consumers of specific models import from submodules. This matches the existing `models/__init__.py` pattern.

2. **model_rebuild location for contracts models**
   - What we know: Write models with `from __future__ import annotations` need `model_rebuild()` with `AwareDatetime` in the namespace
   - What's unclear: Whether to rebuild in `contracts/__init__.py` (centralized) or in each use_case module (distributed)
   - Recommendation: Centralized in `contracts/__init__.py`, matching the `models/__init__.py` pattern. Import all contracts models, build namespace dict, call model_rebuild on each.

3. **CreateTaskRepoPayload tag_ids field aliasing**
   - What we know: The bridge expects `tagIds` (camelCase). Current code does `payload.pop("tags")` then `payload["tagIds"] = resolved_tag_ids` in the repo.
   - What's unclear: With `alias_generator=to_camel`, the field `tag_ids` would alias to `tagIds` automatically via `model_dump(by_alias=True)`. Does this "just work" in Phase 20, or does the repo still need manual key manipulation?
   - Recommendation: Since `CommandModel` inherits `alias_generator=to_camel` from `OmniFocusBaseModel`, `tag_ids` will alias to `tagIds`. The repo can use `model_dump(by_alias=True, exclude_none=True)` with no key manipulation. Verify this works — it may make Phase 21's "convergence" largely free for add_task. If not, add a note to the plan.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2+ with pytest-asyncio 1.3.0+ |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/ -x -q --no-header --tb=short` |
| Full suite command | `uv run pytest tests/ --timeout=30` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MODL-01 | contracts/ package importable, three layers distinguishable | smoke | `uv run python -c "from omnifocus_operator.contracts.use_cases.create_task import CreateTaskCommand, CreateTaskRepoPayload, CreateTaskResult"` | No — Wave 0 |
| MODL-02 | Write-side request models renamed | regression | `uv run pytest tests/ -x -q --no-header --tb=short` (all 517 tests pass with new names) | Yes — existing tests |
| MODL-03 | Typed payloads at repo boundary | unit + regression | `uv run pytest tests/test_service.py tests/test_repository.py tests/test_hybrid_repository.py -x` | Yes — existing tests, signatures change |
| MODL-04 | Sub-models renamed (TagAction, MoveAction, EditTaskActions) | regression | `uv run pytest tests/test_models.py tests/test_service.py -x` | Yes — existing tests |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q --no-header --tb=short`
- **Per wave merge:** `uv run pytest tests/ --timeout=30` + `uv run mypy src/`
- **Phase gate:** Full suite green + mypy clean before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] Import smoke test verifying `contracts/` package is importable with correct model names
- [ ] Verification that `models/write.py` is deleted and `from omnifocus_operator.models.write import ...` raises ImportError
- [ ] Verification that `bridge/protocol.py` and `repository/protocol.py` are deleted

## Sources

### Primary (HIGH confidence)
- **Project source code:** Direct reading of all affected files (`models/write.py`, `models/__init__.py`, `bridge/protocol.py`, `repository/protocol.py`, `service.py`, `server.py`, repository implementations)
- **CONTEXT.md:** Complete rename map, module layout, field specs — all locked decisions
- **`.sandbox/phase-20-model-taxonomy-spec.md`:** Full before/after field-level specification
- **`docs/architecture.md`:** Authoritative naming convention, protocol signatures, package structure
- **Pydantic 2.12.5:** Verified `model_rebuild` API signature, `ConfigDict`, `alias_generator` behavior

### Secondary (MEDIUM confidence)
- **`.sandbox/phase-21-payload-convergence.md`:** Phase 21 target state (informs what NOT to do in Phase 20)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies, all patterns already established in codebase
- Architecture: HIGH — complete rename map and module layout locked in CONTEXT.md + spec
- Pitfalls: HIGH — identified from direct source code analysis and Pydantic v2 behavior
- Test impact: HIGH — exact import counts and affected files enumerated via grep

**Research date:** 2026-03-18
**Valid until:** 2026-04-18 (stable — internal refactoring, no external dependencies changing)
