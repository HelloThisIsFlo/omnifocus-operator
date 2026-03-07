#!/usr/bin/env python3
"""Analyze an OmniFocus snapshot for field, boolean, enum, and emptiness coverage.

Usage:
    # Analyze a snapshot file
    python analyze_snapshot.py snapshot.json

    # Analyze with a full-database reference (for uncoverable detection)
    python analyze_snapshot.py snapshot.json --full-db full.json

    # Build a covering set from a full database dump
    python analyze_snapshot.py full.json --build-cover --output snapshot-sample-live.json

Coverage dimensions:
    - Schema: every field defined in the Pydantic model appears in the data
    - Null: at least one item with a non-null value for each field
    - Boolean: both true and false for every boolean field
    - Enum: every value (from schema + data) for every enum field
    - Empty string: both "" and non-empty for string fields that have both
    - Empty list: both [] and non-empty for list fields that have both
    - Nested objects: all of the above applied to fields inside nested dicts
    - Tag refs: every tag in tags lists has valid id and name
"""

import argparse
import json
import sys
from datetime import datetime

ENTITY_TYPES = ["tasks", "projects", "tags", "folders", "perspectives"]


def _load_known_enums() -> dict[str, dict[str, list[str]]]:
    """Import enum definitions from the actual source code.

    This avoids hardcoding values -- the script always reflects the real model.
    Falls back to an empty registry if imports fail (e.g. running outside the repo).
    Nested fields use dotted keys (e.g. "repetitionRule.scheduleType").
    """
    try:
        import importlib
        import pathlib

        src_dir = str(pathlib.Path(__file__).resolve().parents[4] / "src")
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)

        enums = importlib.import_module("omnifocus_operator.models.enums")

        def values(enum_cls):
            return [e.value for e in enum_cls]

        rep_rule_enums = {
            "repetitionRule.scheduleType": values(enums.ScheduleType),
            "repetitionRule.anchorDateKey": values(enums.AnchorDateKey),
        }

        return {
            "tasks": {
                "urgency": values(enums.Urgency),
                "availability": values(enums.Availability),
                **rep_rule_enums,
            },
            "projects": {
                "urgency": values(enums.Urgency),
                "availability": values(enums.Availability),
                **rep_rule_enums,
            },
            "tags": {
                "status": values(enums.TagStatus),
            },
            "folders": {
                "status": values(enums.FolderStatus),
            },
        }
    except Exception as e:
        print(
            f"  Warning: could not import enums from source ({e}), using data-only heuristic",
            file=sys.stderr,
        )
        return {}


def _load_expected_fields() -> dict[str, list[str]] | None:
    """Import Pydantic model classes and extract expected field names (aliases).

    Returns {entity_name: [field_alias, ...]} or None if import fails.
    Also populates EXPECTED_NESTED_FIELDS and EXPECTED_LIST_ITEM_FIELDS.
    """
    try:
        import importlib
        import pathlib

        src_dir = str(pathlib.Path(__file__).resolve().parents[4] / "src")
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)

        task_mod = importlib.import_module("omnifocus_operator.models.task")
        project_mod = importlib.import_module("omnifocus_operator.models.project")
        tag_mod = importlib.import_module("omnifocus_operator.models.tag")
        folder_mod = importlib.import_module("omnifocus_operator.models.folder")
        perspective_mod = importlib.import_module("omnifocus_operator.models.perspective")
        common_mod = importlib.import_module("omnifocus_operator.models.common")

        def field_aliases(cls):
            aliases = [fi.alias or name for name, fi in cls.model_fields.items()]
            # Include @computed_field properties (e.g. Perspective.builtin)
            if hasattr(cls, "model_computed_fields"):
                for name, cfi in cls.model_computed_fields.items():
                    aliases.append(cfi.alias or name)
            return aliases

        # Nested object field expectations: {parent_field: [expected_sub_fields]}
        global EXPECTED_NESTED_FIELDS
        EXPECTED_NESTED_FIELDS = {
            "repetitionRule": field_aliases(common_mod.RepetitionRule),
            "reviewInterval": field_aliases(common_mod.ReviewInterval),
        }

        # List-of-objects field expectations: {parent_field: [expected_sub_fields]}
        global EXPECTED_LIST_ITEM_FIELDS
        EXPECTED_LIST_ITEM_FIELDS = {
            "tags": field_aliases(common_mod.TagRef),
        }

        return {
            "tasks": field_aliases(task_mod.Task),
            "projects": field_aliases(project_mod.Project),
            "tags": field_aliases(tag_mod.Tag),
            "folders": field_aliases(folder_mod.Folder),
            "perspectives": field_aliases(perspective_mod.Perspective),
        }
    except Exception as e:
        print(
            f"  Warning: could not import models from source ({e}), skipping schema field check",
            file=sys.stderr,
        )
        return None


