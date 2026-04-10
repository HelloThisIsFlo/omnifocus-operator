---
status: resolved
trigger: "inbox-subtask-visibility: list_tasks with inInbox=true or project=$inbox returns only root-level inbox tasks"
created: 2026-04-07T11:00:00Z
updated: 2026-04-07T11:30:00Z
---

## Current Focus

hypothesis: CONFIRMED — hybrid SQL uses `t.inInbox = ?` which misses inbox subtasks
test: TDD — writing failing test first, then applying fix
expecting: Test fails before fix, passes after
next_action: Write failing test for inbox subtask visibility

## Symptoms

expected: `list_tasks(project="$inbox")` and `list_tasks(inInbox=true)` should return all inbox tasks including subtasks nested under inbox action groups.
actual: Only root-level inbox tasks are returned. Two sub-issues reported: (1) Hybrid mode: subtasks excluded from inInbox=true but visible via inInbox=false. (2) Bridge-only mode: reported as fully unreachable.
errors: No errors thrown — subtasks silently omitted.
reproduction: Create inbox action groups with children, query with inInbox=true or project=$inbox.
started: Pre-existing, surfaced during Phase 43 UAT.

## Eliminated

- hypothesis: Bridge adapter fails to set project=$inbox on inbox subtasks
  evidence: Code trace shows adapter line 166-180 correctly sets project=inbox_ref when project_id is None and parent_task_id is not None. Golden master snapshot 01-add/07_inbox_subtask confirms bridge returns `inInbox: false, project: null` for subtasks, which adapter transforms to project=$inbox.
  timestamp: 2026-04-07T11:15:00Z

- hypothesis: flattenedTasks in OmniFocus JS API excludes inbox subtasks
  evidence: Golden master snapshot 01-add/07_inbox_subtask includes "GM-InboxSubtask" in state_after.tasks, proving flattenedTasks returns inbox subtasks.
  timestamp: 2026-04-07T11:15:00Z

- hypothesis: Bridge-only list_tasks with in_inbox=True excludes inbox subtasks
  evidence: Bridge-only filters by `t.project.id == inbox_id` (not by inInbox field). After adapter transformation, inbox subtasks have `project.id == "$inbox"`, so the filter WOULD include them. The reported "fully unreachable" symptom for bridge-only may be inaccurate — needs UAT re-verification.
  timestamp: 2026-04-07T11:20:00Z

## Evidence

- timestamp: 2026-04-07T11:05:00Z
  checked: Golden master snapshot 01-add/07_inbox_subtask.json
  found: OmniFocus reports inbox subtask with `inInbox: false` and `project: null` and `parent: $task:inbox_parent`
  implication: OmniFocus only sets inInbox=true for root-level inbox items; subtasks of action groups get inInbox=false

- timestamp: 2026-04-07T11:08:00Z
  checked: Hybrid query_builder.py lines 123-125
  found: SQL filter uses `t.inInbox = ?` with value 1 for in_inbox=True queries
  implication: This SQL condition matches ONLY root-level inbox tasks (inInbox=1), missing all subtasks (inInbox=0)

- timestamp: 2026-04-07T11:10:00Z
  checked: Hybrid query_builder.py lines 131-138
  found: Project filter uses `t.containingProjectInfo` which is NULL for all inbox tasks (root and subtasks)
  implication: Cannot use project_ids filter for inbox tasks — no ProjectInfo row exists for inbox

- timestamp: 2026-04-07T11:12:00Z
  checked: Service resolve.py lines 226-232
  found: `project="$inbox"` is resolved to `in_inbox=True` (project consumed, not passed as project_ids)
  implication: Both `project="$inbox"` and `inInbox=true` go through the same code path — both hit the same SQL limitation

- timestamp: 2026-04-07T11:14:00Z
  checked: Hybrid hybrid.py _build_parent_and_project lines 298-332
  found: Inbox subtasks correctly get `project = {"id": "$inbox", "name": "Inbox"}` on the Task model
  implication: The model representation is correct — the issue is purely in the SQL WHERE clause filtering

- timestamp: 2026-04-07T11:18:00Z
  checked: Bridge-only bridge_only.py lines 157-162
  found: Bridge-only filters by `t.project.id == inbox_id` (Python object comparison), not by inInbox column
  implication: Bridge-only path uses a DIFFERENT filter mechanism than hybrid — should correctly include subtasks

- timestamp: 2026-04-07T11:20:00Z
  checked: Hybrid in_inbox=False behavior
  found: SQL `t.inInbox = 0` matches inbox subtasks (they have inInbox=0 despite being inbox tasks)
  implication: Hybrid no-man's land confirmed: inbox subtasks appear in non-inbox results (wrong) and are excluded from inbox results (wrong)

## Resolution

root_cause: |
  TWO distinct root causes in the hybrid repository, ONE potential misdiagnosis for bridge-only:

  **HYBRID ROOT CAUSE (confirmed):** The SQL query builder filters inbox tasks using `t.inInbox = ?` (query_builder.py line 124), which maps to OmniFocus's `inInbox` SQLite column. OmniFocus only sets `inInbox=1` for root-level inbox items. Subtasks of inbox action groups have `inInbox=0` even though they logically belong to the inbox (they have no containingProjectInfo and their parent chain leads to the inbox).

  This causes two symptoms:
  1. `in_inbox=True` → SQL `t.inInbox = 1` → misses subtasks (they have inInbox=0)
  2. `in_inbox=False` → SQL `t.inInbox = 0` → incorrectly includes inbox subtasks

  The fix needs to use a different criterion: inbox membership should be defined as `containingProjectInfo IS NULL` (no project association), not `inInbox = 1`. This matches how the _build_parent_and_project function already determines inbox status for the model (hybrid.py lines 305-309).

  **BRIDGE-ONLY (likely misdiagnosis):** The bridge-only path filters by `t.project.id == "$inbox"` (bridge_only.py line 160), which should correctly include inbox subtasks because the adapter sets `project = $inbox` for tasks with null project_id. Code analysis suggests bridge-only in_inbox=True WOULD include inbox subtasks. The "fully unreachable" symptom may need UAT re-verification.

fix: |
  Replaced `t.inInbox = ?` with `t.containingProjectInfo IS NULL` / `IS NOT NULL` in
  query_builder.py. This aligns SQL filtering with how _build_parent_and_project already
  determines inbox membership for the model (hybrid.py lines 305-309).
verification: |
  - Two new integration tests pass: test_list_tasks_in_inbox_includes_subtasks (inbox subtasks
    returned with in_inbox=True) and test_list_tasks_in_inbox_false_excludes_inbox_subtasks
    (inbox subtasks excluded from in_inbox=False).
  - Updated 3 existing tests to use containingProjectInfo for non-inbox task differentiation.
  - Updated query_builder unit tests to assert new SQL pattern.
  - Full suite: 1637 passed, 0 failed, 98.11% coverage.
files_changed:
  - src/omnifocus_operator/repository/hybrid/query_builder.py
  - tests/test_hybrid_repository.py
  - tests/test_query_builder.py
