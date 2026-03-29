# Phase 32: Read Model Rewrite - Research

**Researched:** 2026-03-28
**Domain:** Pydantic v2 discriminated unions, RRULE parsing, OmniFocus repetition model transformation
**Confidence:** HIGH

## Summary

This phase replaces the current 4-field `RepetitionRule` model (raw `ruleString`, `scheduleType`, `anchorDateKey`, `catchUpAutomatically`) with a structured model exposing parsed frequency data. The core work is: (1) a production RRULE parser derived from the spike, (2) 8 Pydantic frequency subtypes as a discriminated union, (3) new `RepetitionRule` model with `frequency`, `schedule`, `basedOn`, `end`, and (4) wiring both read paths (SQLite + bridge adapter) to call the parser.

The spike parser (`rrule_validator.py`, 79 tests) is directly portable but needs extension for MINUTELY/HOURLY frequencies and BYDAY positional prefix parsing (e.g., `2TU` = second Tuesday). The golden master operates at raw bridge format and is unaffected -- the transformation layer sits above it.

**Primary recommendation:** Create the `rrule/` module first (parser + models), test it independently with full coverage, then wire into both read paths and update model exports. The module is self-contained and Phase 33 (write path) depends on the types defined here.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Typed discriminated union -- each frequency type is its own Pydantic model with only its relevant fields. 8 subtypes using `Field(discriminator="type")`. Agent sees exactly what applies, no null-field noise.
- **D-02:** Field naming uses agent-friendly terms: `onDays` (weekly), `onDates` (monthly_day_in_month), `on` (monthly_day_of_week). Not RRULE-native terms.
- **D-03:** End condition: single-key dict following `moveTo` pattern: `{"date": "ISO-8601"}` or `{"occurrences": N}`. Omit field entirely for no end.
- **D-04:** MINUTELY and HOURLY parsed like any other frequency type -- simple `{type, interval}` objects.
- **D-05:** BYDAY positional prefix form only (`BYDAY=2TU`, `BYDAY=-1FR`). BYSETPOS as separate parameter not supported -- clear error if encountered.
- **D-06:** 3-value schedule enum: `regularly`, `regularly_with_catch_up`, `from_completion`. Derived from 2 SQLite columns. `from_completion + catchUp=true` = fail-fast error.
- **D-07:** Malformed RRULE strings fail-fast with ValueError and educational error message.
- **D-08:** Interval omitted when 1 (the default). Only appears in output when > 1.
- **D-09:** Clean break -- `ruleString` removed entirely, no transition period.
- **D-10:** Ordinals: first/second/third/fourth/fifth/last. Days: monday-sunday, plus weekday (MO-FR) and weekend_day (SA-SU). All lowercase.
- **D-11:** Repetition rule gets its own module, not inline in `common.py`.
- **D-12:** 30 golden master scenarios in `08-repetition/` already captured. Golden master operates at raw bridge layer -- unaffected by this transformation.

### Claude's Discretion
- RRULE utility function internal structure and wiring to both read paths
- Pydantic model names and ~~FrequencySpec~~ → Frequency hierarchy details
- Exact warning/error message wording (existing `agent_messages` patterns as style guide)
- Test structure and organization
- Exact module/package layout within the "own module" boundary

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| READ-01 | RepetitionRule read model exposes structured frequency fields instead of ruleString | Discriminated union pattern verified with Pydantic 2.12.5; 8 frequency subtypes map cleanly to RRULE FREQ values; serialization with `by_alias=True` produces correct camelCase output |
| READ-02 | All 8 frequency types correctly parsed from RRULE strings | Spike parser handles DAILY/WEEKLY/MONTHLY/YEARLY; needs MINUTELY/HOURLY extension (trivial -- same as DAILY) and BYDAY positional prefix parsing (regex verified); golden master has examples of all 8 types |
| READ-03 | Both SQLite and bridge read paths share a single rrule module | Both paths currently produce dicts that Pydantic validates; parser returns structured dict or model instance; both `_build_repetition_rule()` and `_adapt_repetition_rule()` call same parser |
| READ-04 | parse_rrule and build_rrule round-trip correctly for all frequency types | Spike already has round-trip validation; production version needs same pattern: parse -> build -> parse -> assert equal |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **SAFE-01/02:** All tests use `InMemoryBridge` or `SimulatorBridge`. No automated tests touch the real Bridge.
- **Service layer:** Method Object pattern for use cases; read delegations stay inline (this phase is read-only, so inline pass-throughs are fine)
- **Naming:** Write `the real Bridge` (two words) in comments, not the class name
- **UAT:** Feature phase -- focus on user-observable behavior (structured output)
- **Model base:** All models inherit from `OmniFocusBaseModel` (camelCase alias, validate_by_name, validate_by_alias)

