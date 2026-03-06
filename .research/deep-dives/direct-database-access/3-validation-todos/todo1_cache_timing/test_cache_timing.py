#!/usr/bin/env python3
"""
SQLite Cache Timing Test

Tests whether OmniFocus's SQLite cache updates immediately after writes
via the URL scheme. Creates a test task, modifies it, deletes it, and
measures how quickly each change appears in the SQLite database.

Safety: All tasks use prefix __CACHE_TIMING_TEST__ and are cleaned
up in a finally block.

Usage: python test_cache_timing.py
"""

import json
import sqlite3
import subprocess
import time
import urllib.parse
import uuid
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SQLITE_DB = (
    Path.home()
    / "Library"
    / "Group Containers"
    / "34YW5XSRB7.com.omnigroup.OmniFocus"
    / "com.omnigroup.OmniFocus4"
    / "com.omnigroup.OmniFocusModel"
    / "OmniFocusDatabase.db"
)

IPC_DIR = (
    Path.home()
    / "Library"
    / "Containers"
    / "com.omnigroup.OmniFocus4"
    / "Data"
    / "Documents"
    / "omnifocus-operator"
    / "ipc"
)

REQUEST_FILE = "cache_timing.request.json"
RESPONSE_FILE = "cache_timing.response.json"

POLL_INTERVAL = 0.05  # 50ms
POLL_TIMEOUT = 10.0  # 10 seconds

# ---------------------------------------------------------------------------
# OmniJS script (FIXED — never changes between runs)
# ---------------------------------------------------------------------------

# The script reads operation + params from a request file,
# executes, and writes the result to a response file.
# Because the script text is constant, macOS only prompts once.
OMNIJS_SCRIPT = """
(function() {
    var ipcDir = "IPC_DIR_PLACEHOLDER";
    var reqPath = ipcDir + "/cache_timing.request.json";
    var respPath = ipcDir + "/cache_timing.response.json";

    var reqUrl = URL.fromPath(reqPath, false);
    var reqFW = FileWrapper.fromURL(reqUrl, null);
    var req = JSON.parse(reqFW.contents.toString());

    var result = {success: true};

    if (req.op === "create") {
        var task = new Task(req.name);
        result.id = task.id.primaryKey;
        result.name = task.name;
    } else if (req.op === "modify") {
        var allTasks = flattenedTasks;
        var task = null;
        for (var i = 0; i < allTasks.length; i++) {
            if (allTasks[i].id.primaryKey === req.id) {
                task = allTasks[i];
                break;
            }
        }
        if (task) {
            task.name = req.newName;
            result.found = true;
        } else {
            result.found = false;
        }
    } else if (req.op === "delete") {
        var allTasks = flattenedTasks;
        var task = null;
        for (var i = 0; i < allTasks.length; i++) {
            if (allTasks[i].id.primaryKey === req.id) {
                task = allTasks[i];
                break;
            }
        }
        if (task) {
            deleteObject(task);
            result.deleted = true;
        } else {
            result.deleted = false;
        }
    }

    var respUrl = URL.fromPath(respPath, false);
    var data = Data.fromString(JSON.stringify(result));
    var fw = FileWrapper.withContents(null, data);
    fw.write(respUrl, [FileWrapper.WritingOptions.Atomic], null);
})();
""".strip()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_trigger_url() -> str:
    """Build the OmniFocus URL scheme trigger (constant across runs)."""
    ipc_dir = str(IPC_DIR)
    script = OMNIJS_SCRIPT.replace("IPC_DIR_PLACEHOLDER", ipc_dir)
    encoded = urllib.parse.quote(script, safe="")
    return f"omnifocus:///omnijs-run?script={encoded}"


def trigger_omnifocus(url: str) -> None:
    """Fire the OmniJS script via the OmniFocus URL scheme."""
    subprocess.run(["open", "-g", url], check=True, capture_output=True)


def write_request(op: str, **params) -> None:
    """Write a request JSON file for the OmniJS script to read."""
    request = {"op": op, **params}
    request_path = IPC_DIR / REQUEST_FILE
    request_path.write_text(json.dumps(request))


def poll_for_response() -> dict:
    """Poll until the OmniJS response file appears."""
    response_path = IPC_DIR / RESPONSE_FILE
    start = time.monotonic()
    while time.monotonic() - start < POLL_TIMEOUT:
        if response_path.exists():
            try:
                data = json.loads(response_path.read_text())
                response_path.unlink(missing_ok=True)
                return data
            except (json.JSONDecodeError, OSError):
                pass
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(f"OmniJS response not received within {POLL_TIMEOUT}s")