KNOWN_ENUMS = _load_known_enums()
EXPECTED_FIELDS = _load_expected_fields()
EXPECTED_NESTED_FIELDS: dict[str, list[str]] = getattr(
    sys.modules[__name__], "EXPECTED_NESTED_FIELDS", {}
)
EXPECTED_LIST_ITEM_FIELDS: dict[str, list[str]] = getattr(
    sys.modules[__name__], "EXPECTED_LIST_ITEM_FIELDS", {}
)


def load_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def classify_fields(items: list[dict]) -> dict:
    """Classify each field as boolean, enum, string, list, dict, or other."""
    if not items:
        return {}

    all_keys = set()
    for item in items:
        all_keys.update(item.keys())

    classification = {}
    for key in sorted(all_keys):
        values = [item.get(key) for item in items]
        non_null = [v for v in values if v is not None]

        if all(isinstance(v, bool) for v in non_null) and non_null:
            classification[key] = "boolean"
        elif all(isinstance(v, list) for v in non_null) and non_null:
            classification[key] = "list"
        elif all(isinstance(v, str) for v in non_null) and non_null:
            unique = set(non_null)
            uniqueness_ratio = len(unique) / len(non_null) if non_null else 1
            if len(unique) <= 20 and uniqueness_ratio < 0.05:
                classification[key] = "enum"
            else:
                classification[key] = "string"
        elif all(isinstance(v, dict) for v in non_null) and non_null:
            classification[key] = "dict"
        else:
            classification[key] = "other"

    return classification


def _find_nested_fields(items: list[dict], classification: dict) -> list[str]:
    """Return field names that contain nested dicts."""
    return [k for k, v in classification.items() if v == "dict"]


def _extract_sub_items(items: list[dict], field: str) -> list[dict]:
    """Extract non-null nested dicts from a field across all items."""
    return [item[field] for item in items if isinstance(item.get(field), dict)]


