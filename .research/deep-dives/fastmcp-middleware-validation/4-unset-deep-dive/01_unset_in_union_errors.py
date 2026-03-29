"""How does _Unset appear in union branch validation errors, and WHY?

Context:
    Patch[T]        = Union[T, _Unset]
    PatchOrClear[T] = Union[T, None, _Unset]

    When an agent sends invalid data for these fields, Pydantic tries each union branch.
    The _Unset branch uses is_instance_schema — meaning Pydantic checks
    isinstance(value, _Unset). If the value isn't _Unset, Pydantic generates an error
    for that branch, and the error message mentions _Unset.

    This script makes the noise visible and answers: is _format_validation_errors
    filtering still needed when we use typed params?

How to run:
    cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && uv run python \
        .research/deep-dives/fastmcp-middleware-validation/4-unset-deep-dive/01_unset_in_union_errors.py
"""

from __future__ import annotations

import json
import textwrap

from pydantic import BaseModel, ConfigDict, ValidationError

from omnifocus_operator.contracts.base import UNSET, Patch, PatchOrClear, _Unset

# ---------------------------------------------------------------------------
# Minimal test model
# ---------------------------------------------------------------------------


class TestPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Patch[str] = UNSET  # Union[str, _Unset]
    value: PatchOrClear[float] = UNSET  # Union[float, None, _Unset]
    label: PatchOrClear[str] = UNSET  # Union[str, None, _Unset]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SEPARATOR = "=" * 72


def try_validate(description: str, data: dict) -> None:
    """Attempt model validation and print full error details on failure."""
    print()
    print(SEPARATOR)
    print(f"TEST: {description}")
    print(f"  Input: {json.dumps(data)}")
    print(SEPARATOR)

    try:
        result = TestPatch.model_validate(data)
        print(f"  PASSED — result: {result!r}")
        print(f"  Fields: {result.model_dump()}")
    except ValidationError as exc:
        print(f"  FAILED — {exc.error_count()} error(s)")
        print()
        for i, err in enumerate(exc.errors(), 1):
            print(f"  Error #{i}:")
            print(f"    Full dict: {json.dumps(err, indent=6)}")
            # Highlight _Unset-related noise
            msg = err.get("msg", "")
            err_type = err.get("type", "")
            if "Unset" in msg or "instance" in err_type or "_Unset" in str(err):
                print(f"    >>> _Unset NOISE DETECTED <<<")
                print(f"    msg:  {msg!r}")
                print(f"    type: {err_type!r}")
                print(
                    textwrap.indent(
                        textwrap.dedent("""\
                        WHY: Pydantic tries each union branch left-to-right.
                        The _Unset branch uses is_instance_schema (isinstance check).
                        When the input isn't an _Unset instance, that branch fails
                        with an 'is_instance_of' error mentioning _Unset.
                        This error is internal to union resolution — the agent
                        never sent _Unset, but the error message exposes it."""),
                        "    ",
                    )
                )
            print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print(SEPARATOR)
    print("_Unset in Union Branch Validation Errors — Deep Dive")
    print(SEPARATOR)
    print()
    print(f"_Unset class: {_Unset}")
    print(f"UNSET singleton: {UNSET!r} (id={id(UNSET)})")
    print(f"TestPatch schema unions:")
    print(f"  name:  Patch[str]        = Union[str, _Unset]")
    print(f"  value: PatchOrClear[float] = Union[float, None, _Unset]")
    print(f"  label: PatchOrClear[str]   = Union[str, None, _Unset]")

    # --- Failure cases ---

    try_validate(
        'Wrong type for Patch[str]: {"name": 123}',
        {"name": 123},
    )

    try_validate(
        'Wrong type for PatchOrClear[float]: {"value": "not-a-number"}',
        {"value": "not-a-number"},
    )

    try_validate(
        'Wrong type for PatchOrClear[str]: {"label": 123}',
        {"label": 123},
    )

    try_validate(
        'None for Patch[str] (None not in union): {"name": None}',
        {"name": None},
    )

    # --- Success cases ---

    try_validate(
        'Valid Patch[str]: {"name": "hello"}',
        {"name": "hello"},
    )

    try_validate(
        "Omitted fields (all default to UNSET): {}",
        {},
    )

    try_validate(
        'PatchOrClear with None (clear): {"value": None}',
        {"value": None},
    )

    try_validate(
        'Mixed valid input: {"name": "test", "value": 3.14, "label": None}',
        {"name": "test", "value": 3.14, "label": None},
    )

    # --- Verdict ---

    print()
    print(SEPARATOR)
    print("VERDICT: Is _format_validation_errors filtering still needed?")
    print(SEPARATOR)
    print(
        textwrap.dedent("""\
    Look at the error output above. For every failed validation, Pydantic
    includes an error for the _Unset branch — something like:

        "type": "is_instance_of",
        "msg": "Input should be an instance of _Unset"

    This happens regardless of whether we use typed params or raw dict
    input, because Pydantic always tries all union branches.

    The _Unset branch error is NOISE — the agent never sends _Unset.
    It's an internal implementation detail that leaks into error messages.

    ANSWER: Yes, filtering is still needed. Any validation error on a
    Patch/PatchOrClear field will include _Unset branch failures that
    confuse agents. The _format_validation_errors function should strip
    these out before returning errors to the agent.""")
    )


if __name__ == "__main__":
    main()
