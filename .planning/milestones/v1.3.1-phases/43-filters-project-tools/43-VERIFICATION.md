---
phase: 43-filters-project-tools
verified: 2026-04-07T13:00:00Z
status: passed
score: 10/10
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 7/7
  gaps_closed: []
  gaps_remaining: []
  regressions: []
  note: "Previous verification predated Plan 03 (bridge-only fix). Re-verification adds Plan 03 must-haves and confirms all 3 plans together. Test count moved from 1628 to 1638."
---

# Phase 43: Filters & Project Tools — Verification Report

**Phase Goal:** Agents can filter tasks by `$inbox` as a project, with contradictory filter detection, correct project tool behavior, and complete tool documentation for $inbox usage.
**Verified:** 2026-04-07T13:00:00Z
**Status:** PASSED
**Re-verification:** Yes — previous verification predated Plan 03 (bridge-only adapter fix)

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `list_tasks(project="$inbox")` returns same tasks as `inInbox: true` | VERIFIED | `_ListTasksPipeline.execute()` calls `resolve_inbox` at line 301 which converts `project="$inbox"` to `in_inbox=True, project=None`. `self._in_inbox` flows into `_build_repo_query` at line 352. `TestListTasksInboxFilter` confirms. |
| 2 | `list_tasks(project="inbox")` matches only real projects, NOT system inbox | VERIFIED | `resolve_inbox` only intercepts `$`-prefixed values. Bare "inbox" flows through `_resolve_project` to `resolve_filter` (name substring). `test_bare_inbox_matches_project_name_not_system` confirms. |
| 3 | Contradictory filters raise error; redundant combination accepted silently | VERIFIED | `CONTRADICTORY_INBOX_FALSE` raised for `$inbox + inInbox=false`; `CONTRADICTORY_INBOX_PROJECT` for `inInbox=true + real project`; `($inbox, inInbox=true)` returns `(True, None)` silently. Tests in `TestResolveInbox` cover all cases. |
| 4 | `get_project("$inbox")` returns a descriptive error | VERIFIED | `Resolver.lookup_project` at line 197: `if project_id.startswith(SYSTEM_LOCATION_PREFIX): raise ValueError(GET_PROJECT_INBOX_ERROR)`. Raises for any `$`-prefix. `TestLookupProjectInboxGuard` covers `$inbox`, `$trash`, normal ID. |
| 5 | `list_projects` never includes inbox; search matching "Inbox" triggers warning | VERIFIED | PROJ-02 no-code: inbox is virtual, never in SQLite or bridge. PROJ-03: `_check_inbox_search_warning()` appends `LIST_PROJECTS_INBOX_WARNING` when search term is a substring of "Inbox". `TestListProjectsInboxWarning` covers warn/no-warn cases. |
| 6 | Descriptions document `$inbox` usage in relevant fields | VERIFIED | `$inbox` appears in 8 locations in `descriptions.py` (lines 134, 225, 230, 353, 360, 432, 443, 535). Filter field descriptions `PROJECT_FILTER_DESC` and `IN_INBOX_FILTER_DESC` intentionally omit `$inbox` per D-21. |
| 7 | `get_project` description mentions that `$inbox` returns an error | VERIFIED | `GET_PROJECT_TOOL_DOC` at line 360: `"$inbox is not a real project and cannot be looked up here — it has no review schedule..."` |
| 8 | Bridge-only `list_tasks` never returns project root tasks as task entries | VERIFIED | `adapt_snapshot` lines 379-381 filter tasks whose ID is in `project_id_set` (keys of `project_names` dict). `TestProjectRootTaskFiltering` (3 tests) in `test_adapter.py`. |
| 9 | Bridge-only `get_all` excludes project root tasks from tasks list | VERIFIED | Same `adapt_snapshot` filter applies to all task output paths. `TestProjectRootTaskExclusion.test_get_all_excludes_project_root_tasks` in `test_bridge_only_repository.py` confirms end-to-end. |
| 10 | Bridge-only and hybrid (SQL) paths return equivalent task lists | VERIFIED | SQL path excludes project roots via `LEFT JOIN ProjectInfo WHERE pi.task IS NULL`. Bridge-only now mirrors this with `project_id_set` filtering. `TestProjectRootTaskExclusion.test_list_tasks_excludes_project_root_tasks` confirms. |