def _check_schema_fields(items: list[dict], entity_name: str):
    """Check that every field defined in the Pydantic model appears in the data.

    Returns (missing_fields, extra_fields, nested_issues, list_item_issues).
    """
    if EXPECTED_FIELDS is None:
        return [], [], {}, {}

    expected = EXPECTED_FIELDS.get(entity_name)
    if expected is None:
        return [], [], {}, {}

    # Collect all keys that appear in any item
    actual_keys = set()
    for item in items:
        actual_keys.update(item.keys())

    missing = [f for f in expected if f not in actual_keys]
    extra = sorted(actual_keys - set(expected))

    # Check nested object fields
    nested_issues = {}
    for parent_field, expected_sub in EXPECTED_NESTED_FIELDS.items():
        if parent_field not in actual_keys:
            continue
        sub_items = _extract_sub_items(items, parent_field)
        if not sub_items:
            continue
        sub_actual = set()
        for si in sub_items:
            sub_actual.update(si.keys())
        sub_missing = [f for f in expected_sub if f not in sub_actual]
        sub_extra = sorted(sub_actual - set(expected_sub))
        if sub_missing or sub_extra:
            nested_issues[parent_field] = {"missing": sub_missing, "extra": sub_extra}

    # Check list-of-objects fields (e.g. tags -> TagRef)
    list_item_issues = {}
    for parent_field, expected_sub in EXPECTED_LIST_ITEM_FIELDS.items():
        if parent_field not in actual_keys:
            continue
        # Collect all items from all lists
        all_list_items = []
        for item in items:
            val = item.get(parent_field)
            if isinstance(val, list):
                all_list_items.extend(v for v in val if isinstance(v, dict))
        if not all_list_items:
            continue

        sub_actual = set()
        for li in all_list_items:
            sub_actual.update(li.keys())
        sub_missing = [f for f in expected_sub if f not in sub_actual]
        sub_extra = sorted(sub_actual - set(expected_sub))

        # Also check for invalid items (missing required fields or empty values)
        invalid_items = []
        for li in all_list_items:
            for f in expected_sub:
                val = li.get(f)
                if val is None or val == "":
                    invalid_items.append(li)
                    break

        issues = {}
        if sub_missing:
            issues["missing_fields"] = sub_missing
        if sub_extra:
            issues["extra_fields"] = sub_extra
        if invalid_items:
            issues["invalid_count"] = len(invalid_items)
            issues["invalid_example"] = invalid_items[0]
        if issues:
            list_item_issues[parent_field] = issues

    return missing, extra, nested_issues, list_item_issues


def _analyze_field_coverage(
    items: list[dict],
    ref_items: list[dict],
    known_enums: dict[str, list[str]],
    field_prefix: str = "",
):
    """Core coverage analysis for a flat list of dicts.

    Returns a dict with gaps found across all dimensions.
    Used for both top-level entities and nested objects.
    """
    if not items:
        return {}

    all_keys = set()
    for item in items:
        all_keys.update(item.keys())

    classification = classify_fields(ref_items)
    result = {
        "always_null": [],
        "bool_gaps": {},
        "enum_gaps": {},
        "uncoverable_enums": {},
        "emptiness_gaps": {},
    }

    prefix = f"{field_prefix}." if field_prefix else ""

    # Null coverage
    for key in sorted(all_keys):
        if all(item.get(key) is None for item in items):
            result["always_null"].append(f"{prefix}{key}")

    # Boolean coverage
    for key in sorted(all_keys):
        if classification.get(key) != "boolean":
            continue
        vals = [item[key] for item in items if isinstance(item.get(key), bool)]
        missing = []
        if True not in vals:
            missing.append("true")
        if False not in vals:
            missing.append("false")
        if missing:
            result["bool_gaps"][f"{prefix}{key}"] = missing

    # Enum coverage
    enum_fields = set()
    for k in known_enums:
        if field_prefix:
            if k.startswith(f"{field_prefix}."):
                enum_fields.add(k[len(field_prefix) + 1 :])
        else:
            if "." not in k:
                enum_fields.add(k)
    ref_classification = classify_fields(ref_items)
    for key in all_keys:
        if ref_classification.get(key) == "enum":
            enum_fields.add(key)

    for key in sorted(enum_fields):
        full_known_key = f"{prefix}{key}" if not field_prefix else f"{field_prefix}.{key}"
        expected = set(known_enums.get(full_known_key, []))
        db_values = {item[key] for item in ref_items if item.get(key) is not None}
        expected |= db_values

        sample_values = {item[key] for item in items if item.get(key) is not None}
        missing = expected - sample_values
        if missing:
            coverable = missing & db_values
            uncoverable = missing - db_values
            if coverable:
                result["enum_gaps"][f"{prefix}{key}"] = {
                    "present": sorted(sample_values),
                    "missing": sorted(coverable),
                }
            if uncoverable:
                result["uncoverable_enums"][f"{prefix}{key}"] = sorted(uncoverable)

    # Emptiness coverage (empty string / empty list)
    for key in sorted(all_keys):
        field_type = classification.get(key)
        if field_type == "string":
            sample_has_empty = any(item.get(key) == "" for item in items)
            sample_has_pop = any(
                isinstance(item.get(key), str) and item.get(key) != "" for item in items
            )
            ref_has_empty = any(item.get(key) == "" for item in ref_items)
            ref_has_pop = any(
                isinstance(item.get(key), str) and item.get(key) != "" for item in ref_items
            )
            if ref_has_empty and ref_has_pop:
                missing = []
                if not sample_has_empty:
                    missing.append("empty")
                if not sample_has_pop:
                    missing.append("populated")
                if missing:
                    result["emptiness_gaps"][f"{prefix}{key}"] = missing

        elif field_type == "list":
            sample_has_empty = any(
                isinstance(item.get(key), list) and len(item[key]) == 0 for item in items
            )
            sample_has_pop = any(
                isinstance(item.get(key), list) and len(item[key]) > 0 for item in items
            )
            ref_has_empty = any(
                isinstance(item.get(key), list) and len(item[key]) == 0 for item in ref_items
            )
            ref_has_pop = any(
                isinstance(item.get(key), list) and len(item[key]) > 0 for item in ref_items
            )
            if ref_has_empty and ref_has_pop:
                missing = []
                if not sample_has_empty:
                    missing.append("empty")
                if not sample_has_pop:
                    missing.append("populated")
                if missing:
                    result["emptiness_gaps"][f"{prefix}{key}"] = missing

    return result


