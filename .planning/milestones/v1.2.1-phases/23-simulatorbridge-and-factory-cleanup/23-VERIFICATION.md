---
phase: 23-simulatorbridge-and-factory-cleanup
verified: 2026-03-20T19:15:00Z
status: passed
score: 8/8 must-haves verified
re_verification: false
---

# Phase 23: SimulatorBridge and Factory Cleanup — Verification Report

**Phase Goal:** SimulatorBridge removed from production exports and bridge factory eliminated — repository factory creates RealBridge directly, PYTEST safety guard lives in RealBridge.__init__
**Verified:** 2026-03-20
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | RealBridge.__init__ raises RuntimeError when PYTEST_CURRENT_TEST is set | VERIFIED | `real.py:117` calls `_guard_automated_testing()`; `real.py:136` checks `type(self) is RealBridge and os.environ.get("PYTEST_CURRENT_TEST")`; test suite passes 592 tests including smoke + ipc_engine guard tests |
| 2 | SimulatorBridge.__init__ does NOT raise (type(self) is RealBridge bypasses) | VERIFIED | Runtime check confirmed: `SimulatorBridge(ipc_dir=Path(...))` succeeds when PYTEST_CURRENT_TEST is set; type guard excludes subclasses by design |
| 3 | bridge/factory.py no longer exists | VERIFIED | File absent — `ls src/omnifocus_operator/bridge/factory.py` returns no match |
| 4 | create_bridge is not importable from omnifocus_operator.bridge | VERIFIED | `from omnifocus_operator.bridge import create_bridge` raises ImportError; `create_bridge` absent from `__all__` (34-line `__init__.py` confirmed) |
| 5 | SimulatorBridge is not importable from omnifocus_operator.bridge | VERIFIED | `from omnifocus_operator.bridge import SimulatorBridge` raises ImportError; `SimulatorBridge` absent from `__all__` |
| 6 | Repository factory creates RealBridge directly without OMNIFOCUS_BRIDGE env var | VERIFIED | `repository/factory.py` contains `_create_real_bridge()` importing `from omnifocus_operator.bridge.real import DEFAULT_IPC_DIR, RealBridge`; only OMNIFOCUS_BRIDGE occurrences are docstring comment ("no longer used") and `OMNIFOCUS_BRIDGE_TIMEOUT` (legitimate config, different var) |
| 7 | All tests import SimulatorBridge via direct module path (bridge.simulator) only | VERIFIED | Every `from omnifocus_operator.bridge.simulator import SimulatorBridge` in tests uses direct path; the only `from omnifocus_operator.bridge import SimulatorBridge` in tests is inside a negative assertion block (wrapped in `pytest.raises(ImportError)`) |
| 8 | All existing tests pass after migration | VERIFIED | 592 passed, 5 warnings, 97% coverage — full suite green |

**Score:** 8/8 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/omnifocus_operator/bridge/real.py` | PYTEST safety guard via `_guard_automated_testing()` | VERIFIED | Lines 130-141: `_guard_automated_testing` defined; line 117: called as first line of `__init__`; `type(self) is RealBridge` check present at line 136 |
| `src/omnifocus_operator/repository/factory.py` | Simplified factory with `_create_real_bridge()` helper | VERIFIED | Lines 67-79: `_create_real_bridge()` defined; imports `RealBridge` directly from `bridge.real`; no `ConstantMtimeSource`, no `create_bridge`, no `OMNIFOCUS_BRIDGE` env var read |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/omnifocus_operator/bridge/real.py` | PYTEST_CURRENT_TEST env var | `_guard_automated_testing` in `__init__` | WIRED | `type(self) is RealBridge` check at line 136; called at line 117 |
| `src/omnifocus_operator/repository/factory.py` | `src/omnifocus_operator/bridge/real.py` | `_create_real_bridge` imports RealBridge directly | WIRED | Line 69: `from omnifocus_operator.bridge.real import DEFAULT_IPC_DIR, RealBridge`; both `_create_hybrid_repository` (line 102) and `_create_bridge_repository` (line 113) call `_create_real_bridge()` |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| INFRA-04 | 23-01-PLAN.md | SimulatorBridge not importable from `omnifocus_operator.bridge` | SATISFIED | `__init__.py` has no `SimulatorBridge` import or `__all__` entry; runtime ImportError confirmed |
| INFRA-05 | 23-01-PLAN.md | Tests import SimulatorBridge via direct module path only | SATISFIED | All test-file imports use `from omnifocus_operator.bridge.simulator import SimulatorBridge`; only exception is a negative-assertion test wrapped in `pytest.raises(ImportError)` |
| INFRA-06 | 23-01-PLAN.md | `OMNIFOCUS_BRIDGE` env var removed — repository factory creates RealBridge directly | SATISFIED | Factory imports `RealBridge` from `bridge.real`; `OMNIFOCUS_BRIDGE` only appears in a docstring comment saying it is no longer used |
| INFRA-07 | 23-01-PLAN.md | Bridge factory (`create_bridge`) removed — PYTEST guard moved to `RealBridge.__init__` | SATISFIED | `bridge/factory.py` deleted; `create_bridge` absent from package; `_guard_automated_testing()` on `RealBridge` confirmed |

No orphaned requirements — all four IDs claimed by plan 23-01 are accounted for.

---

### Anti-Patterns Found

None. Scanned all modified files:

- `src/omnifocus_operator/bridge/real.py` — clean implementation, no stubs or TODOs
- `src/omnifocus_operator/bridge/__init__.py` — clean 34-line file, no factory references
- `src/omnifocus_operator/repository/factory.py` — `_create_bridge_repository` correctly marked `# pragma: no cover — SAFE-01` (not a stub; UAT-tested only per project convention)
- Test files — all migrations complete, no `OMNIFOCUS_BRIDGE` references, `TestCreateBridge` and `TestFactory` deleted, `TestRealBridgeSafety` in place

---

### Human Verification Required

None. All observable truths are programmatically verifiable via static analysis and the test suite.

---

### Gaps Summary

No gaps. Phase goal fully achieved:

- PYTEST guard lives on `RealBridge._guard_automated_testing()` with `type(self) is RealBridge` bypass for subclasses
- `bridge/factory.py` deleted; `create_bridge` and `SimulatorBridge` removed from package exports
- Repository factory creates `RealBridge` directly via `_create_real_bridge()` helper; `OMNIFOCUS_BRIDGE` env var gone from production code
- All 592 tests pass at 97% coverage

---

_Verified: 2026-03-20_
_Verifier: Claude (gsd-verifier)_
