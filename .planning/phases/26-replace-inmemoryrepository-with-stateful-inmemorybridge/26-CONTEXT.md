# Phase 26: Replace InMemoryRepository with stateful InMemoryBridge - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

InMemoryRepository deleted. InMemoryBridge becomes stateful — handles `add_task`/`edit_task` commands by mutating in-memory state. Write tests exercise the real serialization path (`BridgeWriteMixin` → `model_dump(by_alias=True)` → bridge) instead of an independent simulation that can drift. No new tools, no behavioral changes — pure test infrastructure.

</domain>

<decisions>
## Implementation Decisions

### State format
- **D-01:** Dict-native — InMemoryBridge stores entities as camelCase dicts internally (matching real bridge format)
- **D-02:** Seeded with `make_snapshot_dict()` — same factory already used today, produces camelCase dicts
- **D-03:** `send_command("get_all")` reassembles the dict from internal `_tasks`, `_projects`, `_tags`, etc. lists
- **D-04:** No Pydantic models inside the bridge — the bridge speaks dicts, stores dicts, returns dicts

### Write simulation fidelity
- **D-05:** Full behavioral parity with the real bridge — InMemoryBridge must simulate OmniFocus faithfully enough that tests are reliable
- **D-06:** Minimal implementation complexity, but faithful behavior — don't over-engineer, but don't cut corners on correctness
- **D-07:** InMemoryRepository's current write logic migrates into InMemoryBridge, adapted from model-level to dict-level operations
- **D-08:** add_task: generates synthetic ID, URL, timestamps, computed fields (in_inbox, effectiveFlagged, etc.), appends to internal tasks list
- **D-09:** edit_task: finds task by ID, applies field updates, tag operations (remove then add), lifecycle (complete/drop), move operations — all on camelCase dicts
- **D-10:** Phase 27 golden master will validate this parity claim — Phase 26 builds it right, Phase 27 proves it

### Test migration wiring
- **D-11:** Pytest fixture composition — `bridge` fixture creates InMemoryBridge, `repo` fixture takes `bridge` fixture and creates BridgeRepository around it
- **D-12:** Tests inject whichever fixtures they need — `repo` only, or both `repo` and `bridge` — standard pytest pattern, no tuple unpacking or factory functions
- **D-13:** ConstantMtimeSource wired into the repo fixture — invisible to tests that don't care about caching behavior

### Claude's Discretion
- Whether existing call tracking (`_calls`, `call_count`) and error injection (`set_error`/`clear_error`) survive unchanged
- How to dispatch operations in `send_command` (if/elif vs registry)
- Error handling for unknown operations or missing task IDs in edit
- Whether `make_snapshot()` (Pydantic version) is kept alongside `make_snapshot_dict()` for tests that need models directly
- Exact field defaults and computed field logic for add_task simulation
- Migration order across the 9 test files (~147 InMemoryRepository imports)
- Whether `changed_fields()` (from Phase 25) is used inside InMemoryBridge's write handlers

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Current InMemoryBridge (to be rewritten)
- `tests/doubles/bridge.py` — Current static-data implementation; call tracking and error injection patterns to preserve
- `tests/doubles/__init__.py` — Current exports (InMemoryBridge, BridgeCall, InMemoryRepository, ConstantMtimeSource, SimulatorBridge)

### InMemoryRepository (to be deleted — migrate logic first)
- `tests/doubles/repository.py` — Full write simulation: add_task (~30 LOC), edit_task (~60 LOC), field mapping, tag operations, lifecycle, move. This logic migrates to InMemoryBridge adapted for dict-level operations

### Real serialization path (tests must exercise this)
- `src/omnifocus_operator/repository/bridge_write_mixin.py` — `_send_to_bridge`: `model_dump(by_alias=True, exclude_unset=True)` → bridge
- `src/omnifocus_operator/repository/bridge.py` — BridgeRepository: write → invalidate cache → re-read on next get_all

### Bridge contract
- `src/omnifocus_operator/contracts/protocols.py` — Bridge protocol: `send_command(operation, params) -> dict`

### Test factories
- `tests/conftest.py` — `make_snapshot_dict()`, `make_snapshot()`, `make_task_dict()`, etc.

### Requirements
- `.planning/REQUIREMENTS.md` — INFRA-10, INFRA-11, INFRA-12

### Prior phase decisions affecting this phase
- Phase 22 CONTEXT: DomainLogic tests use StubResolver/StubRepo (already off InMemoryRepository)
- Phase 25 CONTEXT (D-16): `changed_fields()` available for InMemoryBridge write handlers

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `make_snapshot_dict()` / `make_task_dict()`: camelCase dict factories — direct seeding for InMemoryBridge
- `BridgeCall` dataclass: call tracking record — reused unchanged
- `ConstantMtimeSource`: test mtime source — wired into repo fixture
- `changed_fields()` on CommandModel: potential use in InMemoryBridge write handlers

### Established Patterns
- `BridgeWriteMixin._send_to_bridge()`: the serialization path all write tests will now exercise
- BridgeRepository cache invalidation: `_cached = None` after write, re-reads on next `get_all`
- Fixture composition in pytest: `repo` fixture depends on `bridge` fixture, tests inject what they need

### Integration Points
- `tests/doubles/bridge.py`: InMemoryBridge rewritten to be stateful
- `tests/doubles/repository.py`: Deleted after logic migrated
- `tests/doubles/__init__.py`: Remove InMemoryRepository export
- `tests/conftest.py`: Add `bridge`, `repo` fixtures (or per-test-file conftest)
- 9 test files with ~147 InMemoryRepository imports: migrate to fixture-based wiring

</code_context>

<deferred>
## Deferred Ideas

- **Golden master validation** — Phase 27 captures RealBridge behavior via UAT and proves InMemoryBridge matches. Phase 26 builds faithfully; Phase 27 proves it.

</deferred>

---

*Phase: 26-replace-inmemoryrepository-with-stateful-inmemorybridge*
*Context gathered: 2026-03-21*
