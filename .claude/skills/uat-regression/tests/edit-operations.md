---
suite: edit-operations
display: Edit Operations
test_count: 34

setup: |
  ### Task Hierarchy

  Create this structure in the inbox using `add_tasks`:

  ```
  UAT-EditOps (parent)
  +-- T1-NoteOps
  +-- T2-FieldEditing
  +-- T3-NoopWarnings
  +-- T4-StatusComplete
  +-- T5-StatusDrop
  +-- T6-Errors
  ```

  Create the parent first, then all children (can be parallel). Store all IDs.

  ### Post-Create

  1. `edit_tasks` on T4-StatusComplete: `actions: { lifecycle: "complete" }`
  2. `edit_tasks` on T5-StatusDrop: `actions: { lifecycle: "drop" }`

  ### Verify

  T4: availability=completed
  T5: availability=dropped
---

# Edit Operations Test Suite

Tests field editing, patch semantics, no-op warnings, status warnings, error handling, and combo scenarios for `edit_tasks`.

## Conventions

- **Inbox only.** Never create tasks in projects. Every task goes to inbox (no `parent` for top-level, or under the test parent task).
- **Timezone required.** Date fields need timezone info in ISO 8601 (e.g., `+01:00` or `Z`). Without it, Pydantic rejects the value.
- **Note operations via `actions.note`.** Top-level `note:` on `edit_tasks` was removed in Phase 55. Use `actions: { note: { replace: ... } }` to set or clear, `actions: { note: { append: "..." } }` to append. `append` and `replace` are mutually exclusive in a single action; at least one must be set. `add_tasks` still accepts top-level `note:` as initial content (unchanged).

## Tests

### 1. Note Operations

#### Test 1a: replace: null clears the note
1. Seed a note on T1: `edit_tasks` on T1 with `actions: { note: { replace: "hello" } }`
2. `edit_tasks` on T1 with `actions: { note: { replace: null } }`
3. PASS if: success, no error; confirm via `get_task` that the note is cleared (empty or absent)

#### Test 1b: replace: "" clears the note
1. Seed a note on T1: `edit_tasks` on T1 with `actions: { note: { replace: "some text" } }`
2. `edit_tasks` on T1 with `actions: { note: { replace: "" } }`
3. `get_task` T1 and verify note is `""` (empty string, not `null`)
4. PASS if: success, note is `""` (empty string)

#### Test 1c: append adds content with single newline separator
1. Seed T1: `edit_tasks` on T1 with `actions: { note: { replace: "existing content" } }`
2. `edit_tasks` on T1 with `actions: { note: { append: "added content" } }`
3. `get_task` T1 and verify note is exactly `"existing content\nadded content"` — ONE `\n` separator, not `\n\n`
4. PASS if: note is `"existing content\nadded content"` (single-newline separator per NOTE-02 revision)

#### Test 1d: append on empty note sets directly (no leading separator)
1. Ensure T1 has empty note: `edit_tasks` on T1 with `actions: { note: { replace: null } }`
2. `edit_tasks` on T1 with `actions: { note: { append: "first content" } }`
3. `get_task` T1 and verify note is exactly `"first content"` — no leading newline, no leading whitespace
4. PASS if: note is `"first content"` with no leading separator

#### Test 1e: append on whitespace-only note sets directly
1. Seed T1 with a whitespace-only note: `edit_tasks` on T1 with `actions: { note: { replace: "   " } }` (three spaces)
2. `edit_tasks` on T1 with `actions: { note: { append: "clean content" } }`
3. `get_task` T1 and verify note is exactly `"clean content"` — original whitespace discarded, no leading separator
4. PASS if: note is `"clean content"` (whitespace-only existing treated as empty per strip-and-check rule)

#### Test 1f: append "" is a no-op with warning
1. Seed T1: `edit_tasks` on T1 with `actions: { note: { replace: "baseline" } }`
2. `edit_tasks` on T1 with `actions: { note: { append: "" } }`
3. `get_task` T1 and verify note is unchanged at `"baseline"`
4. PASS if: success with a warning — warning is present, fluent from an agent's perspective (mentions empty append is a no-op), contains NO internals (`type=`, `pydantic`, `input_value`, `_Unset`); note value unchanged

