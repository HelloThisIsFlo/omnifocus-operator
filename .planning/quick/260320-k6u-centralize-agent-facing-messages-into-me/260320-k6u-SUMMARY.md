---
phase: quick-260320-k6u
plan: 01
subsystem: messaging
tags: [agent-messages, refactoring, ast-enforcement]

requires:
  - phase: 18-write-model-strictness
    provides: warning constants and AST test pattern
provides:
  - agent_messages/ package with centralized warnings and errors
  - AST-based enforcement for inline error string regressions
affects: [server, service-domain, service-resolve, contracts-common]

tech-stack:
  added: []
  patterns:
    - "agent_messages/ package for all agent-facing strings (warnings + errors)"
    - "AST-based test enforcement for both warning append() and ValueError raise patterns"

key-files:
  created:
    - src/omnifocus_operator/agent_messages/__init__.py
    - src/omnifocus_operator/agent_messages/errors.py
    - src/omnifocus_operator/agent_messages/warnings.py
  modified:
    - src/omnifocus_operator/warnings.py
    - src/omnifocus_operator/server.py
    - src/omnifocus_operator/service/domain.py
    - src/omnifocus_operator/service/resolve.py
    - src/omnifocus_operator/contracts/common.py
    - tests/test_warnings.py
    - tests/test_service_domain.py

key-decisions:
  - "Backward-compat shim in warnings.py for existing imports (removed in future cleanup)"
  - "Flat UPPER_SNAKE_CASE naming for error constants (no prefix taxonomy for ~15 constants)"
  - "AST error scan detects msg=f'...' + raise ValueError(msg) pattern specifically"

patterns-established:
  - "agent_messages/ package: all agent-visible strings live here, enforced by AST tests"

requirements-completed: [centralize-agent-messages]

duration: 5min
completed: 2026-03-20
---

# Quick Task 260320-k6u: Centralize Agent-Facing Messages Summary

**agent_messages/ package with 14 warning + 15 error constants, AST enforcement for both, zero inline agent-facing strings remaining**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-20T15:22:33Z
- **Completed:** 2026-03-20T15:28:29Z
- **Tasks:** 3
- **Files modified:** 11

## Accomplishments
- Created `agent_messages/` package with `warnings.py` (moved), `errors.py` (15 new constants), `__init__.py` (re-exports)
- Replaced all 16 inline error strings across server.py, domain.py, resolve.py, contracts/common.py
- Expanded AST enforcement from 4 tests (warnings only) to 8 tests (warnings + errors)
- 592 tests pass (4 new), 97% coverage, mypy/ruff clean

## Task Commits

Each task was committed atomically:

1. **Task 1: Create agent_messages/ package, move warnings, add errors** - `c99434c` (feat)
2. **Task 2: Update all consumer imports and replace inline error strings** - `69ee3c9` (refactor)
3. **Task 3: Expand AST-based test enforcement to cover errors** - `1ccd86d` (test)

## Files Created/Modified
- `src/omnifocus_operator/agent_messages/__init__.py` - Re-exports all constants for flat access
- `src/omnifocus_operator/agent_messages/warnings.py` - 14 warning constants (moved from warnings.py)
- `src/omnifocus_operator/agent_messages/errors.py` - 15 error constants (new)
- `src/omnifocus_operator/warnings.py` - Backward-compat shim (re-exports from agent_messages)
- `src/omnifocus_operator/server.py` - 6 inline errors replaced, warning imports updated
- `src/omnifocus_operator/service/domain.py` - 3 inline errors replaced, warning imports updated
- `src/omnifocus_operator/service/resolve.py` - 4 inline errors replaced with constants
- `src/omnifocus_operator/contracts/common.py` - 3 validator error strings replaced
- `tests/test_warnings.py` - 8 tests: 4 warning + 4 error enforcement
- `tests/test_service_domain.py` - Warning imports updated to agent_messages path

## Decisions Made
- Backward-compat shim in `warnings.py` keeps existing external imports working -- cleanup deferred
- Flat UPPER_SNAKE_CASE naming for ~15 error constants (no prefix taxonomy needed at this scale)
- AST error detection scans for `msg = f"..."` / `msg = "..."` followed by `raise ValueError(msg)` pattern
- `TAG_NOT_FOUND` uses `{name}` placeholder (not `{id}`) since server.py passes `id` param that could be a name

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All agent-facing messages centralized in one auditable package
- AST enforcement prevents regressions for both warnings and errors
- Backward-compat shim can be removed in a future cleanup task

## Self-Check: PASSED

All 5 key files verified present. All 3 task commits verified in git log.

---
*Phase: quick-260320-k6u*
*Completed: 2026-03-20*