def analyze_coverage(items: list[dict], entity_name: str, full_db_items: list[dict] | None = None):
    """Analyze field coverage for a list of items."""
    if not items:
        print(f"\n{'=' * 60}")
        print(f"  {entity_name} (0 items) -- EMPTY")
        print(f"{'=' * 60}")
        return {"entity": entity_name, "count": 0, "ok": False}

    ref_items = full_db_items or items
    known = KNOWN_ENUMS.get(entity_name, {})
    issues = []

    # Schema field check
    missing_fields, extra_fields, nested_schema, list_item_issues = _check_schema_fields(
        ref_items, entity_name
    )

    # Top-level coverage
    top = _analyze_field_coverage(items, ref_items, known)

    # Nested object coverage
    classification = classify_fields(ref_items)
    nested_fields = _find_nested_fields(ref_items, classification)
    nested_results = {}
    for nf in nested_fields:
        sub_sample = _extract_sub_items(items, nf)
        sub_ref = _extract_sub_items(ref_items, nf)
        if sub_ref:
            nested_results[nf] = _analyze_field_coverage(sub_sample, sub_ref, known, nf)

    # Merge all gaps
    all_always_null = list(top["always_null"])
    all_bool_gaps = dict(top["bool_gaps"])
    all_enum_gaps = dict(top["enum_gaps"])
    all_uncoverable_enums = dict(top["uncoverable_enums"])
    all_emptiness_gaps = dict(top["emptiness_gaps"])

    for _nf, nr in nested_results.items():
        all_always_null.extend(nr["always_null"])
        all_bool_gaps.update(nr["bool_gaps"])
        all_enum_gaps.update(nr["enum_gaps"])
        all_uncoverable_enums.update(nr["uncoverable_enums"])
        all_emptiness_gaps.update(nr["emptiness_gaps"])

    # Check if null/bool gaps are uncoverable
    uncoverable_nulls = []
    coverable_nulls = []
    if full_db_items:
        for key in all_always_null:
            if "." in key:
                parent, child = key.split(".", 1)
                sub_ref = _extract_sub_items(full_db_items, parent)
                if all(item.get(child) is None for item in sub_ref):
                    uncoverable_nulls.append(key)
                else:
                    coverable_nulls.append(key)
            else:
                if all(item.get(key) is None for item in full_db_items):
                    uncoverable_nulls.append(key)
                else:
                    coverable_nulls.append(key)

        uncoverable_bools = {}
        coverable_bools = {}
        for key, missing in all_bool_gaps.items():
            if "." in key:
                parent, child = key.split(".", 1)
                full_vals = [
                    item[child]
                    for item in _extract_sub_items(full_db_items, parent)
                    if isinstance(item.get(child), bool)
                ]
            else:
                full_vals = [item[key] for item in full_db_items if isinstance(item.get(key), bool)]
            actually_missing = [v for v in missing if (v == "true") not in full_vals]
            if actually_missing:
                uncoverable_bools[key] = actually_missing
            remaining = [m for m in missing if m not in actually_missing]
            if remaining:
                coverable_bools[key] = remaining
    else:
        coverable_nulls = all_always_null
        coverable_bools = all_bool_gaps

    # Report
    ok = (
        not missing_fields
        and not list_item_issues
        and not coverable_nulls
        and not coverable_bools
        and not all_enum_gaps
        and not all_emptiness_gaps
    )
    status = "OK" if ok else "GAPS"

    print(f"\n{'=' * 60}")
    print(f"  {entity_name} ({len(items)} items) -- {status}")
    print(f"{'=' * 60}")

    has_any_notes = (
        missing_fields
        or extra_fields
        or nested_schema
        or list_item_issues
        or all_always_null
        or all_bool_gaps
        or all_enum_gaps
        or all_uncoverable_enums
        or all_emptiness_gaps
    )
    if not has_any_notes:
        print("  All fields, booleans, enums, and emptiness fully covered.")
    else:
        if missing_fields:
            print("\n  MISSING schema fields (defined in model, absent from data):")
            for f in missing_fields:
                print(f"    - {f}")
            issues.append(f"{len(missing_fields)} schema fields missing")

        if extra_fields:
            print("\n  Extra fields (in data, not in model):")
            for f in extra_fields:
                print(f"    - {f}")

        if nested_schema:
            for parent, info in nested_schema.items():
                if info["missing"]:
                    print(f"\n  MISSING nested fields in {parent}:")
                    for f in info["missing"]:
                        print(f"    - {parent}.{f}")
                    issues.append(f"{parent}: {len(info['missing'])} nested fields missing")
                if info["extra"]:
                    print(f"\n  Extra nested fields in {parent}:")
                    for f in info["extra"]:
                        print(f"    - {parent}.{f}")

        if list_item_issues:
            for parent, info in list_item_issues.items():
                if info.get("missing_fields"):
                    print(f"\n  MISSING fields in {parent} items:")
                    for f in info["missing_fields"]:
                        print(f"    - {parent}[].{f}")
                    issues.append(f"{parent} items: fields missing")
                if info.get("extra_fields"):
                    print(f"\n  Extra fields in {parent} items:")
                    for f in info["extra_fields"]:
                        print(f"    - {parent}[].{f}")
                if info.get("invalid_count"):
                    print(
                        f"\n  INVALID {parent} items: {info['invalid_count']} items "
                        f"with null/empty required fields"
                    )
                    print(f"    example: {json.dumps(info['invalid_example'])}")
                    issues.append(f"{info['invalid_count']} invalid {parent} items")

        if uncoverable_nulls:
            print("\n  Uncoverable nulls (not in DB at all):")
            for key in uncoverable_nulls:
                print(f"    - {key}")

        if coverable_nulls:
            print("\n  MISSED null coverage (exists in DB, not in sample):")
            for key in coverable_nulls:
                print(f"    - {key}")
            issues.append(f"{len(coverable_nulls)} null fields missed")

        if full_db_items and uncoverable_bools:
            print("\n  Uncoverable booleans (value never appears in DB):")
            for key, vals in uncoverable_bools.items():
                print(f"    - {key}: {', '.join(vals)} never exists")

        if coverable_bools:
            print("\n  MISSED boolean coverage:")
            for key, vals in coverable_bools.items():
                print(f"    - {key}: missing {', '.join(vals)}")
            issues.append(f"{len(coverable_bools)} boolean fields incomplete")

        if all_uncoverable_enums:
            print("\n  Uncoverable enum values (defined in schema, not in DB):")
            for key, vals in all_uncoverable_enums.items():
                print(f"    - {key}: {', '.join(vals)} never exists in DB")

        if all_enum_gaps:
            print("\n  MISSED enum coverage (exists in DB, not in sample):")
            for key, info in all_enum_gaps.items():
                print(f"    - {key}: have {info['present']}, missing {info['missing']}")
            issues.append(f"{len(all_enum_gaps)} enum fields incomplete")

        if all_emptiness_gaps:
            print("\n  MISSED emptiness coverage (both empty and populated exist in DB):")
            for key, missing in all_emptiness_gaps.items():
                print(f"    - {key}: missing {', '.join(missing)}")
            issues.append(f"{len(all_emptiness_gaps)} emptiness gaps")

    return {
        "entity": entity_name,
        "count": len(items),
        "ok": ok,
        "missing_fields": missing_fields,
        "list_item_issues": list_item_issues,
        "uncoverable_nulls": uncoverable_nulls if full_db_items else None,
        "uncoverable_enums": all_uncoverable_enums or None,
        "coverable_nulls": coverable_nulls,
        "coverable_bools": coverable_bools,
        "enum_gaps": all_enum_gaps,
        "emptiness_gaps": all_emptiness_gaps,
        "issues": issues,
    }


