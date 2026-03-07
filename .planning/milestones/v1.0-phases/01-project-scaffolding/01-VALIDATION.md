---
phase: 1
slug: project-scaffolding
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-01
validated: 2026-03-07
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=9.0.2 + pytest-asyncio >=1.3.0 |
| **Config file** | `pyproject.toml` under `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest -x` |
| **Full suite command** | `uv run pytest --cov-fail-under=80` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -x`
- **After every plan wave:** Run `uv run pytest --cov-fail-under=80`
- **Before `/gsd:verify-work`:** Full suite must be green + `uv run ruff check` + `uv run ruff format --check` + `uv run mypy src/`
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-T1 | 01 | 1 | ARCH-03 | smoke | `uv run pytest tests/test_smoke.py::test_package_imports -x` | Yes | green |
| 01-01-T2 | 01 | 1 | ARCH-03 | smoke | `uv run pytest tests/test_smoke.py::test_main_entry_point_exists -x` | Yes | green |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

- [x] `tests/test_smoke.py` — covers ARCH-03 (package import + version check)
- [x] `tests/conftest.py` — empty, present for structure
- [x] `tests/__init__.py` — makes tests discoverable by mypy
- [x] Framework install: `uv sync --dev` — installs pytest, pytest-asyncio, pytest-cov, pytest-timeout

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Pre-commit hooks run on commit | ARCH-03 | Requires git hook execution | Run `git commit` and verify ruff + mypy hooks trigger |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated

---

## Validation Audit 2026-03-07

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

All requirements (ARCH-03) have automated verification via `tests/test_smoke.py`. No gaps to fill.
