---
created: 2026-04-14T18:10:03.401Z
title: Compute true inherited fields by walking parent hierarchy
area: service
files:
  - src/omnifocus_operator/server/projection.py
  - src/omnifocus_operator/repository/bridge_only/adapter.py
  - .planning/phases/53-response-shaping/53-UAT.md
---

## Problem

After renaming `effective*` to `inherited*` (Phase 53), OmniFocus's self-echo behavior is semantically wrong: a task with `plannedDate` shows `inheritedPlannedDate` with the same value even when no parent sets a planned date. "Inherited" implies "came from above" but OmniFocus always fills `effectiveX` with the resolved value regardless of source.

A heuristic approach (strip `inheritedX` when equal to `X`) was considered but rejected: booleans like `flagged` have high coincidental equality between parent and child, making the heuristic unreliable.

## Solution

Walk the parent hierarchy to determine whether an `inherited*` value actually comes from a parent. If the value originates from the task itself (no parent sets it), omit the `inherited*` field. The parent hierarchy is already walked for cycle detection, so the infrastructure exists. This gives correct semantics for all field types — dates and booleans alike.

## Origin

Discovered during Phase 53 UAT (Gap 1, test 1). Documented in `.planning/phases/53-response-shaping/53-UAT.md`.
