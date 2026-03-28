"""Output schema validation, union regression guards, and naming convention tests.

Ensures that serialized tool output validates against the MCP outputSchema
that FastMCP advertises to clients. Catches regressions like @model_serializer
erasing JSON Schema structure, and enforces models/ vs contracts/ naming rules.
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import pkgutil
from typing import Any

import jsonschema
import pydantic_core
import pytest
from pydantic import BaseModel, TypeAdapter

from omnifocus_operator.contracts.use_cases.add_task import AddTaskResult
from omnifocus_operator.contracts.use_cases.edit_task import EditTaskResult
from omnifocus_operator.models import AllEntities, Project, Tag, Task
from omnifocus_operator.models.repetition_rule import (
    EndCondition,
    Frequency,
)
from omnifocus_operator.server import create_server
from tests.conftest import (
    make_model_project_dict,
    make_model_snapshot_dict,
    make_model_tag_dict,
    make_model_task_dict,
    make_perspective_dict,
)

# ---------------------------------------------------------------------------
# Server-sourced output schemas (the real schemas FastMCP serves to clients)
# ---------------------------------------------------------------------------


def _load_tool_schemas() -> dict[str, dict[str, Any]]:
    """Load output schemas from the actual FastMCP server."""

    async def _fetch() -> dict[str, dict[str, Any]]:
        server = create_server()
        tools = await server.list_tools()
        return {t.name: t.output_schema for t in tools}

    return asyncio.run(_fetch())


_TOOL_SCHEMAS: dict[str, dict[str, Any]] = _load_tool_schemas()

# Return types used only by TestUnionRegressionGuard for raw $defs inspection
# (server schemas are fully inlined, so $defs checking requires TypeAdapter).
_REGRESSION_GUARD_TYPES: dict[str, type] = {
    "get_all": AllEntities,
    "get_task": Task,
    "get_project": Project,
    "get_tag": Tag,
    "add_tasks": list[AddTaskResult],
    "edit_tasks": list[EditTaskResult],
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def serialize_like_fastmcp(value: Any) -> Any:
    """Reproduce FastMCP's serialization path."""
    return pydantic_core.to_jsonable_python(value)


# ---------------------------------------------------------------------------
# Repetition rule fixture data (camelCase dicts for model_validate)
# ---------------------------------------------------------------------------


def _make_repetition_rule_dict(variant: str) -> dict[str, Any]:
    """Return a camelCase repetition rule dict for the given variant."""
    rules: dict[str, dict[str, Any]] = {
        "daily": {
            "frequency": {"type": "daily", "interval": 1},
            "schedule": "regularly",
            "basedOn": "due_date",
            "end": None,
        },
        "weekly_bare": {
            "frequency": {"type": "weekly", "interval": 1},
            "schedule": "regularly",
            "basedOn": "due_date",
            "end": None,
        },
        "weekly_with_days": {
            "frequency": {
                "type": "weekly_on_days",
                "interval": 1,
                "onDays": ["MO", "WE", "FR"],
            },
            "schedule": "from_completion",
            "basedOn": "defer_date",
            "end": {"occurrences": 10},
        },
        "monthly_day_of_week": {
            "frequency": {
                "type": "monthly_day_of_week",
                "interval": 1,
                "on": {"second": "tuesday"},
            },
            "schedule": "regularly_with_catch_up",
            "basedOn": "due_date",
            "end": {"date": "2025-12-31"},
        },
        "monthly_day_in_month": {
            "frequency": {
                "type": "monthly_day_in_month",
                "interval": 2,
                "onDates": [1, 15, -1],
            },
            "schedule": "regularly",
            "basedOn": "planned_date",
            "end": None,
        },
    }
    return rules[variant]


# ---------------------------------------------------------------------------
# Pre-built fixture instances
# ---------------------------------------------------------------------------

