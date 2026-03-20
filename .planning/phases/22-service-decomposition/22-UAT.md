---
status: complete
phase: 22-service-decomposition
source: 22-01-SUMMARY.md, 22-02-SUMMARY.md
started: 2026-03-20T00:00:00Z
updated: 2026-03-20T12:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Package Layout
expected: service/ directory contains exactly 5 files: __init__.py, service.py, resolve.py, domain.py, payload.py. Each file has a clear single responsibility matching its name.
result: issue
reported: "resolve.py combines resolution and validation — should be split into resolve.py and validate.py since they have different dependency profiles and will grow for different reasons. With agent-built code, structure decisions should be made up-front."
severity: minor

### 2. Import Path Preservation
expected: `from omnifocus_operator.service import OperatorService` and `from omnifocus_operator.service import ErrorOperatorService` still work. The __init__.py re-exports only these two — clean public API, internals stay internal.
result: pass

### 3. Orchestrator Readability
expected: service.py reads as a thin orchestrator — each method's flow is visibly: validate -> resolve -> domain logic -> build payload -> delegate to repo. No business logic buried in orchestration. Should feel like reading a table of contents.
result: pass

### 4. Resolver Boundary
expected: resolve.py owns all "find the right entity" logic — parent resolution, tag resolution, name validation. Clear inputs (names/IDs from user), clear outputs (resolved OmniFocus entities). No domain logic leaking in.
result: issue
reported: "service.py:139 does get_task directly instead of going through Resolver. Task existence verification is resolution, not orchestration. Also domain.py has direct repo.get_task calls (lines 316, 328) that should route through Resolver."
severity: minor

### 5. DomainLogic Boundary
expected: domain.py owns all business rules — lifecycle, status warnings, tag diffing, cycle detection, move processing, no-op detection. Takes resolved entities as input, returns decisions. No repo calls, no resolution logic.
result: pass

### 6. PayloadBuilder Boundary
expected: payload.py is pure — transforms validated domain decisions into typed repo payloads. No async, no repo, no resolution. Should be the simplest module in the package.
result: issue
reported: "note=None → '' clear-intent normalization lives in payload.py:80 but tag replace:null → [] clear-intent lives in domain.py:168. Same semantic pattern split across two modules. Should centralize 'null means clear' interpretation in one domain method (normalize_clear_intents) that handles both note and tags."
severity: minor

### 7. DI Wiring Pattern
expected: OperatorService constructor wires dependencies: Resolver(repo), DomainLogic(repo, resolver), PayloadBuilder(). Each extracted class receives only what it needs — no god-object passing.
result: pass

### 8. Test Strategy — Stub vs Real
expected: test_service_domain.py uses StubResolver/StubRepo (not InMemoryRepository) — future-proofs for Phase 26. test_service_resolve.py uses real InMemoryRepository. test_service_payload.py is pure (no stubs at all). Strategy matches each module's dependency profile.
result: pass

## Summary

total: 8
passed: 5
issues: 3
pending: 0
skipped: 0

## Gaps

- truth: "resolve.py should only contain resolution logic, validation should be separate"
  status: failed
  reason: "User reported: resolve.py combines resolution and validation — should be split since they have different dependency profiles and growth vectors"
  severity: minor
  test: 1
  artifacts:
    - path: "src/omnifocus_operator/service/resolve.py"
      issue: "Contains both Resolver class and validate_task_name functions"
  missing:
    - "Split into resolve.py (Resolver class) and validate.py (validation functions)"

- truth: "All entity existence checks should route through Resolver"
  status: failed
  reason: "User reported: service.py:139 and domain.py:316,328 do direct repo.get_task calls instead of going through Resolver"
  severity: minor
  test: 4
  artifacts:
    - path: "src/omnifocus_operator/service/service.py"
      issue: "Line 139: direct repo.get_task for edit target verification"
    - path: "src/omnifocus_operator/service/domain.py"
      issue: "Lines 316, 328: direct repo.get_task for container/anchor verification"
  missing:
    - "Add resolve_task method to Resolver"
    - "Route all entity existence checks through Resolver"

- truth: "Null-means-clear intent normalization should be centralized"
  status: failed
  reason: "User reported: note=None→'' in payload.py:80 and tag replace:null→[] in domain.py:168 are the same pattern split across two modules. Should be one normalize_clear_intents method in domain."
  severity: minor
  test: 6
  artifacts:
    - path: "src/omnifocus_operator/service/payload.py"
      issue: "Line 80: note null→empty string normalization"
    - path: "src/omnifocus_operator/service/domain.py"
      issue: "Line 168: tag replace null→empty list normalization"
  missing:
    - "Create normalize_clear_intents method in DomainLogic"
    - "Move both note and tag clear-intent logic there"
