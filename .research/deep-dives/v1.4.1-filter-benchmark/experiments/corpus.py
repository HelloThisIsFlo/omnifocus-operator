"""Synthetic task corpus builder for the filter benchmark.

Builds an in-memory SQLite database with a minimal subset of the OmniFocus
Task schema — enough columns to run the parent-subtree + tag + date filters.
Schema matches column names in production ``HybridRepository`` so the SQL
prototype query shape is representative.

Tree shape is OmniFocus-leaf-biased: ~80% of tasks are leaves, ~15% have
1-5 children, ~5% have nested grandchildren. Projects are Task rows plus
a ProjectInfo row (same pattern as production). Tags are N:M via TaskToTag.
"""

from __future__ import annotations

import random
import sqlite3
import time
from dataclasses import dataclass

_CF_EPOCH_OFFSET = 700_000_000.0  # approx 2023 in CF-epoch seconds


@dataclass(frozen=True)
class CorpusStats:
    total_tasks: int  # includes project rows
    pure_tasks: int  # excludes project rows
    projects: int
    tags: int
    task_tag_edges: int
    max_depth: int
    target_parent_id: str
    target_subtree_size: int


def _gen_id(seed: random.Random, prefix: str = "t") -> str:
    # Mirror OmniFocus-style short IDs (alphanum ~12 chars)
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
    return prefix + "".join(seed.choices(alphabet, k=11))


