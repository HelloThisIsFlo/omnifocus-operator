#!/usr/bin/env python3
"""
Decode the TaskToTag.rankInTask binary encoding scheme.

rankInTask is a TEXT column storing raw bytes — not human-readable strings.
This script decodes the fractional-indexing scheme OmniFocus uses to order
tags displayed on a task.

Key questions:
  1. What encoding scheme does rankInTask use?
  2. Is byte-level comparison sufficient for correct sort order?
  3. How are insertions (reordering tags) encoded?
  4. What would generating a new rankInTask value require?

Usage:
    python3 rankintask_decoding.py

All access is read-only (?mode=ro). No mutations.

FINDINGS (2026-03-31):
  - Byte-level fractional indexing scheme:
    - Sequential tags get 2-byte values: 0x0001, 0x0002, 0x0003, ...
    - Insertions between neighbors get a 3rd midpoint byte:
      between 0x0003 and 0x0004 -> 0x00033F (63 ≈ midpoint of [0, 255])
    - Byte comparison (ORDER BY rankInTask) = correct sort order
  - Length distribution: 82% are 2 bytes (sequential), 18% are 3 bytes (insertions)
  - Older/reorganized data uses wider initial spacing (e.g. 0x9788, 0xE8AC)
  - For future writes: find neighbor bytes, compute midpoint. Same algorithm
    as integer rank, just in byte space. If no room (adjacent bytes), add a
    3rd byte at midpoint.
"""

from __future__ import annotations

import os
import sqlite3
from collections import defaultdict

DB_PATH = os.path.expanduser(
    "~/Library/Group Containers/34YW5XSRB7.com.omnigroup.OmniFocus"
    "/com.omnigroup.OmniFocus4/com.omnigroup.OmniFocusModel"
    "/OmniFocusDatabase.db"
)


def connect() -> sqlite3.Connection:
    uri = f"file:{DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def section(title: str) -> None:
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def to_bytes(val: str | bytes) -> bytes:
    """Convert rankInTask value to raw bytes."""
    if isinstance(val, bytes):
        return val
    return val.encode("latin-1")


