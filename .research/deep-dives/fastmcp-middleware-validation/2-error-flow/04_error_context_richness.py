"""What extra context is available in ValidationError.errors() ctx dict for better error messages?

Question:
    Pydantic validation errors have a `ctx` field in each error dict that can
    contain extra context. For example, literal_error might include `expected`
    values, union_tag_invalid might include the discriminator info, etc.
    Can we build richer error messages by leveraging ctx data, instead of just
    pattern-matching on error type and msg string?

What to look for:
    - Which error types have a non-empty ctx dict?
    - Does literal_error ctx contain `expected` (list of valid literals)?
    - Does union_tag_invalid ctx contain `discriminator`, `tag`, `expected_tags`?
    - Does extra_forbidden have anything useful in ctx?
    - What about missing_field, string_type, datetime_parsing, value_error?
    - For _Unset noise errors: what does the full error dict look like?

How to run:
    cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && uv run python \
        .research/deep-dives/fastmcp-middleware-validation/2-error-flow/04_error_context_richness.py
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand
from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

SEPARATOR = "=" * 72
THIN_SEP = "-" * 72


def try_validate(label: str, model_cls: type, data: dict[str, Any]) -> list[dict[str, Any]]:
    """Attempt validation and return list of error dicts, or empty list on success."""
    print(f"\n{SEPARATOR}")
    print(f"TEST: {label}")
    print(f"Model: {model_cls.__name__}")
    print(f"Input: {json.dumps(data, indent=2, default=str)}")
    print(SEPARATOR)

    try:
        model_cls.model_validate(data)
        print("  --> VALID (no error)")
        return []
    except ValidationError as exc:
        errors = exc.errors()
        for i, e in enumerate(errors):
            print(f"\n  Error [{i}]:")
            print(f"    type:  {e.get('type')}")
            print(f"    loc:   {e.get('loc')}")
            print(f"    msg:   {e.get('msg')}")
            print(f"    input: {e.get('input')!r}")
            print(f"    ctx:   {e.get('ctx')}")
            print(f"    url:   {e.get('url')}")
            # Print full dict for completeness
            print(f"    FULL:  {json.dumps(e, indent=6, default=str)}")
        return errors


def main() -> None:
    all_results: dict[str, list[dict[str, Any]]] = {}

    # ================================================================
    # GROUP 1: The 4 rewrite types in current _format_validation_errors
    # ================================================================

    # 1a. extra_forbidden -- unknown field
    errors = try_validate(
        "extra_forbidden (unknown field on AddTaskCommand)",
        AddTaskCommand,
        {"name": "Test", "bogusField": "hello"},
    )
    all_results["extra_forbidden"] = errors

    # 1b. literal_error -- invalid lifecycle value
    errors = try_validate(
        "literal_error (invalid lifecycle on EditTaskCommand)",
        EditTaskCommand,
        {"id": "abc123", "actions": {"lifecycle": "archive"}},
    )
    all_results["literal_error"] = errors

    # 1c. union_tag_invalid -- invalid frequency type
    errors = try_validate(
        "union_tag_invalid (invalid frequency type on AddTaskCommand)",
        AddTaskCommand,
        {
            "name": "Test",
            "repetitionRule": {
                "frequency": {"type": "biweekly", "interval": 1},
                "schedule": "regularly",
                "basedOn": "due_date",
            },
        },
    )
    all_results["union_tag_invalid"] = errors

    # 1d. _Unset noise error -- send wrong type for an UNSET-defaulted field
    #     e.g., set name to an integer on EditTaskCommand (name: Patch[str] = UNSET)
    errors = try_validate(
        "_Unset noise (wrong type for Patch[str] field)",
        EditTaskCommand,
        {"id": "abc123", "name": 12345},
    )
    all_results["_Unset_noise"] = errors

    # ================================================================
    # GROUP 2: Additional error types for ctx exploration
    # ================================================================

    # 2a. missing field -- omit required 'name' on AddTaskCommand
    errors = try_validate(
        "missing (omit required field 'name')",
        AddTaskCommand,
        {"tags": ["Work"]},
    )
    all_results["missing"] = errors

    # 2b. string_type -- send non-string for a string field
    errors = try_validate(
        "string_type (non-string for required 'id' on EditTaskCommand)",
        EditTaskCommand,
        {"id": ["not", "a", "string"]},
    )
    all_results["string_type"] = errors

    # 2c. datetime_parsing -- invalid datetime string
    errors = try_validate(
        "datetime_parsing (bad datetime for dueDate)",
        AddTaskCommand,
        {"name": "Test", "dueDate": "not-a-date"},
    )
    all_results["datetime_parsing"] = errors

    # 2d. value_error from model_validator -- TagAction with both replace and add
    errors = try_validate(
        "value_error (model_validator: replace + add on TagAction)",
        EditTaskCommand,
        {
            "id": "abc123",
            "actions": {
                "tags": {"replace": ["Tag1"], "add": ["Tag2"]},
            },
        },
    )
    all_results["value_error_model_validator"] = errors

    # 2e. value_error from model_validator -- MoveAction with zero keys
    errors = try_validate(
        "value_error (model_validator: MoveAction with no keys)",
        EditTaskCommand,
        {
            "id": "abc123",
            "actions": {"move": {}},
        },
    )
    all_results["value_error_move_no_keys"] = errors

    # 2f. value_error from model_validator -- TagAction with no operations
    errors = try_validate(
        "value_error (model_validator: TagAction with no ops)",
        EditTaskCommand,
        {
            "id": "abc123",
            "actions": {"tags": {}},
        },
    )
    all_results["value_error_tags_no_ops"] = errors

    # ================================================================
    # SUMMARY
    # ================================================================
    print(f"\n\n{SEPARATOR}")
    print("SUMMARY: ctx richness by error type")
    print(SEPARATOR)

    for label, errors in all_results.items():
        print(f"\n{THIN_SEP}")
        print(f"  {label}:")
        if not errors:
            print("    (no errors -- validated successfully)")
            continue
        for e in errors:
            etype = e.get("type", "?")
            ctx = e.get("ctx")
            has_ctx = bool(ctx)
            ctx_keys = sorted(ctx.keys()) if ctx else []
            print(f"    type={etype}")
            print(f"      has ctx: {has_ctx}")
            if ctx_keys:
                print(f"      ctx keys: {ctx_keys}")
                for k, v in sorted(ctx.items()):
                    print(f"        {k} = {v!r}")
            else:
                print(f"      ctx: {ctx}")

    print(f"\n\n{SEPARATOR}")
    print("CONCLUSION: Which error types have useful ctx for reformatting?")
    print(SEPARATOR)

    useful_types: list[str] = []
    empty_types: list[str] = []

    for label, errors in all_results.items():
        for e in errors:
            etype = e.get("type", "?")
            ctx = e.get("ctx")
            if ctx:
                useful_types.append(f"{etype} (from {label})")
            else:
                empty_types.append(f"{etype} (from {label})")

    print("\n  Error types WITH useful ctx:")
    for t in useful_types:
        print(f"    + {t}")

    print("\n  Error types WITHOUT ctx (empty or None):")
    for t in empty_types:
        print(f"    - {t}")


if __name__ == "__main__":
    main()
