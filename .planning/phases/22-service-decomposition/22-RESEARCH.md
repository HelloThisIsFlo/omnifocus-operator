# Phase 22: Service Decomposition - Research

**Researched:** 2026-03-19
**Domain:** Python package refactoring, service layer decomposition
**Confidence:** HIGH

## Summary

Phase 22 is a pure structural refactoring: decompose the 669-line `service.py` into a `service/` package with four modules (service.py, resolve.py, domain.py, payload.py). The CONTEXT.md is exceptionally detailed -- it contains the full decomposition map, class signatures, dependency graph, reference code examples, and test strategy. This is not an exploratory phase; the decisions are locked and the code shapes are agreed.

The primary research task is verifying the existing codebase against the CONTEXT.md assumptions, identifying any discrepancies, and documenting the exact mechanics of each extraction.

**Primary recommendation:** Follow CONTEXT.md reference examples closely. The main risk is subtle behavioral drift during extraction -- the existing 109 service tests are the safety net.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **Package structure:** `service/__init__.py`, `service/service.py`, `service/resolve.py`, `service/domain.py`, `service/payload.py`
- **Module naming:** Action names (resolve, domain, payload), not categories
- **Class signatures:** `Resolver(repo)`, `DomainLogic(repo, resolver)`, `PayloadBuilder()` (no deps), `validate_task_name()` standalone
- **Dependency graph:** `Repository -> Resolver -> DomainLogic`. No cycles.
- **_Unset stays in orchestrator:** Domain methods receive clean Python values, never `_Unset`
- **Protocol conformance:** Both `OperatorService` and `ErrorOperatorService` must explicitly implement `Service` protocol
- **Logging:** Each module has own `logger = logging.getLogger("omnifocus_operator")`
- **Test strategy:** Mirror module structure, DomainLogic uses stub Resolver, PayloadBuilder tests are pure, Resolver uses real InMemoryRepository
- **Warning generation is domain logic:** All warning constants used from `domain.py`
- **`_to_utc_ts` lives in domain.py:** Collocated with no-op detection
- **Read delegation stays in service.py:** One-liner pass-throughs, no logic to extract
- **`__init__.py` is thin re-export only:** `from .service import OperatorService, ErrorOperatorService`

### Claude's Discretion

- Exact internal structure of `_all_fields_match` and `_is_empty_edit` in DomainLogic
- Whether `_add_if_set` and `_add_dates_if_set` in PayloadBuilder are methods or standalone helpers
- Stub Resolver implementation details for DomainLogic tests
- Exact logging message content (preserve existing messages where possible)
- Import organization within each module
- Whether `validate_task_name_if_set` (for edit_task name check) is a separate function or handled inline

### Deferred Ideas (OUT OF SCOPE)

None -- discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SVCR-01 | Validation logic extracted to dedicated module | `resolve.py` with `Resolver` class + `validate_task_name` standalone function. Current code: lines 125-128 (name validation), 497-543 (parent/tag resolution) |
| SVCR-02 | Domain logic extracted to dedicated module | `domain.py` with `DomainLogic` class. Current code: lines 434-470 (lifecycle), 472-495 (cycle), 545-646 (tag diff), 327-411 (no-op/empty-edit detection) |
| SVCR-03 | Format conversion extracted to dedicated module | `payload.py` with `PayloadBuilder` class. Current code: lines 143-161 (add payload), 213-264 (edit payload field extraction) |
| SVCR-04 | service.py converted to service/ package | `__init__.py` re-exports `OperatorService`, `ErrorOperatorService`. All existing import paths (`from omnifocus_operator.service import OperatorService`) preserved |
| SVCR-05 | Each extracted module independently testable | New test files: `test_service_resolve.py`, `test_service_domain.py`, `test_service_payload.py`. Each module can be imported and tested without OperatorService |

</phase_requirements>

## Architecture Patterns

### Target Package Structure

```
src/omnifocus_operator/service/
  __init__.py          # Re-exports: OperatorService, ErrorOperatorService
  service.py           # OperatorService (thin orchestrator), ErrorOperatorService
  resolve.py           # Resolver class, validate_task_name standalone
  domain.py            # DomainLogic class, _to_utc_ts helper
  payload.py           # PayloadBuilder class
```

### Mirrored Test Structure

