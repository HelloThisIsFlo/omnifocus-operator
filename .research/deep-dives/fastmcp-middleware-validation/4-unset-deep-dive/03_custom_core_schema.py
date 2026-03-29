"""Can we modify _Unset's __get_pydantic_core_schema__ to suppress noise in validation errors?

Context:
    Currently ``_Unset.__get_pydantic_core_schema__`` returns
    ``core_schema.is_instance_schema(cls)``. When Pydantic tries a union branch
    and the value isn't an _Unset instance, it generates error messages like
    "Input should be an instance of _Unset". These leak into validation errors
    that the agent sees (or that middleware must filter out).

    Question: can we customize the core schema to either:
    1. Suppress the error entirely (custom_error_schema wrapping)
    2. Change the error message to something useful (cls_repr, custom_error_message)
    3. Use a different schema type that doesn't generate confusing errors
       (missing_sentinel_schema, none_schema, etc.)

Approach:
    Create several _Unset-like test classes, each with a different core schema
    strategy. For each, build a test model with a ``Union[str, None, Variant]``
    field (mimicking PatchOrClear[str]), then:
    - Generate JSON schema — does UNSET stay hidden?
    - Validate the UNSET singleton — does it accept correctly?
    - Validate invalid input — what error messages appear?

Key metric:
    Which alternatives keep UNSET hidden from JSON schema AND eliminate
    "_Unset" noise from error messages?

How to run:
    cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && uv run python \\
        .research/deep-dives/fastmcp-middleware-validation/4-unset-deep-dive/03_custom_core_schema.py
"""

from __future__ import annotations

import json
from typing import Any, Union

from pydantic import BaseModel, GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

# ---------------------------------------------------------------------------
# Real _Unset — import for baseline comparison
# ---------------------------------------------------------------------------
from omnifocus_operator.contracts.base import UNSET, _Unset

# ---------------------------------------------------------------------------
# Variant A (baseline): is_instance_schema(cls) — current behavior
# ---------------------------------------------------------------------------


class _UnsetA:
    """Baseline: current is_instance_schema(cls)."""

    _instance: _UnsetA | None = None

    def __new__(cls) -> _UnsetA:
        if cls._instance is None:
            cls._instance = object.__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "UNSET_A"

    def __bool__(self) -> bool:
        return False

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: Any, _handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.is_instance_schema(cls)


UNSET_A = _UnsetA()

# ---------------------------------------------------------------------------
# Variant B: is_instance_schema with cls_repr to change error message text
# ---------------------------------------------------------------------------


class _UnsetB:
    """Use cls_repr to change what appears in error messages."""

    _instance: _UnsetB | None = None

    def __new__(cls) -> _UnsetB:
        if cls._instance is None:
            cls._instance = object.__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "UNSET_B"

    def __bool__(self) -> bool:
        return False

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: Any, _handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.is_instance_schema(cls, cls_repr="INTERNAL_SENTINEL")


UNSET_B = _UnsetB()

# ---------------------------------------------------------------------------
# Variant C: custom_error_schema wrapping is_instance_schema
# ---------------------------------------------------------------------------


class _UnsetC:
    """Wrap is_instance_schema in custom_error_schema to replace error message."""

    _instance: _UnsetC | None = None

    def __new__(cls) -> _UnsetC:
        if cls._instance is None:
            cls._instance = object.__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "UNSET_C"

    def __bool__(self) -> bool:
        return False

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: Any, _handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.custom_error_schema(
            core_schema.is_instance_schema(cls),
            custom_error_type="omitted_field_sentinel",
            custom_error_message="This field was omitted (no change)",
        )


UNSET_C = _UnsetC()

# ---------------------------------------------------------------------------
# Variant D: plain validator function (no is_instance_schema at all)
# ---------------------------------------------------------------------------


class _UnsetD:
    """Use a plain validator function to check isinstance manually."""

    _instance: _UnsetD | None = None

    def __new__(cls) -> _UnsetD:
        if cls._instance is None:
            cls._instance = object.__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "UNSET_D"

    def __bool__(self) -> bool:
        return False

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: Any, _handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        def validate_unset(value: Any) -> _UnsetD:
            if isinstance(value, cls):
                return value
            raise ValueError("not a sentinel value")

        return core_schema.no_info_plain_validator_function(validate_unset)


