#!/usr/bin/env python3
"""
SQLite Freshness Detection Test

Explores every possible approach for detecting whether the OmniFocus
SQLite cache has been updated after a bridge write. For each approach,
we snapshot "before" values, trigger a single write via the OmniJS
bridge, then immediately check "after" values — no polling, no sleep.

We then re-check with a fresh SQLite connection, after 500ms, and
after 2s, to see if any indicators are delayed.

The goal: find reliable freshness signals so we can answer "has SQLite
caught up?" without polling.

Safety:
- All writes go through the OmniJS URL scheme (never write to SQLite)
- Test task uses prefix __FRESHNESS_TEST_{uuid}__
- Cleanup in try/finally
- SQLite opened read-only

Usage: python test_sqlite_freshness.py
"""

import contextlib
import json
import os
import sqlite3
import struct
import subprocess
import time
import urllib.parse
import uuid
from dataclasses import dataclass, field
from pathlib import Path

# -------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------

SQLITE_DB = (
    Path.home()
    / "Library"
    / "Group Containers"
    / "34YW5XSRB7.com.omnigroup.OmniFocus"
    / "com.omnigroup.OmniFocus4"
    / "com.omnigroup.OmniFocusModel"
    / "OmniFocusDatabase.db"
)

SQLITE_WAL = SQLITE_DB.parent / "OmniFocusDatabase.db-wal"
SQLITE_SHM = SQLITE_DB.parent / "OmniFocusDatabase.db-shm"

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

REQUEST_FILE = "freshness_test.request.json"
RESPONSE_FILE = "freshness_test.response.json"

POLL_INTERVAL = 0.05  # 50ms
POLL_TIMEOUT = 10.0  # 10 seconds

# -------------------------------------------------------------------
# OmniJS script (FIXED — never changes between runs)
# -------------------------------------------------------------------

OMNIJS_SCRIPT = """
(function() {
    var ipcDir = "IPC_DIR_PLACEHOLDER";
    var reqPath = ipcDir + "/freshness_test.request.json";
    var respPath = ipcDir + "/freshness_test.response.json";

    var reqUrl = URL.fromPath(reqPath, false);
    var reqFW = FileWrapper.fromURL(reqUrl, null);
    var req = JSON.parse(reqFW.contents.toString());

    var result = {success: true};

    if (req.op === "create") {
        var task = new Task(req.name);
        result.id = task.id.primaryKey;
        result.name = task.name;
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
    fw.write(
        respUrl,
        [FileWrapper.WritingOptions.Atomic],
        null
    );
})();
""".strip()

# -------------------------------------------------------------------
# Helpers: Bridge IPC
# -------------------------------------------------------------------


def get_trigger_url() -> str:
    """Build the OmniFocus URL scheme trigger."""
    ipc_dir = str(IPC_DIR)
    script = OMNIJS_SCRIPT.replace("IPC_DIR_PLACEHOLDER", ipc_dir)
    encoded = urllib.parse.quote(script, safe="")
    return f"omnifocus:///omnijs-run?script={encoded}"


def trigger_omnifocus(url: str) -> None:
    """Fire the OmniJS script via the URL scheme."""
    subprocess.run(["open", "-g", url], check=True, capture_output=True)


def write_request(op: str, **params) -> None:
    """Write a request JSON for the OmniJS script."""
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


# -------------------------------------------------------------------
# Helpers: SQLite / filesystem probes
# -------------------------------------------------------------------


def open_readonly_conn() -> sqlite3.Connection:
    """Open a read-only SQLite connection."""
    uri = f"file:{SQLITE_DB}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def stat_file(path: Path) -> os.stat_result | None:
    """Stat a file, returning None if it doesn't exist."""
    try:
        return os.stat(path)
    except FileNotFoundError:
        return None


def get_db_mtime_ns() -> int | None:
    """Get mtime_ns of the main .db file."""
    st = stat_file(SQLITE_DB)
    return st.st_mtime_ns if st else None


