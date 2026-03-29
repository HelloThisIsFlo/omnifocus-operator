"""Can Pydantic-level error customization produce agent-friendly errors at the source?

Question:
    Our _format_validation_errors() in server.py post-processes Pydantic
    ValidationErrors to rewrite them into clean, agent-friendly messages.
    Can we push that logic INTO Pydantic models so the errors come out
    clean without any post-processing?

    Pydantic features to test:
    1. field_validator with custom ValueError messages
    2. model_validator(mode="before") to intercept extra fields before extra="forbid"
    3. Custom validators on discriminated unions (frequency type)
    4. _Unset core schema customization (custom_error_type/message)

    For each: compare the raw Pydantic error to what _format_validation_errors
    produces today. Can we match (or beat) the quality without post-processing?

How to run:
    cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && uv run python \
        .research/deep-dives/fastmcp-middleware-validation/3-approaches/06_pydantic_custom_errors.py
"""

from __future__ import annotations

import json
from typing import Annotated, Any, Literal, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    GetCoreSchemaHandler,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic.alias_generators import to_camel
from pydantic_core import CoreSchema, core_schema

# ---------------------------------------------------------------------------
# Import real models for baseline comparison
# ---------------------------------------------------------------------------
from omnifocus_operator.contracts.base import UNSET, CommandModel, PatchOrClear, _Unset
from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand
from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand
from omnifocus_operator.models.repetition_rule import Frequency
from omnifocus_operator.server import _format_validation_errors

SEPARATOR = "=" * 72
THIN_SEP = "-" * 72

VALID_FREQUENCY_TYPES = (
    "minutely, hourly, daily, weekly, weekly_on_days, "
    "monthly, monthly_day_of_week, monthly_day_in_month, yearly"
)


def show_comparison(
    label: str,
    model_cls: type,
    data: dict[str, Any],
    *,
    custom_model_cls: type | None = None,
) -> None:
    """Validate data against both baseline and custom model, compare error output.

    If custom_model_cls is provided, validate against both and compare.
    Otherwise just show the baseline error + formatted output.
    """
    print(f"\n{SEPARATOR}")
    print(f"TEST: {label}")
    print(f"Input: {json.dumps(data, indent=2, default=str)}")
    print(SEPARATOR)

    # --- Baseline ---
    print(f"\n  BASELINE ({model_cls.__name__}):")
    try:
        model_cls.model_validate(data)
        print("    --> VALID (no error)")
        baseline_errors: list[dict] = []
    except ValidationError as exc:
        baseline_errors = exc.errors()
        formatted = _format_validation_errors(exc)
        print(f"    Raw error count: {len(baseline_errors)}")
        for i, e in enumerate(baseline_errors):
            is_noise = "_Unset" in e.get("msg", "")
            marker = " <<< NOISE (filtered by _format_validation_errors)" if is_noise else ""
            print(f"      [{i}] type={e['type']}  loc={e.get('loc')}  msg={e['msg']!r}{marker}")
        print(f"    After _format_validation_errors ({len(formatted)} msgs):")
        for msg in formatted:
            print(f"      -> {msg}")

    # --- Custom ---
    if custom_model_cls is not None:
        print(f"\n  CUSTOM ({custom_model_cls.__name__}):")
        try:
            custom_model_cls.model_validate(data)
            print("    --> VALID (no error)")
        except ValidationError as exc:
            custom_errors = exc.errors()
            print(f"    Raw error count: {len(custom_errors)}")
            for i, e in enumerate(custom_errors):
                is_noise = "_Unset" in e.get("msg", "")
                marker = " <<< NOISE" if is_noise else ""
                print(
                    f"      [{i}] type={e['type']}  loc={e.get('loc')}  msg={e['msg']!r}{marker}"
                )
            # Show which messages are ALREADY agent-friendly (no post-processing needed)
            clean_msgs = [e["msg"] for e in custom_errors if "_Unset" not in e.get("msg", "")]
            print(f"    Agent-visible messages (no post-processing): {len(clean_msgs)}")
            for msg in clean_msgs:
                print(f"      -> {msg}")
        except Exception as exc:
            print(f"    Non-validation error: {type(exc).__name__}: {exc}")


# ===========================================================================
# TEST 1: field_validator with custom ValueError messages
# ===========================================================================

