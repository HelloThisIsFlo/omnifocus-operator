#!/usr/bin/env python3
"""
Validate that rank values across all OmniFocus entity tables fit within
signed 32-bit range, confirming the sort_path CTE's printf('%010d', rank + 2147483648)
is safe from overflow.

Key questions:
  1. Do any rank values exceed signed 32-bit [-2147483648, 2147483647]?
  2. Does the shifted value (rank + 2147483648) fit in 10 zero-padded digits?
  3. Could SQLite's flexible INTEGER typing allow 64-bit values to sneak in?

Usage:
    python3 rank_range_validation.py

All access is read-only (?mode=ro). No mutations.

FINDINGS (2026-03-31):
  - All three tables (Task, Folder, Context) fit comfortably in signed 32-bit
  - Task:    [-2,140,575,383 .. 2,147,483,638]  shifted max = 4,294,967,286 (10 digits)
  - Folder:  [-2,143,888,531 .. 2,118,123,520]  shifted max = 4,265,607,168 (10 digits)
  - Context: [-1,610,612,736 .. 2,147,483,167]  shifted max = 4,294,966,815 (10 digits)
  - Max possible unsigned 32-bit = 4,294,967,295 = exactly 10 digits
  - Schema declares `rank integer NOT NULL` — SQLite could store 64-bit, but
    OmniFocus uses midpoint insertion with 65536 gaps, clearly a 32-bit scheme
  - VERDICT: printf('%010d', rank + 2147483648) is safe. No overflow risk.
"""

from __future__ import annotations

import os
import sqlite3

DB_PATH = os.path.expanduser(
    "~/Library/Group Containers/34YW5XSRB7.com.omnigroup.OmniFocus"
    "/com.omnigroup.OmniFocus4/com.omnigroup.OmniFocusModel"
    "/OmniFocusDatabase.db"
)

SIGNED_32_MIN = -2_147_483_648
SIGNED_32_MAX = 2_147_483_647
UNSIGNED_32_MAX = 4_294_967_295  # = 2^32 - 1, exactly 10 digits


def connect() -> sqlite3.Connection:
    uri = f"file:{DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def section(title: str) -> None:
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def main() -> None:
    conn = connect()

    section("1. Rank range per entity table")

    tables = ["Task", "Folder", "Context"]
    all_fit = True

    for table in tables:
        row = conn.execute(
            f"SELECT MIN(rank) as mn, MAX(rank) as mx, COUNT(*) as cnt "
            f"FROM {table}"
        ).fetchone()
        mn, mx, cnt = row["mn"], row["mx"], row["cnt"]

        fits_signed_32 = mn >= SIGNED_32_MIN and mx <= SIGNED_32_MAX
        shifted_min = mn + 2_147_483_648
        shifted_max = mx + 2_147_483_648
        shifted_digits = len(str(shifted_max))

        print(f"{table} ({cnt} rows):")
        print(f"  Raw range:     [{mn:>14,} .. {mx:>14,}]")
        print(f"  Signed 32-bit: {'PASS' if fits_signed_32 else 'FAIL'}")
        print(f"  Shifted range: [{shifted_min:>14,} .. {shifted_max:>14,}]")
        print(f"  Shifted digits: {shifted_digits} (need <= 10)")
        print(f"  Fits %%010d:    {'PASS' if shifted_digits <= 10 else 'FAIL'}")
        print()

        if not fits_signed_32 or shifted_digits > 10:
            all_fit = False

    section("2. Schema declarations")

    for table in tables:
        schema = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        for line in schema["sql"].split(","):
            if "rank" in line.lower():
                print(f"  {table}: {line.strip()}")

    print()
    print("  SQLite INTEGER type is flexible (1-8 bytes), but OmniFocus")
    print("  uses midpoint insertion with 65536 gaps — a 32-bit scheme.")

    section("3. Boundary check: closest values to 32-bit limits")

    # How close is the max rank to the 32-bit ceiling?
    for table in tables:
        row = conn.execute(
            f"SELECT MAX(rank) as mx FROM {table}"
        ).fetchone()
        headroom = SIGNED_32_MAX - row["mx"]
        print(f"  {table}: max rank headroom = {headroom:,} "
              f"({headroom / 65536:.0f} insertion slots)")

    section("4. Verdict")

    if all_fit:
        print("  PASS: All rank values fit in signed 32-bit.")
        print(f"  printf('%010d', rank + 2147483648) is safe.")
        print(f"  Max unsigned 32-bit = {UNSIGNED_32_MAX:,} = {len(str(UNSIGNED_32_MAX))} digits.")
        print()
        print("  The 32-bit assumption is safe for current data AND by design:")
        print("  OmniFocus uses a midpoint-insertion scheme with 65536 gaps,")
        print("  which is a standard 32-bit fractional indexing pattern.")
    else:
        print("  FAIL: Some rank values exceed 32-bit range!")
        print("  The sort_path CTE needs wider printf formatting.")

    conn.close()
    print("\n✅ Rank range validation complete. All queries read-only.")


if __name__ == "__main__":
    main()
