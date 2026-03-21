---
status: complete
phase: 26-replace-inmemoryrepository-with-stateful-inmemorybridge
source: 26-01-SUMMARY.md, 26-02-SUMMARY.md
started: 2026-03-21T02:15:00Z
updated: 2026-03-21T02:28:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Doubles Package Exports
expected: Open `tests/doubles/__init__.py`. The public API should be clean and minimal — InMemoryBridge, BridgeCall, ConstantMtimeSource, SimulatorBridge. No trace of InMemoryRepository in exports or comments.
result: pass

### 2. InMemoryBridge API Surface
expected: Open `tests/doubles/bridge.py`. The class should read as a self-documenting test double: clear docstring explaining stateful vs stub modes, intuitive send_command dispatch (get_all/add_task/edit_task), and the backward-compat fallback should feel like a natural safety net, not a hack.
result: issue
reported: "InMemoryBridge has two hidden modes (stateful vs stub) with auto-detection via seed data shape. Should be split into two separate classes: StubBridge (canned responses, no state) and InMemoryBridge (stateful dispatch only). Duplicate the shared plumbing (~15 lines of call tracking, error injection, WAL). Kill the _stateful flag and auto-detection."
severity: minor

### 3. InMemoryRepository Fully Removed
expected: Confirm `tests/doubles/repository.py` no longer exists. Run `grep -r "InMemoryRepository" tests/` — should find zero hits (no stale imports, comments, or references).
result: pass

### 4. Fixture Composition Pattern
expected: Open `tests/test_service.py` (top ~40 lines) and `tests/test_service_resolve.py` (top ~60 lines). The bridge→repo fixture chain should be readable: `bridge()` creates InMemoryBridge with snapshot data, `repo(bridge)` wires it into BridgeRepository. The pattern should feel natural and consistent across both files.
result: issue
reported: "Fixtures exist (bridge, repo) but almost no tests use them. Every test recreates bridge + repo + service inline — same 3 lines copy-pasted ~90+ times. Additionally, imports like AddTaskCommand and make_tag_dict are repeated inline in 15+ test methods instead of at top of file. Should add service(repo) fixture. Design direction: custom @pytest.mark.snapshot(...) marker for declarative test data, fixture reads marker to build pre-loaded service. Hoist all repeated inline imports to module level. Eliminates boilerplate for both default and custom snapshot cases."
severity: major

### 5. Test Readability After Migration
expected: Skim a few test methods in `tests/test_service.py` (e.g. test_get_all_data_returns_snapshot, test_add_task_delegates). The inline `InMemoryBridge(data=make_snapshot_dict(...))` construction should be clear — you can see exactly what data each test starts with. No indirection or mystery.
result: skipped
reason: Same root cause as Test 4 — boilerplate duplication is the readability problem.

### 6. Test Suite Health
expected: Run `just test` (or equivalent). All ~640 tests pass, no warnings about missing imports or deprecated usage. Coverage stays at or above 94%.
result: pass

## Summary

total: 6
passed: 3
issues: 2
pending: 0
skipped: 1
blocked: 0

## Gaps

- truth: "InMemoryBridge should be a single-purpose stateful test double with no hidden modes"
  status: failed
  reason: "User reported: InMemoryBridge has two hidden modes (stateful vs stub) with auto-detection via seed data shape. Should be split into StubBridge + InMemoryBridge. Duplicate shared plumbing, kill _stateful flag."
  severity: minor
  test: 2
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "Tests should use fixture composition (bridge→repo→service) instead of repeating construction boilerplate"
  status: failed
  reason: "User reported: Fixtures exist but almost no tests use them. Every test recreates bridge + repo + service inline — same 3 lines copy-pasted ~90+ times. Additionally, imports like AddTaskCommand and make_tag_dict are repeated inline in 15+ test methods instead of at top of file. Should add service(repo) fixture. Design direction: custom @pytest.mark.snapshot(...) marker for declarative test data, fixture reads marker to build pre-loaded service. Hoist all repeated inline imports to module level. Eliminates boilerplate for both default and custom snapshot cases."
  severity: major
  test: 4
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