def test_1_field_validator() -> None:
    """Can field_validator produce clean error messages for type mismatches?"""
    print(f"\n\n{'#' * 72}")
    print("# TEST 1: field_validator with custom ValueError messages")
    print(f"{'#' * 72}")

    class AddTaskCustomName(CommandModel):
        """AddTaskCommand variant with a custom field_validator for 'name'."""

        name: str
        parent: str | None = None

        @field_validator("name", mode="before")
        @classmethod
        def validate_name(cls, v: Any) -> str:
            if not isinstance(v, str):
                raise ValueError(f"name must be a string, got {type(v).__name__}")
            if not v.strip():
                raise ValueError("name cannot be empty")
            return v

    # Test 1a: Wrong type for name
    show_comparison(
        "1a: name receives int instead of string",
        AddTaskCommand,
        {"name": 123},
        custom_model_cls=AddTaskCustomName,
    )

    # Test 1b: Empty name
    show_comparison(
        "1b: name is empty string",
        AddTaskCommand,
        {"name": ""},
        custom_model_cls=AddTaskCustomName,
    )

    # Test 1c: name missing entirely
    show_comparison(
        "1c: name field missing",
        AddTaskCommand,
        {"parent": "someId"},
        custom_model_cls=AddTaskCustomName,
    )

    print(f"\n{THIN_SEP}")
    print("  VERDICT (Test 1):")
    print("    field_validator CAN produce clean custom messages for value-level checks.")
    print("    But 'missing field' errors come from Pydantic core, not the validator.")
    print("    The validator only runs if the field IS present.")


# ===========================================================================
# TEST 2: Customizing "Extra inputs are not permitted" message
# ===========================================================================

def test_2_extra_fields() -> None:
    """Can we customize the extra="forbid" error message?"""
    print(f"\n\n{'#' * 72}")
    print("# TEST 2: Customizing 'Extra inputs are not permitted'")
    print(f"{'#' * 72}")

    # Approach 2a: model_validator(mode="before") checks for unknown fields
    class AddTaskCustomExtra(CommandModel):
        """Intercept unknown fields before extra='forbid' kicks in."""

        name: str
        parent: str | None = None

        @model_validator(mode="before")
        @classmethod
        def check_unknown_fields(cls, data: Any) -> Any:
            if isinstance(data, dict):
                known = set(cls.model_fields.keys())
                # Also check camelCase aliases
                alias_map = {}
                for field_name, field_info in cls.model_fields.items():
                    if field_info.alias:
                        alias_map[field_info.alias] = field_name
                    # Also generate camelCase alias
                    alias_map[to_camel(field_name)] = field_name

                for key in data:
                    if key not in known and key not in alias_map:
                        raise ValueError(f"Unknown field '{key}'")
            return data

    show_comparison(
        "2a: model_validator intercepts unknown fields before extra='forbid'",
        AddTaskCommand,
        {"name": "Test", "bogusField": "value", "anotherBad": 42},
        custom_model_cls=AddTaskCustomExtra,
    )

    # Approach 2b: Does model_validator fire INSTEAD of or BEFORE extra="forbid"?
    # If both fire, we get duplicate errors.
    show_comparison(
        "2b: Single unknown field -- does model_validator prevent extra_forbidden?",
        AddTaskCommand,
        {"name": "Test", "unknownField": "x"},
        custom_model_cls=AddTaskCustomExtra,
    )

    print(f"\n{THIN_SEP}")
    print("  VERDICT (Test 2):")
    print("    model_validator(mode='before') fires BEFORE field validation.")
    print("    If it raises, Pydantic stops -- no extra_forbidden error.")
    print("    BUT: it raises a SINGLE ValueError for the first unknown field,")
    print("    unlike extra='forbid' which reports ALL unknown fields.")
    print("    We'd need to collect all unknowns and raise a single ValueError")
    print("    with all of them (or raise multiple -- but ValueError is singular).")


# ===========================================================================
# TEST 3: Customizing the discriminated union error for frequency
# ===========================================================================

