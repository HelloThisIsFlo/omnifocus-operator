---
phase: 57
slug: parent-filter-filter-unification
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-20
approved: 2026-04-20
---

# Phase 57 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (existing) |
| **Config file** | `pyproject.toml` (pytest section) + `tests/conftest.py` |
| **Quick run command** | `uv run pytest tests/test_list_contracts.py tests/test_service_resolve.py tests/test_list_pipelines.py tests/test_service_domain.py tests/test_query_builder.py tests/test_bridge_only_repository.py tests/test_hybrid_repository.py -x -q` |
| **Full suite command** | `uv run pytest -x -q` |
| **Schema guard (mandatory post-contract change)** | `uv run pytest tests/test_output_schema.py -x -q` |
| **Estimated runtime** | Quick: ~10s; Full: ~90s |

---

## Sampling Rate

- **After every task commit:** Run the Quick command above.
- **After any task touching `contracts/use_cases/list/tasks.py` or other output-boundary models:** Also run the Schema guard command (mandatory per project `CLAUDE.md`).
- **After every plan wave:** Run the Full suite.
- **Before `/gsd-verify-work`:** Full suite green + Schema guard green.
- **Max feedback latency:** ~10s (quick); ~90s (full).

---

## Per-Task Verification Map

Plans (`57-01`, `57-02`, `57-03`) populate this through their `<verify><automated>` blocks. Each task gets its own automated pytest target, and every task maps to at least one REQ-ID in its plan's `requirements` frontmatter.

| Task ID | Plan | Wave | Requirements | Test Type | Automated Command | Status |
|---------|------|------|--------------|-----------|-------------------|--------|
| 57-01-01 | 01 | 1 | UNIFY-01, UNIFY-03, PARENT-03, PARENT-04 | unit | `uv run pytest tests/test_service_subtree.py -x -q` | ✅ green |
| 57-01-02 | 01 | 1 | UNIFY-04, UNIFY-05, UNIFY-06 | unit+integration | `uv run pytest tests/test_list_contracts.py tests/test_query_builder.py tests/test_bridge_only_repository.py tests/test_hybrid_repository.py tests/test_list_pipelines.py tests/test_output_schema.py -x -q` | ✅ green |
| 57-02-01 | 02 | 2 | PARENT-01, PARENT-02, PARENT-05, PARENT-06, PARENT-07, PARENT-08, PARENT-09 | unit | `uv run pytest tests/test_list_contracts.py tests/test_descriptions.py tests/test_output_schema.py -x -q` | ✅ green |
| 57-02-02 | 02 | 2 | UNIFY-02, WARN-02, WARN-05 | unit+integration | `uv run pytest tests/test_service_resolve.py tests/test_list_pipelines.py -x -q` | ✅ green |
| 57-03-01 | 03 | 3 | WARN-01, WARN-04 | unit | `uv run pytest tests/test_service_domain.py tests/test_list_pipelines.py -x -q` | ✅ green |
| 57-03-02 | 03 | 3 | WARN-03 | unit | `uv run pytest tests/test_service_domain.py tests/test_list_pipelines.py -x -q` | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky · (task IDs are indicative; plan may further split — see Blocker #5 revision)*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements — no Wave 0 test-scaffolding needed. Reasoning:*

- pytest is established; project uses a **flat `tests/` layout** (no `tests/service/` or `tests/contracts/` subdirectories — tests live as `tests/test_*.py` files).
- Existing `project_ids` tests in `tests/test_query_builder.py`, `tests/test_bridge_only_repository.py`, `tests/test_hybrid_repository.py`, and `tests/test_list_contracts.py` migrate mechanically to `task_id_scope` — no new framework setup.
- `tests/test_output_schema.py` already runs the contract-level JSON Schema guard (mandatory per `CLAUDE.md`).
- The shared expansion function's new test file (e.g., `tests/test_service_subtree.py`) is a plain pytest module within the existing flat tree — no conftest changes, no fixture additions beyond existing ones.
- Cross-filter equivalence (UNIFY-02 / D-15) extends `tests/test_list_pipelines.py` per planner decision — no new file needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `parent` filter end-to-end against live OmniFocus database | PARENT-01..08, WARN-01..05 | Real-database behavior (SAFE-01/02 forbids RealBridge in automated tests) | UAT via `uat/` scripts after phase ships; developer runs `/uat-regression` with new `parent`-filter suite. |
| `FILTERED_SUBTREE_WARNING` verbatim wording against agent UX | WARN-01 | Wording is judgment call; verbatim-lock is automated but agent-facing quality is manual | Manual review of warning text during UAT walkthrough. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none required here)
- [x] No watch-mode flags
- [x] Feedback latency < 15s (quick) / 90s (full)
- [x] `nyquist_compliant: true` set in frontmatter
- [x] `test_output_schema.py` included in pre-verification command (mandatory per `CLAUDE.md`)

**Approval:** approved 2026-04-20

---

## Validation Audit 2026-04-21

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

**Audit summary:** All 6 task rows in the Per-Task Verification Map map to existing, green automated tests. Per-command run results on audit date:

- `tests/test_service_subtree.py` — **10 passed**
- `tests/test_list_contracts.py + test_query_builder.py + test_bridge_only_repository.py + test_hybrid_repository.py + test_list_pipelines.py + test_output_schema.py` — **486 passed**
- `tests/test_list_contracts.py + test_descriptions.py + test_output_schema.py` — **184 passed**
- `tests/test_service_resolve.py + test_list_pipelines.py` — **177 passed** (incl. D-15 cross-filter equivalence gate)
- `tests/test_service_domain.py + test_list_pipelines.py` — **294 passed** (incl. em-dash U+2014 fidelity gates for WARN-01)

All 20 Phase 57 requirements (PARENT-01..09, UNIFY-01..06, WARN-01..05) are COVERED — no PARTIAL, no MISSING, no Manual-Only additions needed beyond those already captured at approval time (RealBridge-backed UAT, WARN-01 agent-UX wording review). `nyquist_compliant: true` reaffirmed.
