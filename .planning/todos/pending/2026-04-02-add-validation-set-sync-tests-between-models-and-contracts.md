---
created: 2026-04-02T14:46:20.410Z
title: Add validation set sync tests between models and contracts
area: models
files:
  - src/omnifocus_operator/models/repetition_rule.py
  - src/omnifocus_operator/contracts/shared/repetition_rule.py
  - tests/test_type_boundary.py
---

## Problem

Phase 36.4 moved `Literal` type aliases (`FrequencyType`, `DayCode`, `DayName`) from `models/` to `contracts/`. Core models use plain validation sets (`_VALID_DAY_CODES`, `_VALID_DAY_NAMES`) instead. These two representations of the same values can drift independently — if someone adds a day code to one but not the other, validation diverges silently.

Additionally, `FrequencyType` has no model-side validation set at all — `Frequency.type` is plain `str` with no runtime validator on the core model, unlike `DayCode`/`DayName` which have both.

## Solution

1. Add `_VALID_FREQUENCY_TYPES = {"minutely", "hourly", "daily", "weekly", "monthly", "yearly"}` to `models/repetition_rule.py`
2. Add a runtime validator on `Frequency.type` that checks against this set (matching pattern of `normalize_day_codes`/`normalize_day_name`)
3. Add sync tests (in `test_type_boundary.py`) that verify:
   - `set(get_args(DayCode)) == _VALID_DAY_CODES`
   - `set(get_args(DayName)) == _VALID_DAY_NAMES`
   - `set(get_args(FrequencyType)) == _VALID_FREQUENCY_TYPES`

Tests import from both `models/` and `contracts/` — no dependency cycle concern since tests aren't in the import graph.
