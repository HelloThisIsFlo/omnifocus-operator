---
suite: inheritance
display: Inheritance
test_count: 16

discovery:
  needs:
    - type: project
      label: dated-project
      filters: [active, has_due, has_defer, has_planned, flagged]
    - type: project
      label: undated-project
      filters: [active, no_due, no_defer, no_planned, not_flagged]

setup: |
  Store dated-project's dueDate, deferDate, plannedDate values — these are the
  expected inherited values for direct-inheritance assertions.

  ### Tasks

  Tasks under dated-project:
    T1-InheritDirect
    T2-ChainParent
      T2a-ChainChild
    T3-L1
      T3a-L2
        T3b-L3
    T4-MoveAway
    T6-OwnOverride
    T7-ChainMoveParent
      T7a-ChainMoveChild
    T8-AggParent (own dueDate=2020-01-01T00:00:00Z, own deferDate=2040-01-01T00:00:00Z, own plannedDate=2030-06-15T00:00:00Z)
      T8a-AggChild (no own dates)
    T9-CompletionParent
      T9a-CompletionChild
    T10-DropParent
      T10a-DropChild

  Tasks in inbox (no parent):
    T5-MoveIn
    T11-NoAncestor (no own dates, flagged unset — used as "no-self-echo" regression guard in Test 6d)

  Creation order:
  1. T1, T2, T3, T4, T5, T6, T7, T8, T9, T10 (parallel — all but T5 under dated-project)
  2. T2a, T3a, T7a, T8a, T9a, T10a (parallel, need parents from step 1)
  3. T3b under T3a (needs T3a from step 2)

  ### Post-Create (lifecycle for new-pair tests)

  1. `edit_tasks` on T9-CompletionParent: `actions: { lifecycle: "complete" }`
  2. `edit_tasks` on T10-DropParent: `actions: { lifecycle: "drop" }`

  ### Verify
  - T9-CompletionParent: availability=completed. T9a-CompletionChild: OmniFocus will typically cascade-complete the
    child (T9a.availability=completed), but T9a has no OWN `completionDate` — the completion is inherited. That's the
    state Test 8a verifies.
  - T10-DropParent: availability=dropped. T10a-DropChild: same cascade behavior expected; T10a has no OWN `dropDate`.

manual_actions:
  - "If dated-project or undated-project profiles are missing, tell user exactly what to create or configure and wait for confirmation."
---

# Inheritance Test Suite