# Tasks with various repetition rules
_TASK_DAILY = Task.model_validate(
    make_model_task_dict(
        id="task-daily",
        name="Daily Task",
        repetitionRule=_make_repetition_rule_dict("daily"),
    )
)
_TASK_WEEKLY_BARE = Task.model_validate(
    make_model_task_dict(
        id="task-weekly-bare",
        name="Weekly Bare Task",
        repetitionRule=_make_repetition_rule_dict("weekly_bare"),
    )
)
_TASK_WEEKLY = Task.model_validate(
    make_model_task_dict(
        id="task-weekly",
        name="Weekly Task",
        repetitionRule=_make_repetition_rule_dict("weekly_with_days"),
    )
)
_TASK_MONTHLY_DOW = Task.model_validate(
    make_model_task_dict(
        id="task-mdow",
        name="Monthly DOW Task",
        repetitionRule=_make_repetition_rule_dict("monthly_day_of_week"),
    )
)
_TASK_MONTHLY_DIM = Task.model_validate(
    make_model_task_dict(
        id="task-mdim",
        name="Monthly DIM Task",
        repetitionRule=_make_repetition_rule_dict("monthly_day_in_month"),
    )
)
_TASK_PLAIN = Task.model_validate(
    make_model_task_dict(id="task-plain", name="Plain Task", repetitionRule=None)
)

# Project with weekly repetition
_PROJECT = Project.model_validate(
    make_model_project_dict(
        id="proj-rep",
        name="Repeating Project",
        repetitionRule=_make_repetition_rule_dict("weekly_with_days"),
    )
)

# Plain tag (no repetitionRule)
_TAG = Tag.model_validate(make_model_tag_dict(id="tag-plain", name="Plain Tag"))

# AllEntities snapshot containing all fixtures
_SNAPSHOT = AllEntities.model_validate(
    make_model_snapshot_dict(
        tasks=[
            make_model_task_dict(
                id="task-daily",
                name="Daily Task",
                repetitionRule=_make_repetition_rule_dict("daily"),
            ),
            make_model_task_dict(
                id="task-weekly-bare",
                name="Weekly Bare Task",
                repetitionRule=_make_repetition_rule_dict("weekly_bare"),
            ),
            make_model_task_dict(
                id="task-weekly",
                name="Weekly Task",
                repetitionRule=_make_repetition_rule_dict("weekly_with_days"),
            ),
            make_model_task_dict(
                id="task-mdow",
                name="Monthly DOW Task",
                repetitionRule=_make_repetition_rule_dict("monthly_day_of_week"),
            ),
            make_model_task_dict(
                id="task-mdim",
                name="Monthly DIM Task",
                repetitionRule=_make_repetition_rule_dict("monthly_day_in_month"),
            ),
            make_model_task_dict(
                id="task-plain",
                name="Plain Task",
                repetitionRule=None,
            ),
        ],
        projects=[
            make_model_project_dict(
                id="proj-rep",
                name="Repeating Project",
                repetitionRule=_make_repetition_rule_dict("weekly_with_days"),
            ),
        ],
        tags=[make_model_tag_dict(id="tag-plain", name="Plain Tag")],
        perspectives=[make_perspective_dict(id="persp-test", name="Test Perspective")],
    )
)

# Write tool result fixtures
_ADD_TASK_RESULT = AddTaskResult(success=True, id="new-task-001", name="Created Task")
_EDIT_TASK_RESULT = EditTaskResult(success=True, id="task-001", name="Edited Task", warnings=[])

# Map tool names to their fixture instances
_TOOL_FIXTURES: dict[str, Any] = {
    "get_all": _SNAPSHOT,
    "get_task": _TASK_DAILY,
    "get_project": _PROJECT,
    "get_tag": _TAG,
    "add_tasks": [_ADD_TASK_RESULT],
    "edit_tasks": [_EDIT_TASK_RESULT],
}


# ---------------------------------------------------------------------------
# Schema-vs-data validation tests (D-02, covers SC-1 + SC-2)
# ---------------------------------------------------------------------------


