---
created: 2026-03-22T14:24:25.129Z
title: Normalize completionDate and dropDate to presence check instead of stripping
area: testing
files:
  - tests/golden_master/normalize.py
  - tests/test_bridge_contract.py
---

## Problem

`completionDate` and `dropDate` are currently in `VOLATILE_TASK_FIELDS` — stripped entirely from golden master comparison. But whether the field is null vs non-null IS deterministic and meaningful:

- Completing a task should set `completionDate` to *something* (not null)
- An uncompleted task should have `completionDate = null`
- Same for `dropDate` with lifecycle `"drop"`

By stripping these fields entirely, the contract test misses a class of bugs where InMemoryBridge fails to populate them on lifecycle transitions.

## Solution

In `normalize_for_comparison()`, instead of stripping these fields, normalize non-null values to a sentinel:

```python
PRESENCE_ONLY_FIELDS = {"completionDate", "dropDate"}
for field in PRESENCE_ONLY_FIELDS:
    if field in result and result[field] is not None:
        result[field] = "<set>"
```

Then move `completionDate` and `dropDate` out of `VOLATILE_TASK_FIELDS` — they no longer need stripping since the exact timestamp is replaced by `"<set>"`.

This verifies that completing/dropping a task actually populates the date field, without caring about the exact timestamp (which legitimately differs between RealBridge and InMemoryBridge).
