"""Golden master capture: record RealBridge behavior for contract tests.

This script is for HUMAN execution only. Do NOT run from CI or agents.
See uat/README.md for details and safety rules (SAFE-01, SAFE-02).

Usage:
    uv run python uat/capture_golden_master.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from omnifocus_operator.bridge._real import DEFAULT_IPC_DIR, RealBridge

from omnifocus_operator.bridge.adapter import adapt_snapshot
from tests.golden.normalize import (
    filter_to_known_ids,
    normalize_response,
    normalize_state,
)

GOLDEN_DIR = Path(__file__).resolve().parent.parent / "tests" / "golden"


# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------

# Placeholders filled in at runtime after manual setup and add_task responses.
GM_PROJECT_ID: str = ""
GM_TAG1_ID: str = ""
GM_TAG2_ID: str = ""

# Task IDs accumulated from add_task responses
TASK_IDS: dict[str, str] = {}

# All known IDs for filtering get_all
known_task_ids: set[str] = set()
known_project_ids: set[str] = set()
known_tag_ids: set[str] = set()


def _build_scenarios() -> list[dict[str, Any]]:
    """Build the 17 scenario definitions using captured IDs."""
    return [
        # --- add_task scenarios ---
        {
            "scenario": "01_add_inbox_task",
            "description": "Create a basic task in inbox with no optional fields",
            "operation": "add_task",
            "params": {"name": "GM-InboxTask"},
            "capture_id_as": "inbox_task",
        },
        {
            "scenario": "02_add_task_with_parent",
            "description": "Create a task under a project",
            "operation": "add_task",
            "params": {"name": "GM-ParentTask", "parent": GM_PROJECT_ID},
            "capture_id_as": "parent_task",
        },
        {
            "scenario": "03_add_task_all_fields",
            "description": "Create a task with all optional fields set",
            "operation": "add_task",
            "params": {
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
            "scenario": "04_add_task_with_tags",
            "description": "Create a task with two tags",
            "operation": "add_task",
            "params": {
                "name": "GM-TaggedTask",
                "tagIds": [GM_TAG1_ID, GM_TAG2_ID],
            },
            "capture_id_as": "tagged_task",
        },
        # --- edit_task scenarios ---
        {
            "scenario": "05_edit_name",
            "description": "Rename a task",
            "operation": "edit_task",
            "params_fn": lambda: {"id": TASK_IDS["inbox_task"], "name": "GM-InboxTask-Renamed"},
        },
        {
            "scenario": "06_edit_note",
            "description": "Set note on a task",
            "operation": "edit_task",
            "params_fn": lambda: {"id": TASK_IDS["inbox_task"], "note": "Added note via edit"},
        },
        {
            "scenario": "07_edit_flagged",
            "description": "Flag a task",
            "operation": "edit_task",
            "params_fn": lambda: {"id": TASK_IDS["inbox_task"], "flagged": True},
        },
        {
            "scenario": "08_edit_dates",
            "description": "Set due and defer dates on a task",
            "operation": "edit_task",
            "params_fn": lambda: {
                "id": TASK_IDS["parent_task"],
                "dueDate": "2026-12-20T17:00:00.000Z",
                "deferDate": "2026-12-18T09:00:00.000Z",
            },
        },
        {
            "scenario": "09_clear_dates",
            "description": "Clear due and defer dates (null means clear)",
            "operation": "edit_task",
            "params_fn": lambda: {
                "id": TASK_IDS["parent_task"],
                "dueDate": None,
                "deferDate": None,
            },
        },
        {
            "scenario": "10_edit_estimated_minutes",
            "description": "Set estimated minutes on a task",
            "operation": "edit_task",
            "params_fn": lambda: {"id": TASK_IDS["inbox_task"], "estimatedMinutes": 45},
        },
        {
            "scenario": "11_add_tags",
            "description": "Add a tag to a task",
            "operation": "edit_task",
            "params_fn": lambda: {"id": TASK_IDS["inbox_task"], "addTagIds": [GM_TAG1_ID]},
        },
        {
            "scenario": "12_remove_tags",
            "description": "Remove a tag from a task",
            "operation": "edit_task",
            "params_fn": lambda: {"id": TASK_IDS["inbox_task"], "removeTagIds": [GM_TAG1_ID]},
        },
        {
            "scenario": "13_replace_tags",
            "description": "Replace tags on a task (remove all, add one)",
            "operation": "edit_task",
            "params_fn": lambda: {
                "id": TASK_IDS["inbox_task"],
                "removeTagIds": [],
                "addTagIds": [GM_TAG2_ID],
            },
        },
        {
            "scenario": "14_lifecycle_complete",
            "description": "Complete a task",
            "operation": "edit_task",
            "params_fn": lambda: {"id": TASK_IDS["inbox_task"], "lifecycle": "complete"},
        },
        {
            "scenario": "15_lifecycle_drop",
            "description": "Create a task then drop it",
            "operation": "add_task",
            "params": {"name": "GM-DropTarget"},
            "capture_id_as": "drop_target",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {"id": TASK_IDS["drop_target"], "lifecycle": "drop"},
            },
        },
        {
            "scenario": "16_move_to_project",
            "description": "Create an inbox task then move it to a project",
            "operation": "add_task",
            "params": {"name": "GM-MoveTarget"},
            "capture_id_as": "move_target",
            "followup": {
                "operation": "edit_task",
                "params_fn": lambda: {
                    "id": TASK_IDS["move_target"],
                    "moveTo": {"containerId": GM_PROJECT_ID},
                },
            },
        },
        {
            "scenario": "17_move_to_inbox",
            "description": "Move a task back to inbox",
            "operation": "edit_task",
            "params_fn": lambda: {
                "id": TASK_IDS["move_target"],
                "moveTo": {"containerId": None},
            },
        },
    ]


# ---------------------------------------------------------------------------
# Capture helpers
# ---------------------------------------------------------------------------


async def _get_all_adapted(bridge: RealBridge) -> dict[str, Any]:
    """Get full snapshot from bridge and adapt to model format."""
    raw = await bridge.send_command("get_all")
    adapt_snapshot(raw)
    return raw


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

    # Execute the write operation
    response = await bridge.send_command(operation, params)

    # If this is an add_task, track the new ID
    if operation == "add_task":
        capture_key = scenario.get("capture_id_as")
        if capture_key:
            TASK_IDS[capture_key] = response["id"]
            known_task_ids.add(response["id"])

    # If there's a followup (e.g., add_task then edit_task), run it
    followup = scenario.get("followup")
    if followup:
        followup_params = followup["params_fn"]()
        response = await bridge.send_command(followup["operation"], followup_params)

    # Capture state after all operations for this scenario
    state = await _get_all_adapted(bridge)
    filtered = filter_to_known_ids(state, known_task_ids, known_project_ids, known_tag_ids)

    # Build fixture (params may need resolving for serialization)
    resolved_params = params if isinstance(params, dict) else scenario["params_fn"]()
    if followup:
        resolved_params = followup["params_fn"]()

    fixture: dict[str, Any] = {
        "scenario": scenario["scenario"],
        "description": scenario["description"],
        "operation": followup["operation"] if followup else operation,
        "params": resolved_params,
        "response": normalize_response(response),
        "state_after": normalize_state(filtered),
    }

    desc = scenario["description"]
    print(f"  Scenario {scenario_num:02d}/{total}: {desc}... OK")
    return fixture


def _write_fixture(fixture: dict[str, Any], scenario_name: str) -> None:
    """Write a scenario fixture to a JSON file."""
    path = GOLDEN_DIR / f"scenario_{scenario_name}.json"
    path.write_text(json.dumps(fixture, indent=2, sort_keys=False) + "\n", encoding="utf-8")


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
    print("  1. You manually create a test project and two tags in OmniFocus")
    print("  2. The script verifies each entity exists")
    print("  3. 17 scenarios run automatically (add/edit tasks)")
    print("  4. Fixture JSON files are written to tests/golden/")
    print("  5. Test tasks are consolidated for easy cleanup")
    print()
    print("Prerequisites:")
    print("  - OmniFocus must be running")
    print("  - Bridge script must be installed in OmniFocus")
    print()


async def _phase_2_manual_setup(bridge: RealBridge) -> None:
    """Guide user through creating test entities and verify each one."""
    global GM_PROJECT_ID, GM_TAG1_ID, GM_TAG2_ID

    print("-" * 60)
    print("  Phase 2: Manual Setup")
    print("-" * 60)
    print()

    # --- Project ---
    while True:
        print("Please create a project named 'GM-TestProject' in OmniFocus.")
        input("Press Enter when done... ")
        state = await _get_all_adapted(bridge)
        project = _find_by_name(state.get("projects", []), "GM-TestProject")
        if project:
            GM_PROJECT_ID = project["id"]
            known_project_ids.add(GM_PROJECT_ID)
            print(f"  Found: GM-TestProject (ID: {GM_PROJECT_ID})")
            print()
            break
        print("  ERROR: Project 'GM-TestProject' not found. Please try again.")
        print()

    # --- Tag 1 ---
    while True:
        print("Please create a tag named 'GM-Tag1' in OmniFocus.")
        input("Press Enter when done... ")
        state = await _get_all_adapted(bridge)
        tag = _find_by_name(state.get("tags", []), "GM-Tag1")
        if tag:
            GM_TAG1_ID = tag["id"]
            known_tag_ids.add(GM_TAG1_ID)
            print(f"  Found: GM-Tag1 (ID: {GM_TAG1_ID})")
            print()
            break
        print("  ERROR: Tag 'GM-Tag1' not found. Please try again.")
        print()

    # --- Tag 2 ---
    while True:
        print("Please create a tag named 'GM-Tag2' in OmniFocus.")
        input("Press Enter when done... ")
        state = await _get_all_adapted(bridge)
        tag = _find_by_name(state.get("tags", []), "GM-Tag2")
        if tag:
            GM_TAG2_ID = tag["id"]
            known_tag_ids.add(GM_TAG2_ID)
            print(f"  Found: GM-Tag2 (ID: {GM_TAG2_ID})")
            print()
            break
        print("  ERROR: Tag 'GM-Tag2' not found. Please try again.")
        print()

    # --- Write initial state ---
    state = await _get_all_adapted(bridge)
    initial = filter_to_known_ids(state, known_task_ids, known_project_ids, known_tag_ids)
    initial_normalized = normalize_state(initial)
    initial_path = GOLDEN_DIR / "initial_state.json"
    initial_path.write_text(
        json.dumps(initial_normalized, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(f"  Initial state written to {initial_path}")
    print()


def _phase_3_confirmation() -> bool:
    """Show scenario list and ask user to confirm."""
    print("-" * 60)
    print("  Phase 3: Scenario Preview")
    print("-" * 60)
    print()
    print("The following 17 scenarios will be executed:")
    print()
    print("  add_task scenarios:")
    print("    01. Add inbox task (no parent, no optional fields)")
    print("    02. Add task with parent (under GM-TestProject)")
    print("    03. Add task with all fields (flagged, dates, note, estimate)")
    print("    04. Add task with tags (GM-Tag1, GM-Tag2)")
    print()
    print("  edit_task scenarios:")
    print("    05. Edit name")
    print("    06. Edit note")
    print("    07. Edit flagged")
    print("    08. Edit dates (set due + defer)")
    print("    09. Clear dates (null means clear)")
    print("    10. Edit estimated minutes")
    print("    11. Add tags")
    print("    12. Remove tags")
    print("    13. Replace tags")
    print("    14. Lifecycle: complete")
    print("    15. Lifecycle: drop (creates a task first)")
    print("    16. Move to project (creates inbox task first)")
    print("    17. Move to inbox")
    print()

    answer = input("Ready to run 17 scenarios? [y/N] ").strip().lower()
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
        _write_fixture(fixture, scenario["scenario"])

    print()
    print(f"  All {total} scenarios captured successfully.")
    print(f"  Fixture files written to {GOLDEN_DIR}/")
    print()


async def _phase_5_consolidation(bridge: RealBridge) -> None:
    """Move all test-created tasks under the test project for easy cleanup."""
    print("-" * 60)
    print("  Phase 5: Consolidation")
    print("-" * 60)
    print()

    for task_id in known_task_ids:
        await bridge.send_command(
            "edit_task",
            {"id": task_id, "moveTo": {"containerId": GM_PROJECT_ID}},
        )

    print("  All test tasks consolidated under 'GM-TestProject'.")
    print()
    print("  To clean up:")
    print("    1. Delete the project 'GM-TestProject' in OmniFocus")
    print("       (this deletes all test tasks too)")
    print("    2. Delete tags 'GM-Tag1' and 'GM-Tag2'")
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
    print("  Consolidation project: 'GM-TestProject'")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> int:
    """Run the golden master capture workflow."""
    _phase_1_introduction()

    bridge = RealBridge(ipc_dir=DEFAULT_IPC_DIR)

    try:
        # Phase 2: Manual setup
        await _phase_2_manual_setup(bridge)

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
    print("    3. Clean up OmniFocus (delete GM-TestProject, GM-Tag1, GM-Tag2)")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
