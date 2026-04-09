"""Tests for agent-facing error message consolidation.

Ensures all agent-facing error messages are defined as constants in the
agent_messages.errors module, and that no inline strings sneak back into
consumer modules.
"""

import ast
import inspect

from omnifocus_operator import middleware, server
from omnifocus_operator.agent_messages import errors as err_mod
from omnifocus_operator.contracts.shared import actions as contracts_common
from omnifocus_operator.contracts.shared import repetition_rule as contracts_repetition_rule
from omnifocus_operator.contracts.use_cases.add import tasks as contracts_add_task
from omnifocus_operator.contracts.use_cases.edit import tasks as contracts_edit_task
from omnifocus_operator.contracts.use_cases.list import (
    _date_filter as contracts_list_date_filter,
)
from omnifocus_operator.contracts.use_cases.list import _validators as contracts_list_validators
from omnifocus_operator.contracts.use_cases.list import folders as contracts_list_folders
from omnifocus_operator.contracts.use_cases.list import projects as contracts_list_projects
from omnifocus_operator.contracts.use_cases.list import tags as contracts_list_tags
from omnifocus_operator.contracts.use_cases.list import tasks as contracts_list_tasks
from omnifocus_operator.models import repetition_rule as models_repetition_rule
from omnifocus_operator.service import domain as service_domain
from omnifocus_operator.service import errors as service_errors
from omnifocus_operator.service import resolve
from omnifocus_operator.service import service as service_orchestrator
from omnifocus_operator.service import validate as service_validate
from tests.agent_messages_helpers import get_consumer_sources, get_upper_snake_constants

_ERROR_CONSUMERS = [
    middleware,
    server,
    resolve,
    service_domain,
    service_errors,
    service_orchestrator,
    service_validate,
    contracts_common,
    contracts_add_task,
    contracts_edit_task,
    contracts_repetition_rule,
    contracts_list_date_filter,
    contracts_list_folders,
    contracts_list_validators,
    contracts_list_projects,
    contracts_list_tags,
    contracts_list_tasks,
    models_repetition_rule,
]


class TestErrorConsolidation:
    """Verify all error constants are used and no inline error strings snuck back in."""

    def test_all_error_constants_referenced_in_consumers(self) -> None:
        """Every constant in errors.py must appear in at least one error consumer."""
        source = get_consumer_sources(_ERROR_CONSUMERS)
        constants = get_upper_snake_constants(err_mod)
        unreferenced = {c for c in constants if c not in source}
        assert unreferenced == set(), (
            f"Error constants not referenced in consumer modules: {unreferenced}"
        )

    def test_no_inline_error_strings_in_consumers(self) -> None:
        """No inline f-string or string literal used as error message in consumers.

        Detects three patterns:

        Phase 1+2 (indirect raise via variable):
            msg = f"some error: {var}"  # or msg = "literal"
            raise ValueError(msg)

        Phase 3a (direct raise with inline string):
            raise ValueError("some error")
            raise ValueError(f"some error: {var}")

        Phase 3b (super().__init__() with inline string):
            super().__init__("some error")
            super().__init__(f"some error: {var}")
        """
        for mod in _ERROR_CONSUMERS:
            source = inspect.getsource(mod)
            tree = ast.parse(source)
            inline_errors: list[str] = []

            # --- Phase 1+2: indirect raise via variable ---
            inline_msg_vars: dict[str, int] = {}  # name -> lineno
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Assign)
                    and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and isinstance(node.value, (ast.JoinedStr, ast.Constant))
                ):
                    target_name = node.targets[0].id
                    if isinstance(node.value, ast.JoinedStr) or (
                        isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
                    ):
                        inline_msg_vars[target_name] = node.lineno

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

            # --- Phase 3a: direct raise with inline string ---
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Raise)
                    and node.exc is not None
                    and isinstance(node.exc, ast.Call)
                    and node.exc.args
                ):
                    arg = node.exc.args[0]
                    if isinstance(arg, (ast.Constant, ast.JoinedStr)):
                        if isinstance(arg, ast.Constant) and not isinstance(arg.value, str):
                            continue
                        snippet = ast.get_source_segment(source, arg) or f"line {arg.lineno}"
                        inline_errors.append(
                            f"line {node.lineno}: direct raise with inline string: {snippet}"
                        )

            # --- Phase 3b: super().__init__() with inline string ---
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                # Match super().__init__(...)
                if not (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr == "__init__"
                    and isinstance(node.func.value, ast.Call)
                    and isinstance(node.func.value.func, ast.Name)
                    and node.func.value.func.id == "super"
                ):
                    continue
                for arg in node.args:
                    if isinstance(arg, (ast.Constant, ast.JoinedStr)):
                        if isinstance(arg, ast.Constant) and not isinstance(arg.value, str):
                            continue
                        snippet = ast.get_source_segment(source, arg) or f"line {arg.lineno}"
                        inline_errors.append(
                            f"line {node.lineno}: super().__init__() with inline string: {snippet}"
                        )

            assert inline_errors == [], f"Inline error strings in {mod.__name__}:\n" + "\n".join(
                f"  - {e}" for e in inline_errors
            )

    def test_error_constants_are_strings(self) -> None:
        """All error constants must be plain strings."""
        constants = get_upper_snake_constants(err_mod)
        for name in constants:
            value = getattr(err_mod, name)
            assert isinstance(value, str), f"{name} is {type(value).__name__}, expected str"

    def test_parameterized_errors_have_valid_placeholders(self) -> None:
        """Parameterized errors must have balanced braces."""
        constants = get_upper_snake_constants(err_mod)
        for name in constants:
            value = getattr(err_mod, name)
            opens = value.count("{") - value.count("{{")
            closes = value.count("}") - value.count("}}")
            assert opens == closes, f"{name} has unbalanced braces: {opens} opens, {closes} closes"
