"""UAT script -- run manually against real OmniFocus SQLite. NOT for automated testing.

Validates HybridRepository against the real OmniFocus SQLite database.
Read-only only -- no writes, no modifications.

This script follows SAFE-01/SAFE-02: never imported by tests, never run in CI.

Usage:
    uv run python uat/test_sqlite_reader.py
"""

from __future__ import annotations

import asyncio
import sys

from omnifocus_operator.repository.hybrid import HybridRepository


async def main() -> int:
    """Validate HybridRepository against the real OmniFocus SQLite database."""
    print("=== OmniFocus SQLite Reader UAT ===")
    print()

    repo = HybridRepository()
    db_path = repo._db_path
    print(f"Database: {db_path}")
    print()

    try:
        data = await repo.get_all()
    except Exception as exc:
        print(f"ERROR: Failed to read database: {exc}")
        print()
        print("Troubleshooting:")
        print("  - Does the OmniFocus SQLite database exist at the path above?")
        print("  - Is OmniFocus installed?")
        return 1

    # Entity counts
    print("Entity counts:")
    print(f"  Tasks:        {len(data.tasks)}")
    print(f"  Projects:     {len(data.projects)}")
    print(f"  Tags:         {len(data.tags)}")
    print(f"  Folders:      {len(data.folders)}")
    print(f"  Perspectives: {len(data.perspectives)}")
    print()

    checks_passed = 0
    checks_total = 0

    def check(name: str, passed: bool, detail: str = "") -> None:
        nonlocal checks_passed, checks_total
        checks_total += 1
        status = "PASS" if passed else "FAIL"
        if passed:
            checks_passed += 1
        suffix = f"  {detail}" if detail else ""
        print(f"  [{status}] {name}{suffix}")

    print("Validations:")

    # 1. All tasks have urgency + availability
    tasks_missing_status = [t.id for t in data.tasks if not t.urgency or not t.availability]
    check(
        "All tasks have urgency + availability",
        len(tasks_missing_status) == 0,
        f"{len(tasks_missing_status)} tasks missing" if tasks_missing_status else "",
    )

    # 2. All projects have urgency + availability
    projects_missing_status = [p.id for p in data.projects if not p.urgency or not p.availability]
    check(
        "All projects have urgency + availability",
        len(projects_missing_status) == 0,
        f"{len(projects_missing_status)} projects missing" if projects_missing_status else "",
    )

    # 3. Timestamps in valid range (2001-2030)
    min_year = 2001
    max_year = 2030
    bad_timestamps = 0
    for task in data.tasks:
        for dt in [task.added, task.modified]:
            if dt is not None and (dt.year < min_year or dt.year > max_year):
                bad_timestamps += 1
    for proj in data.projects:
        for dt in [proj.added, proj.modified]:
            if dt is not None and (dt.year < min_year or dt.year > max_year):
                bad_timestamps += 1
    check(
        f"Timestamps in valid range ({min_year}-{max_year})",
        bad_timestamps == 0,
        f"{bad_timestamps} out-of-range timestamps" if bad_timestamps else "",
    )

    # 4. Tag associations
    tasks_with_tags = sum(1 for t in data.tasks if len(t.tags) > 0)
    check(
        f"{tasks_with_tags} tasks have tag associations",
        tasks_with_tags > 0,
    )

    # 5. All perspectives have names
    empty_name_perspectives = [p.id for p in data.perspectives if not p.name]
    check(
        "All perspectives have names",
        len(empty_name_perspectives) == 0,
        f"{len(empty_name_perspectives)} without names" if empty_name_perspectives else "",
    )

    # 6. Projects have review dates
    projects_without_review = [p.id for p in data.projects if p.last_review_date is None]
    check(
        "All projects have review dates",
        len(projects_without_review) == 0,
        f"{len(projects_without_review)} without lastReviewDate" if projects_without_review else "",
    )

    # 7. No crashes on full dataset (already passed if we got here)
    check("No crashes on full dataset", True)

    print()
    print(f"=== UAT COMPLETE: {checks_passed}/{checks_total} checks passed ===")

    return 0 if checks_passed == checks_total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