#### Test 1g: append with whitespace-only argument is a no-op with warning
1. Seed T1: `edit_tasks` on T1 with `actions: { note: { replace: "baseline" } }`
2. `edit_tasks` on T1 with `actions: { note: { append: "   " } }` (three spaces)
3. `get_task` T1 and verify note is unchanged at `"baseline"`
4. PASS if: success with a warning — same fluency/no-internals bar as 1f; note unchanged. Whitespace-only append is treated identically to empty per NOTE-02 revision (2026-04-17).

#### Test 1h: replace with identical content is a no-op with warning
1. Seed T1: `edit_tasks` on T1 with `actions: { note: { replace: "same content" } }`
2. `edit_tasks` on T1 with `actions: { note: { replace: "same content" } }` (repeat the exact value)
3. PASS if: success with a warning — warning is present, fluent (mentions the note already has this content), no internals leak; note value unchanged

#### Test 1i: replace empty on already-empty note is a no-op with warning
1. Ensure T1 has empty note: `edit_tasks` on T1 with `actions: { note: { replace: null } }`
2. `edit_tasks` on T1 with `actions: { note: { replace: null } }` (clear again)
3. PASS if: success with a warning — warning is present, fluent (mentions the note is already empty), no internals leak. Also run a follow-up: `actions: { note: { replace: "" } }` on the still-empty note — same warning shape.

### 2. Field Editing

#### Test 2a: Patch semantics
1. Set `name: "T2-Updated", flagged: true, estimatedMinutes: 30` plus `actions: { note: { replace: "test note" } }` on T2 (top-level name/flagged/estimatedMinutes combined with the note action in a single call)
2. Edit only `flagged: false` on T2
3. `get_task` T2 and verify: name still "T2-Updated", note still "test note", estimatedMinutes still 30, `flagged` absent from response (false → stripped), `inheritedFlagged` absent (T2 is in inbox — no ancestor to inherit from)
4. PASS if: untouched fields preserved; flagged=false self-stripped from output; no inheritedFlagged leaks in on inbox tasks

#### Test 2b: Date fields set + clear
1. `dueDate: "2026-03-15T17:00:00+01:00", deferDate: "2026-03-10T09:00:00+01:00"` on T2
2. Verify success
3. `dueDate: null, deferDate: null` on T2
4. PASS if: both set and clear succeed

#### Test 2c: estimatedMinutes set + clear
1. `estimatedMinutes: 45` on T2
2. `estimatedMinutes: null` on T2
3. PASS if: both succeed

#### Test 2d: Name change
1. `name: "T2-Renamed"` on T2
2. Verify response shows new name
3. `name: "T2-FieldEditing"` (rename back)
4. PASS if: both succeed, response reflects new name

#### Test 2e: Multi-field single call (note via actions)
1. `flagged: true, estimatedMinutes: 60, dueDate: "2026-03-20T12:00:00+01:00"` plus `actions: { note: { replace: "multi" } }` on T2 (three top-level fields + note action in a single call)
2. `get_task` to verify all four effects landed (note="multi", estimatedMinutes=60, dueDate set, flagged=true), plus `inheritedFlagged` absent (T2 sets its own flagged → self-shadowed) and `inheritedDueDate` absent (T2 sets its own dueDate → self-shadowed)
3. PASS if: all four changes applied in one call (note via actions, the other three at top level); inherited* counterparts are absent (self-shadow)

#### Test 2f: plannedDate set + clear
1. `plannedDate: "2026-03-12T10:00:00+01:00"` on T2
2. `get_task` to verify `plannedDate` is set AND `inheritedPlannedDate` is absent (self-shadowed since T2 sets its own plannedDate)
3. `plannedDate: null` on T2
4. PASS if: both set and clear succeed; when set, the own field is present and its inherited* counterpart is absent (self-shadow)

#### Test 2g: Naive datetime on edit
1. `dueDate: "2026-07-15T14:00:00"` on T2 (no Z, no offset — naive local)
2. `get_task` on T2
3. PASS if: edit succeeds; no error; `dueDate` in response contains `2026-07-15` and `14:00`
4. Clean up: `dueDate: null` on T2

### 3. No-Op Warnings

#### Test 3a: No-op — empty edit
1. Edit T3 with only `id`, no other fields
2. PASS if: success with warning about no changes specified

