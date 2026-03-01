---
phase: 1
slug: project-scaffolding
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-01
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
| 01-01-01 | 01 | 1 | ARCH-03 | smoke | `uv run pytest tests/test_smoke.py -x` | Wave 0 | pending |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_smoke.py` — covers ARCH-03 (package import + version check)
- [ ] `tests/conftest.py` — empty, present for structure
- [ ] `tests/__init__.py` — makes tests discoverable by mypy
- [ ] Framework install: `uv sync --dev` — installs pytest, pytest-asyncio, pytest-cov, pytest-timeout

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Pre-commit hooks run on commit | ARCH-03 | Requires git hook execution | Run `git commit` and verify ruff + mypy hooks trigger |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
