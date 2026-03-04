# OmniFocus API Ground Truth

Empirical audit of the OmniFocus Automation (JXA) scripting API.
Every finding is verified by running scripts against a live OmniFocus database.

## Why This Exists

The OmniFocus Operator bridge translates JXA objects into Python models. This
translation must be exact. OmniFocus documentation is sparse and sometimes
misleading (e.g., `.name` on enums is documented but doesn't work). The only
reliable approach is empirical: run scripts, observe output, record facts.

This directory is the definitive reference. If a question arises about what
OmniFocus returns for a given property, the answer is here — backed by scripts
that can be re-run to verify.

## How to Run

1. Open OmniFocus
2. Menu: **Automation > Show Console**
3. Paste script contents into the console
4. Press **Cmd+Enter** (or click Run)
5. Read the output

## Scripts (run in order)

### Part 1: Project Discovery (READ-ONLY)

#### 01 — Project vs Root Task Scan ◻️
**What it checks:** Every field on `p.*` vs `p.task.*` across all projects.
Verifies task-only fields (added, modified, active, effectiveActive), tracks
effectiveCompletionDate behavior, measures status distributions, checks all
shared fields for divergence, and verifies id matching.
**What to look for:** Zero divergences on shared fields. Task-only fields should
be undefined on `p.*` and always defined on `p.task.*`. IDs should always match.

#### 02 — Project Effective Fields ◻️
**What it checks:** All 6 "effective*" fields (`effectiveDueDate`,
`effectiveDeferDate`, `effectiveCompletionDate`, `effectivePlannedDate`,
`effectiveDropDate`, `effectiveFlagged`) for the undefined-on-project bug.
**What to look for:** Which effective fields return `undefined` on `p.*` but
have values on `p.task.*`? Is `effectiveCompletionDate` the only broken one, or
are others broken too?

#### 03 — Status Enum Discovery ◻️
**What it checks:** All possible enum values for `Project.Status`, `Task.Status`,
`Tag.Status`, and `Folder.Status`. Tests cross-type compatibility (is
`Project.Status.Active === Tag.Status.Active`?). Exhaustive constant probe.
**What to look for:** Complete list of constants per type. Whether a single
switch function can handle all entity types. Any UNKNOWN values.

#### 04 — Project Status Cross-Reference ◻️
**What it checks:** Maps the relationship between `Project.Status` (Active/OnHold/
Done/Dropped), root task `active`/`effectiveActive`, and root task `Task.Status`.
**What to look for:** The mapping table — when a project is OnHold, what does the
root task show? When Done, is `active=false`? Any unexpected combinations?

### Part 2: Write-Side Verification

> ⚠️ **Scripts 05, 07, and 08 WRITE to your OmniFocus database.**
> All test entities use the "🧪 API Audit" tag for identification.
> Script 08 cleans everything up.

#### 05 — [WRITE] Create Test Data ⚠️
**What it does:** Creates a tag ("🧪 API Audit"), a project, and two tasks
with known properties (due dates, flags, notes, defer dates).
**What to look for:** All creation succeeds, IDs and initial values are logged.

#### 06 — Read-Back Verify ◻️
**What it checks:** Full side-by-side comparison of all properties on the test
project's `p.*` vs `p.task.*`, plus all child task properties.
**What to look for:** Confirms findings from Scripts 01-02 on controlled data.
Verifies relationships (project, parent, assignedContainer on tasks).

#### 07 — [WRITE] Modify and Verify ⚠️
**What it checks:** Write proxying between `p.*` and `p.task.*`:
  - Set `p.dueDate` → does `p.task.dueDate` update?
  - Clear `p.dueDate = null` → does `p.task.dueDate` clear?
  - Set `p.task.flagged = true` → does `p.flagged` update?
  - Mark/un-mark project complete → status, active, effectiveActive changes
  - Set/revert `p.status = OnHold` → all side effects
**What to look for:** Bidirectional proxying. Complete status transition behavior.

#### 08 — [WRITE] Cleanup ⚠️
**What it does:** Deletes all entities tagged "🧪 API Audit" (tasks, project, tag).
**What to look for:** Verification that nothing remains after cleanup.

### Part 3: Other Entity Types (READ-ONLY)

#### 09 — Task Field Audit ◻️
**What it checks:** ALL fields on every `flattenedTask`. Distributions for
boolean fields, status, dates, relationships, tags, estimatedMinutes,
repetitionRule, notes.
**What to look for:** Are `added`/`modified` always present? What % of tasks
are in inbox? Status distribution. Any fields that are unexpectedly null.

#### 10 — Tag Audit ◻️
**What it checks:** ALL fields on every `flattenedTag`. Status enum constants
and cross-type comparison with `Project.Status`.
**What to look for:** `Tag.Status` constants (Active, OnHold, Dropped).
Whether `Tag.Status.Active === Project.Status.Active`. `allowsNextAction` distribution.

#### 11 — Folder Audit ◻️
**What it checks:** ALL fields on every `flattenedFolder`. Status enum constants
and cross-type comparison.
**What to look for:** `Folder.Status` constants. Whether folders have the same
status enum as projects/tags or a different set.

#### 12 — Perspective Audit ◻️
**What it checks:** ALL perspectives (built-in and custom). Identifier presence,
name, and probes for any additional accessible properties.
**What to look for:** Which properties exist on perspectives beyond id/name.
Whether built-in perspectives have identifiers.

## Using the Audit Skill

Run `/omnifocus-api-audit` in Claude Code to start a guided audit session.
The skill walks through each script in order, explains what to look for,
and records findings in FINDINGS.md.

## Re-Running

If OmniFocus updates their API, re-run all scripts and compare output
against FINDINGS.md. Any changes indicate API behavior changes that may
require bridge updates.
