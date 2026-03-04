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

## Workflow

### Starting the Audit

1. Read the README to refresh on what each script checks
2. Check FINDINGS.md for any already-completed sections (if resuming)
3. Determine which script to run next

### For Each Script

1. **Explain** what the script checks and why it matters (1-2 sentences)
2. **Read** the script file and present it to the user
3. **Instruct** the user to paste it into OmniFocus > Automation > Show Console
4. **Wait** for the user to paste the output
5. **Analyze** the output:
   - Confirm expected results
   - Flag any surprises or UNKNOWN values
   - Note any divergences from preliminary findings
6. **Record** findings in FINDINGS.md (update the relevant section)

### Write Scripts (05, 07, 08)

Before running scripts 05, 07, or 08, **warn clearly**:

> ⚠️ This script WRITES to your OmniFocus database. It will create/modify/delete
> test entities tagged "🧪 API Audit". This is safe and reversible — Script 08
> cleans everything up. Proceed?

### Script Sequence

**Part 1 — Project Discovery (READ-ONLY)**
- Script 01: Project vs Root Task Full Scan
- Script 02: Project Effective Fields
- Script 03: Status Enum Discovery
- Script 04: Project Status Cross-Reference

**Part 2 — Write-Side Verification**
- Script 05: [WRITE] Create Test Data
- Script 06: Read-Back Verify
- Script 07: [WRITE] Modify and Verify
- Script 08: [WRITE] Cleanup

**Part 3 — Other Entity Types (READ-ONLY)**
- Script 09: Task Field Audit
- Script 10: Tag Audit
- Script 11: Folder Audit
- Script 12: Perspective Audit

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
- Which properties exist on Perspective beyond id/name
- Built-in vs custom perspective distinction

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

## Recording Findings

After analyzing each script's output:

1. Open FINDINGS.md
2. Find the relevant section
3. Replace "TO BE FILLED" with actual findings
4. Include specific numbers from the output
5. Fill in the tables with verified data
6. Add any action items discovered

## Endgame

The audit is complete when:
- [ ] All 12 scripts have been run and output analyzed
- [ ] Every section of FINDINGS.md is filled with empirical data
- [ ] All tables have verified values
- [ ] The Bridge Implications section (Section 8) has a concrete action list
- [ ] No "TO BE FILLED" placeholders remain in FINDINGS.md
