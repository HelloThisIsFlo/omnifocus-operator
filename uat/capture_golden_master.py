"""Golden master capture: record RealBridge behavior for contract tests.

This script is for HUMAN execution only. Do NOT run from CI or agents.
See uat/README.md for details and safety rules (SAFE-01, SAFE-02).

Usage:
    uv run python uat/capture_golden_master.py
"""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from omnifocus_operator.bridge.real import DEFAULT_IPC_DIR, RealBridge
from tests.golden_master.normalize import (
    UNCOMPUTED_PROJECT_FIELDS,
    UNCOMPUTED_TASK_FIELDS,
    VOLATILE_PROJECT_FIELDS,
    VOLATILE_TAG_FIELDS,
    VOLATILE_TASK_FIELDS,
    filter_to_known_ids,
    normalize_response,
    normalize_state,
)

GOLDEN_MASTER_DIR = Path(__file__).resolve().parent.parent / "tests" / "golden_master"
SNAPSHOTS_DIR = GOLDEN_MASTER_DIR / "snapshots"


# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------

# Placeholders filled in at runtime after manual setup and add_task responses.
GM_PROJECT_ID: str = ""
GM_PROJECT2_ID: str = ""
GM_DATED_PROJECT_ID: str = ""
GM_TAG1_ID: str = ""
GM_TAG2_ID: str = ""

# Phase 56 task-property-surface placeholders (09-task-property-surface/).
# Three projects exercising the HIER-05 project.type precedence (parallel,
# sequential, singleActions) and one pre-seeded task with an attachment
# (attachments cannot be created via OmniJS — manual-drop required).
GM_PHASE56_PARALLEL_PROJECT_ID: str = ""
GM_PHASE56_SEQUENTIAL_PROJECT_ID: str = ""
GM_PHASE56_SINGLE_ACTIONS_PROJECT_ID: str = ""
GM_PHASE56_ATTACHED_TASK_ID: str = ""

# Task IDs accumulated from add_task responses
TASK_IDS: dict[str, str] = {}

# All known IDs for filtering get_all
known_task_ids: set[str] = set()
known_project_ids: set[str] = set()
known_tag_ids: set[str] = set()

# Pre-seeded task IDs that must NOT be moved into the Phase 5 cleanup
# container (e.g. GM-Phase56-Attached — the human invested manual effort
# attaching a file; the next capture re-uses the same task in place).
_preserved_task_ids: set[str] = set()

# Symbolic ID map: real OmniFocus ID → stable symbolic ref (e.g. "$project:test_project").
# Populated during Phase 2 (projects/tags/external refs) and Phase 4 (tasks).
# Applied before writing fixtures so re-captures produce identical output.
_id_map: dict[str, str] = {}


