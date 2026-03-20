---
id: SEED-001
status: dormant
planted: 2026-03-20
planted_during: v1.2.1 Phase 23
trigger_when: repetition rule write support is being planned or implemented
scope: Small
---

# SEED-001: Investigate dropped+repeating task completion warning accuracy

## Why This Matters

We may be giving agents misleading information. When a dropped task with a repetition rule is completed, we warn "next occurrence created" — but OmniFocus might not actually create a new occurrence for a dropped task. If so, the agent acts on false info.

## When to Surface

**Trigger:** When repetition rule write support is being planned or implemented (v1.2.3)

This seed should be presented during `/gsd:new-milestone` when the milestone
scope matches any of these conditions:
- Repetition rule behavior is being added or modified
- Task lifecycle warnings are being reviewed
- Write-side repeating task semantics are being formalized

## Scope Estimate

**Small** — Manual UAT to verify the behavior, then a targeted warning fix if confirmed inaccurate.

## Breadcrumbs

- `tests/test_service.py` — `test_lifecycle_cross_state_repeating_stacked_warnings` asserts the potentially inaccurate warning
- `.research/updated-spec/MILESTONE-v1.2.3.md` — repetition rule write support spec
- `.planning/todos/pending/2026-03-17-investigate-dropped-repeating-task-warning-accuracy.md` — original todo (to be removed)

## Notes

Promoted from a quick note captured on 2026-03-17. The investigation is purely manual (UAT against real OmniFocus). The code fix, if needed, is small — suppress or conditionalize one warning string.