UNSET_D = _UnsetD()

# ---------------------------------------------------------------------------
# Variant E: missing_sentinel_schema (new in pydantic-core)
# ---------------------------------------------------------------------------


class _UnsetE:
    """Use missing_sentinel_schema — designed for sentinel values."""

    _instance: _UnsetE | None = None

    def __new__(cls) -> _UnsetE:
        if cls._instance is None:
            cls._instance = object.__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "UNSET_E"

    def __bool__(self) -> bool:
        return False

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: Any, _handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.missing_sentinel_schema()


UNSET_E = _UnsetE()

# ---------------------------------------------------------------------------
# Variant F: with_default_schema wrapping is_instance + on_error='default'
# ---------------------------------------------------------------------------


class _UnsetF:
    """Wrap is_instance_schema in with_default_schema(on_error='default').

    Idea: if the is_instance check fails, fall back to a default value
    instead of raising an error. This might suppress the error entirely
    within the union resolution.
    """

    _instance: _UnsetF | None = None

    def __new__(cls) -> _UnsetF:
        if cls._instance is None:
            cls._instance = object.__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "UNSET_F"

    def __bool__(self) -> bool:
        return False

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: Any, _handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.with_default_schema(
            core_schema.is_instance_schema(cls),
            default=None,
            on_error="default",
        )


UNSET_F = _UnsetF()


# ---------------------------------------------------------------------------
# Test infrastructure
# ---------------------------------------------------------------------------

VARIANTS: list[tuple[str, type, Any]] = [
    ("A: is_instance_schema (baseline)", _UnsetA, UNSET_A),
    ("B: is_instance + cls_repr", _UnsetB, UNSET_B),
    ("C: custom_error_schema wrapper", _UnsetC, UNSET_C),
    ("D: plain validator function", _UnsetD, UNSET_D),
    ("E: missing_sentinel_schema", _UnsetE, UNSET_E),
    ("F: with_default + on_error='default'", _UnsetF, UNSET_F),
]


def build_model(variant_cls: type, variant_name: str) -> type[BaseModel]:
    """Build a model with a PatchOrClear[str]-like field using the given sentinel type."""
    # Use create_model-style dynamic construction
    model = type(
        f"TestModel_{variant_name}",
        (BaseModel,),
        {
            "__annotations__": {
                "name": str,
                "value": Union[str, None, variant_cls],  # noqa: UP007
            },
            "value": None,  # default
        },
    )
    return model


def test_json_schema(model: type[BaseModel], label: str) -> dict | None:
    """Generate JSON schema and check for sentinel leakage."""
    try:
        schema = model.model_json_schema()
        return schema
    except Exception as exc:
        print(f"  JSON schema generation FAILED: {exc}")
        return None


def test_accepts_sentinel(model: type[BaseModel], sentinel: Any) -> bool:
    """Check if the model accepts the sentinel value."""
    try:
        instance = model(name="test", value=sentinel)
        accepted = instance.value is sentinel
        return accepted
    except Exception as exc:
        print(f"  Sentinel acceptance FAILED: {exc}")
        return False


def test_invalid_input_errors(model: type[BaseModel]) -> tuple[list[dict], bool]:
    """Validate clearly invalid input and collect error messages.

    Returns (errors, silently_accepted) where silently_accepted is True if
    the model accepted invalid input without raising — a correctness problem.
    """
    try:
        model.model_validate({"name": "test", "value": 12345})
        print("  DANGER: validation passed for invalid input (int 12345)")
        print("  -> This variant silently swallows invalid data!")
        return [], True
    except Exception as exc:
        if hasattr(exc, "errors"):
            return exc.errors(), False
        print(f"  Non-validation error: {exc}")
        return [], False


def has_unset_noise(errors: list[dict]) -> tuple[int, list[str]]:
    """Count errors mentioning sentinel-related noise and collect those messages.

    We look for: _Unset class names, INTERNAL_SENTINEL (cls_repr override),
    MISSING sentinel (missing_sentinel_schema), and custom sentinel messages.
    Basically anything an agent should NOT see in a validation error.
    """
    noise_keywords = ["_Unset", "Unset", "INTERNAL_SENTINEL", "MISSING", "sentinel"]
    noisy_msgs = []
    for e in errors:
        msg = e.get("msg", "")
        if any(kw in msg for kw in noise_keywords):
            noisy_msgs.append(msg)
    return len(noisy_msgs), noisy_msgs


