"""Catalog ALL Pydantic error types from real AddTaskCommand / EditTaskCommand.

Question: What's the full catalog of Pydantic error types we'll encounter
with real AddTaskCommand and EditTaskCommand models?

Current _format_validation_errors() handles 4 patterns:
  1. _Unset noise suppression (msg contains "_Unset")
  2. extra_forbidden -> "Unknown field"
  3. literal_error on lifecycle -> educational message
  4. union_tag_invalid on frequency -> lists valid types

This script provokes every kind of validation error to find gaps.

Run:
  cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && uv run python .research/deep-dives/fastmcp-middleware-validation/2-error-flow/03_error_types_real_models.py
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from pydantic import ValidationError

from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand
from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SEPARATOR = "=" * 80
SUB_SEPARATOR = "-" * 60


def truncate(value: Any, max_len: int = 80) -> str:
    """Truncate repr to max_len chars."""
    s = repr(value)
    return s if len(s) <= max_len else s[: max_len - 3] + "..."


def run_case(
    label: str,
    model: type,
    data: dict[str, Any],
    error_catalog: list[dict[str, Any]],
) -> None:
    """Validate data against model, print errors, accumulate catalog."""
    print(f"\n{SUB_SEPARATOR}")
    print(f"CASE: {label}")
    print(f"Model: {model.__name__}")
    print(f"Input: {truncate(data, 120)}")

    try:
        model.model_validate(data)
        print("  -> VALID (no error)")
    except ValidationError as exc:
        print(f"  -> {exc.error_count()} error(s)")
        for err in exc.errors():
            loc = ".".join(str(part) for part in err["loc"])
            entry = {
                "case": label,
                "model": model.__name__,
                "type": err["type"],
                "loc": loc,
                "msg": err["msg"],
                "input": truncate(err.get("input"), 60),
            }
            error_catalog.append(entry)
            print(f"  [{err['type']}] loc={loc}")
            print(f"    msg: {err['msg']}")
            print(f"    input: {truncate(err.get('input'), 60)}")


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

def main() -> None:
    catalog: list[dict[str, Any]] = []

    print(SEPARATOR)
    print("PART 1: AddTaskCommand errors")
    print(SEPARATOR)

    # 1. Missing required field (name)
    run_case(
        "ADD: missing required field (name)",
        AddTaskCommand,
        {},
        catalog,
    )

    # 2. Wrong type for string field
    run_case(
        "ADD: wrong type for string field (name: 123)",
        AddTaskCommand,
        {"name": 123},
        catalog,
    )

    # 3. Extra/unknown field
    run_case(
        "ADD: extra/unknown field (bogus)",
        AddTaskCommand,
        {"name": "test", "bogus": True},
        catalog,
    )

    # 4. Invalid datetime format
    run_case(
        "ADD: invalid datetime (dueDate: 'not-a-date')",
        AddTaskCommand,
        {"name": "test", "dueDate": "not-a-date"},
        catalog,
    )

    # 5. Invalid nested model -- bad frequency type (discriminator)
    run_case(
        "ADD: invalid frequency discriminator (type: 'bogus')",
        AddTaskCommand,
        {
            "name": "test",
            "repetitionRule": {
                "frequency": {"type": "bogus"},
                "schedule": "regularly",
                "basedOn": "due_date",
            },
        },
        catalog,
    )

    # 6. Invalid enum value (schedule)
    run_case(
        "ADD: invalid enum value (schedule: 'bogus')",
        AddTaskCommand,
        {
            "name": "test",
            "repetitionRule": {
                "frequency": {"type": "daily"},
                "schedule": "bogus",
                "basedOn": "due_date",
            },
        },
        catalog,
    )

    # 7. Wrong type for bool (flagged: "yes")
    run_case(
        "ADD: wrong type for bool (flagged: 'yes')",
        AddTaskCommand,
        {"name": "test", "flagged": "yes"},
        catalog,
    )

    # 8. Wrong type for number (estimatedMinutes: "five")
    run_case(
        "ADD: wrong type for number (estimatedMinutes: 'five')",
        AddTaskCommand,
        {"name": "test", "estimatedMinutes": "five"},
        catalog,
    )

    # 9. Invalid basedOn enum
    run_case(
        "ADD: invalid basedOn enum ('bogus')",
        AddTaskCommand,
        {
            "name": "test",
            "repetitionRule": {
                "frequency": {"type": "daily"},
                "schedule": "regularly",
                "basedOn": "bogus",
            },
        },
        catalog,
    )

    # 10. Missing required nested field (frequency missing from repetitionRule)
    run_case(
        "ADD: missing required nested field (frequency omitted)",
        AddTaskCommand,
        {
            "name": "test",
            "repetitionRule": {
                "schedule": "regularly",
                "basedOn": "due_date",
            },
        },
        catalog,
    )

    # 11. Frequency object missing type discriminator
    run_case(
        "ADD: frequency object missing type field",
        AddTaskCommand,
        {
            "name": "test",
            "repetitionRule": {
                "frequency": {"interval": 2},
                "schedule": "regularly",
                "basedOn": "due_date",
            },
        },
        catalog,
    )

    # 12. Wrong type for entire nested model (repetitionRule: "bogus")
    run_case(
        "ADD: wrong type for nested model (repetitionRule: string)",
        AddTaskCommand,
        {"name": "test", "repetitionRule": "bogus"},
        catalog,
    )

    # 13. Wrong type for list field (tags: "single-string")
    run_case(
        "ADD: wrong type for list (tags: 'single-string')",
        AddTaskCommand,
        {"name": "test", "tags": "single-string"},
        catalog,
    )

    # 14. Wrong type in list items (tags: [123, true])
    run_case(
        "ADD: wrong type in list items (tags: [123, true])",
        AddTaskCommand,
        {"name": "test", "tags": [123, True]},
        catalog,
    )

    # 15. Extra field on nested model
    run_case(
        "ADD: extra field on nested model (repetitionRule.bogus)",
        AddTaskCommand,
        {
            "name": "test",
            "repetitionRule": {
                "frequency": {"type": "daily"},
                "schedule": "regularly",
                "basedOn": "due_date",
                "bogus": True,
            },
        },
        catalog,
    )

    # 16. Null for required field
    run_case(
        "ADD: null for required field (name: null)",
        AddTaskCommand,
        {"name": None},
        catalog,
    )

    print(f"\n\n{SEPARATOR}")
    print("PART 2: EditTaskCommand errors")
    print(SEPARATOR)

    # 1. Missing required field (id)
    run_case(
        "EDIT: missing required field (id)",
        EditTaskCommand,
        {},
        catalog,
    )

    # 2. Invalid literal value (lifecycle: "bogus")
    run_case(
        "EDIT: invalid literal (actions.lifecycle: 'bogus')",
        EditTaskCommand,
        {"id": "abc", "actions": {"lifecycle": "bogus"}},
        catalog,
    )

    # 3. Invalid frequency discriminator
    run_case(
        "EDIT: invalid frequency discriminator (type: 'bogus')",
        EditTaskCommand,
        {
            "id": "abc",
            "repetitionRule": {
                "frequency": {"type": "bogus"},
            },
        },
        catalog,
    )

    # 4. Extra field on nested model (actions.move.bogus)
    run_case(
        "EDIT: extra field on nested model (actions.move.bogus)",
        EditTaskCommand,
        {"id": "abc", "actions": {"move": {"ending": "proj1", "bogus": True}}},
        catalog,
    )

    # 5. Invalid tag action (replace + add)
    run_case(
        "EDIT: invalid tag action (replace + add)",
        EditTaskCommand,
        {"id": "abc", "actions": {"tags": {"replace": ["Tag1"], "add": ["Tag2"]}}},
        catalog,
    )

    # 6. Invalid move action (multiple keys)
    run_case(
        "EDIT: invalid move action (multiple keys)",
        EditTaskCommand,
        {"id": "abc", "actions": {"move": {"beginning": "proj1", "ending": "proj2"}}},
        catalog,
    )

    # 7. Extra field at top level
    run_case(
        "EDIT: extra field at top level (bogus)",
        EditTaskCommand,
        {"id": "abc", "bogus": True},
        catalog,
    )

    # 8. Empty tag action (no operation)
    run_case(
        "EDIT: empty tag action (no add/remove/replace)",
        EditTaskCommand,
        {"id": "abc", "actions": {"tags": {}}},
        catalog,
    )

    # 9. Wrong type for id
    run_case(
        "EDIT: wrong type for id (int)",
        EditTaskCommand,
        {"id": 999},
        catalog,
    )

    # 10. Invalid datetime on edit
    run_case(
        "EDIT: invalid datetime (dueDate: 'tuesday')",
        EditTaskCommand,
        {"id": "abc", "dueDate": "tuesday"},
        catalog,
    )

    # 11. Extra field on actions itself
    run_case(
        "EDIT: extra field on actions (actions.bogus)",
        EditTaskCommand,
        {"id": "abc", "actions": {"bogus": True}},
        catalog,
    )

    # 12. Wrong type for flagged
    run_case(
        "EDIT: wrong type for flagged (string)",
        EditTaskCommand,
        {"id": "abc", "flagged": "yes"},
        catalog,
    )

    # 13. Wrong type for estimatedMinutes
    run_case(
        "EDIT: wrong type for estimatedMinutes (string)",
        EditTaskCommand,
        {"id": "abc", "estimatedMinutes": "five"},
        catalog,
    )

    # 14. Nested repetition rule: invalid schedule enum
    run_case(
        "EDIT: invalid schedule enum in repetitionRule",
        EditTaskCommand,
        {
            "id": "abc",
            "repetitionRule": {
                "frequency": {"type": "daily"},
                "schedule": "bogus",
            },
        },
        catalog,
    )

    # 15. Move action with no keys at all
    run_case(
        "EDIT: move action with no keys",
        EditTaskCommand,
        {"id": "abc", "actions": {"move": {}}},
        catalog,
    )

    # ---------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------

    print(f"\n\n{SEPARATOR}")
    print("SUMMARY: Error Type Catalog")
    print(SEPARATOR)

    # Count by error type
    type_counter: Counter[str] = Counter()
    type_examples: dict[str, list[str]] = {}

    for entry in catalog:
        t = entry["type"]
        type_counter[t] += 1
        if t not in type_examples:
            type_examples[t] = []
        loc_str = entry["loc"] or "(root)"
        example = f'{entry["case"]} -> {loc_str}'
        if example not in type_examples[t]:
            type_examples[t].append(example)

    print(f"\n{'Error Type':<30} {'Count':>5}   Example Locations")
    print("-" * 90)
    for error_type, count in type_counter.most_common():
        examples = type_examples[error_type]
        # Print first example on same line, rest indented
        print(f"{error_type:<30} {count:>5}   {examples[0]}")
        for ex in examples[1:4]:  # Show up to 3 more examples
            print(f"{'':30} {'':>5}   {ex}")
        if len(examples) > 4:
            print(f"{'':30} {'':>5}   ... and {len(examples) - 4} more")

    print(f"\nTotal errors cataloged: {len(catalog)}")
    print(f"Unique error types: {len(type_counter)}")

    # Which types are NOT handled by _format_validation_errors?
    handled = {"extra_forbidden", "literal_error", "union_tag_invalid"}
    unhandled = set(type_counter.keys()) - handled
    print(f"\n{'Currently handled types':30} {sorted(handled)}")
    print(f"{'Types falling to default':30} {sorted(unhandled)}")
    print(f"  (these just get e['msg'] passed through as-is)")

    # Check for _Unset noise
    unset_entries = [e for e in catalog if "_Unset" in e["msg"]]
    print(f"\n_Unset noise entries: {len(unset_entries)}")
    for e in unset_entries:
        print(f"  [{e['type']}] {e['case']} -> {e['loc']}")
        print(f"    msg: {e['msg']}")


if __name__ == "__main__":
    main()