def _build_scenarios() -> list[dict[str, Any]]:
    """Build ~52 scenario definitions across 7 categories using captured IDs."""
    return [
        # =================================================================
        # 01-add/ (7 scenarios)
        # =================================================================
        {
            "folder": "01-add",
            "file": "01_inbox_task",
            "scenario": "01-add/01_inbox_task",
            "description": "Create a basic task in inbox with no optional fields",
            "operation": "add_task",
            "params": {"name": "GM-InboxTask"},
            "capture_id_as": "inbox_task",
        },
        {
            "folder": "01-add",
            "file": "02_with_parent",
            "scenario": "01-add/02_with_parent",
            "description": "Create a task under a project",
            "operation": "add_task",
            "params_fn": lambda: {"name": "GM-ParentTask", "parent": GM_PROJECT_ID},
            "capture_id_as": "parent_task",
        },
        {
            "folder": "01-add",
            "file": "03_all_fields",
            "scenario": "01-add/03_all_fields",
            "description": "Create a task with all optional fields set",
            "operation": "add_task",
            "params_fn": lambda: {
                "name": "GM-AllFields",
                "parent": GM_PROJECT_ID,
                "flagged": True,
                "dueDate": "2026-12-15T17:00:00.000Z",
                "deferDate": "2026-12-10T09:00:00.000Z",
                "plannedDate": "2026-12-12T09:00:00.000Z",
                "estimatedMinutes": 30,
                "note": "Golden master test note",
            },
            "capture_id_as": "all_fields_task",
        },
        {
            "folder": "01-add",
            "file": "04_with_tags",
            "scenario": "01-add/04_with_tags",
            "description": "Create a task with two tags",
            "operation": "add_task",
            "params_fn": lambda: {
                "name": "GM-TaggedTask",
                "tagIds": [GM_TAG1_ID, GM_TAG2_ID],
            },
            "capture_id_as": "tagged_task",
        },
        {
            "folder": "01-add",
            "file": "05_parent_and_tags",
            "scenario": "01-add/05_parent_and_tags",
            "description": "Create a task with parent and one tag",
            "operation": "add_task",
            "params_fn": lambda: {
                "name": "GM-ParentTagTask",
                "parent": GM_PROJECT_ID,
                "tagIds": [GM_TAG1_ID],
            },
            "capture_id_as": "parent_tag_task",
        },
        {
            "folder": "01-add",
            "file": "06_max_payload",
            "scenario": "01-add/06_max_payload",
            "description": "Create a task with all fields, parent, and tags (maximum payload)",
            "operation": "add_task",
            "params_fn": lambda: {
                "name": "GM-MaxPayload",
                "parent": GM_PROJECT_ID,
                "tagIds": [GM_TAG1_ID, GM_TAG2_ID],
                "flagged": True,
                "dueDate": "2026-12-20T17:00:00.000Z",
                "deferDate": "2026-12-15T09:00:00.000Z",
                "plannedDate": "2026-12-18T09:00:00.000Z",
                "estimatedMinutes": 60,
                "note": "Max payload test",
            },
            "capture_id_as": "max_payload_task",
        },
        {
            "folder": "01-add",
            "file": "07_inbox_subtask",
            "scenario": "01-add/07_inbox_subtask",
            "description": "Create a subtask under an inbox task (no project)",
            "operation": "add_task",
            "params": {"name": "GM-InboxParent"},
            "capture_id_as": "inbox_parent",
            "followup": {
                "operation": "add_task",
                "params_fn": lambda: {
                    "name": "GM-InboxSubtask",
                    "parent": TASK_IDS["inbox_parent"],
                },
                "capture_id_as": "inbox_subtask",
            },
        },
        # =================================================================
        # 02-edit/ (10 scenarios)
        # =================================================================
        {
            "folder": "02-edit",
            "file": "01_rename",
            "scenario": "02-edit/01_rename",
            "description": "Rename a task",
            "operation": "add_task",
            "params": {"name": "GM-RenameTarget"},
            "capture_id_as": "rename_target",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["rename_target"],
                    "name": "GM-RenameTarget-Renamed",
                },
            },
        },
        {
            "folder": "02-edit",
            "file": "02_set_note",
            "scenario": "02-edit/02_set_note",
            "description": "Set note on a task",
            "operation": "add_task",
            "params": {"name": "GM-NoteTarget"},
            "capture_id_as": "note_target",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["note_target"],
                    "note": "Added note via edit",
                },
            },
        },
        # note: OmniFocus rejects note=null at the bridge level.
        # Our service layer converts null -> "" (see domain.py:92), but the
        # bridge itself requires a non-null value. Only empty string is valid.
        {
            "folder": "02-edit",
            "file": "03_clear_note_empty",
            "scenario": "02-edit/03_clear_note_empty",
            "description": "Clear note using empty string",
            "operation": "edit_task",
            "params_fn": lambda: {"id": TASK_IDS["note_target"], "note": ""},
        },
        {
            "folder": "02-edit",
            "file": "04_flag",
            "scenario": "02-edit/04_flag",
            "description": "Flag a task",
            "operation": "add_task",
            "params": {"name": "GM-FlagTarget"},
            "capture_id_as": "flag_target",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["flag_target"],
                    "flagged": True,
                },
            },
        },
        {
            "folder": "02-edit",
            "file": "05_unflag",
            "scenario": "02-edit/05_unflag",
            "description": "Unflag a task",
            "operation": "edit_task",
            "params_fn": lambda: {"id": TASK_IDS["flag_target"], "flagged": False},
        },
        {
            "folder": "02-edit",
            "file": "06_set_dates",
            "scenario": "02-edit/06_set_dates",
            "description": "Set due and defer dates on a task",
            "operation": "add_task",
            "params": {"name": "GM-DateTarget"},
            "capture_id_as": "date_target",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["date_target"],
                    "dueDate": "2026-12-20T17:00:00.000Z",
                    "deferDate": "2026-12-18T09:00:00.000Z",
                },
            },
        },
        {
            "folder": "02-edit",
            "file": "07_clear_dates",
            "scenario": "02-edit/07_clear_dates",
            "description": "Clear due and defer dates (null means clear)",
            "operation": "edit_task",
            "params_fn": lambda: {
                "id": TASK_IDS["date_target"],
                "dueDate": None,
                "deferDate": None,
            },
        },
        {
            "folder": "02-edit",
            "file": "08_set_estimated",
            "scenario": "02-edit/08_set_estimated",
            "description": "Set estimated minutes on a task",
            "operation": "add_task",
            "params": {"name": "GM-EstimateTarget"},
            "capture_id_as": "estimate_target",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["estimate_target"],
                    "estimatedMinutes": 45,
                },
            },
        },
        {
            "folder": "02-edit",
            "file": "09_clear_estimated",
            "scenario": "02-edit/09_clear_estimated",
            "description": "Clear estimated minutes (null means clear)",
            "operation": "edit_task",
            "params_fn": lambda: {
                "id": TASK_IDS["estimate_target"],
                "estimatedMinutes": None,
            },
        },
        {
            "folder": "02-edit",
            "file": "10_set_planned_date",
            "scenario": "02-edit/10_set_planned_date",
            "description": "Set planned date on a task",
            "operation": "add_task",
            "params": {"name": "GM-PlannedTarget"},
            "capture_id_as": "planned_target",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["planned_target"],
                    "plannedDate": "2026-12-25T09:00:00.000Z",
                },
            },
        },
        # =================================================================
        # 03-move/ (9 scenarios)
        # =================================================================
        {
            "folder": "03-move",
            "file": "01_to_project_ending",
            "scenario": "03-move/01_to_project_ending",
            "description": "Move task to project (ending position)",
            "operation": "add_task",
            "params": {"name": "GM-MoveEndTarget"},
            "capture_id_as": "move_end_target",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["move_end_target"],
                    "moveTo": {"position": "ending", "containerId": GM_PROJECT_ID},
                },
            },
        },
        {
            "folder": "03-move",
            "file": "02_to_inbox",
            "scenario": "03-move/02_to_inbox",
            "description": "Move task back to inbox",
            "operation": "edit_task",
            "params_fn": lambda: {
                "id": TASK_IDS["move_end_target"],
                "moveTo": {"position": "ending", "containerId": None},
            },
        },
        {
            "folder": "03-move",
            "file": "03_to_beginning",
            "scenario": "03-move/03_to_beginning",
            "description": "Move task to project (beginning position)",
            "operation": "add_task",
            "params": {"name": "GM-MoveBeginTarget"},
            "capture_id_as": "move_begin_target",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["move_begin_target"],
                    "moveTo": {"position": "beginning", "containerId": GM_PROJECT_ID},
                },
            },
        },
        {
            "folder": "03-move",
            "file": "04_after_anchor",
            "scenario": "03-move/04_after_anchor",
            "description": "Move task to position after an anchor task",
            "operation": "edit_task",
            "params_fn": lambda: {
                "id": TASK_IDS["move_begin_target"],
                "moveTo": {"position": "after", "anchorId": TASK_IDS["parent_task"]},
            },
        },
        {
            "folder": "03-move",
            "file": "05_before_anchor",
            "scenario": "03-move/05_before_anchor",
            "description": "Move task to position before an anchor task",
            "operation": "add_task",
            "params": {"name": "GM-MoveBeforeTarget"},
            "capture_id_as": "move_before_target",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["move_before_target"],
                    "moveTo": {"position": "before", "anchorId": TASK_IDS["parent_task"]},
                },
            },
        },
        {
            "folder": "03-move",
            "file": "06_between_projects",
            "scenario": "03-move/06_between_projects",
            "description": "Move task from one project to another",
            "operation": "add_task",
            "params_fn": lambda: {
                "name": "GM-CrossProjectTarget",
                "parent": GM_PROJECT_ID,
            },
            "capture_id_as": "cross_project_target",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["cross_project_target"],
                    "moveTo": {"position": "ending", "containerId": GM_PROJECT2_ID},
                },
            },
        },
        {
            "folder": "03-move",
            "file": "07_task_as_parent",
            "scenario": "03-move/07_task_as_parent",
            "description": "Move task under another task (task as parent)",
            "operation": "add_task",
            "params": {"name": "GM-SubtaskMoveTarget"},
            "capture_id_as": "subtask_move_target",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["subtask_move_target"],
                    "moveTo": {"position": "ending", "containerId": TASK_IDS["parent_task"]},
                },
            },
        },
        # --- GM-4: hasChildren true→false when last child removed ---
        {
            "folder": "03-move",
            "file": "08_remove_last_child",
            "scenario": "03-move/08_remove_last_child",
            "description": "Move last child to inbox so parent hasChildren becomes false",
            "operation": "add_task",
            "params": {"name": "GM-HasChildrenParent"},
            "capture_id_as": "has_children_parent",
            "followup": {
                "operation": "add_task",
                "params_fn": lambda: {
                    "name": "GM-HasChildrenChild",
                    "parent": TASK_IDS["has_children_parent"],
                },
                "capture_id_as": "has_children_child",
            },
        },
        {
            "folder": "03-move",
            "file": "09_remove_last_child_verify",
            "scenario": "03-move/09_remove_last_child_verify",
            "description": "Verify hasChildren=false after moving last child to inbox",
            "operation": "edit_task",
            "params_fn": lambda: {
                "id": TASK_IDS["has_children_child"],
                "moveTo": {"position": "ending", "containerId": None},
            },
        },
        # =================================================================
        # 04-tags/ (5 scenarios)
        # =================================================================
        {
            "folder": "04-tags",
            "file": "01_add_tags",
            "scenario": "04-tags/01_add_tags",
            "description": "Add a tag to a task",
            "operation": "add_task",
            "params": {"name": "GM-TagAddTarget"},
            "capture_id_as": "tag_add_target",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["tag_add_target"],
                    "addTagIds": [GM_TAG1_ID],
                },
            },
        },
        {
            "folder": "04-tags",
            "file": "02_remove_tags",
            "scenario": "04-tags/02_remove_tags",
            "description": "Remove a tag from a task",
            "operation": "edit_task",
            "params_fn": lambda: {
                "id": TASK_IDS["tag_add_target"],
                "removeTagIds": [GM_TAG1_ID],
            },
        },
        {
            "folder": "04-tags",
            "file": "03_replace_tags",
            "scenario": "04-tags/03_replace_tags",
            "description": "Replace tags (remove all, add one)",
            "operation": "add_task",
            "params_fn": lambda: {
                "name": "GM-TagReplaceTarget",
                "tagIds": [GM_TAG1_ID, GM_TAG2_ID],
            },
            "capture_id_as": "tag_replace_target",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["tag_replace_target"],
                    "removeTagIds": [GM_TAG1_ID, GM_TAG2_ID],
                    "addTagIds": [GM_TAG1_ID],
                },
            },
        },
        {
            "folder": "04-tags",
            "file": "04_add_duplicate",
            "scenario": "04-tags/04_add_duplicate",
            "description": "Add a tag that is already present (should be no-op for that tag)",
            "operation": "edit_task",
            "params_fn": lambda: {
                "id": TASK_IDS["tag_replace_target"],
                "addTagIds": [GM_TAG1_ID],
            },
        },
        {
            "folder": "04-tags",
            "file": "05_remove_absent",
            "scenario": "04-tags/05_remove_absent",
            "description": "Remove a tag not on task (should be no-op)",
            "operation": "edit_task",
            "params_fn": lambda: {
                "id": TASK_IDS["tag_replace_target"],
                "removeTagIds": [GM_TAG2_ID],
            },
        },
        # =================================================================
        # 05-lifecycle/ (6 scenarios)
        # =================================================================
        {
            "folder": "05-lifecycle",
            "file": "01_complete",
            "scenario": "05-lifecycle/01_complete",
            "description": "Complete a task",
            "operation": "add_task",
            "params": {"name": "GM-CompleteTarget"},
            "capture_id_as": "complete_target",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["complete_target"],
                    "lifecycle": "complete",
                },
            },
        },
        {
            "folder": "05-lifecycle",
            "file": "02_drop",
            "scenario": "05-lifecycle/02_drop",
            "description": "Drop a task",
            "operation": "add_task",
            "params": {"name": "GM-DropTarget"},
            "capture_id_as": "drop_target",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["drop_target"],
                    "lifecycle": "drop",
                },
            },
        },
        {
            "folder": "05-lifecycle",
            "file": "03_defer_blocked",
            "scenario": "05-lifecycle/03_defer_blocked",
            "description": "Set future defer date (task becomes Blocked)",
            "operation": "add_task",
            "params": {"name": "GM-DeferTarget"},
            "capture_id_as": "defer_target",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["defer_target"],
                    "deferDate": "2027-06-01T09:00:00.000Z",
                },
            },
        },
        {
            "folder": "05-lifecycle",
            "file": "04_clear_defer",
            "scenario": "05-lifecycle/04_clear_defer",
            "description": "Clear defer date (task becomes Available)",
            "operation": "edit_task",
            "params_fn": lambda: {
                "id": TASK_IDS["defer_target"],
                "deferDate": None,
            },
        },
        # --- GM-3: Cross-state lifecycle transitions ---
        {
            "folder": "05-lifecycle",
            "file": "05_complete_dropped",
            "scenario": "05-lifecycle/05_complete_dropped",
            "description": "Complete a task that was already dropped",
            "operation": "edit_task",
            # drop_target was dropped in 05-lifecycle/02_drop
            "params_fn": lambda: {
                "id": TASK_IDS["drop_target"],
                "lifecycle": "complete",
            },
        },
        {
            "folder": "05-lifecycle",
            "file": "06_drop_completed",
            "scenario": "05-lifecycle/06_drop_completed",
            "description": "Drop a task that was already completed",
            "operation": "edit_task",
            # complete_target was completed in 05-lifecycle/01_complete
            "params_fn": lambda: {
                "id": TASK_IDS["complete_target"],
                "lifecycle": "drop",
            },
        },
        # =================================================================
        # 06-combined/ (5 scenarios)
        # =================================================================
        {
            "folder": "06-combined",
            "file": "01_fields_and_move",
            "scenario": "06-combined/01_fields_and_move",
            "description": "Edit fields and move task in a single call",
            "operation": "add_task",
            "params": {"name": "GM-CombinedMoveTarget"},
            "capture_id_as": "combined_move_target",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["combined_move_target"],
                    "name": "GM-CombinedMoveTarget-Edited",
                    "flagged": True,
                    "moveTo": {"position": "ending", "containerId": GM_PROJECT_ID},
                },
            },
        },
        {
            "folder": "06-combined",
            "file": "02_fields_and_lifecycle",
            "scenario": "06-combined/02_fields_and_lifecycle",
            "description": "Edit fields and complete task in a single call",
            "operation": "add_task",
            "params": {"name": "GM-CombinedLifecycleTarget"},
            "capture_id_as": "combined_lifecycle_target",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["combined_lifecycle_target"],
                    "note": "Final note",
                    "lifecycle": "complete",
                },
            },
        },
        {
            "folder": "06-combined",
            "file": "03_subtask_add_move",
            "scenario": "06-combined/03_subtask_add_move",
            "description": "Add subtask under a task, then move it to inbox",
            "operation": "add_task",
            "params_fn": lambda: {
                "name": "GM-SubtaskAddMoveTarget",
                "parent": TASK_IDS["parent_task"],
            },
            "capture_id_as": "subtask_add_move",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["subtask_add_move"],
                    "moveTo": {"position": "ending", "containerId": None},
                },
            },
        },
        # --- GM-1: Anchor on completed/dropped task ---
        {
            "folder": "06-combined",
            "file": "04_anchor_on_completed",
            "scenario": "06-combined/04_anchor_on_completed",
            "description": "Move task to position after a completed task (anchor on completed)",
            "operation": "add_task",
            "params_fn": lambda: {
                "name": "GM-AnchorOnCompleted",
                "parent": GM_PROJECT_ID,
            },
            "capture_id_as": "anchor_on_completed",
            "followup": {
                "operation": "edit_task",
                # complete_target was completed in 05-lifecycle/01_complete,
                # then dropped in 06_drop_completed — but it's still a valid anchor.
                "params_fn": lambda: {
                    "id": TASK_IDS["anchor_on_completed"],
                    "moveTo": {"position": "after", "anchorId": TASK_IDS["complete_target"]},
                },
            },
        },
        # --- GM-5: Combined edit + move on completed task ---
        {
            "folder": "06-combined",
            "file": "05_edit_completed_task",
            "scenario": "06-combined/05_edit_completed_task",
            "description": "Rename and move a completed task in a single call",
            "operation": "edit_task",
            # complete_target is completed (then dropped) — edit + move it
            "params_fn": lambda: {
                "id": TASK_IDS["complete_target"],
                "name": "GM-CompleteTarget-Edited",
                "moveTo": {"position": "ending", "containerId": GM_PROJECT2_ID},
            },
        },
        # =================================================================
        # 07-inheritance/ (8 scenarios: 01-04, 03 chain, 05a-c nesting, 06 move)
        # =================================================================
        {
            "folder": "07-inheritance",
            "file": "01_effective_due",
            "scenario": "07-inheritance/01_effective_due",
            "description": "Task under dated project inherits effectiveDueDate",
            "operation": "add_task",
            "params_fn": lambda: {
                "name": "GM-InheritDue",
                "parent": GM_DATED_PROJECT_ID,
            },
            "capture_id_as": "inherit_due_task",
        },
        {
            "folder": "07-inheritance",
            "file": "02_effective_flagged",
            "scenario": "07-inheritance/02_effective_flagged",
            "description": "Task under flagged project inherits effectiveFlagged=true",
            "operation": "add_task",
            "params_fn": lambda: {
                "name": "GM-InheritFlagged",
                "parent": GM_DATED_PROJECT_ID,
            },
            "capture_id_as": "inherit_flagged_task",
        },
        {
            "folder": "07-inheritance",
            "file": "03_flagged_chain",
            "scenario": "07-inheritance/03_flagged_chain",
            "description": "Subtask under flagged parent task inherits effectiveFlagged chain",
            "operation": "add_task",
            "params_fn": lambda: {
                "name": "GM-FlagChainParent",
                "parent": GM_DATED_PROJECT_ID,
            },
            "capture_id_as": "flag_chain_parent",
            "followup": {
                "operation": "add_task",
                "params_fn": lambda: {
                    "name": "GM-FlagChainChild",
                    "parent": TASK_IDS["flag_chain_parent"],
                },
                "capture_id_as": "flag_chain_child",
            },
        },
        {
            "folder": "07-inheritance",
            "file": "04_effective_defer",
            "scenario": "07-inheritance/04_effective_defer",
            "description": "Task under dated project inherits effectiveDeferDate",
            "operation": "add_task",
            "params_fn": lambda: {
                "name": "GM-InheritDefer",
                "parent": GM_DATED_PROJECT_ID,
            },
            "capture_id_as": "inherit_defer_task",
        },
        {
            "folder": "07-inheritance",
            "file": "05a_deep_nesting_l1",
            "scenario": "07-inheritance/05a_deep_nesting_l1",
            "description": "Deep nesting L1: task directly under dated project",
            "operation": "add_task",
            "params_fn": lambda: {
                "name": "GM-DeepL1",
                "parent": GM_DATED_PROJECT_ID,
            },
            "capture_id_as": "deep_l1",
        },
        {
            "folder": "07-inheritance",
            "file": "05b_deep_nesting_l2",
            "scenario": "07-inheritance/05b_deep_nesting_l2",
            "description": "Deep nesting L2: subtask under L1",
            "operation": "add_task",
            "params_fn": lambda: {
                "name": "GM-DeepL2",
                "parent": TASK_IDS["deep_l1"],
            },
            "capture_id_as": "deep_l2",
        },
        {
            "folder": "07-inheritance",
            "file": "05c_deep_nesting_l3",
            "scenario": "07-inheritance/05c_deep_nesting_l3",
            "description": "Deep nesting L3: sub-subtask under L2 (3-level inheritance)",
            "operation": "add_task",
            "params_fn": lambda: {
                "name": "GM-DeepL3",
                "parent": TASK_IDS["deep_l2"],
            },
            "capture_id_as": "deep_l3",
        },
        # --- GM-6: Effective date recalculation after move ---
        {
            "folder": "07-inheritance",
            "file": "06_effective_date_after_move",
            "scenario": "07-inheritance/06_effective_date_after_move",
            "description": "Effective dates clear after move to undated project",
            "operation": "add_task",
            "params_fn": lambda: {
                "name": "GM-DateInheritMove",
                "parent": GM_DATED_PROJECT_ID,
            },
            "capture_id_as": "date_inherit_move",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["date_inherit_move"],
                    "moveTo": {"position": "ending", "containerId": GM_PROJECT2_ID},
                },
            },
        },
        # =================================================================
        # 08-repetition/ — Read scenarios (23): each scenario creates its
        # own repeating task via add_task, then does a minimal edit (set
        # note) to trigger state capture including the repetitionRule.
        # =================================================================
        {
            "folder": "08-repetition",
            "file": "01_daily_simple",
            "scenario": "08-repetition/01_daily_simple",
            "description": "FREQ=DAILY repetition rule",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-DailySimple",
                "dueDate": "2026-12-01T10:00:00.000Z",
                "repetitionRule": {
                    "ruleString": "FREQ=DAILY",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": True,
                },
            },
            "capture_id_as": "repeat_daily_simple",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_daily_simple"],
                    "note": "FREQ=DAILY",
                },
            },
        },
        {
            "folder": "08-repetition",
            "file": "02_daily_interval",
            "scenario": "08-repetition/02_daily_interval",
            "description": "FREQ=DAILY;INTERVAL=3 repetition rule",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-DailyInterval",
                "dueDate": "2026-12-01T10:00:00.000Z",
                "repetitionRule": {
                    "ruleString": "FREQ=DAILY;INTERVAL=3",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": True,
                },
            },
            "capture_id_as": "repeat_daily_interval",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_daily_interval"],
                    "note": "FREQ=DAILY;INTERVAL=3",
                },
            },
        },
        {
            "folder": "08-repetition",
            "file": "03_weekly_bare",
            "scenario": "08-repetition/03_weekly_bare",
            "description": "FREQ=WEEKLY repetition rule (no BYDAY)",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-WeeklyBare",
                "dueDate": "2026-12-01T10:00:00.000Z",
                "repetitionRule": {
                    "ruleString": "FREQ=WEEKLY",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": True,
                },
            },
            "capture_id_as": "repeat_weekly_bare",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_weekly_bare"],
                    "note": "FREQ=WEEKLY",
                },
            },
        },
        {
            "folder": "08-repetition",
            "file": "04_weekly_days",
            "scenario": "08-repetition/04_weekly_days",
            "description": "FREQ=WEEKLY;BYDAY=MO,WE,FR repetition rule",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-WeeklyDays",
                "dueDate": "2026-12-01T10:00:00.000Z",
                "repetitionRule": {
                    "ruleString": "FREQ=WEEKLY;BYDAY=MO,WE,FR",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": True,
                },
            },
            "capture_id_as": "repeat_weekly_days",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_weekly_days"],
                    "note": "FREQ=WEEKLY;BYDAY=MO,WE,FR",
                },
            },
        },
        {
            "folder": "08-repetition",
            "file": "05_monthly_plain",
            "scenario": "08-repetition/05_monthly_plain",
            "description": "FREQ=MONTHLY repetition rule",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-MonthlyPlain",
                "dueDate": "2026-12-15T10:00:00.000Z",
                "repetitionRule": {
                    "ruleString": "FREQ=MONTHLY",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": True,
                },
            },
            "capture_id_as": "repeat_monthly_plain",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_monthly_plain"],
                    "note": "FREQ=MONTHLY",
                },
            },
        },
        {
            "folder": "08-repetition",
            "file": "06_monthly_day_of_week",
            "scenario": "08-repetition/06_monthly_day_of_week",
            "description": "FREQ=MONTHLY;BYDAY=2TU repetition rule (positional)",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-MonthlyDayOfWeek",
                "dueDate": "2026-12-09T10:00:00.000Z",  # a Tuesday
                "repetitionRule": {
                    "ruleString": "FREQ=MONTHLY;BYDAY=2TU",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": True,
                },
            },
            "capture_id_as": "repeat_monthly_day_of_week",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_monthly_day_of_week"],
                    "note": "FREQ=MONTHLY;BYDAY=2TU",
                },
            },
        },
        {
            "folder": "08-repetition",
            "file": "07_monthly_last_weekday",
            "scenario": "08-repetition/07_monthly_last_weekday",
            "description": "FREQ=MONTHLY;BYDAY=-1FR repetition rule (negative prefix)",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-MonthlyLastWeekday",
                "dueDate": "2026-12-25T10:00:00.000Z",  # last Friday of Dec 2026
                "repetitionRule": {
                    "ruleString": "FREQ=MONTHLY;BYDAY=-1FR",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": True,
                },
            },
            "capture_id_as": "repeat_monthly_last_weekday",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_monthly_last_weekday"],
                    "note": "FREQ=MONTHLY;BYDAY=-1FR",
                },
            },
        },
        {
            "folder": "08-repetition",
            "file": "08_monthly_day_in_month",
            "scenario": "08-repetition/08_monthly_day_in_month",
            "description": "FREQ=MONTHLY;BYMONTHDAY=15 repetition rule",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-MonthlyDayInMonth",
                "dueDate": "2026-12-15T10:00:00.000Z",
                "repetitionRule": {
                    "ruleString": "FREQ=MONTHLY;BYMONTHDAY=15",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": True,
                },
            },
            "capture_id_as": "repeat_monthly_day_in_month",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_monthly_day_in_month"],
                    "note": "FREQ=MONTHLY;BYMONTHDAY=15",
                },
            },
        },
        {
            "folder": "08-repetition",
            "file": "09_monthly_last_day",
            "scenario": "08-repetition/09_monthly_last_day",
            "description": "FREQ=MONTHLY;BYMONTHDAY=-1 repetition rule (last day)",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-MonthlyLastDay",
                "dueDate": "2026-12-31T10:00:00.000Z",
                "repetitionRule": {
                    "ruleString": "FREQ=MONTHLY;BYMONTHDAY=-1",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": True,
                },
            },
            "capture_id_as": "repeat_monthly_last_day",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_monthly_last_day"],
                    "note": "FREQ=MONTHLY;BYMONTHDAY=-1",
                },
            },
        },
        {
            "folder": "08-repetition",
            "file": "10_yearly",
            "scenario": "08-repetition/10_yearly",
            "description": "FREQ=YEARLY repetition rule",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-Yearly",
                "dueDate": "2026-12-01T10:00:00.000Z",
                "repetitionRule": {
                    "ruleString": "FREQ=YEARLY",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": True,
                },
            },
            "capture_id_as": "repeat_yearly",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_yearly"],
                    "note": "FREQ=YEARLY",
                },
            },
        },
        {
            "folder": "08-repetition",
            "file": "11_minutely",
            "scenario": "08-repetition/11_minutely",
            "description": "FREQ=MINUTELY;INTERVAL=30 repetition rule (sub-daily)",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-Minutely",
                "dueDate": "2026-12-01T10:00:00.000Z",
                "repetitionRule": {
                    "ruleString": "FREQ=MINUTELY;INTERVAL=30",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": True,
                },
            },
            "capture_id_as": "repeat_minutely",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_minutely"],
                    "note": "FREQ=MINUTELY;INTERVAL=30",
                },
            },
        },
        {
            "folder": "08-repetition",
            "file": "12_hourly",
            "scenario": "08-repetition/12_hourly",
            "description": "FREQ=HOURLY;INTERVAL=2 repetition rule (sub-daily)",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-Hourly",
                "dueDate": "2026-12-01T10:00:00.000Z",
                "repetitionRule": {
                    "ruleString": "FREQ=HOURLY;INTERVAL=2",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": True,
                },
            },
            "capture_id_as": "repeat_hourly",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_hourly"],
                    "note": "FREQ=HOURLY;INTERVAL=2",
                },
            },
        },
        {
            "folder": "08-repetition",
            "file": "13_with_count",
            "scenario": "08-repetition/13_with_count",
            "description": "FREQ=WEEKLY;COUNT=10 repetition rule (end by occurrences)",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-WithCount",
                "dueDate": "2026-12-01T10:00:00.000Z",
                "repetitionRule": {
                    "ruleString": "FREQ=WEEKLY;COUNT=10",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": True,
                },
            },
            "capture_id_as": "repeat_with_count",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_with_count"],
                    "note": "FREQ=WEEKLY;COUNT=10",
                },
            },
        },
        {
            "folder": "08-repetition",
            "file": "14_with_until",
            "scenario": "08-repetition/14_with_until",
            "description": "FREQ=MONTHLY;UNTIL=20261231T000000Z repetition rule (end by date)",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-WithUntil",
                "dueDate": "2026-12-01T10:00:00.000Z",
                "repetitionRule": {
                    "ruleString": "FREQ=MONTHLY;UNTIL=20261231T000000Z",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": True,
                },
            },
            "capture_id_as": "repeat_with_until",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_with_until"],
                    "note": "FREQ=MONTHLY;UNTIL=20261231T000000Z",
                },
            },
        },
        {
            "folder": "08-repetition",
            "file": "15_from_completion",
            "scenario": "08-repetition/15_from_completion",
            "description": "FromCompletion schedule type",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-FromCompletion",
                "dueDate": "2026-12-01T10:00:00.000Z",
                "repetitionRule": {
                    "ruleString": "FREQ=DAILY;INTERVAL=3",
                    "scheduleType": "FromCompletion",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": True,
                },
            },
            "capture_id_as": "repeat_from_completion",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_from_completion"],
                    "note": "FREQ=DAILY;INTERVAL=3 FromCompletion",
                },
            },
        },
        {
            "folder": "08-repetition",
            "file": "16_catchup_enabled",
            "scenario": "08-repetition/16_catchup_enabled",
            "description": "Regularly + catchUpAutomatically=true",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-CatchUpEnabled",
                "dueDate": "2026-12-01T10:00:00.000Z",
                "repetitionRule": {
                    "ruleString": "FREQ=WEEKLY",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": True,
                },
            },
            "capture_id_as": "repeat_catchup_enabled",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_catchup_enabled"],
                    "note": "FREQ=WEEKLY catchUp=true",
                },
            },
        },
        # --- Anchor date and config variations ---
        {
            "folder": "08-repetition",
            "file": "17_anchor_defer",
            "scenario": "08-repetition/17_anchor_defer",
            "description": "Repetition anchored on DeferDate",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-AnchorDefer",
                "deferDate": "2026-12-01T09:00:00.000Z",
                "dueDate": "2026-12-08T10:00:00.000Z",
                "repetitionRule": {
                    "ruleString": "FREQ=WEEKLY",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DeferDate",
                    "catchUpAutomatically": True,
                },
            },
            "capture_id_as": "repeat_anchor_defer",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_anchor_defer"],
                    "note": "FREQ=WEEKLY anchor=DeferDate",
                },
            },
        },
        {
            "folder": "08-repetition",
            "file": "18_anchor_planned",
            "scenario": "08-repetition/18_anchor_planned",
            "description": "Repetition anchored on PlannedDate",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-AnchorPlanned",
                "plannedDate": "2026-12-01T09:00:00.000Z",
                "dueDate": "2026-12-08T10:00:00.000Z",
                "repetitionRule": {
                    "ruleString": "FREQ=DAILY",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "PlannedDate",
                    "catchUpAutomatically": True,
                },
            },
            "capture_id_as": "repeat_anchor_planned",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_anchor_planned"],
                    "note": "FREQ=DAILY anchor=PlannedDate",
                },
            },
        },
        {
            "folder": "08-repetition",
            "file": "19_catchup_disabled",
            "scenario": "08-repetition/19_catchup_disabled",
            "description": "Regularly + catchUpAutomatically=false",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-CatchUpDisabled",
                "dueDate": "2026-12-01T10:00:00.000Z",
                "repetitionRule": {
                    "ruleString": "FREQ=WEEKLY",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": False,
                },
            },
            "capture_id_as": "repeat_catchup_disabled",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_catchup_disabled"],
                    "note": "FREQ=WEEKLY catchUp=false",
                },
            },
        },
        {
            "folder": "08-repetition",
            "file": "20_all_non_default",
            "scenario": "08-repetition/20_all_non_default",
            "description": "All non-default: FromCompletion + DeferDate + catchUp=false",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-AllNonDefault",
                "deferDate": "2026-12-01T09:00:00.000Z",
                "dueDate": "2026-12-08T10:00:00.000Z",
                "repetitionRule": {
                    "ruleString": "FREQ=DAILY;INTERVAL=2",
                    "scheduleType": "FromCompletion",
                    "anchorDateKey": "DeferDate",
                    "catchUpAutomatically": False,
                },
            },
            "capture_id_as": "repeat_all_non_default",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_all_non_default"],
                    "note": "FREQ=DAILY;INTERVAL=2 FromCompletion DeferDate catchUp=false",
                },
            },
        },
        # --- BYSETPOS multi-day positional (D-05 gap) ---
        {
            "folder": "08-repetition",
            "file": "21_monthly_weekend_day",
            "scenario": "08-repetition/21_monthly_weekend_day",
            "description": "FREQ=MONTHLY;BYDAY=SU,SA;BYSETPOS=1 (1st weekend day)",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-MonthlyWeekendDay",
                "dueDate": "2026-12-01T10:00:00.000Z",
                "repetitionRule": {
                    "ruleString": "FREQ=MONTHLY;BYDAY=SU,SA;BYSETPOS=1",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": True,
                },
            },
            "capture_id_as": "repeat_monthly_weekend_day",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_monthly_weekend_day"],
                    "note": "FREQ=MONTHLY;BYDAY=SU,SA;BYSETPOS=1",
                },
            },
        },
        {
            "folder": "08-repetition",
            "file": "22_monthly_weekday",
            "scenario": "08-repetition/22_monthly_weekday",
            "description": "FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=2 (2nd weekday)",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-MonthlyWeekday",
                "dueDate": "2026-12-01T10:00:00.000Z",
                "repetitionRule": {
                    "ruleString": "FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=2",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": True,
                },
            },
            "capture_id_as": "repeat_monthly_weekday",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_monthly_weekday"],
                    "note": "FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=2",
                },
            },
        },
        {
            "folder": "08-repetition",
            "file": "23_monthly_last_weekend_day",
            "scenario": "08-repetition/23_monthly_last_weekend_day",
            "description": "FREQ=MONTHLY;BYDAY=SU,SA;BYSETPOS=-1 (last weekend day)",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-MonthlyLastWeekendDay",
                "dueDate": "2026-12-01T10:00:00.000Z",
                "repetitionRule": {
                    "ruleString": "FREQ=MONTHLY;BYDAY=SU,SA;BYSETPOS=-1",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": True,
                },
            },
            "capture_id_as": "repeat_monthly_last_weekend_day",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_monthly_last_weekend_day"],
                    "note": "FREQ=MONTHLY;BYDAY=SU,SA;BYSETPOS=-1",
                },
            },
        },
        # =================================================================
        # 08-repetition/ — Edit-preservation scenarios (6): create a task
        # with a repetition rule, then edit a non-rule field. The rule
        # must survive the edit unchanged.
        # =================================================================
        {
            "folder": "08-repetition",
            "file": "24_edit_rename",
            "scenario": "08-repetition/24_edit_rename",
            "description": "Rename a repeating task (rule preserved)",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-EditRename",
                "dueDate": "2026-12-01T10:00:00.000Z",
                "repetitionRule": {
                    "ruleString": "FREQ=DAILY",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": True,
                },
            },
            "capture_id_as": "repeat_edit_rename",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_edit_rename"],
                    "name": "GM-Repeat-EditRename-Renamed",
                },
            },
        },
        {
            "folder": "08-repetition",
            "file": "25_edit_flag",
            "scenario": "08-repetition/25_edit_flag",
            "description": "Flag a repeating task (rule preserved)",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-EditFlag",
                "dueDate": "2026-12-01T10:00:00.000Z",
                "repetitionRule": {
                    "ruleString": "FREQ=DAILY;INTERVAL=3",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": True,
                },
            },
            "capture_id_as": "repeat_edit_flag",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_edit_flag"],
                    "flagged": True,
                },
            },
        },
        {
            "folder": "08-repetition",
            "file": "26_edit_note",
            "scenario": "08-repetition/26_edit_note",
            "description": "Change note on a repeating task (rule preserved)",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-EditNote",
                "dueDate": "2026-12-01T10:00:00.000Z",
                "repetitionRule": {
                    "ruleString": "FREQ=WEEKLY",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": True,
                },
            },
            "capture_id_as": "repeat_edit_note",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_edit_note"],
                    "note": "Updated note — rule should survive",
                },
            },
        },
        {
            "folder": "08-repetition",
            "file": "27_edit_due_date",
            "scenario": "08-repetition/27_edit_due_date",
            "description": "Change due date on a repeating task (rule preserved)",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-EditDueDate",
                "dueDate": "2026-12-01T10:00:00.000Z",
                "repetitionRule": {
                    "ruleString": "FREQ=WEEKLY;BYDAY=MO,WE,FR",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": True,
                },
            },
            "capture_id_as": "repeat_edit_due_date",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_edit_due_date"],
                    "dueDate": "2027-01-15T10:00:00.000Z",
                },
            },
        },
        {
            "folder": "08-repetition",
            "file": "28_edit_move",
            "scenario": "08-repetition/28_edit_move",
            "description": "Move a repeating task to a project (rule preserved)",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-EditMove",
                "dueDate": "2026-12-15T10:00:00.000Z",
                "repetitionRule": {
                    "ruleString": "FREQ=MONTHLY",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": True,
                },
            },
            "capture_id_as": "repeat_edit_move",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_edit_move"],
                    "moveTo": {"position": "ending", "containerId": GM_PROJECT_ID},
                },
            },
        },
        {
            "folder": "08-repetition",
            "file": "29_edit_add_tag",
            "scenario": "08-repetition/29_edit_add_tag",
            "description": "Add tag to a repeating task (rule preserved)",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-EditAddTag",
                "dueDate": "2026-12-09T10:00:00.000Z",
                "repetitionRule": {
                    "ruleString": "FREQ=MONTHLY;BYDAY=2TU",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": True,
                },
            },
            "capture_id_as": "repeat_edit_add_tag",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_edit_add_tag"],
                    "addTagIds": [GM_TAG1_ID],
                },
            },
        },
        # =================================================================
        # 08-repetition/ — Lifecycle scenarios
        #
        # Each creates its own repeating task, then applies the lifecycle
        # operation. Completing creates a new occurrence with ID pattern
        # {originalId}.{n} (e.g. "abc123.0", "abc123.1").
        # Scenario 33 chains on 32's task for the second completion.
        # =================================================================
        {
            "folder": "08-repetition",
            "file": "30_complete_repeating",
            "scenario": "08-repetition/30_complete_repeating",
            "description": "Complete a repeating task (new occurrence with .0 ID)",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-CompleteTarget",
                "dueDate": "2026-12-01T10:00:00.000Z",
                "repetitionRule": {
                    "ruleString": "FREQ=DAILY",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": True,
                },
            },
            "capture_id_as": "repeat_complete_target",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_complete_target"],
                    "lifecycle": "complete",
                },
            },
        },
        {
            "folder": "08-repetition",
            "file": "31_drop_repeating",
            "scenario": "08-repetition/31_drop_repeating",
            "description": "Drop a repeating task",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-DropTarget",
                "dueDate": "2026-12-01T10:00:00.000Z",
                "repetitionRule": {
                    "ruleString": "FREQ=DAILY",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": True,
                },
            },
            "capture_id_as": "repeat_drop_target",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_drop_target"],
                    "lifecycle": "drop",
                },
            },
        },
        {
            "folder": "08-repetition",
            "file": "32_complete_first",
            "scenario": "08-repetition/32_complete_first",
            "description": "Complete a repeating task — first completion (.0 ID)",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-MultiComplete",
                "dueDate": "2026-12-01T10:00:00.000Z",
                "repetitionRule": {
                    "ruleString": "FREQ=DAILY",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": True,
                },
            },
            "capture_id_as": "repeat_multi_complete",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_multi_complete"],
                    "lifecycle": "complete",
                },
            },
        },
        {
            "folder": "08-repetition",
            "file": "33_complete_second",
            "scenario": "08-repetition/33_complete_second",
            "description": "Complete same repeating task again — second completion (.1 ID)",
            "operation": "edit_task",
            "params_fn": lambda: {
                "id": TASK_IDS["repeat_multi_complete"],
                "lifecycle": "complete",
            },
        },
        # =================================================================
        # 08-repetition/ — Write scenarios: add/set/replace/clear
        #
        # Scenario 34 creates with a rule inline. Scenarios 35-37 chain
        # on the same task (SET → REPLACE → CLEAR). Scenario 38 creates
        # its own task.
        # =================================================================
        {
            "folder": "08-repetition",
            "file": "34_add_with_rule",
            "scenario": "08-repetition/34_add_with_rule",
            "description": "add_task with repetitionRule (all non-default fields)",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-AddWithRule",
                "dueDate": "2026-12-01T10:00:00.000Z",
                "deferDate": "2026-11-25T09:00:00.000Z",
                "repetitionRule": {
                    "ruleString": "FREQ=DAILY;INTERVAL=2",
                    "scheduleType": "FromCompletion",
                    "anchorDateKey": "DeferDate",
                    "catchUpAutomatically": False,
                },
            },
            "capture_id_as": "repeat_add_with_rule",
        },
        {
            "folder": "08-repetition",
            "file": "35_edit_set_rule",
            "scenario": "08-repetition/35_edit_set_rule",
            "description": "SET repetition rule where none existed",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-SetTarget",
                "dueDate": "2026-12-01T10:00:00.000Z",
            },
            "capture_id_as": "repeat_set_target",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_set_target"],
                    "repetitionRule": {
                        "ruleString": "FREQ=WEEKLY",
                        "scheduleType": "Regularly",
                        "anchorDateKey": "DueDate",
                        "catchUpAutomatically": True,
                    },
                },
            },
        },
        {
            "folder": "08-repetition",
            "file": "36_edit_replace_rule",
            "scenario": "08-repetition/36_edit_replace_rule",
            "description": "REPLACE repetition rule — all fields change",
            "operation": "edit_task",
            "params_fn": lambda: {
                "id": TASK_IDS["repeat_set_target"],
                "repetitionRule": {
                    "ruleString": "FREQ=MONTHLY;BYMONTHDAY=15",
                    "scheduleType": "FromCompletion",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": False,
                },
            },
        },
        {
            "folder": "08-repetition",
            "file": "37_edit_clear_rule",
            "scenario": "08-repetition/37_edit_clear_rule",
            "description": "CLEAR repetition rule to null",
            "operation": "edit_task",
            "params_fn": lambda: {
                "id": TASK_IDS["repeat_set_target"],
                "repetitionRule": None,
            },
        },
        {
            "folder": "08-repetition",
            "file": "38_edit_set_rule_combo",
            "scenario": "08-repetition/38_edit_set_rule_combo",
            "description": "SET repetition rule + rename + flag in same call",
            "operation": "add_task",
            "params": {
                "name": "GM-Repeat-ComboTarget",
                "dueDate": "2026-12-01T10:00:00.000Z",
            },
            "capture_id_as": "repeat_combo_target",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["repeat_combo_target"],
                    "name": "GM-Repeat-ComboTarget-Edited",
                    "flagged": True,
                    "repetitionRule": {
                        "ruleString": "FREQ=DAILY;INTERVAL=3",
                        "scheduleType": "Regularly",
                        "anchorDateKey": "DueDate",
                        "catchUpAutomatically": True,
                    },
                },
            },
        },
        # =================================================================
        # 09-task-property-surface/ (Phase 56 — 8 scenarios)
        #
        # Covers the read surface added in Phase 56: raw bridge fields
        # `completedByChildren`, `sequential`, `hasAttachments`,
        # `containsSingletonActions` (projects), and `hasChildren` across
        # the behavioral combinations that matter for the derived model-
        # layer flags (`completesWithChildren`, `type`, `isSequential`,
        # `dependsOnChildren`, `hasNote`, `hasRepetition`,
        # `hasAttachments`).
        #
        # These scenarios rely on three pre-seeded projects (parallel,
        # sequential, singleActions) and one pre-seeded task with an
        # attachment (manual drag-drop in OmniFocus — OmniJS cannot create
        # attachments). See `_phase_2_manual_setup` for the setup prompts.
        # =================================================================
        # --- 01: sequential parent task, completesWithChildren=false ---
        # Create parent (type=sequential, completesWithChildren=false),
        # then add first child. State after the FOLLOWUP captures the
        # parent with its new sequential + !completesWithChildren flags
        # plus hasChildren=true (a real child is present).
        {
            "folder": "09-task-property-surface",
            "file": "01_sequential_no_autocomplete_parent",
            "scenario": "09-task-property-surface/01_sequential_no_autocomplete_parent",
            "description": (
                "Sequential parent task with completesWithChildren=false — "
                "covers isSequential, dependsOnChildren (true via children "
                "present + no auto-complete), type=sequential, "
                "completesWithChildren=false, hasChildren=true"
            ),
            "operation": "add_task",
            "params": {
                "name": "GM-Phase56-SeqNoAutoParent",
                "type": "sequential",
                "completesWithChildren": False,
            },
            "capture_id_as": "phase56_seq_no_auto_parent",
            "followup": {
                "operation": "add_task",
                "params_fn": lambda: {
                    "name": "GM-Phase56-SeqNoAutoChild",
                    "parent": TASK_IDS["phase56_seq_no_auto_parent"],
                },
                "capture_id_as": "phase56_seq_no_auto_child",
            },
        },
        # --- 02: parallel parent task, completesWithChildren=true ---
        # Auto-complete case: parent auto-completes when the last child
        # completes, so `dependsOnChildren` (derived) resolves to false
        # even with children present.
        {
            "folder": "09-task-property-surface",
            "file": "02_parallel_autocomplete_parent",
            "scenario": "09-task-property-surface/02_parallel_autocomplete_parent",
            "description": (
                "Parallel parent task with completesWithChildren=true — "
                "covers the auto-complete case (dependsOnChildren=false "
                "despite children present), completesWithChildren=true, "
                "type=parallel, hasChildren=true"
            ),
            "operation": "add_task",
            "params": {
                "name": "GM-Phase56-ParAutoParent",
                "type": "parallel",
                "completesWithChildren": True,
            },
            "capture_id_as": "phase56_par_auto_parent",
            "followup": {
                "operation": "add_task",
                "params_fn": lambda: {
                    "name": "GM-Phase56-ParAutoChild",
                    "parent": TASK_IDS["phase56_par_auto_parent"],
                },
                "capture_id_as": "phase56_par_auto_child",
            },
        },
        # --- 03: task with a note ---
        # Note presence — adapter derives hasNote=true; raw `note` field
        # carries the string directly so the replay comparison is on the
        # raw note, not the derived flag.
        {
            "folder": "09-task-property-surface",
            "file": "03_task_with_note",
            "scenario": "09-task-property-surface/03_task_with_note",
            "description": (
                "Task with a non-empty note — covers hasNote=true "
                "(derived from non-empty note string at adapter layer)"
            ),
            "operation": "add_task",
            "params": {
                "name": "GM-Phase56-Noted",
                "note": "GM-Phase56 note body.",
            },
            "capture_id_as": "phase56_noted",
        },
        # --- 04: attachment task (pre-seeded, attachment added manually) ---
        # Attachments cannot be created via OmniJS. The human pre-seeds a
        # task named 'GM-Phase56-Attached' with a drag-dropped file; this
        # scenario touches it with a no-op-ish edit (set note) to trigger
        # a state_after capture that includes the raw hasAttachments=true
        # field. Task ID is discovered and registered in
        # `_phase_2_manual_setup` so it lands in known_task_ids.
        {
            "folder": "09-task-property-surface",
            "file": "04_task_with_attachment",
            "scenario": "09-task-property-surface/04_task_with_attachment",
            "description": (
                "Pre-seeded task with an attachment (manual setup; OmniJS "
                "cannot create attachments) — covers hasAttachments=true. "
                "Scenario touches the pre-seeded task with a note edit to "
                "trigger a state_after capture including the raw field."
            ),
            "operation": "edit_task",
            "params_fn": lambda: {
                "id": GM_PHASE56_ATTACHED_TASK_ID,
                "note": "GM-Phase56 attachment touch.",
            },
        },
        # --- 05: project-type matrix — parallel project ---
        # Pre-seeded project: 🧪 GM-Phase56-ParallelProj (type=parallel,
        # set in OmniFocus Inspector). Scenario adds a minimal task under
        # it; state_after filters to the known project + new task, so the
        # project's raw `sequential=false` / `containsSingletonActions=
        # false` are exercised.
        {
            "folder": "09-task-property-surface",
            "file": "05_project_type_parallel",
            "scenario": "09-task-property-surface/05_project_type_parallel",
            "description": (
                "Task under a parallel project — captures project raw "
                "sequential=false + containsSingletonActions=false "
                "(HIER-05: project.type derives to 'parallel')"
            ),
            "operation": "add_task",
            "params_fn": lambda: {
                "name": "GM-Phase56-ParProjChild",
                "parent": GM_PHASE56_PARALLEL_PROJECT_ID,
            },
            "capture_id_as": "phase56_par_proj_child",
        },
        # --- 06: project-type matrix — sequential project ---
        # Pre-seeded project: 🧪 GM-Phase56-SequentialProj (type=
        # sequential, containsSingletonActions=false).
        {
            "folder": "09-task-property-surface",
            "file": "06_project_type_sequential",
            "scenario": "09-task-property-surface/06_project_type_sequential",
            "description": (
                "Task under a sequential project — captures project raw "
                "sequential=true + containsSingletonActions=false "
                "(HIER-05: project.type derives to 'sequential'; also "
                "flips project.isSequential via the 56-08 hoist)"
            ),
            "operation": "add_task",
            "params_fn": lambda: {
                "name": "GM-Phase56-SeqProjChild",
                "parent": GM_PHASE56_SEQUENTIAL_PROJECT_ID,
            },
            "capture_id_as": "phase56_seq_proj_child",
        },
        # --- 07: project-type matrix — single-actions project ---
        # Pre-seeded project: 🧪 GM-Phase56-SingleActionsProj
        # (containsSingletonActions=true; sequential raw bit may be
        # either value — HIER-05 says singleActions wins regardless).
        {
            "folder": "09-task-property-surface",
            "file": "07_project_type_single_actions",
            "scenario": "09-task-property-surface/07_project_type_single_actions",
            "description": (
                "Task under a single-actions project — captures project "
                "raw containsSingletonActions=true (HIER-05: derives to "
                "project.type='singleActions' regardless of the raw "
                "sequential bit; project.isSequential resolves to false)"
            ),
            "operation": "add_task",
            "params_fn": lambda: {
                "name": "GM-Phase56-SAProjChild",
                "parent": GM_PHASE56_SINGLE_ACTIONS_PROJECT_ID,
            },
            "capture_id_as": "phase56_sa_proj_child",
        },
        # --- 08: sequential parent flipped to parallel via edit ---
        # Exercises the patch path for `type` on edit_task: create a
        # sequential parent, then edit it to parallel. State after the
        # followup captures sequential=false, locking the edit-side
        # contract for PROP-06 against the real Bridge.
        {
            "folder": "09-task-property-surface",
            "file": "08_edit_type_and_completes_flip",
            "scenario": "09-task-property-surface/08_edit_type_and_completes_flip",
            "description": (
                "Edit a task's type + completesWithChildren fields — "
                "covers the patch-semantics edit path for PROP-05 / "
                "PROP-06 (sequential → parallel, "
                "completesWithChildren false → true)"
            ),
            "operation": "add_task",
            "params": {
                "name": "GM-Phase56-EditTarget",
                "type": "sequential",
                "completesWithChildren": False,
            },
            "capture_id_as": "phase56_edit_target",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["phase56_edit_target"],
                    "type": "parallel",
                    "completesWithChildren": True,
                },
            },
        },
    ]


