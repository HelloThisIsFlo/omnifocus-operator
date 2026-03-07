---
phase: 11
slug: datasource-protocol
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-07
validated: 2026-03-07
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x with pytest-asyncio |
| **Config file** | `pyproject.toml` (pytest section) |
| **Quick run command** | `uv run python -m pytest tests/ -x -q` |
| **Full suite command** | `uv run python -m pytest tests/ -q` |
| **Estimated runtime** | ~8 seconds |
| **Test count** | 236 |
| **Coverage** | 98.4% |

---

## Sampling Rate

- **After every task commit:** Run `uv run python -m pytest tests/ -x -q`
- **After every plan wave:** Run `uv run python -m pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 1 | ARCH-01, ARCH-03 | unit | `uv run python -m pytest tests/test_repository.py -x -q` | Yes | green |
| 11-02-01 | 02 | 2 | ARCH-02, ARCH-03 | unit | `uv run python -m pytest tests/test_service.py tests/test_server.py -x -q` | Yes | green |
| 11-02-02 | 02 | 2 | (docs) | existence | `test -f docs/architecture.md` | Yes | green |

*Status: pending · green · red · flaky*

---

## Requirement Coverage Detail

| Requirement | Tests | Verification |
|-------------|-------|-------------|
| **ARCH-01**: Repository protocol | `test_satisfies_repository_protocol`, `test_bridge_repository_satisfies_protocol`, TestSNAP01-05 | Protocol exists, runtime_checkable, both implementations satisfy it |
| **ARCH-02**: Consumer migration | test_service.py (InMemoryRepository), test_server.py (Repository type hint), grep zero OmniFocusRepository refs | All consumers use protocol, not concrete class |
| **ARCH-03**: InMemoryRepository | `test_returns_snapshot`, `test_satisfies_repository_protocol`, all test_service.py tests | InMemoryRepository used for test isolation, returns pre-built snapshot |

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. Tests were migrated, not created from scratch.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete

---

## Validation Audit 2026-03-07

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
