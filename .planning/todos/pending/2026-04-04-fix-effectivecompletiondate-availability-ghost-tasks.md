---
created: 2026-04-04T13:49:52.656Z
title: Fix effectiveCompletionDate availability ghost tasks
area: repository
files:
  - src/omnifocus_operator/repository/hybrid/hybrid.py
---

## Problem

Tasks with `effectiveCompletionDate` set still report `availability: "available"` and `completionDate: null`. These "ghost" tasks appear in default queries (available + blocked), polluting results with tasks that are effectively done.

Example: task `a5Wy7iqIVxX` ("Trash Bag") has `effectiveCompletionDate: "2026-03-10T22:28:40.694000Z"` but `availability: "available"`. In the "Get Ready To Leave" project, this caused 354 tasks returned instead of the current active instance, because completed repetitions of subtasks were incorrectly marked as available. Also breaks hierarchy reconstruction — orphaned completed subtasks reference parent tasks that are correctly filtered out.

## Solution

If `effectiveCompletionDate` is set, `availability` should be `"completed"` and the task should not appear in default (available + blocked) queries. Needs investigation into whether this is a SQLite mapping issue or a bridge data issue.
