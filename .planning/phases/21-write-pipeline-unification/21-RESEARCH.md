# Phase 21: Write Pipeline Unification - Research

**Researched:** 2026-03-19
**Domain:** Internal refactoring — write pipeline symmetry (service + repository layers)
**Confidence:** HIGH

## Summary

Phase 21 unifies the add_task and edit_task write paths so both follow identical structural patterns at every layer boundary. The scope is well-defined and constrained: converge serialization strategy (`exclude_none` -> `exclude_unset`), eliminate the camelCase intermediate dict in edit_task's service code, extract shared bridge-sending logic into a `BridgeWriteMixin`, and add explicit protocol inheritance.

Phase 20 already did the heavy lifting (typed payloads, contracts/ package). What remains is smaller mechanical work. All changes are internal — no behavioral changes, no new tools.

**Primary recommendation:** Three ordered steps: (1) service-side payload construction cleanup, (2) repo serialization + mixin extraction, (3) explicit protocol conformance. Each step keeps all 522 tests green.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Both repos standardize on `exclude_unset=True` (currently add_task uses `exclude_none=True`)
- Service builds `CreateTaskRepoPayload` via kwargs dict with only populated fields -> `model_validate()`, instead of setting all fields (some to None) via direct constructor
- edit_task: build `repo_kwargs` in snake_case from the start, eliminate the `_payload_to_repo` mapping entirely
- Shared `_send_to_bridge(command: str, payload) -> dict[str, Any]` helper in a `BridgeWriteMixin` class
- Helper does `payload.model_dump(by_alias=True, exclude_unset=True)` + `self._bridge.send_command(command, raw)` — nothing else
- Cache invalidation (`self._cached = None`) stays OUTSIDE the helper, visible in each calling method
- Mixin lives in `repository/` (not in the bridge module)
- All three repos explicitly declare they implement the Repository protocol
- Mixin-first in inheritance chain: `class BridgeRepository(BridgeWriteMixin, Repository)`

### Claude's Discretion
- Exact file location for BridgeWriteMixin within `repository/`
- InMemory internal pattern (model_dump vs direct field access)
- Whether to unify InMemory's add_task and edit_task internal patterns or leave them different
- Ordering of changes across the codebase

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PIPE-01 | add_task and edit_task have symmetric signatures at the service-repository boundary | Protocol already defines symmetric signatures. Repos need explicit inheritance. Service payload construction needs convergence (add_task: kwargs dict pattern, edit_task: eliminate camelCase roundtrip). |
| PIPE-02 | Both write paths use the same pattern for bridge payload construction (no split between repo model_dump vs service dict-building) | Repos converge on `exclude_unset=True`. BridgeWriteMixin centralizes `model_dump(by_alias=True, exclude_unset=True)` + `send_command()`. Service builds both payloads via kwargs dict -> `model_validate()`. |
</phase_requirements>

## Architecture Patterns

### Current State (asymmetries to fix)

**Service layer:**
- add_task: builds `CreateTaskRepoPayload` via direct constructor, passes all fields (many as `None`) -> relies on repo's `exclude_none` to strip them
- edit_task: builds camelCase intermediate dict (`payload`), then maps back to snake_case via `_payload_to_repo` dict before `model_validate()` -> relies on repo's `exclude_unset`

**Repository layer:**
- add_task in Bridge/Hybrid: `payload.model_dump(by_alias=True, exclude_none=True)`
- edit_task in Bridge/Hybrid: `payload.model_dump(by_alias=True, exclude_unset=True)`
- Both repos duplicate the `model_dump() + send_command()` plumbing
- No repo explicitly inherits from `Repository` protocol

### Target State

**Service layer (both paths identical):**
```python
# Build kwargs dict with only populated fields
repo_kwargs: dict[str, object] = {"name": command.name}
if command.parent is not None:
    repo_kwargs["parent"] = command.parent
if resolved_tag_ids is not None:
    repo_kwargs["tag_ids"] = resolved_tag_ids
# ... only set fields that have values
payload = CreateTaskRepoPayload.model_validate(repo_kwargs)
```

