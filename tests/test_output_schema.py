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

from omnifocus_operator.contracts.use_cases.add.tasks import AddTaskResult
from omnifocus_operator.contracts.use_cases.edit.tasks import EditTaskResult
from omnifocus_operator.models import AllEntities, Project, Tag, Task
from omnifocus_operator.models.enums import BasedOn, Schedule
from omnifocus_operator.models.repetition_rule import (
    EndCondition,
    Frequency,
    RepetitionRule,
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
                "type": "weekly",
                "interval": 1,
                "onDays": ["MO", "WE", "FR"],
            },
            "schedule": "from_completion",
            "basedOn": "defer_date",
            "end": {"occurrences": 10},
        },
        "monthly_on": {
            "frequency": {
                "type": "monthly",
                "interval": 1,
                "on": {"second": "tuesday"},
            },
            "schedule": "regularly_with_catch_up",
            "basedOn": "due_date",
            "end": {"date": "2025-12-31"},
        },
        "monthly_on_dates": {
            "frequency": {
                "type": "monthly",
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
_TASK_MONTHLY_ON = Task.model_validate(
    make_model_task_dict(
        id="task-mon",
        name="Monthly On Task",
        repetitionRule=_make_repetition_rule_dict("monthly_on"),
    )
)
_TASK_MONTHLY_ON_DATES = Task.model_validate(
    make_model_task_dict(
        id="task-mod",
        name="Monthly On Dates Task",
        repetitionRule=_make_repetition_rule_dict("monthly_on_dates"),
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
                id="task-mon",
                name="Monthly On Task",
                repetitionRule=_make_repetition_rule_dict("monthly_on"),
            ),
            make_model_task_dict(
                id="task-mod",
                name="Monthly On Dates Task",
                repetitionRule=_make_repetition_rule_dict("monthly_on_dates"),
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
        ["daily", "weekly_bare", "weekly_with_days", "monthly_on", "monthly_on_dates"],
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
        # EndByDate: monthly_on has end.date="2025-12-31"
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
                        repetitionRule=_make_repetition_rule_dict("monthly_on"),
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

    def test_interval_1_suppressed_in_serialized_output(self) -> None:
        """Frequency with interval=1 should omit interval from output."""
        rule = RepetitionRule(
            frequency=Frequency(type="daily", interval=1),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
        )
        data = serialize_like_fastmcp(rule)
        assert "interval" not in data["frequency"], (
            f"interval=1 should be suppressed in serialized output. Got: {data['frequency']}"
        )
        assert data["frequency"]["type"] == "daily"

    def test_interval_non_default_preserved_in_serialized_output(self) -> None:
        """Frequency with interval!=1 should include interval in serialized output."""
        rule = RepetitionRule(
            frequency=Frequency(type="daily", interval=3),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
        )
        data = serialize_like_fastmcp(rule)
        assert data["frequency"]["interval"] == 3, (
            f"interval=3 should be preserved in serialized output. Got: {data['frequency']}"
        )
        assert data["frequency"]["type"] == "daily"

    def test_interval_1_validates_against_output_schema(self) -> None:
        """Task with interval=1 frequency validates against outputSchema (interval omitted)."""
        task = Task.model_validate(
            make_model_task_dict(
                id="task-interval-1",
                name="Interval 1 Task",
                repetitionRule={
                    "frequency": {"type": "daily", "interval": 1},
                    "schedule": "regularly",
                    "basedOn": "due_date",
                },
            )
        )
        schema = _TOOL_SCHEMAS["get_task"]
        data = serialize_like_fastmcp(task)
        jsonschema.validate(data, schema)


# ---------------------------------------------------------------------------
# Union regression guard (D-05, covers SC-3)
# ---------------------------------------------------------------------------


class TestUnionRegressionGuard:
    """Union types must not degrade to {"type":"object","additionalProperties":true}."""

    def test_frequency_is_flat_model_with_type_enum(self) -> None:
        """Frequency schema must be a flat object with type enum."""
        schema = TypeAdapter(Frequency).json_schema(mode="serialization")

        # Flat model: no $defs branches (no discriminated union)
        assert "$defs" not in schema or len(schema.get("$defs", {})) == 0, (
            "Frequency should be a flat model without $defs branches. "
            f"Got $defs: {list(schema.get('$defs', {}).keys())}"
        )

        # Must be an object type with properties
        assert schema.get("type") == "object", (
            f"Frequency schema should be object type. Got: {schema}"
        )
        assert "properties" in schema, f"Frequency schema missing properties. Got: {schema}"

        # type field must have enum constraint with exactly 6 values
        type_prop = schema["properties"].get("type", {})
        assert "enum" in type_prop, (
            f"Frequency.type should have enum constraint (from Literal). Got: {type_prop}"
        )
        expected_types = ["minutely", "hourly", "daily", "weekly", "monthly", "yearly"]
        assert sorted(type_prop["enum"]) == sorted(expected_types), (
            f"Expected 6 frequency types {expected_types}, got: {type_prop['enum']}"
        )

        # Optional specialization fields must be present
        props = schema["properties"]
        assert "onDays" in props, "Missing onDays field in Frequency schema"
        assert "on" in props, "Missing on field in Frequency schema"
        assert "onDates" in props, "Missing onDates field in Frequency schema"

        # interval must have default of 1 (minimum enforced by @field_validator,
        # not visible in JSON Schema)
        interval_prop = props.get("interval", {})
        assert interval_prop.get("default") == 1, (
            f"Frequency.interval should have default=1. Got: {interval_prop}"
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

CONTRACT_SUFFIXES = ("Command", "Result", "RepoPayload", "RepoResult", "Action", "Spec", "Query")

# models/ classes exempt from "no contract suffix" check:
# Private/internal base classes are already filtered by leading underscore.
MODELS_EXEMPT: set[str] = {
    "OmniFocusBaseModel",
    "OmniFocusEntity",
    "ActionableEntity",
}

# contracts/ classes exempt from "must have contract suffix" check:
CONTRACTS_EXEMPT: set[str] = {
    "CommandModel",
    "EditTaskActions",
    "QueryModel",
    "StrictModel",
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

    def test_models_package_has_no_contract_suffixes(self) -> None:
        """No public class in models/ should end with a contract suffix."""
        models = _scan_package_models("omnifocus_operator.models")
        violations = []
        for name, _cls in models:
            if name in MODELS_EXEMPT:
                continue
            if any(name.endswith(suffix) for suffix in CONTRACT_SUFFIXES):
                violations.append(name)
        assert not violations, (
            f"models/ classes with contract suffixes (see docs/model-taxonomy.md): {violations}"
        )

    def test_contracts_package_uses_recognized_suffixes(self) -> None:
        """Every public class in contracts/ must end with a recognized suffix."""
        contracts = _scan_package_models("omnifocus_operator.contracts")
        violations = []
        for name, _cls in contracts:
            if name in CONTRACTS_EXEMPT:
                continue
            if not any(name.endswith(suffix) for suffix in CONTRACT_SUFFIXES):
                violations.append(name)
        assert not violations, (
            f"contracts/ classes missing recognized suffix "
            f"(see docs/model-taxonomy.md). "
            f"Expected one of: {CONTRACT_SUFFIXES}. Violations: {violations}"
        )
