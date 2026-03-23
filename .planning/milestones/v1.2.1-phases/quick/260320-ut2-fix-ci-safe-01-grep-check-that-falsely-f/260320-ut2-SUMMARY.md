---
phase: quick
quick_id: 260320-ut2
description: Fix CI SAFE-01 grep check that falsely flags legitimate RealBridge references in test files
completed: 2026-03-20
---

# Quick Task 260320-ut2: Summary

## Problem
CI SAFE-01 check used `grep -r "RealBridge" tests/` which caught legitimate references:
- `tests/doubles/simulator.py` — SimulatorBridge inherits from RealBridge (approved test infrastructure)
- `tests/test_smoke.py`, `tests/test_ipc_engine.py` — tests verifying SAFE-01 enforcement itself

## Fix
Updated `.github/workflows/ci.yml` SAFE-01 step to:
- Exclude `tests/doubles/` directory (test infrastructure)
- Exclude `test_smoke.py` and `test_ipc_engine.py` (enforcement tests)
- Added comments explaining the allowlist rationale
- Verified it still catches real violations (tested with fake file)

## Commit
- `8871f03` — fix(ci): refine SAFE-01 grep to allow legitimate RealBridge references
