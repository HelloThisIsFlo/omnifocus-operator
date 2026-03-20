# Phase 23: SimulatorBridge and Factory Cleanup - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove SimulatorBridge from production package exports, eliminate the bridge factory (`create_bridge` + `bridge/factory.py`) entirely, and move the PYTEST safety guard into `RealBridge.__init__`. After this phase, production code always creates RealBridge directly — no factory indirection, no `OMNIFOCUS_BRIDGE` env var. SimulatorBridge module stays in `src/` (physical relocation is Phase 24).

</domain>

<decisions>
## Implementation Decisions

### PYTEST guard migration
- **D-01:** Guard moves to a private method `_guard_automated_testing()` on RealBridge
- **D-02:** Uses `type(self) is RealBridge` check — subclasses (SimulatorBridge) auto-bypass without any opt-out machinery
- **D-03:** Called as first line of `RealBridge.__init__` — clean init, guard logic extracted to its own method

### Repository factory simplification
- **D-04:** Both `_create_hybrid_repository()` and `_create_bridge_repository()` share a private `_create_real_bridge()` helper in `repository/factory.py`
- **D-05:** `_create_real_bridge()` imports and instantiates RealBridge directly — reads `OMNIFOCUS_IPC_DIR` and `OMNIFOCUS_BRIDGE_TIMEOUT` env vars inline
- **D-06:** `OMNIFOCUS_BRIDGE` env var removed from all production code — no bridge type switching in production
- **D-07:** `OMNIFOCUS_IPC_DIR` and `OMNIFOCUS_BRIDGE_TIMEOUT` env vars stay — legitimate production config
- **D-08:** `_create_bridge_repository()` always uses `FileMtimeSource` — no `ConstantMtimeSource` path in production. Tests that need ConstantMtimeSource construct BridgeRepository directly

### Export cleanup
- **D-09:** Remove `SimulatorBridge` from `bridge/__init__.py` imports and `__all__` — same clean-break pattern as Phase 19
- **D-10:** Remove `create_bridge` from `bridge/__init__.py` imports and `__all__` — factory module is deleted
- **D-11:** Delete `bridge/factory.py` entirely

### Test cleanup
- **D-12:** Delete all `create_bridge()` tests — factory no longer exists
- **D-13:** Adapt PYTEST guard tests to test `RealBridge()` directly instead of `create_bridge("real")`
- **D-14:** Keep adapted guard test in `test_ipc_engine.py` (rename TestFactorySafety -> TestRealBridgeSafety)
- **D-15:** Update smoke test in `test_smoke.py` to test `RealBridge()` directly
- **D-16:** Add negative import test: assert `from omnifocus_operator.bridge import SimulatorBridge` raises ImportError (in `test_simulator_bridge.py`)
- **D-17:** Add negative import test: assert `from omnifocus_operator.bridge import create_bridge` raises ImportError (in `test_simulator_bridge.py`)
- **D-18:** Tests that monkeypatched `create_bridge` construct test dependencies directly instead — no factory mocking

### Phase boundary with Phase 24
- **D-19:** Phase 23 is logical cleanup (exports + factory deletion). Phase 24 is physical relocation (move test double modules from `src/` to `tests/`). Kept separate so Phase 23 can be verified independently before file moves.

### Claude's Discretion
- Commit strategy (single vs multi-commit)
- Order of operations within the phase
- Exact error message wording for PYTEST guard
- Whether to update docstrings referencing bridge factory

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Bridge factory (to be deleted)
- `src/omnifocus_operator/bridge/factory.py` — The entire file is being deleted. Contains `create_bridge()` with "simulator" + "real" cases and PYTEST guard
- `src/omnifocus_operator/bridge/__init__.py` — Lines 9, 20, 34-35: SimulatorBridge and create_bridge exports to remove

### Bridge implementations
- `src/omnifocus_operator/bridge/real.py` — RealBridge class where `_guard_automated_testing()` will be added
- `src/omnifocus_operator/bridge/simulator.py` — SimulatorBridge (RealBridge subclass with no-op trigger) — stays in src/ but removed from exports

### Repository factory (to be simplified)
- `src/omnifocus_operator/repository/factory.py` — Lines 84-87: `create_bridge` import + OMNIFOCUS_BRIDGE usage to replace with inline RealBridge. Lines 94-99: same in `_create_bridge_repository`. Line 102: simulator MtimeSource path to remove

### Test files to update
- `tests/test_simulator_bridge.py` — Lines 120-165: factory tests to delete. Lines 171-183: export tests to flip to negative assertions. Lines 233, 261, 292: monkeypatched create_bridge to replace with direct construction
- `tests/test_ipc_engine.py` — Lines 566-590: TestFactorySafety to adapt to RealBridge.__init__. Lines 602-608: SimulatorBridge export test to update
- `tests/test_smoke.py` — Lines 25-30: SAFE-01 guard test to adapt
- `tests/test_service.py` — Lines 2044-2067: create_bridge tests to delete or adapt

### Phase 19 precedent
- `.planning/phases/19-inmemorybridge-export-cleanup/19-CONTEXT.md` — Same pattern: clean break, no backward compat, direct module imports

### Requirements
- `.planning/REQUIREMENTS.md` — INFRA-04, INFRA-05, INFRA-06, INFRA-07 definitions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 19 established the pattern: remove from `__all__`, remove import line, migrate test imports to direct module paths
- `test_simulator_bridge.py` already uses `from omnifocus_operator.bridge.simulator import SimulatorBridge` in unit tests — only factory/export tests need changing

### Established Patterns
- Package `__init__.py` files use explicit `__all__` lists — remove entries from both import and `__all__`
- Bridge factory uses `match/case` — entire module deleted, not just a case
- Repository factory uses lazy imports inside helper functions — new `_create_real_bridge()` follows same pattern
- Phase 22 established StubResolver/StubRepo pattern for test isolation — Phase 23 continues this trajectory (tests construct dependencies directly)

### Integration Points
- `repository/factory.py` is the ONLY production consumer of `create_bridge()` — once it's updated, no production code references the bridge factory
- `bridge/__init__.py` re-exports are the ONLY way to import SimulatorBridge from the package — removing them is sufficient
- `test_service.py:19` imports `create_bridge` from bridge package — needs update

</code_context>

<specifics>
## Specific Ideas

- PYTEST guard as private method (`_guard_automated_testing`) keeps RealBridge.__init__ clean — user specifically wanted to avoid cluttering init
- `type(self) is RealBridge` is the bypass mechanism — no class attributes, no __init_subclass__ magic
- `_create_real_bridge()` helper in repo factory avoids duplicating env-var reading between hybrid and bridge-only paths
- Negative import tests mirror Phase 19's approach — prove the export was actually removed

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 23-simulatorbridge-and-factory-cleanup*
*Context gathered: 2026-03-20*
