---
phase: 36
slug: service-orchestration-cross-path-equivalence-merged-from-old-phases-36-37
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-31
audited: 2026-03-31
---

# Phase 36 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/ -x -q --timeout=10` |
| **Full suite command** | `uv run pytest tests/ -q --timeout=30` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q --timeout=10`
- **After every plan wave:** Run `uv run pytest tests/ -q --timeout=30`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| T1 | 36-01 | 1 | INFRA-06 (validation) | unit | `uv run pytest tests/test_list_contracts.py -x -q -k "offset or review_due"` | ✅ | ✅ green |
| T2 | 36-01 | 1 | INFRA-06 (pipeline/CF epoch) | unit | `uv run pytest tests/test_list_pipelines.py tests/test_query_builder.py -x -q -k "review_due"` | ✅ | ✅ green |
| T1 | 36-02 | 2 | INFRA-03 (seed infra) | integration | `uv run pytest tests/test_cross_path_equivalence.py -x -q` | ✅ | ✅ green |
| T2 | 36-02 | 2 | INFRA-03 (entity tests) | integration | `uv run pytest tests/test_cross_path_equivalence.py -x -q -v` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] Cross-path equivalence test file — seed adapters + parametrized fixture
- [x] Validation test stubs for offset-requires-limit, ReviewDueFilter parsing, educational errors

*All Wave 0 requirements satisfied during execution.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete

---

## Validation Audit 2026-03-31

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

### Coverage Summary

| Requirement | Tests | Status |
|-------------|-------|--------|
| INFRA-06 (input validation, ReviewDueFilter, educational errors) | 24 tests across 3 files | ✓ COVERED |
| INFRA-03 (cross-path equivalence) | 32 parametrized tests (16 × bridge/sqlite) | ✓ COVERED |

**Total: 56 tests, all green. Phase is Nyquist-compliant.**
