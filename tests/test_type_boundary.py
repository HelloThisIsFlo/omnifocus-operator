"""Tests for type constraint boundary enforcement.

Ensures Literal and Annotated types are not used on core model field annotations
in models/. These constraint types belong on contract models in contracts/ where
they generate rich JSON Schema for agents. Core models use plain types with
runtime validators.

See docs/model-taxonomy.md "Type constraint boundary" for the convention.
"""

import ast
import pathlib
from typing import get_args

import pytest

from omnifocus_operator.contracts.shared.repetition_rule import (
    DayCode,
    DayName,
    FrequencyType,
)
from omnifocus_operator.models.repetition_rule import (
    _VALID_DAY_CODES,
    _VALID_DAY_NAMES,
    _VALID_FREQUENCY_TYPES,
    Frequency,
)

_SRC_ROOT = pathlib.Path(__file__).resolve().parent.parent / "src" / "omnifocus_operator"
_MODELS_DIR = _SRC_ROOT / "models"
_SKIP_FILES = {"__init__.py", "base.py", "_validators.py"}

# Known exceptions: agent-facing core models where Annotated provides schema
# benefit and no internal construction site is affected.
_EXCEPTIONS: set[tuple[str, str]] = set()
# (class_name, field_name) -- add entries here with a comment explaining why.


def _resolve_module_literal_aliases(tree: ast.Module) -> set[str]:
    """Find module-level names that are assigned a Literal[...] or Annotated[...] expression.

    Returns a set of variable names (e.g., {"_FrequencyType", "_DayName"}) that
    are aliases for Literal or Annotated types. These must not appear on class
    field annotations in models/.
    """
    aliases: set[str] = set()
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        # Get the value expression
        value = node.value
        if value is None:
            continue
        # Check if value is Subscript with Literal or Annotated
        if (
            isinstance(value, ast.Subscript)
            and isinstance(value.value, ast.Name)
            and value.value.id in {"Literal", "Annotated"}
        ):
            # Get the target name(s)
            if isinstance(node, ast.AnnAssign) and hasattr(node.target, "id"):
                aliases.add(node.target.id)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        aliases.add(target.id)
    return aliases


def _find_constraint_types(
    node: ast.expr,
    module_aliases: set[str] | frozenset[str] = frozenset(),
) -> list[str]:
    """Recursively search an annotation AST node for Literal and Annotated references.

    Returns a list of found type names (e.g., ["Literal"], ["Annotated"], or both).
    Also detects module-level aliases that resolve to Literal/Annotated.
    Handles:
    - ast.Name(id="Literal") / ast.Name(id="Annotated")
    - ast.Name(id=alias) where alias is in module_aliases
    - ast.Subscript(value=ast.Name(id="Literal")) (e.g., Literal["a", "b"])
    - ast.Subscript(value=ast.Name(id="Annotated")) (e.g., Annotated[int, ...])
    - Nested in ast.BinOp (union X | Y)
    - Nested in ast.Subscript (e.g., list[Literal[...]])
    """
    found: list[str] = []
    constraint_names = {"Literal", "Annotated"}

    if isinstance(node, ast.Name) and node.id in constraint_names:
        found.append(node.id)
    elif isinstance(node, ast.Name) and node.id in module_aliases:
        found.append(f"alias:{node.id}")
    elif isinstance(node, ast.Subscript):
        # Check the subscript value (e.g., Literal in Literal["a"])
        found.extend(_find_constraint_types(node.value, module_aliases))
        # Check inside the slice (e.g., list[Literal[...]])
        found.extend(_find_constraint_types(node.slice, module_aliases))
    elif isinstance(node, ast.BinOp):
        # Union: X | Y
        found.extend(_find_constraint_types(node.left, module_aliases))
        found.extend(_find_constraint_types(node.right, module_aliases))
    elif isinstance(node, ast.Tuple):
        # Tuple inside subscript slice (e.g., Annotated[int, Field(ge=1)])
        for elt in node.elts:
            found.extend(_find_constraint_types(elt, module_aliases))
    elif isinstance(node, ast.Attribute) and node.attr in constraint_names:
        # typing.Literal or typing.Annotated
        found.append(node.attr)

    return found


class TestTypeBoundaryEnforcement:
    """Verify Literal and Annotated types stay on contract model fields, not core models."""

    def test_no_literal_or_annotated_on_model_fields(self) -> None:
        """Scan models/ for Literal/Annotated field annotations.

        Only ast.AnnAssign nodes inside ast.ClassDef bodies are checked --
        module-level type alias definitions are naturally excluded.
        """
        violations: list[str] = []

        for py_file in sorted(_MODELS_DIR.rglob("*.py")):
            if py_file.name in _SKIP_FILES:
                continue

            source = py_file.read_text()
            tree = ast.parse(source)
            rel_path = py_file.relative_to(_SRC_ROOT)

            # Build set of module-level aliases that resolve to Literal/Annotated
            aliases = _resolve_module_literal_aliases(tree)

            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue

                for stmt in node.body:
                    if not isinstance(stmt, ast.AnnAssign):
                        continue
                    if not hasattr(stmt.target, "id"):
                        continue

                    field_name = stmt.target.id
                    if (node.name, field_name) in _EXCEPTIONS:
                        continue

                    constraint_types = _find_constraint_types(
                        stmt.annotation, module_aliases=aliases
                    )
                    if constraint_types:
                        types_str = ", ".join(sorted(set(constraint_types)))
                        violations.append(
                            f"Class '{node.name}' in {rel_path} "
                            f"field '{field_name}' uses {types_str}"
                        )

        assert violations == [], (
            "Literal/Annotated (or aliases thereof) found on core model field "
            "annotations in models/.\n"
            "These constraint types belong on contract models in contracts/.\n"
            "See docs/model-taxonomy.md 'Type constraint boundary'.\n\n"
            "Violations:\n" + "\n".join(f"  - {v}" for v in violations)
        )


class TestValidationSetSync:
    """Verify Literal type aliases in contracts/ stay in sync with validation sets in models/.

    If someone adds a value to a Literal alias without updating the corresponding
    validation set (or vice versa), these tests fail.
    """

    def test_day_codes_in_sync(self) -> None:
        assert set(get_args(DayCode)) == _VALID_DAY_CODES

    def test_day_names_in_sync(self) -> None:
        assert set(get_args(DayName)) == _VALID_DAY_NAMES

    def test_frequency_types_in_sync(self) -> None:
        assert set(get_args(FrequencyType)) == _VALID_FREQUENCY_TYPES

    def test_frequency_rejects_invalid_type(self) -> None:
        with pytest.raises(ValueError, match="Invalid frequency type"):
            Frequency(type="bogus", interval=1)
