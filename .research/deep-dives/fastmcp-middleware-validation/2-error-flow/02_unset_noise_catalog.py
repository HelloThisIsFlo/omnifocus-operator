"""When using typed EditTaskCommand parameters, do we still get _Unset noise in validation errors?

Context:
    The current ``_format_validation_errors()`` in server.py filters out any error
    whose ``msg`` contains ``"_Unset"``. This was needed because when the agent sends
    invalid data for a ``PatchOrClear[T]`` field (which is ``Union[T, None, _Unset]``),
    Pydantic may generate error messages mentioning the ``_Unset`` branch of the union
    — e.g., "Input should be an instance of _Unset". The question is: does this still
    happen with typed params (where FastMCP calls ``model_validate()`` with native Python
    dicts), or does ``is_instance_schema`` prevent it?

What to look for:
    - For each invalid input, inspect every raw error dict from ``exc.errors()``
    - Count how many error messages mention "_Unset" or "Unset"
    - If zero: the ``is_instance_schema`` on ``_Unset`` cleanly rejects non-sentinel
      values without polluting error messages, and the filter in server.py is dead code
    - If nonzero: the filter is still needed, and we catalog which fields/types produce it

How to run:
    cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && uv run python \
        .research/deep-dives/fastmcp-middleware-validation/2-error-flow/02_unset_noise_catalog.py
"""

from __future__ import annotations

import json
import sys

from pydantic import ValidationError

from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

# --- Test cases: each is (label, invalid_input_dict) ---

TEST_CASES: list[tuple[str, dict]] = [
    (
        "invalid PatchOrClear[AwareDatetime] — dueDate: 'not-a-date'",
        {"id": "x", "dueDate": "not-a-date"},
    ),
    (
        "invalid Patch[bool] — flagged: 'not-a-bool'",
        {"id": "x", "flagged": "not-a-bool"},
    ),
    (
        "invalid Patch[str] — name: 123",
        {"id": "x", "name": 123},
    ),
    (
        "invalid PatchOrClear[float] — estimatedMinutes: 'not-a-number'",
        {"id": "x", "estimatedMinutes": "not-a-number"},
    ),
    (
        "invalid PatchOrClear[str] — note: 123",
        {"id": "x", "note": 123},
    ),
    (
        "invalid Patch[Literal['complete','drop']] — actions.lifecycle: 'bogus'",
        {"id": "x", "actions": {"lifecycle": "bogus"}},
    ),
]


def run_case(label: str, data: dict) -> tuple[int, int, list[dict]]:
    """Validate data against EditTaskCommand, return (total_errors, unset_errors, raw_errors)."""
    try:
        EditTaskCommand.model_validate(data)
        # Should not succeed — input is intentionally invalid
        print(f"  UNEXPECTED: validation passed for {data!r}")
        return (0, 0, [])
    except ValidationError as exc:
        raw_errors = exc.errors()
        unset_count = sum(
            1 for e in raw_errors if "_Unset" in e["msg"] or "Unset" in e["msg"]
        )
        return (len(raw_errors), unset_count, raw_errors)


def main() -> None:
    total_errors_all = 0
    total_unset_all = 0

    print("=" * 72)
    print("UNSET NOISE CATALOG — EditTaskCommand.model_validate()")
    print("=" * 72)

    for label, data in TEST_CASES:
        print()
        print("-" * 72)
        print(f"CASE: {label}")
        print(f"  Input: {json.dumps(data)}")
        print("-" * 72)

        total, unset, raw_errors = run_case(label, data)
        total_errors_all += total
        total_unset_all += unset

        for i, e in enumerate(raw_errors):
            has_unset = "_Unset" in e["msg"] or "Unset" in e["msg"]
            marker = " <<< UNSET NOISE" if has_unset else ""
            print(f"  Error {i + 1}/{total}:{marker}")
            print(f"    type: {e['type']}")
            print(f"    loc:  {e['loc']}")
            print(f"    msg:  {e['msg']}")
            if "input" in e:
                print(f"    input: {e['input']!r}")

        print()
        print(f"  Summary: {total} error(s), {unset} with UNSET noise")

    # --- Final verdict ---
    print()
    print("=" * 72)
    print("FINAL VERDICT")
    print("=" * 72)
    print(f"  Total errors across all cases: {total_errors_all}")
    print(f"  Errors containing UNSET noise: {total_unset_all}")
    print()
    if total_unset_all > 0:
        print("  UNSET noise present: YES")
        print("  -> The _Unset filter in _format_validation_errors() is still needed.")
    else:
        print("  UNSET noise present: NO")
        print("  -> is_instance_schema cleanly rejects invalid values without _Unset noise.")
        print("  -> The _Unset filter in _format_validation_errors() may be dead code.")


if __name__ == "__main__":
    main()