#### Test 3b: No-op — same flagged
1. `flagged: true` on T3
2. `flagged: true` again on T3
3. PASS if: second call returns warning about no changes detected

#### Test 3c: No-op — same name
1. `name: "T3-NoopWarnings"` on T3 (its current name)
2. PASS if: warning about no changes detected

#### Test 3d: No-op — same dueDate
1. `dueDate: "2026-04-01T12:00:00+01:00"` on T3
2. `dueDate: "2026-04-01T12:00:00+01:00"` again on T3
3. PASS if: second call returns warning about no changes detected
4. Clean up: `dueDate: null` on T3

#### Test 3e: No-op — same estimatedMinutes
1. `estimatedMinutes: 15` on T3
2. `estimatedMinutes: 15` again on T3
3. PASS if: second call returns warning about no changes detected
4. Clean up: `estimatedMinutes: null` on T3

#### Test 3f: No-op — same deferDate
1. `deferDate: "2026-04-01T09:00:00+01:00"` on T3
2. `deferDate: "2026-04-01T09:00:00+01:00"` again on T3
3. PASS if: second call returns warning about no changes detected
4. Clean up: `deferDate: null` on T3

#### Test 3g: No-op — same plannedDate
1. `plannedDate: "2026-04-01T10:00:00+01:00"` on T3
2. `plannedDate: "2026-04-01T10:00:00+01:00"` again on T3
3. PASS if: second call returns warning about no changes detected
4. Clean up: `plannedDate: null` on T3

### 4. Status Warnings

#### Test 4a: Editing a completed task
1. `flagged: true` on T4 (completed by user in setup)
2. `get_task` T4 to verify `flagged: true` actually took effect
3. PASS if: success with warning mentioning "completed", AND `get_task` confirms flagged is true

#### Test 4b: Editing a dropped task
1. `name: "T5-Dropped"` on T5 (dropped by user in setup)
2. PASS if: success with warning mentioning "dropped"

### 5. Error Handling

Run each INDIVIDUALLY (they will error):

#### Test 5a: Nonexistent task ID
1. `edit_tasks` with `id: "nonexistent-id-12345", name: "nope"`
2. PASS if: clean error mentioning "not found"

#### Test 5b: Empty name
1. `name: ""` on T6
2. PASS if: error about name cannot be empty

### 6. Combinations

#### Test 6a: note clear via actions + field change
1. Seed T1: `edit_tasks` on T1 with `actions: { note: { replace: "will be cleared" } }` and `flagged: false` (single call combining top-level flag + note action)
2. `edit_tasks` on T1 with `actions: { note: { replace: null } }` and `flagged: true` (single call clearing the note + flipping flagged)
3. `get_task` T1 and verify note is cleared and flagged is true
4. PASS if: success, both effects applied per call, no error — demonstrates actions.note composes with top-level fields

#### Test 6b: No-op on completed task — status warning suppressed
1. `flagged: true` on T4 (already completed, already flagged from Test 4a)
2. PASS if: only "no changes detected" warning — the status warning ("your changes were applied") must NOT appear since nothing changed

### 7. Task Property Surface (Phase 56)

New writable task fields — `completesWithChildren: Patch[bool]` and `type: Patch[TaskType]` where `TaskType = "parallel" | "sequential"`. Both reject `null` (Patch[bool]/Patch[enum] have no cleared state); `"singleActions"` is rejected naturally via the TaskType enum.

#### Test 7a: Edit completesWithChildren
1. `edit_tasks` on T2 with `completesWithChildren: true`
2. `get_task` T2 with `include: ["hierarchy"]` and verify `completesWithChildren: true`
3. `edit_tasks` on T2 with `completesWithChildren: false`
4. `get_task` T2 with `include: ["hierarchy"]` and verify `completesWithChildren: false` (always present in hierarchy group, including when false — PROP-08 / NEVER_STRIP)
5. PASS if: both set-true and set-false succeed; hierarchy response shows the written value each time

#### Test 7b: Edit type
1. `edit_tasks` on T2 with `type: "sequential"`
2. `get_task` T2 with `include: ["hierarchy"]` and verify `type: "sequential"`
3. `edit_tasks` on T2 with `type: "parallel"`
4. `get_task` T2 with `include: ["hierarchy"]` and verify `type: "parallel"`
5. PASS if: both flips succeed and round-trip correctly