**Repository layer (both paths identical):**
```python
class BridgeWriteMixin:
    _bridge: Bridge  # provided by the concrete class

    async def _send_to_bridge(self, command: str, payload: OmniFocusBaseModel) -> dict[str, Any]:
        raw = payload.model_dump(by_alias=True, exclude_unset=True)
        return await self._bridge.send_command(command, raw)

class BridgeRepository(BridgeWriteMixin, Repository):
    async def add_task(self, payload: CreateTaskRepoPayload) -> CreateTaskRepoResult:
        result = await self._send_to_bridge("add_task", payload)
        self._cached = None  # visible cache invalidation
        return CreateTaskRepoResult(id=result["id"], name=result["name"])
```

### Key Insight: exclude_none vs exclude_unset Safety

Verified empirically: when the service builds `CreateTaskRepoPayload` via kwargs dict (only setting populated fields), `exclude_none` and `exclude_unset` produce **identical output** for add_task. The change from `exclude_none` to `exclude_unset` is safe because:
- Unset fields (not passed to constructor) are excluded by `exclude_unset`
- `exclude_none` was only needed because the old pattern passed all fields as `None` explicitly
- Both behaviors correctly preserve `flagged=False` (falsy but meaningful) — neither `None` nor unset

### Anti-Patterns to Avoid
- **Changing the intermediate dict format in edit_task without updating no-op detection:** The no-op detection (lines 342-403 in service.py) currently uses camelCase keys. When refactoring to snake_case, the no-op detection keys must change too. This is the riskiest part — test coverage is strong here but the mapping is manual.
- **Moving cache invalidation into the mixin:** The user explicitly wants cache invalidation visible at each call site, not hidden in a helper.
- **Forgetting `_ensures_write_through` on HybridRepository:** The decorator must stay on the concrete methods, not move into the mixin.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| camelCase serialization | Manual key mapping dicts | Pydantic's `by_alias=True` with `alias_generator=to_camel` | Already in the base model; the `_payload_to_repo` mapping is legacy |
| Field presence tracking | Manual dict building with `if key in payload` | Pydantic's `exclude_unset=True` | Tracks which fields were explicitly passed to constructor |

## Common Pitfalls

### Pitfall 1: No-op Detection Key Migration
**What goes wrong:** Service's no-op detection uses camelCase dict keys (`"estimatedMinutes"`, `"dueDate"`, etc.) to compare payload against current task state. After refactoring to snake_case, these comparisons silently miss fields.
**Why it happens:** The field_comparisons dict and `_date_keys` set use camelCase strings matching the old intermediate dict format.
**How to avoid:** When converting edit_task's intermediate dict to snake_case, update ALL comparison logic to use snake_case keys too. Tests for no-op detection are thorough (test_noop_detection_same_name, test_noop_detection_different_name, test_noop_detection_same_date_different_timezone, etc.) — they'll catch regressions.
**Warning signs:** Tests pass but no-op detection stops working (would show as behavioral regression in tests that check for `EDIT_NO_CHANGES_DETECTED` warning).

### Pitfall 2: MoveToRepoPayload Construction
**What goes wrong:** The moveTo handling in edit_task currently builds a camelCase dict (`{"position": ..., "containerId": ...}`) then converts it to `MoveToRepoPayload`. After refactoring, the intermediate dict should use snake_case, but the `MoveToRepoPayload` field names are already snake_case.
**Why it happens:** The current code builds `move_to_dict` with camelCase keys, then manually extracts `containerId`/`anchorId` when constructing MoveToRepoPayload.
**How to avoid:** Build `move_to_dict` with snake_case keys from the start, then pass directly to `MoveToRepoPayload(...)`.

### Pitfall 3: HybridRepository Has No self._cached
**What goes wrong:** The BridgeWriteMixin should not reference `self._cached` — only BridgeRepository has it. HybridRepository uses SQLite (no in-memory cache).
**Why it happens:** Cache invalidation pattern differs between the two repos.
**How to avoid:** Keep cache invalidation outside the mixin (already a locked decision). BridgeRepository does `self._cached = None`, HybridRepository does nothing (the `@_ensures_write_through` decorator handles freshness via WAL polling).

