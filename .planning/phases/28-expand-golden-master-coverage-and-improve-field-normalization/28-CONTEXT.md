# Phase 28: Expand golden master coverage and improve field normalization - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Expand the golden master from 20 to ~42 scenarios covering all untested bridge code paths (null/clear semantics, anchor-based moves, combined operations, tag edge cases, status transitions, inheritance). Reorganize fixtures into numbered subfolders by operation category. Graduate 9 fields from VOLATILE/UNCOMPUTED to verified (presence-check or exact match). InMemoryBridge gets ancestor-chain inheritance logic for effective fields. Full re-capture against RealBridge required.

No new MCP tools, no behavioral changes to the server — pure test infrastructure expansion.

</domain>

<decisions>
## Implementation Decisions

### Scenario coverage
- **D-01:** Full reorganization into numbered subfolders: `01-add/`, `02-edit/`, `03-move/`, `04-tags/`, `05-lifecycle/`, `06-combined/`, `07-inheritance/`. Alphabetical sort = execution order. No manifest file needed.
- **D-02:** Scenarios within each folder numbered sequentially (01, 02, ...). Self-documenting ordering — capture script and contract test both sort by name.
- **D-03:** Full re-capture of ALL scenarios (existing 20 renumbered + 18 new + 4 inheritance = ~42 total). Not an incremental addition — clean slate with the new folder structure.

### Scenario layout

**01-add/ (6 scenarios)**
- 01: inbox task (minimal)
- 02: with parent
- 03: all fields
- 04: with tags
- 05: parent + tags
- 06: max payload (parent + tags + all dates + flagged + note + estimatedMinutes)

**02-edit/ (11 scenarios)**
- 01: rename
- 02: set note
- 03: clear note (null)
- 04: clear note (empty string)
- 05: flag
- 06: unflag
- 07: set dates (due + defer)
- 08: clear dates (null)
- 09: set estimated minutes
- 10: clear estimated minutes (null)
- 11: set/clear plannedDate

**03-move/ (7 scenarios)**
- 01: to project (ending)
- 02: to inbox
- 03: to beginning
- 04: after anchor task
- 05: before anchor task
- 06: between projects (project A → project B)
- 07: task as parent (move under another task)

**04-tags/ (5 scenarios)**
- 01: add tags
- 02: remove tags
- 03: replace tags (remove all, add one)
- 04: add duplicate tag (already present)
- 05: remove absent tag (not on task)

**05-lifecycle/ (4 scenarios)**
- 01: complete
- 02: drop
- 03: set future deferDate → Blocked
- 04: clear deferDate → Available

**06-combined/ (3 scenarios)**
- 01: fields + move in same call
- 02: fields + lifecycle in same call
- 03: subtask add + move out

**07-inheritance/ (4 scenarios)**
- 01: task under project with dueDate → verify effectiveDueDate inherited
- 02: task under flagged project → verify effectiveFlagged = true
- 03: subtask under flagged parent task → verify effectiveFlagged chain
- 04: task under project with deferDate → verify effectiveDeferDate inherited

### Setup prerequisites
- **D-04:** Manual setup extended with two new entities:
  - `🧪 GM-TestProject2` — for project-to-project moves (scenario 03-move/06)
  - `🧪 GM-TestProject-Dated` — pre-configured with dueDate, deferDate, flagged=true for inheritance scenarios
- **D-05:** Anchor tasks for before/after moves are created automatically by earlier add/ scenarios and reused by 03-move/ via ID tracking. No extra manual step.
- **D-06:** Projects and tags persist across captures — no need to recreate them on subsequent runs. Script verifies they exist during setup.

### Cleanup
- **D-07:** All test tasks consolidated under a single `🧪 GM-Cleanup` task in the inbox at end of capture. User deletes one inbox task to clean up. Projects and tags are optional cleanup (listed in instructions but designed to persist for next capture).

### Normalization — field graduation
- **D-08:** `completionDate` and `dropDate` move from VOLATILE to **presence-check**: normalize non-null values to `"<set>"` sentinel instead of stripping. Verifies lifecycle transitions actually populate the field without caring about exact timestamp.
- **D-09:** `effectiveCompletionDate` and `effectiveDropDate` — same presence-check pattern as D-08.
- **D-10:** `effectiveFlagged` — graduates to **exact match**. InMemoryBridge already computes this for standalone tasks; inheritance helper extends it to ancestor chain.
- **D-11:** `effectiveDueDate`, `effectiveDeferDate`, `effectivePlannedDate` — graduate to **exact match**. InMemoryBridge gets ancestor-chain inheritance logic (walk parent → project, return first non-null).
- **D-12:** `repetitionRule` — graduates to **exact match**. All golden master tasks have null; InMemoryBridge also returns null. Verifies both sides agree (catches accidental non-null regressions).
- **D-13:** Fields remaining UNCOMPUTED after this phase: `status`, `taskStatus` (OmniFocus status computation intentionally out of scope — DueSoon, Overdue, Next are time-dependent).

### InMemoryBridge changes
- **D-14:** New `_compute_effective_field()` helper: walks parent chain (task → ... → project), returns first non-null value for the requested field. ~15 lines. Reused for all effective date fields.
- **D-15:** `effectiveFlagged` uses boolean OR variant: true if any ancestor is flagged.
- **D-16:** Effective fields populated on `add_task` and updated on `edit_task` (when direct field or parent changes).