```
tests/
  test_service.py              # EXISTING -- keep as integration tests (full pipeline)
  test_service_resolve.py      # NEW -- Resolver unit tests (real InMemoryRepo)
  test_service_domain.py       # NEW -- DomainLogic unit tests (stub Resolver)
  test_service_payload.py      # NEW -- PayloadBuilder unit tests (pure)
```

### Pattern: `repository/` Package as Precedent

The `repository/` package established the exact pattern to follow:
- `__init__.py` re-exports public symbols from submodules
- Protocol imported from contracts, not re-declared
- Implementations in their own files (bridge.py, hybrid.py, in_memory.py)
- `__all__` in each module for explicit exports

**Current `repository/__init__.py`:**
```python
from omnifocus_operator.contracts.protocols import Repository
from omnifocus_operator.repository.bridge import BridgeRepository
from omnifocus_operator.repository.factory import create_repository
from omnifocus_operator.repository.hybrid import HybridRepository

__all__ = ["BridgeRepository", "HybridRepository", "Repository", "create_repository"]
```

**Target `service/__init__.py`:**
```python
from omnifocus_operator.service.service import ErrorOperatorService, OperatorService

__all__ = ["ErrorOperatorService", "OperatorService"]
```

### Pattern: Protocol Conformance Declaration

The `Service` protocol in `contracts/protocols.py` (line 29) is NOT currently implemented by `OperatorService`. The protocol is `runtime_checkable` is NOT set (unlike `Repository`). This means conformance is structural only (mypy checks), not runtime-checkable with `isinstance()`.

**Current `OperatorService` declaration:** `class OperatorService:` (no protocol)
**Target:** `class OperatorService(Service):` (explicit protocol implementation)

**`ErrorOperatorService` complication:** Currently `class ErrorOperatorService(OperatorService):` and overrides `__getattr__` to raise on every access. The `(Service)` protocol base should be added here too, but since it inherits from `OperatorService`, it already structurally satisfies `Service` through its parent. The explicit declaration is documentation, not runtime behavior.

### Pattern: Dependency Injection (DDD Style)

Per user preference ("I come from Java DDD/CQRS world"):
- Classes with constructor injection, not bare functions
- Exception: `validate_task_name()` is standalone (no dependencies)
- Exception: `PayloadBuilder()` has no constructor args (pure transformation)

```
OperatorService
  |- self._repository: Repository
  |- self._resolver: Resolver(repository)
  |- self._domain: DomainLogic(repository, resolver)
  |- self._payload: PayloadBuilder()
```

## Extraction Map: Current Code -> Target Modules

### resolve.py Extractions

| Current Location | Target | Notes |
|-----------------|--------|-------|
| `OperatorService._resolve_parent` (L497-511) | `Resolver.resolve_parent` | Project-first resolution. Async. |
| `OperatorService._resolve_tags` (L513-543) | `Resolver.resolve_tags` + `Resolver._match_tag` | CONTEXT.md splits into two methods. Current code uses `repo.get_tag(name)` for ID fallback; CONTEXT.md iterates `all_data.tags` list. **Behavior-equivalent** -- both find tag by ID. |
| Name validation in `add_task` (L125-128) | `validate_task_name()` standalone | Message: "Task name is required" |
| Name validation in `edit_task` (L233-235) | `validate_task_name_if_set()` or inline | Message: "Task name cannot be empty". Claude's discretion. |

**Tag resolution ID fallback difference:**
- Current: `await self._repository.get_tag(name)` -- extra repo call
- CONTEXT.md: `next((t for t in tags if t.id == name), None)` -- uses already-fetched list
- Both are correct. The CONTEXT.md approach is slightly more efficient (avoids an extra repo call) since `resolve_tags` already fetched `all_data`.

### domain.py Extractions

| Current Location | Target | Notes |
|-----------------|--------|-------|
| `OperatorService._process_lifecycle` (L434-470) | `DomainLogic.process_lifecycle` | Already a clean method, nearly copy-paste |
| `OperatorService._check_cycle` (L472-495) | `DomainLogic.check_cycle` | Walks parent chain via `repo.get_all()` |
| `OperatorService._compute_tag_diff` (L545-646) | `DomainLogic.compute_tag_diff` + private helpers | Largest extraction. Uses `_Unset` internally -- must refactor to receive clean values |
| Empty edit detection (L327-346) | `DomainLogic._is_empty_edit` or `detect_early_return` | Checks `len(payload) == 1` |
| No-op detection (L349-410) | `DomainLogic._all_fields_match` + `detect_early_return` | Date comparison via `_to_utc_ts` |
| `_to_utc_ts` helper (L51-59) | Module-level in `domain.py` | Collocated with no-op detection |
| Status warning (L224-231) | `DomainLogic.check_completed_status` | Simple check: warn if editing completed/dropped without lifecycle |
| Move processing (L286-325) | `DomainLogic.process_move` + helpers | Container/anchor resolution, cycle detection |
| Same-container move warning (L381-395) | Inside `DomainLogic.detect_early_return` or `process_move` | Currently inside no-op detection block |

