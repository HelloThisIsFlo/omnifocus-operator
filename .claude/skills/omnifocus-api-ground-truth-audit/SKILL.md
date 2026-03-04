---
name: omnifocus-api-ground-truth-audit
description: >
  Guide through the OmniFocus API Ground Truth audit. Runs 12 JXA scripts in
  sequence against a live OmniFocus database to empirically verify every field
  on every entity type. Use when starting or resuming the audit session.
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# OmniFocus API Ground Truth — Guided Audit

## Goal & Philosophy

You are guiding the user through a complete empirical audit of the OmniFocus
Automation (JXA) scripting API. This is **the single most important task in the
OmniFocus Operator project** — the bridge layer that everything else is built on.

**Core principles:**
- **Thoroughness is non-negotiable.** Never skip a check to save time. If a
  script causes problems, fix the script — don't reduce coverage.
- **Every finding must be empirical.** Backed by script output, not assumptions
  or documentation. OmniFocus docs are sparse and sometimes wrong.
- **Record everything in FINDINGS.md.** If it's not written down, it didn't happen.

**The output goal:** For every field on every entity type, determine the
canonical JXA access path (e.g., `p.task.added()` not `p.added()`). These
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

**NEVER run JXA scripts via `osascript`, Bash, or any automated method.** The
user must manually paste each script into the OmniFocus Automation Console and
run it themselves. This ensures the human is always in control of what touches
their live database.

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
4. Pick up at the next unfilled script

### For Each Script

**Process scripts strictly one at a time.** Never present the next script until
the current one's output has been analyzed and its findings recorded.

1. **Explain** what the script checks and why it matters (1-2 sentences)
2. **Direct the user to the script file** — give them the file path so they can
   open it and copy the contents. **Do NOT read the script file or paste its
   contents into the conversation.** This wastes context window. The user will
   open the file themselves (in their editor or Finder) and copy-paste into the
   OmniFocus console. If the IDE supports it, open the file in the editor for them.
3. **Instruct** the user: Open OmniFocus, go to **Automation > Show Console**,
   paste the entire script, then press **Cmd+Enter** (or click Run) to run it.
   The output will appear in the console — copy and paste it back here.
4. **Wait** for the user to paste the output
5. **Analyze** the output:
   - Confirm expected results
   - Flag any surprises or UNKNOWN values
   - Note any divergences from preliminary findings
6. **Record** findings in FINDINGS.md (update the relevant section)
7. **Bridge implication:** For each confirmed finding, note the bridge
   implication in the section's "Bridge Action Items" list. Don't wait until
   the end — capture implications as you go.

### Write Scripts (05, 07, 08)

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

## Handling Problems

- **OmniFocus crashes:** The script is too heavy. Reduce string operations,
  increase counter-based processing. The lightweight pattern (counters + only
  report mismatches) has been proven to handle 368+ projects in under 1 second.
- **Unexpected values:** Investigate — don't ignore. This is exactly what we're
  here to find. Log the specific values and add them to FINDINGS.md.
- **Script errors:** Debug the JXA. Common issues: accessing `.name()` on
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

## Endgame

The audit is complete when:
- [ ] All 12 scripts have been run and output analyzed
- [ ] Every section of FINDINGS.md is filled with empirical data
- [ ] All tables have verified values
- [ ] The Bridge Implications section (Section 8) has a concrete action list
- [ ] No "TO BE FILLED" placeholders remain in FINDINGS.md

### Section 8 Workflow

After all 12 scripts are analyzed, review every "Bridge Action Items" subsection
across Sections 1-7. Consolidate into Section 8 by category: Critical Fixes,
Improvements, Model Changes, Enum Changes. Section 8 is the final deliverable —
a developer reading only Section 8 should know every change needed.

**Category definitions:**
- **Critical Fixes**: Correctness bugs — the bridge currently returns wrong
  data (e.g., status always null, reading from wrong object path)
- **Improvements**: Data quality — the bridge works but could return richer
  or more accurate data (e.g., new fields to expose)
- **Model Changes**: Python model additions/removals — new fields, renamed
  fields, type changes
- **Enum Changes**: EntityStatus enum modifications — new values, removed
  values, mapping changes
