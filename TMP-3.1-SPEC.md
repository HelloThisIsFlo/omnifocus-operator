
```markdown
# Phase 33.1: Flat Frequency Model

## Problem Statement

The `Frequency` type in `src/omnifocus_operator/models/repetition_rule.py` is a
Pydantic discriminated union with 9 subtypes (one per frequency type). This design
was the right call for Phase 32 (read model) — it gives precise JSON Schema where
each type shows only its relevant fields. But it creates three concrete problems
now that the write side exists.

## Problem 1: Type is required on every edit, even same-type updates

The discriminated union uses `type` as the Pydantic discriminator. Every `Frequency`
instance MUST include `type` for Pydantic to know which subtype to validate against.

This means an agent editing a daily task's interval from 3 to 5 must write:

```json
{"repetitionRule": {"frequency": {"type": "daily", "interval": 5}}}
```

When what they naturally want to write is:

```json
{"repetitionRule": {"frequency": {"interval": 5}}}
```

The `type` is redundant — the task already HAS a frequency type. The server knows
it's daily. Forcing the agent to restate it adds friction and creates a failure
mode: if the agent sends the wrong type by mistake, the server treats it as a type
change instead of an interval update.

Phase 33 ships with type required (the discriminated union makes type-optional
impossible at the Pydantic level). The tool description explicitly says
"frequency.type is always required when updating frequency." This works but is
suboptimal for agent DX.

## Problem 2: Interval serialization workaround

During Phase 32, we wanted `interval` to be omitted from read output when it's 1
(the default), since most tasks repeat every 1 of their frequency. The natural
approach is `model_dump(exclude_defaults=True)`. But `type` is ALSO a default
(each subtype sets it as a Literal default), so `exclude_defaults` would strip
`type` too — breaking the output.

The attempted fix was a `@model_serializer` on `_FrequencyBase` that manually
included `type` while excluding `interval=1`. This caused a Phase 32.1 emergency:
`@model_serializer` returning `dict[str, Any]` erased all property/constraint info
from the serialization JSON Schema. The MCP `outputSchema` degraded to
`{"type": "object", "additionalProperties": true}` — meaning MCP clients could no
longer validate tool output.

The current state: `interval` is ALWAYS included in output (even when 1). The
`@model_serializer` was removed entirely. This works but produces noisier output:

```json
// Current output (interval=1 always shown):
{"type": "daily", "interval": 1}

// Desired output (interval=1 omitted as default):
{"type": "daily"}
```

With a flat model where `type` is a required field (no default) and `interval`
has `default=1`, `exclude_defaults=True` would correctly omit interval=1 while
keeping type. No custom serializer needed.

## Problem 3: 9 subtype classes for what is logically one concept

The current hierarchy:

```python
class _FrequencyBase(OmniFocusBaseModel):
    interval: int = 1

class MinutelyFrequency(_FrequencyBase):
    type: Literal["minutely"] = "minutely"

class HourlyFrequency(_FrequencyBase):
    type: Literal["hourly"] = "hourly"

class DailyFrequency(_FrequencyBase):
    type: Literal["daily"] = "daily"

class WeeklyFrequency(_FrequencyBase):
    type: Literal["weekly"] = "weekly"

class WeeklyOnDaysFrequency(_FrequencyBase):
    type: Literal["weekly_on_days"] = "weekly_on_days"
    on_days: list[str]

class MonthlyFrequency(_FrequencyBase):
    type: Literal["monthly"] = "monthly"

class MonthlyDayOfWeekFrequency(_FrequencyBase):
    type: Literal["monthly_day_of_week"] = "monthly_day_of_week"
    on: dict[str, str]

class MonthlyDayInMonthFrequency(_FrequencyBase):
    type: Literal["monthly_day_in_month"] = "monthly_day_in_month"
    on_dates: list[int]

class YearlyFrequency(_FrequencyBase):
    type: Literal["yearly"] = "yearly"

Frequency = Annotated[
    MinutelyFrequency | HourlyFrequency | DailyFrequency | ... ,
    Field(discriminator="type")
]
```

9 classes + 1 base + 1 union type for what is semantically one concept with
3 optional fields (`on_days`, `on`, `on_dates`). The discriminated union buys
Pydantic structural validation (e.g., `on_days` is rejected on a `daily` type),
but this validation can equally live in a service-layer or model validator.

## Desired End State

Three flat frequency models replacing the 9-subtype discriminated union:

```python
# models/repetition_rule.py — READ model
# OmniFocusBaseModel (no extra="forbid") — represents data, not agent input
class Frequency(OmniFocusBaseModel):
    type: str                              # required, no default → survives exclude_defaults
    interval: int = 1                      # default 1 → omitted by exclude_defaults
    on_days: list[str] | None = None       # only for weekly_on_days
    on: dict[str, str] | None = None       # only for monthly_day_of_week
    on_dates: list[int] | None = None      # only for monthly_day_in_month

# contracts/ — ADD spec
# CommandModel (extra="forbid") — validates agent input, catches typos
# Same fields as read Frequency, but different base class justifies
# a separate model (see docs/architecture.md decision tree step 4)
class FrequencyAddSpec(CommandModel):
    type: str                              # required
    interval: int = 1
    on_days: list[str] | None = None
    on: dict[str, str] | None = None
    on_dates: list[int] | None = None

