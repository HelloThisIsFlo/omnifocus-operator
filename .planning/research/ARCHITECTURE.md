# Architecture Patterns: Service Decomposition & Write Pipeline Unification

**Domain:** Internal refactoring of existing MCP server (v1.2.1)
**Researched:** 2026-03-16
**Confidence:** HIGH -- based entirely on reading the actual codebase

## Current Architecture

```
MCP Server (server.py)
  |
  v
OperatorService (service.py)         <-- 637 lines, monolithic
  |
  v
Repository Protocol (repository/protocol.py)
  |
  +-- HybridRepository (SQLite read, Bridge write) -- production
  +-- BridgeRepository (Bridge read+write, caching) -- fallback
  +-- InMemoryRepository (in-memory snapshot) -- test-only
  |
  v
Bridge Protocol (bridge/protocol.py)
  |
  +-- RealBridge (file-based IPC to OmniJS) -- production
  +-- SimulatorBridge (IPC to Python simulator) -- integration test
  +-- InMemoryBridge (in-memory, call tracking) -- unit test
```

### Write Path Asymmetry (the core problem)

**add_task path:**
```
Service.add_task(spec: TaskCreateSpec)
  -> validates name
  -> resolves parent (project-first)
  -> resolves tags (name -> ID)
  -> repo.add_task(spec, resolved_tag_ids=...)  # typed spec + kwarg
```
Repository receives a typed `TaskCreateSpec`, does its own serialization to dict in `add_task`.

**edit_task path:**
```
Service.edit_task(spec: TaskEditSpec)
  -> verifies task exists
  -> processes lifecycle
  -> validates name
  -> BUILDS dict payload IN SERVICE (lines 167-282)  # <-- asymmetry
  -> computes tag diff
  -> resolves moveTo
  -> detects no-ops
  -> repo.edit_task(payload: dict[str, Any])  # untyped dict passthrough
```
Service builds the entire dict, repository is a dumb passthrough.

**Repository protocol reflects the asymmetry:**
```python
# Different signatures, different levels of abstraction
async def add_task(self, spec: TaskCreateSpec, *, resolved_tag_ids: list[str] | None) -> TaskCreateResult
async def edit_task(self, payload: dict[str, Any]) -> dict[str, Any]
```

**Payload building is duplicated across repo implementations:**
- `HybridRepository.add_task` builds payload from spec (lines 492-497)
- `BridgeRepository.add_task` builds payload from spec (lines 115-118) -- same logic

---

## Recommended Architecture

### Target State

```
MCP Server (server.py)
  |
  v
OperatorService (service/__init__.py)     <-- thin orchestrator, ~80 lines
  |  uses:
  |  +-- service/validation.py            <-- name, parent, tag resolution
  |  +-- service/domain.py                <-- lifecycle, no-op detection, tag diff, cycle check
  |  +-- service/conversion.py            <-- spec -> bridge payload dict building
  |
  v
Repository Protocol (repository/protocol.py)
  |  add_task(payload: dict) -> dict       <-- unified: both take dict, return dict
  |  edit_task(payload: dict) -> dict
  |
  +-- HybridRepository
  +-- BridgeRepository
  +-- InMemoryRepository (tests/ only)
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `server.py` | MCP tool registration, request deserialization, response formatting | `OperatorService` |
| `service/__init__.py` | Re-exports `OperatorService`, `ErrorOperatorService` | -- |
| `service/_orchestrator.py` | Orchestrates validation -> domain -> conversion -> repo. No logic of its own. | `validation`, `domain`, `conversion`, Repository |
| `service/validation.py` | Input validation: name checks, parent resolution, tag name-to-ID resolution | Repository (for lookups) |
| `service/domain.py` | Business logic: lifecycle state machine, tag diff, no-op detection, cycle detection | None (pure functions + task state) |
| `service/conversion.py` | Spec-to-payload: both `TaskCreateSpec` and `TaskEditSpec` produce `dict[str, Any]` | None (pure transformation) |
| Repository protocol | Unified write interface: both take `dict[str, Any]`, return `dict[str, Any]` | Bridge |
| Bridge protocol | IPC to OmniFocus: `send_command(operation, params)` | OmniFocus (via file IPC) |

### Data Flow: Unified Write Path

After unification, both add and edit follow the same shape:

```
1. MCP Server deserializes input -> TaskCreateSpec or TaskEditSpec
2. Service calls validation (name, parent, tags)
3. Service calls domain logic (lifecycle, no-op, tag diff -- edit only)
4. Service calls conversion (spec -> bridge payload dict)
5. Service calls repo.add_task(payload) or repo.edit_task(payload)
6. Repo delegates to bridge.send_command(operation, payload)
7. Repo waits for write-through (WAL mtime)
8. Service wraps result as TaskCreateResult or TaskEditResult
```

---

## New Components

### 1. `src/omnifocus_operator/service/validation.py`

**Extracted from:** `OperatorService._resolve_parent`, `._resolve_tags`, name validation check

```python
async def validate_task_name(name: str | None) -> None:
    """Raise ValueError if name is empty/blank. None = not provided (edit skip)."""