## Architecture Patterns

### Recommended Module Structure

```
src/omnifocus_operator/
├── models/
│   ├── __init__.py          # Update exports + model_rebuild() namespace
│   ├── base.py              # OmniFocusBaseModel (unchanged)
│   ├── common.py            # Remove old RepetitionRule, keep TagRef/ParentRef/ReviewInterval
│   ├── enums.py             # Remove old ScheduleType (2 values), add new Schedule (3 values)
│   └── repetition_rule.py   # NEW: structured RepetitionRule + Frequency union + End model
├── rrule/
│   ├── __init__.py          # Re-export parse_rrule, build_rrule
│   ├── parser.py            # parse_rrule(str) -> Frequency
│   └── builder.py           # build_rrule(Frequency) -> str
├── repository/
│   └── hybrid.py            # Update _build_repetition_rule() to call parser
└── bridge/
    └── adapter.py           # Update _adapt_repetition_rule() to call parser
```

**Key insight:** The `rrule/` module is a standalone utility package -- it depends on the models (~~FrequencySpec~~ → Frequency types) but nothing depends on it except the two read paths. Phase 33 will add the builder dependency from the write path.

### Pattern 1: Discriminated Union for Frequency Types

**What:** 8 Pydantic models, each with a `type: Literal[...]` discriminator, combined via `Annotated[Union[...], Field(discriminator='type')]`
**When to use:** When a field can be one of several structured shapes and the `type` field determines which
**Verified with:** Pydantic 2.12.5 on this project

```python
from typing import Annotated, Literal, Union
from pydantic import Field
from omnifocus_operator.models.base import OmniFocusBaseModel

class MinutelyFrequency(OmniFocusBaseModel):
    type: Literal["minutely"] = "minutely"
    interval: int = 1

class HourlyFrequency(OmniFocusBaseModel):
    type: Literal["hourly"] = "hourly"
    interval: int = 1

class DailyFrequency(OmniFocusBaseModel):
    type: Literal["daily"] = "daily"
    interval: int = 1

class WeeklyFrequency(OmniFocusBaseModel):
    type: Literal["weekly"] = "weekly"
    interval: int = 1
    on_days: list[str] | None = None  # serializes as onDays

class MonthlyFrequency(OmniFocusBaseModel):
    type: Literal["monthly"] = "monthly"
    interval: int = 1

class MonthlyDayOfWeekFrequency(OmniFocusBaseModel):
    type: Literal["monthly_day_of_week"] = "monthly_day_of_week"
    interval: int = 1
    on: dict[str, str] | None = None  # {"second": "tuesday"}

class MonthlyDayInMonthFrequency(OmniFocusBaseModel):
    type: Literal["monthly_day_in_month"] = "monthly_day_in_month"
    interval: int = 1
    on_dates: list[int] | None = None  # serializes as onDates

class YearlyFrequency(OmniFocusBaseModel):
    type: Literal["yearly"] = "yearly"
    interval: int = 1

Frequency = Annotated[
    Union[
        MinutelyFrequency, HourlyFrequency, DailyFrequency, WeeklyFrequency,
        MonthlyFrequency, MonthlyDayOfWeekFrequency, MonthlyDayInMonthFrequency,
        YearlyFrequency,
    ],
    Field(discriminator="type"),
]
```

