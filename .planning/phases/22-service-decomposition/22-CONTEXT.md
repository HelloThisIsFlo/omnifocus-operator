# Phase 22: Service Decomposition - Context

**Gathered:** 2026-03-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Convert `service.py` (669 lines) into a `service/` package. Extract validation, domain logic, and format conversion into dedicated, independently testable modules. The orchestrator (OperatorService) becomes pure orchestration — a thin sequence of validate, resolve, domain, build, delegate steps. No new tools, no behavioral changes — pure internal quality.

Both OperatorService and ErrorOperatorService must explicitly implement the Service protocol from `contracts/protocols.py`.

</domain>

<decisions>
## Implementation Decisions

### Package structure

```
service/
├── __init__.py     # from .service import OperatorService, ErrorOperatorService
├── service.py      # OperatorService, ErrorOperatorService (thin orchestration + read delegation)
├── resolve.py      # Resolver class + standalone validate_task_name
├── domain.py       # DomainLogic class (lifecycle, tags, cycle, no-op, move, warnings)
└── payload.py      # PayloadBuilder class (typed repo payload construction)
```

- `service.py` inside the package (not `__init__.py`) — consistent with `repository/` pattern where implementations live in their own files
- `__init__.py` is a thin re-export only

### Module naming — action names, not categories

- `resolve.py` — "take raw user input, verify and normalize it" (not "validation.py")
- `domain.py` — "apply business rules" (lifecycle, tag diff, cycle detection, no-op)
- `payload.py` — "assemble typed RepoPayloads" (not "conversion.py")
- Named after what the module DOES, not abstract categories — resolves the overlap between validation and conversion

### Decomposition map

| Module | Functions |
|---|---|
| **resolve.py** | `Resolver.resolve_parent`, `Resolver.resolve_tags`, `validate_task_name` (standalone) |
| **domain.py** | `DomainLogic.process_lifecycle`, `DomainLogic.compute_tag_diff`, `DomainLogic.check_cycle`, `DomainLogic.detect_noop`, `DomainLogic.check_completed_status`, `DomainLogic.process_move`, `_to_utc_ts` (helper) |
| **payload.py** | `PayloadBuilder.build_add`, `PayloadBuilder.build_edit` |
| **service.py** | `OperatorService.add_task`, `OperatorService.edit_task` (orchestration), read delegation (`get_all_data`, `get_task`, `get_project`, `get_tag`), `ErrorOperatorService` |

### Guiding principles for decomposition

- **All warning generation is domain logic** — lifecycle warnings, tag no-op warnings, completed/dropped status warnings, no-op detection all live in domain.py
- **Cycle detection is domain** — it walks the parent-child graph with domain semantics, not basic input validation
- **`_to_utc_ts` lives in domain** — it's a helper solely for no-op detection (semantic equivalence checking), collocated with its purpose
- **Read delegation stays in service** — one-liner pass-throughs, no logic to extract

### Function signatures — classes with dependency injection

- `Resolver(repo: Repository)` — receives repo for parent/tag resolution
- `DomainLogic(repo: Repository, resolver: Resolver)` — receives both (repo for check_cycle graph walking, resolver for tag diff resolution)
- `PayloadBuilder()` — no dependencies, pure transformation
- `validate_task_name(name)` — standalone function, no dependencies

Dependency graph: `Repository → Resolver → DomainLogic`. No cycles.

Service constructor:
```python
def __init__(self, repository: Repository):
    self._repository = repository
    self._resolver = Resolver(repository)
    self._domain = DomainLogic(repository, self._resolver)
    self._payload = PayloadBuilder()
```

### Payload building returns fully typed payloads

- `PayloadBuilder.build_add(command, resolved_tag_ids) → CreateTaskRepoPayload`
- `PayloadBuilder.build_edit(command, lifecycle, add_tag_ids, remove_tag_ids, move_to) → EditTaskRepoPayload`
- Conversion module owns the full dict → typed model transformation, including MoveToRepoPayload wrapping
- Orchestrator receives a ready-to-send payload — no further assembly required

### _Unset checks stay in the orchestrator

- `_Unset` is a service-layer concern (flow control: "should I call this domain method?")
- Domain methods receive clean Python values (strings, lists, dicts), never `_Unset`
- This keeps domain methods simple to call and test — pass a string, not a command object

### Orchestrator style — minimal delegation recipe

`add_task` reads as: validate → resolve → build → delegate → wrap result (~15 lines)

`edit_task` reads as: fetch task → _Unset checks → domain calls → build payload → detect no-op → delegate → wrap result (~35 lines). Warnings collected throughout, checked once at end.

### Domain internals — well-decomposed, not monolithic

Each public method on DomainLogic delegates to focused private helpers:

- `compute_tag_diff` → `_apply_add`, `_apply_remove`, `_apply_replace`, `_apply_add_remove`
- `detect_noop` → `_is_empty_edit`, `_all_fields_match`
- `process_move` → `_extract_move_target`, `_process_container_move`, `_process_anchor_move`

