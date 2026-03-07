"""Model Overhaul UAT: validate two-axis status model against live OmniFocus.

This script is for HUMAN execution only. Do NOT run from CI or agents.
See uat/README.md for details and safety rules (SAFE-01, SAFE-02).

What this validates:
  - RealBridge snapshot goes through adapt_snapshot correctly
  - Tasks/projects have urgency + availability (not old status field)
  - Tags/folders have snake_case status values
  - No dead fields remain (active, effectiveActive, etc.)
  - Snapshot validates against Pydantic models

Usage:
    uv run python uat/test_model_overhaul.py
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any

from omnifocus_operator.bridge._real import DEFAULT_IPC_DIR, RealBridge

from omnifocus_operator.bridge.adapter import adapt_snapshot
from omnifocus_operator.models import DatabaseSnapshot

# Dead fields that should NOT appear after adapter transformation
_TASK_DEAD_FIELDS = {
    "status",
    "active",
    "effectiveActive",
    "completed",
    "completedByChildren",
    "sequential",
    "shouldUseFloatingTimeZone",
}

_PROJECT_DEAD_FIELDS = {
    "status",
    "taskStatus",
    "active",
    "effectiveActive",
    "completed",
    "completedByChildren",
    "sequential",
    "shouldUseFloatingTimeZone",
    "containsSingletonActions",
}

_TAG_DEAD_FIELDS = {"active", "effectiveActive", "allowsNextAction"}

_FOLDER_DEAD_FIELDS = {"active", "effectiveActive"}

# Valid enum values after adapter transformation
_VALID_URGENCY = {"none", "due_soon", "overdue"}
_VALID_AVAILABILITY = {"available", "blocked", "completed", "dropped"}
_VALID_TAG_STATUS = {"active", "on_hold", "dropped"}
_VALID_FOLDER_STATUS = {"active", "dropped"}


def _check_no_dead_fields(
    entity: dict[str, Any],
    dead_fields: set[str],
    entity_type: str,
    entity_id: str,
) -> list[str]:
    """Return list of error messages for any dead fields found."""
    errors = []
    for field in dead_fields:
        if field in entity:
            errors.append(
                f"  FAIL: {entity_type} {entity_id} has dead field '{field}' = {entity[field]!r}"
            )
    return errors


def _validate_adapted_snapshot(raw: dict[str, Any]) -> tuple[int, int]:
    """Validate the adapted snapshot has correct field shapes.

    Returns (checks_passed, checks_failed).
    """
    passed = 0
    failed = 0
    errors: list[str] = []

    # --- Tasks ---
    for task in raw.get("tasks", []):
        tid = task.get("id", "???")

        # Must have urgency + availability
        if "urgency" not in task:
            errors.append(f"  FAIL: Task {tid} missing 'urgency'")
        elif task["urgency"] not in _VALID_URGENCY:
            errors.append(f"  FAIL: Task {tid} invalid urgency: {task['urgency']!r}")
        else:
            passed += 1

        if "availability" not in task:
            errors.append(f"  FAIL: Task {tid} missing 'availability'")
        elif task["availability"] not in _VALID_AVAILABILITY:
            errors.append(f"  FAIL: Task {tid} invalid availability: {task['availability']!r}")
        else:
            passed += 1

        dead_errs = _check_no_dead_fields(task, _TASK_DEAD_FIELDS, "Task", tid)
        errors.extend(dead_errs)
        if not dead_errs:
            passed += 1

    # --- Projects ---
    for proj in raw.get("projects", []):
        pid = proj.get("id", "???")

        if "urgency" not in proj:
            errors.append(f"  FAIL: Project {pid} missing 'urgency'")
        elif proj["urgency"] not in _VALID_URGENCY:
            errors.append(f"  FAIL: Project {pid} invalid urgency: {proj['urgency']!r}")
        else:
            passed += 1

        if "availability" not in proj:
            errors.append(f"  FAIL: Project {pid} missing 'availability'")
        elif proj["availability"] not in _VALID_AVAILABILITY:
            errors.append(f"  FAIL: Project {pid} invalid availability: {proj['availability']!r}")
        else:
            passed += 1

        dead_errs = _check_no_dead_fields(proj, _PROJECT_DEAD_FIELDS, "Project", pid)
        errors.extend(dead_errs)
        if not dead_errs:
            passed += 1

    # --- Tags ---
    for tag in raw.get("tags", []):
        gid = tag.get("id", "???")

        if "status" not in tag:
            errors.append(f"  FAIL: Tag {gid} missing 'status'")
        elif tag["status"] not in _VALID_TAG_STATUS:
            errors.append(f"  FAIL: Tag {gid} invalid status: {tag['status']!r}")
        else:
            passed += 1

        dead_errs = _check_no_dead_fields(tag, _TAG_DEAD_FIELDS, "Tag", gid)
        errors.extend(dead_errs)
        if not dead_errs:
            passed += 1

    # --- Folders ---
    for folder in raw.get("folders", []):
        fid = folder.get("id", "???")

        if "status" not in folder:
            errors.append(f"  FAIL: Folder {fid} missing 'status'")
        elif folder["status"] not in _VALID_FOLDER_STATUS:
            errors.append(f"  FAIL: Folder {fid} invalid status: {folder['status']!r}")
        else:
            passed += 1

        dead_errs = _check_no_dead_fields(folder, _FOLDER_DEAD_FIELDS, "Folder", fid)
        errors.extend(dead_errs)
        if not dead_errs:
            passed += 1

    failed = len(errors)
    if errors:
        print("\n".join(errors))

    return passed, failed


async def main() -> int:
    """Fetch snapshot from live OmniFocus and validate two-axis model."""
    print("OmniFocus Operator -- Model Overhaul UAT")
    print("=" * 45)
    print()
    print(f"IPC directory: {DEFAULT_IPC_DIR}")
    print()

    bridge = RealBridge(ipc_dir=DEFAULT_IPC_DIR)

    # Step 1: Fetch raw snapshot from OmniFocus
    print("Sending snapshot command to OmniFocus...")
    try:
        raw = await bridge.send_command("snapshot")
    except Exception as exc:
        print(f"\nERROR: {exc}")
        print()
        print("Troubleshooting:")
        print("  - Is OmniFocus running?")
        print("  - Is the bridge script installed in OmniFocus?")
        print(f"  - Does the IPC directory exist? {DEFAULT_IPC_DIR}")
        return 1

    task_count = len(raw.get("tasks", []))
    proj_count = len(raw.get("projects", []))
    tag_count = len(raw.get("tags", []))
    folder_count = len(raw.get("folders", []))
    print(
        f"Raw snapshot: {task_count} tasks, {proj_count} projects, "
        f"{tag_count} tags, {folder_count} folders"
    )

    # Step 2: Run adapter transformation
    print("\nRunning adapt_snapshot()...")
    try:
        adapt_snapshot(raw)
    except Exception as exc:
        print(f"\nERROR: adapt_snapshot failed: {exc}")
        return 1
    print("Adapter transformation complete.")

    # Step 3: Validate adapted data has correct shape
    print("\nValidating two-axis status model...")
    passed, failed = _validate_adapted_snapshot(raw)

    print(f"\nChecks: {passed} passed, {failed} failed")

    if failed > 0:
        print("\nSome checks failed. See errors above.")
        return 1

    # Step 4: Validate against Pydantic models
    print("\nValidating against Pydantic DatabaseSnapshot model...")
    try:
        snapshot = DatabaseSnapshot.model_validate(raw)
    except Exception as exc:
        print(f"\nERROR: Pydantic validation failed: {exc}")
        return 1

    print(f"\n  Tasks:        {len(snapshot.tasks)}")
    print(f"  Projects:     {len(snapshot.projects)}")
    print(f"  Tags:         {len(snapshot.tags)}")
    print(f"  Folders:      {len(snapshot.folders)}")
    print(f"  Perspectives: {len(snapshot.perspectives)}")

    # Step 5: Spot-check a few entities
    print("\nSpot checks:")
    if snapshot.tasks:
        t = snapshot.tasks[0]
        print(f"  Task '{t.name}': urgency={t.urgency}, availability={t.availability}")
    if snapshot.projects:
        p = snapshot.projects[0]
        print(f"  Project '{p.name}': urgency={p.urgency}, availability={p.availability}")
    if snapshot.tags:
        g = snapshot.tags[0]
        print(f"  Tag '{g.name}': status={g.status}")
    if snapshot.folders:
        f = snapshot.folders[0]
        print(f"  Folder '{f.name}': status={f.status}")

    print("\nUAT PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