def get_wal_mtime_ns() -> int | None:
    """Get mtime_ns of the .db-wal file."""
    st = stat_file(SQLITE_WAL)
    return st.st_mtime_ns if st else None


def get_wal_size() -> int | None:
    """Get size in bytes of the .db-wal file."""
    st = stat_file(SQLITE_WAL)
    return st.st_size if st else None


def get_shm_mtime_ns() -> int | None:
    """Get mtime_ns of the .db-shm file."""
    st = stat_file(SQLITE_SHM)
    return st.st_mtime_ns if st else None


def get_shm_size() -> int | None:
    """Get size in bytes of the .db-shm file."""
    st = stat_file(SQLITE_SHM)
    return st.st_size if st else None


def get_db_inode() -> int | None:
    """Get inode of the main .db file."""
    st = stat_file(SQLITE_DB)
    return st.st_ino if st else None


def get_wal_inode() -> int | None:
    """Get inode of the .db-wal file."""
    st = stat_file(SQLITE_WAL)
    return st.st_ino if st else None


def get_data_version(conn: sqlite3.Connection) -> int:
    """Get PRAGMA data_version (changes on external writes)."""
    return conn.execute("PRAGMA data_version").fetchone()[0]


def get_wal_checkpoint_info(
    conn: sqlite3.Connection,
) -> tuple[int, int, int] | None:
    """Get WAL checkpoint info (read-only safe).

    Uses PRAGMA wal_checkpoint with no argument (read-only query).
    Returns (busy, log_pages, checkpointed_pages) or None on error.
    """
    try:
        row = conn.execute("PRAGMA wal_checkpoint").fetchone()
        return (row[0], row[1], row[2])
    except sqlite3.OperationalError:
        return None