### Pitfall 4: Test Name Referencing exclude_none
**What goes wrong:** `test_add_task_excludes_none_fields` in test_hybrid_repository.py tests that None fields are excluded from the bridge payload. After the change to `exclude_unset`, the test name becomes misleading.
**Why it happens:** Test name describes implementation detail, not behavior.
**How to avoid:** Rename to `test_add_task_excludes_unset_fields` or a behavior-focused name like `test_add_task_only_sends_populated_fields`. The assertion logic stays the same (payload built via kwargs dict still excludes those fields).

## Code Examples

### Service add_task: Current vs Target

**Current (all fields to constructor):**
```python
payload = CreateTaskRepoPayload(
    name=command.name,
    parent=command.parent,
    tag_ids=resolved_tag_ids,
    due_date=command.due_date.isoformat() if command.due_date else None,
    # ... all fields, many None
)
```

**Target (kwargs dict, only populated fields):**
```python
repo_kwargs: dict[str, object] = {"name": command.name}
if command.parent is not None:
    repo_kwargs["parent"] = command.parent
if resolved_tag_ids is not None:
    repo_kwargs["tag_ids"] = resolved_tag_ids
if command.due_date is not None:
    repo_kwargs["due_date"] = command.due_date.isoformat()
if command.defer_date is not None:
    repo_kwargs["defer_date"] = command.defer_date.isoformat()
if command.planned_date is not None:
    repo_kwargs["planned_date"] = command.planned_date.isoformat()
if command.flagged is not None:
    repo_kwargs["flagged"] = command.flagged
if command.estimated_minutes is not None:
    repo_kwargs["estimated_minutes"] = command.estimated_minutes
if command.note is not None:
    repo_kwargs["note"] = command.note
payload = CreateTaskRepoPayload.model_validate(repo_kwargs)
```

### Service edit_task: Eliminate camelCase Roundtrip

**Current (camelCase intermediate -> `_payload_to_repo` mapping):**
```python
payload: dict[str, object] = {"id": command.id}
# ... builds camelCase keys like "estimatedMinutes", "dueDate"
_payload_to_repo = {"estimatedMinutes": "estimated_minutes", ...}
for payload_key, repo_key in _payload_to_repo.items():
    if payload_key in payload:
        repo_kwargs[repo_key] = payload[payload_key]
```

**Target (snake_case from the start):**
```python
payload: dict[str, object] = {"id": command.id}
# ... builds snake_case keys directly
_simple_fields = [
    ("name", "name"),
    ("note", "note"),
    ("flagged", "flagged"),
    ("estimated_minutes", "estimated_minutes"),
]
# ... later:
repo_payload = EditTaskRepoPayload.model_validate(payload)
```

### BridgeWriteMixin

```python
class BridgeWriteMixin:
    """Shared bridge-sending logic for BridgeRepository and HybridRepository."""

    _bridge: Bridge

    async def _send_to_bridge(self, command: str, payload: OmniFocusBaseModel) -> dict[str, Any]:
        """Serialize payload to camelCase dict and send via bridge."""
        raw = payload.model_dump(by_alias=True, exclude_unset=True)
        return await self._bridge.send_command(command, raw)
```

### Explicit Protocol Conformance

