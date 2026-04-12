---
phase: 51-task-ordering
verified: 2026-04-12T14:00:00Z
status: passed
score: 5/5
overrides_applied: 0
---

# Phase 51: Task Ordering Verification Report

**Phase Goal:** Agents can see where each task sits among its siblings via an `order` field, and tasks are returned in correct outline order
**Verified:** 2026-04-12T14:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Task responses include an integer `order` field reflecting position within parent (1-based, gap-free) | VERIFIED | `Task.order: str | None = Field(default=None, description=ORDER_FIELD)` in `models/task.py`. Uses dotted notation (string not int — per D-01, LLM-readability choice). HybridRepository populates real dotted paths; BridgeOnlyRepository sets `None`. |
| 2 | Siblings under the same parent have sequential order values (1, 2, 3...) matching OmniFocus display order | VERIFIED | `_compute_dotted_orders()` builds per-parent counters (sequential 1-based). `test_siblings_have_sequential_order` asserts "1","2","3". `test_subtasks_have_dotted_order` asserts "1","1.1","1.2","2". CTE uses `rank` with `printf('%010d', rank+2147483648)` for correct sign-extended lexicographic sort. |
| 3 | `get_all` and `list_tasks` return tasks in outline order — siblings grouped under their parent, depth respected | VERIFIED | `_read_all` executes `_TASK_ORDER_CTE` SQL with `ORDER BY o.sort_path, t.persistentIdentifier`. `_list_tasks_sync` uses `_TASKS_DATA_BASE` (which embeds the CTE) + same ORDER BY. `test_list_tasks_returns_outline_order` asserts depth-first ["First","Child of First","Second"]. `test_get_all_returns_tasks_in_outline_order` asserts same pattern including inbox. |
| 4 | Inbox tasks appear after project tasks in get_all/list_tasks responses | VERIFIED | CTE second anchor uses `'ZZZZZZZZZZ/' || printf(...)` prefix for inbox root tasks, ensuring they sort after all project tasks lexicographically. `test_inbox_tasks_sort_after_project_tasks` asserts ["Project Task","Inbox Task"]. `test_get_all_returns_tasks_in_outline_order` confirms inbox last. |
| 5 | `order` field cannot be set via `edit_tasks` — it is read-only | VERIFIED | `EditTaskCommand.model_fields` has no `order` field — confirmed programmatically. Fields: ['id','name','flagged','note','due_date','defer_date','planned_date','estimated_minutes','repetition_rule','actions']. No `order` key in `EditTaskRepoPayload` either. |

**Score:** 5/5 truths verified

### Note on SC-1 Type