**Verified behavior:**
- `type` field does NOT get camelCase-aliased (stays `type`) -- correct
- `on_days` becomes `onDays`, `on_dates` becomes `onDates` via alias generator
- `Field(discriminator="type")` works with `Annotated[Union[...]]` in Pydantic 2.12.5

### Pattern 2: Interval Omission (D-08)

**What:** Interval should be omitted from serialized output when it equals 1 (the default)
**Approach:** Custom `model_dump` override or `exclude_defaults=True` in serialization

**Important finding:** Using `exclude_defaults=True` also strips `type` (since it has a default). Two viable approaches:
1. **Override `model_dump` on each frequency model** -- checked: works, strips interval=1 while keeping type
2. **Use `model_serializer` decorator** -- more Pydantic-idiomatic

Since FastMCP calls `model_dump(by_alias=True)` on the parent Task/Project model, the frequency models need to control their own serialization. A custom `model_dump` override on a shared base class is cleanest:

```python
class _FrequencyBase(OmniFocusBaseModel):
    interval: int = 1

    def model_dump(self, **kwargs):
        d = super().model_dump(**kwargs)
        alias = "interval"  # alias_generator(interval) = interval (no change)
        if d.get(alias) == 1:
            d.pop(alias, None)
        return d
```

### Pattern 3: Schedule Derivation (D-06)

**What:** Derive 3-value schedule from 2 SQLite columns (`scheduleType` + `catchUpAutomatically`)
**Critical:** `from_completion + catchUp=true` must fail-fast (impossible state)

```python
def _derive_schedule(schedule_type: str, catch_up: bool) -> str:
    if schedule_type == "from_completion" and catch_up:
        raise ValueError(
            "from_completion + catchUpAutomatically=true is an impossible state. "
            "This indicates data corruption in the OmniFocus database."
        )
    if schedule_type == "from_completion":
        return "from_completion"
    if catch_up:
        return "regularly_with_catch_up"
    return "regularly"
```

**SQLite path mapping chain:**
- `fixed` / `from-assigned` -> `regularly`
- `due-after-completion` / `start-after-completion` / `from-completion` -> `from_completion`
- Then combine with `catchUpAutomatically` to get 3-value schedule

**Bridge path mapping chain:**
- `Regularly` -> check catchUp -> `regularly` or `regularly_with_catch_up`
- `FromCompletion` -> `from_completion`
- `None` -> nullify the rule (existing behavior)

### Pattern 4: End Condition Model

**What:** Single-key dict pattern consistent with `moveTo` pattern already in the project

```python
class EndByDate(OmniFocusBaseModel):
    date: str  # ISO-8601

class EndByOccurrences(OmniFocusBaseModel):
    occurrences: int

EndCondition = EndByDate | EndByOccurrences
```

Parsed from RRULE:
- `UNTIL=20261231T000000Z` -> `{"date": "2026-12-31T00:00:00Z"}` (convert from RRULE compact format)
- `COUNT=10` -> `{"occurrences": 10}`
- Neither -> field omitted entirely

### Pattern 5: BYDAY Positional Prefix Parsing

**What:** Parse `BYDAY=2TU` into `{"on": {"second": "tuesday"}}` for monthly_day_of_week
**Regex verified:** `r'^(-?\d+)?(MO|TU|WE|TH|FR|SA|SU)$'`

Mapping tables:
```python
POS_TO_ORDINAL = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth", -1: "last"}
DAY_CODE_TO_NAME = {
    "MO": "monday", "TU": "tuesday", "WE": "wednesday", "TH": "thursday",
    "FR": "friday", "SA": "saturday", "SU": "sunday",
}
```

**Decision required for parser:** When BYDAY has a positional prefix AND FREQ=MONTHLY, this is `monthly_day_of_week`. When BYDAY has no prefix AND FREQ=WEEKLY, this is `weekly` with `onDays`.

