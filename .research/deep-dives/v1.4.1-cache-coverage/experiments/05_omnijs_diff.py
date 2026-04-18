"""Experiment 05 — OmniJS ↔ SQLite per-row diff.

Compares the OmniJS cross-check output (from ``omnijs-crosscheck.js``)
against the SQLite cache for the same persistentIdentifiers. Confirms
per-row identity between bridge and cache.

Usage (three equivalent paths):

1. **Pipe from clipboard** (macOS one-liner):

       pbpaste | uv run python 05_omnijs_diff.py

2. **From a file** (reproducible across runs):

       uv run python 05_omnijs_diff.py path/to/omnijs-output.json

   Default file path: ``omnijs-output.json`` next to this script.

3. **Paste into a committed file** then run:

       # save OmniJS console output as omnijs-output.json here, then:
       uv run python 05_omnijs_diff.py

If nothing is piped, no argument is given, and no ``omnijs-output.json``
exists, the script prints instructions and exits cleanly.

The OmniJS script logs its JSON between ``=== v1.4.1 cache-coverage
OmniJS cross-check ===`` banners — the JSON array between those lines is
what this script expects. Extra banner lines are tolerated; the loader
pulls out the first well-formed JSON array it finds.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from pathlib import Path

DB_PATH = os.path.expanduser(
    "~/Library/Group Containers/34YW5XSRB7.com.omnigroup.OmniFocus"
    "/com.omnigroup.OmniFocus4/com.omnigroup.OmniFocusModel"
    "/OmniFocusDatabase.db"
)

SCRIPT_DIR = Path(__file__).parent
DEFAULT_INPUT = SCRIPT_DIR / "omnijs-output.json"

REQUIRED_KEYS = {"id", "completedByChildren", "sequential", "hasAttachments"}

_INSTRUCTIONS = f"""
No OmniJS output provided.

How to supply it:

  1. Run omnijs-crosscheck.js in OmniFocus → Automation → Show Console.
  2. Copy the JSON array (between the '=== ===' banners).
  3. Either:
     a. Pipe directly:   pbpaste | uv run python {Path(__file__).name}
     b. Save as a file:  save to '{DEFAULT_INPUT.name}' next to this script,
                         then run it with no arguments.
     c. Explicit path:   uv run python {Path(__file__).name} <path-to-json>
"""


def _extract_json_array(raw: str) -> list[dict]:
    """Pull the first well-formed JSON array out of ``raw``.

    Tolerates banner lines, leading/trailing prose, trailing newlines.
    """
    stripped = raw.strip()
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"(\[[\s\S]*\])", raw)
        if match is None:
            raise
        value = json.loads(match.group(1))
    if not isinstance(value, list):
        msg = f"expected a JSON array, got {type(value).__name__}"
        raise ValueError(msg)
    return value


def _validate_rows(rows: list[dict]) -> list[dict]:
    bad = [i for i, row in enumerate(rows) if not REQUIRED_KEYS.issubset(row)]
    if bad:
        msg = f"rows at indices {bad} missing required keys {sorted(REQUIRED_KEYS)}"
        raise ValueError(msg)
    return rows


def _load_omnijs_rows(argv: list[str]) -> list[dict]:
    """Resolve input from (in order): CLI arg → stdin pipe → default file."""
    # 1. CLI arg — explicit path
    if len(argv) > 1:
        path = Path(argv[1])
        if not path.exists():
            print(f"ABORT: file not found: {path}")
            sys.exit(1)
        return _validate_rows(_extract_json_array(path.read_text()))

    # 2. Piped stdin
    if not sys.stdin.isatty():
        data = sys.stdin.read()
        if data.strip():
            return _validate_rows(_extract_json_array(data))

    # 3. Default file
    if DEFAULT_INPUT.exists():
        return _validate_rows(_extract_json_array(DEFAULT_INPUT.read_text()))

    # 4. Nothing provided — print instructions and exit cleanly.
    print(_INSTRUCTIONS)
    sys.exit(0)


def main() -> None:
    if not os.path.exists(DB_PATH):
        print(f"ABORT: OmniFocus SQLite cache not found at {DB_PATH}")
        sys.exit(1)

    omnijs_rows = _load_omnijs_rows(sys.argv)

    uri = f"file:{DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row

    try:
        print("=" * 96)
        print(f"OMNIJS ↔ SQLITE PER-ROW DIFF  ({len(omnijs_rows)} rows)")
        print("=" * 96)
        print(f"{'id':<14} {'field':<20} {'omnijs':<10} {'sqlite':<10} {'match':<7}  note")
        print("-" * 96)

        matches = 0
        mismatches: list[str] = []
        missing: list[str] = []
        total_checks = 0

        for row in omnijs_rows:
            rid = row["id"]
            sql_row = conn.execute(
                "SELECT completeWhenChildrenComplete AS cwcc, sequential AS seq "
                "FROM Task WHERE persistentIdentifier = ?",
                (rid,),
            ).fetchone()
            if sql_row is None:
                missing.append(rid)
                print(f"{rid:<14} {'(row missing)':<20}")
                continue

            has_att_row = conn.execute(
                "SELECT EXISTS(SELECT 1 FROM Attachment WHERE task = ?) AS has",
                (rid,),
            ).fetchone()
            sql_has = bool(has_att_row["has"])

            fields = [
                (
                    "completedByChildren",
                    row["completedByChildren"],
                    bool(sql_row["cwcc"]),
                    sql_row["cwcc"],
                ),
                ("sequential", row["sequential"], bool(sql_row["seq"]), sql_row["seq"]),
                ("hasAttachments", row["hasAttachments"], sql_has, 1 if sql_has else 0),
            ]
            for name, oj, sq, raw in fields:
                total_checks += 1
                ok = oj == sq
                if ok:
                    matches += 1
                else:
                    mismatches.append(f"{rid}/{name}: OmniJS={oj} SQLite={sq}")
                marker = "✓" if ok else "✗"
                raw_note = f"raw={raw}" if name != "hasAttachments" else ""
                print(f"{rid:<14} {name:<20} {oj!s:<10} {sq!s:<10} {marker:<7}  {raw_note}")

        print()
        print("=" * 96)
        print("SUMMARY")
        print("=" * 96)
        print(f"  rows compared : {len(omnijs_rows) - len(missing)}")
        print(f"  missing rows  : {len(missing)} {missing}")
        print(f"  total checks  : {total_checks}")
        print(f"  matches       : {matches}")
        print(f"  mismatches    : {len(mismatches)}")
        for m in mismatches:
            print(f"    • {m}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