def _add_item(item, selected, selected_ids):
    """Add an item to the selected set if not already present. Returns True if added."""
    item_id = item.get("id") or item.get("name")
    if item_id not in selected_ids:
        selected.append(item)
        selected_ids.add(item_id)
        return True
    return False


def _cover_nested_gaps(
    items: list[dict],
    selected: list[dict],
    selected_ids: set,
    nested_field: str,
    known_enums: dict[str, list[str]],
):
    """Add items to cover gaps in a nested object field."""
    sub_ref = _extract_sub_items(items, nested_field)
    if not sub_ref:
        return

    classification = classify_fields(sub_ref)
    all_sub_keys = set()
    for d in sub_ref:
        all_sub_keys.update(d.keys())

    # Boolean coverage within nested
    for key in sorted(all_sub_keys):
        if classification.get(key) != "boolean":
            continue
        current_vals = set()
        for item in selected:
            sub = item.get(nested_field)
            if isinstance(sub, dict) and isinstance(sub.get(key), bool):
                current_vals.add(sub[key])
        for target in [True, False]:
            if target not in current_vals:
                for item in items:
                    sub = item.get(nested_field)
                    if isinstance(sub, dict) and sub.get(key) is target:
                        _add_item(item, selected, selected_ids)
                        break

    # Enum coverage within nested
    enum_fields = set()
    full_key_prefix = f"{nested_field}."
    for k in known_enums:
        if k.startswith(full_key_prefix):
            enum_fields.add(k[len(full_key_prefix) :])
    for key in all_sub_keys:
        if classification.get(key) == "enum":
            enum_fields.add(key)

    for key in sorted(enum_fields):
        full_known_key = f"{nested_field}.{key}"
        expected = set(known_enums.get(full_known_key, []))
        db_values = {d[key] for d in sub_ref if d.get(key) is not None}
        expected |= db_values

        current_values = set()
        for item in selected:
            sub = item.get(nested_field)
            if isinstance(sub, dict) and sub.get(key) is not None:
                current_values.add(sub[key])

        for val in expected - current_values:
            if val not in db_values:
                continue
            for item in items:
                sub = item.get(nested_field)
                if isinstance(sub, dict) and sub.get(key) == val:
                    _add_item(item, selected, selected_ids)
                    break

    # Emptiness coverage within nested
    for key in sorted(all_sub_keys):
        ft = classification.get(key)
        if ft == "string":
            ref_has_empty = any(d.get(key) == "" for d in sub_ref)
            ref_has_pop = any(isinstance(d.get(key), str) and d.get(key) != "" for d in sub_ref)
            if not (ref_has_empty and ref_has_pop):
                continue
            sample_subs = _extract_sub_items(selected, nested_field)
            has_empty = any(d.get(key) == "" for d in sample_subs)
            has_pop = any(isinstance(d.get(key), str) and d.get(key) != "" for d in sample_subs)
            if not has_empty:
                for item in items:
                    sub = item.get(nested_field)
                    if isinstance(sub, dict) and sub.get(key) == "":
                        _add_item(item, selected, selected_ids)
                        break
            if not has_pop:
                for item in items:
                    sub = item.get(nested_field)
                    if isinstance(sub, dict) and isinstance(sub.get(key), str) and sub[key] != "":
                        _add_item(item, selected, selected_ids)
                        break

        elif ft == "list":
            ref_has_empty = any(isinstance(d.get(key), list) and len(d[key]) == 0 for d in sub_ref)
            ref_has_pop = any(isinstance(d.get(key), list) and len(d[key]) > 0 for d in sub_ref)
            if not (ref_has_empty and ref_has_pop):
                continue
            sample_subs = _extract_sub_items(selected, nested_field)
            has_empty = any(isinstance(d.get(key), list) and len(d[key]) == 0 for d in sample_subs)
            has_pop = any(isinstance(d.get(key), list) and len(d[key]) > 0 for d in sample_subs)
            if not has_empty:
                for item in items:
                    sub = item.get(nested_field)
                    if (
                        isinstance(sub, dict)
                        and isinstance(sub.get(key), list)
                        and len(sub[key]) == 0
                    ):
                        _add_item(item, selected, selected_ids)
                        break
            if not has_pop:
                for item in items:
                    sub = item.get(nested_field)
                    if (
                        isinstance(sub, dict)
                        and isinstance(sub.get(key), list)
                        and len(sub[key]) > 0
                    ):
                        _add_item(item, selected, selected_ids)
                        break