Tests truly inherited fields (Phase 53.1 semantics) — `inheritedDueDate`, `inheritedDeferDate`, `inheritedPlannedDate`, `inheritedFlagged`, `inheritedCompletionDate`, `inheritedDropDate` — emitted on tasks only when an ancestor sets the field. `inheritedX` means "an ancestor above me set X" — NOT "OmniFocus echoed my own value back." Own and inherited values coexist independently: when a task sets its own `dueDate` AND an ancestor also sets `dueDate`, the response emits BOTH `dueDate` (own) AND `inheritedDueDate` (ancestor's aggregated value). The walk strips `inherited*` only when NO ancestor contributed (walk yields None/False → stripped — "no self-echo" regression guard). Aggregation rules across multiple ancestors: min for due, max for defer, first-found for planned/drop/completion, any-True for flagged. Projects never emit any `inherited*` field.

## Conventions

- **Project-based.** Unlike other suites, this one creates tasks under real projects (not inbox). Uses the shared **Project Discovery** procedure (SKILL.md).
- **1-item limit.** `edit_tasks` currently accepts exactly 1 item per call.
- **Read-back required.** Every test uses `get_task` (or `get_project`/`list_projects` for project-side checks) to verify inherited fields — inheritance is only observable through reads.
- **Stripping contract.** `false`, `null`, `[]`, `""`, and `"none"` are stripped from responses. So "no self-echo" (walk yields None/False because no ancestor contributed) is asserted as "`inheritedX` absent from response," not "`inheritedX: null`."

## Tests

### 1. Direct Inheritance

#### Test 1: Direct inheritance (L1)
1. `get_task` on T1-InheritDirect
2. PASS if ALL of:
   - `inheritedDueDate` matches dated-project's dueDate
   - `inheritedDeferDate` matches dated-project's deferDate
   - `inheritedPlannedDate` matches dated-project's plannedDate
   - `inheritedFlagged` = true
   - Task's own `dueDate`, `deferDate`, `plannedDate` are absent from response (never set → stripped)
   - Task's own `flagged` is absent (false → stripped)

### 2. Chain Inheritance

#### Test 2: Inheritance through task chain (L2)
1. `get_task` on T2a-ChainChild
2. PASS if ALL of:
   - `inheritedDueDate` matches dated-project's dueDate
   - `inheritedDeferDate` matches dated-project's deferDate
   - `inheritedPlannedDate` matches dated-project's plannedDate
   - `inheritedFlagged` = true
   - Task's own `flagged` is absent (false → stripped)

### 3. Deep Nesting

#### Test 3: Deep nesting (L3)
1. `get_task` on T3b-L3
2. PASS if ALL of:
   - `inheritedDueDate` matches dated-project's dueDate
   - `inheritedDeferDate` matches dated-project's deferDate
   - `inheritedPlannedDate` matches dated-project's plannedDate
   - `inheritedFlagged` = true
   - Task's own `dueDate`, `deferDate`, `plannedDate`, `flagged` all absent (never set → stripped)

### 4. Move Away — Clear Inheritance

#### Test 4: Clearing after move to undated project
1. `get_task` T4-MoveAway — sanity check: confirm `inheritedDueDate` matches dated-project's dueDate
2. `edit_tasks` on T4: `actions: { move: { "ending": "<undated-project-id>" } }`
3. `get_task` T4-MoveAway
4. PASS if ALL of:
   - `inheritedDueDate` absent (undated-project has no dueDate → nothing to inherit → stripped)
   - `inheritedDeferDate` absent
   - `inheritedPlannedDate` absent
   - `inheritedFlagged` absent (undated-project not flagged → false → stripped)

### 5. Move In — Acquire Inheritance

#### Test 5: Move INTO dated project acquires inheritance
1. `get_task` T5-MoveIn — sanity check: confirm `inheritedDueDate` absent (task is in inbox, no ancestor)
2. `edit_tasks` on T5: `actions: { move: { "ending": "<dated-project-id>" } }`
3. `get_task` T5-MoveIn
4. PASS if ALL of:
   - `inheritedDueDate` matches dated-project's dueDate
   - `inheritedDeferDate` matches dated-project's deferDate
   - `inheritedPlannedDate` matches dated-project's plannedDate
   - `inheritedFlagged` = true

### 6. Own + Inherited Semantics

Own and inherited values coexist independently. `inheritedX` is emitted whenever an ancestor sets X — regardless of whether the task itself sets its own X. The agent sees both ("you set X, your ancestor set Y") distinctly. `inheritedX` is absent ONLY when no ancestor contributed (the walk yields None/False → stripped). Setting own X does NOT hide `inheritedX`; the two are orthogonal.

#### Test 6a: Own dueDate + ancestor dueDate coexist
1. `edit_tasks` on T6-OwnOverride: `dueDate: "2026-06-15T12:00:00+01:00"` (deliberately different from dated-project's dueDate)
2. `get_task` T6-OwnOverride
3. PASS if ALL of:
   - `dueDate` = "2026-06-15T12:00:00+01:00" (own value present)
   - `inheritedDueDate` present AND matches dated-project's dueDate (ancestor still visible — own does NOT hide inherited)
   - `inheritedDeferDate` still matches dated-project's deferDate (unchanged — deferDate wasn't touched)
   - `inheritedFlagged` = true (still inherited — flagged wasn't touched)

#### Test 6b: Own flagged + ancestor flagged coexist
1. `edit_tasks` on T6-OwnOverride: `flagged: true`
2. `get_task` T6-OwnOverride
3. PASS if ALL of:
   - `flagged` = true (own value present)
   - `inheritedFlagged` = true (ancestor still visible — dated-project is flagged, so inherited is emitted regardless of own value)
4. Clean up: `flagged: false` on T6 (own reverts to implicit false → stripped; `inheritedFlagged: true` still emitted from project)

#### Test 6c: Clear own dueDate — only inheritedDueDate remains
1. Confirm T6 still has own `dueDate` from Test 6a (if not, re-run 6a first)
2. `edit_tasks` on T6: `dueDate: null`
3. `get_task` T6-OwnOverride
4. PASS if ALL of:
   - `dueDate` absent (own value cleared → null → stripped)
   - `inheritedDueDate` present and matches dated-project's dueDate (ancestor-contributed value was there all along; now it's the only one left)

#### Test 6d: No-self-echo regression guard
Pre-Phase-53.1, a task with no ancestor would have had `inheritedFlagged: false` echoed back. After 53.1, the walk yields False (no ancestor flags) → stripped. Same for dates: walk yields None → stripped. This is the true meaning of "self-echo stripping."
1. `get_task` T11-NoAncestor (inbox, never given own flagged/dueDate/etc.)
2. PASS if ALL of:
   - Task's own `flagged` is absent (false → stripped)
   - `inheritedFlagged` is absent (walk has no ancestor → yields False → stripped — no self-echo)
   - Task's own `dueDate` / `deferDate` / `plannedDate` all absent (never set → stripped)
   - `inheritedDueDate` / `inheritedDeferDate` / `inheritedPlannedDate` all absent (walk has no ancestor → yields None → stripped)

### 7. Per-Field Aggregation

When multiple ancestors set the same field, per-field aggregation rules apply:
min for due, max for defer, first-found (nearest ancestor) for planned/drop/completion, any-True (OR) for flagged.

T8-AggParent has own dueDate=2020-01-01 (earlier than project), deferDate=2040-01-01 (later than project),
plannedDate=2030-06-15 (different from project). T8a-AggChild has no own dates and inherits from both T8 and dated-project.

#### Test 7a: inheritedDueDate = min across ancestors
1. `get_task` T8a-AggChild
2. PASS if:
   - `inheritedDueDate` = "2020-01-01T00:00:00Z" (T8's own dueDate — earlier than dated-project's dueDate → min wins)
   - T8a has no own `dueDate` (absent from response)

#### Test 7b: inheritedDeferDate = max across ancestors
1. `get_task` T8a-AggChild
2. PASS if:
   - `inheritedDeferDate` = "2040-01-01T00:00:00Z" (T8's own deferDate — later than dated-project's deferDate → max wins)
   - T8a has no own `deferDate` (absent from response)

#### Test 7c: inheritedPlannedDate = first-found (nearest ancestor)
1. `get_task` T8a-AggChild
2. PASS if:
   - `inheritedPlannedDate` = "2030-06-15T00:00:00Z" (T8's plannedDate — nearest ancestor with the field set; dated-project's plannedDate ignored)
   - T8a has no own `plannedDate` (absent from response)

### 8. Inherited Lifecycle Dates (new pairs)

These pairs exist after Phase 53.1. A task inherits its nearest completed/dropped ancestor's completion/drop date whenever the task does not have its OWN `completionDate` / `dropDate`. OmniFocus will typically cascade-complete or cascade-drop the child (so `availability` becomes completed/dropped), but the cascade does NOT give the child its own `completionDate` / `dropDate` — the date is inherited from the parent. That's exactly the state these tests verify.

#### Test 8a: inheritedCompletionDate from completed parent task
Pre-requisite: Setup has completed T9-CompletionParent.
1. `get_task` T9-CompletionParent — note its `completionDate` value
2. `get_task` T9a-CompletionChild
3. PASS if:
   - T9a has no own `completionDate` in response (regardless of T9a's `availability` — cascade affects availability but not own completionDate)
   - `inheritedCompletionDate` on T9a matches T9's `completionDate`

#### Test 8b: inheritedDropDate from dropped parent task
Pre-requisite: Setup has dropped T10-DropParent.
1. `get_task` T10-DropParent — note its `dropDate` value
2. `get_task` T10a-DropChild
3. PASS if:
   - T10a has no own `dropDate` in response (regardless of T10a's `availability` — cascade affects availability but not own dropDate)
   - `inheritedDropDate` on T10a matches T10's `dropDate`

### 9. Projects Emit Zero inherited* Fields

Phase 53.1 Part B moved all inherited fields from `ActionableEntity` to `Task`. Projects — despite having dates/flags — never emit `inherited*` fields, under any `include` group.

#### Test 9: list_projects + include=["*"] returns no inherited* on any project
1. `list_projects` with `include: ["*"], limit: 10`
2. Inspect every project in `items`
3. PASS if: NO project item contains any key starting with `inherited` (e.g., no `inheritedDueDate`, `inheritedDeferDate`, `inheritedPlannedDate`, `inheritedFlagged`, `inheritedCompletionDate`, `inheritedDropDate`). Same guarantee applies to single-project reads via `get_project` — spot-check by calling `get_project` on dated-project with `include: ["*"]` and confirming zero `inherited*` keys.

### 10. Chain Move — Children Inherit

#### Test 10: Move parent+child out of dated project; child's inherited fields clear
1. `get_task` T7a-ChainMoveChild — sanity check: confirm `inheritedDueDate` matches dated-project's dueDate
2. `edit_tasks` on T7-ChainMoveParent: `actions: { move: { "ending": "<undated-project-id>" } }`
3. `get_task` T7a-ChainMoveChild
4. PASS if ALL of:
   - `inheritedDueDate` absent
   - `inheritedDeferDate` absent
   - `inheritedPlannedDate` absent
   - `inheritedFlagged` absent

## Report Table Rows

| # | Test | Description | Result |
|---|------|-------------|--------|
| 1 | Direct inheritance (L1) | Task under dated project inherits all 4 inherited fields; no own dates/flag set | |
| 2 | Chain inheritance (L2) | Grandchild inherits through parent task within dated project | |
| 3 | Deep nesting (L3) | 3 levels deep; all 4 inherited fields inherited; no own values | |
| 4 | Move away: clear | Move from dated→undated project; all inherited fields absent (stripped) | |
| 5 | Move in: acquire | Move from inbox→dated project; all inherited fields appear | |
| 6a | Own + ancestor dueDate coexist | Own dueDate set AND ancestor dueDate → BOTH `dueDate` and `inheritedDueDate` in response | |
| 6b | Own + ancestor flagged coexist | Own flagged=true AND ancestor flagged → BOTH `flagged` and `inheritedFlagged: true` in response | |
| 6c | Clear own dueDate — inherited remains | Clearing own dueDate → own `dueDate` absent, `inheritedDueDate` still present | |
| 6d | No-self-echo regression guard | Inbox task with no ancestor → neither `flagged` nor `inheritedFlagged` echoed (true 53.1 stripping) | |
| 7a | Aggregation: due=min | Multiple ancestors with dueDate → inheritedDueDate = earliest | |
| 7b | Aggregation: defer=max | Multiple ancestors with deferDate → inheritedDeferDate = latest | |
| 7c | Aggregation: planned=first-found | Multiple ancestors with plannedDate → nearest ancestor's value wins | |
| 8a | inheritedCompletionDate | Completed parent → child's inheritedCompletionDate matches parent's completionDate | |
| 8b | inheritedDropDate | Dropped parent → child's inheritedDropDate matches parent's dropDate | |
| 9 | Projects emit zero inherited* | list_projects + include=["*"] → no project contains any inherited* key | |
| 10 | Chain move: children | Move parent to undated project; child's inherited fields clear | |
