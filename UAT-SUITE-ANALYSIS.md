# UAT Suite Analysis — v1.4 "Response Shaping & Batch Processing" + v1.4.1 (Phases 56 + 57)

## How to Use This File

This file is the output of a research session that analyzed what v1.4 + v1.4.1 (Phases 56 & 57) changed vs what existing UAT suites cover. It contains everything a fresh agent needs to update the suites without re-doing the research.

**Workflow:** Run `/uat-suite-updater` in a new session. The skill auto-detects this file and enters Worker mode — it will find the next unchecked chunk, do targeted research, execute the changes, and mark the chunk done.

**Scope lock:**
- v1.4 Phases: 53 (Response Shaping), 53.1 (True Inherited Fields), 54 (Batch Processing), 55 (Notes Graduation) — all shipped, archived in `.planning/milestones/v1.4-phases/`
- v1.4.1 Phase 56 (Task Property Surface) — shipped (9/9 plans complete, verification on file), artifacts in `.planning/phases/56-task-property-surface/`
- v1.4.1 Phase 57 (Parent Filter & Filter Unification) — verified passed 2026-04-20 (5/5 success criteria, 20/20 requirements), validation audit 2026-04-21 (0 gaps). STATE.md is stale on this. Artifacts in `.planning/phases/57-parent-filter-filter-unification/`. All 5 warnings exist in code with verbatim-locked text (including FILTERED_SUBTREE_WARNING with U+2014 em-dash).

**Important:** The agent still needs to do its own targeted research for the specific suites it's updating — the gap tables below are a starting point, not exhaustive. Source-of-truth is always the planning doc, never the source code.

**Cross-cutting ambiguity resolution (applies to all chunks):**

1. **Warning text is always a behavioral assertion, never verbatim.** Even for warnings whose text is locked verbatim in specs (INCLUDE_ONLY_CONFLICT per Phase 53 D-06, FILTERED_SUBTREE_WARNING per Phase 57 with em-dash U+2014). Flo wants freedom to reword warnings over time without breaking UAT. The assertion pattern is: warning is **present**, **fluent from an agent's perspective**, **no internals leak** (no `type=`, `pydantic`, `input_value`, `_Unset`). Tests should NOT assert exact strings — if the worker feels the text is awkward, the *suite* is the wrong place to complain; file a todo separately.

2. **Preference-dependent tests follow the existing date-filtering "SOON_DUE" pattern.** See `tests/date-filtering.md` — `SOON_DUE` is discovered during Setup (block asks the user: "OmniFocus due-soon threshold? (Preferences > Dates & Times > ...)"), used as a placeholder throughout, and PASS criteria are marked "threshold-dependent" when applicable. Chunk 5's create-default tests follow the same pattern: ask the tester to check their `OFMCompleteWhenLastItemComplete` / `OFMTaskDefaultSequential` values in Setup, reference them as placeholders, mark assertions "preference-dependent."

3. **Opportunistic cleanup during chunk work is welcome.** If a worker spots clearly redundant or awkwardly structured tests in a suite they're already modifying, tidying is in-scope. Do NOT make cleanup a separate chunk — fold it opportunistically into the chunk that's already touching the suite. Flag structural tweaks to Flo in the chunk summary.

4. **Ambiguity to resolve live — `isSequential` on projects in default response.** Phase 56 CONTEXT §3 and MILESTONE-v1.4.1.md line 70 both say `isSequential` is **tasks-only** in default response (projects use the full `type` enum via `hierarchy` include group). However, Flo's intent is that `isSequential` should behave **identically on tasks AND projects** in default response. This is a spec-vs-intent gap. Resolution strategy: Chunk 3 includes P-IsSequential (projects) AND the tasks-side test. Worker self-verification in Chunk 3 should confirm live behavior and surface the result. If live says tasks-only, keep the P-IsSequential test but mark it as "expected failure — spec drift, file todo." If live says both, the spec gets updated in a follow-up and the test passes. Either way, the test captures the intended contract.

---

## Progress

- [x] Chunk 1 — Inherited field rename + true-inheritance semantics (6 suites touched)
- [ ] Chunk 2 — NEW `response-shaping.md` suite + SKILL.md + reads-combined registration
- [ ] Chunk 3 — Presence flags + hierarchy include group (read-side, 3 suites)
- [ ] Chunk 4 — Notes graduation: top-level-note removal + new note action coverage
- [ ] Chunk 5 — Writable `type` + `completesWithChildren` + create-defaults + derived-field rejection
- [ ] Chunk 6 — Batch processing: per-item result envelope + fail-modes
- [ ] Chunk 7 — Phase 57: `parent` filter + filter unification + 5 new warnings
- [ ] **Delete this file** (all chunks done, everything merged)

---

## Chunks — Task List

### Chunk completion protocol

After finishing the suite edits for a chunk, the agent does NOT commit. Instead:

1. **Present assumptions** — list any assumptions about live behavior that the suite relies on (warning fluency, filter results, edge cases)
2. **Offer self-verification** — "Want me to run these checks myself against your live OmniFocus?" If approved, the agent creates minimal test tasks via MCP, runs the checks, reports results, and cleans up (see Worker Mode Step 4 in the skill for the full protocol). If a discrepancy is found, the agent updates the suite before proceeding.
3. **Summarize changes** — list every file modified, tests added, assertions fixed, and verification results if applicable
4. **Wait for sign-off** — user reviews the changes
5. **On approval**: commit the suite changes, then update the Progress checklist above (check the box)

---

### Chunk 1: Inherited field rename + true-inheritance semantics

**Suites:** `inheritance.md` (primary), `edit-operations.md`, `date-filtering.md`, `list-tasks.md`, `list-projects.md`, `repetition-rules.md`

**Context:** Phase 53 renamed all 4 `effective*` pairs to `inherited*` and added 2 new pairs. Phase 53.1 changed the semantics so `inherited*` is only emitted when truly inherited (no self-echoes). Also: projects no longer emit `inherited*` fields at all.

**What to do:**

- **inheritance.md (8 tests, 32 `effective*` refs):**
  - Global rename: `effectiveDueDate` → `inheritedDueDate`, `effectiveDeferDate` → `inheritedDeferDate`, `effectivePlannedDate` → `inheritedPlannedDate`, `effectiveFlagged` → `inheritedFlagged`
  - Add self-shadowing coverage: one test per direct-set field showing that when the task sets its own value, `inherited*` is absent/stripped (task has direct due → no `inheritedDueDate`)
  - Add per-field aggregation rule tests: `inheritedDueDate` = min across ancestors; `inheritedDeferDate` = max; `inheritedPlannedDate` = first-found; `inheritedFlagged` = any-True (OR)
  - Add new pairs — `inheritedCompletionDate` and `inheritedDropDate` (one test each): set a parent task's completion/drop state, verify child inherits via these fields
  - Add a project-side test: assert that `get_project` and `list_projects` responses **never** emit any `inherited*` field on projects (even with `include: ["*"]`)

