---
phase: 57
slug: parent-filter-filter-unification
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-20
---

# Phase 57 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (existing) |
| **Config file** | `pyproject.toml` (pytest section) + `conftest.py` |
| **Quick run command** | `uv run pytest tests/contracts/use_cases/list/ tests/service/ -x -q` |
| **Full suite command** | `uv run pytest -x -q` |
| **Estimated runtime** | Quick: ~15s; Full: ~90s |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/contracts/use_cases/list/ tests/service/ -x -q`
- **After every plan wave:** Run `uv run pytest -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green + `uv run pytest tests/test_output_schema.py -x -q` must pass
- **Max feedback latency:** 15 seconds (quick); 90 seconds (full)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (Populated by planner — one row per task the planner produces. All tasks must map to a REQ-ID and have an automated verify command using the frameworks above.) | | | | | | | | | ⬜ pending |

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements — no Wave 0 test-scaffolding needed. Reasoning:*

- pytest is established with full service/, repository/, and contracts/ coverage.
- Existing `project_ids` tests in `tests/repository/hybrid/` and `tests/repository/bridge_only/` migrate mechanically to `task_id_scope` — no new framework setup.
- `tests/test_output_schema.py` already runs the contract-level JSON Schema guard (mandatory per `CLAUDE.md`).
- New files needed by the refactor (e.g., `tests/service/test_subtree.py`, `tests/service/test_resolve_parent.py`, cross-filter equivalence test) are new test files within the existing pytest tree — no infra work.
- **If** the planner decides to introduce a new test file for cross-filter equivalence (UNIFY-02 / D-15), it's a plain pytest module — no conftest changes, no fixture additions beyond existing ones.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `parent` filter end-to-end against live OmniFocus database | PARENT-01..08, WARN-01..05 | Real-database behavior (SAFE-01/02 forbids RealBridge in automated tests) | UAT via `uat/` scripts after phase ships; developer runs `/uat-regression` with new `parent`-filter suite. |
| `FILTERED_SUBTREE_WARNING` verbatim wording against agent UX | WARN-01 | Wording is judgment call; verbatim-lock is automated but agent-facing quality is manual | Manual review of warning text during UAT walkthrough. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (none required here)
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s (quick) / 90s (full)
- [ ] `nyquist_compliant: true` set in frontmatter
- [ ] `test_output_schema.py` included in pre-verification command (mandatory per `CLAUDE.md`)

**Approval:** pending
