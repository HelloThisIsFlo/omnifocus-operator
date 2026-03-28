---
created: 2026-03-28T19:55:37.809Z
title: "Refactor Frequency to flat model with type-optional edits"
area: models
files:
  - src/omnifocus_operator/models/repetition_rule.py
  - src/omnifocus_operator/contracts/use_cases/add_task.py
  - src/omnifocus_operator/contracts/use_cases/edit_task.py
  - src/omnifocus_operator/rrule/parser.py
  - src/omnifocus_operator/rrule/builder.py
  - src/omnifocus_operator/service/service.py
  - src/omnifocus_operator/service/validate.py
  - src/omnifocus_operator/server.py
  - tests/test_output_schema.py
  - tests/test_rrule.py
  - tests/test_models.py
  - docs/architecture.md
---

## Problem

The `Frequency` type is a Pydantic discriminated union with 9 subtypes (one per
frequency type). This creates three concrete problems now that the write side exists:

1. **Type required on every edit**: The discriminator forces agents to restate `type`
   even for same-type updates (e.g., changing interval on a daily task). Redundant
   and creates a failure mode if the agent sends the wrong type by mistake.

2. **Interval serialization workaround**: Can't use `exclude_defaults=True` because
   `type` is also a default on each subtype. A `@model_serializer` workaround was
   tried in Phase 32 but erased JSON Schema structure (Phase 32.1 emergency).
   Current state: `interval=1` always shown in output.

3. **9 subtype classes for one concept**: 9 classes + 1 base + 1 union for what is
   semantically one concept with 3 optional fields.

## Solution

Replace the 9-subtype discriminated union with three flat models:

### Read model (`models/repetition_rule.py`)

```python
class Frequency(OmniFocusBaseModel):
    type: str                              # required, no default -> survives exclude_defaults
    interval: int = 1                      # default 1 -> omitted by exclude_defaults
    on_days: list[str] | None = None       # only for weekly_on_days
    on: dict[str, str] | None = None       # only for monthly_day_of_week
    on_dates: list[int] | None = None      # only for monthly_day_in_month
```

### Write models (`contracts/`)

```python
class FrequencyAddSpec(CommandModel):      # extra="forbid" catches typos
    type: str                              # required
    interval: int = 1
    on_days: list[str] | None = None
    on: dict[str, str] | None = None
    on_dates: list[int] | None = None

class FrequencyEditSpec(CommandModel):     # extra="forbid" catches typos
    type: str | None = None                # optional - inferred from existing task
    interval: int | None = None            # None = preserve existing
    on_days: list[str] | None = None
    on: dict[str, str] | None = None
    on_dates: list[int] | None = None
```

### Why three models, not one

Architecture doc decision tree step 4: write models always inherit `CommandModel`
(`extra="forbid"`), read models inherit `OmniFocusBaseModel`. Base class difference
justifies separate models even when field shapes are identical.

### What this solves

- **Problem 1**: `FrequencyEditSpec` makes `type` optional. Service infers from
  existing task. Agent sends `{frequency: {interval: 5}}` and it works.
- **Problem 2**: `exclude_defaults=True` omits `interval=1` (has default), keeps
  `type` (no default). No custom serializer needed.
- **Problem 3**: 11 types -> 3 focused classes.

### What moves where

Cross-type field validation (reject `on_days` on `daily`, etc.) moves from Pydantic
structural validation to service layer. Already lives there per Phase 33 design
(VALID-02). D-02 explicitly anticipated this migration.

## Scope

Cross-cutting refactor:

- **Read model** (`models/repetition_rule.py`): 9 subtypes + union -> flat `Frequency`
- **Write models** (`contracts/`):
  - `FrequencyAddSpec` (CommandModel, type required)
  - `FrequencyEditSpec` (CommandModel, type optional)
  - `RepetitionRuleAddSpec` embeds `FrequencyAddSpec` (was: `Frequency` union)
  - `RepetitionRuleEditSpec` embeds `FrequencyEditSpec` (was: `Patch[Frequency]`)
- **RRULE parser**: Return flat `Frequency` instead of subtypes
- **RRULE builder**: Accept flat `Frequency` instead of union
- **Service layer**: Cross-type field validation + type-optional merge logic
- **Tests**: Update all tests referencing specific frequency subtypes
- **Output schema tests**: Verify flat model output validates against MCP outputSchema
- **Tool descriptions** (`server.py`): `type` becomes optional on edit
- **Architecture doc**: Update Frequency Types table (lines 508-519)

Breaking change on read output — acceptable (pre-release, single user, from source).

## What NOT to change

- `RepetitionRule` container (frequency + schedule + basedOn + end)
- `Schedule`, `BasedOn` enums
- `EndCondition` union (EndByDate | EndByOccurrences)
- Bridge payload format (ruleString + scheduleType + anchorDateKey + catchUpAutomatically)
- Tool description format for add_tasks

## Depends On

Phase 33 (write model must exist before type can be made optional on edits).
