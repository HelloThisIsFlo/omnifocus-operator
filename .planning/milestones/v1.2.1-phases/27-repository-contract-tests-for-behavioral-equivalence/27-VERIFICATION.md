---
phase: 27-repository-contract-tests-for-behavioral-equivalence
verified: 2026-03-21T21:39:33Z
status: gaps_found
score: 7/10 must-haves verified
gaps:
  - truth: "CI contract tests replay golden master scenarios against InMemoryBridge and verify equivalence"
    status: partial
    reason: "Tests pass 17/17 but only because both the capture script and contract tests work at adapted (model-format) data level. InMemoryBridge never processes raw bridge output; the adapter (adapt_snapshot) is applied externally in the capture script before saving fixtures. The contract tests do NOT apply adapt_snapshot — they seed InMemoryBridge with already-adapted data and compare against already-adapted fixtures. Structural equivalence at raw bridge output level is untested."
    artifacts:
      - path: "uat/capture_golden_master.py"
        issue: "Calls adapt_snapshot on get_all output before saving fixtures (line 210). Fixtures store adapted/model-format data, not raw bridge output."
      - path: "tests/test_bridge_contract.py"
        issue: "Does not apply adapt_snapshot during replay. Seeds bridge with adapted data and compares adapted state. Cannot detect raw-format discrepancies between RealBridge and InMemoryBridge."
    missing:
      - "Either: remove adapt_snapshot from capture script (capture raw bridge output) and update InMemoryBridge to also return raw format"
      - "Or: explicitly document this as 'model-format contract tests' and acknowledge the raw-format gap as out of scope for this phase"
  - truth: "All existing tests pass without modification"
    status: failed
    reason: "Regression: tests/test_service.py::TestEditTask::test_move_to_project_ending fails because InMemoryBridge._resolve_parent now returns type='task' for projects (matching OmniFocus raw behavior), but adapt_snapshot (which would convert 'task'->'project' for the project root case) does not run on InMemoryBridge data."
    artifacts:
      - path: "tests/test_service.py"
        issue: "test_move_to_project_ending at line 490: asserts task.parent.type == 'project' but gets 'task'"
      - path: "tests/doubles/bridge.py"
        issue: "_resolve_parent returns type='task' for projects (line 115), which is correct raw-bridge behavior but breaks service-layer tests that expect adapted output"
    missing:
      - "Fix is tied to Gap 1: once adapt_snapshot is properly integrated (either in InMemoryBridge.send_command or removed from capture), this regression resolves"
      - "Interim fix: ensure service-layer tests use a bridge that returns adapted format, OR update test assertion to match actual InMemoryBridge behavior"
  - truth: "Golden master files contain only test-created data, no personal OmniFocus data"
    status: partial
    reason: "Cannot verify programmatically — requires inspection of actual captured fixture content and trust that filter_to_known_ids was applied correctly during capture. Mechanism is correctly wired in capture script."
    artifacts: []
    missing:
      - "Human spot-check: inspect tests/golden/scenario_01_add_inbox_task.json to confirm no personal OmniFocus IDs or task names appear"
human_verification:
  - test: "Inspect golden master fixtures for personal data"
    expected: "All entity names start with 'GM-' prefix; no unrecognized task/project/tag names appear in fixture files"
    why_human: "filter_to_known_ids mechanism is wired correctly, but actual fixture content can only be verified by human inspection of the JSON files"
---

# Phase 27: Repository Contract Tests Verification Report

