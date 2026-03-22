# Phase 28: Expand golden master coverage and improve field normalization - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-22
**Phase:** 28-expand-golden-master-coverage-and-improve-field-normalization
**Areas discussed:** Scenario numbering & ordering, Setup prerequisites, InMemoryBridge parity, Normalization strategy, Execution order, OmniFocus surprises

---

## Folded Todos

Both pending todos folded into Phase 28 scope:

- "Expand golden master with 18 additional scenarios" (score: 0.6)
- "Normalize completionDate and dropDate to presence check instead of stripping" (score: 0.6)

**User's note:** "Yes, the whole point of phase 28 is to implement those two to-dos."

---

## Scenario Numbering & Ordering


| Option              | Description                                              | Selected |
| ------------------- | -------------------------------------------------------- | -------- |
| Continue from 21    | Simple sequential append. No renumbering.                |          |
| Regroup by category | Renumber all into logical groups. Full re-capture.       | ✓        |
| Sub-numbering       | 09a, 09b style. Preserves existing but complicates glob. |          |


**User's choice:** Regroup by category
**Notes:** None — straightforward selection.

### Follow-up: Category grouping


| Option            | Description                             | Selected |
| ----------------- | --------------------------------------- | -------- |
| By operation type | 01-09 add, 10-29 edit, 30-39 move, etc. | ✓        |
| By complexity     | Single-field → multi-field → combined   |          |


**User's choice:** By operation type
**Notes:** Selected the detailed preview layout with specific scenario assignments.

### Follow-up: Naming convention

User rejected the AskUserQuestion about filename conventions and proposed **subfolders** instead of filename prefixes. Discussion led to numbered subfolders.

### Follow-up: Subfolder layout


| Option                              | Description                                                  | Selected |
| ----------------------------------- | ------------------------------------------------------------ | -------- |
| Category subfolders                 | snapshots/add/, snapshots/edit/, etc. Files numbered within. | ✓        |
| Flat with global numbers            | All in snapshots/, global numbering                          |          |
| Category subfolders + global prefix | Both folder and filename prefix                              |          |


**User's choice:** Category subfolders
**Notes:** None — clean separation.

---

## Setup Prerequisites


| Option                         | Description                                                      | Selected |
| ------------------------------ | ---------------------------------------------------------------- | -------- |
| Extend manual setup            | Add GM-TestProject2 to prerequisites. Anchor tasks auto-created. | ✓        |
| Script auto-creates everything | Programmatic creation via bridge.                                |          |


**User's choice:** Extend manual setup
**Notes:** None.

### Follow-up: Cleanup strategy


| Option                  | Description                                                | Selected |
| ----------------------- | ---------------------------------------------------------- | -------- |
| Single cleanup root     | Consolidate under one deletable task + list cleanup steps. | ✓        |
| Auto-cleanup via bridge | Script deletes test tasks.                                 |          |


**User's choice:** Single cleanup root
**Notes:** User refined: cleanup task should be in inbox (easy to find). Projects and tags should persist across captures — only tasks are ephemeral. "I could checkpoint in the middle, make me run the test."

---

## InMemoryBridge Parity


| Option                   | Description                                                  | Selected |
| ------------------------ | ------------------------------------------------------------ | -------- |
| Capture first, fix after | Golden master is source of truth. Failing tests = TODO list. | ✓        |
| Fix InMemoryBridge first | Speculative implementation before capture.                   |          |
| Interleave per category  | Capture → fix → capture → fix per category.                  |          |


**User's choice:** Capture first, fix after
**Notes:** User added important refinement: wants an explicit human checkpoint between capture and InMemoryBridge fixes. Plan 2 (fix phase) should be interactive — user triages failures together with Claude, deciding what's straightforward vs. needs discussion.

---

## Normalization Strategy

Extended discussion — user challenged initial recommendation of "only completionDate/dropDate."

### Initial proposal rejected

Claude initially proposed graduating only completionDate/dropDate and maybe effectiveFlagged. User asked "what other fields would be good candidates?" prompting deeper analysis.

### Key debate: effective fields — all or none

User pointed out that ALL effective fields use the same ancestor-chain inheritance mechanism. "I don't see how this effort is different from effective flag and the other one. I'd say either we do them all or we do none of them."

Claude acknowledged this was correct and revised recommendation.

### InMemoryBridge inheritance effort

User challenged whether inheritance was actually hard: "It's not the end of the world; it's just about going up the hierarchy." Claude confirmed: ~15-line helper method, simple parent-chain walk. No optimization needed for shallow hierarchies.

### Final normalization decision


| Field                                     | Graduation type             | Selected |
| ----------------------------------------- | --------------------------- | -------- |
| completionDate/dropDate                   | Presence-check (null vs "") | ✓        |
| effectiveCompletionDate/effectiveDropDate | Presence-check              | ✓        |
| effectiveFlagged                          | Exact match + inheritance   | ✓        |
| effectiveDueDate/DeferDate/PlannedDate    | Exact match + inheritance   | ✓        |
| repetitionRule                            | Exact match (null == null)  | ✓        |
| status/taskStatus                         | Stays UNCOMPUTED            | ✓        |


**User's choice:** Graduate all effective fields with inheritance scenarios + repetitionRule.
**Notes:** User specifically requested inheritance-specific golden master scenarios (07-inheritance/ subfolder) to make the graduation meaningful. Third test project (GM-TestProject-Dated) added to setup for inheritance testing.

---

## Execution Order Across Subfolders

User proposed numbered folder prefixes (`01-add/`, `02-edit/`, `03-move/`) instead of manifest file or hardcoded order. "Simple, easy to follow, easy to understand."

---

## OmniFocus Surprises Policy

User: "For everything that's straightforward fixes, let's do it, but if something means a huge change, then have another checkpoint with me." Plan 2 should be interactive — triage failures together.

---

## Milestone Closure

User: "Don't worry about closing the milestone; I will do this on my end." Not part of Phase 28 scope.

---

## Claude's Discretion

- Exact fixture JSON structure
- Contract test parametrization (subfolder discovery)
- How much capture script to reuse vs. rewrite
- Inheritance helper integration approach
- InMemoryBridge fix grouping strategy

## Deferred Ideas

- Deeper nesting scenarios (3+ levels) — unless golden master reveals issues
- Status/taskStatus graduation — time-dependent, complex, own phase if ever

