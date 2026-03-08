---
status: resolved
trigger: "removeTags alone crashes with undefined is not an object (evaluating 'params.tagIds.map')"
created: 2026-03-08T00:00:00Z
updated: 2026-03-08T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - mismatch between service layer payload keys and bridge.js expected keys for "remove" mode
test: code review of both layers
expecting: service sends removeTagIds, bridge reads tagIds
next_action: return diagnosis

## Symptoms

expected: When only `removeTags` is provided, bridge removes those tags from the task
actual: Crashes with `undefined is not an object (evaluating 'params.tagIds.map')`
errors: `undefined is not an object (evaluating 'params.tagIds.map')`
reproduction: Call edit_task with only removeTags (no addTags/tags)
started: Since edit_tasks implementation

## Eliminated

(none needed -- root cause found on first hypothesis)

## Evidence

- timestamp: 2026-03-08T00:00:00Z
  checked: service.py lines 181-194 (remove-only branch)
  found: Service sends `tagMode: "remove"` + `removeTagIds: [...]` (no `tagIds` key)
  implication: Bridge will receive params without `tagIds`

- timestamp: 2026-03-08T00:00:00Z
  checked: bridge.js lines 290-295 (remove mode handler)
  found: Bridge reads `params.tagIds.map(...)` -- NOT `params.removeTagIds`
  implication: `params.tagIds` is undefined, calling `.map()` on undefined crashes

- timestamp: 2026-03-08T00:00:00Z
  checked: bridge.js lines 283-289 (add mode handler) for comparison
  found: Add mode also reads `params.tagIds` -- and service sends `tagIds` for add mode (line 180). So add mode works correctly.
  implication: The mismatch is specifically in remove mode

- timestamp: 2026-03-08T00:00:00Z
  checked: bridge.js lines 297-314 (add_remove mode handler)
  found: add_remove mode correctly reads `params.removeTagIds` and `params.addTagIds`
  implication: The "remove" mode handler was written inconsistently with "add_remove" mode

- timestamp: 2026-03-08T00:00:00Z
  checked: handleEditTask.test.js lines 283-294 (remove mode test)
  found: Test passes `tagIds` directly to bridge -- masking the real-world bug where service sends `removeTagIds`
  implication: Test doesn't reflect actual service-to-bridge contract for remove mode

## Resolution

root_cause: |
  Two bugs, both in bridge.js `handleEditTask`, lines 290-295:

  1. **Primary bug**: The "remove" mode handler reads `params.tagIds` but the service layer sends `params.removeTagIds` for remove-only mode. This causes the crash.

  2. **Test bug**: The Vitest test for remove mode (line 289) passes `tagIds` directly, which masks the real-world mismatch. The test should pass `removeTagIds` to match what the service actually sends.

fix: |
  In bridge.js, change the "remove" handler (lines 290-295) to read `params.removeTagIds` instead of `params.tagIds`:
  ```
  } else if (params.tagMode === "remove") {
      var removeObjs = params.removeTagIds.map(function (id) {
  ```

  In handleEditTask.test.js, update the remove mode test to pass `removeTagIds` instead of `tagIds`.

verification:
files_changed: []