def build_covering_set(full_data: dict, output_path: str):
    """Build a minimal covering snapshot from a full database dump."""
    result = {}

    for entity in ENTITY_TYPES:
        items = full_data.get(entity, [])
        if not items:
            result[entity] = []
            continue

        classification = classify_fields(items)
        known = KNOWN_ENUMS.get(entity, {})
        all_keys = set()
        for item in items:
            all_keys.update(item.keys())

        selected_ids = set()
        selected = []

        # Phase 1: Greedy null coverage
        remaining_null_fields = set(all_keys)
        while remaining_null_fields:
            best_item = None
            best_covers = set()
            for item in items:
                covers = {k for k in remaining_null_fields if item.get(k) is not None}
                if len(covers) > len(best_covers):
                    best_covers = covers
                    best_item = item
            if not best_covers:
                break
            _add_item(best_item, selected, selected_ids)
            remaining_null_fields -= best_covers

        # Phase 2: Boolean coverage
        for key in sorted(all_keys):
            if classification.get(key) != "boolean":
                continue
            current_vals = {item[key] for item in selected if isinstance(item.get(key), bool)}
            for target in [True, False]:
                if target not in current_vals:
                    for item in items:
                        if item.get(key) is target:
                            _add_item(item, selected, selected_ids)
                            break

        # Phase 3: Enum coverage
        enum_fields = set()
        for k in known:
            if "." not in k:
                enum_fields.add(k)
        for key in all_keys:
            if classification.get(key) == "enum":
                enum_fields.add(key)

        for key in sorted(enum_fields):
            expected = set(known.get(key, []))
            db_values = {item[key] for item in items if item.get(key) is not None}
            expected |= db_values

            current_values = {item[key] for item in selected if item.get(key) is not None}
            for val in expected - current_values:
                if val not in db_values:
                    continue
                for item in items:
                    if item.get(key) == val:
                        _add_item(item, selected, selected_ids)
                        break

        # Phase 4: Emptiness coverage (empty string / empty list)
        for key in sorted(all_keys):
            field_type = classification.get(key)

            if field_type == "string":
                db_has_empty = any(item.get(key) == "" for item in items)
                db_has_pop = any(
                    isinstance(item.get(key), str) and item.get(key) != "" for item in items
                )
                if not (db_has_empty and db_has_pop):
                    continue
                if not any(item.get(key) == "" for item in selected):
                    for item in items:
                        if item.get(key) == "":
                            _add_item(item, selected, selected_ids)
                            break
                if not any(
                    isinstance(item.get(key), str) and item.get(key) != "" for item in selected
                ):
                    for item in items:
                        if isinstance(item.get(key), str) and item.get(key) != "":
                            _add_item(item, selected, selected_ids)
                            break

            elif field_type == "list":
                db_has_empty = any(
                    isinstance(item.get(key), list) and len(item[key]) == 0 for item in items
                )
                db_has_pop = any(
                    isinstance(item.get(key), list) and len(item[key]) > 0 for item in items
                )
                if not (db_has_empty and db_has_pop):
                    continue
                if not any(
                    isinstance(item.get(key), list) and len(item[key]) == 0 for item in selected
                ):
                    for item in items:
                        if isinstance(item.get(key), list) and len(item[key]) == 0:
                            _add_item(item, selected, selected_ids)
                            break
                if not any(
                    isinstance(item.get(key), list) and len(item[key]) > 0 for item in selected
                ):
                    for item in items:
                        if isinstance(item.get(key), list) and len(item[key]) > 0:
                            _add_item(item, selected, selected_ids)
                            break

        # Phase 5: Nested object coverage
        nested_fields = _find_nested_fields(items, classification)
        for nf in nested_fields:
            _cover_nested_gaps(items, selected, selected_ids, nf, known)

        result[entity] = selected
        print(f"{entity}: {len(selected)} items selected (from {len(items)})")

    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nSnapshot written to {output_path}")
    return result


