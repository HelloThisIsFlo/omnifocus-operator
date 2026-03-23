# Phase 23: SimulatorBridge and Factory Cleanup - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-20
**Phase:** 23-simulatorbridge-and-factory-cleanup
**Areas discussed:** PYTEST guard migration, Repository factory simplification, Test cleanup scope, Phase 23 vs 24 boundary

---

## PYTEST Guard Migration

### Guard bypass mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| type(self) check | Guard only fires when `type(self) is RealBridge` exactly — subclasses pass through | |
| Class attribute opt-out | `_pytest_guard = True` on RealBridge, `False` on SimulatorBridge | |
| __init_subclass__ | Register 'safe' subclasses via Python's __init_subclass__ | |

**User's choice:** type(self) check — but extracted to a utility method to avoid cluttering __init__

### Guard extraction

| Option | Description | Selected |
|--------|-------------|----------|
| Private method on RealBridge | `_guard_automated_testing()` called as first line of __init__ | ✓ |
| Module-level function | Free function taking instance, less discoverable | |
| Class method guard | Classmethod checking against cls, unusual pattern | |

**User's choice:** Private method on RealBridge
**Notes:** User specifically wanted to avoid cluttering __init__ with inline guard logic

---

## Repository Factory Simplification

### RealBridge creation approach

| Option | Description | Selected |
|--------|-------------|----------|
| Inline RealBridge creation | Repo factory imports and instantiates RealBridge directly | ✓ |
| RealBridge.from_env() classmethod | Classmethod on RealBridge reads env vars | |

**User's choice:** Inline RealBridge creation
**Notes:** User confirmed this makes sense because simulator is only used during tests. Requested a shared helper method since both hybrid and bridge-only paths need it.

### MtimeSource in production

| Option | Description | Selected |
|--------|-------------|----------|
| Always FileMtimeSource | No ConstantMtimeSource path in production | ✓ |
| Keep ConstantMtimeSource path | Retain simulator mtime path | |
| You decide | Claude picks | |

**User's choice:** Always FileMtimeSource

### Env var retention

| Option | Description | Selected |
|--------|-------------|----------|
| Keep both IPC_DIR + TIMEOUT | Legitimate production config | ✓ |
| Keep IPC_DIR, remove TIMEOUT | Hardcode timeout | |
| You decide | Claude picks | |

**User's choice:** Keep both

### Helper location

| Option | Description | Selected |
|--------|-------------|----------|
| In repository/factory.py | Private to only consumer, RealBridge stays pure | ✓ |
| In bridge/real.py | Co-located but mixes config with implementation | |

**User's choice:** In repository/factory.py

---

## Test Cleanup Scope

### Factory/export test handling

| Option | Description | Selected |
|--------|-------------|----------|
| Delete factory tests, adapt guard tests | Delete create_bridge() tests, adapt PYTEST guard to test RealBridge.__init__ | ✓ |
| Delete everything, rely on coverage | No explicit guard test | |
| You decide | Claude determines per-test | |

**User's choice:** Delete factory tests, adapt guard tests

### Negative import test

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, add negative import test | Assert ImportError for SimulatorBridge package import | ✓ |
| No, just delete export tests | Removal verified by code review | |
| You decide | Claude decides | |

**User's choice:** Yes, add negative import tests (for both SimulatorBridge and create_bridge)

### Monkeypatched factory tests

| Option | Description | Selected |
|--------|-------------|----------|
| Construct directly | Tests instantiate and pass in dependencies | ✓ |
| Mock _create_real_bridge | Replace monkeypatch target | |
| You decide | Claude adapts individually | |

**User's choice:** Construct directly

### Negative import test location

| Option | Description | Selected |
|--------|-------------|----------|
| Same file — test_simulator_bridge.py | Both SimulatorBridge and create_bridge negative tests together | ✓ |
| Separate files | Split by concern | |
| You decide | Claude places | |

**User's choice:** Same file — test_simulator_bridge.py

### PYTEST guard test location

| Option | Description | Selected |
|--------|-------------|----------|
| Keep in test_ipc_engine.py | Rename TestFactorySafety -> TestRealBridgeSafety, minimal churn | ✓ |
| Move to test_simulator_bridge.py | Group bridge safety tests | |
| You decide | Claude decides | |

**User's choice:** Keep in test_ipc_engine.py

### Smoke test

| Option | Description | Selected |
|--------|-------------|----------|
| Update smoke test too | Change to test RealBridge() directly | ✓ |
| Remove, covered by test_ipc_engine | One test is enough | |
| You decide | Claude decides | |

**User's choice:** Update smoke test too

---

## Phase 23 vs 24 Boundary

### Phase split

| Option | Description | Selected |
|--------|-------------|----------|
| Keep separate | Phase 23 = logical (exports + factory). Phase 24 = physical (file relocation) | ✓ |
| Merge into one phase | Both in Phase 23 | |
| Keep separate but reorder | Relocate first, then clean exports | |

**User's choice:** Keep separate
**Notes:** Verified independently — Phase 23 proves decoupling, Phase 24 does the physical move

### create_bridge export removal

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, obviously | If factory.py is deleted, import would break | ✓ |
| You decide | Claude handles | |

**User's choice:** Yes, obviously

---

## Claude's Discretion

- Commit strategy (single vs multi-commit)
- Order of operations within the phase
- Exact error message wording for PYTEST guard
- Whether to update docstrings referencing bridge factory

## Deferred Ideas

None — discussion stayed within phase scope
