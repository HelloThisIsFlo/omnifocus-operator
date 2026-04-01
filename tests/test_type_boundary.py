"""Tests for type constraint boundary enforcement.

Ensures Literal and Annotated types are not used on core model field annotations
in models/. These constraint types belong on contract models in contracts/ where
they generate rich JSON Schema for agents. Core models use plain types with
runtime validators.

See docs/model-taxonomy.md "Type constraint boundary" for the convention.
"""

import ast
import pathlib

_SRC_ROOT = pathlib.Path(__file__).resolve().parent.parent / "src" / "omnifocus_operator"
_MODELS_DIR = _SRC_ROOT / "models"
_SKIP_FILES = {"__init__.py", "base.py", "_validators.py"}

# Known exceptions: agent-facing core models where Annotated provides schema
# benefit and no internal construction site is affected.
_EXCEPTIONS: set[tuple[str, str]] = {
    # (class_name, field_name) -- add entries here with a comment explaining why
    # EndByOccurrences is agent-facing via EndCondition union on contract fields.
    # Annotated[int, Field(ge=1)] emits minimum: 1 in schema -- valuable for agents.
    ("EndByOccurrences", "occurrences"),
}


def _find_constraint_types(node: ast.expr) -> list[str]:
    """Recursively search an annotation AST node for Literal and Annotated references.

    Returns a list of found type names (e.g., ["Literal"], ["Annotated"], or both).
    Handles:
    - ast.Name(id="Literal") / ast.Name(id="Annotated")
    - ast.Subscript(value=ast.Name(id="Literal")) (e.g., Literal["a", "b"])
    - ast.Subscript(value=ast.Name(id="Annotated")) (e.g., Annotated[int, ...])
    - Nested in ast.BinOp (union X | Y)
    - Nested in ast.Subscript (e.g., list[Literal[...]])
    """
    found: list[str] = []
    _CONSTRAINT_NAMES = {"Literal", "Annotated"}

    if isinstance(node, ast.Name) and node.id in _CONSTRAINT_NAMES:
        found.append(node.id)
    elif isinstance(node, ast.Subscript):
        # Check the subscript value (e.g., Literal in Literal["a"])
        found.extend(_find_constraint_types(node.value))
        # Check inside the slice (e.g., list[Literal[...]])
        found.extend(_find_constraint_types(node.slice))
    elif isinstance(node, ast.BinOp):
        # Union: X | Y
        found.extend(_find_constraint_types(node.left))
        found.extend(_find_constraint_types(node.right))
    elif isinstance(node, ast.Tuple):
        # Tuple inside subscript slice (e.g., Annotated[int, Field(ge=1)])
        for elt in node.elts:
            found.extend(_find_constraint_types(elt))
    elif isinstance(node, ast.Attribute) and node.attr in _CONSTRAINT_NAMES:
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

                    constraint_types = _find_constraint_types(stmt.annotation)
                    if constraint_types:
                        types_str = ", ".join(sorted(set(constraint_types)))
                        violations.append(
                            f"Class '{node.name}' in {rel_path} "
                            f"field '{field_name}' uses {types_str}"
                        )

        assert violations == [], (
            "Literal/Annotated found on core model field annotations in models/.\n"
            "These constraint types belong on contract models in contracts/.\n"
            "See docs/model-taxonomy.md 'Type constraint boundary'.\n\n"
            "Violations:\n" + "\n".join(f"  - {v}" for v in violations)
        )