- **Cross-suite assertion fixes (update `effective*` → `inherited*` in assertion text):**
  - `edit-operations.md:64` — "effectiveFlagged: false matches flagged: false" → "inheritedFlagged absent since task sets flagged directly" (adjust to match new semantics: direct-set ≠ echoed into `inherited*`)
  - `date-filtering.md` — 6 references to `effective*` in date-filter tests, likely around inherited-date filtering semantics; rename each to `inherited*` and verify assertion still reflects intent
  - `list-tasks.md`, `list-projects.md`, `repetition-rules.md` — 1 reference each, simple rename

**Est. scope:** ~10 assertion fixes across 5 suites + ~6 new tests in inheritance.md.

**Self-verification candidates:**
- Assumption: task with own due date + parent with due date emits only `dueDate`, no `inheritedDueDate`
- Assumption: aggregation (min for due, max for defer) matches what the server emits in a 3-deep chain
- Assumption: `list_projects` response contains zero `inherited*` fields under any include mode

---

### Chunk 2: NEW `response-shaping.md` suite + SKILL.md + reads-combined registration

**Suites:** **NEW FILE** `response-shaping.md`, `.claude/skills/uat-regression/SKILL.md` (table row), `reads-combined.md` (composite registration)

**Context:** Phase 53 introduced three cross-cutting concerns that don't fit any existing suite:
1. Universal stripping of null/`[]`/`""`/`false`/`"none"` from responses (except `availability`, always present)
2. Field selection: `include` (semantic groups) and `only` (individual fields) on `list_tasks` and `list_projects`
3. `limit: 0` count-only mode

These touch every tool but are best tested in one dedicated suite with representative tool coverage.

**What to do (new suite, ~14 tests):**

- Test 1 family — Universal stripping (4 tests):
  - 1a: `list_tasks` response strips null/empty-array/false fields on task items (create a minimal task, verify no `tags: []`, no `flagged: false`, no `dueDate: null`)
  - 1b: `list_projects` response strips similarly on project items
  - 1c: `get_task` response strips on single-entity form
  - 1d: **`availability` always present** — task with every other field stripped still shows `availability: "available"`; `availability` never suppressed
- Test 2 family — `include` parameter (3 tests):
  - 2a: `include: ["notes"]` on `list_tasks` adds note-related fields not in default response
  - 2b: `include: ["*"]` returns the full field set for the tool
  - 2c: `include: ["invalid_group"]` → error (behavioral assertion: error present, fluent from agent perspective, contains the invalid name, no pydantic internals leak — see cross-cutting ambiguity 1)
- Test 3 family — `only` parameter (3 tests):
  - 3a: `only: ["id", "dueDate"]` returns only those fields (plus `id` which is always included)
  - 3b: `only: ["invalid_field"]` succeeds but emits a warning (behavioral assertion: warning present, fluent, names the invalid field)
  - 3c: `only` doesn't prevent stripping — `only: ["dueDate"]` on a task with `dueDate: null` still omits `dueDate` (stripping applies before projection)
- Test 4 — `include` + `only` conflict (1 test): both specified → warning present, `only` applied. **Behavioral assertion only** — the spec locks a verbatim string (Phase 53 D-06) but per cross-cutting ambiguity 1, we intentionally do NOT assert exact text. Assert: warning is present, the `only` selection won, the warning text names both parameters and explains the precedence fluently.
- Test 5 — `limit: 0` count-only mode (2 tests):
  - 5a: `list_tasks({limit: 0, ...})` returns `{items: [], total: N, hasMore: ...}` with no data rows
  - 5b: envelope fields (`total`, `hasMore`) always present even when items array is empty
- Test 6 — Batch response stripping (1 test): `add_tasks` with a batch where one item errors — response items strip `null` `id`/`name`/`error`/`warnings` fields consistently (absence vs `null` distinction)

**Registration work (MANDATORY — cannot defer):**
1. **SKILL.md table row**: add entry for `response-shaping.md` with: file path `tests/response-shaping.md`, test count (whatever final number is), coverage description ("Response stripping, `include`/`only` field selection, `limit: 0` count-only mode, batch result shape")
2. **reads-combined.md composite**: add the new suite to the aggregated read-side suite. It fits logically between date-filtering and list-projects (cross-cutting response shaping → individual tool coverage). Update the test-count in the file header and in SKILL.md's reads-combined row.
3. **Audit SKILL.md table counts while you're there**: Agent C noted reads-combined claims 169 but components sum to 172, and task-creation/edit-operations table counts are stale. Spot-fix those rows too if trivially verifiable from the actual suite files — but don't make this chunk about the audit; the main work is the new suite.

**Est. scope:** ~14 new tests + ~3 table/registration updates.

**Self-verification candidates:**
- Assumption: stripping applies consistently across `list_tasks`, `list_projects`, `get_task`
- Assumption: invalid group name in `include` produces an **error** (not a warning), while invalid field name in `only` produces a **warning** (not an error)
- Assumption: `availability` always present (never stripped from any tool response)

---

### Chunk 3: Presence flags + hierarchy include group (read-side)

**Suites:** `list-tasks.md` (primary), `list-projects.md`, `read-lookups.md`

**Context:** Phase 56 added derived read-only flags to the default response and expanded the `hierarchy` include group. The design intent is that agents see the right signal at the right cost — common flags in default, structural detail on demand via `hierarchy`.

**What to do:**

- **list-tasks.md — add tests for default-response flags (5 tests):**
  - T-HasNote: task with non-empty note emits `hasNote: true`; task with empty/absent note omits the field
  - T-HasRepetition: task with a repetition rule emits `hasRepetition: true`; task without omits
  - T-HasAttachments: task with attachments (user-added manually) emits `hasAttachments: true`; task without omits (cache-backed; see attachment manual action)
  - T-IsSequential: task with `type: "sequential"` emits `isSequential: true`; parallel task omits
  - T-DependsOnChildren: task with children AND `completesWithChildren: false` emits `dependsOnChildren: true`; container task (completesWithChildren: true) omits; leaf task (no children) omits

- **list-tasks.md + read-lookups.md — hierarchy include group (3 tests):**
  - T-HierarchyTask: `include: ["hierarchy"]` on a task adds `hasChildren`, `type` (full enum: `"parallel"` or `"sequential"`), `completesWithChildren` (always present, including `false`)
  - T-NoSuppressionInvariant: request default + `include: ["hierarchy"]` on a task where `type: "sequential"` AND `dependsOnChildren: true` — assert default flags (`isSequential: true`, `dependsOnChildren: true`) appear AND hierarchy fields (`type: "sequential"`, `hasChildren: true`, `completesWithChildren: false`) also appear. Redundancy is the contract; suppression would be a regression.
  - T-CompletesWithChildrenInNeverStrip: hierarchy group on a task with `completesWithChildren: false` — field survives stripping (`false` emitted, not omitted)

