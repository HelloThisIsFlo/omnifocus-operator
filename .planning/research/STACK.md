# Stack Research: Repetition Rule Write Support

**Domain:** Structured frequency model, RRULE parsing/building, Pydantic discriminated unions
**Researched:** 2026-03-27
**Confidence:** HIGH

## Decision: Zero New Dependencies

No new runtime or dev dependencies needed. Everything builds on existing stack:
- **RRULE parsing/building**: Custom (~200 lines, spike-validated, 79 tests) -- not python-dateutil
- **Discriminated unions**: Pydantic v2 native -- verified working with project's patterns
- **Partial update lifecycle**: Existing UNSET/Patch/PatchOrClear infrastructure -- verified compatible

## Why Custom RRULE Parser, Not python-dateutil

**Recommendation:** Use the custom parser from `.research/deep-dives/rrule-validator/`. Do NOT add python-dateutil.

### Evidence

| Criterion | Custom Parser | python-dateutil |
|-----------|--------------|-----------------|
| **Scope match** | Exact: parse string to components, build string from components | Overkill: designed for date occurrence generation, not string manipulation |
| **Component extraction** | Direct: returns typed dataclass with named fields | Indirect: components stored as private attrs (`_freq`, `_interval`, `_byweekday`), no public API for extraction |
| **String building** | `build_rrule()` with round-trip validation | No public string builder from components |
| **OmniFocus subset** | Validates exactly the RRULE keys OmniFocus uses (FREQ, INTERVAL, BYDAY, BYMONTHDAY, BYSETPOS, COUNT, UNTIL) | Full RFC 5545 -- MINUTELY/SECONDLY, BYMINUTE, BYHOUR, BYWEEKNO, BYYEARDAY etc. that OmniFocus ignores |
| **Dependencies** | Zero (stdlib only) | Adds `python-dateutil` (~150KB, transitive deps) |
| **Validation** | Type-aware: rejects invalid combos (BYSETPOS without BYDAY, COUNT+UNTIL mutual exclusion) | Silently accepts many invalid combos |
| **Tested** | 79 tests covering all OmniFocus frequency types | Would need wrapper tests anyway |
| **Lines** | ~200 lines, fully auditable | ~2,500 lines in `rrule.py` alone |

### What python-dateutil is good for (but we don't need)

- **Date occurrence generation**: "give me the next 10 dates matching this rule" -- OmniFocus handles this internally
- **Timezone handling**: `DTSTART;TZID=` parsing -- OmniFocus RRULE strings don't use DTSTART
- **Complex recurrence sets**: EXDATE, EXRULE, multiple RRULE combination -- OmniFocus uses single RRULE only

### python-dateutil's known problems for our use case

