# OmniFocus API Ground Truth

Empirical audit of the OmniFocus Automation (Omni Automation / OmniJS) scripting API.
Every finding is verified by running scripts against a live OmniFocus database.

## Why This Exists

The OmniFocus Operator bridge translates Omni Automation objects into Python models. This
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

> Parts 1-3 are the core audit (discovery, write verification, entity types).
> Part 4 contains supplementary deep dives into specific areas of interest.

### Part 1: Project Discovery (READ-ONLY)

#### 01 — Project vs Root Task Scan ◻️
**What it checks:** Every field on `p.*` vs `p.task.*` across all projects.
Verifies task-only fields (added, modified, active, effectiveActive), scans
project-specific fields (containsSingletonActions, lastReviewDate, nextReviewDate,
reviewInterval, nextTask, folder, repetitionRule), tracks effectiveCompletionDate
behavior, measures status distributions, checks all shared fields for divergence,
tags divergence (p vs p.task), and verifies id matching.
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
boolean fields, status, dates, relationships, tags, estimatedMinutes (3 categories),
repetitionRule (deep inspection of sub-properties for first 5), notes, name.
Probes collections (linkedFileURLs, notifications, attachments). Tests accessor
equivalence (project() vs containingProject, parentTask() vs parent).
**What to look for:** Are `added`/`modified` always present? What % of tasks
are in inbox? Status distribution. RepetitionRule sub-field types. Collection
existence. Whether accessor pairs return the same objects.
**Critical cross-reference:** The script outputs a Status × active × effectiveActive
cross-tabulation. This reveals whether `effectiveActive` can serve as a shortcut
for Milestone 2's "Overdue masks Blocked" recovery logic — e.g., if Overdue tasks
with `effectiveActive=false` are always in inactive containers, the service layer
can skip manual blocking-condition checks for those cases.

#### 10 — Tag Audit ◻️
**What it checks:** ALL fields on every `flattenedTag`. Status enum constants
and cross-type comparison with `Project.Status`. Tag name uniqueness check
(important because the bridge serializes by name, not ID).
**What to look for:** `Tag.Status` constants (Active, OnHold, Dropped).
Whether `Tag.Status.Active === Project.Status.Active`. `allowsNextAction` distribution.
Whether any tag names are duplicated across the hierarchy.

#### 11 — Folder Audit ◻️
**What it checks:** ALL fields on every `flattenedFolder`. Status enum constants
and cross-type comparison.
**What to look for:** `Folder.Status` constants. Whether folders have the same
status enum as projects/tags or a different set.

#### 12 — Perspective Audit ◻️
**What it checks:** ALL perspectives via both access paths (`Perspective.all` and
`doc.perspectives()`). Compares counts and uses the more complete set. Tests
identifier presence, name, and probes for any additional accessible properties.
**What to look for:** Whether the two access paths return different counts.
Which properties exist on perspectives beyond id/name. Whether built-in
perspectives have identifiers.

### Part 4: Supplementary Audits (READ-ONLY unless noted)

#### 13 — RepetitionRule Full Enumeration ◻️
**What it checks:** ALL tasks with repetitionRule — enumerates all distinct RepetitionScheduleType values (probes beyond the 2 known: Regularly, FromCompletion), all RRULE FREQ patterns, and unique ruleStrings.
**What to look for:** Are there more than 2 scheduleType constants? What FREQ patterns exist (WEEKLY, MONTHLY, DAILY, etc.)? Any UNKNOWN values?

#### 14 — Tag-Based Blocking Investigation ◻️
**What it checks:** Whether tasks assigned to OnHold tags have different taskStatus distributions. Finds all OnHold tags, then all tasks with those tags, and compares status distributions.
**What to look for:** If Available/Next/Overdue counts are 0 for OnHold-tagged tasks, then OnHold tags DO cause blocking. If > 0, they don't affect taskStatus.

#### 15 — Tag Hierarchy Inheritance ◻️
**What it checks:** Whether tag status (OnHold/Dropped) propagates to child tags through active/effectiveActive, similar to folder→project inheritance.
**What to look for:** Do Active child tags inside OnHold parents get effectiveActive=false?

#### 16 — Sequential Project Deep Dive ◻️
**What it checks:** Task ordering in sequential projects. Verifies first-incomplete=Next pattern. Searches for "Overdue masks Blocked" instances: tasks with past due dates that aren't the first incomplete (sequentially blocked but showing Overdue).
**What to look for:** Any Overdue-masks-Blocked instances. Sequential action groups count.

#### 17 — Perspective Mismatch Investigation ◻️
**What it checks:** Why Perspective.all count doesn't match BuiltIn.all + Custom.all. Compares all three collections by ID to find the discrepancy.
**What to look for:** Which perspective is in one collection but not the other.

#### 18 — Full Collection Scan ◻️
**What it checks:** ALL tasks (not just first 500 from Script 09) for linkedFileURLs, notifications, and attachments. Reports any non-empty collections with samples.
**What to look for:** Whether any tasks in the full database have populated collections.

#### 19 — completedByChildren Analysis ◻️
**What it checks:** What completedByChildren actually controls. Finds parent tasks where all children are complete and checks if the parent auto-completed.
**What to look for:** If completedByChildren=true + all children complete → parent completed, then it controls auto-completion.

#### 20 — Inbox Task Audit ◻️
**What it checks:** Detailed analysis of inbox tasks (inInbox=true). Status distribution, relationships, booleans, dates, tags.
**What to look for:** How inbox tasks differ from project tasks. Relationship fields (all null?). Status patterns.

#### 21 — [WRITE] Task-Level Write Operations ⚠️
**What it does:** Tests task-level writes: complete/un-complete, defer date changes, making a task overdue then deferred, drop/un-drop, flag/unflag. Self-cleaning.
**What to look for:** Does setting a future deferDate change Overdue→Blocked? Can you un-drop a task? Status transitions at task level vs project level.

#### 22 — Application & Settings Probe ◻️
**What it checks:** Probes app, document, Settings, and Preferences objects for accessible configuration. Searches for DueSoon threshold, timezone settings, and other useful globals.
**What to look for:** Can the DueSoon threshold be read from the API? Any useful app-level configuration?

#### 23 — Estimated Minutes Distribution ◻️
**What it checks:** Statistical distribution of estimatedMinutes across all tasks. Min, max, mean, median, buckets, most common values.
**What to look for:** Range of values, common estimate sizes, whether zero is ever used.

#### 24 — Date Inheritance Patterns ◻️
**What it checks:** How effective* dates are inherited. For tasks with effectiveDueDate but no direct dueDate, traces the source (project, parent task, or unknown). Same for defer dates.
**What to look for:** Is inheritance fully traceable to project or parent task? Any unknown sources?

## Using the Audit Skill

Run `/omnifocus-api-ground-truth-audit` in Claude Code to start a guided audit session.
The skill walks through each script in order, explains what to look for,
and records findings in FINDINGS.md.

## Re-Running

If OmniFocus updates their API, re-run all scripts and compare output
against FINDINGS.md. Any changes indicate API behavior changes that may
require bridge updates.