# ---------------------------------------------------------------------------
# Capture helpers
# ---------------------------------------------------------------------------


async def _get_all_raw(bridge: RealBridge) -> dict[str, Any]:
    """Get full snapshot from bridge in raw bridge format."""
    return await bridge.send_command("get_all")


def _find_by_name(entities: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    """Find an entity by name in a list of dicts."""
    return next((e for e in entities if e.get("name") == name), None)


def _validate_dated_project(project: dict[str, Any]) -> list[str]:
    """Check that GM-TestProject-Dated has the required properties for inheritance scenarios.

    Returns a list of problems (empty = all good).
    """
    problems: list[str] = []
    if not project.get("dueDate"):
        problems.append("dueDate is not set (needed for effectiveDueDate inheritance)")
    if not project.get("deferDate"):
        problems.append("deferDate is not set (needed for effectiveDeferDate inheritance)")
    if not project.get("flagged"):
        problems.append("flagged is not true (needed for effectiveFlagged inheritance)")
    return problems


# ---------------------------------------------------------------------------
# Symbolic ID helpers — stable IDs for diff-friendly snapshots
# ---------------------------------------------------------------------------

# Fields to strip from initial_state entities (volatile timestamps + uncomputed).
# We keep "id" (needed to seed InMemoryBridge) but strip everything else that
# causes diff noise on re-capture.
_INITIAL_STATE_STRIP_TASK = (VOLATILE_TASK_FIELDS - {"id"}) | UNCOMPUTED_TASK_FIELDS
_INITIAL_STATE_STRIP_PROJECT = (VOLATILE_PROJECT_FIELDS - {"id"}) | UNCOMPUTED_PROJECT_FIELDS
_INITIAL_STATE_STRIP_TAG = VOLATILE_TAG_FIELDS - {"id"}


def _symbolize_ids(data: Any) -> Any:
    """Recursively replace real OmniFocus IDs with stable symbolic refs.

    Exact string match only — safe because OmniFocus IDs are random
    alphanumeric strings that won't collide with task names or other values.
    """
    if isinstance(data, str):
        return _id_map.get(data, data)
    if isinstance(data, list):
        return [_symbolize_ids(item) for item in data]
    if isinstance(data, dict):
        return {k: _symbolize_ids(v) for k, v in data.items()}
    return data


def _normalize_initial_state(state: dict[str, Any]) -> dict[str, Any]:
    """Strip volatile/uncomputed fields from initial_state, keeping id.

    initial_state.json needs ``id`` for seeding InMemoryBridge, but fields
    like url, added, modified, taskStatus, nextTask are noise that changes
    on every capture.
    """
    result: dict[str, Any] = {}
    # Tasks may be present in initial state if any are created during setup
    result["tasks"] = [
        {k: v for k, v in t.items() if k not in _INITIAL_STATE_STRIP_TASK}
        for t in state.get("tasks", [])
    ]

    result["projects"] = [
        {k: v for k, v in p.items() if k not in _INITIAL_STATE_STRIP_PROJECT}
        for p in state.get("projects", [])
    ]
    result["tags"] = [
        {k: v for k, v in t.items() if k not in _INITIAL_STATE_STRIP_TAG}
        for t in state.get("tags", [])
    ]
    return result


def _populate_id_map_from_setup(state: dict[str, Any]) -> None:
    """Build the symbolic ID map for projects, tags, and external refs.

    Called after Phase 2 discovers test entities.  Uses the full get_all
    state to look up folder and parent-tag names for readable symbolic refs.
    """
    # Projects
    _id_map[GM_PROJECT_ID] = "$project:test_project"
    _id_map[GM_PROJECT2_ID] = "$project:test_project2"
    _id_map[GM_DATED_PROJECT_ID] = "$project:dated_project"

    # Tags
    _id_map[GM_TAG1_ID] = "$tag:tag1"
    _id_map[GM_TAG2_ID] = "$tag:tag2"

    # External: folders referenced by test projects
    folders_by_id = {f["id"]: f for f in state.get("folders", [])}
    for p in state.get("projects", []):
        folder_id = p.get("folder")
        if folder_id and folder_id not in _id_map:
            folder = folders_by_id.get(folder_id)
            slug = _slugify(folder["name"]) if folder else "unknown"
            _id_map[folder_id] = f"$folder:{slug}"

    # External: parent tags of test tags
    tags_by_id = {t["id"]: t for t in state.get("tags", [])}
    for t in state.get("tags", []):
        parent_id = t.get("parent")
        if parent_id and parent_id not in _id_map:
            parent = tags_by_id.get(parent_id)
            slug = _slugify(parent["name"]) if parent else "unknown"
            _id_map[parent_id] = f"$tag_group:{slug}"


def _slugify(name: str) -> str:
    """Convert an entity name to a stable slug for symbolic IDs."""
    # Strip emoji prefix (🧪 etc.) and leading/trailing whitespace
    name = re.sub(r"^[\U0001f000-\U0001ffff\s]+", "", name).strip()
    # Lowercase, replace non-alphanumeric with underscores, collapse
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug or "unknown"


async def _capture_scenario(
    bridge: RealBridge,
    scenario: dict[str, Any],
    scenario_num: int,
    total: int,
) -> dict[str, Any]:
    """Execute one scenario: send command, capture state, normalize, return fixture."""
    operation = scenario["operation"]
    params = scenario.get("params") or scenario["params_fn"]()

    # Track IDs created during this scenario (for contract test ID mapping)
    created_ids: list[str] = []

    # Execute the write operation
    response = await bridge.send_command(operation, params)

    # If this is an add_task, track the new ID
    if operation == "add_task":
        created_ids.append(response["id"])
        capture_key = scenario.get("capture_id_as")
        if capture_key:
            TASK_IDS[capture_key] = response["id"]
            _id_map[response["id"]] = f"$task:{capture_key}"
            known_task_ids.add(response["id"])

    # If there's a followup (e.g., add_task then edit_task), run it
    followup = scenario.get("followup")
    if followup:
        followup_params = followup["params_fn"]()
        response = await bridge.send_command(followup["operation"], followup_params)

        # If followup is also an add_task (e.g., inheritance chain scenarios),
        # track the ID from the followup response
        if followup["operation"] == "add_task":
            created_ids.append(response["id"])
            followup_capture_key = followup.get("capture_id_as")
            if followup_capture_key:
                TASK_IDS[followup_capture_key] = response["id"]
                _id_map[response["id"]] = f"$task:{followup_capture_key}"
                known_task_ids.add(response["id"])

    # Capture state after all operations for this scenario
    state = await _get_all_raw(bridge)

    # Discover derived occurrence IDs (e.g. "abc123.0", "abc123.1") created
    # when repeating tasks are completed. Add them to known_task_ids so they
    # appear in state_after and are cleaned up in Phase 5.
    for task in state.get("tasks", []):
        tid = task["id"]
        dot_pos = tid.rfind(".")
        if dot_pos > 0 and tid[:dot_pos] in known_task_ids and tid not in known_task_ids:
            known_task_ids.add(tid)
            created_ids.append(tid)
            parent_symbolic = _id_map.get(tid[:dot_pos], tid[:dot_pos])
            _id_map[tid] = f"{parent_symbolic}.{tid[dot_pos + 1 :]}"

    filtered = filter_to_known_ids(state, known_task_ids, known_project_ids, known_tag_ids)

    # Build fixture (params may need resolving for serialization)
    resolved_params = params if isinstance(params, dict) else scenario["params_fn"]()
    if followup:
        followup_params_resolved = followup["params_fn"]()
        resolved_params = followup_params_resolved

    fixture: dict[str, Any] = {
        "scenario": scenario["scenario"],
        "description": scenario["description"],
        "operation": followup["operation"] if followup else operation,
        "params": resolved_params,
        "response": normalize_response(response),
        "state_after": normalize_state(filtered),
        "created_ids": created_ids,
    }

    # For followup scenarios, store the primary operation so the contract
    # test can replay it (e.g., create the task before editing it).
    if followup:
        fixture["setup_operation"] = operation
        fixture["setup_params"] = params if isinstance(params, dict) else scenario["params_fn"]()

    desc = scenario["description"]
    print(f"  Scenario {scenario_num:02d}/{total}: {desc}... OK")
    return fixture


def _write_fixture(fixture: dict[str, Any]) -> None:
    """Write a scenario fixture to a JSON file in the appropriate subfolder."""
    folder = fixture.pop("folder", None)
    filename = fixture.pop("file", None)

    if folder and filename:
        subfolder = SNAPSHOTS_DIR / folder
        subfolder.mkdir(parents=True, exist_ok=True)
        path = subfolder / f"{filename}.json"
    else:
        # Fallback for fixtures without folder/file (shouldn't happen)
        path = SNAPSHOTS_DIR / f"scenario_{fixture['scenario']}.json"

    # Strip folder/file keys from fixture data before writing
    data = {k: v for k, v in fixture.items() if k not in ("folder", "file")}
    path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Phases
# ---------------------------------------------------------------------------


def _phase_1_introduction() -> None:
    """Print banner and explain what will happen."""
    print()
    print("=" * 60)
    print("  OmniFocus Operator -- Golden Master Capture")
    print("=" * 60)
    print()
    print("This script captures bridge behavior from real OmniFocus to")
    print("create golden master fixtures for contract tests.")
    print()
    print("What will happen:")
    print("  1. You verify 6 projects, 2 tags, and 1 attached task exist in OmniFocus")
    print("  2. The script verifies each entity exists")
    print("  3. Scenarios run automatically across 9 categories")
    print("  4. Fixture JSON files are written to tests/golden_master/snapshots/")
    print("     organized in numbered subfolders (01-add/ through 09-task-property-surface/)")
    print("  5. Test tasks are consolidated for easy cleanup")
    print()
    print("Prerequisites:")
    print("  - OmniFocus must be running")
    print("  - Bridge script must be installed in OmniFocus")
    print()


async def _phase_2_manual_setup(bridge: RealBridge) -> None:
    """Guide user through creating test entities and verify each one."""
    global GM_PROJECT_ID, GM_PROJECT2_ID, GM_DATED_PROJECT_ID, GM_TAG1_ID, GM_TAG2_ID

    print("-" * 60)
    print("  Phase 2: Manual Setup")
    print("-" * 60)
    print()

    # One upfront query to check what already exists
    state = await _get_all_raw(bridge)

    project = _find_by_name(state.get("projects", []), "🧪 GM-TestProject")
    project2 = _find_by_name(state.get("projects", []), "🧪 GM-TestProject2")
    dated_project = _find_by_name(state.get("projects", []), "🧪 GM-TestProject-Dated")
    tag1 = _find_by_name(state.get("tags", []), "🧪 GM-Tag1")
    tag2 = _find_by_name(state.get("tags", []), "🧪 GM-Tag2")

    all_found = all([project, project2, dated_project, tag1, tag2])

    if all_found:
        GM_PROJECT_ID = project["id"]  # type: ignore[index]
        GM_PROJECT2_ID = project2["id"]  # type: ignore[index]
        GM_DATED_PROJECT_ID = dated_project["id"]  # type: ignore[index]
        GM_TAG1_ID = tag1["id"]  # type: ignore[index]
        GM_TAG2_ID = tag2["id"]  # type: ignore[index]
        known_project_ids.update({GM_PROJECT_ID, GM_PROJECT2_ID, GM_DATED_PROJECT_ID})
        known_tag_ids.update({GM_TAG1_ID, GM_TAG2_ID})
        print(f"  Found: 🧪 GM-TestProject (ID: {GM_PROJECT_ID})")
        print(f"  Found: 🧪 GM-TestProject2 (ID: {GM_PROJECT2_ID})")
        print(f"  Found: 🧪 GM-TestProject-Dated (ID: {GM_DATED_PROJECT_ID})")
        print(f"  Found: 🧪 GM-Tag1 (ID: {GM_TAG1_ID})")
        print(f"  Found: 🧪 GM-Tag2 (ID: {GM_TAG2_ID})")
        print("  All entities found -- skipping manual setup.")
        print()

        # Verify GM-TestProject-Dated has required properties
        problems = _validate_dated_project(dated_project)  # type: ignore[arg-type]
        if problems:
            print("  ⚠ 🧪 GM-TestProject-Dated is missing required properties:")
            for p in problems:
                print(f"    - {p}")
            print()
            print("  Please fix in OmniFocus Inspector, then press Enter to re-check.")
            while problems:
                input("  Press Enter when fixed... ")
                state = await _get_all_raw(bridge)
                dated_project = _find_by_name(state.get("projects", []), "🧪 GM-TestProject-Dated")
                if dated_project is None:
                    print("  ERROR: Project not found. Please re-create it.")
                    continue
                problems = _validate_dated_project(dated_project)
                if problems:
                    print("  Still missing:")
                    for p in problems:
                        print(f"    - {p}")
                else:
                    GM_DATED_PROJECT_ID = dated_project["id"]
                    print(
                        "  ✓ 🧪 GM-TestProject-Dated verified: dueDate, deferDate, flagged all set."
                    )
            print()
        else:
            print("  ✓ GM-TestProject-Dated verified: dueDate, deferDate, flagged set.")
            print()

        print("  NOTE: Also ensure 'Complete with last action' is OFF for this project")
        print("  (not exposed via bridge -- cannot verify automatically).")
        print()
    else:
        # Guide through each missing entity
        entities = [
            ("🧪 GM-TestProject", "projects", "project"),
            ("🧪 GM-TestProject2", "projects", "project"),
            ("🧪 GM-TestProject-Dated", "projects", "project"),
            ("🧪 GM-Tag1", "tags", "tag"),
            ("🧪 GM-Tag2", "tags", "tag"),
        ]
        found_entities: dict[str, dict[str, Any]] = {}
        # Map any already-found entities
        if project:
            found_entities["🧪 GM-TestProject"] = project
        if project2:
            found_entities["🧪 GM-TestProject2"] = project2
        if dated_project:
            found_entities["🧪 GM-TestProject-Dated"] = dated_project
        if tag1:
            found_entities["🧪 GM-Tag1"] = tag1
        if tag2:
            found_entities["🧪 GM-Tag2"] = tag2

        for name, list_key, entity_type in entities:
            if name in found_entities:
                entity = found_entities[name]
                print(f"  Found: {name} (ID: {entity['id']})")
            else:
                while True:
                    print(f"Please create a {entity_type} named '{name}' in OmniFocus.")
                    if name == "🧪 GM-TestProject-Dated":
                        print("  This project must have: dueDate set, deferDate set, flagged=true")
                        print("  Also disable 'Complete with last action' in Inspector")
                    input("Press Enter when done... ")
                    state = await _get_all_raw(bridge)
                    entity = _find_by_name(state.get(list_key, []), name)
                    if entity:
                        found_entities[name] = entity
                        print(f"  Found: {name} (ID: {entity['id']})")
                        break
                    print("  ERROR: Not found. Please try again.")
                print()

        # Validate GM-TestProject-Dated properties
        dated = found_entities["🧪 GM-TestProject-Dated"]
        problems = _validate_dated_project(dated)
        if problems:
            print("  ⚠ 🧪 GM-TestProject-Dated is missing required properties:")
            for p in problems:
                print(f"    - {p}")
            print()
            print("  Please fix in OmniFocus Inspector, then press Enter to re-check.")
            while problems:
                input("  Press Enter when fixed... ")
                state = await _get_all_raw(bridge)
                dated = _find_by_name(state.get("projects", []), "🧪 GM-TestProject-Dated")
                if dated is None:
                    print("  ERROR: Project not found. Please re-create it.")
                    continue
                problems = _validate_dated_project(dated)
                if problems:
                    print("  Still missing:")
                    for p in problems:
                        print(f"    - {p}")
                else:
                    found_entities["🧪 GM-TestProject-Dated"] = dated
                    print(
                        "  ✓ 🧪 GM-TestProject-Dated verified: dueDate, deferDate, flagged all set."
                    )
            print()
        else:
            print("  ✓ GM-TestProject-Dated verified: dueDate, deferDate, flagged set.")
            print()

        print("  NOTE: Also ensure 'Complete with last action' is OFF for this project")
        print("  (not exposed via bridge -- cannot verify automatically).")
        print()

        GM_PROJECT_ID = found_entities["🧪 GM-TestProject"]["id"]
        GM_PROJECT2_ID = found_entities["🧪 GM-TestProject2"]["id"]
        GM_DATED_PROJECT_ID = found_entities["🧪 GM-TestProject-Dated"]["id"]
        GM_TAG1_ID = found_entities["🧪 GM-Tag1"]["id"]
        GM_TAG2_ID = found_entities["🧪 GM-Tag2"]["id"]
        known_project_ids.update({GM_PROJECT_ID, GM_PROJECT2_ID, GM_DATED_PROJECT_ID})
        known_tag_ids.update({GM_TAG1_ID, GM_TAG2_ID})

    # Build symbolic ID map from discovered entities.
    # Re-query to ensure we have the full state (including folders for slug lookup).
    full_state = await _get_all_raw(bridge)
    _populate_id_map_from_setup(full_state)


async def _phase_2b_phase56_setup(bridge: RealBridge) -> None:
    """Discover Phase 56 pre-seeded entities (project-type matrix + attached task).

    The 09-task-property-surface scenarios exercise the raw bridge
    `sequential` / `containsSingletonActions` / `hasAttachments` fields
    that cannot be created via OmniJS (project type flags live in the
    Inspector; attachments are drag-dropped only). The human pre-seeds
    four entities once — this helper discovers them, registers their
    IDs, and populates symbolic refs for stable fixture output.

    Required pre-seeded entities (🧪 prefix + Phase56 tag for easy
    filtering in the human's Inbox view):
      - 🧪 GM-Phase56-ParallelProj        (project, type=parallel)
      - 🧪 GM-Phase56-SequentialProj      (project, type=sequential)
      - 🧪 GM-Phase56-SingleActionsProj   (project, containsSingletonActions=true)
      - 🧪 GM-Phase56-Attached            (task, drag-dropped attachment)

    The attached task MUST live somewhere stable (e.g. under
    🧪 GM-TestProject or the inbox); its ID is registered in
    `known_task_ids` AND `_preserved_task_ids` so it's included in
    state_after for scenario 04 but NOT moved into the cleanup
    container in Phase 5.
    """
    global GM_PHASE56_PARALLEL_PROJECT_ID, GM_PHASE56_SEQUENTIAL_PROJECT_ID
    global GM_PHASE56_SINGLE_ACTIONS_PROJECT_ID, GM_PHASE56_ATTACHED_TASK_ID

    print("-" * 60)
    print("  Phase 2b: Manual Setup (Phase 56 extensions)")
    print("-" * 60)
    print()

    required_projects: list[tuple[str, str]] = [
        (
            "🧪 GM-Phase56-ParallelProj",
            "parallel project — Inspector: type=parallel, containsSingletonActions=false",
        ),
        (
            "🧪 GM-Phase56-SequentialProj",
            "sequential project — Inspector: type=sequential, containsSingletonActions=false",
        ),
        (
            "🧪 GM-Phase56-SingleActionsProj",
            "single-actions project — Inspector: containsSingletonActions=true",
        ),
    ]
    attached_task_name = "🧪 GM-Phase56-Attached"

    while True:
        state = await _get_all_raw(bridge)
        found_projects: dict[str, dict[str, Any]] = {}
        missing: list[str] = []
        for name, _ in required_projects:
            project = _find_by_name(state.get("projects", []), name)
            if project:
                found_projects[name] = project
            else:
                missing.append(name)

        attached_task = _find_by_name(state.get("tasks", []), attached_task_name)
        if not attached_task:
            missing.append(attached_task_name)

        if not missing:
            break

        print("  Please create the following in OmniFocus:")
        for name, instructions in required_projects:
            if name in missing:
                print(f"    - {name} ({instructions})")
        if attached_task_name in missing:
            print(
                f"    - {attached_task_name} — task anywhere "
                "(inbox or a sandbox project); drag-drop any small file "
                "onto it as an attachment"
            )
        print()
        input("  Press Enter when all entities exist... ")
        print()

    # Validate project type flags
    problems: list[str] = []
    parallel = found_projects["🧪 GM-Phase56-ParallelProj"]
    sequential = found_projects["🧪 GM-Phase56-SequentialProj"]
    single_actions = found_projects["🧪 GM-Phase56-SingleActionsProj"]
    if parallel.get("sequential") is not False:
        problems.append("🧪 GM-Phase56-ParallelProj: sequential should be false")
    if parallel.get("containsSingletonActions") is not False:
        problems.append("🧪 GM-Phase56-ParallelProj: containsSingletonActions should be false")
    if sequential.get("sequential") is not True:
        problems.append("🧪 GM-Phase56-SequentialProj: sequential should be true")
    if sequential.get("containsSingletonActions") is not False:
        problems.append("🧪 GM-Phase56-SequentialProj: containsSingletonActions should be false")
    if single_actions.get("containsSingletonActions") is not True:
        problems.append("🧪 GM-Phase56-SingleActionsProj: containsSingletonActions should be true")
    if not attached_task.get("hasAttachments"):
        problems.append(
            f"{attached_task_name}: hasAttachments is not true "
            "(drag-drop a file onto this task in OmniFocus)"
        )

    while problems:
        print("  ⚠ Phase 56 entities have inspector-property problems:")
        for p in problems:
            print(f"    - {p}")
        print()
        print("  Fix in OmniFocus Inspector (type, containsSingletonActions)")
        print("  or drag-drop an attachment, then press Enter to re-check.")
        input("  Press Enter when fixed... ")

        state = await _get_all_raw(bridge)
        parallel = _find_by_name(state.get("projects", []), "🧪 GM-Phase56-ParallelProj") or {}
        sequential = _find_by_name(state.get("projects", []), "🧪 GM-Phase56-SequentialProj") or {}
        single_actions = (
            _find_by_name(state.get("projects", []), "🧪 GM-Phase56-SingleActionsProj") or {}
        )
        attached_task = _find_by_name(state.get("tasks", []), attached_task_name) or {}
        problems = []
        if parallel.get("sequential") is not False:
            problems.append("🧪 GM-Phase56-ParallelProj: sequential should be false")
        if parallel.get("containsSingletonActions") is not False:
            problems.append("🧪 GM-Phase56-ParallelProj: containsSingletonActions should be false")
        if sequential.get("sequential") is not True:
            problems.append("🧪 GM-Phase56-SequentialProj: sequential should be true")
        if sequential.get("containsSingletonActions") is not False:
            problems.append(
                "🧪 GM-Phase56-SequentialProj: containsSingletonActions should be false"
            )
        if single_actions.get("containsSingletonActions") is not True:
            problems.append(
                "🧪 GM-Phase56-SingleActionsProj: containsSingletonActions should be true"
            )
        if not attached_task.get("hasAttachments"):
            problems.append(
                f"{attached_task_name}: hasAttachments is not true "
                "(drag-drop a file onto this task in OmniFocus)"
            )

    # Register IDs and symbolic refs
    GM_PHASE56_PARALLEL_PROJECT_ID = parallel["id"]
    GM_PHASE56_SEQUENTIAL_PROJECT_ID = sequential["id"]
    GM_PHASE56_SINGLE_ACTIONS_PROJECT_ID = single_actions["id"]
    GM_PHASE56_ATTACHED_TASK_ID = attached_task["id"]
    known_project_ids.update(
        {
            GM_PHASE56_PARALLEL_PROJECT_ID,
            GM_PHASE56_SEQUENTIAL_PROJECT_ID,
            GM_PHASE56_SINGLE_ACTIONS_PROJECT_ID,
        }
    )
    known_task_ids.add(GM_PHASE56_ATTACHED_TASK_ID)
    # Pre-seeded attached task stays in place across captures
    _preserved_task_ids.add(GM_PHASE56_ATTACHED_TASK_ID)

    _id_map[GM_PHASE56_PARALLEL_PROJECT_ID] = "$project:phase56_parallel"
    _id_map[GM_PHASE56_SEQUENTIAL_PROJECT_ID] = "$project:phase56_sequential"
    _id_map[GM_PHASE56_SINGLE_ACTIONS_PROJECT_ID] = "$project:phase56_single_actions"
    _id_map[GM_PHASE56_ATTACHED_TASK_ID] = "$task:phase56_attached"

    print(f"  Found: 🧪 GM-Phase56-ParallelProj (ID: {GM_PHASE56_PARALLEL_PROJECT_ID})")
    print(f"  Found: 🧪 GM-Phase56-SequentialProj (ID: {GM_PHASE56_SEQUENTIAL_PROJECT_ID})")
    print(f"  Found: 🧪 GM-Phase56-SingleActionsProj (ID: {GM_PHASE56_SINGLE_ACTIONS_PROJECT_ID})")
    print(f"  Found: {attached_task_name} (ID: {GM_PHASE56_ATTACHED_TASK_ID})")
    print("  ✓ All Phase 56 entities verified.")
    print()


async def _check_leftover_tasks(bridge: RealBridge) -> None:
    """Ensure no GM- tasks remain from a previous run."""
    state = await _get_all_raw(bridge)
    leftover = [
        t
        for t in state.get("tasks", [])
        if t.get("name", "").startswith(("GM-", "🧪 GM-"))
        and t["id"] not in known_project_ids
        and t["id"] not in known_task_ids
    ]
    if not leftover:
        return

    print("  WARNING: Found leftover tasks from a previous run:")
    for t in leftover:
        print(f"    - {t['name']} (ID: {t['id']})")
    print()
    print("  These will pollute the golden master state snapshots.")
    print("  Please delete them in OmniFocus before continuing.")
    print()

    while True:
        input("  Press Enter when cleaned up (or Ctrl+C to abort)... ")
        state = await _get_all_raw(bridge)
        remaining = [
            t
            for t in state.get("tasks", [])
            if t.get("name", "").startswith(("GM-", "🧪 GM-"))
            and t["id"] not in known_project_ids
            and t["id"] not in known_task_ids
        ]
        if not remaining:
            print("  All clear -- no leftover tasks found.")
            print()
            return
        print(f"  Still found {len(remaining)} GM- task(s). Please delete them all.")
        print()


def _phase_3_confirmation() -> bool:
    """Show scenario list and ask user to confirm."""
    print("-" * 60)
    print("  Phase 3: Scenario Preview")
    print("-" * 60)
    print()
    print("The following ~92 scenarios will be executed across 9 categories:")
    print()
    print("  01-add/ (6 scenarios):")
    print("    01. Inbox task (minimal)")
    print("    02. With parent project")
    print("    03. All fields (flagged, dates, note, estimate)")
    print("    04. With tags")
    print("    05. Parent + tags")
    print("    06. Max payload (all fields + parent + tags)")
    print()
    print("  02-edit/ (10 scenarios):")
    print("    01. Rename")
    print("    02. Set note")
    print("    03. Clear note (empty string)")
    print("    04. Flag")
    print("    05. Unflag")
    print("    06. Set dates (due + defer)")
    print("    07. Clear dates (null)")
    print("    08. Set estimated minutes")
    print("    09. Clear estimated minutes (null)")
    print("    10. Set planned date")
    print()
    print("  03-move/ (9 scenarios):")
    print("    01. To project (ending)")
    print("    02. To inbox")
    print("    03. To beginning")
    print("    04. After anchor task")
    print("    05. Before anchor task")
    print("    06. Between projects")
    print("    07. Task as parent")
    print("    08-09. Remove last child (hasChildren false)")
    print()
    print("  04-tags/ (5 scenarios):")
    print("    01. Add tags")
    print("    02. Remove tags")
    print("    03. Replace tags")
    print("    04. Add duplicate tag (no-op)")
    print("    05. Remove absent tag (no-op)")
    print()
    print("  05-lifecycle/ (6 scenarios):")
    print("    01. Complete")
    print("    02. Drop")
    print("    03. Defer (blocked)")
    print("    04. Clear defer (available)")
    print("    05. Complete a dropped task")
    print("    06. Drop a completed task")
    print()
    print("  06-combined/ (5 scenarios):")
    print("    01. Fields + move")
    print("    02. Fields + lifecycle")
    print("    03. Subtask add + move out")
    print("    04. Anchor on completed/dropped task")
    print("    05. Edit + move completed task")
    print()
    print("  07-inheritance/ (8 scenarios):")
    print("    01. Effective due date from project")
    print("    02. Effective flagged from project")
    print("    03. Flagged chain (parent task -> child)")
    print("    04. Effective defer date from project")
    print("    05a-c. Deep nesting (3 levels)")
    print("    06. Effective dates clear after move to undated project")
    print()
    print("  08-repetition/ (38 scenarios):")
    print("    01-23. RRULE variations (daily, weekly, monthly, yearly, sub-daily,")
    print("           COUNT, UNTIL, fromCompletion, catchUp, anchor, BYSETPOS)")
    print("    24-29. Edit-preservation (rename, flag, note, due date, move, add tag)")
    print("    30-33. Lifecycle (complete, drop, complete twice)")
    print("    34.    add_task with repetitionRule")
    print("    35-37. SET → REPLACE → CLEAR lifecycle")
    print("    38.    SET rule + rename + flag combo")
    print()
    print("  09-task-property-surface/ (8 scenarios):")
    print("    01. Sequential parent, completesWithChildren=false (+ child)")
    print("    02. Parallel parent, completesWithChildren=true (+ child)")
    print("    03. Task with a note (hasNote)")
    print("    04. Task with an attachment (pre-seeded, hasAttachments)")
    print("    05-07. Project-type matrix (parallel / sequential / singleActions)")
    print("    08. Edit flip: type + completesWithChildren via edit_task")
    print()

    scenarios = _build_scenarios()
    answer = input(f"Ready to run {len(scenarios)} scenarios? [y/N] ").strip().lower()
    return answer == "y"


async def _phase_4_capture(bridge: RealBridge) -> None:
    """Execute all scenarios and write fixture files."""
    print()
    print("-" * 60)
    print("  Phase 4: Capture")
    print("-" * 60)
    print()

    scenarios = _build_scenarios()
    total = len(scenarios)

    for i, scenario in enumerate(scenarios, 1):
        fixture = await _capture_scenario(bridge, scenario, i, total)
        # Replace real OmniFocus IDs with stable symbolic refs before writing
        fixture = _symbolize_ids(fixture)
        # Attach folder/file for _write_fixture routing (after symbolize —
        # these are path components, not data)
        fixture["folder"] = scenario.get("folder")
        fixture["file"] = scenario.get("file")
        _write_fixture(fixture)

    print()
    print(f"  All {total} scenarios captured successfully.")
    print(f"  Fixture files written to {SNAPSHOTS_DIR}/")
    print()


async def _phase_5_cleanup(bridge: RealBridge) -> None:
    """Create a cleanup task in inbox and move all scenario tasks under it."""
    print("-" * 60)
    print("  Phase 5: Cleanup")
    print("-" * 60)
    print()

    # Create GM-Cleanup task in INBOX (not under project, per D-07)
    date_str = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M")
    cleanup_name = f"🧪 GM-Cleanup (capture {date_str})"
    result = await bridge.send_command(
        "add_task",
        {"name": cleanup_name},
    )
    cleanup_task_id = result["id"]
    print(f"  Created cleanup task: {cleanup_name}")

    # Move all scenario tasks under the cleanup task.
    # Derived occurrence IDs (e.g. "abc123.0") are already in known_task_ids —
    # they were discovered during Phase 4 capture.
    # Preserved tasks (e.g. 🧪 GM-Phase56-Attached) stay in place — the human
    # invested manual effort (attachment drag-drop) and the next capture
    # re-discovers them in the same location.
    for task_id in known_task_ids - _preserved_task_ids:
        await bridge.send_command(
            "edit_task",
            {"id": task_id, "moveTo": {"position": "ending", "containerId": cleanup_task_id}},
        )

    # Reset mutations applied to preserved tasks during capture so the next run
    # starts from the same baseline. Currently only scenario 04 touches a
    # preserved task (clears note on 🧪 GM-Phase56-Attached). Expand this block
    # if more preserved-task mutations are added.
    if GM_PHASE56_ATTACHED_TASK_ID:
        await bridge.send_command(
            "edit_task",
            {"id": GM_PHASE56_ATTACHED_TASK_ID, "note": ""},
        )
        print("  Reset note on preserved attached task.")

    print("  All test tasks consolidated under the cleanup task.")
    print()
    print("  To clean up:")
    print(f"    1. Delete '{cleanup_name}' from inbox in OmniFocus")
    print("    2. Projects and tags are designed to persist for future captures")
    print()


def _report_cleanup_info() -> None:
    """Print cleanup information for manual recovery."""
    print()
    print("=" * 60)
    print("  Cleanup Information")
    print("=" * 60)
    print()
    if known_task_ids:
        print(f"  Task IDs created: {', '.join(sorted(known_task_ids))}")
    if known_project_ids:
        print(f"  Project IDs: {', '.join(sorted(known_project_ids))}")
    if known_tag_ids:
        print(f"  Tag IDs: {', '.join(sorted(known_tag_ids))}")
    print()
    print("  You can find test tasks by searching for 'GM-' in OmniFocus.")
    print("  Look for '🧪 GM-Cleanup' in the inbox.")
    print()


async def _capture_initial_state(bridge: RealBridge) -> None:
    """Capture initial state after setup and leftover cleanup."""
    state = await _get_all_raw(bridge)
    initial = filter_to_known_ids(state, known_task_ids, known_project_ids, known_tag_ids)
    # Strip volatile/uncomputed fields (url, added, modified, taskStatus, etc.)
    # but keep id — contract tests need it to seed InMemoryBridge.
    initial = _normalize_initial_state(initial)
    # Replace real OmniFocus IDs with stable symbolic refs
    initial = _symbolize_ids(initial)
    initial_path = SNAPSHOTS_DIR / "initial_state.json"
    initial_path.write_text(
        json.dumps(initial, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(f"  Initial state written to {initial_path}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> int:
    """Run the golden master capture workflow."""
    _phase_1_introduction()

    # Clean slate: nuke and recreate snapshots directory
    if SNAPSHOTS_DIR.exists():
        shutil.rmtree(SNAPSHOTS_DIR)
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    bridge = RealBridge(ipc_dir=DEFAULT_IPC_DIR)

    try:
        # Phase 2: Manual setup (creates project/tags, verifies they exist)
        await _phase_2_manual_setup(bridge)

        # Phase 2b: Phase 56 extensions — project-type matrix + attached task.
        # Registers Phase 56 pre-seeded entity IDs BEFORE _check_leftover_tasks
        # so the pre-seeded attachment task isn't flagged as stale.
        await _phase_2b_phase56_setup(bridge)

        # Check for leftover tasks before capturing initial state --
        # otherwise hasChildren etc. reflect stale data
        await _check_leftover_tasks(bridge)

        # Capture initial state (projects + tags only; tasks created during scenarios)
        await _capture_initial_state(bridge)

        # Phase 3: Confirmation
        if not _phase_3_confirmation():
            print("\nCapture cancelled.")
            return 1

        # Phase 4: Capture
        await _phase_4_capture(bridge)

        # Phase 5: Cleanup
        await _phase_5_cleanup(bridge)

    except (KeyboardInterrupt, asyncio.CancelledError):
        # User hit Ctrl+C partway through — run Phase 5 cleanup on whatever
        # tasks have been created so far so they end up under a single
        # 🧪 GM-Cleanup task in the inbox (same deletion UX as a full run).
        #
        # We catch BOTH exceptions because Ctrl+C behaves differently
        # depending on where it lands:
        #   - During a sync blocking call (e.g. input() in Phase 3),
        #     Python raises KeyboardInterrupt directly.
        #   - During an asyncio await (e.g. bridge.send_command), asyncio's
        #     SIGINT handler cancels the main task, which propagates
        #     CancelledError up through the awaits.
        #
        # Once the main task is cancelled, subsequent awaits in the same
        # task re-raise CancelledError immediately — so we must
        # current_task().uncancel() before awaiting the cleanup, otherwise
        # Phase 5 can't run a single bridge call.
        print()
        print()
        print("  Capture interrupted — running partial cleanup...")
        current = asyncio.current_task()
        if current is not None:
            current.uncancel()
        try:
            await _phase_5_cleanup(bridge)
        except Exception as cleanup_exc:
            print(f"  Partial cleanup failed: {cleanup_exc}")
            _report_cleanup_info()
        return 130  # conventional exit code for SIGINT

    except Exception as exc:
        # Phase 6: Error handling
        print()
        print(f"  ERROR: {exc}")
        _report_cleanup_info()
        return 1

    print("=" * 60)
    print("  Golden master capture complete!")
    print("=" * 60)
    print()
    print("  Next steps:")
    print("    1. Run contract tests: uv run pytest tests/test_bridge_contract.py -x -v")
    print("    2. Run full suite: uv run pytest")
    print("    3. Clean up: delete '🧪 GM-Cleanup' from inbox")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