### Anti-Patterns to Avoid
- **Duplicating parse logic between read paths:** Both SQLite and bridge paths MUST call the same parser function. The parser takes a raw RRULE string and returns a ~~FrequencySpec~~ → Frequency.
- **Putting RRULE parsing in the Pydantic model itself:** The model represents the structured output; the parser is a separate utility that produces dicts the model validates.
- **Handling `from_completion + catchUp=true` silently:** This is an impossible state. Must crash with ValueError, not silently map to some default.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RRULE parsing | Full RFC 5545 parser | Purpose-built parser for OmniFocus subset only | OmniFocus produces a tiny subset; full parser adds complexity without value (YAGNI, per user decision) |
| Date format conversion | Manual UNTIL format converter | Simple string slicing | `YYYYMMDDTHHMMSSZ` -> ISO-8601 is trivial: `f"{s[:4]}-{s[4:6]}-{s[6:8]}T{s[9:11]}:{s[11:13]}:{s[13:15]}Z"` |
| Discriminated union | Manual type dispatch | Pydantic `Field(discriminator="type")` | Pydantic handles validation, serialization, schema generation, and error messages |

## Common Pitfalls

### Pitfall 1: BYDAY Without Positional Prefix in MONTHLY Context
**What goes wrong:** Plain `BYDAY=MO,WE,FR` in a MONTHLY context would mean "every Monday, Wednesday, Friday of every month" -- different from positional prefix
**Why it happens:** OmniFocus may theoretically produce this, but golden master data shows it only uses positional prefix form for MONTHLY
**How to avoid:** Per D-05, only handle positional prefix form. If encountering plain day codes with FREQ=MONTHLY, raise clear error
**Warning signs:** Parser tests pass but real OmniFocus data produces unexpected results

### Pitfall 2: Schedule Derivation Order Matters
**What goes wrong:** Checking `catchUp` before `scheduleType` could map `from_completion + catchUp=false` to `regularly` instead of `from_completion`
**Why it happens:** If-else chain order
**How to avoid:** Check scheduleType first, then combine with catchUp
**Warning signs:** Tests show "regularly" for tasks that should be "from_completion"

### Pitfall 3: UNTIL Format Conversion
**What goes wrong:** RRULE uses compact format `20261231T000000Z`, but the agent-facing model should use ISO-8601 `2026-12-31T00:00:00Z`
**Why it happens:** Easy to forget format conversion in one direction
**How to avoid:** Parse and build must both handle the conversion. Test round-trip explicitly.
**Warning signs:** Dates in output look like `20261231T000000Z` instead of ISO-8601

### Pitfall 4: model_rebuild() Namespace Must Include New Types
**What goes wrong:** `models/__init__.py` has a `_ns` dict and `model_rebuild()` calls for forward reference resolution. If new frequency types aren't added, Pydantic raises `PydanticUndefinedAnnotation`
**Why it happens:** Forward reference resolution in the model hierarchy; TYPE_CHECKING imports
**How to avoid:** Add new RepetitionRule type (and ~~FrequencySpec~~ → Frequency subtypes if needed) to `_ns` dict and call `model_rebuild()` on the new model class
**Warning signs:** Import-time errors or validation errors mentioning undefined types

### Pitfall 5: camelCase Alias for `monthlyDayOfWeek` Type Literal
**What goes wrong:** The `type` field value `"monthly_day_of_week"` is a Literal string, not a field name. Pydantic's alias generator applies to field names, not Literal values. The type discriminator value will be `"monthly_day_of_week"` in JSON output, NOT `"monthlyDayOfWeek"`.
**Why it happens:** Confusion between field name aliasing and Literal value aliasing
**How to avoid:** This is actually the desired behavior per D-02. The type value IS the discriminator and should be stable/predictable, not camelCased.
**Warning signs:** Tests asserting camelCase type values will fail

### Pitfall 6: Golden Master Comparison After Model Change
**What goes wrong:** The golden master stores raw bridge format with `ruleString`, `scheduleType`, `anchorDateKey`, `catchUpAutomatically`. The InMemoryBridge and bridge adapter still produce this format. If the golden master comparison pipeline calls `model_validate()` on the new RepetitionRule, it will fail because the raw bridge data doesn't match the new model shape.
**Why it happens:** The transformation from raw -> structured happens in the repository/adapter layer, AFTER the golden master comparison point
**How to avoid:** Golden master operates at raw bridge layer (per D-12). The `repetitionRule` field is already in `UNCOMPUTED_PROJECT_FIELDS` in `normalize.py`. For tasks, the golden master comparison uses InMemoryBridge's raw format. The parser is a separate layer tested independently.
**Warning signs:** Golden master tests break after model change

