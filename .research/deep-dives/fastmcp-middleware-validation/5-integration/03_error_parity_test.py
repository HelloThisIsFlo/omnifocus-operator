"""
Side-by-side error parity test: old path (dict + manual validate) vs new path
(typed params + ValidationReformatterMiddleware).

For each invalid input, compares the error message agents would see from both
approaches. Documents differences and classifies them as acceptable improvements,
regressions, or neutral.

How to run:
    cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && uv run python .research/deep-dives/fastmcp-middleware-validation/5-integration/03_error_parity_test.py
"""

from __future__ import annotations

import asyncio
import json
import textwrap
from typing import Any

import pydantic
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext
from pydantic import ValidationError

from omnifocus_operator.agent_messages.errors import INVALID_INPUT
from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand
from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand
from omnifocus_operator.server import _format_validation_errors


# ============================================================
# 1. OLD path: dict + manual validate (current server.py approach)
# ============================================================


def old_path_validate_add(raw_dict: dict[str, Any]) -> str | None:
    """Simulate current server.py add_tasks validation."""
    try:
        AddTaskCommand.model_validate(raw_dict)
        return None  # no error
    except ValidationError as exc:
        messages = _format_validation_errors(exc)
        return "; ".join(messages) or INVALID_INPUT


def old_path_validate_edit(raw_dict: dict[str, Any]) -> str | None:
    """Simulate current server.py edit_tasks validation."""
    try:
        EditTaskCommand.model_validate(raw_dict)
        return None  # no error
    except ValidationError as exc:
        messages = _format_validation_errors(exc)
        return "; ".join(messages) or INVALID_INPUT


# ============================================================
# 2. NEW path: typed params + ValidationReformatterMiddleware
# ============================================================


class ValidationReformatterMiddleware(Middleware):
    """Catch Pydantic ValidationError from typed params, reformat, re-raise as ToolError.

    Same middleware from 3-approaches/01_middleware_reformatter.py.
    """

    async def on_call_tool(self, context: MiddlewareContext, call_next: Any) -> Any:
        try:
            return await call_next(context)
        except pydantic.ValidationError as exc:
            messages = _format_validation_errors(exc)
            agent_msg = "; ".join(messages) or INVALID_INPUT
            raise ToolError(agent_msg) from exc
        except Exception as exc:
            exc_type_name = type(exc).__qualname__
            exc_module = type(exc).__module__ or ""
            if "ValidationError" in exc_type_name and "pydantic" in exc_module:
                try:
                    messages = _format_validation_errors(exc)  # type: ignore[arg-type]
                    agent_msg = "; ".join(messages) or INVALID_INPUT
                    raise ToolError(agent_msg) from exc
                except ToolError:
                    raise
                except Exception:
                    pass
            raise


mcp = FastMCP("error-parity-spike")
mcp.add_middleware(ValidationReformatterMiddleware())


@mcp.tool()
async def add_tasks(items: list[AddTaskCommand]) -> str:
    """Create tasks. Accepts typed list[AddTaskCommand]."""
    return f"OK: created {len(items)} task(s)"


@mcp.tool()
async def edit_tasks(items: list[EditTaskCommand]) -> str:
    """Edit tasks. Accepts typed list[EditTaskCommand]."""
    return f"OK: edited {len(items)} task(s)"


# ============================================================
# 3. Test infrastructure
# ============================================================

SEPARATOR = "=" * 78
THIN_SEP = "-" * 78

# Collect results for final summary
all_results: list[dict[str, Any]] = []


async def run_one_test(
    client: Client,
    *,
    label: str,
    tool: str,
    raw_dict: dict[str, Any],
    old_path_fn: Any,
) -> None:
    """Run a single test: old path (sync validate) + new path (client call)."""
    # -- OLD path --
    old_error = old_path_fn(raw_dict)

    # -- NEW path: wrap raw_dict in items list --
    new_error: str | None = None
    try:
        await client.call_tool(tool, {"items": [raw_dict]})
    except ToolError as e:
        new_error = str(e)
    except Exception as e:
        new_error = f"[UNEXPECTED {type(e).__name__}] {e}"

    # -- Compare --
    match = old_error == new_error
    diff = ""
    if not match:
        if old_error is None and new_error is None:
            match = True  # both succeeded
        elif old_error is None:
            diff = "OLD succeeded, NEW failed"
        elif new_error is None:
            diff = "OLD failed, NEW succeeded"
        else:
            diff = _describe_diff(old_error, new_error)

    result = {
        "label": label,
        "tool": tool,
        "input": raw_dict,
        "old": old_error,
        "new": new_error,
        "match": match,
        "diff": diff,
    }
    all_results.append(result)

    # -- Print --
    print(f"\nTest: {label}")
    print(f"Input: {json.dumps(raw_dict, default=str)}")
    print(f"OLD: {old_error}")
    print(f"NEW: {new_error}")
    print(f"MATCH: {'YES' if match else 'NO'}")
    if diff:
        print(f"DIFF: {diff}")