**Key refactoring for `_compute_tag_diff`:**
- Current code uses `_Unset` checks internally (L562-564: `has_replace`, `has_add`, `has_remove`)
- In the new design, the **orchestrator** determines which fields are set (via `_Unset` checks), then passes clean `TagAction` to `DomainLogic`
- The `DomainLogic.compute_tag_diff` still receives a `TagAction` object, but the `_Unset` checks happen inside it (it imports `_Unset` from `contracts.base`)
- Actually, looking at CONTEXT.md reference code (line 329), `has_replace` etc. are still checked inside `compute_tag_diff`. The `_Unset` isolation is about the **orchestrator** gating whether to call the method at all, not about removing all `_Unset` usage from domain.

**Clarification on `_Unset` in domain.py:**
- The CONTEXT.md principle says "Domain methods receive clean Python values (strings, lists, dicts), never `_Unset`"
- But `compute_tag_diff` receives a `TagAction` which has `_Unset` default values
- Resolution: The `_Unset` checks in `compute_tag_diff` are about the internal structure of `TagAction`, not about the method's own parameters. The orchestrator ensures the `TagAction` itself is not `_Unset` before calling. Within the `TagAction`, the `_Unset` checking is tag-action validation logic, not flow control.

### payload.py Extractions

| Current Location | Target | Notes |
|-----------------|--------|-------|
| Add payload construction (L143-161) | `PayloadBuilder.build_add` | kwargs dict -> `CreateTaskRepoPayload.model_validate()` |
| Edit payload field extraction (L213-264) | `PayloadBuilder.build_edit` | Simple fields, note null-clear, date serialization |
| `MoveToRepoPayload` wrapping (L415-418) | Inside `PayloadBuilder.build_edit` | `move_to` dict -> `MoveToRepoPayload(**move_data)` |

### service.py (Orchestrator) Remaining

After extraction, `OperatorService.edit_task` should read as:
1. Fetch task (verify exists)
2. Validate name if set
3. `_Unset` checks (flow control)
4. Call domain methods (lifecycle, status, tags, move)
5. Build payload
6. Detect no-op / early return
7. Delegate to repository
8. Return result

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Import path preservation | Custom `__init__.py` magic | Standard re-export pattern | `from .service import OperatorService` is the established pattern from `repository/` |
| Protocol conformance testing | Custom isinstance checks | mypy structural checking | `Service` protocol is not `@runtime_checkable` -- mypy handles it |
| No-op date comparison | String comparison | `_to_utc_ts` normalization | Timezone-aware datetime vs ISO string comparison is deceptively complex |

## Common Pitfalls

### Pitfall 1: Import Path Breakage
**What goes wrong:** After converting `service.py` to `service/`, `from omnifocus_operator.service import OperatorService` stops working.
**Why it happens:** Missing or incorrect `__init__.py` re-exports.
**How to avoid:** The `__init__.py` MUST re-export everything that was in the old `service.py.__all__`: `OperatorService`, `ErrorOperatorService`.
**Warning signs:** `ImportError` in server.py or test files. Run full test suite after creating the package.
**Consumers to verify:**
- `src/omnifocus_operator/server.py` -- 8 imports of `OperatorService`, 1 of `ErrorOperatorService`
- `tests/test_service.py` -- top-level import of `OperatorService`, 5 inline imports of `ErrorOperatorService`
- `tests/test_server.py` -- 6 imports of `OperatorService`

### Pitfall 2: Behavioral Drift in Tag Resolution
**What goes wrong:** The extracted `Resolver._match_tag` uses a list scan for ID fallback, but the current code uses `repo.get_tag(name)`. If `InMemoryRepository.get_tag` has different behavior than a list scan (e.g., it finds tags by ID that aren't in the snapshot's tag list), behavior could drift.
**How to avoid:** Check that `InMemoryRepository.get_tag` simply iterates `self._snapshot.tags` (confirmed: line 51-52 of in_memory.py does `next((t for t in self._snapshot.tags if t.id == tag_id), None)`). The behavior is equivalent.
**Warning signs:** Tag resolution tests fail after extraction.

