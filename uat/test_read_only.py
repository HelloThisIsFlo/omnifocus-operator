"""Read-only UAT: validate RealBridge snapshot against live OmniFocus.

This script is for HUMAN execution only. Do NOT run from CI or agents.
See uat/README.md for details and safety rules (SAFE-01, SAFE-02).

Usage:
    uv run python uat/test_read_only.py
"""

from __future__ import annotations

import asyncio
import sys

from omnifocus_operator.bridge._real import DEFAULT_IPC_DIR, RealBridge
from omnifocus_operator.models import DatabaseSnapshot


async def main() -> int:
    """Connect to real OmniFocus, dump all data, and validate the snapshot."""
    print("OmniFocus Operator -- Read-Only UAT")
    print("=" * 40)
    print()
    print(f"IPC directory: {DEFAULT_IPC_DIR}")
    print()

    bridge = RealBridge(ipc_dir=DEFAULT_IPC_DIR)

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
        print("  - Check the bridge script logs in OmniFocus console.")
        return 1

    print("Response received. Validating snapshot...")
    try:
        snapshot = DatabaseSnapshot.model_validate(raw)
    except Exception as exc:
        print(f"\nERROR: Failed to validate response as DatabaseSnapshot: {exc}")
        return 1

    print()
    print("Snapshot validated successfully!")
    print()
    print(f"  Tasks:        {len(snapshot.tasks)}")
    print(f"  Projects:     {len(snapshot.projects)}")
    print(f"  Tags:         {len(snapshot.tags)}")
    print(f"  Folders:      {len(snapshot.folders)}")
    print(f"  Perspectives: {len(snapshot.perspectives)}")
    print()
    print("UAT PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