**Score:** 10/10 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/omnifocus_operator/agent_messages/errors.py` | `CONTRADICTORY_INBOX_FALSE`, `CONTRADICTORY_INBOX_PROJECT`, `GET_PROJECT_INBOX_ERROR` | VERIFIED | All three constants present at lines 156, 160, 167 |
| `src/omnifocus_operator/agent_messages/warnings.py` | `LIST_PROJECTS_INBOX_WARNING` | VERIFIED | Present at line 136 |
| `src/omnifocus_operator/agent_messages/descriptions.py` | `GET_PROJECT_TOOL_DOC` with `$inbox` mention | VERIFIED | `$inbox is not a real project...` paragraph at line 360 |
| `src/omnifocus_operator/service/resolve.py` | `resolve_inbox` method; `lookup_project` `$`-prefix guard | VERIFIED | `resolve_inbox` at line 217; guard at lines 197-198 |
| `src/omnifocus_operator/service/service.py` | `_ListTasksPipeline` calls `resolve_inbox`; `_ListProjectsPipeline` has `_check_inbox_search_warning` | VERIFIED | Lines 301 and 388 respectively |
| `src/omnifocus_operator/repository/bridge_only/adapter.py` | Project root task filtering in `adapt_snapshot` | VERIFIED | Lines 379-381; `project_id_set` set-based filter after name dicts built |
| `tests/test_service_resolve.py` | `TestResolveInbox` (10 methods), `TestLookupProjectInboxGuard` (3 methods) | VERIFIED | Both classes present |
| `tests/test_list_pipelines.py` | `TestListTasksInboxFilter` (6 scenarios), `TestListProjectsInboxWarning` (4 scenarios) | VERIFIED | Both classes present |
| `tests/test_adapter.py` | `TestProjectRootTaskFiltering` with project root exclusion tests | VERIFIED | Class at line 793; 3 test methods |
| `tests/test_bridge_only_repository.py` | `TestProjectRootTaskExclusion` integration tests | VERIFIED | Class at line 478; 2 test methods |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `service.py _ListTasksPipeline.execute` | `resolve.py resolve_inbox` | `self._resolver.resolve_inbox(self._query.in_inbox, self._query.project)` | WIRED | Line 301-303; output bound to `self._in_inbox, self._project_to_resolve` |
| `service.py _ListTasksPipeline._resolve_project` | `self._project_to_resolve` | Uses `self._project_to_resolve` not `self._query.project` | WIRED | Lines 318-329; `$inbox` never reaches `resolve_filter` |
| `service.py _ListTasksPipeline._build_repo_query` | `self._in_inbox` | Passes `self._in_inbox` to `ListTasksRepoQuery.in_inbox` | WIRED | Line 352 |
| `resolve.py lookup_project` | `errors.py GET_PROJECT_INBOX_ERROR` | `raise ValueError(GET_PROJECT_INBOX_ERROR)` | WIRED | Lines 197-198 |
| `service.py _ListProjectsPipeline._check_inbox_search_warning` | `warnings.py LIST_PROJECTS_INBOX_WARNING` | `self._warnings.append(LIST_PROJECTS_INBOX_WARNING)` | WIRED | Lines 388-395 |
| `adapter.py adapt_snapshot` | `project_names` dict | Filter `raw["tasks"]` excluding IDs in `project_id_set` | WIRED | Lines 374 (build), 379-381 (filter) |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `_ListTasksPipeline._build_repo_query` | `self._in_inbox` | Set by `resolve_inbox` from `self._query.in_inbox` / `$inbox` detection | Yes — flows into `ListTasksRepoQuery.in_inbox` passed to `self._repository.list_tasks` | FLOWING |
| `_ListProjectsPipeline._check_inbox_search_warning` | `self._query.search` | Direct from `ListProjectsQuery.search` input | Yes — warning appended to `self._warnings` which is included in `_result_from_repo()` | FLOWING |
| `adapt_snapshot` project root filter | `project_id_set` | Built from `project_names` dict (keys of raw projects) | Yes — filters `raw["tasks"]` before adaptation loops | FLOWING |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Inbox-related tests pass | `uv run pytest tests/test_service_resolve.py tests/test_list_pipelines.py tests/test_adapter.py tests/test_bridge_only_repository.py -x -q --no-cov` | 213 passed | PASS |
| Full test suite green | `uv run pytest -x -q --no-cov` | 1638 passed | PASS |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| FILT-01 | 43-01, 43-03 | `list_tasks(project="$inbox")` returns same as `inInbox: true`; bridge-only parity | SATISFIED | `resolve_inbox` converts `$inbox` to `in_inbox=True`; `adapt_snapshot` filter ensures bridge-only equivalence |
| FILT-02 | 43-01 | `list_tasks(project="inbox")` does NOT match system inbox | SATISFIED | Bare "inbox" bypasses `resolve_inbox`; resolved by name via `resolve_filter` |
| FILT-03 | 43-01 | `$inbox` + `inInbox: false` → error | SATISFIED | `CONTRADICTORY_INBOX_FALSE` raised in `resolve_inbox` |
| FILT-04 | 43-01 | `$inbox` + `inInbox: true` → accepted silently | SATISFIED | `resolve_inbox` returns `(True, None)` without error |
| FILT-05 | 43-01 | `inInbox: true` + real project → error | SATISFIED | `CONTRADICTORY_INBOX_PROJECT` raised in `resolve_inbox` |
| PROJ-01 | 43-02 | `get_project("$inbox")` returns descriptive error | SATISFIED | `lookup_project` `$`-prefix guard raises `GET_PROJECT_INBOX_ERROR` |
| PROJ-02 | 43-02 | `list_projects` never includes inbox | SATISFIED | No-code; inbox is virtual (not in SQLite or bridge) |
| PROJ-03 | 43-02 | `list_projects` search matching "Inbox" → warning | SATISFIED | `_check_inbox_search_warning` appends `LIST_PROJECTS_INBOX_WARNING` |
| NRES-07 | 43-02 | List filter fields accept entity names | SATISFIED | Already satisfied by v1.3 `resolve_filter`; `[x]` at REQUIREMENTS.md line 66 |
| DESC-03 | 43-02 | Descriptions document `$inbox` usage in relevant fields | SATISFIED | `$inbox` in 8 locations in `descriptions.py`; filter field omission intentional per D-21 |
| DESC-04 | 43-02 | `get_project` description mentions `$inbox` error behavior | SATISFIED | `GET_PROJECT_TOOL_DOC` line 360-362 contains the inbox error paragraph |

**Note:** FILT-01 through FILT-05, PROJ-01 through PROJ-03, DESC-03, and DESC-04 remain `[ ]` checkboxes in REQUIREMENTS.md. Per project convention, these are milestone-level updates — only NRES-07 was explicitly required by the plan to be checked, and it is. This is not a gap.

---

## Anti-Patterns Found

No blockers found.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `descriptions.py` | 325 | `# TODO(v1.5): Remove when built-in perspectives are supported` | Info | Pre-existing, unrelated to Phase 43 |

---

## Human Verification Required

None. All must-haves verified programmatically.

---

_Verified: 2026-04-07T13:00:00Z_
_Verifier: Claude (gsd-verifier)_