**Phase Goal:** Repository contract tests for behavioral equivalence — golden master captured from RealBridge, CI contract tests verify InMemoryBridge matches
**Verified:** 2026-03-21T21:39:33Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths — Plan 01

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | InMemoryBridge resolves parent to {type, id, name} dict when add_task has parent param | VERIFIED | `_resolve_parent` helper at line 106 of bridge.py; `test_add_task_with_parent_resolves_project` passes |
| 2 | InMemoryBridge resolves tag names from internal _tags list when edit_task adds tags | VERIFIED | `_resolve_tag_name` called at line 236 of bridge.py; `test_edit_task_add_tags_resolves_name_from_internal_tags` passes |
| 3 | InMemoryBridge resolves tags from internal _tags list when add_task has tagIds param | VERIFIED | `params.get("tagIds", [])` at line 152; `test_add_task_with_tag_ids_resolves_names` passes |
| 4 | normalize_for_comparison strips dynamic fields from task/project/tag dicts | VERIFIED | Function exists at normalize.py:60; DYNAMIC_*_FIELDS constants defined; entity_type dispatch wired |
| 5 | filter_to_known_ids returns only entities matching provided ID sets | VERIFIED | Function exists at normalize.py:94; all three ID sets used in filtering |

**Plan 01 Score:** 5/5 truths verified

### Observable Truths — Plan 02

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | User can run `uv run python uat/capture_golden_master.py` and get guided through golden master capture | VERIFIED | Script exists; `input(` prompts present; `async def main()` + `asyncio.run(main())` entry point wired; README documents usage |
| 2 | Capture script creates golden master JSON files in tests/golden/ | VERIFIED | 17 scenario files + initial_state.json exist in tests/golden/ |
| 3 | CI contract tests replay golden master scenarios against InMemoryBridge and verify equivalence | PARTIAL | 17/17 scenarios pass, but both capture script and replay operate at adapted (model-format) level — see Gap 1 |
| 4 | Golden master files contain only test-created data, no personal OmniFocus data | PARTIAL | filter_to_known_ids is wired in capture script; human spot-check of fixture content needed |
| 5 | All test-created data consolidated under one deletable parent at end of capture | VERIFIED | consolidation via moveTo loop present in capture script |

**Plan 02 Score:** 3/5 truths verified (2 partial)

**Overall Score:** 7/10 truths verified (2 partial, 1 full regression)

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/golden/__init__.py` | Package init exporting normalize/filter helpers | VERIFIED | Exports all 7 symbols including normalize_state |
| `tests/golden/normalize.py` | normalize_for_comparison, normalize_response, normalize_state, filter_to_known_ids | VERIFIED | All 4 functions + 3 DYNAMIC_* constants present |
| `tests/golden/README.md` | Documents golden master directory | VERIFIED | Contains capture_golden_master.py reference and GOLD-01 mention |
| `tests/doubles/bridge.py` | InMemoryBridge with parent + tag resolution | VERIFIED | _resolve_parent and _resolve_tag_name helpers, add_task + edit_task updated |
| `tests/test_stateful_bridge.py` | New gap-fix tests | VERIFIED | 7 new tests present (parent_resolves_project, parent_resolves_task, parent_unknown_falls_back, tag_ids_resolves_names, tag_ids_unknown_falls_back, add_tags_resolves_name_from_internal_tags) |
| `uat/capture_golden_master.py` | Interactive guided capture script | VERIFIED | Exists, valid Python, RealBridge + adapt_snapshot + normalize imports present |
| `tests/test_bridge_contract.py` | CI contract tests | VERIFIED | TestBridgeContract class with parametrized per-scenario tests; 17/17 pass |
| `tests/golden/initial_state.json` | Seeded state file | VERIFIED | File exists (written by capture script) |
| `tests/golden/scenario_01_add_inbox_task.json` through `scenario_17_move_to_inbox.json` | 17 golden master scenario files | VERIFIED | All 17 files present |
| `uat/README.md` | Updated with capture_golden_master.py section | VERIFIED | Section `### capture_golden_master.py (Phase 27)` at line 36 |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| tests/golden/normalize.py | tests/test_bridge_contract.py | `from tests.golden.normalize import` | WIRED | Lines 25-29 of test_bridge_contract.py |
| tests/golden/normalize.py | uat/capture_golden_master.py | `from tests.golden.normalize import` | WIRED | Lines 21-25 of capture_golden_master.py |
| tests/doubles/bridge.py | tests/test_bridge_contract.py | `from tests.doubles import InMemoryBridge` | WIRED | Line 24 of test_bridge_contract.py |
| uat/capture_golden_master.py | tests/golden/scenario_*.json | writes JSON fixture files | WIRED | `json.dump` + GOLDEN_DIR path in capture script |
| tests/test_bridge_contract.py | tests/golden/scenario_*.json | loads and replays scenarios | WIRED | `GOLDEN_DIR.glob("scenario_*.json")` at line 64 |
| tests/doubles/bridge.py (InMemoryBridge._resolve_parent) | returns type="task" for projects | OmniFocus raw-format behavior | WIRED but breaks service-layer adapter assumption | Causes regression in test_service.py (see Gaps) |

