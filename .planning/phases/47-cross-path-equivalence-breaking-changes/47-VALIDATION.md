---
phase: 47
slug: cross-path-equivalence-breaking-changes
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-08
validated: 2026-04-09
---

# Phase 47 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/ -x -q --timeout=10` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q --timeout=10`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 47-01-01 | 01 | 1 | BREAK-03, BREAK-06, BREAK-08 | T-47-01 | Pydantic StrEnum rejects invalid values | unit | `uv run pytest tests/test_service_domain.py tests/test_list_contracts.py -x -q` | ✅ | ✅ green |
| 47-01-02 | 01 | 1 | BREAK-04, BREAK-05, BREAK-07 | T-47-02 | Hints are educational, non-blocking | unit | `uv run pytest tests/test_service_domain.py tests/test_date_filter_contracts.py tests/test_list_pipelines.py tests/test_resolve_dates.py -x -q` | ✅ | ✅ green |
| 47-02-01 | 02 | 2 | EXEC-10, EXEC-11 | T-47-03 | Test data is synthetic | integration | `uv run pytest tests/test_cross_path_equivalence.py -x -q` | ✅ | ✅ green |
| 47-02-02 | 02 | 2 | EXEC-10, EXEC-11 | T-47-03 | Test data is synthetic | integration | `uv run pytest tests/test_cross_path_equivalence.py -x -q -k "DateFilter"` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- Existing infrastructure covers all phase requirements. Test files for cross-path equivalence, contracts, and service already exist.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Tool descriptions render correctly in MCP client | BREAK-07 | Agent-facing display quality is subjective | Inspect `list_tasks` tool description in Claude Desktop inspector |

---

## Developer-Accepted Overrides

Three requirements produce generic Pydantic validation errors rather than custom educational messages. The developer accepted these deviations before planning (CONTEXT.md D-05, D-09) — project is pre-release with zero external users, so migration guidance is unnecessary.

| Requirement | Original Intent | Actual Behavior | Override Reason |
|-------------|----------------|-----------------|-----------------|
| BREAK-01 | Educational error for `urgency` filter | Generic "Extra inputs are not permitted" | `urgency` never existed as a filter; `extra="forbid"` handles it |
| BREAK-02 | Educational error for `completed: true` | Generic Pydantic enum error | Boolean never accepted; Pydantic type validation rejects it |
| BREAK-06/08 | Educational error for `availability: "all"/"any"` | Generic "Input should be 'available', 'blocked' or 'remaining'" | Pre-release project; no users to migrate |

See `47-VERIFICATION.md` for full override documentation.

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

## Validation Audit 2026-04-09

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Developer overrides | 3 (pre-existing in VERIFICATION.md) |