- **list-projects.md — project default flags + hierarchy (4 tests):**
  - P-HasNote/HasRepetition/HasAttachments: one test each, same pattern as task side (projects DEFINITELY emit these 3 in default response)
  - **P-IsSequential (AMBIGUOUS — see cross-cutting ambiguity 4):** project with `type: "sequential"` emits `isSequential: true` in default response. **Per spec this should NOT appear on projects (tasks-only per FLAG-04)**, but per Flo's intent, project and task behavior should be identical. **Worker action**: write the test assuming identical behavior (project-side emission), run self-verification against live OmniFocus during Chunk 3, and report the outcome. If live matches spec (projects omit `isSequential`), mark this test as "expected failure" with note "resolve spec drift in follow-up — todo required". If live matches Flo's intent (projects emit), the test passes and we file a follow-up todo to update the spec docs. Either way, the test captures the intended contract.
  - P-HierarchyProject: `include: ["hierarchy"]` on a project adds `hasChildren`, `type` (full enum: `"parallel"` | `"sequential"` | `"singleActions"`), `completesWithChildren`
  - P-ProjectTypeEnum: project with Single Actions flag set shows `type: "singleActions"` (precedence rule: `singleActions` beats `sequential` beats `parallel` per HIER-05)

- **read-lookups.md — spot-check parity (1 test):**
  - L-GetTaskNewFlags: `get_task` returns the same presence flags and hierarchy fields as `list_tasks` for the same task (one round-trip test proving both surfaces agree)

**Est. scope:** ~13 new tests across 3 suites. Shared setup helps: create one task hierarchy with enough diversity to cover most flag states, reuse across tests.

**Key design assertion to protect (no-suppression invariant):**
> When `hierarchy` is requested on a task that triggers `dependsOnChildren` or `isSequential`, the agent sees BOTH the derived default flag AND the fuller hierarchy fields. Redundancy is intentional — do NOT de-duplicate. (Phase 56 SC-4)