def test_3_discriminated_union() -> None:
    """Can we customize the 'union_tag_invalid' error for frequency type?"""
    print(f"\n\n{'#' * 72}")
    print("# TEST 3: Customizing discriminated union error (frequency)")
    print(f"{'#' * 72}")

    # Approach 3a: Wrap Frequency in a field_validator
    class RepRuleCustomFreq(CommandModel):
        """RepetitionRuleAddSpec variant with custom frequency validator."""

        frequency: Frequency
        schedule: str
        based_on: str

        @field_validator("frequency", mode="before")
        @classmethod
        def validate_frequency_type(cls, v: Any) -> Any:
            if isinstance(v, dict):
                freq_type = v.get("type")
                if freq_type is None:
                    raise ValueError(
                        "frequency must include a 'type' field -- "
                        f"valid types: {VALID_FREQUENCY_TYPES}"
                    )
                valid = {
                    "minutely", "hourly", "daily", "weekly", "weekly_on_days",
                    "monthly", "monthly_day_of_week", "monthly_day_in_month", "yearly",
                }
                if freq_type not in valid:
                    raise ValueError(
                        f"Invalid frequency type '{freq_type}' -- "
                        f"valid types: {VALID_FREQUENCY_TYPES}"
                    )
            return v

    # Use AddTaskCommand as baseline (it has repetitionRule -> frequency)
    show_comparison(
        "3a: Invalid frequency type via field_validator",
        AddTaskCommand,
        {
            "name": "Test",
            "repetitionRule": {
                "frequency": {"type": "biweekly", "interval": 1},
                "schedule": "regularly",
                "basedOn": "due_date",
            },
        },
        custom_model_cls=RepRuleCustomFreq,
    )

    # 3b: Missing type field entirely
    show_comparison(
        "3b: Frequency dict without 'type' field",
        AddTaskCommand,
        {
            "name": "Test",
            "repetitionRule": {
                "frequency": {"interval": 2},
                "schedule": "regularly",
                "basedOn": "due_date",
            },
        },
        custom_model_cls=RepRuleCustomFreq,
    )

    # Approach 3c: __get_pydantic_core_schema__ on a custom Frequency type
    # Can we wrap the tagged union in custom_error_schema?
    print(f"\n{THIN_SEP}")
    print("  Approach 3c: Custom core schema on Frequency union")
    print(THIN_SEP)

    class CustomFrequency:
        """Attempt to override core schema for the discriminated union."""

        @classmethod
        def __get_pydantic_core_schema__(
            cls, source_type: Any, handler: GetCoreSchemaHandler
        ) -> CoreSchema:
            # Get the original tagged-union schema from Frequency
            from omnifocus_operator.models.repetition_rule import (
                DailyFrequency,
                HourlyFrequency,
                MinutelyFrequency,
                MonthlyDayInMonthFrequency,
                MonthlyDayOfWeekFrequency,
                MonthlyFrequency,
                WeeklyFrequency,
                WeeklyOnDaysFrequency,
                YearlyFrequency,
            )

            # Build a tagged union schema manually with custom error
            choices: dict[str, CoreSchema] = {}
            for freq_cls in [
                MinutelyFrequency, HourlyFrequency, DailyFrequency,
                WeeklyFrequency, WeeklyOnDaysFrequency, MonthlyFrequency,
                MonthlyDayOfWeekFrequency, MonthlyDayInMonthFrequency,
                YearlyFrequency,
            ]:
                schema = handler.generate_schema(freq_cls)
                type_val = freq_cls.model_fields["type"].default
                choices[type_val] = schema

            tagged = core_schema.tagged_union_schema(
                choices,
                discriminator="type",
                custom_error_type="value_error",
                custom_error_message=(
                    f"Invalid frequency type -- valid types: {VALID_FREQUENCY_TYPES}"
                ),
            )
            return tagged

    try:
        # Build a model using this custom schema provider
        FrequencyCustom = Annotated[
            Union[  # noqa: UP007
                Any,  # placeholder; the core schema override handles dispatch
            ],
            CustomFrequency,
        ]

        class RepRuleCustomSchema(BaseModel):
            model_config = ConfigDict(
                alias_generator=to_camel,
                validate_by_name=True,
                validate_by_alias=True,
            )
            frequency: Any  # Will be validated via the approach below

        # Actually, let's try the tagged_union_schema approach directly
        # by building a model with __get_validators__ override.
        # This is exploratory -- let's see what happens.

        # Simpler approach: build model dynamically
        class RepRuleTaggedUnion(BaseModel):
            model_config = ConfigDict(
                alias_generator=to_camel,
                validate_by_name=True,
                validate_by_alias=True,
                extra="forbid",
            )
            frequency: Annotated[Frequency, Field(discriminator="type")]

        # Test invalid type
        try:
            RepRuleTaggedUnion.model_validate({"frequency": {"type": "biweekly"}})
        except ValidationError as exc:
            print(f"    Standard tagged union error:")
            for e in exc.errors():
                print(f"      type={e['type']}  msg={e['msg']!r}")
                print(f"      ctx={e.get('ctx')}")
        except Exception as exc:
            print(f"    Error: {type(exc).__name__}: {exc}")

        # Now try wrapping Frequency's schema with custom_error_message
        # We need to check if tagged_union_schema supports custom_error_type
        print(f"\n    Testing core_schema.tagged_union_schema with custom_error_message:")

        from omnifocus_operator.models.repetition_rule import (
            DailyFrequency,
            HourlyFrequency,
            MinutelyFrequency,
            MonthlyDayInMonthFrequency,
            MonthlyDayOfWeekFrequency,
            MonthlyFrequency,
            WeeklyFrequency,
            WeeklyOnDaysFrequency,
            YearlyFrequency,
        )

        freq_classes = [
            MinutelyFrequency, HourlyFrequency, DailyFrequency,
            WeeklyFrequency, WeeklyOnDaysFrequency, MonthlyFrequency,
            MonthlyDayOfWeekFrequency, MonthlyDayInMonthFrequency,
            YearlyFrequency,
        ]
        choices = {}
        for fc in freq_classes:
            type_val = fc.model_fields["type"].default
            choices[type_val] = fc.__pydantic_core_schema__

        tagged = core_schema.tagged_union_schema(
            choices,
            discriminator="type",
            custom_error_type="value_error",
            custom_error_message=f"Invalid frequency type -- valid types: {VALID_FREQUENCY_TYPES}",
        )
        print(f"    tagged_union_schema built successfully")
        print(f"    Schema keys: {list(tagged.keys())}")
        print(f"    custom_error_type: {tagged.get('custom_error_type')}")
        print(f"    custom_error_message: {tagged.get('custom_error_message')}")

        # Build a validator from this schema and test it
        from pydantic import TypeAdapter

        adapter = TypeAdapter(Frequency)

        # Override with custom tagged union -- need a new TypeAdapter
        # TypeAdapter doesn't accept raw core_schema directly, but we can
        # test via a model that uses __get_pydantic_core_schema__
        class FrequencyWithCustomError:
            @classmethod
            def __get_pydantic_core_schema__(
                cls, source_type: Any, handler: GetCoreSchemaHandler
            ) -> CoreSchema:
                return tagged

        CustomFreqType = Annotated[Any, FrequencyWithCustomError]

        class TestFreqModel(BaseModel):
            frequency: CustomFreqType

        try:
            TestFreqModel.model_validate({"frequency": {"type": "biweekly"}})
        except ValidationError as exc:
            print(f"\n    Custom tagged_union_schema error output:")
            for e in exc.errors():
                print(f"      type={e['type']}  msg={e['msg']!r}")
                print(f"      ctx={e.get('ctx')}")
            print(f"    --> Compare: does custom_error_message appear in msg?")

    except Exception as exc:
        print(f"    FAILED: {type(exc).__name__}: {exc}")
        import traceback
        traceback.print_exc()

    print(f"\n{THIN_SEP}")
    print("  VERDICT (Test 3):")
    print("    field_validator(mode='before') CAN intercept and rewrite frequency errors.")
    print("    It fires BEFORE the discriminated union parser, so we can pre-validate")
    print("    the 'type' field and raise a clean ValueError.")
    print("    tagged_union_schema's custom_error_type/message: tested above.")


