---
status: resolved
trigger: "edit_tasks with actions.tags.replace doesn't remove existing tags"
created: 2026-03-10T00:00:00Z
updated: 2026-03-10T12:00:00Z
---

## Current Focus

hypothesis: get_task() does not respect the _stale flag, reads stale SQLite data for current_ids
test: confirmed by code reading -- get_task lacks stale check that get_all has
expecting: n/a -- confirmed
next_action: return diagnosis

## Symptoms

expected: replace: ["Checklist"] on task with [Sandbox, New Tag] should result in only [Checklist]
actual: Task ends up with all 3 tags [Sandbox, New Tag, Checklist]. replace: [] doesn't clear tags either.
errors: None -- reports success
reproduction: UAT flow where prior steps modify tags, then replace is called
started: After Phase 16.2 refactor (diff-based tag handling)

## Eliminated

(none needed -- root cause found on first hypothesis)

## Evidence

- timestamp: 2026-03-10
  checked: service.py _compute_tag_diff logic (lines 387-473)
  found: Diff logic is correct -- computes to_add and to_remove properly from final vs current_ids
  implication: Bug is not in the diff algorithm itself

- timestamp: 2026-03-10
  checked: HybridRepository.get_task() (line 682-687) vs get_all() (line 479-487)
  found: get_task() reads SQLite directly without checking _stale flag. get_all() checks _stale and waits for fresh data.
  implication: After a prior write, get_task returns stale data with old/missing tags

- timestamp: 2026-03-10
  checked: service.py edit_task flow (lines 125, 194, 363)
  found: task = get_task (NO stale wait) then _compute_tag_diff uses task.tags as current_ids, but _resolve_tags calls get_all (WITH stale wait)
  implication: current_ids from stale read, resolved_ids from fresh read -- mismatch causes wrong diff

- timestamp: 2026-03-10
  checked: What happens when current_ids is empty/stale
  found: If current_ids={} but task actually has {A,B}, then to_remove = {} - final = {} (nothing removed). to_add = final (tag added). Result: old tags kept + new tag added.
  implication: Perfectly explains the symptom of all 3 tags appearing

## Resolution

root_cause: HybridRepository.get_task() does not respect the _stale flag. When edit_task is called after a prior write operation, get_task reads stale SQLite data. The task's current tags (current_ids) are wrong/empty, so _compute_tag_diff computes an incorrect diff -- it never generates removeTagIds because it thinks the task has no tags to remove.
fix: (not applied -- diagnosis only)
verification: (not applied)
files_changed: []