**Self-verification candidates (MUST run for this chunk — the ambiguity is live-or-die):**
- **Assumption (ambiguity resolution)**: `isSequential` on projects in default response — run live against a sequential project and report whether the flag appears. This resolves cross-cutting ambiguity 4.
- Assumption: `hasAttachments` reflects current bridge state and is cache-backed (one refresh may lag deletions)
- Assumption: project with singleActions flag returns `type: "singleActions"`, not `"parallel"` (precedence rule)
- Assumption: `completesWithChildren: false` actually survives stripping (it's in `NEVER_STRIP` per SC-3)

---

### Chunk 4: Notes graduation — top-level-note removal + new note action coverage

**Suites:** `edit-operations.md` (primary), `integration-flows.md`, `validation-errors.md`

**Context:** Phase 55 removed top-level `note` from `edit_tasks` input. It now lives in `actions.note.append` and `actions.note.replace`. `add_tasks` retains top-level `note` (initial-content-setter, no change). This breaks ~8 existing edit tests that use `note:` at top level, and creates new surface for append/replace semantics.

**What to do:**

- **edit-operations.md — assertion fixes (~8 places) + new tests:**
  - Rewrite test 1a (line 48–51): `note: "hello"` top-level → `actions: {note: {replace: "hello"}}`; `note: null` → `actions: {note: {replace: null}}`. Test name stays "clears the note via replace: null".
  - Rewrite test 1b (line 53–56): same pattern, using `replace: ""`.
  - Rewrite test 2a (line 62): multi-field edit — move `note: "test note"` into an `actions.note.replace` block alongside the top-level name/flagged/estimatedMinutes fields
  - Rewrite test 5a (line 85): same pattern — `note: "multi"` in combined field edit
  - Rewrite test 6a (line 141), 6b (line 142): similar
  - Rewrite test 7a (line 171), 7b (line 172): note + flagged combos
  - Add new tests for append semantics:
    - N-AppendNewline: append to existing note → single `\n` separator (e.g., `"existing"` + `append: "new"` → `"existing\nnew"`, NOT `"existing\n\nnew"`)
    - N-AppendEmptyNote: append to empty note → content set directly (no leading separator): `""` + `append: "foo"` → `"foo"`
    - N-AppendWhitespaceOnly: note `"   "` + `append: "x"` → `"x"` (whitespace-only treated as empty for purposes of leading-separator suppression)
  - Add tests for warnings (all behavioral assertions per cross-cutting ambiguity 1):
    - N-AppendEmptyString: `append: ""` → no-op with warning (NOTE_APPEND_EMPTY)
    - N-AppendWhitespaceArg: `append: "   "` → no-op with warning
    - N-ReplaceIdentical: note already `"hello"`, replace with `"hello"` → no-op with warning (NOTE_REPLACE_ALREADY_CONTENT)
    - N-ReplaceAlreadyEmpty: note already empty, replace with `null` or `""` → no-op with warning (NOTE_ALREADY_EMPTY)
  - Add test: N-NoteActionAlone — `actions: {note: {replace: "x"}}` with no other actions (tags, move, etc.) is valid and applies cleanly

- **integration-flows.md — assertion fix (1 place):**
  - line 51 — `note: null` in an edit_tasks call → `actions: {note: {replace: null}}`

- **validation-errors.md — new error tests (2 tests):**
  - VE-NoteAppendWithReplace: `actions.note.append: "x", actions.note.replace: "y"` in same action → error (behavioral assertion)
  - VE-NoteNoOperation: `actions.note: {}` (neither append nor replace set) → error (behavioral assertion)

**Est. scope:** ~8 assertion fixes + ~9 new tests in edit-operations + 1 fix in integration-flows + 2 tests in validation-errors. Total: ~9 fixes + ~11 new tests. This is the largest chunk — keep it one pass since all the work is in the note-semantics domain.

**Self-verification candidates:**
- Assumption: `\n` is the separator (single newline), not `\n\n`
- Assumption: whitespace-only notes treated as empty for separator-suppression logic
- Assumption: the four note-related warnings (NOTE_APPEND_EMPTY, NOTE_REPLACE_ALREADY_CONTENT, NOTE_ALREADY_EMPTY, NOTE_APPEND_WITH_REPLACE) are fluent and agent-friendly in their current live form

---

### Chunk 5: Writable `type` + `completesWithChildren` + create-defaults + derived-field rejection

**Suites:** `task-creation.md` (primary), `edit-operations.md`, `validation-errors.md`

**Context:** Phase 56 write-side adds two new writable fields to tasks: `completesWithChildren` (`Patch[bool]`) and `type` (`Patch[TaskType]` where `TaskType = "parallel" | "sequential"`). Six derived read-only fields are rejected via `extra="forbid"`. Create-defaults read from user's OmniFocus preferences.

**What to do:**

- **task-creation.md — new `add_tasks` coverage (5 tests):**
  - T-AddCompletesWithChildren: `add_tasks([{name: "X", completesWithChildren: true}])` succeeds, round-trip via `get_task` shows `completesWithChildren: true` in hierarchy include
  - T-AddType: `add_tasks([{name: "X", type: "sequential"}])` succeeds, round-trip shows `type: "sequential"`; separate test for `type: "parallel"` create-default behavior
  - T-AddTypeSingleActionsRejected: `add_tasks([{name: "X", type: "singleActions"}])` → Pydantic enum error (no custom message expected — spec says generic schema error is correct per FLAG-08/PROP-04)
  - **T-CreateDefaultCompletesWithChildren (preference-dependent)**: follow the `SOON_DUE` pattern in `date-filtering.md`. During Setup, ask the tester: "Check OmniFocus Preferences → Organization → 'Complete projects and groups when their last action is completed' — is it ON?" Store as placeholder `CWC_DEFAULT`. Test: `add_tasks([{name: "X"}])` (field omitted) → response shows `completesWithChildren` resolved to `CWC_DEFAULT`. Mark PASS criterion as "preference-dependent."
  - **T-CreateDefaultType (preference-dependent)**: same pattern. Setup asks: "OmniFocus Preferences → Organization → 'Default action group type' — parallel or sequential?" Store as `TYPE_DEFAULT`. Test: `add_tasks([{name: "X"}])` → response shows `type` = `TYPE_DEFAULT`. Mark "preference-dependent."

- **edit-operations.md — new `edit_tasks` coverage (4 tests):**
  - E-EditCompletesWithChildren: toggle the field on an existing task, round-trip verify
  - E-EditType: flip `type: "parallel"` ↔ `"sequential"` on an existing task, round-trip verify
  - E-EditNullRejected: `completesWithChildren: null` rejected (Patch[bool] — no cleared state for booleans); `type: null` rejected
  - E-EditSingleActionsRejected: `type: "singleActions"` on edit → same enum error as on create

- **validation-errors.md — new cross-tool validation (4 tests — derived-field rejection, one per action):**
  - VE-RejectHasNote: `add_tasks([{name: "X", hasNote: true}])` → Pydantic schema error (`extra="forbid"`) — generic, no custom message
  - VE-RejectIsSequential: same pattern with `isSequential: true`
  - VE-RejectDependsOnChildren: same pattern
  - VE-RejectDerivedOnEdit: `edit_tasks([{id: "...", hasChildren: true}])` → same error (one representative for edit-side)
  - Alternative: collapse into one parametric test if the suite style allows it — but current suite convention seems to be one test per error, so stay consistent.

**Additional — test PROP-07 structural guarantee (no project-write tools):**
- Decide whether this goes in `validation-errors.md` or is skipped. The feature is "structural absence" — there's no `add_projects` or `edit_projects` tool to call. A UAT test would be trying to call a non-existent tool, which isn't testable via the MCP client in the same way. **Recommendation**: skip — this is a schema/tool-registration guarantee, better tested at the contract/registration level (which the Phase 56 internal tests already cover). UAT can't observe tool-absence cleanly.

**Est. scope:** ~5 new tests in task-creation + ~4 in edit-operations + ~4 in validation-errors = ~13 new tests.

**Self-verification candidates:**
- Assumption: create-defaults actually writes the resolved preference value explicitly (not OmniFocus's silent default) — verify by inspecting response fields match the user's current preferences
- Assumption: `"singleActions"` on task produces a generic Pydantic enum error (no custom message)
- Assumption: derived-field rejection error is generic (no custom educational message per FLAG-08)
- **Setup requirement**: before running T-CreateDefault* tests, verify the tester has captured `CWC_DEFAULT` and `TYPE_DEFAULT` from their OmniFocus preferences. Same pattern as `SOON_DUE` in date-filtering.

---

### Chunk 6: Batch processing — per-item result envelope + fail-modes

**Suites:** `batch-processing.md` (primary), `validation-errors.md` (batch limit error)

**Context:** Phase 54 lifted the 1-item constraint on `add_tasks` and `edit_tasks`, with different failure semantics per tool: `add_tasks` is best-effort (all items processed), `edit_tasks` is fail-fast (stop at first error, skip the rest). Per-item result shape has distinct field-presence rules by status.

Existing batch-processing.md has 2 tests (the 50-item mega-batch). This chunk adds per-item semantics coverage without duplicating the mega-batch.

**What to do:**

- **batch-processing.md — new tests (~10 tests):**
  - B-AddBestEffort: 3-item `add_tasks` where item 2 fails (e.g., invalid tag) — items 1 and 3 succeed with `status: "success"`, item 2 returns `status: "error"`. Assert `name` present on success, absent on error (no null field leaking).
  - B-AddItemIdAbsence: failed `add_tasks` item returns `status: "error"` with NO `id` field (task never got created — no OF ID exists). Assert the field is absent, not null.
  - B-EditFailFast: 3-item `edit_tasks` where item 2 fails — items 3+ return `status: "skipped"` with warning referencing the failing item (behavioral assertion: warning present, fluent, mentions item index). Earlier successful items (item 1) are committed.
  - B-EditSkippedHasId: `edit_tasks` skipped item retains its `id` in the response (since we know which task was skipped, unlike failed creates)
  - B-BatchResultStripping: per-item result envelopes strip null/empty `warnings` arrays consistently across all three statuses. Assert: successful item with no warnings shows no `warnings` key; error item with no extra warnings shows no `warnings` key.
  - B-SequentialCommitted: `edit_tasks([{id: X, name: "A"}, {id: X, name: "B"}])` (same task twice) — item 2 sees item 1's committed state. Final task name is "B", not "A". (Documents the sequential-order-matters contract.)
  - B-CrossItemRefNotSupported: `add_tasks([{name: "parent"}, {name: "child", parent: {task: {name: "parent"}}}])` — item 2 cannot reference item 1's just-created task (contract test). Expected: item 2 fails (parent not found) OR processes before commit — whichever the spec actually locks. Investigate Phase 54 spec for exact expectation. (May become a 1-test "documented limitation" if the behavior is "this just doesn't work as agents expect".)
  - B-ErrorPrefix: per-item error messages use "Task N:" prefix format (behavioral assertion: error text starts with "Task " and a 1-indexed number). Phase 54 D-03 locks this format in the middleware — verify in live run whether the prefix is present and fluent.

- **validation-errors.md — batch-limit error (2 tests):**
  - VE-AddBatchLimit: `add_tasks` with 51 items → schema validation error (generic Pydantic max_length message — no custom constant needed per Phase 54 VERIFICATION)
  - VE-EditBatchLimit: same for `edit_tasks` with 51 items

**Est. scope:** ~10 new tests in batch-processing + ~2 in validation-errors = ~12 new tests. Existing batch-processing.md has 2 mega-batch tests — those stay; new tests are additive.

**Self-verification candidates:**
- Assumption: "Task N:" prefix format present and fluent — live-verify the wording
- Assumption: skipped-item warning text references the failing item's index
- Assumption: `add_tasks` failed-item has NO `id` field in the response (not `id: null`)
- Assumption: `add_tasks` successful item has `id` present (OmniFocus returns one on creation)

---

### Chunk 7: Phase 57 — `parent` filter + filter unification + 5 new warnings

**Suites:** `list-tasks.md` (primary), `validation-errors.md`

**Context:** Phase 57 adds a `parent` filter to `list_tasks` and unifies the `project` and `parent` filter pipelines. One shared `expand_scope` helper, one unified `task_id_scope` repo primitive. Five new warnings guide correct usage. Phase is fully verified (5/5 SCs, 20/20 requirements) as of 2026-04-20.

**Key behavioral contracts:**
- Single-reference only (arrays rejected). Resolver: `$` prefix → exact ID → name substring (same three-step cascade as other filters).
- `parent` accepts tasks AND projects; `project` accepts projects only. Same entity → byte-identical results.
- Resolved task is included as anchor in result set. Resolved project has no anchor (projects aren't `list_tasks` rows).
- All descendants at any depth. AND-composes with every other filter. Preserves outline order, paginates via limit + cursor.
- `parent: "$inbox"` equivalent to `project: "$inbox"` with same contradiction rules.

**Five new warnings (all behavioral assertions per cross-cutting ambiguity 1):**
1. **FILTERED_SUBTREE_WARNING (WARN-01)** — fires when `project` OR `parent` is combined with any other dimensional filter (tags, dates, etc.). Spec has verbatim text locked with em-dash U+2014, but we assert behaviorally.
2. **PARENT_RESOLVES_TO_PROJECT_WARNING (WARN-02)** — fires when a `parent` substring resolves to projects only (no tasks matched). Soft "consider using `project`" hint.
3. **PARENT_PROJECT_COMBINED_WARNING (WARN-03)** — fires when both `parent` and `project` are specified. Soft hint, fires independent of scope intersection.
4. **Multi-match warning (WARN-04)** — reuses existing `FILTER_MULTI_MATCH` infrastructure for substring matches. Already fires for project; now also for parent.
5. **Inbox-name-substring warning (WARN-05)** — reuses existing `LIST_TASKS_INBOX_PROJECT_WARNING`. Parallel check added for parent when substring matches the inbox name.

**What to do:**

- **list-tasks.md — parent filter basic behavior (5 tests):**
  - P57-ParentByName: `parent: "SomeTaskName"` (substring) returns descendants; resolved task itself included as anchor
  - P57-ParentByID: `parent: "<taskId>"` returns descendants with task as anchor
  - P57-ParentInbox: `parent: "$inbox"` returns inbox tasks (equivalent to `project: "$inbox"`)
  - P57-ParentDeepDescendants: 3-level hierarchy — `parent: "<root>"` returns children AND grandchildren (any depth)
  - P57-ParentAndCompose: `parent: "X", tags: ["urgent"]` AND-composes strictly (only descendants matching both)

- **list-tasks.md — anchor semantics (2 tests):**
  - P57-TaskAnchorIncluded: resolved task IS in the result set (task-as-anchor)
  - P57-ProjectNoAnchor: `parent: "<projectName>"` — result set does NOT include the project as a row (projects aren't `list_tasks` rows); descendants still appear

- **list-tasks.md — cross-filter equivalence (1 test):**
  - P57-ParentProjectEquivalence: resolve the same project via `parent: "X"` and `project: "X"` — assert byte-identical result sets. Strong contract test for the unification.

- **list-tasks.md — 5 warnings (5 tests, all behavioral):**
  - P57-WarnFilteredSubtree: `parent: "X", tags: [...]` emits the filtered-subtree warning (present, fluent, mentions intermediates excluded)
  - P57-WarnFilteredSubtreeOnProject: `project: "X", tags: [...]` emits the SAME filtered-subtree warning (unification — both filters share the warning)
  - P57-WarnParentResolvesToProject: `parent: "<substring matching only projects>"` emits the pedagogical "consider `project`" hint
  - P57-WarnParentProjectCombined: specifying both `parent: "..."` and `project: "..."` emits the combined-filters soft warning
  - P57-WarnParentMultiMatch: `parent: "<substring matching multiple tasks>"` emits the multi-match warning (reused infrastructure — verify it still fires correctly for parent)
  - P57-WarnParentInbox: `parent: "<substring matching inbox name>"` emits the inbox-name-substring warning (reused infrastructure, parallel check)
  - Note: that's 6 warning tests total. If suite size is a concern, the parent-inbox case can fold into P57-ParentInbox. Worker's call during execution.

- **validation-errors.md — parent filter errors (2 tests):**
  - VE-ParentArrayRejected: `parent: ["X", "Y"]` → schema error (must be single reference, not a list)
  - VE-ParentInboxContradiction: `parent: "$inbox", inInbox: false` → contradiction error (same rule as `project: "$inbox"` + `inInbox: false`)

**Est. scope:** ~13 new tests in list-tasks + ~2 in validation-errors = ~15 new tests. Near the upper bound of the rule-of-thumb (~15 new tests per chunk). Keep it one chunk since all the work is Phase 57 domain.

**Self-verification candidates:**
- Assumption: `parent: "$inbox"` and `project: "$inbox"` produce identical results (unification contract)
- Assumption: filtered-subtree warning fires for BOTH `project + X` and `parent + X` (same constant, same firing rule)
- Assumption: parent-resolves-to-project warning only fires when ALL matches are projects (not when mixed with tasks — pedagogical tone, not punitive)
- Assumption: the 5 warnings are fluent from an agent's perspective
- Assumption: resolved task IS an anchor (included in result set), resolved project is NOT (no anchor row)

---

## Reference Material

Everything below is research output — the chunks above reference it.

---

## What v1.4 + v1.4.1 (Phases 56 + 57) Built

### Theme 1 — Response Shaping & Token Efficiency (Phase 53)
- Universal stripping of null/`[]`/`""`/`false`/`"none"` from all responses (except `availability`, always present)
- `include: ["notes" | "metadata" | "hierarchy" | "time" | "*"]` on list tools — semantic field groups
- `only: ["field1", "field2"]` on list tools — surgical field selection; `id` always included
- `limit: 0` → count-only mode (`{items: [], total, hasMore}`)
- `include` + `only` mutually exclusive at the response layer — warning, `only` wins
- Requirements: STRIP-01..04, COUNT-01, FSEL-01..12

### Theme 2 — True Inherited Fields (Phase 53 rename + Phase 53.1 semantics)
- `effective*` renamed to `inherited*` across 6 pairs (dueDate, deferDate, plannedDate, flagged, completionDate, dropDate) — two new pairs in 53.1
- True-inheritance semantics: `inherited*` only emitted when an ancestor sets the field. Self-echoes stripped.
- Projects never emit `inherited*` fields (model surgery — fields moved from `ActionableEntity` to `Task`)
- Per-field aggregation: due = min, defer = max, planned/completion/drop = first-found, flagged = any-True (OR)
- Requirements: RENAME-01, INHERIT-01..10

### Theme 3 — Batch Processing (Phase 54)
- `add_tasks` and `edit_tasks` now accept up to 50 items (pydantic-enforced max_length)
- `add_tasks` best-effort: all items processed, per-item `status: "success" | "error"`, `name` only on success, `id` on success only
- `edit_tasks` fail-fast: stop at first error, remaining items `status: "skipped"` with reference warning
- Serial execution in array order; same-task edits see prior items' committed state
- Per-item error format: "Task N: <message>" middleware-enforced prefix
- Cross-item references NOT supported (item 2 cannot depend on item 1's generated ID)
- Requirements: BATCH-01..10

### Theme 4 — Notes Graduation (Phase 55)
- `edit_tasks`: top-level `note` field REMOVED; moved to `actions.note.append` / `actions.note.replace`
- `add_tasks`: top-level `note` retained (initial-content-setter; no change)
- Append semantics: `\n` separator; whitespace-only input → no-op with warning; append to empty/whitespace-only note sets directly (no leading separator)
- Replace semantics: `null` or `""` clears; identical content → no-op with warning
- Note action alone is valid in `actions` block (no tags/move required)
- New errors: NOTE_APPEND_WITH_REPLACE (both set), NOTE_NO_OPERATION (neither set)
- New warnings: NOTE_APPEND_EMPTY, NOTE_REPLACE_ALREADY_CONTENT, NOTE_ALREADY_EMPTY
- Requirements: NOTE-01..05

### Theme 5 — Task Property Surface, Read-Side (Phase 56)
- Default response gains 5 derived flags on **tasks**: `hasNote`, `hasRepetition`, `hasAttachments`, `isSequential`, `dependsOnChildren` (all strip-when-false)
- Default response gains derived flags on **projects**: `hasNote`, `hasRepetition`, `hasAttachments`. **Spec says tasks-only for `isSequential` (FLAG-04), but Flo's intent is projects emit it too — this is the live-verification ambiguity resolved in Chunk 3. No `dependsOnChildren` on projects either way (projects have no parent-completion notion).**
- `hierarchy` include group adds: `hasChildren`, `type` (full enum; `"singleActions"` valid for projects only), `completesWithChildren` (always present, including `false` — in NEVER_STRIP)
- No-suppression invariant: default and hierarchy pipelines emit independently (contract test)
- `ProjectType` assembly precedence: `singleActions` > `sequential` > `parallel`
- Tool descriptions surface behavioral meaning for `isSequential` and `dependsOnChildren` (not UAT-testable — doc-regression domain)
- `availability` removed from NEVER_STRIP (cleanup; no observable contract change)
- `completesWithChildren: false` added to NEVER_STRIP (new observable contract)
- Requirements: PREFS-01..05, CACHE-01..04, FLAG-01..07, HIER-01..05, STRIP-11

### Theme 6 — Task Property Surface, Write-Side (Phase 56)
- Writable on tasks: `completesWithChildren: Patch[bool]`, `type: Patch[TaskType]` where `TaskType = "parallel" | "sequential"`
- `null` rejected on both (no cleared state for booleans/enums)
- `"singleActions"` on task rejected via Pydantic enum validation (generic error, no custom message)
- Create-defaults: omitted fields resolved from user's `OFMCompleteWhenLastItemComplete` / `OFMTaskDefaultSequential` preferences; written explicitly to task (not relying on OmniFocus implicit defaulting)
- Factory-default fallback: absent preference → `true` / `"parallel"`
- Derived read-only fields rejected via `extra="forbid"`: `hasNote`, `hasRepetition`, `hasAttachments`, `hasChildren`, `isSequential`, `dependsOnChildren` — generic schema error, no custom messaging (FLAG-08)
- Project writes rejected at tool surface (no `add_projects` / `edit_projects`) — deferred to v1.5/v1.7 per current roadmap
- Requirements: PROP-01..08, FLAG-08

### Theme 7 — Parent Filter & Filter Unification (Phase 57)
- New `parent: Patch[str]` field on `ListTasksQuery` — single reference (substring/ID/`$inbox`), arrays rejected
- Shared `expand_scope(ref_id, snapshot, accept_entity_types)` helper at `service/subtree.py` — one function, parameterized by accepted entity types
- Retired `project_ids` from `ListTasksRepoQuery`; unified to `task_id_scope: list[str] | None`
- Repo uses trivial set-membership filter: HybridRepository via `persistentIdentifier IN (?)`, BridgeOnly via `t.id in scope_set`
- `parent` accepts tasks AND projects; `project` accepts projects only. Same entity → byte-identical result sets.
- Conditional anchor injection inside `expand_scope`: task-ref adds `{ref_id}` to scope; project-ref returns only descendants (projects aren't `list_tasks` rows)
- Scope intersection when both `parent` and `project` set: `scope_from_project & scope_from_parent` at service layer, single AND clause at repo
- Five warnings — FILTERED_SUBTREE (verbatim-locked text with U+2014 em-dash), PARENT_RESOLVES_TO_PROJECT (soft hint), PARENT_PROJECT_COMBINED (soft hint), multi-match reuse, inbox-name-substring reuse
- Perf budget: Spike 2 benchmark locked p95 ≤ 1.30ms at 10K (77× under viable threshold — unification pays for itself)
- Requirements: PARENT-01..09, UNIFY-01..06, WARN-01..05

---

## Gap Analysis by Suite

### inheritance.md (8 tests) — NEEDS MAJOR UPDATES

**Assertion fixes needed:** 32 uses of `effective*` → `inherited*` throughout the suite.

**New scenarios needed:**

| Category | Test | Why |
|----------|------|-----|
| Self-shadowing | T-SelfShadowDue | When task has own `dueDate`, verify `inheritedDueDate` is absent (Phase 53.1: no self-echoes) |
| Self-shadowing | T-SelfShadowFlagged | Same pattern for `flagged` |
| New pairs | T-InheritedCompletion | `inheritedCompletionDate` didn't exist before — new field from 53.1 |
| New pairs | T-InheritedDrop | `inheritedDropDate` — same |
| Aggregation | T-AggregationDueMin | 2-parent chain, verify `inheritedDueDate` is min |
| Aggregation | T-AggregationDeferMax | Same chain, verify `inheritedDeferDate` is max |
| Projects | T-ProjectsNoInherited | `list_projects` / `get_project` never emit any `inherited*` field |

### edit-operations.md (24 tests) — NEEDS UPDATES

**Assertion fixes needed:**
- 1 use of `effectiveFlagged` → `inheritedFlagged` (line 64) — plus semantic rewrite since new rules strip self-echoes
- 8 uses of top-level `note:` in `edit_tasks` calls (tests 1a, 1b, 2a, 5a, 6a, 6b, 7a, 7b) → `actions.note.replace` form

**New scenarios needed:**

| Category | Test | Why |
|----------|------|-----|
| Note append | N-AppendNewline | Phase 55 append semantics with `\n` separator |
| Note append | N-AppendEmptyNote | Append to empty note sets directly (no leading separator) |
| Note append | N-AppendWhitespaceOnly | Whitespace note treated as empty for separator logic |
| Note warnings | N-AppendEmptyString | NOTE_APPEND_EMPTY warning on `append: ""` |
| Note warnings | N-AppendWhitespaceArg | NOTE_APPEND_EMPTY on `append: "   "` |
| Note warnings | N-ReplaceIdentical | NOTE_REPLACE_ALREADY_CONTENT on identical content |
| Note warnings | N-ReplaceAlreadyEmpty | NOTE_ALREADY_EMPTY when clearing an already-empty note |
| Note structure | N-NoteActionAlone | Note action valid without tags/move |
| Write type | E-EditCompletesWithChildren | New writable field |
| Write type | E-EditType | New writable field |
| Write type | E-EditNullRejected | Null rejected on both new fields |
| Write type | E-EditSingleActionsRejected | Enum validation on task-side |

### task-creation.md (19 tests) — NEEDS UPDATES

**New scenarios needed:**

| Category | Test | Why |
|----------|------|-----|
| Write type | T-AddCompletesWithChildren | New writable field on `add_tasks` |
| Write type | T-AddType | New writable field on `add_tasks` |
| Write type | T-AddTypeSingleActionsRejected | Enum validation |
| Create-default | T-CreateDefaultCompletesWithChildren | Preference-driven default (uses SOON_DUE pattern — see Setup) |
| Create-default | T-CreateDefaultType | Preference-driven default |

### list-tasks.md (46 tests) — NEEDS UPDATES

**Assertion fixes needed:**
- 1 use of `effective*` → `inherited*` (rename cleanup)

**New scenarios needed:**

| Category | Test | Why |
|----------|------|-----|
| Default flags | T-HasNote, T-HasRepetition, T-HasAttachments, T-IsSequential, T-DependsOnChildren | 5 derived read-only flags, tasks-side |
| Include group | T-HierarchyTask | Expanded hierarchy group (hasChildren + type + completesWithChildren) |
| Invariant | T-NoSuppressionInvariant | Critical contract: default + hierarchy emit redundantly |
| Stripping | T-CompletesWithChildrenInNeverStrip | `false` value survives stripping |
| Parent filter | P57-ParentByName/ById/Inbox/Deep/Compose | 5 basic tests for new filter |
| Anchor | P57-TaskAnchorIncluded, P57-ProjectNoAnchor | 2 anchor-semantics tests |
| Equivalence | P57-ParentProjectEquivalence | Byte-identical results — strong unification contract |
| Warnings (Phase 57) | P57-WarnFilteredSubtree, WarnFilteredSubtreeOnProject, WarnParentResolvesToProject, WarnParentProjectCombined, WarnParentMultiMatch, WarnParentInbox | 5-6 warning behavioral tests |

### list-projects.md (33 tests) — NEEDS UPDATES

**Assertion fixes needed:**
- 1 use of `effective*` → `inherited*`

**New scenarios needed:**

| Category | Test | Why |
|----------|------|-----|
| Default flags | P-HasNote, P-HasRepetition, P-HasAttachments | 3 project flags (confirmed in spec) |
| Default flags (ambiguous) | P-IsSequential | Live-verify whether project emits `isSequential` in default — see cross-cutting ambiguity 4 |
| Include group | P-HierarchyProject | Hierarchy group on projects with full type enum |
| ProjectType | P-ProjectTypeEnum | `singleActions` > `sequential` > `parallel` precedence |

### read-lookups.md (8 tests) — NEEDS UPDATES

**New scenarios needed:**

| Category | Test | Why |
|----------|------|-----|
| Parity | L-GetTaskNewFlags | Verify `get_task` exposes same presence flags and hierarchy fields as `list_tasks` |

### validation-errors.md (35 tests) — NEEDS UPDATES

**New scenarios needed:**

| Category | Test | Why |
|----------|------|-----|
| Note actions | VE-NoteAppendWithReplace | NOTE_APPEND_WITH_REPLACE error |
| Note actions | VE-NoteNoOperation | NOTE_NO_OPERATION error |
| Extra=forbid | VE-RejectHasNote/IsSequential/DependsOnChildren/DerivedOnEdit | FLAG-08 contract (6 derived read-only flags) |
| Batch limit | VE-AddBatchLimit, VE-EditBatchLimit | 51+ items → schema error |
| Parent errors | VE-ParentArrayRejected, VE-ParentInboxContradiction | Phase 57 — schema and contradiction errors |

### batch-processing.md (2 tests) — NEEDS EXPANSION

**New scenarios needed:**

| Category | Test | Why |
|----------|------|-----|
| Best-effort | B-AddBestEffort | 3-item add with middle-item error |
| ID absence | B-AddItemIdAbsence | Failed add has no `id` field (not null) |
| Fail-fast | B-EditFailFast | 3-item edit with middle-item error → subsequent skipped |
| ID presence | B-EditSkippedHasId | Skipped edit items retain `id` |
| Stripping | B-BatchResultStripping | Null `warnings` arrays stripped in per-item result |
| Sequential | B-SequentialCommitted | Same-task sequential edits see committed state |
| Limit | B-CrossItemRefNotSupported | Cross-item references don't resolve |
| Format | B-ErrorPrefix | "Task N:" prefix format |

### date-filtering.md (35 tests) — NEEDS UPDATES

**Assertion fixes needed:**
- 6 uses of `effective*` → `inherited*` (date filter tests that reference inherited dates)

### repetition-rules.md (40 tests) — NEEDS UPDATES

**Assertion fixes needed:**
- 1 use of `effective*` → `inherited*`

### integration-flows.md (8 tests) — NEEDS UPDATES

**Assertion fixes needed:**
- 1 use of top-level `note:` in `edit_tasks` call (line 51) → `actions.note.replace`

### Suites that DON'T need changes (v1.4 + Phases 56 + 57 scope)

| Suite | Why it's fine |
|-------|---------------|
| tag-operations.md | Tag operations untouched; the actions envelope was already in place |
| move-operations.md | Move semantics unchanged; batch changes are covered by batch-processing.md |
| lifecycle.md | Lifecycle unaffected by response shaping / batch / notes / property surface / parent filter |
| simple-list-tools.md | `list_tags`, `list_folders`, `list_perspectives` explicitly excluded from `include`/`only` |
| reads-combined.md | Composite — updated via Chunk 2 registration (add response-shaping row); no new content |
| writes-combined.md | Composite — no structural change needed; individual member suites are updated in chunks 1/4/5/6 |

---

## Warning/Error Inventory

Every new warning/error from v1.4 + v1.4.1 (Phases 56 + 57) that needs at least one UAT test.

### Errors

| ID | Source | Trigger | Assertion style | Covered By (target chunk/test) |
|----|--------|---------|-----------------|--------------------------------|
| INCLUDE_INVALID_TASK | 53-CONTEXT §5 | Invalid field-group name in `include` on `list_tasks` | Behavioral | Chunk 2 / Test 2c |
| INCLUDE_INVALID_PROJECT | 53-CONTEXT §5 | Invalid field-group name in `include` on `list_projects` | Behavioral | Chunk 2 / Test 2c (representative) |
| NOTE_APPEND_WITH_REPLACE | 55-CONTEXT D-03 | Both `actions.note.append` and `.replace` set | Behavioral | Chunk 4 / VE-NoteAppendWithReplace |
| NOTE_NO_OPERATION | 55-CONTEXT D-03 | Empty `actions.note: {}` block | Behavioral | Chunk 4 / VE-NoteNoOperation |
| TYPE_SINGLEACTIONS_ON_TASK | PROP-04 | `type: "singleActions"` on add/edit task | Generic Pydantic enum error | Chunk 5 / T-AddTypeSingleActionsRejected + E-EditSingleActionsRejected |
| DERIVED_FIELD_REJECTED | FLAG-08 | Any of 6 derived flags in add/edit input | Generic Pydantic extra="forbid" | Chunk 5 / VE-Reject* |
| BATCH_LIMIT_EXCEEDED | BATCH-01 | 51+ items in add/edit | Generic Pydantic max_length | Chunk 6 / VE-*BatchLimit |
| PARENT_ARRAY_REJECTED | PARENT-01 | Array value on `parent` filter | Generic Pydantic type error | Chunk 7 / VE-ParentArrayRejected |
| PARENT_INBOX_CONTRADICTION | PARENT-01 | `parent: "$inbox", inInbox: false` | Same error as `project: "$inbox"` contradiction | Chunk 7 / VE-ParentInboxContradiction |

### Warnings

| ID | Source | Trigger | Assertion style | Covered By (target chunk/test) |
|----|--------|---------|-----------------|--------------------------------|
| INCLUDE_ONLY_CONFLICT | 53-CONTEXT D-06 | Both `include` and `only` specified | Behavioral (spec locks verbatim but we assert fluency per ambiguity 1) | Chunk 2 / Test 4 |
| INCLUDE_INVALID_FIELD | 53-CONTEXT D-05 | Invalid field name in `only` parameter | Behavioral | Chunk 2 / Test 3b |
| NOTE_APPEND_EMPTY | 55-CONTEXT D-04 / N1 | Empty or whitespace-only `append` value | Behavioral | Chunk 4 / N-AppendEmptyString, N-AppendWhitespaceArg |
| NOTE_REPLACE_ALREADY_CONTENT | 55-CONTEXT D-05 / N2 | Replace with identical content | Behavioral | Chunk 4 / N-ReplaceIdentical |
| NOTE_ALREADY_EMPTY | 55-CONTEXT D-06 / N3 | Clear-note on already-empty note | Behavioral | Chunk 4 / N-ReplaceAlreadyEmpty |
| BATCH_ITEM_ERROR_PREFIX | 54-CONTEXT D-03 | Any service-layer per-item error | Behavioral ("Task N:" prefix present and fluent) | Chunk 6 / B-ErrorPrefix + indirectly B-AddBestEffort/EditFailFast |
| BATCH_ITEM_SKIPPED | 54-CONTEXT D-04 | `edit_tasks` item skipped due to earlier failure | Behavioral (references failing item index, fluent) | Chunk 6 / B-EditFailFast |
| FILTERED_SUBTREE_WARNING | 57-CONTEXT D-13 (WARN-01) | `project` OR `parent` combined with any other dimensional filter | Behavioral (spec locks verbatim with U+2014 em-dash but we assert fluency per ambiguity 1) | Chunk 7 / P57-WarnFilteredSubtree + P57-WarnFilteredSubtreeOnProject |
| PARENT_RESOLVES_TO_PROJECT_WARNING | 57-CONTEXT D-13 (WARN-02) | `parent` substring resolves to projects only | Behavioral (pedagogical tone) | Chunk 7 / P57-WarnParentResolvesToProject |
| PARENT_PROJECT_COMBINED_WARNING | 57-CONTEXT D-13 (WARN-03) | Both `parent` and `project` specified | Behavioral (soft hint) | Chunk 7 / P57-WarnParentProjectCombined |
| FILTER_MULTI_MATCH (reuse) | 57-CONTEXT D-14 (WARN-04) | `parent` substring matches multiple tasks | Behavioral (reused existing infra) | Chunk 7 / P57-WarnParentMultiMatch |
| LIST_TASKS_INBOX_PROJECT_WARNING (reuse) | 57-CONTEXT D-14 (WARN-05) | `parent` substring matches inbox name | Behavioral (reused existing infra) | Chunk 7 / P57-WarnParentInbox (or folded into P57-ParentInbox) |

### Notes on inventory

- **All warning assertions are behavioral** per cross-cutting ambiguity 1. Even the two warnings with spec-locked verbatim text (INCLUDE_ONLY_CONFLICT, FILTERED_SUBTREE_WARNING with U+2014 em-dash) are asserted on fluency + presence + no-internals, not exact string match. This preserves Flo's ability to reword warnings over time without breaking UAT.
- **No new warnings for Phase 56** — the property-surface work is pure emission/stripping and schema rejection.
- **Phase 57 adds 3 new warning constants + reuses 2** — all five are covered by Chunk 7.

---

## Combined Suite Strategy

### reads-combined.md
- Currently aggregates: list-tasks, date-filtering, list-projects, simple-list-tools, validation-errors (5 suites, ~172 tests)
- Chunk 2 adds: response-shaping.md as a 6th aggregated suite (~14 tests)
- Chunks 3, 7 add tests to existing member suites (list-tasks gets ~8 from Chunk 3 + ~13 from Chunk 7; validation-errors gets ~8 from Chunks 4-7)
- Estimated new total: ~220 tests
- No restructuring needed — just add the new suite's section with its prefix letter (next in sequence)

### writes-combined.md
- Currently aggregates: read-lookups, task-creation, edit-operations, tag-operations, move-operations, lifecycle, inheritance, integration-flows, repetition-rules (9 suites, 154 tests)
- Chunks 1/4/5/6 add tests to existing member suites → count increases naturally, no new suite needed
- Estimated new total: ~200 tests (from ~30 new + ~10 assertion fixes across member suites)
- No restructuring needed; the composite auto-expands via member-suite edits

### No combined-suite SPLIT recommended at this time
- Both composites grow meaningfully (reads ~220, writes ~200) but stay manageable
- The existing split by read/write axis is still the right factoring
- Re-evaluate at the v1.5 milestone boundary when project-writes add another significant write-side chunk

---

## Summary of Work

| Suite | Action | New Tests | Assertion Fixes |
|-------|--------|-----------|-----------------|
| inheritance.md | Rename + new fields + semantics | 6 | ~32 (effective→inherited + semantic rewrites) |
| edit-operations.md | Notes + new writable fields | 13 | ~9 (8 top-level-note + 1 effective) |
| task-creation.md | New writable fields + defaults | 5 | 0 |
| list-tasks.md | Presence flags + hierarchy + Phase 57 parent filter | ~21 (8 Chunk 3 + 13 Chunk 7) | 1 |
| list-projects.md | Project flags + ProjectType | 5 | 1 |
| read-lookups.md | get_task parity | 1 | 0 |
| validation-errors.md | Note actions + derived + batch + parent errors | 10 | 0 |
| batch-processing.md | Per-item semantics + fail-modes | 10 | 0 |
| date-filtering.md | effective → inherited | 0 | ~6 |
| repetition-rules.md | effective → inherited | 0 | 1 |
| integration-flows.md | Top-level note → actions.note | 0 | 1 |
| **NEW response-shaping.md** | **Create suite + register** | ~14 | 0 |
| **Total** | | **~85** | **~51** |

---

## Final Cleanup

Once ALL chunks are complete and committed, and the user has validated everything:

1. Run `/uat-suite-updater` one more time — it will enter Completion mode and archive this file to `.research/uat-suite-seeds/v1.4.1.md` (covers v1.4 + Phases 56 + 57; the whole v1.4.1 milestone)
2. The worktree branch is now ready for the user to review and merge to main