async def resolve_parent(parent_id: str, repo: Repository) -> str:
    """Resolve parent ID. Project-first, then task. Raises ValueError."""

async def resolve_tags(tag_names: list[str], repo: Repository) -> list[str]:
    """Resolve tag names to IDs (case-insensitive, ID fallback). Raises ValueError."""
```

**Why extract:** Used identically by both add and edit paths. Currently private methods that only use `self._repository`. Making them free functions with explicit `repo` parameter removes the class coupling.

### 2. `src/omnifocus_operator/service/domain.py`

**Extracted from:** `OperatorService._process_lifecycle`, `._compute_tag_diff`, `._check_cycle`, no-op detection (lines 309-380)

```python
def process_lifecycle(action: str, task: Task) -> tuple[bool, list[str]]:
    """Returns (should_call_bridge, warnings). Already stateless."""

async def compute_tag_diff(
    tag_actions: TagActionSpec, current_tags: list[TagRef], repo: Repository,
) -> tuple[list[str], list[str], list[str]]:
    """Returns (add_ids, remove_ids, warnings)."""

async def check_cycle(task_id: str, container_id: str, repo: Repository) -> None:
    """Raises ValueError if move creates circular reference."""

def detect_noop(payload: dict[str, Any], task: Task) -> tuple[bool, list[str]]:
    """Returns (is_noop, warnings). Compares payload against current state."""
```

**Why extract:** Domain logic independent of service orchestration. `_process_lifecycle` is already a pure function. `_compute_tag_diff` only needs repo for tag resolution. No-op detection is a pure comparison.

### 3. `src/omnifocus_operator/service/conversion.py`

**Extracted from:** payload building in `HybridRepository.add_task` (lines 492-497), `BridgeRepository.add_task` (lines 115-118), and `OperatorService.edit_task` (lines 196-282)

```python
def build_add_payload(
    spec: TaskCreateSpec, resolved_tag_ids: list[str] | None,
) -> dict[str, Any]:
    """Convert TaskCreateSpec to bridge-ready camelCase dict."""

def build_edit_payload(
    spec: TaskEditSpec,
    add_tag_ids: list[str] | None,
    remove_tag_ids: list[str] | None,
    move_to: dict[str, object] | None,
    lifecycle: str | None,
) -> dict[str, Any]:
    """Convert TaskEditSpec fields to bridge-ready camelCase dict.
    Only includes non-UNSET fields."""
```

**Why extract:** Serialization logic is currently split -- add payload built in two repo implementations (duplicated), edit payload built in service. Unifying into one module eliminates the duplication and asymmetry.

### 4. `src/omnifocus_operator/service/__init__.py`

Re-exports `OperatorService` and `ErrorOperatorService` so all existing imports work unchanged:
```python
from omnifocus_operator.service._orchestrator import ErrorOperatorService, OperatorService
```

---

## Modified Components

### Repository Protocol (`repository/protocol.py`)

**Change:** Unify `add_task` and `edit_task` signatures.

```python
# BEFORE
async def add_task(self, spec: TaskCreateSpec, *, resolved_tag_ids: list[str] | None) -> TaskCreateResult
async def edit_task(self, payload: dict[str, Any]) -> dict[str, Any]

