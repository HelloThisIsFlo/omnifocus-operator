---
phase: quick-260401-twg
plan: 01
subsystem: api
tags: [mcp, pydantic, schema, descriptions, agent-facing]

requires:
  - phase: 36.3
    provides: Centralized descriptions.py with all field/class constants
provides:
  - Updated write-side date descriptions with examples instead of timezone prose
  - Per-value enum documentation for schedule and basedOn
  - Descriptions for all previously bare fields
  - get_all last-resort warning referencing list_tasks/list_projects
  - Test enforcement for centralized examples= values
affects: [contracts, server, agent-facing-schemas]

tech-stack:
  added: []
  patterns:
    - "Field(examples=[CONSTANT]) for centralized example values on date fields"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/agent_messages/descriptions.py
    - src/omnifocus_operator/contracts/use_cases/add/tasks.py
    - src/omnifocus_operator/contracts/use_cases/edit/tasks.py
    - src/omnifocus_operator/contracts/shared/repetition_rule.py
    - tests/test_descriptions.py

key-decisions:
  - "EN DASH in ON_DATE replaced with hyphen-minus to satisfy ruff RUF001 -- semantic meaning preserved"

patterns-established:
  - "examples=[CONSTANT] pattern: all Field(examples=...) values must reference descriptions.py constants"

requirements-completed: []

duration: 4min
completed: 2026-04-01
---

# Quick Task 260401-twg: Improve MCP Tool Schema Descriptions Summary

**Replace timezone prose with ISO 8601 examples, add per-value enum docs, describe all bare fields, and enforce centralized examples**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-01T23:39:50Z
- **Completed:** 2026-04-01T23:44:38Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Write-side date fields now show `examples=["2026-03-15T17:00:00Z"]` instead of timezone prose
- SCHEDULE_DOC and BASED_ON_DOC have per-value one-liners (schedule includes WIP tag for edge cases)
- All previously bare fields (name, flagged, estimatedMinutes, note, id) have descriptions
- ON_DATE, ON_DAYS, ON_WEEKDAY_PATTERN clarify scope, mutual exclusivity, and optionality
- Tag field descriptions shortened to format hints; error behavior stays in tool docs only
- GET_ALL_TOOL_DOC warns agents to prefer list_tasks/list_projects
- New test prevents inline example values from creeping back

## Task Commits

Each task was committed atomically:

1. **Task 1: Update descriptions.py and wire examples/descriptions** - `b63e981` (feat)
2. **Task 2: Add examples= enforcement test** - `7885e5d` (test)

## Files Created/Modified

- `src/omnifocus_operator/agent_messages/descriptions.py` - Updated 10+ constants, added 10 new ones (DATE_EXAMPLE, field descriptions, ON_WEEKDAY_PATTERN)
- `src/omnifocus_operator/contracts/use_cases/add/tasks.py` - Added examples=[DATE_EXAMPLE] on date Fields, descriptions on name/flagged/estimatedMinutes/note
- `src/omnifocus_operator/contracts/use_cases/edit/tasks.py` - Added examples=[DATE_EXAMPLE] on date Fields, descriptions on id/name/flagged/note/estimatedMinutes
- `src/omnifocus_operator/contracts/shared/repetition_rule.py` - Added ON_DATE/ON_WEEKDAY_PATTERN descriptions to on_dates/on Fields
- `tests/test_descriptions.py` - New test_no_inline_examples_in_agent_models enforcement test

## Decisions Made

- EN DASH in ON_DATE phrasing (`1-31`) replaced with hyphen-minus to satisfy ruff RUF001 linter rule -- semantic meaning preserved

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] EN DASH character in ON_DATE**
- **Found during:** Task 1 (descriptions.py update)
- **Issue:** CONTEXT.md locked phrasing used en-dash `1-31` which ruff RUF001 rejects as ambiguous
- **Fix:** Replaced with standard hyphen-minus `1-31` -- identical meaning for a range
- **Files modified:** src/omnifocus_operator/agent_messages/descriptions.py
- **Verification:** ruff check passes
- **Committed in:** b63e981 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Trivial character substitution to satisfy linter. No scope change.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None.

## Self-Check: PASSED

---
*Phase: quick-260401-twg*
*Completed: 2026-04-01*
