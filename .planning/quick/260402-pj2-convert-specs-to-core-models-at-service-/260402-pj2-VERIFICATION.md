---
phase: 260402-pj2
verified: 2026-04-02T18:05:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
---

# Quick Task 260402-pj2: Convert Specs to Core Models at Service Boundary — Verification Report

**Task Goal:** Convert specs to core models at service boundary — create service/convert.py, update pipelines to use it, remove union signatures from payload.py and builder.py, update docs. Also fixes a silent bug where isinstance(end, EndByDate) fails on EndByDateSpec in the edit pipeline.
**Verified:** 2026-04-02T18:05:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | FrequencyAddSpec never crosses the pipeline boundary into payload.py or builder.py | VERIFIED | `grep -n "FrequencyAddSpec" payload.py builder.py` returns empty |
| 2 | EndConditionSpec never crosses the pipeline boundary into payload.py or builder.py | VERIFIED | `grep -n "EndConditionSpec" payload.py builder.py` returns empty |
| 3 | The add pipeline does not round-trip Frequency back to FrequencyAddSpec | VERIFIED | `_process_repetition_rule` stores `self._frequency` (core) and `self._end_condition` (core); `_build_payload` passes them directly to `_build_repetition_rule_payload` — no back-conversion |
| 4 | The edit pipeline's end-date-in-past warning fires correctly (isinstance(end, EndByDate) passes) | VERIFIED | service.py line 604: `end = end_condition_from_spec(spec.end)` converts EndByDateSpec to EndByDate before domain logic |
| 5 | No hasattr duck-typing in builder.py for end condition dispatch | VERIFIED | builder.py lines 103-106 use `isinstance(end, EndByOccurrences)` / `isinstance(end, EndByDate)`; `grep -n "hasattr" builder.py` returns empty |

**Score:** 5/5 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/omnifocus_operator/service/convert.py` | Pure spec-to-core conversion functions | VERIFIED | Exists, 49 lines, exports `frequency_from_spec` and `end_condition_from_spec` as declared in `__all__` |
| `src/omnifocus_operator/service/payload.py` | Core-only type signatures on `_build_repetition_rule_payload` | VERIFIED | Signature: `frequency: Frequency, end: EndCondition \| None` — no spec unions |
| `src/omnifocus_operator/rrule/builder.py` | Core-only type signatures on `build_rrule`, isinstance dispatch | VERIFIED | Signature: `frequency: Frequency, end: EndCondition \| None`; dispatch uses isinstance |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `service/service.py` | `service/convert.py` | import and call in both pipelines | WIRED | Line 47: `from omnifocus_operator.service.convert import end_condition_from_spec, frequency_from_spec`; called at lines 464, 465 (add pipeline) and 604 (edit pipeline) |
| `service/service.py` | `service/payload.py` | `_build_repetition_rule_payload` receives core Frequency and EndCondition only | WIRED | Line 486-487: passes `self._frequency` (core Frequency) and `self._end_condition` (core EndCondition) |
| `service/payload.py` | `rrule/builder.py` | `build_rrule` receives core types only | WIRED | payload.py line 131: `build_rrule(frequency, end)` where both are core types per narrowed signature |

---

### Data-Flow Trace (Level 4)

Not applicable — this is a refactoring/type-boundary task with no new rendering or data-display surfaces.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| convert.py imports work | `uv run python -c "from omnifocus_operator.service.convert import frequency_from_spec, end_condition_from_spec; print('imports OK')"` | `imports OK` | PASS |
| Targeted tests pass | `uv run pytest tests/test_service.py tests/test_service_payload.py tests/test_rrule.py -x -q` | 306 passed | PASS |
| Full test suite passes | `uv run pytest tests/ -x -q` | 1428 passed, 98% coverage | PASS |
| mypy clean on modified files | `uv run python -m mypy payload.py builder.py convert.py` | No output (no errors) | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| TODO-15 | 260402-pj2-PLAN.md | Convert specs to core models at service boundary | SATISFIED | convert.py created, pipelines rewired, signatures narrowed, docs updated |

---

### Anti-Patterns Found

None. No TODOs, stubs, hardcoded empties, or spec type leaks detected in the modified files.

---

### Human Verification Required

None. All behavioral contracts are fully verifiable via tests and grep.

---

### Gaps Summary

No gaps. All five observable truths verified. The type boundary between spec types (contracts layer) and core models (models layer) is now enforced at the service pipeline boundary. The silent edit-pipeline bug is fixed via conversion before domain logic. Downstream signatures in payload.py and builder.py are core-only with no union specs remaining.

---

_Verified: 2026-04-02T18:05:00Z_
_Verifier: Claude (gsd-verifier)_
