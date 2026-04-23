---
suite: integration-flows
display: Integration Flows
test_count: 8

discovery:
  needs:
    - type: tag
      label: tag-a
      filters: [available, unambiguous]
    - type: tag
      label: tag-b
      filters: [available, unambiguous]
    - type: tag
      label: tag-c
      filters: [available, unambiguous]

setup: |
  ### Tasks
  UAT-Integration (inbox parent)
  UAT-Integration-Alt (second inbox parent)
---

# Integration Flows Test Suite

End-to-end flows verifying write-through guarantees and data consistency across tools. Each test writes via one tool, then reads back via `get_task` to confirm persistence.

## Conventions

- **Inbox only.** Never create tasks in projects. Every task goes to inbox (no `parent` for top-level, or under the test parent task).
- **Timezone required.** Date fields need timezone info in ISO 8601 (e.g., `+01:00` or `Z`). Without it, Pydantic rejects the value.
- **Tags by ID.** Some tag names are ambiguous. Discover tags via `get_all` first, then use IDs where names might collide.
- **One item per call here.** This suite uses 1-item calls even though `add_tasks`/`edit_tasks` accept batches up to 50 items post-Phase 54 — sequential single-item calls keep each assertion focused on one round-trip.
- **Note operations via `actions.note`.** Top-level `note:` on `edit_tasks` was removed in Phase 55. Use `actions: { note: { replace: ... } }` or `actions: { note: { append: "..." } }`. `add_tasks` still accepts top-level `note:` as initial content.
- **Sequential tests.** Tests in this suite build on each other (G-1 creates the task, G-2 through G-7 modify and verify it). Run them in order.

## Tests

### G-1: Create → read-back all fields
1. `add_tasks` with:
   - `name: "G1-Roundtrip"`
   - `parent: "<UAT-Integration-id>"`
   - `tags: [<tag-a-name>]`
   - `dueDate: "2026-04-15T17:00:00+01:00"`
   - `flagged: true`
   - `estimatedMinutes: 25`
   - `note: "integration test"`
2. `get_task` on returned ID
3. PASS if: all fields match — name, `parent: {"task": {"id": "<UAT-id>", "name": "UAT-Integration"}}`, tag-a present, dueDate set, flagged true, estimatedMinutes 25, note contains "integration test"

### G-2: Edit fields → read-back
1. `edit_tasks` on G1's task: `name: "G1-Edited", flagged: false` plus `actions: { note: { replace: null } }` (top-level name/flagged combined with the note-clear action in one call)
2. `get_task` to verify
3. PASS if: name is "G1-Edited", flagged is false, note is empty/cleared

### G-3: Edit dates → read-back
1. `edit_tasks` on G1's task: `deferDate: "2026-04-10T09:00:00+01:00", plannedDate: "2026-04-12T10:00:00+01:00"`
2. `get_task` to verify
3. PASS if: deferDate and plannedDate are set to the specified values

### G-4: Move → read-back parent
1. `edit_tasks` on G1's task: `actions: { move: {"ending": "<UAT-Integration-Alt-id>"} }`
2. `get_task` to verify parent changed to UAT-Integration-Alt
3. PASS if: `parent.task.id` matches UAT-Integration-Alt and `parent.task.name` is present

### G-5: Move back → read-back parent
1. `edit_tasks` on G1's task: `actions: { move: {"ending": "<UAT-Integration-id>"} }`
2. `get_task` to verify parent changed back to UAT-Integration
3. PASS if: `parent.task.id` matches UAT-Integration and `parent.task.name` is present

### G-6: Tags replace → read-back
1. `edit_tasks` on G1's task: `actions: { tags: { replace: [<tag-b>, <tag-c>] } }`
2. `get_task` to verify exactly tag-b and tag-c present (tag-a gone)
3. PASS if: tags match exactly [tag-b, tag-c]

### G-7: Lifecycle → read-back
1. `edit_tasks` on G1's task: `actions: { lifecycle: "complete" }`
2. `get_task` to verify `availability` is `"completed"` and `completionDate` is set
3. PASS if: both fields confirmed

### G-8: get_all consistency
1. Call `get_all`
2. Find G1's task in the tasks list by ID
3. PASS if: task appears in `get_all` results with the same state as `get_task` (completed, name "G1-Edited", tags [tag-b, tag-c])

## Report Table Rows

| # | Test | Description | Result |
|---|------|-------------|--------|
| G-1 | Create → read-back | All fields round-trip correctly after add_tasks | |
| G-2 | Edit fields → read-back | Name, flagged, note changes reflected in get_task | |
| G-3 | Edit dates → read-back | deferDate and plannedDate set and confirmed | |
| G-4 | Move → read-back | Parent change to alt reflected in get_task | |
| G-5 | Move back → read-back | Parent change back reflected in get_task | |
| G-6 | Tags → read-back | Tag replace reflected in get_task | |
| G-7 | Lifecycle → read-back | Completion reflected in get_task | |
| G-8 | get_all consistency | Completed task appears correctly in full snapshot | |
