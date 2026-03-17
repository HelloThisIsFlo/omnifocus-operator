---
title: "Investigate dropped+repeating task completion warning accuracy"
status: pending
priority: P2
source: "promoted from /gsd:note"
created: 2026-03-17
theme: general
---

## Goal

Verify whether OmniFocus actually creates a new occurrence when you complete a task that was already dropped but has a repetition rule.

## Context

Promoted from quick note captured on 2026-03-17 16:45.

The test `test_lifecycle_cross_state_repeating_stacked_warnings` in `tests/test_service.py` asserts both warnings stack when completing a dropped+repeating task:
- "Task was already dropped -- lifecycle action applied, task is now complete."
- "Repeating task -- this occurrence completed, next occurrence created."

The second warning might be inaccurate — a dropped task may no longer repeat, so OmniFocus might not create a new occurrence. If so, we're giving the user misleading information.

## Acceptance Criteria

- [ ] UAT-tested against real OmniFocus: drop a repeating task, then complete it, observe whether a new occurrence appears
- [ ] If the warning is inaccurate, file a follow-up todo to fix/suppress it in this scenario
