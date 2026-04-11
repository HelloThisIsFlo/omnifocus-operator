#!/usr/bin/env python3
"""Discovery script for UAT composite suite setup.

Queries the OmniFocus SQLite cache directly to find entities matching
profile specs. Returns compact JSON (~2KB) instead of a full get_all
dump (~50-100KB), dramatically reducing context window usage during
composite UAT setup.

Standalone — uses only stdlib modules, no project imports.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import plistlib
import sqlite3
import sys
from collections import Counter
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CF_EPOCH = datetime(2001, 1, 1, tzinfo=UTC)
_GM_PREFIX = "\U0001f9ea GM-"  # 🧪 GM-

_DEFAULT_DB_PATH = os.path.expanduser(
    "~/Library/Group Containers/34YW5XSRB7.com.omnigroup.OmniFocus"
    "/com.omnigroup.OmniFocus4/com.omnigroup.OmniFocusModel"
    "/OmniFocusDatabase.db"
)

# ---------------------------------------------------------------------------
# Timezone
# ---------------------------------------------------------------------------


def _get_local_tz() -> ZoneInfo:
    tz_path = pathlib.Path("/etc/localtime").resolve()
    tz_name = str(tz_path).split("zoneinfo/")[-1]
    return ZoneInfo(tz_name)


_LOCAL_TZ = _get_local_tz()

# ---------------------------------------------------------------------------
# SQL queries (mirrors hybrid.py)
# ---------------------------------------------------------------------------

_PROJECTS_SQL = """
SELECT t.*, pi.lastReviewDate, pi.nextReviewDate,
       pi.reviewRepetitionString, pi.nextTask, pi.folder,
       pi.effectiveStatus
FROM Task t
JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task
"""

_TAGS_SQL = "SELECT * FROM Context"

_FOLDERS_SQL = "SELECT * FROM Folder"

_PERSPECTIVES_SQL = "SELECT * FROM Perspective"

# ---------------------------------------------------------------------------
# Timestamp parsing (mirrors hybrid.py)
# ---------------------------------------------------------------------------


def _parse_cf_timestamp(value: float | str | None) -> str | None:
    """CF epoch float → UTC ISO 8601."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return (_CF_EPOCH + timedelta(seconds=value)).isoformat()
    if isinstance(value, str):
        try:
            return (_CF_EPOCH + timedelta(seconds=float(value))).isoformat()
        except ValueError:
            return value
    return None


def _parse_local_datetime(value: str | None) -> str | None:
    """Naive local ISO string → UTC ISO 8601."""
    if value is None:
        return None
    naive = datetime.fromisoformat(value)
    local_dt = naive.replace(tzinfo=_LOCAL_TZ)
    return local_dt.astimezone(UTC).isoformat()


# ---------------------------------------------------------------------------
# Availability mapping (mirrors hybrid.py)
# ---------------------------------------------------------------------------


def _project_availability(row: sqlite3.Row) -> str:
    if row["dateHidden"] is not None:
        return "dropped"
    if row["effectiveStatus"] == "dropped":
        return "dropped"
    if row["dateCompleted"] is not None:
        return "completed"
    if row["effectiveStatus"] == "inactive":
        return "blocked"
    return "available"


def _tag_availability(row: sqlite3.Row) -> str:
    if row["dateHidden"] is not None:
        return "dropped"
    if not row["allowsNextAction"]:
        return "blocked"
    return "available"


def _folder_availability(row: sqlite3.Row) -> str:
    if row["dateHidden"] is not None:
        return "dropped"
    return "available"


# ---------------------------------------------------------------------------
# Entity loaders (cached per connection)
# ---------------------------------------------------------------------------


