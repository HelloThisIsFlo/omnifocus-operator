#!/usr/bin/env python3
"""
Phase 3: Projects, Folders, Tags ordering — rank semantics for non-task entities.

Key questions:
  1. Projects: ordered by rank within their folder? What about folder-less projects?
  2. Folders: ordered by rank within parent folder?
  3. Tags (Context table): ordered by rank within parent tag?
  4. TaskToTag: rankInTask (TEXT!) — what format? Does it control tag display order?

Usage:
    python3 entity_ordering.py

All access is read-only (?mode=ro). No mutations.

FINDINGS (2026-03-31):
  - Folders (80): rank unique within parent, zero duplicates. Same midpoint scheme as tasks.
  - Projects (363 active): rank unique within folder (including NULL folder group)
  - Tags (76): rank unique within parent tag, zero duplicates
  - All three entity types use identical rank semantics as tasks
  - TaskToTag.rankInTask: binary-encoded bytes in TEXT column (e.g. \\x00\\x04)
    Controls tag display order on a task. Byte-level comparison = correct sort.
  - TaskToTag.rankInTag: effectively dead — NULL for 5001/5007 rows
    OmniFocus doesn't persist custom task ordering per tag view.
"""

from __future__ import annotations

import os
import sqlite3

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


def main() -> None:
    conn = connect()

    # ══════════════════════════════════════════════════════════════════
    #  FOLDERS
    # ══════════════════════════════════════════════════════════════════

    section("1. Folder rank analysis")

    # Stats
    stats = conn.execute(
        "SELECT COUNT(*) as cnt, MIN(rank) as min_r, MAX(rank) as max_r, "
        "COUNT(DISTINCT rank) as distinct_r FROM Folder"
    ).fetchone()
    print(f"Total folders:  {stats['cnt']}")
    print(f"Rank range:     {stats['min_r']} .. {stats['max_r']}")
    print(f"Distinct ranks: {stats['distinct_r']}")

    # Top-level folders (parent IS NULL) ordered by rank
    top_folders = conn.execute(
        "SELECT persistentIdentifier, name, rank FROM Folder "
        "WHERE parent IS NULL ORDER BY rank"
    ).fetchall()

    print(f"\nTop-level folders (parent IS NULL), ordered by rank:")
    for f in top_folders:
        print(f"  rank={f['rank']:>10}  {f['name']}")

    # Within-parent uniqueness
    folder_dupes = conn.execute(
        "SELECT parent, rank, COUNT(*) as cnt FROM Folder "
        "GROUP BY parent, rank HAVING cnt > 1"
    ).fetchall()
    print(f"\nWithin-parent rank duplicates: {len(folder_dupes)}")

    # Nested folders sample
    nested = conn.execute(
        "SELECT f.persistentIdentifier, f.name, f.rank, f.parent, "
        "       p.name as parent_name "
        "FROM Folder f LEFT JOIN Folder p ON f.parent = p.persistentIdentifier "
        "WHERE f.parent IS NOT NULL ORDER BY f.parent, f.rank LIMIT 10"
    ).fetchall()

    if nested:
        print("\nNested folders (sample, ordered by parent + rank):")
        current_parent = None
        for f in nested:
            if f["parent"] != current_parent:
                current_parent = f["parent"]
                print(f"\n  Under '{f['parent_name'] or '[ANON]'}':")
            print(f"    rank={f['rank']:>10}  {f['name']}")

    # ══════════════════════════════════════════════════════════════════
    #  PROJECTS (Task + ProjectInfo)
    # ══════════════════════════════════════════════════════════════════

    section("2. Project rank analysis")

    # Projects ordered by folder, then rank
    projects = conn.execute(
        "SELECT t.persistentIdentifier, t.name, t.rank, pi.folder, "
        "       f.name as folder_name "
        "FROM Task t "
        "JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task "
        "LEFT JOIN Folder f ON pi.folder = f.persistentIdentifier "
        "WHERE t.dateCompleted IS NULL AND t.dateHidden IS NULL "
        "ORDER BY pi.folder, t.rank"
    ).fetchall()

    print(f"Active projects: {len(projects)}")

    # Show by folder
    current_folder = "INIT"
    shown = 0
    for p in projects:
        folder_label = p["folder_name"] or "(no folder)"
        if p["folder"] != current_folder:
            current_folder = p["folder"]
            print(f"\n  Folder: {folder_label}")
            shown = 0
        if shown < 5:  # Show max 5 per folder to keep output manageable
            print(f"    rank={p['rank']:>10}  {p['name']}")
            shown += 1
        elif shown == 5:
            remaining = sum(1 for pp in projects if pp["folder"] == current_folder) - 5
            if remaining > 0:
                print(f"    ... and {remaining} more")
            shown += 1

    # Folder-less projects
    no_folder = [p for p in projects if p["folder"] is None]
    print(f"\n  Projects without folder: {len(no_folder)}")

    # Within-folder rank uniqueness
    proj_dupes = conn.execute(
        "SELECT pi.folder, t.rank, COUNT(*) as cnt "
        "FROM Task t JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task "
        "GROUP BY pi.folder, t.rank HAVING cnt > 1"
    ).fetchall()
    print(f"  Within-folder rank duplicates: {len(proj_dupes)}")

    # ══════════════════════════════════════════════════════════════════
    #  TAGS (Context table)
    # ══════════════════════════════════════════════════════════════════

    section("3. Tag (Context) rank analysis")

    stats = conn.execute(
        "SELECT COUNT(*) as cnt, MIN(rank) as min_r, MAX(rank) as max_r "
        "FROM Context"
    ).fetchone()
    print(f"Total tags:  {stats['cnt']}")
    print(f"Rank range:  {stats['min_r']} .. {stats['max_r']}")

    # Top-level tags ordered by rank
    top_tags = conn.execute(
        "SELECT persistentIdentifier, name, rank FROM Context "
        "WHERE parent IS NULL ORDER BY rank"
    ).fetchall()

    print(f"\nTop-level tags (parent IS NULL), ordered by rank:")
    for t in top_tags:
        print(f"  rank={t['rank']:>10}  {t['name']}")

    # Nested tags
    nested_tags = conn.execute(
        "SELECT c.persistentIdentifier, c.name, c.rank, c.parent, "
        "       p.name as parent_name "
        "FROM Context c LEFT JOIN Context p ON c.parent = p.persistentIdentifier "
        "WHERE c.parent IS NOT NULL ORDER BY c.parent, c.rank"
    ).fetchall()

    if nested_tags:
        print(f"\nNested tags (ordered by parent + rank):")
        current_parent = None
        for t in nested_tags:
            if t["parent"] != current_parent:
                current_parent = t["parent"]
                print(f"\n  Under '{t['parent_name']}':")
            print(f"    rank={t['rank']:>10}  {t['name']}")

    # Within-parent uniqueness
    tag_dupes = conn.execute(
        "SELECT parent, rank, COUNT(*) as cnt FROM Context "
        "GROUP BY parent, rank HAVING cnt > 1"
    ).fetchall()
    print(f"\n  Within-parent rank duplicates: {len(tag_dupes)}")

    # ══════════════════════════════════════════════════════════════════
    #  TASKTOTAG: rankInTask and rankInTag
    # ══════════════════════════════════════════════════════════════════

    section("4. TaskToTag: rankInTask and rankInTag analysis")

    # Basic stats
    stats = conn.execute(
        "SELECT COUNT(*) as cnt FROM TaskToTag"
    ).fetchone()
    print(f"Total TaskToTag rows: {stats['cnt']}")

    # rankInTask: type and value examples
    samples = conn.execute(
        "SELECT task, tag, rankInTask, rankInTag FROM TaskToTag "
        "WHERE rankInTask IS NOT NULL LIMIT 10"
    ).fetchall()

    print(f"\nrankInTask samples (TEXT column!):")
    for s in samples:
        print(f"  task={s['task'][:12]}.. tag={s['tag'][:12]}.. "
              f"rankInTask='{s['rankInTask']}' rankInTag='{s['rankInTag']}'")

    # Check if rankInTask is numeric-looking or something else
    non_numeric = conn.execute(
        "SELECT rankInTask FROM TaskToTag "
        "WHERE rankInTask IS NOT NULL AND rankInTask != '' "
        "AND CAST(rankInTask AS INTEGER) != rankInTask "
        "LIMIT 5"
    ).fetchall()

    if non_numeric:
        print(f"\n⚠️  Non-numeric rankInTask values found:")
        for r in non_numeric:
            print(f"  '{r['rankInTask']}'")
    else:
        print(f"\n✅ All non-null rankInTask values are numeric strings")

    # NULL distribution
    null_stats = conn.execute(
        "SELECT "
        "  SUM(CASE WHEN rankInTask IS NULL THEN 1 ELSE 0 END) as null_in_task, "
        "  SUM(CASE WHEN rankInTag IS NULL THEN 1 ELSE 0 END) as null_in_tag "
        "FROM TaskToTag"
    ).fetchone()
    print(f"\nNULL counts: rankInTask={null_stats['null_in_task']}, "
          f"rankInTag={null_stats['null_in_tag']}")

    # Show tags on a specific test task to verify order
    print("\nTags on test tasks (if any):")
    test_ids = [
        "eWUXvLtFUXE",  # OR-01
        "f-bTxFgMvNG",  # OR-03
    ]
    for tid in test_ids:
        tags = conn.execute(
            "SELECT tt.rankInTask, c.name as tag_name "
            "FROM TaskToTag tt JOIN Context c ON tt.tag = c.persistentIdentifier "
            "WHERE tt.task = ? ORDER BY tt.rankInTask",
            (tid,),
        ).fetchall()
        if tags:
            task_name = conn.execute(
                "SELECT name FROM Task WHERE persistentIdentifier = ?", (tid,)
            ).fetchone()["name"]
            print(f"\n  {task_name}:")
            for t in tags:
                print(f"    rankInTask='{t['rankInTask']}'  tag={t['tag_name']}")
        else:
            print(f"  Task {tid}: no tags")

    # rankInTag: does it control "tasks shown under a tag" order?
    print("\n\nrankInTag analysis (tasks-within-tag ordering):")
    # Pick a tag with multiple tasks
    busy_tag = conn.execute(
        "SELECT tag, COUNT(*) as cnt FROM TaskToTag "
        "GROUP BY tag ORDER BY cnt DESC LIMIT 1"
    ).fetchone()

    if busy_tag:
        tag_name = conn.execute(
            "SELECT name FROM Context WHERE persistentIdentifier = ?",
            (busy_tag["tag"],),
        ).fetchone()["name"]
        print(f"  Tag '{tag_name}' has {busy_tag['cnt']} tasks")

        tasks_in_tag = conn.execute(
            "SELECT tt.rankInTag, t.name, t.rank as task_rank "
            "FROM TaskToTag tt JOIN Task t ON tt.task = t.persistentIdentifier "
            "WHERE tt.tag = ? ORDER BY tt.rankInTag LIMIT 10",
            (busy_tag["tag"],),
        ).fetchall()
        print(f"  First 10 tasks ordered by rankInTag:")
        for t in tasks_in_tag:
            print(f"    rankInTag='{t['rankInTag']}'  task_rank={t['task_rank']:>10}  "
                  f"[ANON task]")

    conn.close()
    print("\n✅ Phase 3 complete. All queries read-only.")


if __name__ == "__main__":
    main()
