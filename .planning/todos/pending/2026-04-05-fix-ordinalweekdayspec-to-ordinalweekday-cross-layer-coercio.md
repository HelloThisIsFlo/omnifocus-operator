---
created: 2026-04-05T20:21:07.816Z
title: "Fix OrdinalWeekdaySpec → OrdinalWeekday cross-layer coercion in edit pipeline"
area: service
files:
  - src/omnifocus_operator/contracts/shared/repetition_rule.py:175
  - src/omnifocus_operator/service/service.py:766-769
  - src/omnifocus_operator/models/repetition_rule.py:190-196
---

## Problem

Regression introduced by commit `cf0d426` ("replace opaque on: dict with typed OrdinalWeekday models").

The contract layer defines `OrdinalWeekdaySpec` (inherits `CommandModel`) for agent input, while the core model `Frequency` expects `OrdinalWeekday` (inherits `BaseModel`). Pydantic v2 treats these as distinct model types and refuses to coerce one into the other, even though they have identical fields.

**How it breaks:**

1. Agent sends `edit_tasks` with `repetitionRule.frequency.on: {"last": "friday"}`
2. Pydantic correctly parses the dict into an `OrdinalWeekdaySpec` instance at the contract boundary
3. `_build_frequency_from_edit_spec` (service.py:766-769) iterates specialization fields and passes the `OrdinalWeekdaySpec` instance directly into a dict fed to `Frequency.model_validate()`
4. `Frequency.model_validate()` rejects it: _"Input should be a valid dictionary or instance of OrdinalWeekday"_

**Why it worked before:** The `on` field was typed as `dict[str, str]`, so it arrived as a plain dict and Pydantic v2 happily coerced `{"last": "friday"}` → `OrdinalWeekday`. The typed refactoring replaced dict with `OrdinalWeekdaySpec` but didn't add a conversion step at the boundary where contract models hand off to core models.

**Scope:** Affects both `_build_frequency_from_edit_spec` (type change / fresh build paths) and likely `_merge_frequency` in domain.py — anywhere an `OrdinalWeekdaySpec` crosses into core model territory.

Confirmed with:
```python
Frequency.model_validate({"type": "monthly", "interval": 2, "on": OrdinalWeekdaySpec(last="friday")})
# → ValidationError: Input should be a valid dictionary or instance of OrdinalWeekday
```

## Solution

TBD — the conversion needs to happen at the boundary where contract spec objects are fed into core model construction. Multiple approaches possible (`.model_dump()`, explicit conversion, shared base). Leave approach choice to implementer.
