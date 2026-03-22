---
status: complete
phase: 27-repository-contract-tests-for-behavioral-equivalence
source: 27-01-SUMMARY.md, 27-02-SUMMARY.md, 27-03-SUMMARY.md, 27-04-SUMMARY.md
started: 2026-03-22T14:00:00Z
updated: 2026-03-22T14:10:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Golden Master Package Layout
expected: `tests/golden_master/` has a clear structure: `snapshots/` subfolder with 20 scenario files + `initial_state.json`, a `normalize.py` with the normalization helpers, `__init__.py`, and a `README.md` explaining the regeneration workflow. Naming is consistent: `scenario_01_add_inbox_task.json` through `scenario_20_combined_edit.json`.
result: pass

### 2. VOLATILE vs UNCOMPUTED Normalization Split
expected: `tests/golden_master/normalize.py` clearly separates two categories of excluded fields: VOLATILE (id, url, added, modified — never match between runs) and UNCOMPUTED (effectiveDueDate, completionDate, status, etc. — InMemoryBridge doesn't compute yet but could). The key insight: removing a field from UNCOMPUTED auto-enables contract test verification for that field with zero test changes.
result: pass

### 3. Contract Test Readability
expected: `tests/test_bridge_contract.py` uses parametrized tests with readable scenario names (not just numbers). When a test fails, the diff should clearly show which field diverged between InMemoryBridge and the golden master. The ID cross-reference remapping should be transparent — not hiding real mismatches.
result: pass

### 4. Capture Script Scenario Coverage
expected: `uat/capture_golden_master.py` has 20 scenarios covering: add_task (inbox, parent, all fields, tags, subtask under task), edit_task (name, note, flag, dates, clear dates, estimated minutes, add/remove/replace tags), lifecycle (complete, drop), move (to project, to inbox, subtask to inbox), and combined multi-field edit. Each scenario is self-documenting with a clear name.
result: pass

### 5. InMemoryBridge Raw Format Convention
expected: `tests/doubles/bridge.py` — InMemoryBridge now stores and returns raw bridge format (status strings like "Next", parent/project as string IDs) matching what RealBridge returns. The adapter pipeline (adapt_snapshot) runs on this raw output to produce model format. This means InMemoryBridge is a faithful double of the real bridge, not a convenience shortcut.
result: pass

### 6. Parent/Tag Resolution Helpers
expected: `tests/doubles/bridge.py` has shared `_resolve_parent` and `_resolve_tag_name` helpers used by both add_task and edit_task. Parent resolution handles project, task, and unknown parent types. Tag resolution looks up names from the internal `_tags` list rather than using the ID as the name.
result: pass

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