def main() -> None:
    conn = connect()

    # ══════════════════════════════════════════════════════════════════
    #  1. Length distribution
    # ══════════════════════════════════════════════════════════════════

    section("1. rankInTask length distribution")

    total = conn.execute(
        "SELECT COUNT(*) FROM TaskToTag"
    ).fetchone()[0]

    null_count = conn.execute(
        "SELECT COUNT(*) FROM TaskToTag WHERE rankInTask IS NULL"
    ).fetchone()[0]

    lengths = conn.execute(
        "SELECT LENGTH(rankInTask) as len, COUNT(*) as cnt "
        "FROM TaskToTag "
        "WHERE rankInTask IS NOT NULL AND rankInTask != '' "
        "GROUP BY len ORDER BY len"
    ).fetchall()

    print(f"Total TaskToTag rows: {total}")
    print(f"NULL rankInTask:      {null_count}")
    print()
    non_null = sum(r["cnt"] for r in lengths)
    for r in lengths:
        pct = r["cnt"] / non_null * 100
        print(f"  {r['len']} bytes: {r['cnt']:>5} rows ({pct:.1f}%)")

    # ══════════════════════════════════════════════════════════════════
    #  2. Sequential pattern detection
    # ══════════════════════════════════════════════════════════════════

    section("2. Sequential 2-byte values (most common pattern)")

    # Get all 2-byte values
    two_byte = conn.execute(
        "SELECT rankInTask, COUNT(*) as cnt "
        "FROM TaskToTag "
        "WHERE LENGTH(rankInTask) = 2 "
        "GROUP BY rankInTask ORDER BY rankInTask LIMIT 20"
    ).fetchall()

    print("Most common 2-byte values (first 20 unique, sorted):")
    for r in two_byte:
        raw = to_bytes(r["rankInTask"])
        print(f"  hex={raw.hex()} bytes={list(raw)} "
              f"(int={int.from_bytes(raw, 'big')}) count={r['cnt']}")

    # ══════════════════════════════════════════════════════════════════
    #  3. Insertion pattern: 3-byte values as midpoints
    # ══════════════════════════════════════════════════════════════════

    section("3. Three-byte values (insertion midpoints)")

    three_byte = conn.execute(
        "SELECT rankInTask, COUNT(*) as cnt "
        "FROM TaskToTag "
        "WHERE LENGTH(rankInTask) = 3 "
        "GROUP BY rankInTask ORDER BY rankInTask LIMIT 20"
    ).fetchall()

    print("Most common 3-byte values (first 20 unique, sorted):")
    for r in three_byte:
        raw = to_bytes(r["rankInTask"])
        prefix_2 = raw[:2]
        midpoint_byte = raw[2]
        print(f"  hex={raw.hex()} bytes={list(raw)} "
              f"— prefix={prefix_2.hex()} + midpoint byte={midpoint_byte} "
              f"(~{midpoint_byte/255*100:.0f}% between neighbors)")

    # ══════════════════════════════════════════════════════════════════
    #  4. Proof: insertions are midpoints between neighbors
    # ══════════════════════════════════════════════════════════════════

    section("4. Proof: 3-byte values sit between 2-byte neighbors")

    # Find tasks where we can see the insertion pattern
    multi_tag = conn.execute(
        "SELECT task, COUNT(*) as cnt "
        "FROM TaskToTag "
        "WHERE rankInTask IS NOT NULL "
        "GROUP BY task HAVING cnt >= 4 "
        "ORDER BY cnt DESC LIMIT 5"
    ).fetchall()

    for m in multi_tag:
        tags = conn.execute(
            "SELECT tt.rankInTask, c.name as tag_name "
            "FROM TaskToTag tt "
            "JOIN Context c ON tt.tag = c.persistentIdentifier "
            "WHERE tt.task = ? "
            "ORDER BY tt.rankInTask",
            (m["task"],),
        ).fetchall()

        has_3byte = any(len(to_bytes(t["rankInTask"])) == 3 for t in tags)
        if not has_3byte:
            continue

        print(f"Task with {m['cnt']} tags (showing insertion):")
        for t in tags:
            raw = to_bytes(t["rankInTask"])
            marker = " <-- INSERTED" if len(raw) == 3 else ""
            print(f"  hex={raw.hex():>8} bytes={str(list(raw)):>12} "
                  f"  tag=\"{t['tag_name']}\"{marker}")
        print()

    # ══════════════════════════════════════════════════════════════════
    #  5. Byte comparison correctness
    # ══════════════════════════════════════════════════════════════════

    section("5. Byte comparison produces correct sort order")

    print("Verification: does ORDER BY rankInTask (byte comparison)")
    print("produce the same order as explicit integer decoding?")
    print()

    # Pick a task with mixed 2-byte and 3-byte values
    test_task = None
    for m in multi_tag:
        tags = conn.execute(
            "SELECT rankInTask FROM TaskToTag WHERE task = ? "
            "AND rankInTask IS NOT NULL",
            (m["task"],),
        ).fetchall()
        if any(len(to_bytes(t["rankInTask"])) == 3 for t in tags):
            test_task = m["task"]
            break

    if test_task:
        tags = conn.execute(
            "SELECT rankInTask FROM TaskToTag "
            "WHERE task = ? AND rankInTask IS NOT NULL "
            "ORDER BY rankInTask",
            (test_task,),
        ).fetchall()

        byte_order = [to_bytes(t["rankInTask"]) for t in tags]
        int_order = sorted(byte_order, key=lambda b: int.from_bytes(b.ljust(3, b'\x00'), 'big'))

        match = byte_order == int_order
        print(f"  Byte sort == integer sort: {'PASS' if match else 'FAIL'}")
        print(f"  Byte order:    {[b.hex() for b in byte_order]}")
        print(f"  Integer order: {[b.hex() for b in int_order]}")

    # ══════════════════════════════════════════════════════════════════
    #  6. Writing algorithm (for future reference)
    # ══════════════════════════════════════════════════════════════════

    section("6. How to generate a new rankInTask (future writes)")

    print("""
    Algorithm (byte-level fractional indexing):

    1. APPEND (new last tag):
       - Find max existing rankInTask for the task
       - If 2 bytes [a, b]: new = [a, b+1] (or [a+1, 0] on overflow)
       - If 3 bytes [a, b, c]: new = [a, b+1] (round up to next 2-byte)

    2. INSERT between neighbors [a, b] and [c, d]:
       - If b+1 < d (same first byte, room between):
         new = [a, (b+d)//2]  — 2-byte midpoint
       - If no room in 2 bytes:
         new = [a, b, 127]    — 3-byte, midpoint byte ~0x7F
       - General: find first differing byte position, insert midpoint

    3. PREPEND (new first tag):
       - Find min existing rankInTask
       - If [0, n] with n > 1: new = [0, n//2]
       - If [0, 1]: new = [0, 0, 127] (3-byte)

    This is the standard fractional-indexing pattern (same as Figma,
    Google Docs, etc.) applied at byte granularity.
    """)

    # ══════════════════════════════════════════════════════════════════
    #  7. rankInTag: confirm it's dead
    # ══════════════════════════════════════════════════════════════════

    section("7. rankInTag: confirm effectively unused")

    rit_stats = conn.execute(
        "SELECT "
        "  COUNT(*) as total, "
        "  SUM(CASE WHEN rankInTag IS NULL THEN 1 ELSE 0 END) as null_cnt, "
        "  SUM(CASE WHEN rankInTag IS NOT NULL THEN 1 ELSE 0 END) as non_null "
        "FROM TaskToTag"
    ).fetchone()

    print(f"Total rows:        {rit_stats['total']}")
    print(f"rankInTag NULL:    {rit_stats['null_cnt']} "
          f"({rit_stats['null_cnt']/rit_stats['total']*100:.1f}%)")
    print(f"rankInTag non-NULL: {rit_stats['non_null']}")

    if rit_stats["non_null"] > 0:
        samples = conn.execute(
            "SELECT rankInTag FROM TaskToTag "
            "WHERE rankInTag IS NOT NULL LIMIT 5"
        ).fetchall()
        print("\nNon-NULL samples:")
        for s in samples:
            raw = to_bytes(s["rankInTag"])
            print(f"  hex={raw.hex()} bytes={list(raw)}")

    print("\nVerdict: rankInTag is effectively dead — OmniFocus does not")
    print("persist custom task ordering within tag views.")

    conn.close()
    print("\n✅ rankInTask decoding complete. All queries read-only.")


if __name__ == "__main__":
    main()