# AFTER
async def add_task(self, payload: dict[str, Any]) -> dict[str, Any]
async def edit_task(self, payload: dict[str, Any]) -> dict[str, Any]
```

Both now: accept pre-built dict, return dict from bridge. Payload construction moved to `conversion.py`, result wrapping moved to service.

**Impact:** All three repository implementations + their tests.

### HybridRepository (`repository/hybrid.py`)

**Change:** `add_task` drops spec-based signature, becomes a thin bridge delegate (matches `edit_task` pattern).

```python
# BEFORE (lines 477-509) -- builds payload from spec
@_ensures_write_through
async def add_task(self, spec, *, resolved_tag_ids=None) -> TaskCreateResult:
    payload = spec.model_dump(by_alias=True, exclude_none=True, mode="json")
    payload.pop("tags", None)
    if resolved_tag_ids:
        payload["tagIds"] = resolved_tag_ids
    result = await self._bridge.send_command("add_task", payload)
    return TaskCreateResult(success=True, id=result["id"], name=result["name"])

# AFTER -- symmetric with edit_task
@_ensures_write_through
async def add_task(self, payload: dict[str, Any]) -> dict[str, Any]:
    return await self._bridge.send_command("add_task", payload)
```

### BridgeRepository (`repository/bridge.py`)

Same change as HybridRepository. Drops `TaskCreateSpec` import, returns `dict` instead of `TaskCreateResult`.

### InMemoryRepository (`repository/in_memory.py`)

**Signature change:** `add_task` takes `dict[str, Any]` instead of `TaskCreateSpec`.
**Behavioral change:** Builds in-memory `Task` from dict keys (camelCase) instead of spec attributes.
**Location change:** Move to `tests/` (or at minimum remove from `repository/__init__.py` exports).

### Bridge `__init__.py`

**Remove:** `InMemoryBridge` and `BridgeCall` from `__all__` and imports.

### Bridge factory (`bridge/factory.py`)

**Remove:** `"inmemory"` case. Update error message to list only `simulator` and `real`.

### Write Models (`models/write.py`)

**Add:** `extra="forbid"` on `TaskCreateSpec`, `TaskEditSpec`, `MoveToSpec`, `TagActionSpec`, `ActionsSpec`.

```python
class TaskCreateSpec(OmniFocusBaseModel):
    model_config = ConfigDict(extra="forbid")
    ...
```

**Note:** `OmniFocusBaseModel` sets `alias_generator`, `validate_by_name`, `validate_by_alias`. Pydantic v2 merges `ConfigDict` from parent and child -- `extra="forbid"` adds to the existing config without overriding.

### Service (`service.py` -> `service/_orchestrator.py`)

Slims from ~637 lines to ~80-100 lines. All private methods extracted. `edit_task` becomes a clear orchestration flow:

```python
async def edit_task(self, spec: TaskEditSpec) -> TaskEditResult:
    task = await self._repository.get_task(spec.id)
    if not task: raise ValueError(...)
    warnings = []

    # Domain: lifecycle
    lifecycle, lifecycle_warnings = process_lifecycle_if_present(spec, task)
    warnings.extend(lifecycle_warnings)

    # Validation: name, tags, move
    validate_edit_name(spec)
    add_ids, remove_ids, tag_warnings = await resolve_edit_tags(spec, task, self._repo)
    warnings.extend(tag_warnings)
    move_to = await resolve_edit_move(spec, task, self._repo)

    # Conversion: spec -> payload
    payload = build_edit_payload(spec, add_ids, remove_ids, move_to, lifecycle)

    # Domain: no-op detection
    is_noop, noop_warnings = detect_noop(payload, task, warnings)
    if is_noop: return TaskEditResult(success=True, id=spec.id, name=task.name, warnings=...)

    # Execute
    result = await self._repository.edit_task(payload)
    return TaskEditResult(success=True, id=result["id"], name=result["name"], warnings=warnings or None)
