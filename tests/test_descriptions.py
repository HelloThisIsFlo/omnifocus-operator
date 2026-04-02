"""Tests for agent-facing description consolidation.

Ensures all agent-facing description constants are defined in descriptions.py,
referenced in consumer modules, and that no inline strings sneak back into
agent-facing models.
"""

import ast
import inspect
import pathlib

from omnifocus_operator import server as server_mod
from omnifocus_operator.agent_messages import descriptions as desc_mod
from omnifocus_operator.contracts.shared import actions as contracts_actions
from omnifocus_operator.contracts.shared import repetition_rule as contracts_repetition_rule
from omnifocus_operator.contracts.use_cases.add import tasks as contracts_add_tasks
from omnifocus_operator.contracts.use_cases.edit import tasks as contracts_edit_tasks
from omnifocus_operator.contracts.use_cases.list import common as contracts_list_common
from omnifocus_operator.contracts.use_cases.list import folders as contracts_list_folders
from omnifocus_operator.contracts.use_cases.list import projects as contracts_list_projects
from omnifocus_operator.contracts.use_cases.list import tags as contracts_list_tags
from omnifocus_operator.contracts.use_cases.list import tasks as contracts_list_tasks
from omnifocus_operator.models import common as models_common
from omnifocus_operator.models import enums as models_enums
from omnifocus_operator.models import folder as models_folder
from omnifocus_operator.models import perspective as models_perspective
from omnifocus_operator.models import project as models_project
from omnifocus_operator.models import repetition_rule as models_repetition_rule
from omnifocus_operator.models import snapshot as models_snapshot
from omnifocus_operator.models import tag as models_tag
from omnifocus_operator.models import task as models_task

_CONSUMER_MODULES = [
    models_common,
    models_task,
    models_project,
    models_tag,
    models_folder,
    models_perspective,
    models_snapshot,
    models_enums,
    models_repetition_rule,
    contracts_actions,
    contracts_repetition_rule,
    contracts_add_tasks,
    contracts_edit_tasks,
    contracts_list_common,
    contracts_list_tasks,
    contracts_list_projects,
    contracts_list_tags,
    contracts_list_folders,
    server_mod,
]


def _get_upper_snake_constants(module: object) -> set[str]:
    """Return all UPPER_SNAKE_CASE names exported from a module."""
    return {name for name in dir(module) if name.isupper() and not name.startswith("_")}


def _get_consumer_sources() -> str:
    """Return combined source of all consumer modules."""
    return "\n".join(inspect.getsource(m) for m in _CONSUMER_MODULES)


# --- Known internal classes (not agent-facing, exempt from centralization) ---

_INTERNAL_CLASSES = {
    # Base classes -- not in JSON Schema $defs
    "OmniFocusBaseModel",
    "OmniFocusEntity",
    "ActionableEntity",
    "StrictModel",
    "CommandModel",
    "QueryModel",
    # Protocol classes -- not Pydantic models
    "Service",
    "Repository",
    "Bridge",
    # Repo-boundary models -- internal, not agent-facing
    "AddTaskRepoPayload",
    "AddTaskRepoResult",
    "EditTaskRepoPayload",
    "EditTaskRepoResult",
    "MoveToRepoPayload",
    "RepetitionRuleRepoPayload",
    "ListRepoResult",
    "ListTasksRepoQuery",
    "ListProjectsRepoQuery",
    "ListTagsRepoQuery",
    "ListFoldersRepoQuery",
    # Internal sentinel
    "_Unset",
}


# ---------------------------------------------------------------------------
# Description consolidation tests
# ---------------------------------------------------------------------------