The ROADMAP says "integer `order` field" but the implementation uses `str | None` with dotted notation (e.g., `"2.3.1"`). This was an explicit design decision (D-01) captured in the CONTEXT doc before planning — the dotted string format was chosen over integer for LLM readability. This is not a deviation from intent, it is the intended design.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/omnifocus_operator/models/task.py` | Task model with order field | VERIFIED | `order: str | None = Field(default=None, description=ORDER_FIELD)` at line 22 |
| `src/omnifocus_operator/agent_messages/descriptions.py` | ORDER_FIELD constant, 3 tool docs updated | VERIFIED | `ORDER_FIELD` constant at line 99. `GET_TASK_TOOL_DOC`, `LIST_TASKS_TOOL_DOC`, `GET_ALL_TOOL_DOC` all reference `order` field |
| `src/omnifocus_operator/repository/bridge_only/adapter.py` | Sets order=None for degraded mode | VERIFIED | `raw["order"] = None` at line 218 inside `_adapt_task()` — only runs when `status` key present (idempotency preserved) |
| `src/omnifocus_operator/repository/hybrid/query_builder.py` | `_TASK_ORDER_CTE` and `_TASKS_DATA_BASE` | VERIFIED | `_TASK_ORDER_CTE` defined at line 135 (3-anchor recursive CTE). `_TASKS_DATA_BASE` at line 160 embeds CTE. ORDER BY uses `o.sort_path, t.persistentIdentifier` |
| `src/omnifocus_operator/repository/hybrid/hybrid.py` | CTE wired into all 3 read paths | VERIFIED | `_compute_dotted_orders()` at line 339, `_build_full_dotted_orders()` at line 379, `_compute_task_order()` at line 826. All three paths: `_read_all` (line 720), `_list_tasks_sync` (line 981), `_read_task` (line 819) |
| `tests/test_hybrid_repository.py` | 9 ordering tests in TestTaskOrdering | VERIFIED | `TestTaskOrdering` at line 3036 with 9 tests covering siblings, dotted paths, inbox namespace, outline order, sparse ordinals, pagination, get_task, get_all |
| `tests/test_cross_path_equivalence.py` | order excluded from cross-path comparison | VERIFIED | `assert_equivalent` uses `model_dump(exclude={"order"})` at line 966 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `Task.order` | `HybridRepository._read_all` | `_compute_dotted_orders(task_rows)` + `order=dotted_orders.get(...)` | WIRED | Line 729-737 in hybrid.py |
| `Task.order` | `HybridRepository._list_tasks_sync` | `_build_full_dotted_orders(conn)` + `order=dotted_orders.get(...)` | WIRED | Lines 981-991 in hybrid.py |
| `Task.order` | `HybridRepository._read_task` | `_compute_task_order(conn, row)` scoped CTE | WIRED | Lines 819-821 in hybrid.py |
| `_TASK_ORDER_CTE` | `query_builder.build_list_tasks_sql` | Embedded in `_TASKS_DATA_BASE` + `ORDER BY o.sort_path` | WIRED | Lines 299-302 in query_builder.py |
| `BridgeOnlyRepository` adapter | `Task.order` | `raw["order"] = None` in `_adapt_task()` | WIRED | Line 218 in adapter.py |
| `EditTaskCommand` | (no order field) | Field omitted from model | WIRED | Verified programmatically — field not present |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `HybridRepository._read_all` | `dotted_orders` | `_compute_dotted_orders(task_rows)` where `task_rows` comes from CTE SQL query | Yes — CTE reads `rank` column from Task table | FLOWING |
| `HybridRepository._list_tasks_sync` | `dotted_orders` | `_build_full_dotted_orders(conn)` runs full unfiltered CTE | Yes — real DB query, sparse ordinals preserved | FLOWING |
| `HybridRepository._read_task` | `order` | `_compute_task_order(conn, row)` scoped CTE | Yes — scoped to task's project or inbox namespace | FLOWING |
| `BridgeOnlyRepository` (via adapter) | `task["order"]` | Hardcoded `None` | Intentionally None — degraded mode signal per D-03 | FLOWING (by design) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Task model has order field | `uv run python -c "from omnifocus_operator.models.task import Task; print(Task.model_fields['order'].annotation)"` | `str | None` | PASS |
| `order` not in EditTaskCommand | `uv run python -c "from omnifocus_operator.contracts.use_cases.edit.tasks import EditTaskCommand; print('order' in EditTaskCommand.model_fields)"` | `False` | PASS |
| CTE has ZZZZZZZZZZ inbox prefix | `uv run python -c "from omnifocus_operator.repository.hybrid.query_builder import _TASK_ORDER_CTE; print('ZZZZZZZZZZ' in _TASK_ORDER_CTE)"` | `True` | PASS |
| TestTaskOrdering suite passes | `uv run pytest tests/test_hybrid_repository.py::TestTaskOrdering --no-cov -q` | `9 passed` | PASS |
| Full test suite passes | `uv run pytest --no-cov -q` | `2030 passed` | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| ORDER-01 | 51-01 | Task responses include `order` integer field | SATISFIED | `Task.order: str | None` field present, populated on all read paths |
| ORDER-02 | 51-02 | Sequential gap-free siblings | SATISFIED | `_compute_dotted_orders` + CTE rank-sorted rows = 1-based sequential per parent |
| ORDER-03 | 51-01 | `order` field read-only — not settable via edit_tasks | SATISFIED | `order` absent from `EditTaskCommand` and `EditTaskRepoPayload` |
| ORDER-04 | 51-02 | Outline order via recursive CTE | SATISFIED | `_TASK_ORDER_CTE` with 3 anchors wired into all 3 HybridRepository read paths |
| ORDER-05 | 51-02 | Inbox tasks sort after projects | SATISFIED | `ZZZZZZZZZZ/` prefix in inbox anchor of CTE; verified by ordering test |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `descriptions.py` | 401 | `# TODO(v1.5): Remove when built-in perspectives are supported` | Info | Pre-existing — not introduced in this phase |

No stubs or blocking anti-patterns found in phase-modified files.

### Human Verification Required

None. All success criteria are verifiable programmatically. The one behavior that requires live OmniFocus data (does the CTE produce the same rank order as the OmniFocus UI?) is explicitly out of automated scope (SAFE-02: UAT is human-initiated only). That is standard for all phases.

### Gaps Summary

No gaps. All 5 success criteria are met:

1. `order` field exists on Task model with `str | None` type and dotted notation semantics (the "integer" wording in ROADMAP SC-1 was superseded by D-01 before planning — this is the intended design, not a deviation).
2. Sequential gap-free ordinals are computed by `_compute_dotted_orders()` from CTE-sorted rows.
3. All three read paths (`get_all`, `list_tasks`, `get_task`) return tasks in CTE outline order.
4. Inbox tasks sort after projects via `ZZZZZZZZZZ/` prefix in the CTE.
5. `order` is absent from `EditTaskCommand` and `EditTaskRepoPayload` — structurally read-only.

---

_Verified: 2026-04-12T14:00:00Z_
_Verifier: Claude (gsd-verifier)_
