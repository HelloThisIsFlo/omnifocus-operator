---
status: resolved
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
result: pass
resolved: "Plan 11-03 renamed DatabaseSnapshot->AllEntities and get_snapshot()->get_all() across all 15 files. 236 tests pass."

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0

## Gaps

- truth: "Repository protocol method is get_all() returning AllEntities, establishing convention: get_* for structured containers, list_* for flat filtered collections"
  status: resolved
  reason: "Plan 11-03 renamed all occurrences. Zero old references remain in src/ or tests/."
  severity: major
  test: 5
  root_cause: "Original implementation used get_snapshot()/DatabaseSnapshot naming from v1.0 when caching was at the protocol level. Now that caching moved inside BridgeRepository, the snapshot metaphor no longer applies at the protocol boundary."
  resolved_by: "11-03-PLAN.md"