class _EntityCache:
    """Lazily loads and caches entity lists from SQLite."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._projects: list[dict] | None = None
        self._tags: list[dict] | None = None
        self._folders: list[dict] | None = None
        self._perspectives: list[dict] | None = None
        self._folder_names: dict[str, str] | None = None

    def _get_folder_names(self) -> dict[str, str]:
        if self._folder_names is None:
            rows = self._conn.execute(_FOLDERS_SQL).fetchall()
            self._folder_names = {r["persistentIdentifier"]: r["name"] for r in rows}
        return self._folder_names

    def projects(self) -> list[dict]:
        if self._projects is not None:
            return self._projects
        folder_names = self._get_folder_names()
        rows = self._conn.execute(_PROJECTS_SQL).fetchall()
        result = []
        for r in rows:
            folder_id = r["folder"]
            result.append(
                {
                    "id": r["persistentIdentifier"],
                    "name": r["name"],
                    "availability": _project_availability(r),
                    "flagged": bool(r["flagged"]),
                    "dueDate": _parse_local_datetime(r["dateDue"]),
                    "deferDate": _parse_local_datetime(r["dateToStart"]),
                    "plannedDate": _parse_local_datetime(r["datePlanned"]),
                    "folderId": folder_id,
                    "folderName": folder_names.get(folder_id, "") if folder_id else None,
                    "nextReviewDate": _parse_cf_timestamp(r["nextReviewDate"]),
                }
            )
        self._projects = result
        return result

    def tags(self) -> list[dict]:
        if self._tags is not None:
            return self._tags
        rows = self._conn.execute(_TAGS_SQL).fetchall()
        entities = []
        for r in rows:
            entities.append(
                {
                    "id": r["persistentIdentifier"],
                    "name": r["name"],
                    "availability": _tag_availability(r),
                }
            )
        # Compute name_count for ambiguity detection
        name_counts = Counter(e["name"] for e in entities)
        for e in entities:
            e["name_count"] = name_counts[e["name"]]
        self._tags = entities
        return entities

    def folders(self) -> list[dict]:
        if self._folders is not None:
            return self._folders
        rows = self._conn.execute(_FOLDERS_SQL).fetchall()
        entities = []
        for r in rows:
            entities.append(
                {
                    "id": r["persistentIdentifier"],
                    "name": r["name"],
                    "availability": _folder_availability(r),
                    "parentId": r["parent"],
                }
            )
        # Compute child_count
        parent_counts = Counter(e["parentId"] for e in entities if e["parentId"])
        for e in entities:
            e["child_count"] = parent_counts.get(e["id"], 0)
        self._folders = entities
        return entities

    def perspectives(self) -> list[dict]:
        if self._perspectives is not None:
            return self._perspectives
        rows = self._conn.execute(_PERSPECTIVES_SQL).fetchall()
        result = []
        for r in rows:
            value_data = r["valueData"]
            if not value_data:
                continue
            try:
                plist = plistlib.loads(value_data)
            except (plistlib.InvalidFileException, ValueError):
                continue
            name = plist.get("name", "")
            if not name:
                continue
            result.append(
                {
                    "id": r["persistentIdentifier"],
                    "name": name,
                }
            )
        self._perspectives = result
        return result


# ---------------------------------------------------------------------------
# Filter matching
# ---------------------------------------------------------------------------

_REVIEW_SOON_DAYS = 14


def _matches_filters(entity: dict, entity_type: str, filters: list[str]) -> bool:
    """Return True if entity passes ALL filters."""
    now = datetime.now(UTC)
    for f in filters:
        if not _check_one_filter(entity, entity_type, f, now):
            return False
    return True


def _check_one_filter(entity: dict, entity_type: str, filt: str, now: datetime) -> bool:
    if entity_type == "project":
        return _check_project_filter(entity, filt, now)
    if entity_type == "tag":
        return _check_tag_filter(entity, filt)
    if entity_type == "folder":
        return _check_folder_filter(entity, filt)
    # perspective has no filters
    return True


def _check_project_filter(p: dict, filt: str, now: datetime) -> bool:
    match filt:
        case "active":
            return p["availability"] == "available"
        case "completed":
            return p["availability"] == "completed"
        case "dropped":
            return p["availability"] == "dropped"
        case "blocked":
            return p["availability"] == "blocked"
        case "has_due":
            return p["dueDate"] is not None
        case "no_due":
            return p["dueDate"] is None
        case "has_defer":
            return p["deferDate"] is not None
        case "no_defer":
            return p["deferDate"] is None
        case "has_planned":
            return p["plannedDate"] is not None
        case "no_planned":
            return p["plannedDate"] is None
        case "flagged":
            return p["flagged"] is True
        case "not_flagged":
            return p["flagged"] is False
        case "in_folder":
            return p["folderId"] is not None
        case "review_soon":
            nrd = p.get("nextReviewDate")
            if nrd is None:
                return False
            review_dt = datetime.fromisoformat(nrd)
            return (review_dt - now).days <= _REVIEW_SOON_DAYS
        case _:
            print(f"Warning: unknown project filter '{filt}'", file=sys.stderr)
            return True


def _check_tag_filter(t: dict, filt: str) -> bool:
    match filt:
        case "available":
            return t["availability"] == "available"
        case "blocked":
            return t["availability"] == "blocked"
        case "dropped":
            return t["availability"] == "dropped"
        case "not_dropped":
            return t["availability"] != "dropped"
        case "unambiguous":
            return t.get("name_count", 1) == 1
        case _:
            print(f"Warning: unknown tag filter '{filt}'", file=sys.stderr)
            return True


def _check_folder_filter(f: dict, filt: str) -> bool:
    match filt:
        case "available":
            return f["availability"] == "available"
        case "dropped":
            return f["availability"] == "dropped"
        case "has_parent":
            return f["parentId"] is not None
        case "has_children":
            return f.get("child_count", 0) > 0
        case _:
            print(f"Warning: unknown folder filter '{filt}'", file=sys.stderr)
            return True


# ---------------------------------------------------------------------------
# Sort: GM- prefixed first, then alphabetical
# ---------------------------------------------------------------------------


def _sort_key(entity: dict) -> tuple[int, str]:
    name = entity.get("name", "")
    gm_first = 0 if name.startswith(_GM_PREFIX) else 1
    return (gm_first, name.lower())


# ---------------------------------------------------------------------------
# Output field stripping (remove internal-only fields)
# ---------------------------------------------------------------------------

_INTERNAL_FIELDS = {"name_count", "child_count"}


def _strip_internal(entity: dict) -> dict:
    return {k: v for k, v in entity.items() if k not in _INTERNAL_FIELDS}


# ---------------------------------------------------------------------------
# Spec parsing
# ---------------------------------------------------------------------------


def _parse_need_spec(spec: str) -> dict:
    """Parse TYPE:LABEL[:COUNT]:FILTER[,FILTER,...] → dict."""
    parts = spec.split(":")
    if len(parts) < 2:
        print(f"Error: --need spec must have at least TYPE:LABEL, got '{spec}'", file=sys.stderr)
        sys.exit(2)

    entity_type = parts[0]
    label = parts[1]

    if entity_type not in ("project", "tag", "folder", "perspective"):
        print(f"Error: unknown entity type '{entity_type}' in --need '{spec}'", file=sys.stderr)
        sys.exit(2)

    # Remaining parts: optional count, then filters
    rest = parts[2:]
    count = 1
    filters: list[str] = []

    if rest:
        # If first remaining part is all digits, it's the count
        if rest[0].isdigit():
            count = int(rest[0])
            rest = rest[1:]
        # Remaining parts are filter groups (colon-separated, comma-separated within)
        for part in rest:
            filters.extend(f.strip() for f in part.split(",") if f.strip())

    return {
        "type": entity_type,
        "label": label,
        "count": count,
        "filters": filters,
    }


def _parse_count_spec(spec: str) -> dict:
    """Parse LABEL:TYPE[:FILTER[,FILTER,...]] → dict."""
    parts = spec.split(":")
    if len(parts) < 2:
        print(f"Error: --count spec must have at least LABEL:TYPE, got '{spec}'", file=sys.stderr)
        sys.exit(2)

    label = parts[0]
    entity_type = parts[1]

    if entity_type not in ("project", "tag", "folder", "perspective"):
        print(f"Error: unknown entity type '{entity_type}' in --count '{spec}'", file=sys.stderr)
        sys.exit(2)

    filters: list[str] = []
    for part in parts[2:]:
        filters.extend(f.strip() for f in part.split(",") if f.strip())

    return {
        "type": entity_type,
        "label": label,
        "filters": filters,
    }


# ---------------------------------------------------------------------------
# Resolvers
# ---------------------------------------------------------------------------


def _resolve_profiles(
    needs: list[dict], cache: _EntityCache
) -> tuple[dict[str, list[dict] | None], list[str]]:
    """Resolve --need specs. Returns (profiles, unmatched)."""
    profiles: dict[str, list[dict] | None] = {}
    unmatched: list[str] = []

    for need in needs:
        entity_type = need["type"]
        label = need["label"]
        count = need["count"]
        filters = need["filters"]

        loader = {
            "project": cache.projects,
            "tag": cache.tags,
            "folder": cache.folders,
            "perspective": cache.perspectives,
        }[entity_type]

        entities = loader()
        matched = [e for e in entities if _matches_filters(e, entity_type, filters)]
        matched.sort(key=_sort_key)

        if matched:
            profiles[label] = [_strip_internal(e) for e in matched[:count]]
        else:
            profiles[label] = None
            unmatched.append(label)

    return profiles, unmatched


def _resolve_counts(counts: list[dict], cache: _EntityCache) -> dict[str, int]:
    """Resolve --count specs."""
    result: dict[str, int] = {}

    for spec in counts:
        entity_type = spec["type"]
        label = spec["label"]
        filters = spec["filters"]

        loader = {
            "project": cache.projects,
            "tag": cache.tags,
            "folder": cache.folders,
            "perspective": cache.perspectives,
        }[entity_type]

        entities = loader()
        matched = [e for e in entities if _matches_filters(e, entity_type, filters)]
        result[label] = len(matched)

    return result


def _resolve_ambiguous(types: list[str], cache: _EntityCache) -> dict[str, list[dict]]:
    """Resolve --find-ambiguous specs."""
    result: dict[str, list[dict]] = {}

    for entity_type in types:
        if entity_type == "tags":
            tags = cache.tags()
            name_counts = Counter(t["name"] for t in tags)
            dupes = []
            for name, cnt in name_counts.items():
                if cnt >= 2:
                    ids = [t["id"] for t in tags if t["name"] == name]
                    dupes.append({"name": name, "count": cnt, "ids": ids})
            if dupes:
                result["tags"] = sorted(dupes, key=lambda d: d["name"])

        elif entity_type in ("projects", "folders"):
            loader = cache.projects if entity_type == "projects" else cache.folders
            entities = loader()
            names = [e["name"] for e in entities]
            # Substring overlap: name A is substring of name B (A != B)
            overlaps: dict[str, list[str]] = {}
            for i, a in enumerate(names):
                for j, b in enumerate(names):
                    if i != j and a in b:
                        shorter = a if len(a) <= len(b) else b
                        if shorter not in overlaps:
                            overlaps[shorter] = []
                        longer = b if shorter == a else a
                        if longer not in overlaps[shorter]:
                            overlaps[shorter].append(longer)
            if overlaps:
                entries = []
                for short_name, long_names in sorted(overlaps.items()):
                    ids = [
                        e["id"]
                        for e in entities
                        if e["name"] == short_name or e["name"] in long_names
                    ]
                    all_names = [short_name, *long_names]
                    entries.append(
                        {
                            "name": short_name,
                            "overlaps_with": long_names,
                            "ids": ids,
                            "all_names": all_names,
                        }
                    )
                result[entity_type] = entries

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover OmniFocus entities for UAT setup")
    parser.add_argument(
        "--need",
        action="append",
        default=[],
        metavar="SPEC",
        help="TYPE:LABEL[:COUNT]:FILTER[,FILTER,...] — find entities matching profile",
    )
    parser.add_argument(
        "--count",
        action="append",
        default=[],
        metavar="SPEC",
        help="LABEL:TYPE[:FILTER,...] — count matching entities",
    )
    parser.add_argument(
        "--find-ambiguous",
        default=None,
        metavar="TYPES",
        help="TYPE[,TYPE,...] — detect ambiguous names",
    )
    parser.add_argument("--db", default=None, metavar="PATH", help="Override database path")
    args = parser.parse_args()

    db_path = args.db or _DEFAULT_DB_PATH
    if not os.path.exists(db_path):
        json.dump({"error": f"Database not found: {db_path}"}, sys.stdout, indent=2)
        print()
        sys.exit(1)

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        cache = _EntityCache(conn)
        output: dict = {}

        # Resolve --need
        if args.need:
            need_specs = [_parse_need_spec(s) for s in args.need]
            profiles, unmatched = _resolve_profiles(need_specs, cache)
            output["profiles"] = profiles
            if unmatched:
                output["unmatched"] = unmatched

        # Resolve --count
        if args.count:
            count_specs = [_parse_count_spec(s) for s in args.count]
            output["counts"] = _resolve_counts(count_specs, cache)

        # Resolve --find-ambiguous
        if args.find_ambiguous:
            amb_types = [t.strip() for t in args.find_ambiguous.split(",")]
            ambiguous = _resolve_ambiguous(amb_types, cache)
            if ambiguous:
                output["ambiguous"] = ambiguous

        json.dump(output, sys.stdout, indent=2)
        print()

    finally:
        conn.close()


if __name__ == "__main__":
    main()