```

---

## Patterns to Follow

### Pattern 1: Module-level functions over class methods

**What:** Extract logic as module-level async/sync functions, not methods on helper classes.
**When:** The function doesn't need persistent state across calls.
**Why:** All current private methods on `OperatorService` are stateless -- they only use `self._repository` as a dependency. Free functions with explicit `repo` parameter are clearer and directly testable without instantiating the service.

### Pattern 2: Package with backward-compatible imports

**What:** Convert `service.py` to `service/` package directory.
**When:** Decomposing a module with established import paths.
**Why:** `from omnifocus_operator.service import OperatorService` is used in `server.py`, tests, and lifespan. The `__init__.py` re-exports everything, so no external import changes needed.

```
service/
  __init__.py       # re-exports OperatorService, ErrorOperatorService
  _orchestrator.py  # OperatorService, ErrorOperatorService
  validation.py     # validate_task_name, resolve_parent, resolve_tags
  domain.py         # process_lifecycle, compute_tag_diff, check_cycle, detect_noop
  conversion.py     # build_add_payload, build_edit_payload
```

### Pattern 3: Conversion as pure functions

**What:** All spec-to-dict conversion in `conversion.py` as pure sync functions (no async, no repo access).
**When:** Serialization/format conversion code.
**Why:** Pure functions are trivially testable with no dependencies. Makes the data flow explicit: validation resolves IDs first, then conversion uses resolved IDs.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: WriteModel base class with inheritance

**What:** Creating a `WriteModel` base class for `TaskCreateSpec` and `TaskEditSpec`.
**Why bad:** The two specs are fundamentally different -- `TaskCreateSpec` uses `None` defaults (OmniFocus picks defaults), `TaskEditSpec` uses `UNSET` sentinel (omit = no change). Forcing inheritance would require awkward type gymnastics.
**Instead:** Keep as sibling classes. Share behavior through the conversion module.

### Anti-Pattern 2: Moving conversion into models

**What:** Adding `to_bridge_payload()` methods on spec models.
**Why bad:** Models would need to know bridge payload format (camelCase keys, `tagIds` vs `tags`). Violates single responsibility.
**Instead:** Models = pure data containers. Conversion = separate module.

### Anti-Pattern 3: Intermediate typed payload model

**What:** Creating a `BridgePayload` Pydantic model between service and repository.
**Why bad:** Bridge protocol is `dict[str, Any]`. Adding a typed intermediate creates serialization overhead. The dict gets serialized to JSON for IPC immediately. Type safety comes from conversion functions having typed inputs.
**Instead:** Use `dict[str, Any]` at repo boundary.

### Anti-Pattern 4: Over-extracting into tiny modules

**What:** Separate files for each function (e.g., `lifecycle.py`, `tag_diff.py`, `cycle_check.py`).
**Why bad:** Domain logic totals ~150 lines. Four+ files creates navigation overhead without encapsulation benefit.
**Instead:** Three modules by concern: `validation.py`, `domain.py`, `conversion.py`.

---

## Suggested Build Order

Ordered by dependency direction: repo protocol changes must land before service changes that depend on new signatures.

### Phase 1: Write model strictness (independent, no deps)

Add `extra="forbid"` to all write spec models.

- **Files:** `models/write.py`
- **Tests:** Verify unknown fields raise `ValidationError`
- **Risk:** LOW -- Pydantic v2 ConfigDict merging is well-tested
- **Dependencies:** None

### Phase 2: Unify repository write signatures

Change `add_task` and `edit_task` on Repository protocol to both accept/return `dict[str, Any]`.

- **Files:**
  - `repository/protocol.py` (protocol change)
  - `repository/hybrid.py` (simplify `add_task` to bridge passthrough)
  - `repository/bridge.py` (same simplification)
  - `repository/in_memory.py` (update `add_task` to work from dict)
- **Service bridge:** Service's `add_task` temporarily builds payload dict inline (copy 5 lines from old `HybridRepository.add_task`) before Phase 3 moves it to `conversion.py`.
- **Risk:** LOW -- mechanical signature change, existing tests catch breakage
- **Dependencies:** None (parallel with Phase 1)

### Phase 3: Extract service into package

Convert `service.py` to `service/` package with sub-modules.

**Internal order (each step keeps tests green):**
1. Create `service/` directory with `__init__.py` re-exporting current API
2. Move `OperatorService` + `ErrorOperatorService` to `service/_orchestrator.py`
3. Extract `validation.py` (resolve_parent, resolve_tags, validate_task_name)
4. Extract `domain.py` (process_lifecycle, compute_tag_diff, check_cycle, detect_noop)
5. Extract `conversion.py` (build_add_payload, build_edit_payload)
6. Slim `_orchestrator.py` to use extracted modules

- **Risk:** MEDIUM -- most complex phase, many moving parts. Each sub-step must keep tests green.
- **Dependencies:** Phase 2 (service needs to build payload for new repo signature)

### Phase 4: Relocate InMemoryBridge from production exports

Two sub-steps (matches existing TODO):

1. **Remove from public surface:** Drop from `bridge/__init__.py`, remove `"inmemory"` from bridge factory, update test imports to direct paths.
2. **Physical relocation (optional):** Move file to `tests/` if desired. File can stay in `src/` with no public export.

- **Files:** `bridge/__init__.py`, `bridge/factory.py`, `repository/factory.py`, 4 test files
- **Risk:** LOW -- import-only changes, no behavioral change
- **Dependencies:** Best done last to avoid import churn during other phases

---

## Integration Points

### Unchanged

| Integration | Path |
|-------------|------|
| `server.py` -> `OperatorService` | `from omnifocus_operator.service import OperatorService` |
| `server.py` -> write models | `from omnifocus_operator.models import TaskCreateSpec, TaskEditSpec` |
| Repository -> Bridge | `self._bridge.send_command(op, payload)` |
| Write-through decorator | `@_ensures_write_through` on repo write methods |

### New

| Integration | Description |
|-------------|-------------|
| `_orchestrator.py` -> `validation.py` | `validate_task_name()`, `resolve_parent()`, `resolve_tags()` |
| `_orchestrator.py` -> `domain.py` | `process_lifecycle()`, `compute_tag_diff()`, `detect_noop()`, `check_cycle()` |
| `_orchestrator.py` -> `conversion.py` | `build_add_payload()`, `build_edit_payload()` |
| `validation.py` -> Repository | Needs repo for `get_project`, `get_task`, `get_tag`, `get_all` lookups |
| `domain.py` -> Repository | `compute_tag_diff` needs repo for tag resolution; `check_cycle` needs repo for task tree |

### Breaking changes (internal only, no public API changes)

| Change | Affected |
|--------|----------|
| `Repository.add_task` signature | All 3 repo implementations + direct repo tests |
| `InMemoryBridge` removed from `bridge.__init__` | 5 test files importing from `bridge` package |
| `service.py` becomes `service/` package | None -- `__init__.py` re-exports everything |

---

## Sources

- Direct codebase analysis (HIGH confidence)
  - `src/omnifocus_operator/service.py` -- 637 lines, primary decomposition target
  - `src/omnifocus_operator/repository/protocol.py` -- write signature asymmetry
  - `src/omnifocus_operator/repository/hybrid.py` -- add_task payload building (lines 477-509)
  - `src/omnifocus_operator/repository/bridge.py` -- add_task payload building (lines 102-126, duplicated)
  - `src/omnifocus_operator/repository/in_memory.py` -- test-only implementation
  - `src/omnifocus_operator/models/write.py` -- write models, UNSET sentinel
  - `src/omnifocus_operator/bridge/in_memory.py` -- test double in production tree
  - `src/omnifocus_operator/bridge/__init__.py` -- public exports including test doubles
  - `src/omnifocus_operator/bridge/factory.py` -- inmemory branch in factory
  - `.planning/todos/pending/2026-03-10-remove-inmemorybridge-from-production-exports-and-factory.md`