# ===========================================================================
# TEST 4: Suppressing _Unset noise at the Pydantic level
# ===========================================================================

def test_4_unset_noise() -> None:
    """Can we make _Unset produce zero noise in validation errors?"""
    print(f"\n\n{'#' * 72}")
    print("# TEST 4: Suppressing _Unset noise at the Pydantic level")
    print(f"{'#' * 72}")

    # The problem: when validating EditTaskCommand with invalid input for a
    # PatchOrClear field, Pydantic tries all union branches including _Unset
    # and reports "Input should be an instance of _Unset" as a sub-error.
    # _format_validation_errors filters these out by checking '_Unset' in msg.

    # Approach 4a: Use custom_error_schema to change the _Unset error message
    class _UnsetCustomError:
        """_Unset variant with custom_error_schema to suppress noise."""

        _instance: _UnsetCustomError | None = None

        def __new__(cls) -> _UnsetCustomError:
            if cls._instance is None:
                cls._instance = object.__new__(cls)
            return cls._instance

        def __repr__(self) -> str:
            return "UNSET"

        def __bool__(self) -> bool:
            return False

        @classmethod
        def __get_pydantic_core_schema__(
            cls, _source_type: Any, _handler: GetCoreSchemaHandler
        ) -> CoreSchema:
            return core_schema.custom_error_schema(
                core_schema.is_instance_schema(cls),
                custom_error_type="omitted_field",
                custom_error_message="Field was omitted (this is an internal marker, not a real error)",
            )

    UNSET_CUSTOM = _UnsetCustomError()

    # Build test models
    PatchOrClearStr = Union[str, None, _Unset]  # noqa: UP007 -- baseline
    PatchOrClearStrCustom = Union[str, None, _UnsetCustomError]  # noqa: UP007

    class BaselineModel(BaseModel):
        model_config = ConfigDict(extra="forbid")
        id: str
        name: PatchOrClearStr = UNSET

    class CustomModel(BaseModel):
        model_config = ConfigDict(extra="forbid")
        id: str
        name: PatchOrClearStrCustom = UNSET_CUSTOM

    # Test 4a: Invalid value for PatchOrClear field
    show_comparison(
        "4a: Invalid type for PatchOrClear[str] field (int instead of str/None)",
        BaselineModel,
        {"id": "abc", "name": 12345},
        custom_model_cls=CustomModel,
    )

    # Test 4b: Does UNSET still work as default?
    print(f"\n{THIN_SEP}")
    print("  4b: UNSET as default value (field omitted)")
    print(THIN_SEP)

    baseline_ok = BaselineModel.model_validate({"id": "abc"})
    custom_ok = CustomModel.model_validate({"id": "abc"})
    print(f"    Baseline: name={baseline_ok.name!r}, is _Unset: {isinstance(baseline_ok.name, _Unset)}")
    print(f"    Custom:   name={custom_ok.name!r}, is _UnsetCustomError: {isinstance(custom_ok.name, _UnsetCustomError)}")

    # Test 4c: Can we make the error message something that's easily filterable
    # but NOT confusing if it leaks to the agent?
    print(f"\n{THIN_SEP}")
    print("  4c: What if we use a message that's agent-safe if it leaks?")
    print(THIN_SEP)

    class _UnsetSafeMsg:
        """_Unset variant with an agent-safe error message."""

        _instance: _UnsetSafeMsg | None = None

        def __new__(cls) -> _UnsetSafeMsg:
            if cls._instance is None:
                cls._instance = object.__new__(cls)
            return cls._instance

        def __repr__(self) -> str:
            return "UNSET"

        def __bool__(self) -> bool:
            return False

        @classmethod
        def __get_pydantic_core_schema__(
            cls, _source_type: Any, _handler: GetCoreSchemaHandler
        ) -> CoreSchema:
            # Use cls_repr to change what appears in the error message
            return core_schema.is_instance_schema(cls, cls_repr="OmittedField")

    UNSET_SAFE = _UnsetSafeMsg()

    PatchOrClearStrSafe = Union[str, None, _UnsetSafeMsg]  # noqa: UP007

    class SafeModel(BaseModel):
        model_config = ConfigDict(extra="forbid")
        id: str
        name: PatchOrClearStrSafe = UNSET_SAFE

    try:
        SafeModel.model_validate({"id": "abc", "name": 12345})
    except ValidationError as exc:
        print(f"    Error messages with cls_repr='OmittedField':")
        for e in exc.errors():
            has_unset = "_Unset" in e["msg"]
            has_omitted = "OmittedField" in e["msg"]
            print(f"      type={e['type']}  msg={e['msg']!r}")
            print(f"        Has '_Unset': {has_unset}  Has 'OmittedField': {has_omitted}")

    # Test 4d: Does custom_error_type change the error 'type' field?
    # This would let us filter by type instead of string-matching msg.
    print(f"\n{THIN_SEP}")
    print("  4d: Can we filter by error 'type' instead of string-matching 'msg'?")
    print(THIN_SEP)

    try:
        CustomModel.model_validate({"id": "abc", "name": 12345})
    except ValidationError as exc:
        for e in exc.errors():
            print(f"    type={e['type']!r}  msg={e['msg']!r}")
        custom_types = {e["type"] for e in exc.errors()}
        print(f"    Unique error types: {custom_types}")
        print(f"    Can filter by type=='omitted_field': {'omitted_field' in custom_types}")

    print(f"\n{THIN_SEP}")
    print("  VERDICT (Test 4):")
    print("    custom_error_schema: changes both 'type' and 'msg' fields.")
    print("    cls_repr: changes the msg text (replaces class name in message).")
    print("    Both approaches let us filter _Unset noise more reliably.")
    print("    custom_error_type is the cleanest: filter by e['type'] == 'omitted_field'")
    print("    instead of fragile string matching on e['msg'].")