```python
class BridgeRepository(BridgeWriteMixin, Repository):
    # capabilities first, contract last
    ...

class HybridRepository(BridgeWriteMixin, Repository):
    ...

class InMemoryRepository(Repository):
    # no mixin — no bridge
    ...
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio |
| Config file | `pyproject.toml` |
| Quick run command | `uv run python -m pytest -x -q --no-header` |
| Full suite command | `uv run python -m pytest -q --no-header` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PIPE-01 | Symmetric signatures at service-repo boundary | unit | `uv run python -m pytest tests/test_repository.py::TestInMemoryRepository -x` | Existing (protocol conformance) |
| PIPE-01 | Explicit protocol inheritance for all 3 repos | unit | `uv run python -m pytest tests/test_repository.py -k "satisfies_protocol" -x` | Existing (2 tests) + test_hybrid_repository.py (1 test) |
| PIPE-02 | Bridge payload uses exclude_unset for add_task | unit | `uv run python -m pytest tests/test_hybrid_repository.py -k "excludes" -x` | Existing (rename needed) |
| PIPE-02 | Service builds add_task payload via kwargs dict | unit | `uv run python -m pytest tests/test_service.py -k "TestAddTask" -x` | Existing (18 tests) |
| PIPE-02 | Service builds edit_task payload without camelCase roundtrip | unit | `uv run python -m pytest tests/test_service.py -k "TestEditTask" -x` | Existing (50+ tests) |
| PIPE-02 | BridgeWriteMixin used by both bridge repos | unit | `uv run python -m pytest tests/test_repository.py tests/test_hybrid_repository.py -k "add_task or edit_task" -x` | Existing (covers behavior) |

### Sampling Rate
- **Per task commit:** `uv run python -m pytest -x -q --no-header` (full suite, ~13s)
- **Per wave merge:** `uv run python -m pytest -q --no-header` (full suite)
- **Phase gate:** Full suite green + mypy passes

### Wave 0 Gaps
None — existing test infrastructure covers all phase requirements. All 522 tests exercise the write pipeline through service and repository layers. No new test files needed; some test names may be renamed for clarity.

## Specific Implementation Notes

### Service edit_task Refactoring Details

The edit_task method (lines 160-445) builds an intermediate `payload` dict in camelCase. This dict serves dual purposes:
1. **No-op detection** (lines 342-403): compares payload keys against current task state
2. **Repo payload construction** (lines 405-432): maps camelCase back to snake_case via `_payload_to_repo`

When refactoring to snake_case from the start:
- The `_simple_fields` list changes from `("name", "name"), ("note", "note"), ("flagged", "flagged"), ("estimated_minutes", "estimatedMinutes")` to `("name", "name"), ("note", "note"), ("flagged", "flagged"), ("estimated_minutes", "estimated_minutes")`
- The `_date_fields` list changes similarly
- `field_comparisons` dict keys change from camelCase to snake_case
- `_date_keys` set changes from `{"dueDate", "deferDate", "plannedDate"}` to `{"due_date", "defer_date", "planned_date"}`
- Tag-related keys change from `"addTagIds"/"removeTagIds"` to `"add_tag_ids"/"remove_tag_ids"`
- `"moveTo"` becomes `"move_to"`
- The `_payload_to_repo` mapping and its loop are eliminated entirely — `payload` dict IS the repo_kwargs dict
- `MoveToRepoPayload` construction changes from extracting `containerId`/`anchorId` to `container_id`/`anchor_id`

### BridgeWriteMixin File Location

Recommendation: `src/omnifocus_operator/repository/bridge_write_mixin.py`
- Clear name, immediately discoverable in the repository package
- Follows existing convention of one class per file in the repository package
- Import in bridge.py and hybrid.py: `from omnifocus_operator.repository.bridge_write_mixin import BridgeWriteMixin`

### InMemory Alignment

InMemoryRepository's edit_task already uses `model_dump(by_alias=True, exclude_unset=True)` to get a camelCase dict, then applies mutations via a `_key_map`. This works but creates an unnecessary camelCase -> snake_case mapping inside a test double.

Recommendation: keep `model_dump` for consistency with the real repos' pattern, but the internal implementation details (how InMemory applies mutations) don't need to match the bridge repos exactly. The test double just needs to produce correct results.

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection of all files listed in CONTEXT.md canonical_refs
- Empirical verification of `exclude_none` vs `exclude_unset` behavior via Python REPL
- Full test suite run confirming 522 tests pass (baseline)

### Secondary (MEDIUM confidence)
- Pydantic `model_dump` documentation: `exclude_unset` tracks which fields were explicitly passed to the constructor; `exclude_none` filters by value regardless of whether field was explicitly set

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies, pure refactoring
- Architecture: HIGH — all patterns verified against actual codebase, empirically tested
- Pitfalls: HIGH — identified from direct code analysis, test coverage verified

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (stable — internal refactoring, no external dependencies)
