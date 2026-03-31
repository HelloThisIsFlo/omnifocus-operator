---
status: resolved
trigger: "pagination-ordering-nondeterministic: offset/limit pagination may return non-deterministic results"
created: 2026-03-31T00:00:00Z
updated: 2026-03-31T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - Fix applied and verified. Adding integration tests for deterministic ordering.
test: Add tests to test_repository.py (bridge) and test_hybrid_repository.py (hybrid) verifying sorted-by-ID output with pagination
expecting: All tests pass, proving deterministic ordering at repo level
next_action: Write and run integration tests

## Symptoms

expected: offset/limit pagination should return consistent, deterministic ordering across calls
actual: SQLite hybrid repo likely has no ORDER BY clause, meaning offset/limit gives non-deterministic results. Bridge-only repo ordering is also unclear.
errors: none — silent non-determinism
reproduction: use offset/limit on get_all or filtered queries — results may vary between calls
started: likely since pagination (offset/limit) was implemented

## Eliminated

## Evidence

- timestamp: 2026-03-31T00:01:00Z
  checked: query_builder.py build_list_tasks_sql and build_list_projects_sql
  found: LIMIT/OFFSET appended directly without any ORDER BY clause
  implication: SQLite returns rows in arbitrary order, pagination is non-deterministic

- timestamp: 2026-03-31T00:01:00Z
  checked: bridge.py list_tasks and list_projects
  found: Python slicing (items[offset:], items[:limit]) without sorting first
  implication: Order depends on bridge dump order which may vary between calls

- timestamp: 2026-03-31T00:01:00Z
  checked: persistentIdentifier column in SQL queries
  found: t.persistentIdentifier is the stable ID column used in all queries (Task table primary identifier)
  implication: Suitable ORDER BY target for deterministic ordering

## Resolution

root_cause: SQL queries in query_builder.py use LIMIT/OFFSET without ORDER BY, and bridge.py slices lists without sorting -- both cause non-deterministic pagination results
fix: Add ORDER BY t.persistentIdentifier to SQL queries before LIMIT/OFFSET; add sorted() by id before slicing in bridge.py; add integration tests for both repos
verification: All 1347 tests pass (6 new deterministic ordering tests added across bridge and hybrid repos). 98% coverage.
files_changed:
  - src/omnifocus_operator/repository/query_builder.py
  - src/omnifocus_operator/repository/bridge.py
  - tests/test_query_builder.py
  - tests/test_repository.py
  - tests/test_hybrid_repository.py