# contracts/ — EDIT spec
# CommandModel (extra="forbid") — validates agent input
# type is optional: when omitted, service infers from existing task
class FrequencyEditSpec(CommandModel):
    type: str | None = None                # optional — inferred from existing
    interval: int | None = None            # None = preserve existing
    on_days: list[str] | None = None       # None = preserve existing
    on: dict[str, str] | None = None
    on_dates: list[int] | None = None
```

### Why three models, not one

The architecture doc (decision tree step 4) establishes that write models always
inherit `CommandModel` (`extra="forbid"`), while read models inherit
`OmniFocusBaseModel` (no `extra="forbid"`). This base class difference alone
justifies a dedicated write model, even when the field shapes are identical.

- `Frequency` (read): `OmniFocusBaseModel` — represents data from SQLite/bridge.
  No `extra="forbid"` because it's not validating agent input.
- `FrequencyAddSpec` (write): `CommandModel` — identical fields, but
  `extra="forbid"` catches agent typos like `{type: "daily", intervel: 3}`.
- `FrequencyEditSpec` (write): `CommandModel` — different shape (`type` optional),
  `extra="forbid"` catches typos.

### What this solves

**Problem 1 (type optional on edit):** `FrequencyEditSpec` makes `type` optional.
When omitted, the service layer infers it from the existing task's frequency.
Agent can send `{frequency: {interval: 5}}` and the server does the right thing.

**Problem 2 (interval serialization):** `model_dump(exclude_defaults=True)` on the
read `Frequency` omits `interval=1` (has default) but keeps `type` (no default).
No custom serializer. Non-applicable fields (`on_days`, `on`, `on_dates`) excluded
via `model_dump(exclude_none=True)`. Output is clean:

```json
// Daily, default interval:
{"type": "daily"}

// Weekly on days, interval 2:
{"type": "weekly_on_days", "interval": 2, "onDays": ["MO", "FR"]}

// Monthly, default interval:
{"type": "monthly"}
```

**Problem 3 (class count):** 9 subtype classes + 1 base + 1 union → 3 focused
classes (1 read + 2 write specs). Net reduction from 11 to 3. Each class has a
clear purpose and the right validation behavior for its context.

### What moves where

Cross-type field validation (e.g., rejecting `on_days` on a `daily` frequency)
moves from Pydantic structural validation to the service layer. This is where
type-specific validation already lives per Phase 33's design (VALID-02). Phase 33
was designed with this migration in mind — D-02 says "keep frequency validation
in the service layer so that Phase 33.1 can swap to a flat model without
rewriting service logic."

## Scope

This is a cross-cutting refactor affecting:

- **Read model** (`models/repetition_rule.py`): Replace 9 subtypes + union with
  single flat `Frequency` class (`OmniFocusBaseModel`)
- **Write models** (`contracts/`):
  - New `FrequencyAddSpec` (`CommandModel`, `extra="forbid"`) — same fields as
    read `Frequency`, type required
  - New `FrequencyEditSpec` (`CommandModel`, `extra="forbid"`) — type optional,
    None = preserve existing
  - `RepetitionRuleAddSpec` embeds `FrequencyAddSpec` (was: `Frequency` union)
  - `RepetitionRuleEditSpec` embeds `FrequencyEditSpec` (was: `Patch[Frequency]`)
- **RRULE parser** (`rrule/parser.py`): Return flat `Frequency` instead of
  specific subtypes
- **RRULE builder** (`rrule/builder.py`): Accept flat `Frequency` instead of union
- **Service layer**: Add cross-type field validation (reject `on_days` on `daily`,
  etc.). Update merge logic to handle type-optional frequency edits
- **Tests**: Update all tests referencing specific frequency subtypes
- **Output schema tests** (`test_output_schema.py`): Verify the flat model's
  serialized output still validates against MCP outputSchema
- **Tool descriptions** (`server.py`): Update edit_tasks description — `type`
  becomes optional when updating within the same frequency type

Breaking change on read output — acceptable (pre-release, single user, installed
from source). Same rationale as Phase 32 D-09.

## What NOT to change

- `RepetitionRule` container model (frequency + schedule + basedOn + end) — unchanged
- `Schedule`, `BasedOn` enums — unchanged
- `EndCondition` union (EndByDate | EndByOccurrences) — unchanged
- Bridge payload format — unchanged (still 4-field: ruleString + scheduleType +
  anchorDateKey + catchUpAutomatically)
- Tool description format for add_tasks — unchanged (the frequency type list and
  examples stay the same, just the underlying model is simpler)

## Key Files

- `src/omnifocus_operator/models/repetition_rule.py` — primary refactor target (9 subtypes → flat `Frequency`)
- `src/omnifocus_operator/contracts/use_cases/add_task.py` — embed `FrequencyAddSpec`
- `src/omnifocus_operator/contracts/use_cases/edit_task.py` — embed `FrequencyEditSpec` (type optional)
- `src/omnifocus_operator/contracts/common.py` — or new file for `FrequencyAddSpec`/`FrequencyEditSpec`
- `src/omnifocus_operator/rrule/parser.py` — update return types
- `src/omnifocus_operator/rrule/builder.py` — update input types
- `src/omnifocus_operator/service/service.py` — merge logic for type-optional edits
- `src/omnifocus_operator/service/validate.py` — cross-type field validation
- `src/omnifocus_operator/server.py` — update edit_tasks tool description
- `tests/test_output_schema.py` — verify schema still valid
- `tests/test_rrule.py` — update frequency type references
- `tests/test_models.py` — update frequency type references
- `docs/architecture.md` — update Frequency Types table (lines 508-519) to reflect flat model

## Depends On

Phase 33 (write model must exist before we can make type optional on edits).
```