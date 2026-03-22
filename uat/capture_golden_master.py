"""Golden master capture: record RealBridge behavior for contract tests.

This script is for HUMAN execution only. Do NOT run from CI or agents.
See uat/README.md for details and safety rules (SAFE-01, SAFE-02).

Usage:
    uv run python uat/capture_golden_master.py
"""

from __future__ import annotations

import asyncio
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from omnifocus_operator.bridge.real import DEFAULT_IPC_DIR, RealBridge
from tests.golden_master.normalize import (
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

# Task IDs accumulated from add_task responses
TASK_IDS: dict[str, str] = {}

# All known IDs for filtering get_all
known_task_ids: set[str] = set()
known_project_ids: set[str] = set()
known_tag_ids: set[str] = set()


def _build_scenarios() -> list[dict[str, Any]]:
    """Build ~43 scenario definitions across 7 categories using captured IDs."""
    return [
        # =================================================================
        # 01-add/ (6 scenarios)
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
        # =================================================================
        # 02-edit/ (11 scenarios)
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
        {
            "folder": "02-edit",
            "file": "03_clear_note_null",
            "scenario": "02-edit/03_clear_note_null",
            "description": "Clear note using null",
            "operation": "edit_task",
            "params_fn": lambda: {"id": TASK_IDS["note_target"], "note": None},
        },
        {
            "folder": "02-edit",
            "file": "04_clear_note_empty",
            "scenario": "02-edit/04_clear_note_empty",
            "description": "Clear note using empty string",
            "operation": "edit_task",
            "params_fn": lambda: {"id": TASK_IDS["note_target"], "note": ""},
        },
        {
            "folder": "02-edit",
            "file": "05_flag",
            "scenario": "02-edit/05_flag",
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
            "file": "06_unflag",
            "scenario": "02-edit/06_unflag",
            "description": "Unflag a task",
            "operation": "edit_task",
            "params_fn": lambda: {"id": TASK_IDS["flag_target"], "flagged": False},
        },
        {
            "folder": "02-edit",
            "file": "07_set_dates",
            "scenario": "02-edit/07_set_dates",
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
            "file": "08_clear_dates",
            "scenario": "02-edit/08_clear_dates",
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
            "file": "09_set_estimated",
            "scenario": "02-edit/09_set_estimated",
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
            "file": "10_clear_estimated",
            "scenario": "02-edit/10_clear_estimated",
            "description": "Clear estimated minutes (null means clear)",
            "operation": "edit_task",
            "params_fn": lambda: {
                "id": TASK_IDS["estimate_target"],
                "estimatedMinutes": None,
            },
        },
        {
            "folder": "02-edit",
            "file": "11_set_planned_date",
            "scenario": "02-edit/11_set_planned_date",
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
        # 03-move/ (7 scenarios)
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
        # 05-lifecycle/ (4 scenarios)
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
        # =================================================================
        # 06-combined/ (3 scenarios)
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
        # =================================================================
        # 07-inheritance/ (7 scenarios: 01-04 simple, 03 has chain, 05a-05c deep nesting)
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
            "description": "Deep nesting L3: sub-subtask under L2 (inherits from project through 3 levels)",
            "operation": "add_task",
            "params_fn": lambda: {
                "name": "GM-DeepL3",
                "parent": TASK_IDS["deep_l2"],
            },
            "capture_id_as": "deep_l3",
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
                known_task_ids.add(response["id"])

    # Capture state after all operations for this scenario
    state = await _get_all_raw(bridge)
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
    print("  1. You verify 3 projects and 2 tags exist in OmniFocus")
    print("  2. The script verifies each entity exists")
    print("  3. ~43 scenarios run automatically across 7 categories")
    print("  4. Fixture JSON files are written to tests/golden_master/snapshots/")
    print("     organized in numbered subfolders (01-add/ through 07-inheritance/)")
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

    # Entity definitions: (display_name, global_var_name, entity_list_key)
    projects_to_find = [
        ("🧪 GM-TestProject", "projects"),
        ("🧪 GM-TestProject2", "projects"),
        ("🧪 GM-TestProject-Dated", "projects"),
    ]
    tags_to_find = [
        ("🧪 GM-Tag1", "tags"),
        ("🧪 GM-Tag2", "tags"),
    ]

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
        print("  REMINDER: Ensure 🧪 GM-TestProject-Dated has:")
        print("    - dueDate set (any future date)")
        print("    - deferDate set (any future date)")
        print("    - flagged = true")
        print("  These are required for inheritance scenarios (07-*).")
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
                    input("Press Enter when done... ")
                    state = await _get_all_raw(bridge)
                    entity = _find_by_name(state.get(list_key, []), name)
                    if entity:
                        found_entities[name] = entity
                        print(f"  Found: {name} (ID: {entity['id']})")
                        break
                    print("  ERROR: Not found. Please try again.")
                print()

        GM_PROJECT_ID = found_entities["🧪 GM-TestProject"]["id"]
        GM_PROJECT2_ID = found_entities["🧪 GM-TestProject2"]["id"]
        GM_DATED_PROJECT_ID = found_entities["🧪 GM-TestProject-Dated"]["id"]
        GM_TAG1_ID = found_entities["🧪 GM-Tag1"]["id"]
        GM_TAG2_ID = found_entities["🧪 GM-Tag2"]["id"]
        known_project_ids.update({GM_PROJECT_ID, GM_PROJECT2_ID, GM_DATED_PROJECT_ID})
        known_tag_ids.update({GM_TAG1_ID, GM_TAG2_ID})


async def _check_leftover_tasks(bridge: RealBridge) -> None:
    """Ensure no GM- tasks remain from a previous run."""
    state = await _get_all_raw(bridge)
    leftover = [
        t
        for t in state.get("tasks", [])
        if t.get("name", "").startswith(("GM-", "🧪 GM-")) and t["id"] not in known_project_ids
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
            if t.get("name", "").startswith(("GM-", "🧪 GM-")) and t["id"] not in known_project_ids
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
    print("The following ~43 scenarios will be executed across 7 categories:")
    print()
    print("  01-add/ (6 scenarios):")
    print("    01. Inbox task (minimal)")
    print("    02. With parent project")
    print("    03. All fields (flagged, dates, note, estimate)")
    print("    04. With tags")
    print("    05. Parent + tags")
    print("    06. Max payload (all fields + parent + tags)")
    print()
    print("  02-edit/ (11 scenarios):")
    print("    01. Rename")
    print("    02. Set note")
    print("    03. Clear note (null)")
    print("    04. Clear note (empty string)")
    print("    05. Flag")
    print("    06. Unflag")
    print("    07. Set dates (due + defer)")
    print("    08. Clear dates (null)")
    print("    09. Set estimated minutes")
    print("    10. Clear estimated minutes (null)")
    print("    11. Set planned date")
    print()
    print("  03-move/ (7 scenarios):")
    print("    01. To project (ending)")
    print("    02. To inbox")
    print("    03. To beginning")
    print("    04. After anchor task")
    print("    05. Before anchor task")
    print("    06. Between projects")
    print("    07. Task as parent")
    print()
    print("  04-tags/ (5 scenarios):")
    print("    01. Add tags")
    print("    02. Remove tags")
    print("    03. Replace tags")
    print("    04. Add duplicate tag (no-op)")
    print("    05. Remove absent tag (no-op)")
    print()
    print("  05-lifecycle/ (4 scenarios):")
    print("    01. Complete")
    print("    02. Drop")
    print("    03. Defer (blocked)")
    print("    04. Clear defer (available)")
    print()
    print("  06-combined/ (3 scenarios):")
    print("    01. Fields + move")
    print("    02. Fields + lifecycle")
    print("    03. Subtask add + move out")
    print()
    print("  07-inheritance/ (7 scenarios):")
    print("    01. Effective due date from project")
    print("    02. Effective flagged from project")
    print("    03. Flagged chain (parent task -> child)")
    print("    04. Effective defer date from project")
    print("    05a-c. Deep nesting (3 levels)")
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
        # Attach folder/file for _write_fixture routing
        fixture["folder"] = scenario.get("folder")
        fixture["file"] = scenario.get("file")
        _write_fixture(fixture)

    print()
    print(f"  All {total} scenarios captured successfully.")
    print(f"  Fixture files written to {SNAPSHOTS_DIR}/")
    print()


async def _phase_5_consolidation(bridge: RealBridge) -> None:
    """Create a cleanup task in inbox and move all scenario tasks under it."""
    print("-" * 60)
    print("  Phase 5: Consolidation")
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

    # Move all scenario tasks under the cleanup task
    for task_id in known_task_ids:
        await bridge.send_command(
            "edit_task",
            {"id": task_id, "moveTo": {"position": "ending", "containerId": cleanup_task_id}},
        )

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
    # Keep IDs -- contract tests need them to seed InMemoryBridge and build
    # known_*_ids sets for filter_to_known_ids. Only scenario state_after
    # snapshots are normalized (IDs stripped for comparison).
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

        # Check for leftover tasks BEFORE capturing initial state --
        # otherwise hasChildren etc. reflect stale data
        await _check_leftover_tasks(bridge)

        # Capture initial state (clean, after leftover removal)
        await _capture_initial_state(bridge)

        # Phase 3: Confirmation
        if not _phase_3_confirmation():
            print("\nCapture cancelled.")
            return 1

        # Phase 4: Capture
        await _phase_4_capture(bridge)

        # Phase 5: Consolidation
        await _phase_5_consolidation(bridge)

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
