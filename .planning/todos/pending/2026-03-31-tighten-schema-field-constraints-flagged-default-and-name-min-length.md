---
created: 2026-03-31T21:22:38.974Z
title: "Tighten schema field constraints: flagged default and name min_length"
area: server
files:
  - src/omnifocus_operator/contracts/
---

## Problem

Two field definitions on command models are looser than they should be:

1. **`AddTaskCommand.flagged` is `Optional[bool] = None`** — Should be `bool = False`. No reason for null on creation; always send explicitly to bridge.
2. **`name` field allows empty string** — Add `min_length=1` on `AddTaskCommand.name` and `EditTaskCommand.name`.

## Solution

- Change `AddTaskCommand.flagged` to `bool = False`
- Add `min_length=1` to name fields
- Quick change, no architectural impact