def get_file_change_counter() -> int | None:
    """Read the SQLite file change counter (bytes 24-27).

    In WAL mode this may not update until checkpoint.
    """
    try:
        with open(SQLITE_DB, "rb") as f:
            f.seek(24)
            raw = f.read(4)
            if len(raw) == 4:
                return struct.unpack(">I", raw)[0]
    except OSError:
        pass
    return None


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Get PRAGMA schema_version."""
    return conn.execute("PRAGMA schema_version").fetchone()[0]


def get_page_count(conn: sqlite3.Connection) -> int:
    """Get PRAGMA page_count."""
    return conn.execute("PRAGMA page_count").fetchone()[0]


def get_freelist_count(conn: sqlite3.Connection) -> int:
    """Get PRAGMA freelist_count."""
    return conn.execute("PRAGMA freelist_count").fetchone()[0]


def get_page_size(conn: sqlite3.Connection) -> int:
    """Get PRAGMA page_size."""
    return conn.execute("PRAGMA page_size").fetchone()[0]


def get_journal_mode(conn: sqlite3.Connection) -> str:
    """Get PRAGMA journal_mode."""
    return conn.execute("PRAGMA journal_mode").fetchone()[0]


def get_task_count(conn: sqlite3.Connection) -> int:
    """Get total task count."""
    return conn.execute("SELECT COUNT(*) FROM Task").fetchone()[0]


def query_task_by_id(conn: sqlite3.Connection, task_id: str) -> dict | None:
    """Query a task by persistentIdentifier."""
    row = conn.execute(
        "SELECT persistentIdentifier, name FROM Task WHERE persistentIdentifier = ?",
        (task_id,),
    ).fetchone()
    return dict(row) if row else None


def get_wal_header_info() -> dict | None:
    """Read the WAL file header (first 32 bytes).

    WAL header format:
    - Bytes 0-3:   Magic number (0x377f0682 or 0x377f0683)
    - Bytes 4-7:   File format version (3007000)
    - Bytes 8-11:  Database page size
    - Bytes 12-15: Checkpoint sequence number
    - Bytes 16-19: Salt-1
    - Bytes 20-23: Salt-2
    - Bytes 24-27: Checksum-1
    - Bytes 28-31: Checksum-2
    """
    try:
        with open(SQLITE_WAL, "rb") as f:
            header = f.read(32)
            if len(header) < 32:
                return None
            magic = struct.unpack(">I", header[0:4])[0]
            version = struct.unpack(">I", header[4:8])[0]
            page_size = struct.unpack(">I", header[8:12])[0]
            ckpt_seq = struct.unpack(">I", header[12:16])[0]
            salt1 = struct.unpack(">I", header[16:20])[0]
            salt2 = struct.unpack(">I", header[20:24])[0]
            return {
                "magic": hex(magic),
                "version": version,
                "page_size": page_size,
                "checkpoint_seq": ckpt_seq,
                "salt1": salt1,
                "salt2": salt2,
            }
    except OSError:
        return None


def estimate_wal_frame_count() -> int | None:
    """Estimate WAL frame count from file size.

    WAL format: 32-byte header, then frames.
    Each frame = 24-byte frame header + page_size bytes.
    """
    wal_info = get_wal_header_info()
    wal_size = get_wal_size()
    if wal_info is None or wal_size is None:
        return None
    page_size = wal_info["page_size"]
    frame_size = 24 + page_size
    data_size = wal_size - 32  # subtract header
    if data_size <= 0:
        return 0
    return data_size // frame_size


def get_db_header_version() -> int | None:
    """Read the SQLite version-valid-for number (bytes 92-95).

    This is set to the change counter when the database is modified.
    In WAL mode, may differ from the change counter.
    """
    try:
        with open(SQLITE_DB, "rb") as f:
            f.seek(92)
            raw = f.read(4)
            if len(raw) == 4:
                return struct.unpack(">I", raw)[0]
    except OSError:
        pass
    return None


def get_db_write_format() -> int | None:
    """Read the SQLite write format (byte 18).

    Value 2 = WAL mode.
    """
    try:
        with open(SQLITE_DB, "rb") as f:
            f.seek(18)
            raw = f.read(1)
            if len(raw) == 1:
                return raw[0]
    except OSError:
        pass
    return None


def get_db_read_format() -> int | None:
    """Read the SQLite read format (byte 19).

    Value 2 = WAL mode.
    """
    try:
        with open(SQLITE_DB, "rb") as f:
            f.seek(19)
            raw = f.read(1)
            if len(raw) == 1:
                return raw[0]
    except OSError:
        pass
    return None


# -------------------------------------------------------------------
# Snapshot: collect all indicators at once
# -------------------------------------------------------------------


@dataclass
class Snapshot:
    """All freshness indicators captured at a single point."""

    label: str
    timestamp_mono: float = 0.0

    # Filesystem indicators
    db_mtime_ns: int | None = None
    wal_mtime_ns: int | None = None
    wal_size: int | None = None
    shm_mtime_ns: int | None = None
    shm_size: int | None = None
    db_inode: int | None = None
    wal_inode: int | None = None

    # SQLite header (raw bytes)
    file_change_counter: int | None = None
    header_version_valid: int | None = None
    db_write_format: int | None = None
    db_read_format: int | None = None

    # WAL header
    wal_checkpoint_seq: int | None = None
    wal_salt1: int | None = None
    wal_salt2: int | None = None
    wal_frame_count_est: int | None = None

    # SQLite PRAGMAs (require a connection)
    data_version: int | None = None
    wal_ckpt_busy: int | None = None
    wal_ckpt_log: int | None = None
    wal_ckpt_checkpointed: int | None = None
    page_count: int | None = None
    freelist_count: int | None = None
    schema_version: int | None = None
    journal_mode: str | None = None

    # Data-level indicators
    task_count: int | None = None
    task_found: bool | None = None

    # Extra: all table row counts
    extra_counts: dict = field(default_factory=dict)


def take_snapshot(
    label: str,
    conn: sqlite3.Connection | None = None,
    task_id: str | None = None,
) -> Snapshot:
    """Capture all freshness indicators at once."""
    snap = Snapshot(label=label)
    snap.timestamp_mono = time.monotonic()

    # --- Filesystem ---
    snap.db_mtime_ns = get_db_mtime_ns()
    snap.wal_mtime_ns = get_wal_mtime_ns()
    snap.wal_size = get_wal_size()
    snap.shm_mtime_ns = get_shm_mtime_ns()
    snap.shm_size = get_shm_size()
    snap.db_inode = get_db_inode()
    snap.wal_inode = get_wal_inode()

    # --- Raw header bytes ---
    snap.file_change_counter = get_file_change_counter()
    snap.header_version_valid = get_db_header_version()
    snap.db_write_format = get_db_write_format()
    snap.db_read_format = get_db_read_format()

    # --- WAL header ---
    wal_info = get_wal_header_info()
    if wal_info:
        snap.wal_checkpoint_seq = wal_info["checkpoint_seq"]
        snap.wal_salt1 = wal_info["salt1"]
        snap.wal_salt2 = wal_info["salt2"]
    snap.wal_frame_count_est = estimate_wal_frame_count()

    # --- PRAGMAs (need connection) ---
    if conn is not None:
        snap.data_version = get_data_version(conn)
        ckpt = get_wal_checkpoint_info(conn)
        if ckpt is not None:
            snap.wal_ckpt_busy = ckpt[0]
            snap.wal_ckpt_log = ckpt[1]
            snap.wal_ckpt_checkpointed = ckpt[2]
        snap.page_count = get_page_count(conn)
        snap.freelist_count = get_freelist_count(conn)
        snap.schema_version = get_schema_version(conn)
        snap.journal_mode = get_journal_mode(conn)

        # Data-level
        snap.task_count = get_task_count(conn)

        if task_id:
            row = query_task_by_id(conn, task_id)
            snap.task_found = row is not None

    return snap


# -------------------------------------------------------------------
# Report formatting
# -------------------------------------------------------------------

# Each approach: (name, attribute(s), description)
APPROACHES: list[tuple[str, list[str], str]] = [
    (
        "1. DB file mtime_ns",
        ["db_mtime_ns"],
        "os.stat() on .db file",
    ),
    (
        "2. WAL file mtime_ns",
        ["wal_mtime_ns"],
        "os.stat() on .db-wal file",
    ),
    (
        "3. WAL file size",
        ["wal_size"],
        "Size of .db-wal in bytes",
    ),
    (
        "4. PRAGMA data_version",
        ["data_version"],
        "Changes on external modification",
    ),
    (
        "5. WAL checkpoint info",
        ["wal_ckpt_busy", "wal_ckpt_log", "wal_ckpt_checkpointed"],
        "PRAGMA wal_checkpoint(PASSIVE)",
    ),
    (
        "6. File change counter",
        ["file_change_counter"],
        "Bytes 24-27 of DB header",
    ),
    (
        "7. Immediate row read",
        ["task_found"],
        "Query task by ID (no polling)",
    ),
    (
        "8. Row count change",
        ["task_count"],
        "SELECT COUNT(*) FROM Task",
    ),
    (
        "9. PRAGMA page_count",
        ["page_count"],
        "Total pages in database",
    ),
    (
        "10. PRAGMA freelist_count",
        ["freelist_count"],
        "Free pages in database",
    ),
    (
        "11. WAL frame count (est.)",
        ["wal_frame_count_est"],
        "Estimated from WAL file size",
    ),
    (
        "12. WAL checkpoint seq",
        ["wal_checkpoint_seq"],
        "From WAL header bytes 12-15",
    ),
    (
        "13. WAL salt values",
        ["wal_salt1", "wal_salt2"],
        "WAL header salt-1 and salt-2",
    ),
    (
        "14. SHM file mtime_ns",
        ["shm_mtime_ns"],
        "os.stat() on .db-shm file",
    ),
    (
        "15. SHM file size",
        ["shm_size"],
        "Size of .db-shm in bytes",
    ),
    (
        "16. DB inode",
        ["db_inode"],
        "Inode of .db (detects replace)",
    ),
    (
        "17. WAL inode",
        ["wal_inode"],
        "Inode of .db-wal (detects replace)",
    ),
    (
        "18. Header version-valid-for",
        ["header_version_valid"],
        "Bytes 92-95 of DB header",
    ),
    (
        "19. PRAGMA schema_version",
        ["schema_version"],
        "Schema version number",
    ),
    (
        "20. DB write/read format",
        ["db_write_format", "db_read_format"],
        "Bytes 18-19 of DB header (2=WAL)",
    ),
]


def fmt_val(val) -> str:
    """Format a value for display, truncating large ints."""
    if val is None:
        return "None"
    if isinstance(val, bool):
        return str(val)
    if isinstance(val, int) and abs(val) > 1_000_000_000:
        return f"{val:,}"
    return str(val)


def did_change(before, after) -> str:
    """Return a change indicator string."""
    if before is None and after is None:
        return "N/A"
    if before == after:
        return "  NO"
    return " YES"


def print_approach_table(
    name: str,
    attrs: list[str],
    desc: str,
    snaps: list[Snapshot],
) -> list[bool]:
    """Print a table for one approach. Returns change flags."""
    changes = []

    print(f"\n{'=' * 72}")
    print(f"  {name}")
    print(f"  {desc}")
    print(f"{'=' * 72}")

    # Header
    labels = [s.label for s in snaps]
    hdr = f"  {'Attr':<28}"
    for lbl in labels:
        hdr += f" {lbl:>16}"
    hdr += "  Changed?"
    print(hdr)
    print(f"  {'-' * 28}" + f" {'-' * 16}" * len(snaps) + "  --------")

    for attr in attrs:
        vals = [getattr(s, attr) for s in snaps]
        row = f"  {attr:<28}"
        for v in vals:
            row += f" {fmt_val(v):>16}"
        # "Changed" = any post-before snap differs from before
        before_val = vals[0]
        any_changed = any(v != before_val for v in vals[1:])
        row += f"  {' YES' if any_changed else '  NO'}"
        print(row)
        changes.append(any_changed)

    return changes


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------


def main() -> None:
    test_uuid = uuid.uuid4().hex[:12]
    task_name = f"__FRESHNESS_TEST_{test_uuid}__"

    IPC_DIR.mkdir(parents=True, exist_ok=True)

    if not SQLITE_DB.exists():
        print(f"ERROR: SQLite database not found at {SQLITE_DB}")
        return

    url = get_trigger_url()
    task_id: str | None = None

    print("SQLite Freshness Detection Test")
    print("================================")
    print()
    print(f"DB:  {SQLITE_DB}")
    print(f"WAL: {SQLITE_WAL}")
    print(f"SHM: {SQLITE_SHM}")
    print()

    # Open a persistent connection (reused across checks)
    conn = open_readonly_conn()
    jmode = get_journal_mode(conn)
    print(f"[INFO] PRAGMA journal_mode = {jmode}")
    print()

    try:
        # --- BEFORE snapshot ---
        print("[1/6] Taking BEFORE snapshot...")
        snap_before = take_snapshot("Before", conn=conn, task_id=None)
        print(f"      Task count: {snap_before.task_count}")
        print()

        # --- Trigger bridge write ---
        print("[2/6] Creating test task via bridge...")
        write_request("create", name=task_name)
        t0 = time.monotonic()
        trigger_omnifocus(url)
        response = poll_for_response()
        bridge_elapsed = time.monotonic() - t0
        task_id = response["id"]
        print(f"      Bridge responded in {bridge_elapsed:.3f}s")
        print(f"      Task ID: {task_id}")
        print()

        # --- IMMEDIATE snapshot (same connection) ---
        print("[3/6] Taking IMMEDIATE snapshot (same conn)...")
        snap_immediate = take_snapshot("Immediate", conn=conn, task_id=task_id)
        print(f"      Task found: {snap_immediate.task_found}")
        print()

        # --- FRESH CONNECTION snapshot ---
        print("[4/6] Taking FRESH CONNECTION snapshot...")
        conn2 = open_readonly_conn()
        snap_fresh = take_snapshot("FreshConn", conn=conn2, task_id=task_id)
        conn2.close()
        print(f"      Task found: {snap_fresh.task_found}")
        print()

        # --- After 500ms ---
        print("[5/6] Waiting 500ms, then snapshot...")
        time.sleep(0.5)
        snap_500ms = take_snapshot("After500ms", conn=conn, task_id=task_id)
        print(f"      Task found: {snap_500ms.task_found}")
        print()

        # --- After 2s ---
        print("[6/6] Waiting 2s more, then snapshot...")
        time.sleep(2.0)
        # Also open a second fresh connection for this
        conn3 = open_readonly_conn()
        snap_2s = take_snapshot("After2s", conn=conn3, task_id=task_id)
        conn3.close()
        print(f"      Task found: {snap_2s.task_found}")
        print()

        # --- Report ---
        snaps = [
            snap_before,
            snap_immediate,
            snap_fresh,
            snap_500ms,
            snap_2s,
        ]

        print()
        print("COMPREHENSIVE RESULTS")
        print("=====================")
        print()
        print("Each approach is shown with values at 5 points:")
        print("  Before | Immediate (same conn) | Fresh conn | +500ms | +2s")

        reliable = []
        unreliable = []

        for name, attrs, desc in APPROACHES:
            changes = print_approach_table(name, attrs, desc, snaps)
            any_approach_changed = any(changes)
            if any_approach_changed:
                reliable.append(name)
            else:
                unreliable.append(name)

        # --- Connection comparison detail ---
        print(f"\n{'=' * 72}")
        print("  EXTRA: Connection comparison detail")
        print(f"{'=' * 72}")
        print()
        print(f"  data_version (same conn, before):  {snap_before.data_version}")
        print(f"  data_version (same conn, after):   {snap_immediate.data_version}")
        print(f"  data_version (fresh conn):         {snap_fresh.data_version}")
        print(f"  data_version (same, +500ms):       {snap_500ms.data_version}")
        print(f"  data_version (fresh, +2s):         {snap_2s.data_version}")
        print()

        # --- Timing detail ---
        print(f"{'=' * 72}")
        print("  TIMING")
        print(f"{'=' * 72}")
        elapsed_immediate = snap_immediate.timestamp_mono - snap_before.timestamp_mono
        elapsed_fresh = snap_fresh.timestamp_mono - snap_before.timestamp_mono
        elapsed_500 = snap_500ms.timestamp_mono - snap_before.timestamp_mono
        elapsed_2s = snap_2s.timestamp_mono - snap_before.timestamp_mono
        print(f"  Bridge response: {bridge_elapsed:.3f}s")
        print(f"  Immediate snap:  {elapsed_immediate:.3f}s after before")
        print(f"  Fresh conn snap: {elapsed_fresh:.3f}s after before")
        print(f"  500ms snap:      {elapsed_500:.3f}s after before")
        print(f"  2s snap:         {elapsed_2s:.3f}s after before")
        print()

        # --- Summary ---
        print()
        print("SUMMARY")
        print("=======")
        print()
        print("Reliable freshness indicators (detected change):")
        if reliable:
            for r in reliable:
                print(f"  [OK] {r}")
        else:
            print("  (none)")
        print()
        print("Unreliable/unchanged indicators (did NOT detect change):")
        if unreliable:
            for u in unreliable:
                print(f"  [--] {u}")
        else:
            print("  (none)")
        print()

    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Cleanup: delete the test task
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

        # Clean up IPC files
        req_path = IPC_DIR / REQUEST_FILE
        req_path.unlink(missing_ok=True)

        # Close persistent connection
        with contextlib.suppress(Exception):
            conn.close()


if __name__ == "__main__":
    main()
