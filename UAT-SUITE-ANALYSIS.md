# UAT Suite Analysis — v1.3.1 "First-Class References"

## How to Use This File

This file is the output of a research session that analyzed what v1.3.1 changed vs what existing UAT suites cover. It contains everything a fresh agent needs to update the suites without re-doing the research.

**Workflow:** Run `/uat-suite-updater` in a new session. When it asks what feature you're working on, point it here: "Read `UAT-SUITE-ANALYSIS.md` at the repo root — it has the full gap analysis. Pick up from the next unchecked chunk." The agent should:
1. Read this file
2. Find the next unchecked chunk
3. Use the gap analysis + warning/error inventory (later in this file) as its research input — it does NOT need to re-research the codebase from scratch
4. Follow the uat-suite-updater skill workflow from Step 3 onward (collect user's known tests → suggest additions → get sign-off → write)
5. After writing, mark the chunk as done by checking its box

**Important:** The agent still needs to do its own Step 2 (research) for the specific suites it's updating — the gap tables below are a starting point, not exhaustive. The agent should verify against actual source code, especially for exact warning strings.

---

## Progress

- [x] Chunk 1 — Write-side suites ($inbox + response shape)
- [x] Chunk 2 — list-tasks.md
- [x] Chunk 3 — list-projects.md + simple-list-tools.md
- [x] Chunk 4 — validation-errors.md
- [ ] Chunk 5 — Composite manifests + SKILL.md + cleanup
- [ ] **Delete this file** (all chunks done, everything merged)

---

## Chunks — Task List

### Chunk completion protocol

After finishing the suite edits for a chunk, the agent does NOT commit. Instead:

1. **Summarize changes** — list every file modified, tests added, assertions fixed
2. **Tell the user what to review** — which suite files to read, what to look for (new test wording, assertion accuracy, correct line references)
3. **Suggest spot-checks** — specific things the user can try in OmniFocus via the MCP tools to sanity-check the test descriptions (e.g., "try `get_project('$inbox')` and verify you get the error the test expects")
4. **Wait for validation** — user reviews, tries the spot-checks, gives thumbs up or requests changes
5. **On approval**: commit the suite changes, then update the Progress checklist above (check the box)

This ensures the user stays in the loop and no broken test descriptions get committed.

---

### Chunk 1: Write-side suites — `$inbox` + response shape ◻️

**Suites:** task-creation.md, move-operations.md, read-lookups.md, integration-flows.md

**What to do:**
- **task-creation**: Add tests for `parent: "$inbox"` (creates in inbox), `parent: null` (error), `parent: "$trash"` (invalid system location error). Fix test 1a assertion (`inInbox: true` → check `project.id == "$inbox"`). Fix test 1b assertion (parent format is now `{task: {id, name}}`). Add response shape test for enriched `parent`/`project` on created tasks.
- **move-operations**: Add tests for `moveTo: {ending: "$inbox"}` and `{beginning: "$inbox"}` as inbox move. Add null rejection tests for `ending: null` and `beginning: null`. Add `before: "$inbox"` and `after: "$inbox"` error tests (should suggest beginning/ending). Fix tests 1a (lines 62-65: `inInbox` → `project.id == "$inbox"`), 1b (line 69: same), and report row 1a (line 181).
- **read-lookups**: Add `get_project("$inbox")` error test. Add/update response shape assertions: `get_task` returns tagged `parent` wrapper + enriched `project`; `get_project` returns enriched `folder`/`nextTask`; `get_tag` returns enriched `parent`.
- **integration-flows**: Fix parent assertions in G-2 (line 54), G-4 (lines 68-69), G-5 (lines 73-74) — parent is now `{task: {id, name}}` not a flat reference.

**Est. scope:** ~14 new tests + ~11 assertion fixes across 4 suite files.

---

### Chunk 2: list-tasks.md ◻️

**Suite:** list-tasks.md (currently 35 tests — biggest update)

**What to do:**
- Add `$inbox` filter tests: `project: "$inbox"` returns inbox tasks; equivalence with `inInbox: true`; `project: "$inbox", inInbox: true` silently accepted (redundant).
- Add contradiction error tests (run INDIVIDUALLY): `project: "$inbox", inInbox: false` → CONTRADICTORY_INBOX_FALSE; `inInbox: true, project: "<real-project>"` → CONTRADICTORY_INBOX_PROJECT.
- Add inbox name warning test: `project: "Inbox"` (substring match on real project name) → LIST_TASKS_INBOX_PROJECT_WARNING.
- Add `ALL` availability tests: `availability: ["ALL"]` returns all 4 states; `availability: ["ALL", "AVAILABLE"]` → AVAILABILITY_MIXED_ALL warning.
- Add null/empty rejection tests (run INDIVIDUALLY): `project: null` → FILTER_NULL; `flagged: null` → FILTER_NULL; `tags: []` → TAGS_EMPTY; `availability: []` → AVAILABILITY_EMPTY.
- Fix test 6d (line 228): remove `inInbox` from camelCase field list; add `parent` (tagged wrapper), `project` (`{id, name}`).
- Fix tests 1e/1f: assertions are behaviorally correct but wording references `inInbox` field — update to reference `project.id == "$inbox"` as the inbox indicator.

**Est. scope:** ~13 new tests + ~2 assertion fixes.

---

### Chunk 3: list-projects.md + simple-list-tools.md ◻️

**Suites:** list-projects.md (25 tests), simple-list-tools.md (18 tests)

**What to do for list-projects:**
- Add `$inbox` search warning test: `list_projects` with `search: "Inbox"` → LIST_PROJECTS_INBOX_WARNING.
- Add `ALL` availability: `availability: ["ALL"]` returns all states; `availability: ["ALL", "DROPPED"]` → AVAILABILITY_MIXED_ALL.
- Add null/empty rejection (run INDIVIDUALLY): `folder: null` → FILTER_NULL; `flagged: null` → FILTER_NULL; `availability: []` → AVAILABILITY_EMPTY.
- Fix test 7b (line 190): add `folder` and `nextTask` as enriched `{id, name}` references in camelCase shape check.

**What to do for simple-list-tools:**
- Add `ALL` availability for tags: `availability: ["ALL"]`; for folders: `availability: ["ALL"]`.
- Add mixed ALL warning: one test on either tool with `["ALL", "AVAILABLE"]`.
- Add null rejection: `search: null` on any tool → FILTER_NULL.
- Add empty availability: `availability: []` on any tool → AVAILABILITY_EMPTY.
- Fix test 2d (line 119): folder `parent` is now `{id, name}` not bare ID.
- Fix test 5b (line 165): tag/folder `parent` fields are enriched.

**Est. scope:** ~14 new tests + ~3 assertion fixes across 2 suite files.

---

### Chunk 4: validation-errors.md ◻️

**Suite:** validation-errors.md (currently 17 tests)

**What to do:**
- Add cross-tool error formatting tests for ALL new v1.3.1 error types. These test that the error messages are clean (no pydantic internals, camelCase field names, actionable text). The errors are already tested for *behavior* in chunks 1-3; this suite tests *formatting quality*.
- New tests:
  - `list_tasks(project: null)` — FILTER_NULL, clean message
  - `list_projects(folder: null)` — FILTER_NULL, cross-tool consistency
  - `list_tasks(tags: [])` — TAGS_EMPTY, clean message
  - `list_tasks(availability: [])` — AVAILABILITY_EMPTY, clean message with ALL hint
  - `edit_tasks(moveTo: {ending: null})` — MOVE_NULL_CONTAINER, mentions `$inbox`
  - `add_tasks(parent: null)` — ADD_PARENT_NULL, clean message
  - `get_project("$inbox")` — GET_PROJECT_INBOX, educational error
  - `add_tasks(parent: "$trash")` — INVALID_SYSTEM_LOCATION, lists valid locations
  - `add_tasks(parent: "$foo")` — RESERVED_PREFIX, explains `$` is reserved
- **Important:** Check which of these overlap with error tests already added in chunks 1-3. This suite focuses on message *formatting* (no `type=`, no `input_value`, camelCase in field names, no `_Unset`), not just behavior. If a chunk 1-3 suite already has the error test, this suite should still test the *formatting* separately if the error is a new type.

**Est. scope:** ~9 new tests + 0 assertion fixes.

---

### Chunk 5: Composite manifests + SKILL.md + cleanup ◻️

**No uat-suite-updater needed** — this is a structural task, not a test-writing task.

**What to do:**
1. Create `writes-combined.md` composite manifest referencing (in this order): read-lookups, task-creation, edit-operations, tag-operations, move-operations, lifecycle, inheritance, integration-flows, repetition-rules
2. Create `reads-combined.md` composite manifest referencing: list-tasks, list-projects, simple-list-tools, validation-errors
3. Delete `v1.2-combined.md` and `v1.3-combined.md`
4. Update SKILL.md:
   - Replace the v1.2-combined and v1.3-combined rows in the "Available Test Suites" table with writes-combined and reads-combined
   - Update all base suite test counts to reflect additions from chunks 1-4
   - Update trigger phrases in the `description` frontmatter field (add "run writes", "run reads", "write regression", "read regression", "full regression")
5. Verify the composite manifests follow the exact format of existing composites (v1.2-combined.md is the template)

**Est. scope:** 2 new files, 2 deletions, 1 file update.

---

## Reference Material

Everything below is research output — the chunks above reference it. Read the relevant sections when working on a chunk.

---

## What v1.3.1 Built (Phases 39–44)

Six phases delivering three cross-cutting themes:

### Theme A: `$inbox` System Location
- `$inbox` as explicit location across reads AND writes
- Write-side: `add_tasks(parent: "$inbox")`, `edit_tasks(moveTo: {ending: "$inbox"})`
- Read-side: `list_tasks(project: "$inbox")` = equivalent to `inInbox: true`
- Guards: `get_project("$inbox")` → error, `list_projects` search "inbox" → warning
- Contradictions: `$inbox + inInbox=false` → error, `inInbox=true + project` → error
- Null rejection: `beginning: null`, `ending: null`, `parent: null` all produce educational errors
- `before/after: "$inbox"` → error suggesting `beginning`/`ending`

### Theme B: Enriched References
- All cross-references now `{id, name}` pairs (was bare ID strings)
- `Task.parent` → tagged wrapper: `{"project": {id, name}}` or `{"task": {id, name}}`
- `Task.project` → always present: `{id: "$inbox", name: "Inbox"}` for inbox tasks
- `Task.inInbox` field **removed entirely**
- `Project.folder` → `FolderRef {id, name}` (was `str | None`)
- `Project.nextTask` → `TaskRef {id, name}` (was `str | None`)
- `Tag.parent` → `TagRef {id, name}` (was `str | None`)
- `Folder.parent` → `FolderRef {id, name}` (was `str | None`)

### Theme C: Patch Semantics on List Filters
- All list query filter fields migrated from `T | None = None` to `Patch[T] = UNSET`
- `null` on any filter → error: "'{field}' cannot be null. To skip this filter, simply omit the field."
- `tags: []` → error: "cannot be empty"
- `availability: []` → error: "cannot be empty — include at least one status value, or use [\"ALL\"]"
- New `ALL` availability shorthand: `availability: ["ALL"]` expands to all statuses
- Mixed ALL warning: `["ALL", "AVAILABLE"]` → "'ALL' already includes every status"

---

## Gap Analysis by Suite

### 1. list-tasks.md (35 tests) — NEEDS UPDATES

**New scenarios needed:**

| Category | Test | Why |
|----------|------|-----|
| $inbox filter | `project: "$inbox"` returns inbox tasks | Theme A — core feature |
| $inbox filter | `project: "$inbox"` results = `inInbox: true` results | Theme A — equivalence |
| $inbox contradiction | `project: "$inbox", inInbox: false` → error | Theme A — CONTRADICTORY_INBOX_FALSE |
| $inbox contradiction | `inInbox: true, project: "RealProject"` → error | Theme A — CONTRADICTORY_INBOX_PROJECT |
| $inbox redundant | `project: "$inbox", inInbox: true` → succeeds silently | Theme A — accepted redundancy |
| Inbox name warning | `project: "Inbox"` (name match) → warning about virtual location | Theme A — LIST_TASKS_INBOX_PROJECT_WARNING |
| ALL shorthand | `availability: ["ALL"]` → returns all 4 states | Theme C |
| Mixed ALL | `availability: ["ALL", "AVAILABLE"]` → warning | Theme C |
| Null filter | `project: null` → error | Theme C — FILTER_NULL |
| Null filter | `flagged: null` → error | Theme C — FILTER_NULL |
| Empty tags | `tags: []` → error | Theme C — TAGS_EMPTY |
| Empty availability | `availability: []` → error | Theme C — AVAILABILITY_EMPTY |
| Response shape | `task.parent` is tagged wrapper, `task.project` is `{id, name}`, no `inInbox` field | Theme B |

**Existing tests that may need assertion updates:**
- Test 6d (response shape) — now must check for `parent` tagged wrapper, `project` ref, absence of `inInbox`
- Test 1e/1f (inInbox filter) — assertions still valid but response shape changed (no `inInbox` field in response)

---

### 2. list-projects.md (25 tests) — NEEDS UPDATES

| Category | Test | Why |
|----------|------|-----|
| $inbox guard | `list_projects` search matching "inbox" → warning | Theme A — LIST_PROJECTS_INBOX_WARNING |
| ALL shorthand | `availability: ["ALL"]` → all states | Theme C |
| Mixed ALL | `availability: ["ALL", "DROPPED"]` → warning | Theme C |
| Null filter | `folder: null` → error | Theme C — FILTER_NULL |
| Null filter | `flagged: null` → error | Theme C — FILTER_NULL |
| Empty availability | `availability: []` → error | Theme C — AVAILABILITY_EMPTY |
| Response shape | `project.folder` is `{id, name}`, `project.nextTask` is `{id, name}` | Theme B |

**Existing tests that may need assertion updates:**
- Test 7b (response shape) — must check enriched folder/nextTask references

---

### 3. simple-list-tools.md (18 tests) — NEEDS UPDATES

| Category | Test | Why |
|----------|------|-----|
| ALL shorthand (tags) | `availability: ["ALL"]` | Theme C |
| ALL shorthand (folders) | `availability: ["ALL"]` | Theme C |
| Mixed ALL | Any tool with `["ALL", "AVAILABLE"]` → warning | Theme C |
| Null filter | `search: null` → error | Theme C — FILTER_NULL |
| Empty availability | `availability: []` → error | Theme C — AVAILABILITY_EMPTY |
| Response shape (tags) | `tag.parent` is `{id, name}` | Theme B |
| Response shape (folders) | `folder.parent` is `{id, name}` | Theme B |

**Existing tests that may need assertion updates:**
- Test 5b (response shape) — enriched parent references

---

### 4. validation-errors.md (17 tests) — NEEDS UPDATES

New v1.3.1 errors that should be tested for formatting quality:

| Category | Test | Why |
|----------|------|-----|
| Filter null | `list_tasks(project: null)` — clean error, no internals | Theme C |
| Filter null | `list_projects(folder: null)` — clean error | Theme C |
| Tags empty | `list_tasks(tags: [])` — clean error | Theme C |
| Availability empty | `list_tasks(availability: [])` — clean error | Theme C |
| Move null | `edit_tasks(moveTo: {ending: null})` — clean error | Theme A |
| Add parent null | `add_tasks(parent: null)` — clean error | Theme A |
| $inbox guard | `get_project("$inbox")` — clean error | Theme A |
| System location | `add_tasks(parent: "$trash")` — clean error about valid locations | Theme A — INVALID_SYSTEM_LOCATION |
| Reserved prefix | `add_tasks(parent: "$foo")` — clean error | Theme A — RESERVED_PREFIX |

---

### 5. move-operations.md (16 tests) — NEEDS UPDATES

| Category | Test | Why |
|----------|------|-----|
| $inbox move | `moveTo: {ending: "$inbox"}` — moves to inbox | Theme A — core |
| $inbox move | `moveTo: {beginning: "$inbox"}` — moves to inbox start | Theme A — core |
| Null rejection | `moveTo: {ending: null}` → error | Theme A — MOVE_NULL_CONTAINER |
| Null rejection | `moveTo: {beginning: null}` → error | Theme A — MOVE_NULL_CONTAINER |
| Anchor $inbox | `moveTo: {before: "$inbox"}` → error suggesting beginning/ending | Theme A — MOVE_NULL_ANCHOR context |
| Anchor $inbox | `moveTo: {after: "$inbox"}` → error suggesting beginning/ending | Theme A |

---

### 6. task-creation.md (14 tests) — NEEDS UPDATES

| Category | Test | Why |
|----------|------|-----|
| $inbox parent | `parent: "$inbox"` creates in inbox (same as omitting) | Theme A |
| Null parent | `parent: null` → error | Theme A — ADD_PARENT_NULL |
| Invalid system loc | `parent: "$trash"` → error | Theme A — INVALID_SYSTEM_LOCATION |
| Response shape | Created task has enriched `parent`/`project` fields | Theme B |

---

### 7. read-lookups.md (7 tests) — NEEDS UPDATES

| Category | Test | Why |
|----------|------|-----|
| $inbox guard | `get_project("$inbox")` → error | Theme A |
| Response shape | `get_task` returns enriched parent/project | Theme B |
| Response shape | `get_project` returns enriched folder/nextTask | Theme B |
| Response shape | `get_tag` returns enriched parent | Theme B |

---

### 8. Suites that DON'T need changes

| Suite | Why it's fine |
|-------|---------------|
| **inheritance.md** (8 tests) | Tests effective field inheritance (dates, flagged). No cross-reference assertions. Shape changes don't affect what's tested. |
| **lifecycle.md** (12 tests) | Tests complete/drop/cross-state. No parent/project assertions. |
| **tag-operations.md** (15 tests) | Tests tag add/remove/replace. Tag operations unchanged in v1.3.1. |
| **integration-flows.md** (8 tests) | End-to-end flows. May need response shape updates but these are loose assertions — **verify during implementation**. |

---

## New Suite Needed?

**Recommendation: No new standalone suite.**

All v1.3.1 scenarios fit naturally into existing suites:
- `$inbox` write scenarios → move-operations, task-creation
- `$inbox` read scenarios → list-tasks, list-projects, read-lookups
- Enriched references → response shape tests in each existing suite
- Patch/ALL filter changes → list-tasks, list-projects, simple-list-tools
- New error formatting → validation-errors

Creating a separate "$inbox" or "references" suite would duplicate setup and fragment related tests. Better to extend existing suites where the context already exists.

---

## v1.2 Suite Breakage Analysis

v1.3.1's response shape changes (Theme B) break existing assertions in v1.2-era suites:

| Suite | What breaks | Why |
|-------|-------------|-----|
| **move-operations** (lines 62, 64, 65, 69, 181) | `verify inInbox: true/false`, report row "`inInbox` flips" | `inInbox` field removed; inbox detection now via `project.id == "$inbox"` |
| **task-creation** (line 48) | `inInbox: true or parent is null` | `inInbox` gone; `parent` is never null (always tagged wrapper) |
| **list-tasks** (line 228) | Lists `inInbox` as camelCase field to verify | Field no longer exists in response |
| **simple-list-tools** (line 119) | `parent field set to a non-null folder ID` | Now `{id, name}` pair, not bare ID string |
| **integration-flows** (lines 54, 68, 74) | `parent id matches UAT-Integration` | Parent is now tagged `{task: {id, name}}` |
| **read-lookups** (line 41) | `parent referencing UAT-ReadLookups` | Format changed to tagged wrapper |
| **list-projects** (line 190) | `nextTask` in camelCase check | Now enriched `{id, name}` reference |

**Conclusion:** v1.2 suites would fail today. They MUST be updated regardless of combined suite strategy.

---

## Combined Suite Strategy

**Decision: Replace v1.2-combined and v1.3-combined with 2 thematic composites.**

The old milestone-based composites (v1.2, v1.3) don't make sense anymore — v1.3.1 is cross-cutting and breaks the milestone boundary. Instead, reorganize by theme:

### New composite structure

| Composite | Base Suites | Est. Tests | Theme |
|-----------|-------------|-----------|-------|
| **writes-combined.md** | read-lookups, task-creation, edit-operations, tag-operations, move-operations, lifecycle, inheritance, integration-flows, repetition-rules | ~155 | Everything that creates/modifies/reads individual tasks |
| **reads-combined.md** | list-tasks, list-projects, simple-list-tools, validation-errors | ~120 | Everything that queries/filters/lists |

### Rationale
- **Two commands** for full regression, not thirteen individual suites
- Natural split: write pipeline changes → run writes. Filter changes → run reads. Cross-cutting → run both.
- Each composite is ~1,200 lines of spec — large but manageable in context
- If either grows too large later, split further (e.g., separate repetition-rules from core writes)
- Old v1.2-combined.md and v1.3-combined.md become obsolete — delete them

### Implementation
1. Update all 8 affected base suites in-place (fix broken assertions + add new scenarios)
2. Create writes-combined.md and reads-combined.md as new composite manifests
3. Delete v1.2-combined.md and v1.3-combined.md
4. Update SKILL.md: replace old composite entries with new ones, update trigger phrases

---

## Summary of Work

| Suite | Action | New Tests | Assertion Fixes |
|-------|--------|-----------|-----------------|
| list-tasks.md | Add $inbox filters, contradictions, ALL, null rejection, response shape | ~13 | ~2 (inInbox refs in 6d, 1e/1f) |
| list-projects.md | Add $inbox warning, ALL, null rejection, response shape | ~7 | ~1 (nextTask in 7b) |
| simple-list-tools.md | Add ALL, null rejection, response shape | ~7 | ~1 (folder parent in 2d, 5b) |
| validation-errors.md | Add filter null, move null, parent null, $inbox errors | ~9 | 0 |
| move-operations.md | Add $inbox moves, null rejection, anchor errors + fix inInbox assertions | ~6 | ~4 (inInbox → project.id checks) |
| task-creation.md | Add $inbox parent, null parent, response shape | ~4 | ~2 (inInbox, parent format) |
| read-lookups.md | Add $inbox guard, response shape enrichment | ~4 | ~2 (parent format) |
| integration-flows.md | Fix parent assertions for tagged wrapper format | 0 | ~3 (parent shape in G-2, G-4, G-5) |
| **Total** | | **~50** | **~15** |

---

## Warning/Error Inventory for Cross-Reference

Every new warning/error from v1.3.1 that needs at least one UAT test:

### Errors
| ID | Text Pattern | Covered By |
|----|-------------|------------|
| MOVE_NULL_CONTAINER | "{field} cannot be null. To move to inbox, use '$inbox'..." | move-operations |
| ADD_PARENT_NULL | "parent cannot be null. Omit the field..." | task-creation |
| INVALID_SYSTEM_LOCATION | "Unknown system location '{value}'..." | validation-errors, task-creation |
| RESERVED_PREFIX | "'{value}' starts with '$'..." | validation-errors |
| CONTRADICTORY_INBOX_FALSE | "Contradictory filters: project=$inbox + inInbox=false..." | list-tasks |
| CONTRADICTORY_INBOX_PROJECT | "Contradictory filters: inInbox=true + project..." | list-tasks |
| GET_PROJECT_INBOX | "The inbox is not a real OmniFocus project..." | read-lookups, validation-errors |
| FILTER_NULL | "'{field}' cannot be null..." | validation-errors, list-tasks |
| TAGS_EMPTY | "'{field}' cannot be empty..." | validation-errors, list-tasks |
| AVAILABILITY_EMPTY | "'{field}' cannot be empty — include at least one..." | validation-errors, list-tasks |

### Warnings
| ID | Text Pattern | Covered By |
|----|-------------|------------|
| LIST_TASKS_INBOX_PROJECT_WARNING | "project filter matches Inbox by name but..." | list-tasks |
| LIST_PROJECTS_INBOX_WARNING | "$inbox appears as project on tasks but..." | list-projects |
| AVAILABILITY_MIXED_ALL | "'ALL' already includes every status..." | list-tasks (or any list suite) |

---

## Final Cleanup

Once ALL chunks are complete and committed, and the user has validated everything:

1. Delete this file: `git rm UAT-SUITE-ANALYSIS.md && git commit -m "chore: remove UAT suite analysis (all chunks completed)"`
2. The worktree branch is now ready for the user to review and merge to main