class TestSchemaValidation:
    """Serialized tool output must validate against the MCP outputSchema."""

    def test_all_tools_have_fixtures(self) -> None:
        """Every registered tool has a fixture and vice versa."""
        assert set(_TOOL_SCHEMAS.keys()) == set(_TOOL_FIXTURES.keys())

    @pytest.mark.parametrize("tool_name", sorted(_TOOL_SCHEMAS))
    def test_tool_output_validates_against_schema(self, tool_name: str) -> None:
        """For each MCP tool, serialized fixture data validates against outputSchema."""
        schema = _TOOL_SCHEMAS[tool_name]
        fixture = _TOOL_FIXTURES[tool_name]

        if schema.get("x-fastmcp-wrap-result", False):
            data = {"result": serialize_like_fastmcp(fixture)}
        else:
            data = serialize_like_fastmcp(fixture)

        jsonschema.validate(data, schema)

    @pytest.mark.parametrize(
        "variant",
        ["daily", "weekly_bare", "weekly_with_days", "monthly_day_of_week", "monthly_day_in_month"],
    )
    def test_repetition_rule_variants_validate(self, variant: str) -> None:
        """Each frequency type validates when serialized inside an AllEntities snapshot."""
        snapshot = AllEntities.model_validate(
            make_model_snapshot_dict(
                tasks=[
                    make_model_task_dict(
                        id=f"task-{variant}",
                        name=f"Task with {variant}",
                        repetitionRule=_make_repetition_rule_dict(variant),
                    ),
                ],
            )
        )
        schema = _TOOL_SCHEMAS["get_all"]
        data = serialize_like_fastmcp(snapshot)
        jsonschema.validate(data, schema)

    def test_end_conditions_validate(self) -> None:
        """EndByDate and EndByOccurrences both validate inside AllEntities."""
        # EndByOccurrences: weekly_with_days has end.occurrences=10
        # EndByDate: monthly_day_of_week has end.date="2025-12-31"
        snapshot = AllEntities.model_validate(
            make_model_snapshot_dict(
                tasks=[
                    make_model_task_dict(
                        id="task-end-occ",
                        name="End by occurrences",
                        repetitionRule=_make_repetition_rule_dict("weekly_with_days"),
                    ),
                    make_model_task_dict(
                        id="task-end-date",
                        name="End by date",
                        repetitionRule=_make_repetition_rule_dict("monthly_day_of_week"),
                    ),
                ],
            )
        )
        schema = _TOOL_SCHEMAS["get_all"]
        data = serialize_like_fastmcp(snapshot)
        jsonschema.validate(data, schema)

    def test_add_task_result_with_warnings_validates(self) -> None:
        """AddTaskResult with populated warnings list validates against outputSchema."""
        result = AddTaskResult(
            success=True,
            id="task-with-warnings",
            name="Task With Warnings",
            warnings=["End date is in the past", "Setting repetition on completed task"],
        )
        schema = _TOOL_SCHEMAS["add_tasks"]
        if schema.get("x-fastmcp-wrap-result", False):
            data = {"result": serialize_like_fastmcp([result])}
        else:
            data = serialize_like_fastmcp([result])
        jsonschema.validate(data, schema)

    def test_add_task_result_without_warnings_validates(self) -> None:
        """AddTaskResult with warnings=None validates (optional field)."""
        result = AddTaskResult(success=True, id="task-no-warnings", name="No Warnings")
        schema = _TOOL_SCHEMAS["add_tasks"]
        if schema.get("x-fastmcp-wrap-result", False):
            data = {"result": serialize_like_fastmcp([result])}
        else:
            data = serialize_like_fastmcp([result])
        jsonschema.validate(data, schema)


# ---------------------------------------------------------------------------
# Union regression guard (D-05, covers SC-3)
# ---------------------------------------------------------------------------