def main():
    parser = argparse.ArgumentParser(description="Analyze OmniFocus snapshot coverage")
    parser.add_argument("snapshot", help="Path to snapshot JSON file")
    parser.add_argument(
        "--full-db", help="Path to full database JSON (for enum/uncoverable analysis)"
    )
    parser.add_argument(
        "--build-cover", action="store_true", help="Build a covering set instead of analyzing"
    )
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    default_output = f".sandbox/snapshot-sample-live-{timestamp}.json"
    parser.add_argument("--output", default=default_output, help="Output path for --build-cover")
    args = parser.parse_args()

    data = load_json(args.snapshot)

    if args.build_cover:
        result = build_covering_set(data, args.output)
        # Verify the result
        print("\n" + "=" * 60)
        print("  VERIFICATION")
        print("=" * 60)
        results = []
        for entity in ENTITY_TYPES:
            r = analyze_coverage(result.get(entity, []), entity, data.get(entity, []))
            results.append(r)
    else:
        full_data = load_json(args.full_db) if args.full_db else None
        results = []
        for entity in ENTITY_TYPES:
            full_items = full_data.get(entity, []) if full_data else None
            r = analyze_coverage(data.get(entity, []), entity, full_items)
            results.append(r)

    # Summary
    print(f"\n{'=' * 60}")
    print("  SUMMARY")
    print(f"{'=' * 60}")
    all_ok = True
    for r in results:
        status = "OK" if r["ok"] else "GAPS"
        issues = ", ".join(r.get("issues", [])) or "none"
        uncov_parts = []
        if r.get("uncoverable_nulls"):
            uncov_parts.append(f"{len(r['uncoverable_nulls'])} nulls")
        if r.get("uncoverable_enums"):
            uncov_parts.append(f"{len(r['uncoverable_enums'])} enums")
        uncov_str = f" (uncoverable: {', '.join(uncov_parts)})" if uncov_parts else ""
        print(f"  {r['entity']:15s} {r['count']:3d} items  [{status:4s}]  {issues}{uncov_str}")
        if not r["ok"]:
            all_ok = False

    if all_ok:
        print("\n  All coverable fields, booleans, enums, and emptiness are covered.")
    else:
        print("\n  Some gaps exist -- see details above.")
        print("  MISSED gaps can be fixed by adding more items to the snapshot.")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
