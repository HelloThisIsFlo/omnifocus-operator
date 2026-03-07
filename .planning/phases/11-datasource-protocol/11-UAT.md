---
status: complete
phase: 11-datasource-protocol
source: 11-01-SUMMARY.md, 11-02-SUMMARY.md
started: 2026-03-07T16:00:00Z
updated: 2026-03-07T16:10:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running server/service. Run `uv run pytest` from repo root. All 236 tests pass. Then start the MCP server — it boots without import errors or crashes.
result: pass

### 2. MCP Server Connects
expected: Connect to the MCP server from Claude Desktop (or your MCP client). The server responds to a `list_all` tool call and returns OmniFocus data without errors.
result: pass

### 3. Architecture Doc Exists
expected: Open `docs/architecture.md`. It exists, is readable, and describes the three-layer architecture (MCP Server -> Service -> Repository) with the new Repository protocol.
result: pass

### 4. No Backward-Compat Aliases Leak
expected: Run `uv run python -c "from omnifocus_operator.repository import OmniFocusRepository"` — this should raise an ImportError (alias was removed). The clean exports are Repository, BridgeRepository, InMemoryRepository only.
result: pass

### 5. Naming Convention: get_all() and AllEntities
expected: Repository protocol method is `get_all()` returning `AllEntities` (not `get_snapshot()` / `DatabaseSnapshot`). Convention: `get_*` for structured multi-type containers, `list_*` for flat filtered collections.
result: issue
reported: "Protocol method is get_snapshot() returning DatabaseSnapshot. Should be get_all() returning AllEntities per naming convention discussion. get_* for structured containers, list_* for flat filtered collections."
severity: major

## Summary

total: 5
passed: 4
issues: 1
pending: 0
skipped: 0

## Gaps

- truth: "Repository protocol method is get_all() returning AllEntities, establishing convention: get_* for structured containers, list_* for flat filtered collections"
  status: failed
  reason: "User reported: Protocol method is get_snapshot() returning DatabaseSnapshot. Should be get_all() returning AllEntities per naming convention discussion."
  severity: major
  test: 5
  root_cause: "Original implementation used get_snapshot()/DatabaseSnapshot naming from v1.0 when caching was at the protocol level. Now that caching moved inside BridgeRepository, the snapshot metaphor no longer applies at the protocol boundary."
  artifacts:
    - path: "src/omnifocus_operator/repository/protocol.py"
      issue: "Method named get_snapshot, should be get_all"
    - path: "src/omnifocus_operator/models/snapshot.py"
      issue: "Class named DatabaseSnapshot, should be AllEntities"
  missing:
    - "Rename DatabaseSnapshot to AllEntities across all models and imports"
    - "Rename get_snapshot() to get_all() in Repository protocol and all implementations"
    - "Update all call sites (service.py, tests, etc.)"
  debug_session: ""
