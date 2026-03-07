---
phase: 5
slug: service-layer-and-mcp-server
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-02
validated: 2026-03-07
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ --tb=short` |
| **Estimated runtime** | ~7 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 7 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Test Location | Status |
|---------|------|------|-------------|-----------|---------------|--------|
| 05-01-01 | 01 | 1 | ARCH-01, ARCH-02 | unit | `tests/test_service.py::TestOperatorService`, `TestConstantMtimeSource`, `TestCreateBridge` | COVERED |
| 05-01-02 | 01 | 1 | ARCH-01, ARCH-02 | integration | `tests/test_server.py::TestARCH01ThreeLayerArchitecture`, `TestARCH02BridgeInjection` | COVERED |
| 05-01-03 | 01 | 1 | TOOL-01, TOOL-02, TOOL-03 | integration | `tests/test_server.py::TestTOOL01*`, `TestTOOL02*`, `TestTOOL03*` | COVERED |
| 05-01-04 | 01 | 1 | TOOL-04 | static | `tests/test_server.py::TestTOOL04StdoutClean` | COVERED |

*Status: COVERED · PARTIAL · MISSING*

---

## Requirements Coverage Detail

| Requirement | Description | Test File(s) | Test Class(es) | Test Count |
|-------------|-------------|--------------|-----------------|------------|
| ARCH-01 | Three-layer architecture | test_service.py, test_server.py | `TestOperatorService`, `TestARCH01ThreeLayerArchitecture` | 4 |
| ARCH-02 | Bridge injection via env var | test_service.py, test_server.py | `TestCreateBridge`, `TestARCH02BridgeInjection` | 6 |
| TOOL-01 | list_all structured output | test_server.py | `TestTOOL01ListAllStructuredOutput` | 2 |
| TOOL-02 | Tool annotations | test_server.py | `TestTOOL02Annotations` | 2 |
| TOOL-03 | Output schema from Pydantic | test_server.py | `TestTOOL03OutputSchema` | 2 |
| TOOL-04 | stderr only / stdout clean | test_server.py | `TestTOOL04StdoutClean` | 1 |

**Additional coverage beyond requirements:**
- `TestIPC06OrphanSweepWiring` — orphan sweep wiring (Phase 6 cross-concern)
- `TestDegradedMode` — error-serving degraded mode (3 tests)
- `TestErrorOperatorService` — ErrorOperatorService behavior (5 tests)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| RealBridge startup error | ARCH-02 | RealBridge is Phase 8 | Set `OMNIFOCUS_BRIDGE=real`, verify clear error message |

---

## Validation Sign-Off

- [x] All tasks have automated verify commands
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] All requirements have automated test coverage
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** PASSED

---

## Validation Audit 2026-03-07

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

**Notes:** VALIDATION.md was a pre-execution draft with Wave 0 stubs. All 6 requirements were covered during TDD execution (Plans 01-03). Tests organized in `test_service.py` (unit) and `test_server.py` (integration) rather than the originally predicted `test_list_all.py` / `test_stderr.py` files. Suite: 182 tests, 98.23% coverage.
