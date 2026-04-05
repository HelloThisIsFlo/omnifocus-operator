---
phase: 38
slug: improve-list-tool-parameter-documentation
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-05
---

# Phase 38 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (via uv) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_descriptions.py -x -q` |
| **Full suite command** | `uv run pytest tests/test_descriptions.py tests/test_output_schema.py -x -q` |
| **Estimated runtime** | ~3 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_descriptions.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/test_descriptions.py tests/test_output_schema.py -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 3 seconds

---

## Per-Task Verification Map

| Req | Description | Test File | Test Class/Method | Status |
|-----|-------------|-----------|-------------------|--------|
| R1 | 12 bare params get Field(description=...) | `tests/test_descriptions.py` | `test_no_inline_field_descriptions_in_agent_models` | ✅ green |
| R2 | 5 list tool descriptions reworked | `tests/test_descriptions.py` | `TestToolDescriptionEnforcement` (3 tests) | ✅ green |
| R3 | 3 availability enum docstrings updated | `tests/test_descriptions.py` | `test_no_inline_class_docstrings_on_agent_classes` | ✅ green |
| R4 | Folder hierarchy note added | `tests/test_descriptions.py` | `test_all_description_constants_referenced_in_consumers` | ✅ green |
| R5 | Tag hierarchy note + parent field fix | `tests/test_descriptions.py` | `test_all_description_constants_referenced_in_consumers` | ✅ green |
| R6 | Perspectives built-in caveat | `tests/test_descriptions.py` | `test_all_description_constants_referenced_in_consumers` | ✅ green |
| R7 | Unicode → ASCII fix | `tests/test_descriptions.py` | `test_all_description_constants_are_strings` (structural) | ✅ green |
| R8 | Output schema still validates | `tests/test_output_schema.py` | full suite | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All requirements have automated verification via existing test suite
- [x] Sampling continuity: structural AST tests cover every description change
- [x] No Wave 0 dependencies needed
- [x] No watch-mode flags
- [x] Feedback latency < 3s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-05

---

## Validation Audit 2026-04-05

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

**Note:** Phase 38 was pure documentation — string changes to `Field(description=...)` constants and tool docstrings. The existing `test_descriptions.py` suite provides comprehensive structural verification via AST parsing (centralized constants, no inline strings, byte-limit compliance, consumer references). No new tests required.