---

## Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| INFRA-13 | 27-01-PLAN, 27-02-PLAN | Golden master of expected bridge behavior captured from RealBridge via UAT and committed to repo | SATISFIED | 17 scenario files + initial_state.json in tests/golden/; capture script in uat/ |
| INFRA-14 | 27-01-PLAN, 27-02-PLAN | CI contract tests verify InMemoryBridge output matches the committed golden master | PARTIAL | 17/17 contract scenarios pass; however, both sides operate at adapted format level, not raw bridge format — behavioral equivalence at adapter input level is untested |

No orphaned requirements — both INFRA-13 and INFRA-14 are claimed by phase 27 plans.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| tests/doubles/bridge.py | 115 | `return {"type": "task", "id": container_id, "name": ""}` for project parent | Warning | Returns raw-bridge format (correct per golden master) but breaks service-layer tests that call `adapt_snapshot` downstream — mismatch between InMemoryBridge and what tests/services expect |
| uat/capture_golden_master.py | 210 | `adapt_snapshot(raw)` applied before saving fixtures | Warning | Documented Gap 1 from SUMMARY-02: golden master stores model-format data, not raw bridge output |

---

## Human Verification Required

### 1. Spot-check golden master fixture for personal data

**Test:** Open `tests/golden/scenario_01_add_inbox_task.json` and scan all entity names in the `state_after` field.
**Expected:** All task names start with `GM-`, all project names are `GM-TestProject`, all tag names are `GM-Tag1` or `GM-Tag2`. No personal OmniFocus tasks, projects, or tags appear.
**Why human:** The `filter_to_known_ids` mechanism is wired correctly and functioned during capture. Verification requires reading the actual JSON content and recognizing whether any name is personal data.

---

## Gaps Summary

**Two substantive gaps block full goal achievement:**

**Gap 1 — Adapter applied during capture, not during replay:** The golden master stores model-format data (after `adapt_snapshot`). The CI contract tests seed InMemoryBridge with this already-adapted data and compare adapted output. This means the contract tests verify that InMemoryBridge preserves model-format fields across write operations, not that InMemoryBridge produces the same raw-format output as RealBridge. The distinction matters: if `adapt_snapshot` has a bug or silent no-op (see SUMMARY-02's mention of SEED-004), the golden master will never catch it. Root cause: `_get_all_adapted` in the capture script calls `adapt_snapshot` before returning to the scenario capture loop.

**Gap 2 — Regression in test_service.py:** `TestEditTask::test_move_to_project_ending` fails because `_resolve_parent` now returns `type: "task"` for project parents (correct OmniFocus raw behavior, now consistent with golden master). However, the service-layer test calls the repository which wraps InMemoryBridge, and the bridge adapter (`adapt_snapshot`) that would normalize `"task"` → `"project"` for project root parents does not run on InMemoryBridge output. This is the exact consequence of Gap 1: InMemoryBridge now produces raw-format output but the service-layer tests expect adapted output. The fix for Gap 1 will resolve this regression.

**These gaps are related** — both stem from the same root cause: the boundary between raw-bridge format and adapted format is blurred. Fix Gap 1 (decide where the adapter runs) and Gap 2 resolves automatically.

---

_Verified: 2026-03-21T21:39:33Z_
_Verifier: Claude (gsd-verifier)_
