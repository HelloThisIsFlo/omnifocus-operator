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
  - .planning/phases/02-data-models/02-CONTEXT.md:52
---

## Problem

An audit of all 32 nullable model fields found 8 that are incorrectly nullable — OmniFocus
always provides these values, so `| None = None` masks potential data corruption instead of
failing fast.

Additionally, live testing revealed that **OmniFocus Automation enum objects are opaque** —
`.name`, `String()`, `.toString()` all return `undefined`. The inline `x.status.name` pattern
on projects/tags/folders is therefore **actively broken**, always producing `None`. The nullable
type annotation hides this bug.

Full analysis: `.research/Deep Dives/Model Nullable Fields/nullable-fields-audit.md`

## Solution

### Bridge changes (JavaScript) — do first

1. **Create `es()` switch function** for `EntityStatus` (like existing `ts()` for `TaskStatus`).
   Use `Project.Status.*` constants. Replace broken inline `.status.name` on projects (line
   115), tags (line 156), and folders (line 170).
2. **Fix `ts()` fallback** — change `return null` (line 47) to
   `throw new Error("Unknown TaskStatus: " + s)`. The `dispatch()` try-catch handles errors.
3. **All enum switches should throw on unknown values** — fail-fast at the bridge boundary.
4. **Verify via UAT** that `Project.Status.*` constants work for tag/folder status comparison
   (they may use `Tag.Status.*` or `Folder.Status.*` instead).

### Model changes (Python) — after bridge is fixed

5. **Make 6 timestamp fields required** — remove `| None = None` from `added`/`modified` on
   Task, Tag, Folder. Confirmed always-present by live testing.
6. **Make 3 status fields required** — remove `| None = None` from `status: EntityStatus` on
   Project, Tag, Folder. Only after `es()` is working.
7. **Update tests** — remove test cases that set these to `None`.

### Cleanup

8. **Update 02-CONTEXT.md** — remove invalidated requirement about replacing `ts()` with
   `.name` (line 52).