def query_task(task_id: str) -> dict | None:
    """Query the SQLite cache for a task by persistentIdentifier."""
    conn = sqlite3.connect(str(SQLITE_DB))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT persistentIdentifier, name, blocked, overdue, dueSoon "
        "FROM Task WHERE persistentIdentifier = ?",
        (task_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def poll_sqlite_for_task(task_id: str, timeout: float = POLL_TIMEOUT) -> float:
    """Poll SQLite until a task appears. Returns elapsed seconds."""
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        if query_task(task_id) is not None:
            return time.monotonic() - start
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(f"Task {task_id} not visible in SQLite within {timeout}s")


def poll_sqlite_for_name(task_id: str, expected_name: str, timeout: float = POLL_TIMEOUT) -> float:
    """Poll SQLite until a task's name matches. Returns elapsed seconds."""
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        row = query_task(task_id)
        if row and row["name"] == expected_name:
            return time.monotonic() - start
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(f"Task {task_id} name not updated to '{expected_name}' within {timeout}s")


def poll_sqlite_for_deletion(task_id: str, timeout: float = POLL_TIMEOUT) -> float:
    """Poll SQLite until a task is gone. Returns elapsed seconds."""
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        if query_task(task_id) is None:
            return time.monotonic() - start
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(f"Task {task_id} still in SQLite after {timeout}s")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    test_uuid = uuid.uuid4().hex[:12]
    task_name = f"__CACHE_TIMING_TEST_{test_uuid}__"
    modified_name = f"{task_name}_MODIFIED"

    # Ensure IPC directory exists
    IPC_DIR.mkdir(parents=True, exist_ok=True)

    # Verify SQLite DB exists
    if not SQLITE_DB.exists():
        print(f"ERROR: SQLite database not found at {SQLITE_DB}")
        return

    # Build the trigger URL once (constant script text)
    url = get_trigger_url()

    task_id: str | None = None
    results: dict[str, float] = {}

    print("SQLite Cache Timing Test")
    print("========================")
    print()

    try:
        # --- Step 1: Create ---
        print("[1/3] Creating test task...")
        write_request("create", name=task_name)

        t0 = time.monotonic()
        trigger_omnifocus(url)
        response = poll_for_response()
        omnijs_elapsed = time.monotonic() - t0

        task_id = response["id"]
        print(f"      OmniJS responded in {omnijs_elapsed:.3f}s (task ID: {task_id})")

        sqlite_elapsed = poll_sqlite_for_task(task_id)
        results["create"] = sqlite_elapsed
        print(f"      Task visible in SQLite after {sqlite_elapsed:.3f}s")
        print()

        # --- Step 2: Modify ---
        print("[2/3] Modifying test task...")
        write_request("modify", id=task_id, newName=modified_name)

        t0 = time.monotonic()
        trigger_omnifocus(url)
        response = poll_for_response()
        omnijs_elapsed = time.monotonic() - t0
        print(f"      OmniJS responded in {omnijs_elapsed:.3f}s")

        sqlite_elapsed = poll_sqlite_for_name(task_id, modified_name)
        results["modify"] = sqlite_elapsed
        print(f"      Name updated in SQLite after {sqlite_elapsed:.3f}s")
        print()

        # --- Step 3: Delete ---
        print("[3/3] Deleting test task...")
        write_request("delete", id=task_id)

        t0 = time.monotonic()
        trigger_omnifocus(url)
        response = poll_for_response()
        omnijs_elapsed = time.monotonic() - t0
        print(f"      OmniJS responded in {omnijs_elapsed:.3f}s")

        sqlite_elapsed = poll_sqlite_for_deletion(task_id)
        results["delete"] = sqlite_elapsed
        print(f"      Task removed from SQLite after {sqlite_elapsed:.3f}s")
        print()

        # Mark as cleaned up since delete succeeded
        task_id = None

        # --- Results ---
        print("RESULTS")
        print("-------")
        print(f"  Create -> SQLite: {results['create']:.3f}s")
        print(f"  Modify -> SQLite: {results['modify']:.3f}s")
        print(f"  Delete -> SQLite: {results['delete']:.3f}s")
        print()

        max_time = max(results.values())
        if max_time < 1.0:
            print(f"Conclusion: SQLite cache updates are near-instant (all under {max_time:.1f}s)")
        else:
            print(f"Conclusion: SQLite cache updates are NOT instant (max {max_time:.1f}s)")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    except Exception as e:
        print(f"\nERROR: {e}")
    finally:
        # Cleanup: delete the test task if it still exists
        if task_id is not None:
            print("\nCleaning up test task...")
            try:
                write_request("delete", id=task_id)
                trigger_omnifocus(url)
                poll_for_response()
                print("Cleanup complete.")
            except Exception as cleanup_err:
                print(f"WARNING: Cleanup failed: {cleanup_err}")
                print(f"You may need to manually delete task: {task_name}")

        # Clean up request file
        req_path = IPC_DIR / REQUEST_FILE
        req_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
