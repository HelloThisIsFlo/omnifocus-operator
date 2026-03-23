# Phase 26: Replace InMemoryRepository with stateful InMemoryBridge - Research

**Researched:** 2026-03-21
**Domain:** Test infrastructure refactoring -- internal to the test suite, no production code changes
**Confidence:** HIGH

## Summary

This phase replaces `InMemoryRepository` (a repository-layer test double that simulates writes independently of the bridge) with a stateful `InMemoryBridge` that handles `add_task`/`edit_task` commands by mutating in-memory dict state. The key motivation: write tests currently bypass the real serialization path (`BridgeWriteMixin` -> `model_dump(by_alias=True)` -> bridge). After this phase, write tests exercise that path through a real `BridgeRepository` backed by the stateful `InMemoryBridge`.

The migration touches 8 test files with ~147 `InMemoryRepository` references (~108 instantiation sites). Two distinct test categories exist: (1) **read-only tests** that just need a snapshot for `get_all`/`get_task`/`get_project`/`get_tag`, and (2) **write tests** that need `add_task`/`edit_task` to actually mutate state and be readable back. Both categories switch from `InMemoryRepository(snapshot=...)` to `BridgeRepository(bridge=InMemoryBridge(...), mtime_source=ConstantMtimeSource())`.

**Primary recommendation:** Migrate write logic from `InMemoryRepository` (model-level mutations) to `InMemoryBridge` (dict-level mutations), wire all tests through `BridgeRepository` + `InMemoryBridge` fixtures, delete `InMemoryRepository`.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Dict-native -- InMemoryBridge stores entities as camelCase dicts internally (matching real bridge format)
- **D-02:** Seeded with `make_snapshot_dict()` -- same factory already used today, produces camelCase dicts
- **D-03:** `send_command("get_all")` reassembles the dict from internal `_tasks`, `_projects`, `_tags`, etc. lists
- **D-04:** No Pydantic models inside the bridge -- the bridge speaks dicts, stores dicts, returns dicts
- **D-05:** Full behavioral parity with the real bridge -- InMemoryBridge must simulate OmniFocus faithfully enough that tests are reliable
- **D-06:** Minimal implementation complexity, but faithful behavior -- don't over-engineer, but don't cut corners on correctness
- **D-07:** InMemoryRepository's current write logic migrates into InMemoryBridge, adapted from model-level to dict-level operations
- **D-08:** add_task: generates synthetic ID, URL, timestamps, computed fields (in_inbox, effectiveFlagged, etc.), appends to internal tasks list
- **D-09:** edit_task: finds task by ID, applies field updates, tag operations (remove then add), lifecycle (complete/drop), move operations -- all on camelCase dicts
- **D-10:** Phase 27 golden master will validate this parity claim -- Phase 26 builds it right, Phase 27 proves it
- **D-11:** Pytest fixture composition -- `bridge` fixture creates InMemoryBridge, `repo` fixture takes `bridge` fixture and creates BridgeRepository around it
- **D-12:** Tests inject whichever fixtures they need -- `repo` only, or both `repo` and `bridge` -- standard pytest pattern, no tuple unpacking or factory functions
- **D-13:** ConstantMtimeSource wired into the repo fixture -- invisible to tests that don't care about caching behavior

### Claude's Discretion
- Whether existing call tracking (`_calls`, `call_count`) and error injection (`set_error`/`clear_error`) survive unchanged
- How to dispatch operations in `send_command` (if/elif vs registry)
- Error handling for unknown operations or missing task IDs in edit
- Whether `make_snapshot()` (Pydantic version) is kept alongside `make_snapshot_dict()` for tests that need models directly
- Exact field defaults and computed field logic for add_task simulation
- Migration order across the 9 test files (~147 InMemoryRepository imports)
- Whether `changed_fields()` (from Phase 25) is used inside InMemoryBridge's write handlers