### Pitfall 3: _Unset Leaking into Domain Methods
**What goes wrong:** A domain method receives an `_Unset` value instead of a clean Python type, causing unexpected behavior.
**Why it happens:** The orchestrator fails to check `_Unset` before calling a domain method.
**How to avoid:** The orchestrator gates all domain calls with `_Unset` checks. Domain methods should never import `_Unset` for parameter checking.
**Exception:** `compute_tag_diff` receives `TagAction` which internally uses `_Unset` for its fields. This is acceptable -- the `_Unset` is TagAction's internal concern, not the domain method's parameter concern. Similarly, `PayloadBuilder._add_if_set` and `_add_dates_if_set` check `_Unset` on command fields -- this is also acceptable since it's introspecting the command model's structure.

### Pitfall 4: Move Processing Split
**What goes wrong:** Move-related logic is split between domain.py (cycle detection, parent resolution) and the orchestrator (move_to dict construction), leading to confusion about where `MOVE_SAME_CONTAINER` warning is generated.
**How to avoid:** CONTEXT.md puts `process_move` entirely in `DomainLogic`. The same-container check is currently inside the no-op detection block (L381-395) -- it needs to move to either `process_move` or `detect_early_return` in domain.py.
**Current behavior:** Same-container detection happens AFTER payload construction, during no-op check. The CONTEXT.md `detect_early_return` method handles it.

### Pitfall 5: ErrorOperatorService Protocol Declaration
**What goes wrong:** Adding `Service` as a base class to `ErrorOperatorService` might trigger mypy errors because its `__getattr__` override doesn't match the protocol's method signatures.
**How to avoid:** `ErrorOperatorService` inherits from `OperatorService` which will implement `Service`. The `__getattr__` override raises before any protocol method body runs. mypy should be fine since the parent class satisfies the protocol.

### Pitfall 6: Test Splitting -- Moving vs Duplicating
**What goes wrong:** Tests are moved to new files but the integration coverage in `test_service.py` is lost, or tests are duplicated causing maintenance burden.
**How to avoid:** Follow the strategy: `test_service.py` keeps integration tests (full pipeline through OperatorService). New files test extracted modules in isolation. Tests that test specific validation/domain/payload logic can be moved; tests that verify end-to-end behavior stay.
**Decision point:** Some tests (e.g., `test_tag_replace`, `test_lifecycle_complete_available_task`) test both the orchestration AND the domain logic. These should STAY in `test_service.py` as integration tests. New unit tests in `test_service_domain.py` test the domain method directly.

## Code Examples

### service/__init__.py

```python
"""Service package -- agent-facing API surface for OmniFocus Operator."""

from omnifocus_operator.service.service import ErrorOperatorService, OperatorService

__all__ = ["ErrorOperatorService", "OperatorService"]
```

### Protocol Conformance Pattern

```python
# service/service.py
from omnifocus_operator.contracts.protocols import Service

class OperatorService(Service):
    """Service layer -- thin orchestration over resolve, domain, payload modules."""

    def __init__(self, repository: Repository) -> None:
        self._repository = repository
        self._resolver = Resolver(repository)
        self._domain = DomainLogic(repository, self._resolver)
        self._payload = PayloadBuilder()
```

### DomainLogic Test Fixture (Stub Resolver)

```python
# tests/test_service_domain.py
class StubResolver:
    """Returns pre-configured IDs. No InMemoryRepository dependency."""

    def __init__(self, tag_map: dict[str, str] | None = None):
        self._tag_map = tag_map or {}

    async def resolve_tags(self, names: list[str]) -> list[str]:
        return [self._tag_map[n] for n in names]

    async def resolve_parent(self, pid: str) -> str:
        return pid  # always succeeds
```

### PayloadBuilder Test (Pure, No Dependencies)