class TestDescriptionConsolidation:
    """Verify all description constants are used and no inline strings snuck back in."""

    def test_all_description_constants_are_strings(self) -> None:
        """Every UPPER_SNAKE_CASE constant in descriptions.py is a non-empty string."""
        constants = _get_upper_snake_constants(desc_mod)
        assert len(constants) > 0, "No constants found in descriptions module"
        for name in constants:
            value = getattr(desc_mod, name)
            assert isinstance(value, str), f"{name} is {type(value).__name__}, expected str"
            assert len(value) > 0, f"{name} is an empty string"

    def test_all_description_constants_referenced_in_consumers(self) -> None:
        """Every constant in descriptions.py must appear in at least one consumer (DESC-04)."""
        source = _get_consumer_sources()
        constants = _get_upper_snake_constants(desc_mod)
        unreferenced = {c for c in constants if c not in source}
        assert unreferenced == set(), (
            f"Description constants not referenced in consumer modules: {unreferenced}"
        )

    def test_no_inline_field_descriptions_in_agent_models(self) -> None:
        """No inline string literals in Field(description=...) calls (DESC-02 enforcement).

        Constants (ast.Name references) are OK. String literals and f-strings are not.
        """
        violations: list[str] = []

        for mod in _CONSUMER_MODULES:
            source = inspect.getsource(mod)
            tree = ast.parse(source)

            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                # Match Field(...) calls
                if not (
                    isinstance(node.func, ast.Name) and node.func.attr == "Field"
                    if isinstance(node.func, ast.Attribute)
                    else isinstance(node.func, ast.Name) and node.func.id == "Field"
                ):
                    continue

                for kw in node.keywords:
                    if kw.arg != "description":
                        continue
                    # String literal or f-string = bad
                    if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                        violations.append(
                            f"{mod.__name__} line {kw.value.lineno}: "
                            f"inline description string in Field()"
                        )
                    elif isinstance(kw.value, ast.JoinedStr):
                        violations.append(
                            f"{mod.__name__} line {kw.value.lineno}: "
                            f"f-string description in Field()"
                        )

        assert violations == [], (
            "Inline description strings found in agent-facing models:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    def test_no_inline_class_docstrings_on_agent_classes(self) -> None:
        """Agent-facing classes must use __doc__ = CONSTANT, not inline docstrings (DESC-03).

        Checks each consumer module's classes. Classes in the exception list are skipped.
        """
        violations: list[str] = []

        for mod in _CONSUMER_MODULES:
            source = inspect.getsource(mod)
            tree = ast.parse(source)

            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                if node.name in _INTERNAL_CLASSES:
                    continue

                # Check if first body statement is an inline docstring
                if (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                ):
                    violations.append(
                        f"{mod.__name__}:{node.lineno} class {node.name} "
                        f"has inline docstring instead of __doc__ = CONSTANT"
                    )

        assert violations == [], (
            "Agent-facing classes with inline docstrings (should use __doc__ = CONSTANT):\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    def test_no_inline_examples_in_agent_models(self) -> None:
        """No inline literals in Field(examples=...) calls.

        Each element in examples=[...] must be a constant reference (ast.Name),
        not an inline value (ast.Constant). This enforces centralization of
        example values in descriptions.py.
        """
        violations: list[str] = []

        for mod in _CONSUMER_MODULES:
            source = inspect.getsource(mod)
            tree = ast.parse(source)

            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                # Match Field(...) calls
                if not (
                    isinstance(node.func, ast.Name) and node.func.attr == "Field"
                    if isinstance(node.func, ast.Attribute)
                    else isinstance(node.func, ast.Name) and node.func.id == "Field"
                ):
                    continue

                for kw in node.keywords:
                    if kw.arg != "examples":
                        continue
                    if not isinstance(kw.value, ast.List):
                        violations.append(
                            f"{mod.__name__} line {kw.value.lineno}: "
                            f"examples= must be a list literal"
                        )
                        continue
                    for elt in kw.value.elts:
                        if isinstance(elt, ast.Constant):
                            violations.append(
                                f"{mod.__name__} line {elt.lineno}: "
                                f"inline value {elt.value!r} in Field(examples=...); "
                                f"use a constant from descriptions.py"
                            )

        assert violations == [], (
            "Inline example values found in agent-facing models:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


# ---------------------------------------------------------------------------
# Description enforcement tests (DESC-06)
# ---------------------------------------------------------------------------

_SRC_ROOT = pathlib.Path(__file__).resolve().parent.parent / "src" / "omnifocus_operator"

_SKIP_FILES = {"__init__.py", "base.py", "_validators.py"}


# ---------------------------------------------------------------------------
# Tool description enforcement tests (DESC-07)
# ---------------------------------------------------------------------------

_SERVER_PATH = _SRC_ROOT / "server.py"

# Claude Code truncates MCP tool descriptions at this byte limit.
# https://code.claude.com/docs/en/mcp
_TOOL_DESCRIPTION_BYTE_LIMIT = 2048


class TestToolDescriptionEnforcement:
    """Ensure MCP tool functions use centralized description constants (DESC-07)."""

    def _get_tool_decorated_functions(self) -> list[tuple[ast.FunctionDef, ast.Call]]:
        """Return (func_node, decorator_call) for every @mcp.tool(...) function."""
        source = _SERVER_PATH.read_text()
        tree = ast.parse(source)
        results: list[tuple[ast.FunctionDef, ast.Call]] = []

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                # Match mcp.tool(...)
                if (
                    isinstance(decorator.func, ast.Attribute)
                    and decorator.func.attr == "tool"
                    and isinstance(decorator.func.value, ast.Name)
                    and decorator.func.value.id == "mcp"
                ):
                    results.append((node, decorator))
        return results

    def test_tool_functions_use_centralized_descriptions(self) -> None:
        """Every @mcp.tool() must pass description=<Name> (constant ref, not string literal)."""
        tools = self._get_tool_decorated_functions()
        assert len(tools) >= 6, f"Expected at least 6 tools, found {len(tools)}"

        violations: list[str] = []
        for func, decorator in tools:
            desc_kwarg = None
            for kw in decorator.keywords:
                if kw.arg == "description":
                    desc_kwarg = kw
                    break

            if desc_kwarg is None:
                violations.append(
                    f"Tool '{func.name}' (line {func.lineno}): "
                    f"missing description= kwarg in @mcp.tool()"
                )
            elif not isinstance(desc_kwarg.value, ast.Name):
                violations.append(
                    f"Tool '{func.name}' (line {func.lineno}): "
                    f"description= must be a constant reference (Name), "
                    f"not {type(desc_kwarg.value).__name__}"
                )

        assert violations == [], "Tool functions not using centralized descriptions:\n" + "\n".join(
            f"  - {v}" for v in violations
        )

    def test_tool_functions_have_no_inline_docstrings(self) -> None:
        """@mcp.tool() functions must not have inline docstrings (prevents drift)."""
        tools = self._get_tool_decorated_functions()
        violations: list[str] = []

        for func, _decorator in tools:
            if (
                func.body
                and isinstance(func.body[0], ast.Expr)
                and isinstance(func.body[0].value, ast.Constant)
                and isinstance(func.body[0].value.value, str)
            ):
                violations.append(
                    f"Tool '{func.name}' (line {func.lineno}): "
                    f"has inline docstring — use description= kwarg instead"
                )

        assert violations == [], (
            "Tool functions with inline docstrings (should use description= kwarg):\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    def test_tool_descriptions_within_client_byte_limit(self) -> None:
        """Every @mcp.tool() description must fit within Claude Code's 2048-byte limit (DESC-08).

        Claude Code truncates MCP tool descriptions at 2048 bytes. Descriptions
        exceeding this limit are silently clipped, causing the agent to lose
        critical information (return format, constraints, examples).
        """
        tools = self._get_tool_decorated_functions()
        violations: list[str] = []

        for func, decorator in tools:
            # Find description= kwarg that is a constant reference (ast.Name)
            for kw in decorator.keywords:
                if kw.arg == "description" and isinstance(kw.value, ast.Name):
                    constant_name = kw.value.id
                    value = getattr(desc_mod, constant_name)
                    byte_len = len(value.encode("utf-8"))

                    if byte_len > _TOOL_DESCRIPTION_BYTE_LIMIT:
                        over = byte_len - _TOOL_DESCRIPTION_BYTE_LIMIT
                        encoded = value.encode("utf-8")
                        last_visible = encoded[:_TOOL_DESCRIPTION_BYTE_LIMIT][-40:].decode(
                            "utf-8", errors="replace"
                        )
                        first_lost = encoded[_TOOL_DESCRIPTION_BYTE_LIMIT:][:60].decode(
                            "utf-8", errors="replace"
                        )
                        violations.append(
                            f"  - {func.name} ({constant_name}): "
                            f"{byte_len} bytes ({over} over)\n"
                            f'    Last visible: "...{last_visible}"\n'
                            f'    First lost:   "{first_lost}"'
                        )

        assert violations == [], (
            f"Tool descriptions exceed Claude Code's {_TOOL_DESCRIPTION_BYTE_LIMIT}-byte limit:\n"
            + "\n".join(violations)
        )


class TestDescriptionEnforcement:
    """Ensure new classes default to requiring centralized descriptions (DESC-06)."""

    def test_new_classes_require_centralized_descriptions(self) -> None:
        """Scan ALL classes in models/ and contracts/.

        Non-excepted classes must use __doc__ = CONSTANT.
        This ensures new classes added in future phases are caught by default --
        they must either be excepted or centralized.
        """
        scan_dirs = [_SRC_ROOT / "models", _SRC_ROOT / "contracts"]
        violations: list[str] = []

        for scan_dir in scan_dirs:
            for py_file in sorted(scan_dir.rglob("*.py")):
                if py_file.name in _SKIP_FILES:
                    continue

                source = py_file.read_text()
                tree = ast.parse(source)
                rel_path = py_file.relative_to(_SRC_ROOT)

                for node in ast.walk(tree):
                    if not isinstance(node, ast.ClassDef):
                        continue
                    if node.name in _INTERNAL_CLASSES:
                        continue

                    # Check for __doc__ = <Name> assignment pattern
                    has_doc_assignment = False
                    has_inline_docstring = False

                    for stmt in node.body:
                        # __doc__ = CONSTANT assignment
                        if (
                            isinstance(stmt, ast.Assign)
                            and len(stmt.targets) == 1
                            and isinstance(stmt.targets[0], ast.Name)
                            and stmt.targets[0].id == "__doc__"
                        ):
                            has_doc_assignment = True
                            break
                        # Inline docstring (first Expr(Constant(str)))
                        if (
                            isinstance(stmt, ast.Expr)
                            and isinstance(stmt.value, ast.Constant)
                            and isinstance(stmt.value.value, str)
                        ):
                            has_inline_docstring = True
                            break
                        # Stop checking after first non-docstring statement
                        break

                    if has_inline_docstring:
                        violations.append(
                            f"Class '{node.name}' in {rel_path} has inline docstring. "
                            f"Either add it to _INTERNAL_CLASSES if it's internal, "
                            f"or centralize its docstring in descriptions.py."
                        )
                    elif not has_doc_assignment:
                        # No docstring at all -- acceptable for classes that don't
                        # need one (e.g., StrEnum subclasses with self-explanatory names).
                        # The exception list is the primary guardrail.
                        pass

        assert violations == [], "Classes not using centralized descriptions:\n" + "\n".join(
            f"  - {v}" for v in violations
        )
