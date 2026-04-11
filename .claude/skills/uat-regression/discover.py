#!/usr/bin/env python3
"""Discovery script for UAT composite suite setup.

Queries the OmniFocus SQLite cache directly to find entities matching
profile specs. Returns compact JSON (~2KB) instead of a full get_all
dump (~50-100KB), dramatically reducing context window usage during
composite UAT setup.

Primary interface: --suite PATH [--suite PATH]...
  Reads YAML frontmatter from each suite file, consolidates discovery
  needs across suites, queries SQLite, and returns JSON with resolved
  entities + setup instructions per suite.

Ad-hoc interface: --need SPEC [--count SPEC] [--find-ambiguous TYPES]
  Lower-level interface for individual queries.

Standalone — uses only stdlib + yaml (pyyaml), no project imports.
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

import yaml

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
    needs: list[dict],
    cache: _EntityCache,
    distinct: bool = False,
) -> tuple[dict[str, list[dict] | None], list[str]]:
    """Resolve --need specs. Returns (profiles, unmatched).

    When distinct=True, entities already assigned to a previous need of the
    same type are excluded from subsequent picks. This ensures that e.g.
    tag-a, tag-b, tag-c resolve to three different tags.
    """
    profiles: dict[str, list[dict] | None] = {}
    unmatched: list[str] = []
    # Track assigned entity IDs per type for distinct mode
    assigned: dict[str, set[str]] = {}

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

        # In distinct mode, exclude already-assigned IDs of the same type
        if distinct:
            used = assigned.get(entity_type, set())
            matched = [e for e in matched if e["id"] not in used]

        matched.sort(key=_sort_key)

        if matched:
            picked = matched[:count]
            profiles[label] = [_strip_internal(e) for e in picked]
            if distinct:
                if entity_type not in assigned:
                    assigned[entity_type] = set()
                for e in picked:
                    assigned[entity_type].add(e["id"])
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


def _resolve_ambiguous(
    types: list[str], cache: _EntityCache, caps: dict[str, int] | None = None
) -> dict[str, list[dict]]:
    """Resolve --find-ambiguous specs.

    Args:
        caps: optional per-type max results, e.g. {"tags": 3, "projects": 3}.
              Default cap is 3 when called from --suite mode.
    """
    result: dict[str, list[dict]] = {}
    caps = caps or {}

    for entity_type in types:
        if entity_type == "tags":
            tags = cache.tags()
            # Filter empty names to avoid spurious matches
            name_counts = Counter(t["name"] for t in tags if t["name"])
            dupes = []
            for name, cnt in name_counts.items():
                if cnt >= 2:
                    ids = [t["id"] for t in tags if t["name"] == name]
                    dupes.append({"name": name, "count": cnt, "ids": ids})
            if dupes:
                sorted_dupes = sorted(dupes, key=lambda d: d["name"])
                cap = caps.get("tags", 0)
                result["tags"] = sorted_dupes[:cap] if cap else sorted_dupes

        elif entity_type in ("projects", "folders"):
            loader = cache.projects if entity_type == "projects" else cache.folders
            entities = loader()
            # Filter empty names
            names = [e["name"] for e in entities if e["name"]]
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
                cap = caps.get(entity_type, 0)
                result[entity_type] = entries[:cap] if cap else entries

    return result


# ---------------------------------------------------------------------------
# Suite mode: YAML frontmatter parsing and consolidation
# ---------------------------------------------------------------------------


def _parse_frontmatter(path: str) -> dict:
    """Read a suite file and extract YAML frontmatter between --- markers."""
    with open(path) as f:
        content = f.read()

    if not content.startswith("---"):
        return {}

    end = content.find("\n---", 3)
    if end == -1:
        return {}

    yaml_text = content[4:end]  # skip opening "---\n"
    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        print(f"Warning: failed to parse YAML in {path}: {e}", file=sys.stderr)
        return {}

    return data if isinstance(data, dict) else {}


def _consolidate_suites(
    frontmatters: dict[str, dict],
) -> tuple[list[dict], list[dict], dict[str, int]]:
    """Merge discovery blocks across suites.

    Returns (consolidated_needs, consolidated_counts, ambiguous_caps).
    Deduplicates by label — first occurrence wins.
    """
    seen_need_labels: set[str] = set()
    needs: list[dict] = []

    seen_count_labels: set[str] = set()
    counts: list[dict] = []

    # Ambiguous caps: merge max across suites per type
    ambiguous_caps: dict[str, int] = {}

    for fm in frontmatters.values():
        discovery = fm.get("discovery")
        if not discovery:
            continue

        for need in discovery.get("needs", []):
            label = need["label"]
            if label not in seen_need_labels:
                seen_need_labels.add(label)
                needs.append(
                    {
                        "type": need["type"],
                        "label": label,
                        "count": need.get("count", 1),
                        "filters": need.get("filters", []),
                    }
                )

        for count_spec in discovery.get("counts", []):
            label = count_spec["label"]
            if label not in seen_count_labels:
                seen_count_labels.add(label)
                counts.append(
                    {
                        "type": count_spec["type"],
                        "label": label,
                        "filters": count_spec.get("filters", []),
                    }
                )

        amb = discovery.get("ambiguous", {})
        for amb_type, cap in amb.items():
            current = ambiguous_caps.get(amb_type, 0)
            ambiguous_caps[amb_type] = max(current, cap)

    return needs, counts, ambiguous_caps


def _slim_profile(entity: dict) -> dict:
    """Strip entity to {id, name} only for compact output."""
    return {"id": entity["id"], "name": entity["name"]}


def _run_suite_mode(suite_paths: list[str], cache: _EntityCache) -> dict:
    """Execute suite-driven discovery and return consolidated output."""
    # Parse all frontmatters
    frontmatters: dict[str, dict] = {}
    for path in suite_paths:
        if not os.path.exists(path):
            print(f"Error: suite file not found: {path}", file=sys.stderr)
            sys.exit(2)
        fm = _parse_frontmatter(path)
        slug = fm.get("suite", os.path.basename(path).replace(".md", ""))
        frontmatters[slug] = fm

    # Consolidate discovery specs
    needs, counts, ambiguous_caps = _consolidate_suites(frontmatters)

    # Resolve needs → slim profiles
    all_profiles: dict[str, dict | None] = {}
    unmatched: list[str] = []
    if needs:
        raw_profiles, unmatched = _resolve_profiles(needs, cache, distinct=True)
        for label, entities in raw_profiles.items():
            if entities is None:
                all_profiles[label] = None
            elif len(entities) == 1:
                all_profiles[label] = _slim_profile(entities[0])
            else:
                all_profiles[label] = [_slim_profile(e) for e in entities]

    # Resolve counts
    all_counts: dict[str, int] = {}
    if counts:
        all_counts = _resolve_counts(counts, cache)

    # Resolve ambiguous
    all_ambiguous: dict[str, list[dict]] = {}
    if ambiguous_caps:
        # Map cap keys to plural type names for _resolve_ambiguous
        amb_type_map = {"tags": "tags", "projects": "projects", "folders": "folders"}
        amb_types = [amb_type_map[k] for k in ambiguous_caps if k in amb_type_map]
        if amb_types:
            all_ambiguous = _resolve_ambiguous(amb_types, cache, ambiguous_caps)

    # Build per-suite output
    suites_output: dict[str, dict] = {}
    for slug, fm in frontmatters.items():
        # Collect entity labels this suite needs
        discovery = fm.get("discovery", {})
        suite_labels = [n["label"] for n in discovery.get("needs", [])]

        suite_entities: dict[str, dict | list | None] = {}
        for label in suite_labels:
            if label in all_profiles:
                suite_entities[label] = all_profiles[label]

        suites_output[slug] = {
            "display": fm.get("display", slug),
            "test_count": fm.get("test_count", 0),
            "entities": suite_entities,
            "setup": fm.get("setup", ""),
            "computed_values": fm.get("computed_values", {}),
            "user_prompts": fm.get("user_prompts", []),
            "manual_actions": fm.get("manual_actions", []),
        }

    # Build final output
    output: dict = {"suites": suites_output}
    if all_counts:
        output["counts"] = all_counts
    if all_ambiguous:
        output["ambiguous"] = all_ambiguous
    if unmatched:
        output["unmatched"] = unmatched

    return output


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover OmniFocus entities for UAT setup")
    parser.add_argument(
        "--suite",
        action="append",
        default=[],
        metavar="PATH",
        help="Suite file path — reads YAML frontmatter for discovery specs",
    )
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

    # Validate mutual exclusivity
    has_suite = bool(args.suite)
    has_adhoc = bool(args.need or args.count or args.find_ambiguous)
    if has_suite and has_adhoc:
        print(
            "Error: --suite is mutually exclusive with --need/--count/--find-ambiguous",
            file=sys.stderr,
        )
        sys.exit(2)

    db_path = args.db or _DEFAULT_DB_PATH
    if not os.path.exists(db_path):
        json.dump({"error": f"Database not found: {db_path}"}, sys.stdout)
        print()
        sys.exit(1)

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        cache = _EntityCache(conn)

        if has_suite:
            # Suite mode: compact output (no indent)
            output = _run_suite_mode(args.suite, cache)
            json.dump(output, sys.stdout)
            print()
        else:
            # Ad-hoc mode: readable output (indent=2)
            output: dict = {}

            if args.need:
                need_specs = [_parse_need_spec(s) for s in args.need]
                profiles, unmatched = _resolve_profiles(need_specs, cache)
                output["profiles"] = profiles
                if unmatched:
                    output["unmatched"] = unmatched

            if args.count:
                count_specs = [_parse_count_spec(s) for s in args.count]
                output["counts"] = _resolve_counts(count_specs, cache)

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
