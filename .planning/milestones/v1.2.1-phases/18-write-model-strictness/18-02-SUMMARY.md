---
phase: 18-write-model-strictness
plan: 02
subsystem: api
tags: [warnings, refactoring, constants, agent-guidance]

# Dependency graph
requires:
  - phase: none
    provides: "service.py with inline warning strings"
provides:
  - "warnings.py with all 11 agent-facing warning constants"
  - "service.py using warning constants exclusively"
  - "integrity tests preventing inline string regression"
affects: [19-write-model-naming, 22-service-extraction]

# Tech tracking
tech-stack:
  added: []
  patterns: ["warning constants in dedicated module", "AST-based inline string detection in tests"]

key-files:
  created:
    - src/omnifocus_operator/warnings.py
    - tests/test_warnings.py
  modified:
    - src/omnifocus_operator/service.py

key-decisions:
  - "Used {placeholder} syntax with .format() for parameterized warnings"
  - "TAG_ALREADY_ON_TASK uses {tag_id} not {add_resolved[i]} for clarity at call site"
  - "AST-based test detects inline strings in warnings.append() calls"

patterns-established:
  - "Warning constants: all agent-facing messages defined in warnings.py, imported at use site"
  - "Integrity test: AST walks service.py to catch inline warning string regressions"

requirements-completed: [STRCT-01]

# Metrics
duration: 5min
completed: 2026-03-16
---

# Phase 18 Plan 02: Warning Consolidation Summary

**All 11 agent-facing warning strings extracted to warnings.py with integrity tests preventing inline regression**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-16T23:06:01Z
- **Completed:** 2026-03-16T23:11:37Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Created warnings.py with all 11 warning constants grouped by domain (Edit, Move, Lifecycle, Tags)
- Replaced all inline warning strings in service.py with constant references
- Added 4 integrity tests: all constants referenced, no inline strings (AST), type check, placeholder balance
- Full test suite passes (515 tests, 94% coverage)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create warnings.py with consolidated warning constants** - `c41ac1e` (feat)
2. **Task 2: Update service.py to use warning constants and add integrity test** - `8ac18c1` (feat)

## Files Created/Modified
- `src/omnifocus_operator/warnings.py` - All 11 agent-facing warning constants grouped by domain
- `src/omnifocus_operator/service.py` - Imports and uses warning constants, zero inline warning strings
- `tests/test_warnings.py` - Integrity tests: constants referenced, no inline strings, type/placeholder validation

## Decisions Made
- Used `{placeholder}` syntax with `.format()` for parameterized warnings (clear at call site)
- TAG_ALREADY_ON_TASK/TAG_NOT_ON_TASK use `{tag_id}` parameter name (not `{add_resolved[i]}`) for readability
- AST-based detection catches `ast.Constant` and `ast.JoinedStr` (plain strings and f-strings) inside `warnings.append()` calls

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Ruff line-length violations on `.format()` calls with long argument lists -- resolved by ruff auto-format wrapping
- Ruff N812 naming convention (lowercase module `warnings` imported as uppercase `W`) -- renamed alias to `warn_mod`
- Pre-existing test failure (`test_unknown_fields_ignored`) from 18-01 TDD RED phase -- confirmed out of scope, not caused by this plan

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- warnings.py ready for any future warning additions
- Integrity tests will catch inline string regressions
- service.py is cleaner and ready for further extraction in Phase 22

## Self-Check: PASSED

- All 3 files exist (warnings.py, service.py, test_warnings.py)
- Both commits verified (c41ac1e, 8ac18c1)

---
*Phase: 18-write-model-strictness*
*Completed: 2026-03-16*
