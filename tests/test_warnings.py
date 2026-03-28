"""Tests for agent-facing message consolidation (warnings and errors).

Ensures all agent-facing messages are defined as constants in the
agent_messages package, and that no inline strings sneak back into
consumer modules.
"""

import ast
import inspect

from omnifocus_operator import server
from omnifocus_operator.agent_messages import errors as err_mod
from omnifocus_operator.agent_messages import warnings as warn_mod
from omnifocus_operator.contracts import common as contracts_common
from omnifocus_operator.service import domain as service_domain
from omnifocus_operator.service import resolve
from omnifocus_operator.service import service as service_orchestrator


def _get_upper_snake_constants(module: object) -> set[str]:
    """Return all UPPER_SNAKE_CASE names exported from a module."""
    return {name for name in dir(module) if name.isupper() and not name.startswith("_")}


# ---------------------------------------------------------------------------
# Warning enforcement
# ---------------------------------------------------------------------------

_WARNING_CONSUMERS = [service_orchestrator, service_domain, server]

# Forward-declared constants: defined in Plan 33-01, wired in Plan 33-02 (service pipeline).
# Remove entries from this set as each constant gets wired to a consumer.
_FORWARD_DECLARED_WARNINGS = {
    "REPETITION_END_DATE_PAST",
    "REPETITION_EMPTY_ON_DATES",
    "REPETITION_NO_OP",
    "REPETITION_ON_COMPLETED_TASK",
}

# Forward-declared error constants: defined in Plan 33-01, consumed by
# service/validate.py (not yet in _ERROR_CONSUMERS) and service/domain.py
# (wired in Plan 33-02). Remove entries as consumers are registered.
_FORWARD_DECLARED_ERRORS = {
    "REPETITION_TYPE_CHANGE_INCOMPLETE",
    "REPETITION_NO_EXISTING_RULE",
    "REPETITION_INVALID_INTERVAL",
    "REPETITION_INVALID_DAY_CODE",
    "REPETITION_INVALID_ORDINAL",
    "REPETITION_INVALID_DAY_NAME",
    "REPETITION_INVALID_ON_DATE",
    "REPETITION_INVALID_END_OCCURRENCES",
}


def _get_consumer_sources(consumers: list[object]) -> str:
    """Return combined source of all consumer modules."""
    return "\n".join(inspect.getsource(m) for m in consumers)


class TestWarningConsolidation:
    """Verify all warning constants are used and no inline strings snuck back in."""

    def test_all_warning_constants_referenced_in_consumers(self) -> None:
        """Every constant in warnings.py must appear in at least one consumer."""
        source = _get_consumer_sources(_WARNING_CONSUMERS)
        constants = _get_upper_snake_constants(warn_mod)
        unreferenced = {c for c in constants if c not in source}
        unreferenced -= _FORWARD_DECLARED_WARNINGS
        assert unreferenced == set(), (
            f"Warning constants not referenced in consumer modules: {unreferenced}"
        )

    def test_no_inline_warning_strings_in_consumers(self) -> None:
        """No inline string literals in warnings/messages.append() calls."""
        for mod in _WARNING_CONSUMERS:
            source = inspect.getsource(mod)
            tree = ast.parse(source)
            inline_warnings = []
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "append"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id in ("warnings", "messages")
                    and node.args
                ):
                    arg = node.args[0]
                    # Inline string or f-string = bad
                    if isinstance(arg, (ast.Constant, ast.JoinedStr)):
                        inline_warnings.append(
                            ast.get_source_segment(source, arg) or f"line {arg.lineno}"
                        )
            assert inline_warnings == [], (
                f"Inline warning strings in {mod.__name__}: {inline_warnings}"
            )

    def test_warning_constants_are_strings(self) -> None:
        """All warning constants must be plain strings (not None, not int, etc.)."""
        constants = _get_upper_snake_constants(warn_mod)
        for name in constants:
            value = getattr(warn_mod, name)
            assert isinstance(value, str), f"{name} is {type(value).__name__}, expected str"

    def test_parameterized_warnings_have_valid_placeholders(self) -> None:
        """Parameterized warnings must have balanced braces."""
        constants = _get_upper_snake_constants(warn_mod)
        for name in constants:
            value = getattr(warn_mod, name)
            opens = value.count("{") - value.count("{{")
            closes = value.count("}") - value.count("}}")
            assert opens == closes, f"{name} has unbalanced braces: {opens} opens, {closes} closes"


# ---------------------------------------------------------------------------
# Error enforcement
# ---------------------------------------------------------------------------

_ERROR_CONSUMERS = [server, resolve, service_domain, service_orchestrator, contracts_common]


class TestErrorConsolidation:
    """Verify all error constants are used and no inline error strings snuck back in."""

    def test_all_error_constants_referenced_in_consumers(self) -> None:
        """Every constant in errors.py must appear in at least one error consumer."""
        source = _get_consumer_sources(_ERROR_CONSUMERS)
        constants = _get_upper_snake_constants(err_mod)
        unreferenced = {c for c in constants if c not in source}
        unreferenced -= _FORWARD_DECLARED_ERRORS
        assert unreferenced == set(), (
            f"Error constants not referenced in consumer modules: {unreferenced}"
        )

    def test_no_inline_error_strings_in_consumers(self) -> None:
        """No inline f-string or string literal assigned to msg then raised as ValueError.

        Detects the pattern:
            msg = f"some error: {var}"  # or msg = "literal"
            raise ValueError(msg)
        """
        for mod in _ERROR_CONSUMERS:
            source = inspect.getsource(mod)
            tree = ast.parse(source)
            inline_errors: list[str] = []

            # Build a set of variable names assigned from f-strings or string literals
            inline_msg_vars: dict[str, int] = {}  # name -> lineno
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Assign)
                    and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and isinstance(node.value, (ast.JoinedStr, ast.Constant))
                ):
                    target_name = node.targets[0].id
                    if isinstance(node.value, ast.JoinedStr):
                        # f-string assignment: always suspicious
                        inline_msg_vars[target_name] = node.lineno
                    elif isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        # Plain string assignment: suspicious if it looks like
                        # an error message (not a module-level constant import)
                        inline_msg_vars[target_name] = node.lineno

            # Now find raise ValueError(name) where name was assigned inline
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Raise)
                    and node.exc is not None
                    and isinstance(node.exc, ast.Call)
                    and isinstance(node.exc.func, ast.Name)
                    and node.exc.func.id == "ValueError"
                    and node.exc.args
                ):
                    arg = node.exc.args[0]
                    if isinstance(arg, ast.Name) and arg.id in inline_msg_vars:
                        lineno = inline_msg_vars[arg.id]
                        inline_errors.append(
                            f"line {lineno}: {arg.id} assigned as inline string, "
                            f"then raised at line {node.lineno}"
                        )

            assert inline_errors == [], f"Inline error strings in {mod.__name__}:\n" + "\n".join(
                f"  - {e}" for e in inline_errors
            )

    def test_error_constants_are_strings(self) -> None:
        """All error constants must be plain strings."""
        constants = _get_upper_snake_constants(err_mod)
        for name in constants:
            value = getattr(err_mod, name)
            assert isinstance(value, str), f"{name} is {type(value).__name__}, expected str"

    def test_parameterized_errors_have_valid_placeholders(self) -> None:
        """Parameterized errors must have balanced braces."""
        constants = _get_upper_snake_constants(err_mod)
        for name in constants:
            value = getattr(err_mod, name)
            opens = value.count("{") - value.count("{{")
            closes = value.count("}") - value.count("}}")
            assert opens == closes, f"{name} has unbalanced braces: {opens} opens, {closes} closes"
