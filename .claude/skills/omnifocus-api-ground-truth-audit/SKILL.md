---
name: omnifocus-api-ground-truth-audit
description: >
  Guide through the OmniFocus API Ground Truth audit. Runs 24 Omni Automation
  scripts in sequence against a live OmniFocus database to empirically verify
  every field on every entity type. Use when starting or resuming the audit session.
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# OmniFocus API Ground Truth — Guided Audit

## Goal & Philosophy

You are guiding the user through a complete empirical audit of the OmniFocus
Automation (Omni Automation / OmniJS) scripting API. This is **the single most important task in the
OmniFocus Operator project** — the bridge layer that everything else is built on.

**Core principles:**
- **Thoroughness is non-negotiable.** Never skip a check to save time. If a
  script causes problems, fix the script — don't reduce coverage.
- **Every finding must be empirical.** Backed by script output, not assumptions
  or documentation. OmniFocus docs are sparse and sometimes wrong.
- **Record everything in FINDINGS.md.** If it's not written down, it didn't happen.
- **The user controls the pace.** The user has 10+ years of OmniFocus
  experience. They know what's worth exploring. NEVER suggest moving to the
  next script, NEVER say "want to move on?", NEVER frame discussion as a
  delay before the "real work" of recording and proceeding. The scripts are
  tools that feed understanding — understanding is the goal, not completing
  all 24 scripts in minimum time. If a finding sparks a design question,
  explore it fully. If the user wants to dig into edge cases, dig in. The
  user will say when they're ready for the next script. Until then, stay in
  the current topic.
- **Every field is a first-class citizen.** Never deprioritize a field or
  feature because it appears infrequently in the database. A field used by 1
  task deserves the same care and correct handling as one used by 2822. Do not
  say "rare — consider deferring" or "fun curiosity." Frequency in one
  database says nothing about importance.

**The output goal:** For every field on every entity type, determine the
canonical Omni Automation access path (e.g., `p.task.added()` not `p.added()`). These
scripts define the best way to access each field; the bridge will be updated
afterwards to match. Every finding should point toward a concrete bridge change.

## Context

The audit scripts live in:
```
.research/Deep Dives/OmniFocus API Ground Truth/scripts/
```

Findings are recorded in:
```
.research/Deep Dives/OmniFocus API Ground Truth/FINDINGS.md
```

The README explains what each script checks:
```
.research/Deep Dives/OmniFocus API Ground Truth/README.md
```

## Key Background

- OmniFocus projects wrap a "root task" internally (`p.task()`). Some properties
  only exist on the root task (added, modified, active, effectiveActive), not on
  the project object. The bridge MUST read from `p.task.*` for these.
- OmniFocus enum objects are **opaque** — `.name`, `String()`, `.toString()` all
  return `undefined`. Only `===` comparison against known constants works.
- The current bridge has silent bugs: `status` is always null on projects/tags/
  folders because it uses the broken `.name` pattern.
- `Project.Status` has 4 values (Active, OnHold, Done, Dropped) but our
  `EntityStatus` enum only has 3 (missing OnHold).

## Safety

**NEVER run scripts via `osascript`, Bash, or any automated method.** The user
must manually paste each script into the OmniFocus Automation Console and run it
themselves. This ensures the human is always in control of what touches their
live database.

## Workflow

### Starting the Audit

1. Read the README to refresh on what each script checks
2. Check FINDINGS.md for any already-completed sections (if resuming)
3. Determine which script to run next

### Session Start

Before running any scripts:
1. Ask the user for their OmniFocus version (OmniFocus > About OmniFocus)
2. Fill in the "Audit date" and "OmniFocus version" fields in FINDINGS.md
3. Database size (projects, tasks, tags, folders) will be filled as scripts
   report entity counts

### Resuming a Session
1. Read FINDINGS.md — sections already filled indicate completed scripts
2. Skip the version/date prompt if already filled
3. If FINDINGS Section 7 (Write Behavior) is empty but read-side sections have
   data, check whether test data from Script 05 still exists (ask user). If so,
   run Script 08 first to clean up. Then clear any Script 06 findings (they
   reference old test entity IDs) and re-run the full write sequence (Scripts
   05→06→07→08) from scratch.
