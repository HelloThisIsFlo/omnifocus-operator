---
created: 2026-04-02T14:46:20.410Z
title: Convert specs to core models at service boundary
area: service
files:
  - src/omnifocus_operator/service/payload.py:66-70
  - src/omnifocus_operator/service/payload.py:120-123
  - src/omnifocus_operator/rrule/builder.py:70-71
  - src/omnifocus_operator/rrule/builder.py:103-108
---

## Problem

Contract spec types leak past the service boundary into lower layers (builder, payload). This forces union signatures (`Frequency | FrequencyAddSpec`, `EndCondition | EndConditionSpec`) and in the case of `EndConditionSpec`, caused `isinstance` dispatch to be replaced with `hasattr` duck-typing in `builder.py`.

**Pre-existing (on main):**
- `builder.py:70` — `frequency: Frequency | FrequencyAddSpec`
- `payload.py:120` — `frequency: Frequency | FrequencyAddSpec`

**Added by phase 36.4:**
- `builder.py:71` — `end: EndByDate | EndByOccurrences | EndConditionSpec | None`
- `payload.py:123` — `end: EndCondition | EndConditionSpec | None`
- `builder.py:103-108` — `hasattr` duck-typing replacing `isinstance`

Note: `FrequencyEditSpec` in `domain.py:merge_frequency()` is different — it carries UNSET/None/value semantics needed for the merge. The output is already a `Frequency`. This is fine as-is.

## Solution

In `_build_repetition_rule_payload` (payload.py), convert specs to core models before calling `build_rrule`:
- `FrequencyAddSpec → Frequency` via `Frequency.model_validate(spec.model_dump())`
- `EndConditionSpec → EndCondition` (e.g., `EndByDate(date=spec.end.date)`)

Then:
- `build_rrule` signature returns to `frequency: Frequency, end: EndByDate | EndByOccurrences | None`
- `isinstance` dispatch restored in builder.py
- Payload signatures lose the union types

The service layer already does this round-trip for frequency normalization (service.py:461) — just extend the pattern to the payload boundary and stop converting back to specs.