Section separators in the class for visual grouping: Lifecycle, Tags, Cycle detection, No-op detection, Status warnings, Move processing.

### Protocol conformance

- `OperatorService` and `ErrorOperatorService` must explicitly declare they implement the Service protocol from `contracts/protocols.py`
- Same pattern Phase 21 established for repositories

### Logging

- Each module has its own `logger = logging.getLogger("omnifocus_operator")`
- Logging stays close to the logic — Resolver logs resolution attempts, DomainLogic logs lifecycle decisions, etc.

### Test strategy

```
tests/
├── test_service.py              # EXISTING — stays as integration (full pipeline through OperatorService)
├── test_service_resolve.py      # NEW — Resolver unit tests (real InMemoryRepo)
├── test_service_domain.py       # NEW — DomainLogic unit tests (stub Resolver, no InMemoryRepo dependency)
└── test_service_payload.py      # NEW — PayloadBuilder unit tests (pure, no dependencies)
```

- Mirror module structure: one test file per extracted module
- Move existing test_service.py tests that specifically test extracted logic into the new files
- test_service.py keeps only integration tests (full add_task/edit_task flows)
- DomainLogic tests use stub Resolver (not InMemoryRepository) — avoids dependency on InMemoryRepo which is being replaced in Phase 26
- Resolver tests use real InMemoryRepository (will naturally migrate in Phase 26)
- PayloadBuilder tests are pure data transformation — no repo, no stubs

### Claude's Discretion

- Exact internal structure of `_all_fields_match` in DomainLogic (field comparison implementation)
- Whether `_add_if_set` and `_add_dates_if_set` in PayloadBuilder are methods or standalone helpers
- Stub Resolver implementation details for DomainLogic tests
- Exact logging message content (preserve existing messages where possible)
- Import organization within each module

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & contracts
- `docs/architecture.md` — Model Taxonomy section, protocol signatures, write pipeline flow
- `src/omnifocus_operator/contracts/protocols.py` — Service, Repository, Bridge protocols (Service protocol must be implemented)
- `src/omnifocus_operator/contracts/use_cases/create_task.py` — CreateTaskCommand, CreateTaskRepoPayload, CreateTaskResult
- `src/omnifocus_operator/contracts/use_cases/edit_task.py` — EditTaskCommand, EditTaskRepoPayload, MoveToRepoPayload, EditTaskResult

### Current service (the file being decomposed)
- `src/omnifocus_operator/service.py` — All 669 lines being split into the package

### Requirements
- `.planning/REQUIREMENTS.md` — SVCR-01 through SVCR-05 definitions

### Prior phase context
- `.planning/phases/20-model-taxonomy/20-CONTEXT.md` — Naming convention, contracts/ package, typed payloads
- `.planning/phases/21-write-pipeline-unification/21-CONTEXT.md` — Unified pipeline pattern, BridgeWriteMixin, exclude_unset standardization

### Future dependency (informational)
- `.planning/todos/pending/2026-03-19-replace-inmemoryrepository-with-stateful-inmemorybridge.md` — Phase 26 will replace InMemoryRepository; new DomainLogic tests should not depend on it

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `contracts/protocols.py`: Service protocol exists but OperatorService doesn't declare conformance — this phase fixes that
- `contracts/base.py`: `_Unset`, `UNSET` sentinel — used by orchestrator for flow control, not passed to domain/resolve modules
- `warnings.py`: Warning string constants — used by domain.py for all warning generation
- `BridgeWriteMixin` (repository/): Established pattern for extracting shared functionality into a mixin — similar decomposition approach

### Established Patterns
- `repository/` package: implementations in their own files (hybrid.py, bridge.py), `__init__.py` re-exports — same pattern for service/
- Phase 21 kwargs dict → `model_validate()` pattern — PayloadBuilder follows this for both add and edit
- `@_ensures_write_through` decorator on HybridRepository — unaffected by this phase

### Integration Points
- `server.py`: imports `OperatorService`, `ErrorOperatorService` from `omnifocus_operator.service` — import path preserved via `__init__.py` re-export
- `contracts/protocols.py`: Service protocol — both service classes must declare conformance
- `test_service.py`: existing tests need splitting into module-specific test files

</code_context>

<specifics>
## Specific Ideas

- "I come from the Java world with DDD and CQRS" — classes with dependency injection preferred over bare functions with passed parameters
- "I would love to see how you plan on building the domain logic" — domain.py should have clear visual grouping (section separators) and well-decomposed private helpers
- "This method shouldn't be just one block of unreadable code" — public domain methods delegate to focused private helpers (e.g., `process_move` → `_extract_move_target`, `_process_container_move`, `_process_anchor_move`)
- "As long as we can keep the service small" — the orchestrator must be visibly thin after extraction; that's the whole point
- Service protocol conformance: "it's quite a big deal" — explicitly declaring protocol implementation, not just structural typing

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 22-service-decomposition*
*Context gathered: 2026-03-19*