def _describe_diff(old: str, new: str) -> str:
    """Produce a human-readable description of what differs."""
    parts: list[str] = []

    # Check for items.0. prefix difference
    if "items.0." in new and "items.0." not in old:
        parts.append("NEW has 'items.0.' loc prefix (FastMCP validates full list param)")

    # Check for additional _Unset noise in new
    if "_Unset" in new and "_Unset" not in old:
        parts.append("NEW contains _Unset noise not present in OLD")
    elif "_Unset" in old and "_Unset" not in new:
        parts.append("OLD contains _Unset noise not present in NEW")

    # Check for message reordering
    old_parts = set(old.split("; "))
    new_parts = set(new.split("; "))
    if old_parts == new_parts and old != new:
        parts.append("Same messages, different order")

    if not parts:
        # Generic diff
        parts.append(f"Messages differ textually")

    return "; ".join(parts)


# ============================================================
# 4. All test scenarios
# ============================================================


async def run_all_tests() -> None:
    print(SEPARATOR)
    print("  ERROR PARITY TEST: Old Path vs New Path (Typed Params + Middleware)")
    print(SEPARATOR)

    async with Client(mcp) as client:

        # --------------------------------------------------------
        # AddTaskCommand errors
        # --------------------------------------------------------
        print(f"\n{THIN_SEP}")
        print("  AddTaskCommand Scenarios")
        print(THIN_SEP)

        # A1: Missing name
        await run_one_test(
            client,
            label="ADD: Missing 'name' (required field)",
            tool="add_tasks",
            raw_dict={"flagged": True},
            old_path_fn=old_path_validate_add,
        )

        # A2: Unknown field
        await run_one_test(
            client,
            label="ADD: Unknown field 'bogusField'",
            tool="add_tasks",
            raw_dict={"name": "Test", "bogusField": "surprise!"},
            old_path_fn=old_path_validate_add,
        )

        # A3: Invalid datetime
        await run_one_test(
            client,
            label="ADD: Invalid datetime 'not-a-date' for dueDate",
            tool="add_tasks",
            raw_dict={"name": "Test", "dueDate": "not-a-date"},
            old_path_fn=old_path_validate_add,
        )

        # A4: Invalid frequency type
        await run_one_test(
            client,
            label="ADD: Invalid frequency type 'biweekly'",
            tool="add_tasks",
            raw_dict={
                "name": "Test",
                "repetitionRule": {
                    "frequency": {"type": "biweekly"},
                    "schedule": "regularly",
                    "basedOn": "due_date",
                },
            },
            old_path_fn=old_path_validate_add,
        )

        # A5: Invalid schedule enum
        await run_one_test(
            client,
            label="ADD: Invalid schedule enum 'sometimes'",
            tool="add_tasks",
            raw_dict={
                "name": "Test",
                "repetitionRule": {
                    "frequency": {"type": "daily"},
                    "schedule": "sometimes",
                    "basedOn": "due_date",
                },
            },
            old_path_fn=old_path_validate_add,
        )

        # A6: Wrong type for name (int instead of string)
        await run_one_test(
            client,
            label="ADD: Wrong type for name (int instead of string)",
            tool="add_tasks",
            raw_dict={"name": 42},
            old_path_fn=old_path_validate_add,
        )

        # --------------------------------------------------------
        # EditTaskCommand errors
        # --------------------------------------------------------
        print(f"\n{THIN_SEP}")
        print("  EditTaskCommand Scenarios")
        print(THIN_SEP)

        # E1: Missing id
        await run_one_test(
            client,
            label="EDIT: Missing 'id' (required field)",
            tool="edit_tasks",
            raw_dict={"name": "Updated name"},
            old_path_fn=old_path_validate_edit,
        )

        # E2: Invalid lifecycle "delete"
        await run_one_test(
            client,
            label="EDIT: Invalid lifecycle 'delete'",
            tool="edit_tasks",
            raw_dict={"id": "abc123", "actions": {"lifecycle": "delete"}},
            old_path_fn=old_path_validate_edit,
        )

        # E3: Invalid frequency type
        await run_one_test(
            client,
            label="EDIT: Invalid frequency type 'biweekly'",
            tool="edit_tasks",
            raw_dict={
                "id": "abc123",
                "repetitionRule": {
                    "frequency": {"type": "biweekly"},
                },
            },
            old_path_fn=old_path_validate_edit,
        )

        # E4: Unknown field
        await run_one_test(
            client,
            label="EDIT: Unknown field 'bogusField'",
            tool="edit_tasks",
            raw_dict={"id": "abc123", "bogusField": "surprise!"},
            old_path_fn=old_path_validate_edit,
        )

        # E5: Tag replace + add conflict
        await run_one_test(
            client,
            label="EDIT: Tag replace + add conflict",
            tool="edit_tasks",
            raw_dict={
                "id": "abc123",
                "actions": {
                    "tags": {"replace": ["Work"], "add": ["Urgent"]},
                },
            },
            old_path_fn=old_path_validate_edit,
        )

        # E6: Move multiple keys
        await run_one_test(
            client,
            label="EDIT: Move with multiple keys",
            tool="edit_tasks",
            raw_dict={
                "id": "abc123",
                "actions": {
                    "move": {"beginning": "proj1", "ending": "proj2"},
                },
            },
            old_path_fn=old_path_validate_edit,
        )

    # ============================================================
    # 5. Summary
    # ============================================================
    print(f"\n\n{SEPARATOR}")
    print("  SUMMARY")
    print(SEPARATOR)

    total = len(all_results)
    matching = sum(1 for r in all_results if r["match"])
    mismatched = [r for r in all_results if not r["match"]]

    print(f"\n  Total tests:  {total}")
    print(f"  Matching:     {matching}/{total}")
    print(f"  Differences:  {len(mismatched)}")

    if mismatched:
        print(f"\n{THIN_SEP}")
        print("  DIFFERENCES FOUND")
        print(THIN_SEP)

        for r in mismatched:
            print(f"\n  [{r['label']}]")
            old_preview = (r["old"] or "(success)")[:200]
            new_preview = (r["new"] or "(success)")[:200]
            print(f"    OLD: {old_preview}")
            print(f"    NEW: {new_preview}")
            print(f"    DIFF: {r['diff']}")

    # ============================================================
    # 6. Classify differences
    # ============================================================
    print(f"\n\n{SEPARATOR}")
    print("  CLASSIFICATION OF DIFFERENCES")
    print(SEPARATOR)

    if not mismatched:
        print("\n  No differences to classify -- perfect parity!")
    else:
        print(f"\n  Analyzing {len(mismatched)} difference(s):\n")
        for r in mismatched:
            label = r["label"]
            diff = r["diff"]
            old = r["old"] or "(success)"
            new = r["new"] or "(success)"

            # Classify
            if "items.0." in diff:
                classification = "(a) Acceptable improvement"
                reason = (
                    "The 'items.0.' prefix is more precise -- it tells the agent "
                    "exactly which item in the batch failed. The old path validates "
                    "a single dict so has no positional context."
                )
            elif "_Unset" in diff:
                classification = "(b) Regression that needs fixing"
                reason = (
                    "_Unset noise leaking to the agent is a regression. The "
                    "middleware's _format_validation_errors should suppress these."
                )
            elif old == "(success)" or new == "(success)":
                classification = "(b) Regression that needs fixing"
                reason = "One path accepts input the other rejects -- validation mismatch."
            else:
                # Check if semantically equivalent (same info, different wording)
                old_lower = old.lower()
                new_lower = new.lower()
                if _semantically_similar(old_lower, new_lower):
                    classification = "(c) Neutral difference"
                    reason = "Same semantic content, minor wording/order difference."
                else:
                    classification = "(c) Neutral difference (review manually)"
                    reason = "Messages differ -- review whether agent experience is equivalent."

            print(f"  [{label}]")
            print(f"    Classification: {classification}")
            for line in textwrap.wrap(reason, width=70):
                print(f"    {line}")
            print()

    # ============================================================
    # 7. Key findings
    # ============================================================
    print(f"\n{SEPARATOR}")
    print("  KEY FINDINGS")
    print(SEPARATOR)

    loc_diffs = [r for r in mismatched if "items.0." in (r["diff"] or "")]
    unset_diffs = [r for r in mismatched if "_Unset" in (r["diff"] or "")]
    other_diffs = [r for r in mismatched if r not in loc_diffs and r not in unset_diffs]

    print(f"""
  Total tests:      {total}
  Exact matches:    {matching}/{total}
  Loc prefix diffs: {len(loc_diffs)} (items.0. prefix in new path)
  _Unset noise:     {len(unset_diffs)}
  Other diffs:      {len(other_diffs)}

  Known difference (documented in advance):
    loc paths include 'items.0.' prefix in the new path because FastMCP
    validates the full list[AddTaskCommand] / list[EditTaskCommand] parameter.
    The old path validates a single dict directly (items[0]).

  Verdict:
    If all differences are in the 'items.0.' loc prefix category, the
    middleware approach produces equivalent or better error messages.
    The prefix is strictly more informative for batch scenarios.

    If _Unset noise appears, the _format_validation_errors filter is
    working (suppressing _Unset messages) but the loc paths may include
    _Unset-related entries that need attention.

    If other differences appear, they need manual review.
""")


def _semantically_similar(a: str, b: str) -> bool:
    """Quick heuristic: check if two error messages carry the same info."""
    # Strip common noise
    for noise in ["items.0.", "items -> 0 -> "]:
        a = a.replace(noise, "")
        b = b.replace(noise, "")
    # If they match after stripping loc prefixes, they're equivalent
    return a.strip() == b.strip()


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    asyncio.run(run_all_tests())