class TestUnionRegressionGuard:
    """Union types must not degrade to {"type":"object","additionalProperties":true}."""

    def test_frequency_branches_have_properties_and_const(self) -> None:
        """Each Frequency union branch must expose properties with a const type discriminator."""
        schema = TypeAdapter(Frequency).json_schema(mode="serialization")
        defs = schema.get("$defs", {})

        assert len(defs) == 9, f"Expected 9 $defs branches, got {len(defs)}: {list(defs)}"

        for name, branch in defs.items():
            assert "properties" in branch, (
                f"${name} lost its properties -- likely erased by @model_serializer. Got: {branch}"
            )
            type_prop = branch["properties"].get("type", {})
            assert "const" in type_prop, (
                f"${name}.type missing 'const' constraint -- discriminator gone. Got: {type_prop}"
            )

    def test_end_condition_branches_have_properties(self) -> None:
        """EndCondition union branches must have properties, not just {type: object}."""
        schema = TypeAdapter(EndCondition).json_schema(mode="serialization")

        # EndCondition uses anyOf (no discriminator). Branches may be inline or in $defs.
        defs = schema.get("$defs", {})
        any_of = schema.get("anyOf", [])

        # Resolve all branch schemas (inline or via $ref)
        branches: list[dict[str, Any]] = []
        for entry in any_of:
            if "$ref" in entry:
                ref_name = entry["$ref"].split("/")[-1]
                branches.append(defs[ref_name])
            else:
                branches.append(entry)

        assert len(branches) == 2, f"Expected 2 EndCondition branches, got {len(branches)}"
        for branch in branches:
            assert "properties" in branch, (
                f"EndCondition branch lost its properties -- likely erased by "
                f"@model_serializer. Got: {branch}"
            )
            # Must not be the erased form
            assert branch != {"type": "object", "additionalProperties": True}, (
                f"EndCondition branch degraded to bare object. Got: {branch}"
            )

    def test_no_erased_union_in_tool_schemas(self) -> None:
        """No $defs entry in any tool schema should be the erased {type:object} form."""
        erased_form = {"type": "object", "additionalProperties": True}

        for tool_name, return_type in _REGRESSION_GUARD_TYPES.items():
            schema = TypeAdapter(return_type).json_schema(mode="serialization")
            defs = schema.get("$defs", {})
            for def_name, def_schema in defs.items():
                assert def_schema != erased_form, (
                    f"Tool '{tool_name}' has erased $defs entry '{def_name}' -- "
                    f"likely caused by @model_serializer returning dict[str, Any]"
                )


# ---------------------------------------------------------------------------
# Naming convention enforcement (D-06, covers SC-4)
# ---------------------------------------------------------------------------

WRITE_SUFFIXES = ("Command", "Result", "RepoPayload", "RepoResult", "Action", "Spec")

# models/ classes exempt from "no write-side suffix" check:
# Private/internal base classes are already filtered by leading underscore.
MODELS_EXEMPT: set[str] = {
    "OmniFocusBaseModel",
    "OmniFocusEntity",
    "ActionableEntity",
}

# contracts/ classes exempt from "must have write-side suffix" check:
CONTRACTS_EXEMPT: set[str] = {
    "CommandModel",
    "EditTaskActions",
}


def _scan_package_models(package_name: str) -> list[tuple[str, type]]:
    """Discover all public Pydantic BaseModel subclasses in a package."""
    pkg = importlib.import_module(package_name)
    results: list[tuple[str, type]] = []
    for _importer, modname, _ispkg in pkgutil.walk_packages(
        pkg.__path__, prefix=f"{package_name}."
    ):
        mod = importlib.import_module(modname)
        for name, obj in inspect.getmembers(mod, inspect.isclass):
            if (
                issubclass(obj, BaseModel)
                and obj is not BaseModel
                and obj.__module__ == modname
                and not name.startswith("_")
            ):
                results.append((name, obj))
    return results


class TestNamingConvention:
    """Programmatic enforcement of models/ vs contracts/ naming rules."""

    def test_models_package_has_no_write_suffixes(self) -> None:
        """No public class in models/ should end with a write-side suffix."""
        models = _scan_package_models("omnifocus_operator.models")
        violations = []
        for name, _cls in models:
            if name in MODELS_EXEMPT:
                continue
            if any(name.endswith(suffix) for suffix in WRITE_SUFFIXES):
                violations.append(name)
        assert not violations, (
            f"models/ classes with write-side suffixes "
            f"(see docs/architecture.md naming taxonomy): {violations}"
        )

    def test_contracts_package_uses_recognized_suffixes(self) -> None:
        """Every public class in contracts/ must end with a recognized suffix."""
        contracts = _scan_package_models("omnifocus_operator.contracts")
        violations = []
        for name, _cls in contracts:
            if name in CONTRACTS_EXEMPT:
                continue
            if not any(name.endswith(suffix) for suffix in WRITE_SUFFIXES):
                violations.append(name)
        assert not violations, (
            f"contracts/ classes missing recognized suffix "
            f"(see docs/architecture.md naming taxonomy). "
            f"Expected one of: {WRITE_SUFFIXES}. Violations: {violations}"
        )
