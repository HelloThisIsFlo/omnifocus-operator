---
created: "2026-03-18T23:12:24.083Z"
title: "Add Patch and PatchOrClear type aliases to command models"
area: contracts
files:
  - src/omnifocus_operator/contracts/base.py
  - src/omnifocus_operator/contracts/common.py
  - src/omnifocus_operator/contracts/use_cases/edit_task.py
  - src/omnifocus_operator/contracts/use_cases/create_task.py
---

## Problem

Command model field annotations don't visually distinguish value-only fields from clearable fields. You have to eyeball whether `None` is in the union:

```python
name: str | _Unset = UNSET           # value-only (can't clear)
note: str | None | _Unset = UNSET    # clearable (None = clear)
```

This is a core domain distinction that should be visible in the type.

## Solution

Add `Patch[T]` and `PatchOrClear[T]` aliases using `TypeVar` + `Union` (the only approach that produces clean JSON schema + passes mypy):

```python
T = TypeVar("T")
Patch = Union[T, _Unset]
PatchOrClear = Union[T, None, _Unset]
```

Then migrate annotations:
```python
name: Patch[str] = UNSET
note: PatchOrClear[str] = UNSET
```

Also add `changed_fields()` helper to `CommandModel`.

Schema output is byte-for-byte identical — pure readability change.

**Full investigation:** `.research/deep-dives/simplify-sentinel-pattern/FINDINGS.md`
