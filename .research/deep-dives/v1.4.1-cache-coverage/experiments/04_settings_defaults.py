"""Experiment 04 — Are user defaults (OFMCompleteWhenLastItemComplete,
OFMTaskDefaultSequential) in the SQLite cache, or only available via
OmniJS settings API?

The spec notes these are needed server-side as create-time defaults when
the agent omits `completedByChildren` / `sequential` on add_task. If they
live in the cache, the server can read them cheaply. If not, a one-time
OmniJS call at server startup is required.
"""

from __future__ import annotations

import os
import plistlib
import sqlite3
import sys

DB_PATH = os.path.expanduser(
    "~/Library/Group Containers/34YW5XSRB7.com.omnigroup.OmniFocus"
    "/com.omnigroup.OmniFocus4/com.omnigroup.OmniFocusModel"
    "/OmniFocusDatabase.db"
)


def probe_settings() -> None:
    if not os.path.exists(DB_PATH):
        print(f"ABORT: OmniFocus SQLite cache not found at {DB_PATH}")
        sys.exit(1)

    uri = f"file:{DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row

    try:
        # Schema of the Setting table
        print("=" * 72)
        print("Setting TABLE — schema")
        print("=" * 72)
        for r in conn.execute("PRAGMA table_info(Setting)"):
            nullable = "NULL" if r["notnull"] == 0 else "NOT NULL"
            print(f"  {r['name']:<30} {r['type']:<15} {nullable}")

        # Row count
        total = conn.execute("SELECT COUNT(*) AS n FROM Setting").fetchone()["n"]
        print(f"\n  total rows: {total}")

        # Dump ALL rows (likely small)
        print()
        print("=" * 72)
        print("Setting TABLE — all rows (truncating long values)")
        print("=" * 72)
        for r in conn.execute("SELECT * FROM Setting LIMIT 500"):
            d = dict(r)
            # Truncate blob/long fields for readability
            pretty = {}
            for k, v in d.items():
                if isinstance(v, (bytes, bytearray)):
                    pretty[k] = f"<bytes len={len(v)}>"
                elif isinstance(v, str) and len(v) > 80:
                    pretty[k] = v[:80] + "…"
                else:
                    pretty[k] = v
            print(f"  {pretty}")

        # Targeted search for the two keys of interest
        print()
        print("=" * 72)
        print("TARGETED SEARCH — OFM keys of interest")
        print("=" * 72)
        keys = [
            "OFMCompleteWhenLastItemComplete",
            "OFMTaskDefaultSequential",
        ]
        # Look for any column holding string values matching these keys
        # (the Setting table might use key/value columns or some other shape)
        # Get column names
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(Setting)")]
        if not cols:
            print("  (no Setting table columns — unexpected)")
            return

        # Try each text-ish column as the "key" column
        for candidate_col in cols:
            try:
                matches_total = 0
                for key in keys:
                    found = conn.execute(
                        f"SELECT * FROM Setting WHERE {candidate_col} = ?", (key,)
                    ).fetchall()
                    if found:
                        matches_total += len(found)
                        print(f"  MATCH via column '{candidate_col}' for key '{key}':")
                        for r in found:
                            pretty = {}
                            for k, v in dict(r).items():
                                if isinstance(v, (bytes, bytearray)):
                                    pretty[k] = f"<bytes len={len(v)}>"
                                elif isinstance(v, str) and len(v) > 80:
                                    pretty[k] = v[:80] + "…"
                                else:
                                    pretty[k] = v
                            print(f"    {pretty}")
                if matches_total:
                    print()
            except sqlite3.OperationalError:
                # Column doesn't support equality on string — skip
                continue

        # Substring search as fallback (in case keys are embedded in a plist blob)
        print()
        print("=" * 72)
        print("SUBSTRING SEARCH — scan all TEXT/BLOB columns for key substrings")
        print("=" * 72)
        # First, check if any blob column contains these string patterns
        for r in conn.execute("SELECT * FROM Setting LIMIT 500"):
            d = dict(r)
            for k, v in d.items():
                serialized: str | None = None
                if isinstance(v, (bytes, bytearray)):
                    try:
                        serialized = v.decode("utf-8", errors="ignore")
                    except Exception:
                        serialized = None
                elif isinstance(v, str):
                    serialized = v
                if serialized is not None:
                    for needle in keys:
                        if needle in serialized:
                            sample = serialized[
                                max(0, serialized.find(needle) - 20) : serialized.find(needle)
                                + len(needle)
                                + 40
                            ]
                            print(f"  MATCH in column '{k}' → ...{sample}...")

        # Decode valueData plist blobs for the two keys of interest (+ two
        # reference keys for decoding-pattern validation).
        print()
        print("=" * 72)
        print("DECODED VALUES — plistlib.loads(valueData)")
        print("=" * 72)
        probes = (
            "OFMCompleteWhenLastItemComplete",
            "OFMTaskDefaultSequential",
            "OFMAutomaticallyHideCompletedItems",
            "OFMRequiredRelationshipToProcessInboxItem",
        )
        for key in probes:
            row = conn.execute(
                "SELECT valueData FROM Setting WHERE persistentIdentifier = ?", (key,)
            ).fetchone()
            if row is None:
                print(f"  {key}: <NOT IN CACHE — user kept default>")
                continue
            blob = row["valueData"]
            try:
                decoded = plistlib.loads(blob)
                print(f"  {key}: {decoded!r}  (blob_len={len(blob)})")
            except Exception as exc:
                print(
                    f"  {key}: decode error {exc}  (blob_len={len(blob)})  hex={blob.hex()[:60]}…"
                )
    finally:
        conn.close()


if __name__ == "__main__":
    probe_settings()