### Execution flow / human checkpoints
- **D-17:** Plan 1: Rewrite capture script + update contract test infrastructure + normalization changes (subfolder layout, field graduation). All agent work.
- **D-18:** **Human checkpoint**: User runs capture against OmniFocus, reviews fixtures, commits golden master. Agent cannot do this (SAFE-01/02).
- **D-19:** Plan 2: **Interactive session** — run contract tests, triage failures together with user. Straightforward InMemoryBridge fixes done immediately. Surprising OmniFocus behavior discussed before deciding whether to match or document as known divergence. This is NOT a fully autonomous agent execution.

### Claude's Discretion
- Exact fixture JSON structure (fields, metadata per scenario)
- Contract test parametrization approach (how subfolders are discovered and iterated)
- How much of the existing capture script to reuse vs. rewrite
- Whether inheritance helper is a standalone method or integrated into existing add/edit handlers
- Grouping of InMemoryBridge fixes (one commit per category or per individual fix)

### Folded Todos
- **"Expand golden master with 18 additional scenarios"** — scenarios 21-38 from the todo are reorganized into the numbered subfolder layout above. Core coverage gaps addressed: null/clear semantics, anchor moves, combined ops, tag edge cases, status transitions.
- **"Normalize completionDate and dropDate to presence check instead of stripping"** — implemented as D-08 (presence-check sentinel normalization). Extended to also cover effectiveCompletionDate/effectiveDropDate (D-09).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Golden master infrastructure (current state)
- `tests/golden_master/normalize.py` — VOLATILE/UNCOMPUTED field definitions, normalization functions
- `tests/golden_master/snapshots/` — Current fixture files (will be reorganized)
- `tests/golden_master/README.md` — Overview and GOLD-01 regeneration rule
- `tests/test_bridge_contract.py` — Contract test: replays scenarios against InMemoryBridge

### Capture script
- `uat/capture_golden_master.py` — Interactive UAT script (human-run). Will be rewritten with new folder structure and scenarios.

### InMemoryBridge
- `tests/doubles/bridge.py` — Stateful InMemoryBridge: `_handle_add_task`, `_handle_edit_task`, `_handle_get_all`. Gets inheritance helper in this phase.

### Bridge protocol
- `src/omnifocus_operator/contracts/protocols.py` — Bridge protocol: `send_command(operation, params) -> dict`

### Prior phase context
- `.planning/phases/27-repository-contract-tests-for-behavioral-equivalence/27-CONTEXT.md` — Phase 27 decisions (D-01 through D-20) that established the golden master pattern

### Folded todos (original problem statements)
- `.planning/todos/pending/2026-03-22-expand-golden-master-with-18-additional-scenarios.md`
- `.planning/todos/pending/2026-03-22-normalize-completiondate-and-dropdate-to-presence-check-instead-of-stripping.md`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `normalize_for_comparison()` in `tests/golden_master/normalize.py` — extend with presence-check logic and remove graduated fields from UNCOMPUTED
- `filter_to_known_ids()` in `tests/golden_master/normalize.py` — already handles privacy filtering of get_all
- `_resolve_raw_parent()` in `tests/doubles/bridge.py` — parent disambiguation logic, reusable for inheritance chain walking
- `_find_containing_project_raw()` in `tests/doubles/bridge.py` — walks parent chain to find project, similar pattern to inheritance helper

### Established Patterns
- Capture script: 5-phase workflow (intro → manual setup → preview → capture → consolidation)
- Contract test: sequential replay with ID remapping (`id_map: {golden_id: bridge_id}`)
- Fixture format: `{scenario, description, operation, params, response, state_after, created_ids}`
- UAT scripts in `uat/` are standalone Python scripts, human-run, using RealBridge directly

### Integration Points
- `tests/golden_master/snapshots/` — reorganized from flat files to numbered subfolders
- `tests/test_bridge_contract.py` — updated to discover and sort subfolders
- `tests/doubles/bridge.py` — new `_compute_effective_field()` and `_compute_effective_flagged()` helpers
- `tests/golden_master/normalize.py` — VOLATILE/UNCOMPUTED field lists updated, presence-check logic added

</code_context>

<specifics>
## Specific Ideas

- Numbered folder prefixes encode execution order in the filesystem itself (same principle as database migration files) — no external manifest needed
- Projects and tags designed to persist across captures: cleanup only removes test tasks, not setup entities. Reduces friction for re-captures.
- `🧪 GM-Cleanup` task lives in inbox for easy discoverability during manual cleanup
- Plan 2 (InMemoryBridge fixes) is intentionally interactive — user triages failures and decides what to fix vs. document as known divergence

</specifics>

<deferred>
## Deferred Ideas

- **Inheritance scenarios for deeper nesting** — current scenarios test 1-2 levels (task → project, task → task → project). Deeper chains (3+ levels) deferred unless golden master reveals issues.
- **Status field graduation** — `status` and `taskStatus` remain UNCOMPUTED. OmniFocus status computation (DueSoon, Overdue, Next) is time-dependent and complex. Would be its own phase if ever implemented.
- **Milestone closure** — user handles v1.2.1 milestone closure separately, not part of Phase 28.

</deferred>

---

*Phase: 28-expand-golden-master-coverage-and-improve-field-normalization*
*Context gathered: 2026-03-22*
