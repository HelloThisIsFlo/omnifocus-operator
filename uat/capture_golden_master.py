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
GM_TAG1_ID: str = ""
GM_TAG2_ID: str = ""

# Task IDs accumulated from add_task responses
TASK_IDS: dict[str, str] = {}

# All known IDs for filtering get_all
known_task_ids: set[str] = set()
known_project_ids: set[str] = set()
known_tag_ids: set[str] = set()


def _build_scenarios() -> list[dict[str, Any]]:
    """Build the 20 scenario definitions using captured IDs."""
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
                    "moveTo": {"position": "ending", "containerId": GM_PROJECT_ID},
                },
            },
        },
        {
            "scenario": "17_move_to_inbox",
            "description": "Move a task back to inbox",
            "operation": "edit_task",
            "params_fn": lambda: {
                "id": TASK_IDS["move_target"],
                "moveTo": {"position": "ending", "containerId": None},
            },
        },
        # --- parent disambiguation scenarios ---
        {
            "scenario": "18_add_subtask_under_task",
            "description": "Create a sub-task under a task in a project (parent != project)",
            "operation": "add_task",
            "params_fn": lambda: {
                "name": "GM-Subtask",
                "parent": TASK_IDS["parent_task"],
            },
            "capture_id_as": "subtask",
        },
        {
            "scenario": "19_move_subtask_to_inbox",
            "description": "Move a sub-task back to inbox (clears both parent and project)",
            "operation": "edit_task",
            "params_fn": lambda: {
                "id": TASK_IDS["subtask"],
                "moveTo": {"position": "ending", "containerId": None},
            },
        },
        {
            "scenario": "20_combined_edit",
            "description": "Edit multiple fields in a single call (name + note + flagged + tags)",
            "operation": "edit_task",
            "params_fn": lambda: {
                "id": TASK_IDS["tagged_task"],
                "name": "GM-TaggedTask-MultiEdit",
                "note": "Multi-edit test",
                "flagged": True,
                "addTagIds": [GM_TAG1_ID],
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

    # Capture state after all operations for this scenario
    state = await _get_all_raw(bridge)
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


def _write_fixture(fixture: dict[str, Any], scenario_name: str) -> None:
    """Write a scenario fixture to a JSON file."""
    path = SNAPSHOTS_DIR / f"scenario_{scenario_name}.json"
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
    print("  3. 20 scenarios run automatically (add/edit tasks)")
    print("  4. Fixture JSON files are written to tests/golden_master/snapshots/")
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

    # One upfront query to check what already exists
    state = await _get_all_raw(bridge)
    project = _find_by_name(state.get("projects", []), "🧪 GM-TestProject")
    tag1 = _find_by_name(state.get("tags", []), "🧪 GM-Tag1")
    tag2 = _find_by_name(state.get("tags", []), "🧪 GM-Tag2")

    if project and tag1 and tag2:
        GM_PROJECT_ID = project["id"]
        GM_TAG1_ID = tag1["id"]
        GM_TAG2_ID = tag2["id"]
        known_project_ids.add(GM_PROJECT_ID)
        known_tag_ids.update({GM_TAG1_ID, GM_TAG2_ID})
        print(f"  ✓ 🧪 GM-TestProject (ID: {GM_PROJECT_ID})")
        print(f"  ✓ 🧪 GM-Tag1 (ID: {GM_TAG1_ID})")
        print(f"  ✓ 🧪 GM-Tag2 (ID: {GM_TAG2_ID})")
        print("  All entities found — skipping manual setup.")
        print()
    else:
        # Guide through missing entities one by one
        if project:
            GM_PROJECT_ID = project["id"]
            known_project_ids.add(GM_PROJECT_ID)
            print(f"  ✓ 🧪 GM-TestProject (ID: {GM_PROJECT_ID})")
        else:
            while True:
                print("Please create a project named '🧪 GM-TestProject' in OmniFocus.")
                input("Press Enter when done... ")
                state = await _get_all_raw(bridge)
                project = _find_by_name(state.get("projects", []), "🧪 GM-TestProject")
                if project:
                    GM_PROJECT_ID = project["id"]
                    known_project_ids.add(GM_PROJECT_ID)
                    print(f"  ✓ 🧪 GM-TestProject (ID: {GM_PROJECT_ID})")
                    break
                print("  ERROR: Not found. Please try again.")
            print()

        if tag1:
            GM_TAG1_ID = tag1["id"]
            known_tag_ids.add(GM_TAG1_ID)
            print(f"  ✓ 🧪 GM-Tag1 (ID: {GM_TAG1_ID})")
        else:
            while True:
                print("Please create a tag named '🧪 GM-Tag1' in OmniFocus.")
                input("Press Enter when done... ")
                state = await _get_all_raw(bridge)
                tag1 = _find_by_name(state.get("tags", []), "🧪 GM-Tag1")
                if tag1:
                    GM_TAG1_ID = tag1["id"]
                    known_tag_ids.add(GM_TAG1_ID)
                    print(f"  ✓ 🧪 GM-Tag1 (ID: {GM_TAG1_ID})")
                    break
                print("  ERROR: Not found. Please try again.")
            print()

        if tag2:
            GM_TAG2_ID = tag2["id"]
            known_tag_ids.add(GM_TAG2_ID)
            print(f"  ✓ 🧪 GM-Tag2 (ID: {GM_TAG2_ID})")
        else:
            while True:
                print("Please create a tag named '🧪 GM-Tag2' in OmniFocus.")
                input("Press Enter when done... ")
                state = await _get_all_raw(bridge)
                tag2 = _find_by_name(state.get("tags", []), "🧪 GM-Tag2")
                if tag2:
                    GM_TAG2_ID = tag2["id"]
                    known_tag_ids.add(GM_TAG2_ID)
                    print(f"  ✓ 🧪 GM-Tag2 (ID: {GM_TAG2_ID})")
                    break
                print("  ERROR: Not found. Please try again.")
            print()

    # --- Write initial state ---
    state = await _get_all_raw(bridge)
    initial = filter_to_known_ids(state, known_task_ids, known_project_ids, known_tag_ids)
    # Keep IDs — contract tests need them to seed InMemoryBridge and build
    # known_*_ids sets for filter_to_known_ids. Only scenario state_after
    # snapshots are normalized (IDs stripped for comparison).
    initial_path = SNAPSHOTS_DIR / "initial_state.json"
    initial_path.write_text(
        json.dumps(initial, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(f"  Initial state written to {initial_path}")
    print()


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
            print("  All clear — no leftover tasks found.")
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
    print("The following 20 scenarios will be executed:")
    print()
    print("  add_task scenarios:")
    print("    01. Add inbox task (no parent, no optional fields)")
    print("    02. Add task with parent (under 🧪 GM-TestProject)")
    print("    03. Add task with all fields (flagged, dates, note, estimate)")
    print("    04. Add task with tags (🧪 GM-Tag1, 🧪 GM-Tag2)")
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
    print("  parent disambiguation scenarios:")
    print("    18. Add sub-task under task (parent != project)")
    print("    19. Move sub-task to inbox")
    print("    20. Combined multi-action edit")
    print()

    answer = input("Ready to run 20 scenarios? [y/N] ").strip().lower()
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
    print(f"  Fixture files written to {SNAPSHOTS_DIR}/")
    print()


async def _phase_5_consolidation(bridge: RealBridge) -> None:
    """Create a disposable parent task and move all scenario tasks under it."""
    print("-" * 60)
    print("  Phase 5: Consolidation")
    print("-" * 60)
    print()

    # Create a disposable parent task under the project
    date_str = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M")
    cleanup_name = f"⚠️ Delete this task (GM capture {date_str})"
    result = await bridge.send_command(
        "add_task",
        {"name": cleanup_name, "parent": GM_PROJECT_ID},
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
    print("  To clean up: delete the task '⚠️ Delete this task...' in OmniFocus.")
    print("  The project and tags can stay for future captures.")
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
    print("  Look for '⚠️ Delete this task...' under '🧪 GM-TestProject'.")
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

        # Check for leftover tasks from previous runs
        await _check_leftover_tasks(bridge)

        # Phase 3: Confirmation
        if not _phase_3_confirmation():
            print("\nCapture cancelled.")
            return 1

        # Clean slate: nuke and recreate snapshots directory
        if SNAPSHOTS_DIR.exists():
            shutil.rmtree(SNAPSHOTS_DIR)
        SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

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
    print("    3. Clean up: delete '⚠️ Delete this task...' under '🧪 GM-TestProject'")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