## Code Examples

### Parse RRULE to ~~FrequencySpec~~ → Frequency (core parser logic)

```python
import re
from typing import Any

_BYDAY_PATTERN = re.compile(r"^(-?\d+)?(MO|TU|WE|TH|FR|SA|SU)$")
_POS_TO_ORDINAL = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth", -1: "last"}
_DAY_TO_NAME = {
    "MO": "monday", "TU": "tuesday", "WE": "wednesday", "TH": "thursday",
    "FR": "friday", "SA": "saturday", "SU": "sunday",
}
_UNTIL_PATTERN = re.compile(r"^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z$")

def parse_rrule(rule_string: str) -> dict[str, Any]:
    """Parse RRULE string into structured frequency dict.

    Returns dict suitable for Frequency model validation.
    Raises ValueError with educational message on invalid input.
    """
    parts = dict(p.split("=", 1) for p in rule_string.split(";"))
    freq = parts.get("FREQ", "").upper()
    interval = int(parts.get("INTERVAL", "1"))

    result: dict[str, Any] = {"interval": interval}

    if freq == "MINUTELY":
        result["type"] = "minutely"
    elif freq == "HOURLY":
        result["type"] = "hourly"
    elif freq == "DAILY":
        result["type"] = "daily"
    elif freq == "WEEKLY":
        result["type"] = "weekly"
        if "BYDAY" in parts:
            result["on_days"] = parts["BYDAY"].split(",")
    elif freq == "MONTHLY":
        if "BYDAY" in parts:
            # Positional prefix: BYDAY=2TU -> {"second": "tuesday"}
            result["type"] = "monthly_day_of_week"
            m = _BYDAY_PATTERN.match(parts["BYDAY"])
            if not m or m.group(1) is None:
                raise ValueError(f"MONTHLY BYDAY must use positional prefix (e.g., 2TU), got: {parts['BYDAY']}")
            pos = int(m.group(1))
            ordinal = _POS_TO_ORDINAL.get(pos)
            if ordinal is None:
                raise ValueError(f"Invalid BYDAY position {pos}. Valid: 1-5 or -1 (last)")
            result["on"] = {ordinal: _DAY_TO_NAME[m.group(2)]}
        elif "BYMONTHDAY" in parts:
            result["type"] = "monthly_day_in_month"
            result["on_dates"] = [int(parts["BYMONTHDAY"])]
        else:
            result["type"] = "monthly"
    elif freq == "YEARLY":
        result["type"] = "yearly"
    else:
        raise ValueError(f"Unsupported FREQ: {freq!r}")

    return result
```

### End Condition Parsing from RRULE

```python
def _parse_end_condition(parts: dict[str, str]) -> dict[str, Any] | None:
    """Extract end condition from parsed RRULE parts. Returns None for no end."""
    if "COUNT" in parts and "UNTIL" in parts:
        raise ValueError("COUNT and UNTIL are mutually exclusive (RFC 5545)")
    if "COUNT" in parts:
        return {"occurrences": int(parts["COUNT"])}
    if "UNTIL" in parts:
        raw = parts["UNTIL"]
        # Convert YYYYMMDDTHHMMSSZ -> ISO-8601
        m = _UNTIL_PATTERN.match(raw)
        if not m:
            raise ValueError(f"UNTIL must match YYYYMMDDTHHMMSSZ format, got {raw!r}")
        iso = f"{m.group(1)}-{m.group(2)}-{m.group(3)}T{m.group(4)}:{m.group(5)}:{m.group(6)}Z"
        return {"date": iso}
    return None
```

### Wiring Into SQLite Read Path