def build_corpus(
    pure_task_count: int,
    *,
    project_count: int | None = None,
    tag_count: int = 25,
    tag_coverage: float = 0.2,  # fraction of tasks with at least one tag
    seed: int = 42,
) -> tuple[sqlite3.Connection, CorpusStats]:
    """Build an in-memory SQLite DB with the given task count.

    Returns (conn, stats). The target_parent_id in stats is a mid-tree task
    with a realistic subtree (50-500 descendants) — use this as the filter
    argument in benchmarks so scenarios are comparable across scales.
    """
    rng = random.Random(seed)
    if project_count is None:
        project_count = max(5, pure_task_count // 50)
    project_count = min(project_count, max(5, pure_task_count // 10))

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _create_schema(conn)

    cursor = conn.cursor()

    # --- Projects ---
    project_ids: list[str] = []
    for _ in range(project_count):
        pid = _gen_id(rng, prefix="p")
        project_ids.append(pid)
        _insert_task_row(
            cursor,
            persistent_id=pid,
            parent=None,
            containing_project_info=None,  # projects themselves
            name=f"Project {pid[-6:]}",
            rng=rng,
            is_project=True,
        )
        cursor.execute("INSERT INTO ProjectInfo(pk, task) VALUES (?, ?)", (pid, pid))

    # --- Tasks distributed across projects in a leaf-biased tree ---
    # Plan: for each project, generate a chunk of tasks that forms a tree.
    # 80% leaves, 15% nodes with children, 5% with grandchildren.
    tasks_per_project = pure_task_count // project_count
    remainder = pure_task_count - tasks_per_project * project_count

    all_task_ids: list[str] = []
    task_depths: dict[str, int] = {}
    max_depth = 0

    for idx, proj_id in enumerate(project_ids):
        n = tasks_per_project + (1 if idx < remainder else 0)
        if n <= 0:
            continue
        chunk_ids, chunk_depth = _generate_task_tree(cursor, proj_id, n, rng)
        all_task_ids.extend(chunk_ids)
        for tid, d in chunk_depth.items():
            task_depths[tid] = d
            max_depth = max(max_depth, d)

    # --- Tags ---
    tag_ids: list[str] = [_gen_id(rng, prefix="g") for _ in range(tag_count)]
    for tid in tag_ids:
        cursor.execute(
            "INSERT INTO Context(persistentIdentifier, name, allowsNextAction) VALUES (?, ?, 1)",
            (tid, f"Tag {tid[-4:]}"),
        )

    # Assign tags to a subset of tasks
    tagged_count = int(len(all_task_ids) * tag_coverage)
    tagged_tasks = rng.sample(all_task_ids, tagged_count)
    edges = 0
    for task_id in tagged_tasks:
        # 1-3 tags per tagged task
        n_tags = rng.randint(1, 3)
        picked = rng.sample(tag_ids, n_tags)
        for tag_id in picked:
            cursor.execute(
                "INSERT OR IGNORE INTO TaskToTag(task, tag) VALUES (?, ?)",
                (task_id, tag_id),
            )
            edges += 1

    conn.commit()

    # --- Pick a target parent: a task that has a realistic subtree ---
    # Heuristic: find the task with the deepest subtree roughly
    # proportional to total corpus size — we want ~1-5% of tasks as the
    # subtree so the benchmark has meaningful filtering to do.
    target_parent, subtree_size = _pick_target_parent(cursor, all_task_ids, rng)

    stats = CorpusStats(
        total_tasks=len(all_task_ids) + project_count,
        pure_tasks=len(all_task_ids),
        projects=project_count,
        tags=tag_count,
        task_tag_edges=edges,
        max_depth=max_depth,
        target_parent_id=target_parent,
        target_subtree_size=subtree_size,
    )
    return conn, stats


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE Task (
            persistentIdentifier TEXT PRIMARY KEY,
            parent TEXT,
            containingProjectInfo TEXT,
            name TEXT,
            effectiveFlagged INTEGER NOT NULL DEFAULT 0,
            blocked INTEGER NOT NULL DEFAULT 0,
            dateAdded REAL NOT NULL,
            dateModified REAL NOT NULL,
            dateCompleted REAL,
            dateHidden REAL,
            effectiveDateDue REAL,
            effectiveDateCompleted REAL,
            effectiveDateHidden REAL,
            completeWhenChildrenComplete INTEGER NOT NULL DEFAULT 0,
            sequential INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX Task_parent ON Task(parent);
        CREATE INDEX Task_containingProjectInfo ON Task(containingProjectInfo);

        CREATE TABLE ProjectInfo (
            pk TEXT PRIMARY KEY,
            task TEXT NOT NULL
        );
        CREATE INDEX ProjectInfo_task ON ProjectInfo(task);

        CREATE TABLE Context (
            persistentIdentifier TEXT PRIMARY KEY,
            name TEXT,
            allowsNextAction INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE TaskToTag (
            task TEXT NOT NULL,
            tag TEXT NOT NULL,
            PRIMARY KEY (task, tag)
        );
        CREATE INDEX TaskToTag_tag ON TaskToTag(tag);
        """
    )


def _insert_task_row(
    cursor: sqlite3.Cursor,
    *,
    persistent_id: str,
    parent: str | None,
    containing_project_info: str | None,
    name: str,
    rng: random.Random,
    is_project: bool = False,
) -> None:
    # Date fields: CF-epoch seconds, plausible range 2023-2025
    now = _CF_EPOCH_OFFSET + rng.uniform(0, 100_000_000)
    modified = now + rng.uniform(0, 50_000_000)
    # 15% of tasks have a due date
    due = now + rng.uniform(0, 30_000_000) if rng.random() < 0.15 else None
    # 5% completed, 2% dropped
    completed = now + rng.uniform(0, 10_000_000) if rng.random() < 0.05 else None
    dropped = (
        now + rng.uniform(0, 10_000_000) if (rng.random() < 0.02 and completed is None) else None
    )
    flagged = 1 if rng.random() < 0.1 else 0
    blocked = 1 if rng.random() < 0.2 else 0

    cursor.execute(
        """
        INSERT INTO Task(
            persistentIdentifier, parent, containingProjectInfo, name,
            effectiveFlagged, blocked,
            dateAdded, dateModified, dateCompleted, dateHidden,
            effectiveDateDue, effectiveDateCompleted, effectiveDateHidden,
            completeWhenChildrenComplete, sequential
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            persistent_id,
            parent,
            containing_project_info,
            name,
            flagged,
            blocked,
            now,
            modified,
            completed,
            dropped,
            due,
            completed,
            dropped,
            1 if rng.random() < 0.6 else 0,
            1 if rng.random() < 0.1 else 0,
        ),
    )


def _generate_task_tree(
    cursor: sqlite3.Cursor,
    project_id: str,
    n_tasks: int,
    rng: random.Random,
) -> tuple[list[str], dict[str, int]]:
    """Generate n_tasks with a leaf-biased tree shape under a project.

    Distribution target:
    - 80% leaves (no children)
    - 15% level-1 parents (1-5 direct children)
    - 5% level-2+ parents (nested grandchildren)

    Returns (list_of_task_ids, depth_by_id).
    """
    created: list[str] = []
    depths: dict[str, int] = {}
    remaining = n_tasks

    # Step 1: create roots under the project (depth 1)
    # Aim for ~20% of tasks to be roots; rest will be children
    n_roots = max(1, min(remaining, int(n_tasks * 0.2)))
    roots: list[str] = []
    for _ in range(n_roots):
        if remaining <= 0:
            break
        tid = _gen_id(rng, prefix="t")
        _insert_task_row(
            cursor,
            persistent_id=tid,
            parent=None,
            containing_project_info=project_id,
            name=f"Task {tid[-5:]}",
            rng=rng,
        )
        created.append(tid)
        depths[tid] = 1
        roots.append(tid)
        remaining -= 1

    # Step 2: distribute remaining as children of roots / existing nodes
    # Favor depth-1 nodes; some go to depth 2, very few to depth 3+
    candidate_parents = roots[:]
    while remaining > 0 and candidate_parents:
        parent_id = rng.choice(candidate_parents)
        parent_depth = depths[parent_id]
        # 70% chance this stays a leaf after adding child; 30% chance child
        # itself becomes a candidate (nested tree)
        n_children = min(remaining, rng.randint(1, 4))
        for _ in range(n_children):
            if remaining <= 0:
                break
            tid = _gen_id(rng, prefix="t")
            _insert_task_row(
                cursor,
                persistent_id=tid,
                parent=parent_id,
                containing_project_info=project_id,
                name=f"Task {tid[-5:]}",
                rng=rng,
            )
            created.append(tid)
            depths[tid] = parent_depth + 1
            remaining -= 1
            # Decay candidate promotion with depth so we don't go too deep
            if rng.random() < 0.3 and parent_depth + 1 <= 4:
                candidate_parents.append(tid)

        # Stop promoting this parent after it's had children so we don't
        # make it overly wide
        if rng.random() < 0.5:
            candidate_parents.remove(parent_id)

    return created, depths


def _pick_target_parent(
    cursor: sqlite3.Cursor,
    all_task_ids: list[str],
    rng: random.Random,
) -> tuple[str, int]:
    """Pick a task whose subtree is ~1-5% of the corpus — realistic filter."""
    target_lo = max(20, len(all_task_ids) // 200)  # ~0.5% of corpus
    target_hi = max(target_lo + 50, len(all_task_ids) // 20)  # ~5% of corpus

    # Sample up to 30 candidate parent tasks, count their subtree sizes, pick
    # the one closest to target_hi without exceeding it
    sample_pool = rng.sample(all_task_ids, min(50, len(all_task_ids)))
    best_id = sample_pool[0]
    best_size = 0
    for candidate in sample_pool:
        size = _count_subtree_size(cursor, candidate)
        if target_lo <= size <= target_hi and size > best_size:
            best_id = candidate
            best_size = size
    if best_size == 0:
        # Fallback: pick the largest subtree we saw
        for candidate in sample_pool:
            size = _count_subtree_size(cursor, candidate)
            if size > best_size:
                best_id = candidate
                best_size = size
    return best_id, best_size


def _count_subtree_size(cursor: sqlite3.Cursor, root_id: str) -> int:
    row = cursor.execute(
        """
        WITH RECURSIVE sub(id) AS (
            SELECT ?
            UNION ALL
            SELECT t.persistentIdentifier FROM Task t JOIN sub ON t.parent = sub.id
        )
        SELECT COUNT(*) AS n FROM sub
        """,
        (root_id,),
    ).fetchone()
    return int(row["n"])


if __name__ == "__main__":
    # Quick smoke test at 1K scale
    start = time.perf_counter()
    conn, stats = build_corpus(1000)
    elapsed = time.perf_counter() - start
    print(f"Built corpus in {elapsed * 1000:.0f}ms: {stats}")
    conn.close()