### Deferred Ideas (OUT OF SCOPE)
- Golden master validation -- Phase 27 captures RealBridge behavior via UAT and proves InMemoryBridge matches

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-10 | `InMemoryBridge` maintains mutable in-memory state and handles `add_task`/`edit_task` commands as a stateful test double | Architecture pattern: stateful bridge with dict-level mutation; write logic migrated from InMemoryRepository |
| INFRA-11 | `InMemoryRepository` deleted -- write test infrastructure routes through the bridge serialization layer | Deletion plan: migrate all 108 instantiation sites across 8 files, then delete `tests/doubles/repository.py` + update `__init__.py` |
| INFRA-12 | Write tests exercise the real serialization path (`BridgeWriteMixin`, `model_dump(by_alias=True)`, snapshot parsing) via the stateful `InMemoryBridge` | All tests rewired to `BridgeRepository(bridge=InMemoryBridge(...), mtime_source=ConstantMtimeSource())` -- writes go through `_send_to_bridge` which calls `model_dump(by_alias=True, exclude_unset=True)` |

</phase_requirements>

## Architecture Patterns

### Current Architecture (Before)

```
Tests                              Test Doubles
─────                              ────────────
test_service.py ──────────────► InMemoryRepository (snapshot: AllEntities)
test_server.py  ──────────────►   └── add_task(): mutates Pydantic models directly
test_service_resolve.py ──────►   └── edit_task(): model_dump → dict → mutate models
test_repository.py ───────────►
                                InMemoryBridge (static data: dict)
                                  └── send_command(): returns same dict every time
```

**Problem:** Write tests bypass `BridgeWriteMixin._send_to_bridge()` -- the `model_dump(by_alias=True)` serialization path is never tested. InMemoryRepository simulates writes independently, so drift between its behavior and real bridge behavior goes undetected.

### Target Architecture (After)

```
Tests                              Test Doubles
─────                              ────────────
test_service.py ──────────────► BridgeRepository (bridge: InMemoryBridge, mtime: ConstantMtimeSource)
test_server.py  ──────────────►   └── add_task → _send_to_bridge → InMemoryBridge.send_command("add_task")
test_service_resolve.py ──────►   └── edit_task → _send_to_bridge → InMemoryBridge.send_command("edit_task")
test_repository.py ───────────►   └── get_all → InMemoryBridge.send_command("get_all") → AllEntities.model_validate

                                InMemoryBridge (stateful: _tasks, _projects, _tags, _folders, _perspectives)
                                  └── send_command("get_all"): reassembles snapshot dict from internal lists
                                  └── send_command("add_task"): generates task dict, appends to _tasks
                                  └── send_command("edit_task"): finds task dict, applies mutations
```

**Key insight:** The `BridgeRepository` already exists and works. `BridgeWriteMixin._send_to_bridge()` calls `payload.model_dump(by_alias=True, exclude_unset=True)` then `bridge.send_command(operation, params)`. The only missing piece is making `InMemoryBridge.send_command()` handle write operations by mutating internal state rather than always returning static data.

### Fixture Composition Pattern

Already proven in `tests/test_repository.py`:

```python
# Existing pattern (lines 57-78 of test_repository.py):
@pytest.fixture
def bridge(snapshot_data: dict[str, Any]) -> InMemoryBridge:
    return InMemoryBridge(data=snapshot_data)

@pytest.fixture
def mtime() -> FakeMtimeSource:
    return FakeMtimeSource(mtime_ns=1)

@pytest.fixture
def repo(bridge: InMemoryBridge, mtime: FakeMtimeSource) -> BridgeRepository:
    return BridgeRepository(bridge=bridge, mtime_source=mtime)
```

For Phase 26, this pattern extends with `ConstantMtimeSource` (always returns 0) to eliminate caching concerns from tests that don't care about staleness.

### Data Flow Through the Real Serialization Path