```python
# In repository/hybrid.py -- _build_repetition_rule()
def _build_repetition_rule(row: sqlite3.Row) -> dict[str, Any] | None:
    rule_string = row["repetitionRuleString"]
    if not rule_string:
        return None

    schedule_type_raw = row["repetitionScheduleTypeString"]
    catch_up = bool(row["catchUpAutomatically"])
    anchor_key = _ANCHOR_DATE_MAP.get(row["repetitionAnchorDateKey"], "due_date")

    # Parse RRULE -> structured frequency
    frequency = parse_rrule(rule_string)
    end = parse_end_condition(rule_string)
    schedule = _derive_schedule(
        _SCHEDULE_TYPE_MAP.get(schedule_type_raw, schedule_type_raw),
        catch_up,
    )

    result: dict[str, Any] = {
        "frequency": frequency,
        "schedule": schedule,
        "based_on": anchor_key,
    }
    if end is not None:
        result["end"] = end
    return result
```

### Wiring Into Bridge Adapter Path

```python
# In bridge/adapter.py -- _adapt_repetition_rule()
def _adapt_repetition_rule(raw: dict[str, Any]) -> None:
    rule = raw.get("repetitionRule")
    if rule is None:
        return

    schedule_type = rule.get("scheduleType")
    if schedule_type == _SCHEDULE_TYPE_NONE:
        raw["repetitionRule"] = None
        return

    # Parse raw bridge fields into structured model
    rule_string = rule.get("ruleString", "")
    catch_up = rule.get("catchUpAutomatically", False)

    schedule_mapped = _SCHEDULE_TYPE_MAP.get(schedule_type, schedule_type)
    anchor_mapped = _ANCHOR_DATE_KEY_MAP.get(rule.get("anchorDateKey", ""), "due_date")

    frequency = parse_rrule(rule_string)
    end = parse_end_condition(rule_string)
    schedule = _derive_schedule(schedule_mapped, catch_up)

    structured: dict[str, Any] = {
        "frequency": frequency,
        "schedule": schedule,
        "basedOn": anchor_mapped,
    }
    if end is not None:
        structured["end"] = end
    raw["repetitionRule"] = structured
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Raw RRULE string in model | Structured frequency fields | This phase | Agents never see RRULE strings; type-safe discriminated union |
| 2-value ScheduleType enum | 3-value Schedule enum | This phase | `regularly_with_catch_up` collapses scheduleType + catchUp boolean |
| `anchorDateKey` enum | `basedOn` field | This phase | Renamed to match OmniFocus UI language |
| 4-field RepetitionRule | frequency + schedule + basedOn + end | This phase | Breaking change; clean break acceptable per D-09 |

## Existing Code Impact Analysis

### Files to Modify

| File | Change | Risk |
|------|--------|------|
| `models/common.py` | Remove `RepetitionRule` class | LOW -- move to new module |
| `models/enums.py` | Remove `ScheduleType` (2 values); add `Schedule` (3 values); keep `AnchorDateKey` (rename to `BasedOn` or keep) | MEDIUM -- many imports reference these |
| `models/__init__.py` | Update exports, add new types to `_ns` dict, update `model_rebuild()` calls | MEDIUM -- forward reference resolution |
| `models/base.py` | Update `repetition_rule` type annotation on `ActionableEntity` | LOW -- type change only |
| `repository/hybrid.py` | Rewrite `_build_repetition_rule()` to call parser | LOW -- isolated function |
| `bridge/adapter.py` | Rewrite `_adapt_repetition_rule()` to call parser | LOW -- isolated function |
| `tests/conftest.py` | Update `make_model_task_dict` and `make_model_project_dict` repetitionRule format | MEDIUM -- many tests use these factories |
| `tests/test_models.py` | Rewrite `TestRepetitionRule` class for new model shape | LOW -- small test class |
| `tests/test_adapter.py` | Update repetition rule adapter tests for new output format | MEDIUM -- 6 tests to rewrite |

### Files to Create

| File | Purpose |
|------|---------|
| `models/repetition_rule.py` | New RepetitionRule model + ~~FrequencySpec~~ → Frequency types + End models |
| `rrule/__init__.py` | Package init, re-exports |
| `rrule/parser.py` | `parse_rrule()` function |
| `rrule/builder.py` | `build_rrule()` function (needed for round-trip testing, used by Phase 33) |
| `tests/test_rrule.py` | Parser + builder tests (ported from spike + new) |

### Files NOT Modified

- `tests/golden_master/` -- operates at raw bridge layer, unaffected
- `tests/doubles/bridge.py` -- InMemoryBridge produces raw bridge format, adapter transforms it
- `bridge/bridge.js` -- JS bridge produces raw format, Python adapter transforms it
- `server.py` -- returns Pydantic models, FastMCP handles serialization

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` (pytest section) |
| Quick run command | `uv run python -m pytest tests/ -x -q --tb=short` |
| Full suite command | `uv run python -m pytest tests/ -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| READ-01 | Structured frequency fields in RepetitionRule model | unit | `uv run python -m pytest tests/test_models.py -x -k RepetitionRule` | Yes (rewrite needed) |
| READ-02 | All 8 frequency types parse correctly | unit | `uv run python -m pytest tests/test_rrule.py -x` | No -- Wave 0 |
| READ-03 | Both read paths share single rrule module | integration | `uv run python -m pytest tests/test_hybrid_repository.py tests/test_adapter.py -x -k repetition` | Yes (update needed) |
| READ-04 | parse/build round-trip | unit | `uv run python -m pytest tests/test_rrule.py -x -k round_trip` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run python -m pytest tests/ -x -q --tb=short`
- **Per wave merge:** `uv run python -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_rrule.py` -- covers READ-02, READ-04 (parser unit tests, round-trip tests)
- [ ] No new fixtures needed -- existing `conftest.py` factories need updating, not new fixtures