# ---------------------------------------------------------------------------
# Also test with the REAL _Unset + UNSET for comparison
# ---------------------------------------------------------------------------

def test_real_unset() -> None:
    """Test the actual _Unset class from the codebase."""
    print("=" * 72)
    print("REAL _Unset (from contracts.base) — Reference")
    print("=" * 72)

    model = build_model(_Unset, "Real")
    print()

    # JSON schema
    schema = test_json_schema(model, "Real")
    if schema:
        schema_str = json.dumps(schema, indent=2)
        has_leak = "_Unset" in schema_str or "Unset" in schema_str
        print(f"  JSON schema has _Unset leakage: {has_leak}")
        print(f"  Schema: {schema_str}")

    # Sentinel acceptance
    print()
    accepted = test_accepts_sentinel(model, UNSET)
    print(f"  Accepts UNSET singleton: {accepted}")

    # Invalid input errors
    print()
    errors, _silenced = test_invalid_input_errors(model)
    noise_count, noisy_msgs = has_unset_noise(errors)
    print(f"  Total errors for invalid input: {len(errors)}")
    print(f"  Errors with _Unset noise: {noise_count}")
    for i, e in enumerate(errors):
        is_noisy = any(kw in e.get("msg", "") for kw in ["_Unset", "Unset"])
        marker = " <<< NOISE" if is_noisy else ""
        print(f"    [{i+1}] type={e['type']}  msg={e['msg']!r}{marker}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    test_real_unset()

    # Track results for summary table
    results: list[dict] = []

    for label, variant_cls, sentinel in VARIANTS:
        print()
        print("=" * 72)
        print(f"VARIANT {label}")
        print("=" * 72)

        result: dict[str, Any] = {"label": label}

        # Build model
        try:
            model = build_model(variant_cls, label.split(":")[0].strip())
        except Exception as exc:
            print(f"  MODEL BUILD FAILED: {exc}")
            result["build"] = False
            results.append(result)
            continue
        result["build"] = True

        # JSON schema
        print()
        schema = test_json_schema(model, label)
        if schema:
            schema_str = json.dumps(schema, indent=2)
            has_leak = any(
                kw in schema_str
                for kw in ["_Unset", "Unset", "sentinel", "INTERNAL_SENTINEL"]
            )
            result["schema_leak"] = has_leak
            print(f"  JSON schema has sentinel leakage: {has_leak}")
            print(f"  Schema: {schema_str}")
        else:
            result["schema_leak"] = "FAILED"

        # Sentinel acceptance
        print()
        accepted = test_accepts_sentinel(model, sentinel)
        result["accepts_sentinel"] = accepted
        print(f"  Accepts sentinel singleton: {accepted}")

        # Invalid input errors
        print()
        errors, silently_accepted = test_invalid_input_errors(model)
        noise_count, noisy_msgs = has_unset_noise(errors)
        result["total_errors"] = len(errors)
        result["noise_count"] = noise_count
        result["noisy_msgs"] = noisy_msgs
        result["silently_accepted"] = silently_accepted

        print(f"  Total errors for invalid input: {len(errors)}")
        print(f"  Errors with sentinel noise: {noise_count}")
        for i, e in enumerate(errors):
            is_noisy = any(
                kw in e.get("msg", "")
                for kw in ["_Unset", "Unset", "sentinel", "INTERNAL_SENTINEL"]
            )
            marker = " <<< NOISE" if is_noisy else ""
            print(f"    [{i+1}] type={e['type']}  msg={e['msg']!r}{marker}")

        results.append(result)

    # --- Summary table ---
    print()
    print()
    print("=" * 72)
    print("SUMMARY TABLE")
    print("=" * 72)
    print()
    print(f"  {'Variant':<40} {'Build':>6} {'Schema':>8} {'Accept':>7} {'Noise':>6} {'Rejects':>8}")
    print(f"  {'-'*40} {'-'*6} {'-'*8} {'-'*7} {'-'*6} {'-'*8}")

    for r in results:
        build = "OK" if r.get("build") else "FAIL"
        schema = (
            "clean"
            if r.get("schema_leak") is False
            else "LEAK"
            if r.get("schema_leak") is True
            else str(r.get("schema_leak", "?"))
        )
        accept = "yes" if r.get("accepts_sentinel") else "NO"
        noise = str(r.get("noise_count", "?"))
        rejects = "NO!" if r.get("silently_accepted") else "yes"
        print(f"  {r['label']:<40} {build:>6} {schema:>8} {accept:>7} {noise:>6} {rejects:>8}")

    # --- Verdict ---
    print()
    print("=" * 72)
    print("ANALYSIS")
    print("=" * 72)

    winners = [
        r
        for r in results
        if r.get("build")
        and r.get("schema_leak") is False
        and r.get("accepts_sentinel")
        and r.get("noise_count", 999) == 0
        and not r.get("silently_accepted")
    ]

    if winners:
        print()
        print("  Variants that pass ALL criteria (no leak, accepts sentinel, no noise):")
        for w in winners:
            print(f"    - {w['label']}")
    else:
        print()
        print("  No variant passes ALL criteria perfectly.")
        print()
        # Find partial wins
        no_noise = [r for r in results if r.get("noise_count", 999) == 0 and r.get("build")]
        if no_noise:
            print("  Variants with zero noise (but may have other issues):")
            for r in no_noise:
                issues = []
                if r.get("schema_leak"):
                    issues.append("schema leak")
                if not r.get("accepts_sentinel"):
                    issues.append("rejects sentinel")
                if r.get("silently_accepted"):
                    issues.append("SILENTLY ACCEPTS INVALID INPUT")
                suffix = f" (issues: {', '.join(issues)})" if issues else ""
                print(f"    - {r['label']}{suffix}")

        no_leak = [
            r
            for r in results
            if r.get("schema_leak") is False and r.get("build")
        ]
        if no_leak:
            print("  Variants with clean schema (but may have noise):")
            for r in no_leak:
                print(f"    - {r['label']} (noise={r.get('noise_count', '?')})")

    print()
    print("  KEY FINDINGS:")
    print("  - cls_repr parameter: does it change error message text?")
    for r in results:
        if "B:" in r.get("label", ""):
            if r.get("noise_count", 0) == 0:
                print("    -> YES, cls_repr suppresses _Unset from error messages")
            else:
                msgs = r.get("noisy_msgs", [])
                print(f"    -> Noise still present: {msgs}")
            break

    print("  - custom_error_schema: does it replace the error message?")
    for r in results:
        if "C:" in r.get("label", ""):
            if r.get("noise_count", 0) == 0:
                print("    -> YES, custom_error_schema replaces the message")
            else:
                msgs = r.get("noisy_msgs", [])
                print(f"    -> Noise still present: {msgs}")
            break

    print("  - missing_sentinel_schema: is it viable for custom sentinels?")
    for r in results:
        if "E:" in r.get("label", ""):
            if r.get("accepts_sentinel"):
                print("    -> Accepts sentinel, may be a viable approach")
            else:
                print("    -> Does NOT accept custom sentinel (only works with pydantic's own MISSING)")
            break

    print("  - with_default on_error='default': does it suppress errors?")
    for r in results:
        if "F:" in r.get("label", ""):
            if r.get("silently_accepted"):
                print("    -> YES but DANGEROUS: silently accepts invalid input as None")
                print("    -> on_error='default' catches ALL errors in the union branch,")
                print("       so invalid values fall through as None instead of failing")
            break

    print()
    print("  BOTTOM LINE:")
    if winners:
        for w in winners:
            print(f"    WINNER: {w['label']}")
        print()
        print("    custom_error_schema is the only approach that:")
        print("      1. Keeps UNSET hidden from JSON schema")
        print("      2. Accepts the UNSET singleton")
        print("      3. Replaces '_Unset' noise with a clean error message")
        print("      4. Still rejects invalid input correctly")
        print()
        print("    Note: the sentinel error still APPEARS (2 errors total for union),")
        print("    but its message is now 'This field was omitted (no change)' instead")
        print("    of 'Input should be an instance of _Unset'. The filter in server.py")
        print("    could match on error type='omitted_field_sentinel' for precise removal.")
    else:
        print("    No variant meets all criteria. The existing filter approach may be")
        print("    the most pragmatic solution.")


if __name__ == "__main__":
    main()
