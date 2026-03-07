#!/usr/bin/env python3
"""Analyze an OmniFocus snapshot for field, boolean, and enum coverage.

Usage:
    # Analyze a snapshot file
    python analyze_snapshot.py snapshot.json

    # Analyze with a full-database reference (for enum completeness)
    python analyze_snapshot.py snapshot.json --full-db full.json

    # Build a covering set from a full database dump
    python analyze_snapshot.py full.json --build-cover --output snapshot-sample-live.json

Output: per-entity coverage report showing gaps in null, boolean, and enum coverage.
"""

import argparse
import json
import sys
from datetime import datetime

ENTITY_TYPES = ["tasks", "projects", "tags", "folders", "perspectives"]


def load_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def classify_fields(items: list[dict]) -> dict:
    """Classify each field as boolean, enum-like string, or other."""
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
        elif all(isinstance(v, str) for v in non_null) and non_null:
            unique = set(non_null)
            # Enum-like: small value set where most values repeat.
            # Dates and IDs have many unique values relative to count —
            # a true enum (status, urgency) has high repetition.
            uniqueness_ratio = len(unique) / len(non_null) if non_null else 1
            if len(unique) <= 20 and uniqueness_ratio < 0.05:
                classification[key] = "enum"
            else:
                classification[key] = "string"
        else:
            classification[key] = "other"

    return classification


def analyze_coverage(items: list[dict], entity_name: str, full_db_items: list[dict] | None = None):
    """Analyze field coverage for a list of items."""
    if not items:
        print(f"\n{'=' * 60}")
        print(f"  {entity_name} (0 items) -- EMPTY")
        print(f"{'=' * 60}")
        return {"entity": entity_name, "count": 0, "ok": False}

    all_keys = set()
    for item in items:
        all_keys.update(item.keys())

    classification = classify_fields(full_db_items or items)
    issues = []

    # Null coverage
    always_null = []
    for key in sorted(all_keys):
        if all(item.get(key) is None for item in items):
            always_null.append(key)

    # Boolean coverage
    bool_gaps = {}
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
            bool_gaps[key] = missing

    # Enum coverage
    enum_gaps = {}
    if full_db_items:
        full_classification = classify_fields(full_db_items)
        for key in sorted(all_keys):
            if full_classification.get(key) != "enum":
                continue
            full_values = {item[key] for item in full_db_items if item.get(key) is not None}
            sample_values = {item[key] for item in items if item.get(key) is not None}
            missing = full_values - sample_values
            if missing:
                enum_gaps[key] = {"present": sorted(sample_values), "missing": sorted(missing)}

    # Check if gaps are uncoverable (not present in full DB either)
    uncoverable_nulls = []
    coverable_nulls = []
    if full_db_items:
        for key in always_null:
            if all(item.get(key) is None for item in full_db_items):
                uncoverable_nulls.append(key)
            else:
                coverable_nulls.append(key)

        uncoverable_bools = {}
        coverable_bools = {}
        for key, missing in bool_gaps.items():
            full_vals = [item[key] for item in full_db_items if isinstance(item.get(key), bool)]
            actually_missing = []
            for v in missing:
                target = v == "true"
                if target not in full_vals:
                    actually_missing.append(v)
            if actually_missing:
                uncoverable_bools[key] = actually_missing
            remaining = [m for m in missing if m not in actually_missing]
            if remaining:
                coverable_bools[key] = remaining
    else:
        coverable_nulls = always_null
        coverable_bools = bool_gaps

    # Report
    ok = not coverable_nulls and not coverable_bools and not enum_gaps
    status = "OK" if ok else "GAPS"

    print(f"\n{'=' * 60}")
    print(f"  {entity_name} ({len(items)} items) -- {status}")
    print(f"{'=' * 60}")

    if not always_null and not bool_gaps and not enum_gaps:
        print("  All fields, booleans, and enums fully covered.")
    else:
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

        if enum_gaps:
            print("\n  Enum coverage gaps:")
            for key, info in enum_gaps.items():
                print(f"    - {key}: have {info['present']}, missing {info['missing']}")
            issues.append(f"{len(enum_gaps)} enum fields incomplete")

    return {
        "entity": entity_name,
        "count": len(items),
        "ok": ok,
        "uncoverable_nulls": uncoverable_nulls if full_db_items else None,
        "coverable_nulls": coverable_nulls,
        "coverable_bools": coverable_bools,
        "enum_gaps": enum_gaps,
        "issues": issues,
    }


def build_covering_set(full_data: dict, output_path: str):
    """Build a minimal covering snapshot from a full database dump."""
    result = {}

    for entity in ENTITY_TYPES:
        items = full_data.get(entity, [])
        if not items:
            result[entity] = []
            continue

        classification = classify_fields(items)
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
                break  # remaining fields are null across entire DB
            item_id = best_item.get("id") or best_item.get("name")
            if item_id not in selected_ids:
                selected.append(best_item)
                selected_ids.add(item_id)
            remaining_null_fields -= best_covers

        # Phase 2: Boolean coverage
        for key in sorted(all_keys):
            if classification.get(key) != "boolean":
                continue
            current_vals = {item[key] for item in selected if isinstance(item.get(key), bool)}
            for target in [True, False]:
                if target not in current_vals:
                    # Find an item with this value
                    for item in items:
                        if item.get(key) is target:
                            item_id = item.get("id") or item.get("name")
                            if item_id not in selected_ids:
                                selected.append(item)
                                selected_ids.add(item_id)
                            break

        # Phase 3: Enum coverage
        for key in sorted(all_keys):
            if classification.get(key) != "enum":
                continue
            full_values = {item[key] for item in items if item.get(key) is not None}
            current_values = {item[key] for item in selected if item.get(key) is not None}
            for val in full_values - current_values:
                for item in items:
                    if item.get(key) == val:
                        item_id = item.get("id") or item.get("name")
                        if item_id not in selected_ids:
                            selected.append(item)
                            selected_ids.add(item_id)
                        break

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
        uncoverable = r.get("uncoverable_nulls")
        uncov_str = f" (uncoverable: {len(uncoverable)})" if uncoverable else ""
        print(f"  {r['entity']:15s} {r['count']:3d} items  [{status:4s}]  {issues}{uncov_str}")
        if not r["ok"]:
            all_ok = False

    if all_ok:
        print("\n  All coverable fields, booleans, and enums are covered.")
    else:
        print("\n  Some gaps exist -- see details above.")
        print("  MISSED gaps can be fixed by adding more items to the snapshot.")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