```python
# tests/test_service_payload.py
from omnifocus_operator.contracts.use_cases.create_task import CreateTaskCommand
from omnifocus_operator.service.payload import PayloadBuilder

def test_build_add_minimal():
    builder = PayloadBuilder()
    command = CreateTaskCommand(name="Buy milk")
    payload = builder.build_add(command, resolved_tag_ids=None)
    assert payload.name == "Buy milk"
    assert payload.parent is None
    assert payload.tag_ids is None
```

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (via uv run) |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run python -m pytest tests/test_service.py -x -q` |
| Full suite command | `uv run python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SVCR-01 | Validation extracted to resolve.py | unit | `uv run python -m pytest tests/test_service_resolve.py -x -q` | Wave 0 |
| SVCR-02 | Domain logic extracted to domain.py | unit | `uv run python -m pytest tests/test_service_domain.py -x -q` | Wave 0 |
| SVCR-03 | Format conversion extracted to payload.py | unit | `uv run python -m pytest tests/test_service_payload.py -x -q` | Wave 0 |
| SVCR-04 | Import paths preserved | integration | `uv run python -m pytest tests/test_service.py tests/test_server.py -x -q` | Existing |
| SVCR-05 | Modules independently testable | unit | `uv run python -m pytest tests/test_service_resolve.py tests/test_service_domain.py tests/test_service_payload.py -x -q` | Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run python -m pytest tests/test_service.py -x -q` (109 existing tests)
- **Per wave merge:** `uv run python -m pytest tests/ -x -q` (522 total tests)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_service_resolve.py` -- covers SVCR-01 (Resolver unit tests with real InMemoryRepo)
- [ ] `tests/test_service_domain.py` -- covers SVCR-02 (DomainLogic unit tests with stub Resolver)
- [ ] `tests/test_service_payload.py` -- covers SVCR-03 (PayloadBuilder pure unit tests)

## Key Numbers

| Metric | Value |
|--------|-------|
| Current `service.py` lines | 669 |
| Test classes in `test_service.py` | 5 (TestOperatorService, TestAddTask, TestEditTask, TestConstantMtimeSource, TestCreateBridge, TestErrorOperatorService) |
| Tests in `test_service.py` | 109 |
| Total project tests | 522 |
| Import consumers (src/) | server.py (8 OperatorService + 1 ErrorOperatorService) |
| Import consumers (tests/) | test_service.py (1+5), test_server.py (6) |
| Warning constants used | 11 (from warnings.py) |

## Open Questions

1. **`_Unset` in `compute_tag_diff`**
   - What we know: CONTEXT.md says domain methods don't receive `_Unset`, but `compute_tag_diff` receives `TagAction` which has `_Unset` defaults
   - Recommendation: This is acceptable. The orchestrator ensures the `TagAction` object itself is not `_Unset`. The `_Unset` inside TagAction fields is the model's internal concern. Document this nuance.

2. **`MOVE_SAME_CONTAINER` warning placement**
   - What we know: Currently inside the no-op detection block (L381-395). CONTEXT.md shows it in `detect_early_return`.
   - Recommendation: Keep in `detect_early_return` as CONTEXT.md specifies. The same-container check is part of "is this a no-op?" logic.

3. **Test splitting granularity**
   - What we know: 109 tests exist. Some test orchestration + domain together.
   - Recommendation: Don't move tests out of `test_service.py` aggressively. Add NEW unit tests for extracted modules. Only move tests that clearly test a single module's behavior (e.g., lifecycle processing, tag diff computation). Integration tests stay.

## Sources

### Primary (HIGH confidence)

- Current `service.py` (669 lines) -- direct source code analysis
- `contracts/protocols.py` -- Service protocol definition
- `contracts/use_cases/create_task.py`, `edit_task.py` -- command/payload/result types
- `contracts/common.py` -- TagAction, MoveAction types
- `contracts/base.py` -- `_Unset`, `CommandModel`
- `repository/__init__.py` -- package pattern precedent
- `repository/in_memory.py` -- InMemoryRepository used by tests
- `tests/test_service.py` (2119 lines, 109 tests) -- existing test structure
- `tests/conftest.py` -- test fixtures (make_snapshot, make_task_dict, etc.)

### Secondary (MEDIUM confidence)

- CONTEXT.md reference examples -- approved during discussion, target shapes
- `warnings.py` -- all warning constants used by domain logic

## Metadata

**Confidence breakdown:**
- Architecture: HIGH -- CONTEXT.md is exceptionally detailed with approved reference code
- Extraction map: HIGH -- direct analysis of current service.py against CONTEXT.md target
- Pitfalls: HIGH -- identified from direct code analysis and import tracing
- Test strategy: HIGH -- clear strategy from CONTEXT.md, verified against existing test structure

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (stable -- no external dependencies, pure internal refactoring)
