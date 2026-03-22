# Golden Master

Bridge contract test infrastructure for proving InMemoryBridge behavioral equivalence with RealBridge.

## Contents

- `normalize.py` -- Normalization and filtering helpers for comparison
  - `normalize_for_comparison()` -- strip dynamic fields from a single entity
  - `normalize_response()` -- strip `id` from write responses
  - `normalize_state()` -- normalize + sort an entire state snapshot
  - `filter_to_known_ids()` -- filter `get_all` to test-created entities only
- `snapshots/` -- Captured golden master fixtures (nuked and regenerated on each capture)
  - `initial_state.json` -- Seeded state before scenarios
  - `scenario_NN_*.json` -- Per-scenario state snapshots

## Regeneration

```bash
uv run python uat/capture_golden_master.py
```

Per GOLD-01: regenerate when bridge operations change (new commands, field additions, behavioral modifications).

## How It Works

1. **Capture** (manual UAT): `capture_golden_master.py` runs against RealBridge, creates test entities in OmniFocus, records responses and state snapshots as JSON fixtures.
2. **Contract tests** (CI): `test_bridge_contract.py` replays the same operations against InMemoryBridge and asserts structural equivalence after normalizing dynamic fields.