4. **Tell the user where things stand** — summarize what's been completed and
   what's next. Then **ask what they'd like to do.** They might want to:
   - Continue at the next unfilled script
   - Review and discuss already-completed findings (e.g., "let's talk through
     the Section 3 task findings before continuing")
   - Revisit a specific topic that came up in a previous session
   - Explore a design question before running more scripts
   Follow their lead. "Already filled" sections are not closed — the user may
   want to discuss, question, or deepen their understanding of any finding at
   any time.

### For Each Script

**Process scripts strictly one at a time.** Never present the next script until
the current one's output has been analyzed and its findings recorded.

1. **Explain** what the script checks and why it matters (1-2 sentences)
2. **Direct the user to the script file** — give them the file path so they can
   open it and copy the contents. **Do NOT read the script file or paste its
   contents into the conversation when presenting a new script to run.** This
   wastes context window. The user will open the file themselves (in their
   editor or Finder) and copy-paste into the OmniFocus console. Open the file
   in Cursor for the user using `open -a "Cursor" "<file-path>"` (NOT
   `cursor <path>` — that breaks on paths with spaces and opens an empty file
   instead).
   (Exception: if debugging a script error, reviewing what a script checks
   during discussion, or comparing script logic against findings, reading the
   script source is fine — use judgment.)
3. **Instruct** the user: Open OmniFocus, go to **Automation > Show Console**,
   paste the entire script, then press **Cmd+Enter** (or click Run) to run it.
   The output will appear in the console — copy and paste it back here.
4. **Wait** for the user to paste the output
5. **Analyze and discuss** the output with the user. This is the heart of the
   audit — not a step to rush through on the way to recording findings:
   - **Explain what the results mean** in plain terms — what does this tell us
     about how OmniFocus works internally?
   - **Connect to the bigger picture** — how does this relate to earlier
     findings? Does it confirm or contradict what we expected? Does it change
     how we think about the bridge design?
   - **Highlight surprises** — anything unexpected deserves a thoughtful
     explanation, not just a bullet point
   - **Answer the user's questions fully.** If a finding sparks a design
     question (e.g., "should we parse RRULE or store raw?"), explore it
     right there. Don't defer it. Don't say "we'll decide later." Think it
     through together. The user may want to go deep on one aspect — follow
     their lead.
   - **NEVER end your message by suggesting the next script.** No "ready for
     Script 14?", no "want to move on?", no "shall we continue?", no "any
     questions before we continue?". Just respond to what the user said or
     present your analysis. They will tell you when they're done.
     (Note: this rule applies to mid-discussion flow. During the resume
     status summary, it's fine to list "continue at Script N" as one of
     several options — that's presenting status, not nudging.)
**Recording:** At any point during or after discussion, when findings are
clear enough, update the relevant FINDINGS.md section and its Bridge Action
Items. There is no fixed moment for this — it can happen mid-conversation,
after a design tangent, or when the user signals they're satisfied with the
current topic. If discussion reveals new nuances after recording, update the
recording.

### Write Scripts (05, 07, 08, 21)

Before running scripts 05, 07, or 08, **warn clearly**:

> ⚠️ This script WRITES to your OmniFocus database. It will create/modify/delete
> test entities tagged "🧪 API Audit". This is safe and reversible — Script 08
> cleans everything up. Proceed?

**Interrupted session:** If the session is interrupted between Scripts 05 and 08,
test entities tagged "🧪 API Audit" remain in the user's database. They can paste
Script 08 at any time to clean up. If Script 05 needs to be re-run, always run
Script 08 first to avoid duplicate test data.

### Script Sequence

**Part 1 — Project Discovery (READ-ONLY)**
- Script 01: Project vs Root Task Full Scan
- Script 02: Project Effective Fields
- Script 03: Status Enum Discovery
- Script 04: Project Status Cross-Reference

**Part 2 — Write-Side Verification**
- Script 05: [WRITE] Create Test Data
- Script 06: Read-Back Verify (READ-ONLY, but requires Script 05 data)
- Script 07: [WRITE] Modify and Verify
- Script 08: [WRITE] Cleanup

**Part 3 — Other Entity Types (READ-ONLY)**
- Script 09: Task Field Audit
- Script 10: Tag Audit
- Script 11: Folder Audit
- Script 12: Perspective Audit

**Part 4 — Supplementary Audits (READ-ONLY unless noted)**
- Script 13: RepetitionRule Full Enumeration
- Script 14: Tag-Based Blocking Investigation
- Script 15: Tag Hierarchy Inheritance
- Script 16: Sequential Project Deep Dive
- Script 17: Perspective Mismatch Investigation
- Script 18: Full Collection Scan
- Script 19: completedByChildren Analysis
- Script 20: Inbox Task Audit
- Script 21: [WRITE] Task-Level Write Operations
- Script 22: Application & Settings Probe
- Script 23: Estimated Minutes Distribution
- Script 24: Date Inheritance Patterns

### Script → FINDINGS.md Mapping

| Script(s) | FINDINGS Section | Notes |
|-----------|------------------|-------|
| 03        | 1. Enum System   | Fill completely from Script 03 output |
| 01, 02    | 2. Project Type  | Start with 01, refine with 02 |
| 04        | 2. Project Type (Status Cross-Reference) | Add the mapping table |
| 06, 07    | 2. Project Type + 7. Write Behavior | 06 confirms, 07 adds write data |
| 09        | 3. Task Type     | Fill completely from Script 09 output |
| 10        | 4. Tag Type      | Fill completely from Script 10 output |
| 11        | 5. Folder Type   | Fill completely from Script 11 output |
| 12        | 6. Perspective   | Fill completely from Script 12 output |
| 05-08     | 7. Write Behavior | Accumulated across the write sequence |
| All       | 8. Bridge Implications | Synthesize at the very end |
| 13        | 9.1 RepetitionRule | Refines Section 3 repetitionRule data |
| 14        | 9.2 Tag-Based Blocking | Critical for M2 — does OnHold tag block tasks? |
| 15        | 9.3 Tag Hierarchy | Refines Section 4 inheritance data |
| 16        | 9.4 Sequential Projects | Empirical "Overdue masks Blocked" evidence |
| 17        | 9.5 Perspective Mismatch | Resolves Section 6 count discrepancy |
| 18        | 9.6 Collections Full Scan | Extends Section 3 collection data |
| 19        | 9.7 completedByChildren | Clarifies semantics |
| 20        | 9.8 Inbox Tasks | Inbox-specific behavior |
| 21        | 9.9 Task-Level Writes | Extends Section 7 with task writes |
| 22        | 9.10 App Settings | API-accessible configuration |
| 23        | 9.11 Estimated Minutes | Distribution data |
| 24        | 9.12 Date Inheritance | Inheritance tracing |

## What to Verify (Per Script)

### Script 01
- ✅ Zero divergences on all shared fields (name, note, dates, flags, etc.)
- ✅ Task-only fields (added, modified, active, effectiveActive) are undefined on p.*, always present on p.task.*
- ✅ `p.id() === p.task.id()` for all projects
- ✅ `inInbox` is always false for project root tasks
- Note the active/effectiveActive divergence count

### Script 02
- Determine which effective* fields are broken on p.* (return undefined)
- Is effectiveCompletionDate the ONLY broken one, or are others broken too?
- effectiveFlagged is boolean not date — special handling

### Script 03
- Complete list of constants per entity type
- Cross-type compatibility: can one switch function work for all?
- Any UNKNOWN values = potential missing constants
- Note: Script 03 samples only the first 500 tasks for speed. Script 09
  provides the definitive full-database task status distribution.

### Script 04
- Full mapping table: Project.Status → task.active, task.effectiveActive, task.Status
- OnHold behavior is especially important (new discovery)

### Scripts 05-08
- Write proxying: does setting p.dueDate also set p.task.dueDate?
- Bidirectional: does setting p.task.flagged also set p.flagged?
- Status transitions: what happens to active/effectiveActive when completing?
- Clean creation and deletion behavior

### Script 09
- Are added/modified always present on tasks? (Expected: yes)
- inInbox distribution (inbox tasks have no project)
- Status distribution across all 7 Task.Status values
- Relationship patterns (project null = inbox, parentTask null = top-level)
- **Critical: Status × active × effectiveActive cross-reference** — does
  `effectiveActive=false` reliably indicate "blocked by container" for Overdue
  tasks? Could simplify Milestone 2's recovery logic. Pay close attention to
  combinations like Overdue+active=true+effActive=false and Blocked+active=true.

### Scripts 10-11
- Tag.Status and Folder.Status constant discovery
- Cross-type comparison results
- Whether tags/folders have all the same fields as expected

### Script 12
- Two access paths: do `Perspective.all` and `doc.perspectives()` return the same count?
- Complete list of built-in perspective names
- Custom perspective names and identifiers
- Standard property probes: which of added/modified/active/status/etc. exist on perspectives?
- Perspective-specific property probes: which of color/iconName/filter/sorting/etc. exist?
- Classification: built-in = no identifier, custom = has identifier

### Script 13
- How many distinct scheduleType values exist? (Expected at least 2: Regularly, FromCompletion)
- Any UNKNOWN scheduleType values?
- RRULE FREQ patterns (DAILY, WEEKLY, MONTHLY, etc.)

### Script 14
- Are Available/Next/Overdue tasks found with OnHold tags? If yes → tags don't block. If no → tags DO block.
- This directly impacts Milestone 2 recovery logic

### Script 16
- Any "Overdue masks Blocked" instances? (Overdue tasks that are NOT the first incomplete in a sequential project)
- How many sequential action groups exist?

### Script 21
Before running: warn about writes (same as Scripts 05/07/08).
- Does setting future deferDate on a task change status to Blocked?
- Does clearing deferDate revert status?
- Does setting past dueDate make task Overdue?
- Can you un-drop a task with markIncomplete()?
- Does drop() set active=false on a task?

### Script 22
- Can the DueSoon threshold be read via Preferences.read() or Settings?
- Any useful app-level configuration accessible?

## Handling Problems

- **OmniFocus crashes:** The script is too heavy. Reduce string operations,
  increase counter-based processing. The lightweight pattern (counters + only
  report mismatches) has been proven to handle 368+ projects in under 1 second.
- **Unexpected values:** Investigate — don't ignore. This is exactly what we're
  here to find. Log the specific values and add them to FINDINGS.md.
- **Script errors:** Debug the Omni Automation script. Common issues: accessing `.name()` on
  opaque enums, calling methods without `()`, property name typos.
- **UNKNOWN status values:** The entity has a status value not covered by our
  switch. Add new constants to probe.
- **Truncated output:** If output is very long and the user can only paste a
  portion, ask for the missing sections by name (e.g., "Can you paste the
  '--- Status Distribution ---' section?").

## Recording Findings

After analyzing each script's output:

1. Open FINDINGS.md
2. Find the relevant section (use the Script→FINDINGS mapping table)
3. Replace "TO BE FILLED" with actual findings using the formats below
4. Add bridge action items as you go (don't wait until the end)

**Tables:** Fill every cell. Use "Yes"/"No" for boolean columns. Use actual
counts for numeric columns. Never leave a cell empty.

**Prose sections:** Write 2-4 sentences summarizing the empirical observation.
Always cite specific numbers (e.g., "345/368 projects had…"). Note any
surprises or deviations from expectations.

**Bridge Action Items:** Convert each finding that implies a bridge change into
a concrete, actionable checkbox. Format: `- [ ] [verb] [what] — [why]`.
Example: `- [ ] Read added/modified from p.task.* not p.* — undefined on project object`

## Revisiting Existing Findings

FINDINGS.md is institutional memory. Treat existing content as a colleague's
notes from a previous session. Read it, respect it, build on it.

**When re-running a script against an already-filled section:**
- Compare new output against existing FINDINGS.md content
- If results match → confirm: "This matches what we found earlier — [summary]"
- If results differ → flag the discrepancy to the user: "FINDINGS.md says X,
  but this run shows Y. This could be because [possible reasons]. What do you
  think?"
- Never silently overwrite. Never silently ignore differences.

**When updating an existing section:**
- Merge new insights with existing content — don't replace wholesale
- If the current conversation contradicts an existing finding or design note,
  raise it: "The existing findings say [X], but in our discussion we're
  leaning toward [Y]. Should we update?"
- Preserve bridge action items and design decisions from earlier sessions
  unless the user explicitly decides to change them

**Source of truth hierarchy:**
- Current conversation > FINDINGS.md for interpretation and decisions
- But FINDINGS.md may contain edge cases or insights the current conversation
  hasn't touched — don't discard them
- When in doubt, ask the user

## Endgame

The audit is complete when:
- [ ] All 24 scripts have been run and output analyzed
- [ ] Sections 1-8 filled from core scripts (1-12)
- [ ] Section 9 filled from supplementary scripts (13-24)
- [ ] Every section of FINDINGS.md is filled with empirical data
- [ ] All tables have verified values
- [ ] The Bridge Implications section (Section 8) has a concrete action list
- [ ] No "TO BE FILLED" placeholders remain in FINDINGS.md

### Section 8 Workflow

After all 24 scripts are analyzed, review every "Bridge Action Items" subsection
across Sections 1-7 and all Section 9 subsections. Consolidate into Section 8 by
category: Critical Fixes, Improvements, Model Changes, Enum Changes. Section 8
is the final deliverable — a developer reading only Section 8 should know every
change needed.

**Category definitions:**
- **Critical Fixes**: Correctness bugs — the bridge currently returns wrong
  data (e.g., status always null, reading from wrong object path)
- **Improvements**: Data quality — the bridge works but could return richer
  or more accurate data (e.g., new fields to expose)
- **Model Changes**: Python model additions/removals — new fields, renamed
  fields, type changes
- **Enum Changes**: EntityStatus enum modifications — new values, removed
  values, mapping changes
