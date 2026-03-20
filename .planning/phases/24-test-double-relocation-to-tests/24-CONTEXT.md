# Phase 24: Test Double Relocation - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Move all test double modules from `src/omnifocus_operator/` to `tests/doubles/` so production code structurally cannot import them. Five test double classes across four source files relocated, all test imports updated, negative import tests added. No behavioral changes — pure file relocation.

</domain>

<decisions>
## Implementation Decisions

### Directory layout
- **D-01:** Dedicated `tests/doubles/` package (flat, not mirroring src/ structure)
- **D-02:** Four modules: `bridge.py` (InMemoryBridge, BridgeCall), `simulator.py` (SimulatorBridge), `mtime.py` (ConstantMtimeSource), `repository.py` (InMemoryRepository)
- **D-03:** Re-export all doubles from `tests/doubles/__init__.py` for convenience — `from tests.doubles import InMemoryBridge` works
- **D-04:** conftest.py factory functions (make_task_dict, make_snapshot, etc.) stay in conftest.py — they're pytest fixtures, not test doubles

### Mixed-file handling (mtime.py)
- **D-05:** Surgical extract: delete `ConstantMtimeSource` from `src/omnifocus_operator/bridge/mtime.py`, recreate in `tests/doubles/mtime.py`
- **D-06:** Production `mtime.py` keeps `MtimeSource` protocol and `FileMtimeSource` only
- **D-07:** Both `ConstantMtimeSource` (in tests/doubles) and `FileMtimeSource` (in src/) must explicitly implement `MtimeSource` protocol — add protocol implementation if not already present
- **D-08:** Remove `ConstantMtimeSource` from `mtime.py`'s `__all__`

### Enforcement strategy
- **D-09:** Structural enforcement only — Python's import system prevents src/ from importing tests/ (tests/ is not on sys.path for installed packages). No CI grep needed
- **D-10:** Negative import tests proving old paths are broken — same pattern as Phase 19 (InMemoryBridge) and Phase 23 (SimulatorBridge). Test that `from omnifocus_operator.bridge.in_memory import InMemoryBridge` raises ImportError, etc.

### Claude's Discretion
- Commit strategy (single vs multi-commit)
- Order of operations (move files first vs update imports first)
- Exact cleanup of `__all__` lists and docstrings referencing test doubles in production code
- Whether to consolidate negative import tests in one file or distribute across existing test files

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Test double modules (to be relocated)
- `src/omnifocus_operator/bridge/in_memory.py` — InMemoryBridge + BridgeCall (70 lines, move wholesale)
- `src/omnifocus_operator/bridge/simulator.py` — SimulatorBridge (28 lines, move wholesale)
- `src/omnifocus_operator/bridge/mtime.py` — ConstantMtimeSource to extract (lines 52-62); MtimeSource + FileMtimeSource stay
- `src/omnifocus_operator/repository/in_memory.py` — InMemoryRepository (174 lines, move wholesale)

### Production imports to verify clean
- `src/omnifocus_operator/bridge/__init__.py` — Currently exports MtimeSource, FileMtimeSource (no test doubles after Phase 19/23)
- `src/omnifocus_operator/repository/factory.py` — Imports FileMtimeSource, MtimeSource (production only)
- `src/omnifocus_operator/repository/bridge.py` — TYPE_CHECKING import of MtimeSource

### Test files that need import migration (10 files, 332 occurrences)
- `tests/test_bridge.py` — InMemoryBridge, BridgeCall
- `tests/test_repository.py` — InMemoryBridge, InMemoryRepository
- `tests/test_service.py` — ConstantMtimeSource, InMemoryRepository
- `tests/test_server.py` — InMemoryBridge, ConstantMtimeSource, InMemoryRepository
- `tests/test_hybrid_repository.py` — InMemoryBridge
- `tests/test_ipc_engine.py` — SimulatorBridge
- `tests/test_simulator_bridge.py` — SimulatorBridge, InMemoryRepository
- `tests/test_simulator_integration.py` — SimulatorBridge
- `tests/test_service_resolve.py` — InMemoryRepository
- `tests/test_service_domain.py` — references (check exact imports)

### Phase precedents
- `.planning/phases/19-inmemorybridge-export-cleanup/19-CONTEXT.md` — Clean-break pattern, negative import tests
- `.planning/phases/23-simulatorbridge-and-factory-cleanup/23-CONTEXT.md` — D-19 defines Phase 24 as "physical relocation"

### Requirements
- `.planning/REQUIREMENTS.md` — INFRA-08 (test doubles physically in tests/), INFRA-09 (no src/ imports from tests/)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 19/23 negative import test pattern: `pytest.raises(ImportError)` with inline import
- `tests/conftest.py` factory functions (make_task_dict, make_snapshot) — stay in place, not affected

### Established Patterns
- Package `__init__.py` files use explicit `__all__` lists — update mtime.py's `__all__` after ConstantMtimeSource removal
- Direct module imports established in Phase 19/23 — all test files already use `from omnifocus_operator.bridge.in_memory import ...` (not package-level)
- Re-exports from `__init__.py` are fine for test infrastructure (unlike production exports which were cleaned up)

### Integration Points
- `src/omnifocus_operator/bridge/mtime.py` is the only mixed file — all others are pure test doubles
- `tests/conftest.py` does NOT import any test doubles — no conftest changes needed
- `simulator/__main__.py` references SimulatorBridge but is test infrastructure itself (check if import path needs updating)

</code_context>

<specifics>
## Specific Ideas

- "Both ConstantMtimeSource and FileMtimeSource should explicitly implement MtimeSource protocol" — user specifically requested protocol conformance on both sides of the split
- Flat `tests/doubles/` package preferred over mirroring src/ structure — simpler, all doubles in one place

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 24-test-double-relocation-to-tests*
*Context gathered: 2026-03-20*