# ===========================================================================
# SYNTHESIS: Can we eliminate _format_validation_errors entirely?
# ===========================================================================

def test_synthesis() -> None:
    """Full integration: build a model that produces clean errors without post-processing."""
    print(f"\n\n{'#' * 72}")
    print("# SYNTHESIS: Can we eliminate _format_validation_errors?")
    print(f"{'#' * 72}")

    # Build an EditTaskCommand-like model with ALL customizations applied:
    # 1. field_validator for value-level checks
    # 2. model_validator for unknown fields
    # 3. field_validator for frequency discrimination
    # 4. _Unset with custom_error_type for noise filtering

    class _UnsetClean:
        """_Unset with custom_error_type for reliable filtering."""

        _instance: _UnsetClean | None = None

        def __new__(cls) -> _UnsetClean:
            if cls._instance is None:
                cls._instance = object.__new__(cls)
            return cls._instance

        def __repr__(self) -> str:
            return "UNSET"

        def __bool__(self) -> bool:
            return False

        @classmethod
        def __get_pydantic_core_schema__(
            cls, _source_type: Any, _handler: GetCoreSchemaHandler
        ) -> CoreSchema:
            return core_schema.custom_error_schema(
                core_schema.is_instance_schema(cls),
                custom_error_type="omitted_field_sentinel",
                custom_error_message="(internal: omitted field marker)",
            )

    UNSET_CLEAN = _UnsetClean()

    PatchClean = Union[str, _UnsetClean]  # noqa: UP007
    PatchOrClearClean = Union[str, None, _UnsetClean]  # noqa: UP007

    class SynthEditCommand(BaseModel):
        """Simplified EditTaskCommand with all customizations."""

        model_config = ConfigDict(
            alias_generator=to_camel,
            validate_by_name=True,
            validate_by_alias=True,
            extra="forbid",
        )

        id: str
        name: PatchClean = UNSET_CLEAN
        note: PatchOrClearClean = UNSET_CLEAN
        lifecycle: Union[Literal["complete", "drop"], _UnsetClean] = UNSET_CLEAN  # noqa: UP007

        @model_validator(mode="before")
        @classmethod
        def check_unknown_fields(cls, data: Any) -> Any:
            """Intercept unknown fields with a clean message."""
            if isinstance(data, dict):
                known = set(cls.model_fields.keys())
                aliases = {to_camel(k) for k in known}
                all_known = known | aliases
                unknown = [k for k in data if k not in all_known]
                if unknown:
                    msgs = [f"Unknown field '{f}'" for f in unknown]
                    raise ValueError("; ".join(msgs))
            return data

        @field_validator("lifecycle", mode="before")
        @classmethod
        def validate_lifecycle(cls, v: Any) -> Any:
            if isinstance(v, _UnsetClean):
                return v
            if isinstance(v, str) and v in ("complete", "drop"):
                return v
            raise ValueError(f"Invalid lifecycle action '{v}' -- must be 'complete' or 'drop'")

    def format_clean(exc: ValidationError) -> list[str]:
        """Minimal post-processor: ONLY filters sentinel noise by type."""
        return [
            e["msg"]
            for e in exc.errors()
            if e["type"] != "omitted_field_sentinel"
        ]

    # Test cases
    test_cases: list[tuple[str, dict[str, Any]]] = [
        ("Unknown field", {"id": "abc", "bogus": "value"}),
        ("Invalid lifecycle", {"id": "abc", "lifecycle": "archive"}),
        ("Wrong type for name", {"id": "abc", "name": 123}),
        ("Missing required field 'id'", {"name": "test"}),
        ("Multiple errors", {"lifecycle": "bad", "bogus": "x"}),
    ]

    for label, data in test_cases:
        print(f"\n{THIN_SEP}")
        print(f"  Synth test: {label}")
        print(f"  Input: {json.dumps(data, default=str)}")
        print(THIN_SEP)

        # Baseline (real model)
        try:
            EditTaskCommand.model_validate(data)
            print("    Baseline: VALID")
        except ValidationError as exc:
            formatted = _format_validation_errors(exc)
            print(f"    Baseline (_format_validation_errors): {formatted}")

        # Custom model
        try:
            SynthEditCommand.model_validate(data)
            print("    Custom: VALID")
        except ValidationError as exc:
            clean = format_clean(exc)
            raw_count = len(exc.errors())
            print(f"    Custom (format_clean, {raw_count} raw -> {len(clean)} clean): {clean}")

    # --- Final comparison ---
    print(f"\n\n{SEPARATOR}")
    print("FINAL ANALYSIS: Can we eliminate _format_validation_errors?")
    print(SEPARATOR)
    print()
    print("  What Pydantic-level customization CAN do:")
    print("    1. field_validator: Custom messages for type/value checks (name, lifecycle)")
    print("    2. model_validator(mode='before'): Clean 'Unknown field' messages")
    print("    3. field_validator on frequency: Pre-validate discriminator before union dispatch")
    print("    4. custom_error_type on _Unset: Filter by type instead of string matching")
    print()
    print("  What still requires post-processing:")
    print("    - _Unset sentinel noise: STILL generated by union branch attempts.")
    print("      Even with custom_error_type, the errors are still PRESENT --")
    print("      we just filter them more reliably (by type, not string matching).")
    print("    - Multiple union branch failures: Pydantic reports ALL failed branches.")
    print("      We can't prevent _Unset branch from being attempted.")
    print()
    print("  Can we ELIMINATE _format_validation_errors?")
    print("    NO -- but we can SIMPLIFY it significantly:")
    print()
    print("    BEFORE (current):")
    print("      - String-match '_Unset' in msg (fragile)")
    print("      - Pattern-match on error type + location for extra_forbidden")
    print("      - Pattern-match on error type + location for union_tag_invalid")
    print("      - Pattern-match on error type + location for literal_error")
    print()
    print("    AFTER (with Pydantic customization):")
    print("      - Filter e['type'] == 'omitted_field_sentinel' (robust, no string matching)")
    print("      - Everything else: just use e['msg'] directly (already agent-friendly)")
    print()
    print("  TRADE-OFF:")
    print("    + Error messages are clean at the source")
    print("    + _format_validation_errors becomes a trivial filter (1 line)")
    print("    + No fragile string matching")
    print("    - Every CommandModel needs validators (boilerplate)")
    print("    - model_validator for extra fields duplicates extra='forbid' logic")
    print("    - field_validators couple model definitions to error message strings")
    print("    - Validators add runtime overhead (small but non-zero)")
    print()
    print("  RECOMMENDATION:")
    print("    Hybrid approach:")
    print("    1. Change _Unset to use custom_error_type -- makes filtering robust")
    print("    2. Keep _format_validation_errors but simplify to type-based filtering")
    print("    3. DON'T add field/model validators just for error messages --")
    print("       the post-processor handles those patterns more cleanly")
    print("    4. DO add field_validators where they serve DUAL purpose")
    print("       (validation logic + clean messages, like frequency pre-validation)")


# ===========================================================================
# Main
# ===========================================================================

def main() -> None:
    test_1_field_validator()
    test_2_extra_fields()
    test_3_discriminated_union()
    test_4_unset_noise()
    test_synthesis()


if __name__ == "__main__":
    main()
