---
created: 2026-03-03T22:10:26.827Z
title: Enforce fail-fast on model nullable fields and simplify bridge status helpers
area: models
files:
  - src/omnifocus_operator/models/_task.py:34-35
  - src/omnifocus_operator/models/_tag.py:25-26,29
  - src/omnifocus_operator/models/_folder.py:25-26,29
  - src/omnifocus_operator/models/_project.py:31
  - src/omnifocus_operator/bridge/bridge.js:39-48,80,115-116,156,170
  - src/omnifocus_operator/models/_enums.py
---

## Problem

An audit of all 32 nullable model fields found 8 that are incorrectly nullable — OmniFocus
always provides these values, so `| None = None` masks potential data corruption instead of
failing fast. Additionally, the bridge script has a redundant `ts()` switch function and
defensive ternaries for status fields that should be simplified.

Full analysis: `.research/Deep Dives/Model Nullable Fields/nullable-fields-audit.md`

## Solution

### Model changes (Python) — make 8 fields required

Remove `| None = None` from:

- **`added` and `modified`** on Task, Tag, Folder (6 fields) — system-managed timestamps,
  always populated by OmniFocus
- **`status: EntityStatus`** on Project, Tag, Folder (3 fields) — every entity always has a
  lifecycle status (Active/Done/Dropped)

Update tests that explicitly set these to `None` — those test scenarios don't exist in the
real domain.

### Bridge changes (JavaScript)

- **Remove `ts()` function** (lines 39-48) — replace `ts(t.taskStatus)` with
  `t.taskStatus.name` on tasks and `ts(p.taskStatus)` with `p.taskStatus.name` on projects.
  Let Pydantic's `TaskStatus` StrEnum validate the string. This gives clearer error messages
  if OmniFocus ever adds new status values.
- **Simplify inline status ternaries** — replace `x.status ? x.status.name : null` with
  `x.status.name` on projects (line 115), tags (line 156), and folders (line 170). The
  `dispatch()` try-catch already handles unexpected errors gracefully.