- UNTIL dates auto-converted to datetime objects, losing the original string format ([Issue #938](https://github.com/dateutil/dateutil/issues/938))
- No public API to extract structured components from a parsed rule -- only private attributes
- `rruleset` serialization to string has known gaps ([Issue #856](https://github.com/dateutil/dateutil/issues/856))
- Accepts RRULE strings that OmniFocus would reject -- we'd need validation wrapping anyway

### Migration path from spike to production

The spike code is directly portable with these changes:
1. Replace `RRuleComponents` dataclass with Pydantic `Frequency` discriminated union models
2. `validate_rrule()` parsing logic maps directly to `parse_rrule(str) -> Frequency`
3. `build_rrule()` takes a `Frequency` instead of loose kwargs
4. Wire into existing `ScheduleType` and `AnchorDateKey` enums from `models/enums.py` (spike already notes this)

## Pydantic v2 Discriminated Union Pattern

**Verified working** on Pydantic 2.12.5 (project's current version) with all project conventions.

### Pattern: `Literal` type field as discriminator

```python
from typing import Literal, Union, Annotated
from pydantic import Field

class DailyFreq(CommandModel):
    type: Literal["daily"] = "daily"
    interval: int = 1

class WeeklyFreq(CommandModel):
    type: Literal["weekly"] = "weekly"
    interval: int = 1
    on_days: list[str] | None = None

Frequency = Annotated[
    Union[DailyFreq, WeeklyFreq, ...],
    Field(discriminator="type"),
]
```

### Verified compatibility

| Project convention | Works with discriminated unions? | Tested |
|-------------------|--------------------------------|--------|
| `alias_generator=to_camel` | YES -- `type` stays `type` after camelCase conversion | Verified |
| `extra="forbid"` (CommandModel) | YES -- naturally rejects cross-type fields (e.g., `onDays` on `daily`) | Verified |
| `validate_by_name=True` | YES -- both `on_days` and `onDays` accepted | Verified |
| UNSET sentinel + `Patch[Frequency]` | YES -- UNSET means "no change to frequency" | Verified |
| `PatchOrClear[RepetitionRuleCommand]` | YES -- None = remove rule, UNSET = no change | Verified |
| JSON Schema generation | YES -- generates OpenAPI discriminator mapping with `oneOf` + `propertyName: "type"` | Verified |

### Key insight: extra="forbid" gives type-specific validation for free

When each frequency variant is its own `CommandModel` subclass with `extra="forbid"`, Pydantic automatically rejects fields that don't belong to the discriminated type. Sending `{"type": "daily", "onDays": ["MO"]}` raises `ValidationError: Extra inputs are not permitted`. This eliminates half of "Layer 2: type-specific constraints" from the spec -- field membership validation comes from the model structure, not custom code.

Remaining Layer 2 validations that need custom code:
- Value range constraints: `interval >= 1`, valid day codes, ordinal values, `dayOfMonth` range
- Semantic constraints: `BYSETPOS` requires `BYDAY`

### End condition: model_validator pattern (not discriminated union)

The `end` field uses the "key IS the value" pattern from MoveAction, not a discriminated union:

```python
class EndCondition(CommandModel):
    date: AwareDatetime | None = None
    occurrences: int | None = None

    @model_validator(mode="after")
    def _exactly_one_key(self) -> EndCondition:
        # ... same pattern as MoveAction._exactly_one_key
```

This matches the existing MoveAction precedent and keeps the spec's requirement that `end` uses the same "key IS the value" pattern.

## Existing Infrastructure Reuse

### Already exists, no changes needed

| Component | Location | Reuse for v1.2.3 |
|-----------|----------|-------------------|
| `ScheduleType` enum | `models/enums.py` | Maps to `schedule` field values |
| `AnchorDateKey` enum | `models/enums.py` | Maps to `basedOn` field values |
| `UNSET` / `Patch` / `PatchOrClear` | `contracts/base.py` | Partial update semantics for all repetition fields |
| `CommandModel` base | `contracts/base.py` | Base class for all frequency variant models |
| `model_validator` pattern | `contracts/common.py` (MoveAction) | Reuse for EndCondition exactly-one-key validation |
| `_adapt_repetition_rule()` | `bridge/adapter.py` | Needs modification: parse ruleString into structured fields |
| `_build_repetition_rule()` | `repository/hybrid.py` | Needs modification: parse ruleString from SQLite into structured fields |
| `RepetitionRule` model | `models/common.py` | Replace: ruleString -> structured frequency + schedule + basedOn + end fields |

### Needs modification (not new)

| Component | Current | After v1.2.3 |
|-----------|---------|--------------|
| `RepetitionRule` model | `rule_string`, `schedule_type`, `anchor_date_key`, `catch_up_automatically` | `frequency: Frequency`, `schedule: ScheduleType`, `based_on: AnchorDateKey`, `end: EndCondition \| None` |
| Bridge adapter | Passes through raw rule data | Calls `parse_rrule()` on ruleString |
| SQLite mapper | Passes through raw rule data | Calls `parse_rrule()` on ruleString |
| Bridge script | Reads repetition rule properties | Also needs write handler for setting repetition rules |
| EditTaskCommand | No repetition fields | Adds `repetition_rule: PatchOrClear[RepetitionRuleCommand]` |
| AddTaskCommand | No repetition fields | Adds `repetition_rule: RepetitionRuleSpec \| None` |

## What NOT to Add

| Library | Why Not |
|---------|---------|
| `python-dateutil` | Overkill for string-to-components parsing; no public component extraction API; would still need validation wrapping |
| `icalendar` | Full ICS file parser -- we only need RRULE strings, not VCALENDAR/VEVENT |
| `ics` (ics.py) | Calendar file library -- entirely wrong scope |
| `recurring-ical-events` | Event occurrence expansion -- OmniFocus handles this internally |
| Any RRULE library | The custom parser (~200 lines) is more precise, better tested, and zero-dep |

## Installation

```bash
# No changes to pyproject.toml
# Zero new dependencies
```

## Version Compatibility

| Package | Version | Notes |
|---------|---------|-------|
| Pydantic | 2.12.5 (current) | Discriminated unions + alias_generator verified working |
| FastMCP | >=3.1.1 (current) | No interaction with repetition features |
| Python | 3.12+ (current) | `type` statements, `Annotated` syntax available |

## Sources

- [Pydantic v2 Unions docs](https://docs.pydantic.dev/latest/concepts/unions/) -- discriminated union patterns, Field(discriminator=...) syntax (HIGH confidence)
- [Pydantic issue #11039](https://github.com/pydantic/pydantic/issues/11039) -- alias_generator + discriminated union fix confirmed resolved (HIGH confidence)
- [python-dateutil rrule docs](https://dateutil.readthedocs.io/en/stable/rrule.html) -- API surface review for comparison (HIGH confidence)
- [python-dateutil issue #938](https://github.com/dateutil/dateutil/issues/938) -- UNTIL date handling limitation (HIGH confidence)
- [python-dateutil issue #856](https://github.com/dateutil/dateutil/issues/856) -- rruleset serialization gaps (MEDIUM confidence)
- Local verification: Pydantic 2.12.5 tested with discriminated union + alias_generator + extra=forbid + UNSET sentinel (HIGH confidence -- ran in project's actual environment)

---
*Stack research for: OmniFocus Operator v1.2.3 -- Repetition Rule Write Support*
*Researched: 2026-03-27*