```
Service.add_task(AddTaskCommand)
  → Resolver resolves tags/parent
  → Service builds AddTaskRepoPayload
  → BridgeRepository.add_task(payload)
    → BridgeWriteMixin._send_to_bridge("add_task", payload)
      → payload.model_dump(by_alias=True, exclude_unset=True)  ← KEY: real serialization
      → bridge.send_command("add_task", raw_dict)               ← KEY: InMemoryBridge handles this
    → cache invalidated (_cached = None)
    → returns AddTaskRepoResult
```

After Phase 26, InMemoryBridge's `send_command("add_task", params)` receives the dict that went through `model_dump(by_alias=True)` -- camelCase keys, exclude_unset applied. This is the same dict the real OmniJS bridge would receive.

## InMemoryBridge Rewrite Specification

### Internal State Structure

```python
class InMemoryBridge(Bridge):
    def __init__(self, data: dict[str, Any] | None = None, ...) -> None:
        # Parse seed data into separate entity lists
        seed = data or {}
        self._tasks: list[dict[str, Any]] = list(seed.get("tasks", []))
        self._projects: list[dict[str, Any]] = list(seed.get("projects", []))
        self._tags: list[dict[str, Any]] = list(seed.get("tags", []))
        self._folders: list[dict[str, Any]] = list(seed.get("folders", []))
        self._perspectives: list[dict[str, Any]] = list(seed.get("perspectives", []))
        # Preserve existing call tracking and error injection
        self._calls: list[BridgeCall] = []
        self._error: Exception | None = None
        ...
```

### Operation Dispatch

`send_command` must dispatch to the right handler based on `operation`:

- `"get_all"` -> reassemble snapshot dict from internal lists
- `"add_task"` -> generate task dict, append to `_tasks`, return `{"id": ..., "name": ...}`
- `"edit_task"` -> find task in `_tasks`, apply mutations, return `{"id": ..., "name": ...}`
- Any other operation -> return empty dict (or raise, at Claude's discretion)

### add_task Handler (D-08)

Migrated from `InMemoryRepository.add_task` (lines 54-93 of `tests/doubles/repository.py`), adapted from model-level to dict-level:

- Generate synthetic ID: `f"mem-{uuid4().hex[:8]}"`
- Generate URL: `f"omnifocus:///task/{task_id}"`
- Generate timestamps: ISO format with UTC
- Compute fields: `inInbox` (True if no parent), `effectiveFlagged` (same as flagged), etc.
- Input `params` dict arrives with camelCase keys from `model_dump(by_alias=True)`
- Must return `{"id": task_id, "name": name}` to match what BridgeRepository expects

**Key difference from InMemoryRepository:** Receives camelCase keys (`tagIds`, `dueDate`, `estimatedMinutes`) rather than snake_case model attributes. Must produce a complete task dict (all 26 fields) matching `make_task_dict()` defaults.

### edit_task Handler (D-09)

Migrated from `InMemoryRepository.edit_task` (lines 95-174 of `tests/doubles/repository.py`), already operates on dicts via `model_dump(by_alias=True)`:

- Find task in `_tasks` by `id`
- Apply field updates (name, note, flagged, dueDate, deferDate, plannedDate, estimatedMinutes) directly on the dict
- Tag operations: `removeTagIds` then `addTagIds` (already camelCase from payload alias)
- Lifecycle: `complete` -> `availability: "completed"`, `drop` -> `availability: "dropped"`
- Move: update `parent` field + `inInbox`
- Must return `{"id": ..., "name": ...}`

**Key simplification vs InMemoryRepository:** Already working with camelCase dicts, so no `_key_map` translation needed. Field names in `params` dict match field names in stored task dicts.

### Existing Features to Preserve

From current `InMemoryBridge` (lines 20-71 of `tests/doubles/bridge.py`):

| Feature | Current | After Rewrite |
|---------|---------|---------------|
| `BridgeCall` recording | `self._calls.append(...)` | Same -- record every `send_command` call |
| `call_count` property | `len(self._calls)` | Same |
| `set_error`/`clear_error` | Configurable error injection | Same -- raise before processing if set |
| WAL path simulation | `self._wal_path.write_bytes(b"flushed")` | Same |
| `Bridge` protocol conformance | Yes | Yes |

### Return Value Contract

`BridgeRepository` expects specific return shapes:

```python
# BridgeRepository.add_task (bridge.py:116-123):
result = await self._send_to_bridge("add_task", payload)
# result must have result["id"] and result["name"]

# BridgeRepository.edit_task (bridge.py:125-133):
result = await self._send_to_bridge("edit_task", payload)
# result must have result["id"] and result["name"]

# BridgeRepository.get_all via _refresh (bridge.py:135-153):
raw = await self._bridge.send_command("get_all")
adapt_snapshot(raw)
AllEntities.model_validate(raw)
# raw must be a valid snapshot dict (tasks, projects, tags, folders, perspectives)
```

## Migration Inventory

### Files to Modify

| File | InMemoryRepository refs | Category | Migration Strategy |
|------|------------------------|----------|--------------------|
| `tests/test_service.py` | 93 instantiations | Read + Write tests | Replace with `BridgeRepository(InMemoryBridge, ConstantMtimeSource)` |
| `tests/test_server.py` | 4 instantiations (+ 13 other refs) | Read + Write (monkeypatch) | Replace; monkeypatch sites need `BridgeRepository` creation |
| `tests/test_service_resolve.py` | 2 instantiations | Read-only (Resolver) | Replace with `BridgeRepository` |
| `tests/test_repository.py` | 9 instantiations | Repository-specific tests | Delete `TestInMemoryRepository`*, `TestInMemoryAddTask`, `TestInMemoryEditTaskLifecycle`; keep BridgeRepository tests |
| `tests/test_simulator_bridge.py` | 1 instantiation (lifespan) | Read-only | Replace with `BridgeRepository` |
| `tests/test_bridge.py` | 0 (1 import check) | Guard test | Update to verify InMemoryRepository is gone |
| `tests/test_service_domain.py` | 0 (3 comment refs) | Comments only | Update comments |
| `tests/doubles/__init__.py` | Import + export | Module wiring | Remove InMemoryRepository import/export |
| `tests/doubles/repository.py` | The file itself | **DELETE** | Entire file deleted |

*`TestInMemoryRepository.test_satisfies_repository_protocol` can be kept but should test `BridgeRepository` protocol conformance (already exists at line 379-384). The InMemoryRepository-specific protocol test becomes redundant.

### Test Behavior Changes (None Expected)

- Read tests: `InMemoryRepository.get_all()` returns the snapshot directly; `BridgeRepository.get_all()` calls bridge `send_command("get_all")`, passes through `adapt_snapshot()`, then `AllEntities.model_validate()`. Since test data is already in new-shape format (no old `status` keys), `adapt_snapshot()` is a no-op. The result is structurally identical.
- Write tests: Currently bypass `BridgeWriteMixin._send_to_bridge()`. After migration, they exercise the real serialization path. Since the payload `model_dump(by_alias=True, exclude_unset=True)` produces the same camelCase dicts the InMemoryBridge now handles, behavior should be identical.
- One subtle difference: `BridgeRepository.get_all()` is async with a lock. `InMemoryRepository.get_all()` returns the snapshot synchronously. Since all tests already `await` the call, this is transparent.

### Assertion Patterns That Need Attention

**ID prefix check:** Tests check `result.id.startswith("mem-")` -- InMemoryBridge must continue this convention.

**Object identity:** `test_get_all_data_delegates_to_repository` checks `result is snapshot` -- with `BridgeRepository`, each `get_all` returns a freshly-parsed `AllEntities`, so identity check fails. This specific test needs assertion adjustment (equality check instead of identity).

**Direct snapshot mutation:** Some tests access `repo._snapshot` or `snapshot.tasks` directly after writes. With `BridgeRepository`, the equivalent is `await repo.get_all()` then inspect.

## Common Pitfalls

### Pitfall 1: Object Identity Assertions
**What goes wrong:** Tests like `assert result is snapshot` fail because `BridgeRepository` parses a fresh `AllEntities` from the bridge dict on each call.
**Why it happens:** `InMemoryRepository.get_all()` returns the stored snapshot object directly. `BridgeRepository` deserializes through `AllEntities.model_validate()`.
**How to avoid:** Change identity assertions (`is`) to equality assertions (`==`) where appropriate. There's at least one in `test_service.py:50` (`assert result is snapshot`).
**Warning signs:** `AssertionError` on `is` comparisons.

### Pitfall 2: BridgeRepository Cache vs InMemoryRepository Pass-Through
**What goes wrong:** `BridgeRepository` caches results. After a write, cache is invalidated (`_cached = None`), and next `get_all` re-fetches from bridge. If tests rely on inspecting state without calling `get_all` first, they miss updates.
**Why it happens:** `BridgeRepository` has a caching layer that `InMemoryRepository` lacks.
**How to avoid:** Use `ConstantMtimeSource` (returns 0) so mtime never changes. After cache invalidation from writes, the next `get_all` will always re-fetch since `_cached` is `None`. Tests already call `get_all` to inspect state after writes.

### Pitfall 3: adapt_snapshot() Side Effects
**What goes wrong:** `BridgeRepository._refresh()` calls `adapt_snapshot(raw)` which mutates the dict in-place. If InMemoryBridge returns its internal lists directly (not copies), the adapter could modify InMemoryBridge's state.
**Why it happens:** `adapt_snapshot` is designed for old-format bridge data and modifies dicts in-place.
**How to avoid:** InMemoryBridge's `send_command("get_all")` must return a **deep copy** of its internal state, not the internal lists themselves. Since test data is already in new-shape format, `adapt_snapshot` is a no-op, but defensive copying prevents subtle bugs.
**Warning signs:** Tests pass individually but fail when run together due to shared state mutation.

### Pitfall 4: Missing Fields in Generated Task Dicts
**What goes wrong:** `add_task` handler generates a task dict missing fields that `AllEntities.model_validate()` expects. Pydantic validation fails on the next `get_all`.
**Why it happens:** Task model has 26 fields; easy to miss some when constructing manually.
**How to avoid:** Use `make_task_dict()` defaults as a template. Generate the new task dict by overlaying add_task params on `make_task_dict()` defaults.

### Pitfall 5: Monkeypatched Server Tests Assume Repository Interface
**What goes wrong:** `test_server.py` uses `monkeypatch.setattr("omnifocus_operator.repository.create_repository", lambda *a, **kw: InMemoryRepository(...))`. After migration, this must return `BridgeRepository(InMemoryBridge(...), ConstantMtimeSource())` instead.
**Why it happens:** These tests patch the factory to return a specific repo implementation.
**How to avoid:** Update all monkeypatch sites to create `BridgeRepository` with `InMemoryBridge`. The lambda signature stays the same.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Task dict defaults | Manual 26-field dict construction | `make_task_dict(**overrides)` | Already covers all defaults, used throughout tests |
| Snapshot dict assembly | Manual dict with tasks/projects/tags/... | `make_snapshot_dict(**overrides)` | Standard factory, already used for seeding |
| MtimeSource for tests | Custom always-zero implementation | `ConstantMtimeSource` | Already exists in `tests/doubles/mtime.py` |
| Deep copy for get_all | Manual dict reconstruction | `copy.deepcopy()` | Standard library, no edge cases |
| BridgeRepository wiring | Custom repo-bridge wrapper | `BridgeRepository(bridge, mtime_source)` | Production class, already tested |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x + pytest-asyncio |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-10 | InMemoryBridge handles add_task/edit_task stateully | unit | `uv run pytest tests/test_repository.py -x -q` | Existing file, tests need rewrite |
| INFRA-11 | InMemoryRepository deleted | unit | `uv run pytest tests/test_bridge.py::TestImportGuards -x -q` | Existing guard test needs update |
| INFRA-12 | Write tests exercise real serialization path | integration | `uv run pytest tests/test_service.py tests/test_server.py -x -q` | Existing files, rewired |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green (`uv run pytest tests/ -q` -- 611 tests)

### Wave 0 Gaps
None -- existing test infrastructure covers all phase requirements. The phase is about rewiring existing tests, not adding new test infrastructure.

## Discretion Recommendations

### Call tracking and error injection
**Recommendation: Preserve unchanged.** 23 tests in `test_repository.py` use `bridge.call_count` and `bridge.calls`. The `set_error`/`clear_error` pattern is used in error propagation tests. No reason to change these.

### Operation dispatch pattern
**Recommendation: if/elif chain.** Only 3 operations (`get_all`, `add_task`, `edit_task`). A registry pattern adds indirection for no benefit at this scale. Simple and readable.

### Error handling for unknown operations
**Recommendation: Return empty dict.** The current bridge returns `self._data` for any operation. Unknown operations should return `{}` -- consistent with current behavior and avoids test fragility.

### make_snapshot() (Pydantic version)
**Recommendation: Keep it.** `make_snapshot()` is used in 30+ test sites for creating `AllEntities` objects directly. Some tests need model instances (not dicts) for direct property access. It has no dependency on `InMemoryRepository`.

### changed_fields() in InMemoryBridge write handlers
**Recommendation: Not needed.** InMemoryBridge receives raw dicts from `model_dump(by_alias=True, exclude_unset=True)` -- unset fields are already excluded. No need for `changed_fields()` inside the bridge; the dict is the source of truth.

### Migration order
**Recommendation:**
1. Rewrite InMemoryBridge first (no tests break -- it's purely additive)
2. Add shared fixtures in a conftest or per-test-file
3. Migrate test files starting with `test_repository.py` (closest to the bridge), then `test_service_resolve.py` (small), then `test_service.py` (largest), then `test_server.py` (monkeypatch complexity), then remaining files
4. Delete `InMemoryRepository` last (after all references gone)

## Open Questions

1. **How to handle BridgeRepository cache invalidation in write tests**
   - What we know: `BridgeRepository` sets `_cached = None` after writes, next `get_all` re-fetches. `ConstantMtimeSource` returns 0, so mtime check passes (0 != 0 only on first call). After cache invalidation, next `get_all` always refreshes.
   - What's unclear: Whether `ConstantMtimeSource` returns 0 and `_last_mtime_ns` starts at 0 -- if they match, the first `get_all` might think cache is valid when `_cached` is `None`.
   - Recommendation: Check `BridgeRepository` logic -- `if self._cached is None or current_mtime != self._last_mtime_ns` means `_cached is None` always triggers refresh regardless of mtime. This is fine.

## Sources

### Primary (HIGH confidence)
- Direct code inspection of all referenced files in the codebase
- `tests/doubles/bridge.py` -- current InMemoryBridge (71 lines)
- `tests/doubles/repository.py` -- InMemoryRepository to be deleted (174 lines)
- `src/omnifocus_operator/repository/bridge.py` -- BridgeRepository implementation
- `src/omnifocus_operator/repository/bridge_write_mixin.py` -- serialization path
- `tests/conftest.py` -- factory functions (make_snapshot_dict, etc.)
- `tests/test_repository.py` -- existing BridgeRepository fixture pattern (lines 57-78)

## Metadata

**Confidence breakdown:**
- Architecture: HIGH -- all code inspected directly, patterns already exist in codebase
- Migration scope: HIGH -- exhaustive grep of all InMemoryRepository references (147 refs, 108 instantiations across 8 files)
- Pitfalls: HIGH -- identified from actual code paths (adapt_snapshot, cache, identity assertions)

**Research date:** 2026-03-21
**Valid until:** No expiration -- all findings are codebase-internal, not dependent on external libraries