#### Test 7c: completesWithChildren: null rejected
Run INDIVIDUALLY (will error):
1. `edit_tasks` on T6 with `completesWithChildren: null`
2. PASS if: error — fluent from an agent's perspective (explains booleans have no cleared state / omit instead of null); does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 7d: type: null rejected
Run INDIVIDUALLY (will error):
1. `edit_tasks` on T6 with `type: null`
2. PASS if: error — fluent (same shape as 7c: null not valid for `type`; omit to leave unchanged); does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

#### Test 7e: type="singleActions" rejected
Run INDIVIDUALLY (will error):
1. `edit_tasks` on T6 with `type: "singleActions"`
2. PASS if: error — valid values are `parallel` and `sequential` (enum validation; `singleActions` is projects-only and not writable on tasks); does NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`

## Report Table Rows

| # | Test | Description | Result |
|---|------|-------------|--------|
| 1a | Note replace: null | `actions.note.replace: null` clears the note | |
| 1b | Note replace: "" | `actions.note.replace: ""` clears the note; get_task shows `""` | |
| 1c | Append with newline | Append to existing note joins with single `\n` (not `\n\n`) | |
| 1d | Append on empty | Append on empty note sets content directly; no leading separator | |
| 1e | Append on whitespace | Append on whitespace-only note sets directly; original whitespace discarded | |
| 1f | Append "" no-op | `append: ""` → success + warning; note unchanged; no internals leak | |
| 1g | Append whitespace-only no-op | `append: "   "` → success + warning (treated as empty per NOTE-02 revision) | |
| 1h | Replace identical no-op | Replacing with identical content → warning; no internals leak | |
| 1i | Replace empty on empty | Clearing an already-empty note → warning; covers both `null` and `""` | |
| 2a | Patch semantics | Editing one field preserves others; flagged=false self-strips; no inheritedFlagged on inbox tasks | |
| 2b | Date set + clear | Setting dueDate and deferDate, then clearing both with null | |
| 2c | estimatedMinutes set + clear | Setting estimatedMinutes, then clearing with null | |
| 2d | Name change | Renaming a task; response reflects the new name | |
| 2e | Multi-field single call (note via actions) | Top-level fields + `actions.note.replace` composed in one call; inherited* counterparts absent (self-shadow) | |
| 2f | plannedDate set + clear | Set plannedDate; inheritedPlannedDate self-shadowed (absent); then clear | |
| 2g | Naive datetime on edit | Naive local datetime (no Z) accepted; dueDate set correctly | |
| 3a | No-op: empty edit | Sending only an ID with no fields returns "no changes specified" | |
| 3b | No-op: same flagged | Setting flagged to its current value returns "no changes detected" | |
| 3c | No-op: same name | Setting name to its current value returns a warning | |
| 3d | No-op: same dueDate | Setting dueDate to the same value returns a warning | |
| 3e | No-op: same estimatedMinutes | Setting estimatedMinutes to its current value returns a warning | |
| 3f | No-op: same deferDate | Setting deferDate to the same value returns a warning | |
| 3g | No-op: same plannedDate | Setting plannedDate to the same value returns a warning | |
| 4a | Status: completed task | Editing completed task warns; get_task confirms edit took effect | |
| 4b | Status: dropped task | Editing a dropped task succeeds with "dropped" warning | |
| 5a | Error: nonexistent task | Editing a fake task ID returns "not found" | |
| 5b | Error: empty name | Setting name to "" returns a validation error | |
| 6a | Combo: note clear via actions + field | `actions.note.replace: null` + `flagged: true` in one call; both applied | |
| 6b | No-op on completed | No-op suppresses status warning, shows only "no changes" | |
| 7a | Edit: completesWithChildren | Set-true and set-false both round-trip via hierarchy include (`false` always present per PROP-08) | |
| 7b | Edit: type | Flip `parallel` ↔ `sequential`; both round-trip via hierarchy include | |
| 7c | Error: completesWithChildren: null | `null` rejected; fluent error (Patch[bool] has no cleared state); no pydantic internals | |
| 7d | Error: type: null | `null` rejected; fluent error (omit to leave unchanged); no pydantic internals | |
| 7e | Error: type="singleActions" | Enum rejects `singleActions`; valid values are `parallel`/`sequential`; no pydantic internals | |
