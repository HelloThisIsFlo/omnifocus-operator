---
phase: 260402-pj2
plan: 01
subsystem: service
tags: [pydantic, type-boundary, refactoring, bug-fix]

requires:
  - phase: 36.4
    provides: "Type boundary enforcement for Literal/Annotated in models/"
provides:
  - "service/convert.py with frequency_from_spec and end_condition_from_spec"
  - "Core-only type signatures on payload.py and builder.py"
  - "Bug fix: end-date-in-past warning now fires on edit operations"
affects: [service, rrule, payload]

tech-stack:
  added: []
  patterns: ["Spec-to-core conversion at service boundary via convert.py"]

key-files:
  created: ["src/omnifocus_operator/service/convert.py"]
  modified:
    - "src/omnifocus_operator/service/service.py"
    - "src/omnifocus_operator/service/payload.py"
    - "src/omnifocus_operator/rrule/builder.py"
    - "docs/architecture.md"

key-decisions:
  - "build_add gets optional repetition_rule_payload param for pre-converted payloads"
  - "payload.py fallback path also uses convert functions for direct callers"
  - "EndByDate/EndByOccurrences moved to runtime imports in builder.py for isinstance dispatch"

patterns-established:
  - "Spec-to-core conversion: pure functions in service/convert.py called at pipeline boundary"

requirements-completed: [TODO-15]

duration: 5min
completed: 2026-04-02
---

# Quick Task 260402-pj2: Convert Specs to Core Models at Service Boundary

**Pure spec-to-core conversion at service boundary via convert.py, eliminating union signatures, hasattr duck-typing, and fixing silent edit-pipeline end-date warning bug**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-02T17:49:57Z
- **Completed:** 2026-04-02T17:55:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Created `service/convert.py` with `frequency_from_spec` and `end_condition_from_spec` pure conversion functions
- Eliminated Frequency round-trip in add pipeline (spec -> core, no back-conversion to spec)
- Fixed silent bug: `isinstance(EndByDateSpec, EndByDate)` was always False in edit pipeline, so end-date-in-past warning never fired on edits
- Narrowed all downstream signatures to core-only types (no spec unions in payload.py or builder.py)
- Replaced hasattr duck-typing with proper isinstance dispatch in builder.py

## Task Commits

1. **Task 1: Create convert.py and rewire both pipelines** - `4f95bb2` (feat)
2. **Task 2: Narrow downstream signatures and update docs** - `dbe402a` (refactor)

## Files Created/Modified

- `src/omnifocus_operator/service/convert.py` - Pure spec-to-core conversion functions
- `src/omnifocus_operator/service/service.py` - Rewired add/edit pipelines to convert at boundary
- `src/omnifocus_operator/service/payload.py` - Core-only signatures, convert in fallback path
- `src/omnifocus_operator/rrule/builder.py` - Core-only signature, isinstance dispatch
- `docs/architecture.md` - Added convert.py to package structure

## Decisions Made

- `build_add` gets an optional `repetition_rule_payload` param so the pipeline can pass pre-built payloads while the fallback path (used by tests calling `build_add` directly) does its own conversion
- `EndByDate`/`EndByOccurrences` moved from TYPE_CHECKING to runtime imports in builder.py since isinstance requires runtime availability
- Removed stale `type: ignore[arg-type]` on `_build_byday_positional` call -- types now align with core-only Frequency

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] payload.py fallback path still passed spec types after signature narrowing**
- **Found during:** Task 2 (narrowing signatures)
- **Issue:** `build_add`'s fallback path (lines 68-74) extracted spec types from `command.repetition_rule` and passed them to `_build_repetition_rule_payload`, which now expects core types. Test `test_with_end_by_occurrences` failed.
- **Fix:** Added `frequency_from_spec`/`end_condition_from_spec` calls in the fallback path
- **Files modified:** `src/omnifocus_operator/service/payload.py`
- **Verification:** All 306 targeted tests pass
- **Committed in:** `dbe402a` (Task 2 commit)

**2. [Rule 1 - Bug] Stale type: ignore comment in builder.py**
- **Found during:** Task 2 (mypy check)
- **Issue:** `type: ignore[arg-type]` on `_build_byday_positional(frequency.on)` was no longer needed with core-only Frequency type
- **Fix:** Removed the comment
- **Files modified:** `src/omnifocus_operator/rrule/builder.py`
- **Verification:** mypy clean
- **Committed in:** `dbe402a` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both necessary for correctness. No scope creep.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Type boundary fully enforced at service layer
- No spec types leak past pipeline boundary into payload or rrule modules
- Ready for Phase 37 (service orchestration wiring)

---
*Phase: 260402-pj2*
*Completed: 2026-04-02*