## Open Questions

1. **`AnchorDateKey` enum rename to `BasedOn`?**
   - What we know: D-06 mentions `basedOn` as the new field name. Current `AnchorDateKey` enum has the right values (`due_date`, `defer_date`, `planned_date`).
   - What's unclear: Should the enum class itself be renamed to `BasedOn` or keep `AnchorDateKey` internally?
   - Recommendation: Rename to `BasedOn` for consistency with the agent-facing field name. The old name is an internal detail.

2. **`weekday` and `weekend_day` in monthly_day_of_week vocabulary**
   - What we know: D-10 lists these as valid day names. In RRULE, there's no single BYDAY code for "weekday" or "weekend_day".
   - What's unclear: Will OmniFocus ever produce BYDAY with these composite values? Golden master shows only single day codes.
   - Recommendation: Include in the vocabulary definition (for Phase 33 write support) but the parser won't encounter them from OmniFocus read data. If encountered, raise clear error. This is a write-only concern.

3. **BYSETPOS error message wording**
   - What we know: D-05 says clear error if BYSETPOS encountered. Spike parser handles BYSETPOS but production parser should reject it.
   - Recommendation: `"BYSETPOS is not supported. OmniFocus uses positional BYDAY format (e.g., BYDAY=2TU for 'second Tuesday'). Please report this rule string: {rule_string}"`

## Sources

### Primary (HIGH confidence)
- Spike parser: `.research/deep-dives/rrule-validator/rrule_validator.py` -- 79 tests, directly portable
- Golden master: `tests/golden_master/snapshots/08-repetition/` -- 30 scenarios with real OmniFocus RRULE data
- OmniJS guide: `.research/deep-dives/repetition-rule/repetition-rule-guide.md` -- API reference
- Milestone spec: `.research/updated-spec/MILESTONE-v1.2.3.md` -- full structured model spec
- Pydantic 2.12.5 discriminated union: verified via live interpreter (on this machine)

### Secondary (MEDIUM confidence)
- camelCase alias interaction with discriminated unions: verified via live interpreter but limited to 2-type test

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- Pydantic v2 discriminated unions verified on exact project version
- Architecture: HIGH -- both read paths inspected, transformation points identified, spike parser reviewed
- Pitfalls: HIGH -- golden master impact analyzed, serialization edge cases tested, schedule derivation logic mapped

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable domain, no external dependencies changing)
