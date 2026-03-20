---
created: 2026-03-20T13:30:00.000Z
title: Add is_set TypeGuard helper to replace isinstance Unset checks
area: contracts
files:
  - src/omnifocus_operator/contracts/base.py
  - src/omnifocus_operator/service/service.py
  - src/omnifocus_operator/service/domain.py
  - src/omnifocus_operator/service/payload.py
  - src/omnifocus_operator/service/validate.py
  - src/omnifocus_operator/contracts/common.py
---

## Problem

21 occurrences of `not isinstance(x, _Unset)` across 5 files. The double negative is noisy and hurts readability. Every new field that uses `_Unset` adds more of these.

## Solution

Add a `TypeGuard` helper to `contracts/base.py`:

```python
from typing import TypeGuard, TypeVar

T = TypeVar("T")

def is_set(value: T | _Unset) -> TypeGuard[T]:
    """True if value was explicitly provided (not UNSET)."""
    return not isinstance(value, _Unset)
```

Then replace all 21 occurrences:
- `not isinstance(x, _Unset)` → `is_set(x)`
- `isinstance(x, _Unset)` → `not is_set(x)`

TypeGuard bonus: mypy narrows the type after the check, so `command.actions` is known to be `ActionsGroup` (not `ActionsGroup | _Unset`) inside the `if` block. May allow removing some `# type: ignore` comments in service.py.

Quick task scope: add helper, find-and-replace, verify mypy + tests.
