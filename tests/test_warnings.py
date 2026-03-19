"""Tests for warning string consolidation."""

import ast
import inspect

from omnifocus_operator import server
from omnifocus_operator import warnings as warn_mod
from omnifocus_operator.service import domain as service_domain
from omnifocus_operator.service import service as service_orchestrator


def _get_all_warning_constants() -> set[str]:
    """Return all UPPER_SNAKE_CASE names exported from warnings.py."""
    return {name for name in dir(warn_mod) if name.isupper() and not name.startswith("_")}


_WARNING_CONSUMERS = [service_orchestrator, service_domain, server]


def _get_warning_consumer_sources() -> str:
    """Return combined source of all modules that consume warning constants."""
    return "\n".join(inspect.getsource(m) for m in _WARNING_CONSUMERS)


class TestWarningConsolidation:
    """Verify all warning constants are used and no inline strings snuck back in."""

    def test_all_warning_constants_referenced_in_consumers(self) -> None:
        """Every constant in warnings.py must appear in service.py or server.py source."""
        source = _get_warning_consumer_sources()
        constants = _get_all_warning_constants()
        unreferenced = {c for c in constants if c not in source}
        assert unreferenced == set(), (
            f"Warning constants not referenced in service.py or server.py: {unreferenced}"
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
        constants = _get_all_warning_constants()
        for name in constants:
            value = getattr(warn_mod, name)
            assert isinstance(value, str), f"{name} is {type(value).__name__}, expected str"

    def test_parameterized_warnings_have_valid_placeholders(self) -> None:
        """Parameterized warnings must have balanced braces."""
        constants = _get_all_warning_constants()
        for name in constants:
            value = getattr(warn_mod, name)
            # Count { and } -- should be balanced (ignoring {{ escapes)
            opens = value.count("{") - value.count("{{")
            closes = value.count("}") - value.count("}}")
            assert opens == closes, f"{name} has unbalanced braces: {opens} opens, {closes} closes"
