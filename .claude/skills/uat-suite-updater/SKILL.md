---
name: uat-suite-updater
description: Create or update UAT regression test suites for OmniFocus Operator. Two-phase workflow — initialization (deep research → seed file) and worker (pick up chunk → execute). Use when the user says "add UAT suite", "new UAT tests", "update UAT tests", "UAT for [feature]", "add tests to [suite]", "create regression tests", "update UAT suites", "uat suite updater", "pick up UAT chunk", "initialize UAT analysis", "UAT gap analysis", "UAT seed", "run UAT chunk", or wants to add/expand test coverage. Also handles ad-hoc single-suite edits.
---

# UAT Suite Updater

Two-phase workflow for updating UAT regression suites after shipping a milestone: **initialize** (deep research → seed file) then **worker** (pick up chunks → execute).

## Mode Detection

Always run this first. Determines which mode to enter.

1. Look for `UAT-SUITE-ANALYSIS.md` at repo root
2. **Not found** → Initialization Mode
3. **Found** → read the `## Progress` section:
   - Unchecked content chunks exist → **Worker Mode**
   - All content chunks checked (only "Delete this file" unchecked) → **Completion Mode**
4. **Override**: if the user names a specific suite + specific change (e.g., "just add X to edit-operations.md"), skip mode detection → **Ad-hoc Override**

## Initialization Mode

Deep research session that produces a seed file coordinating future worker sessions.

**Precondition**: verify this session is running in a git worktree (`git rev-parse --show-toplevel` vs `git worktree list`). Hard stop if not — the seed file and chunk work should happen on a branch, not main.

### Step 1 — Determine milestone scope

- Read `.planning/STATE.md` (frontmatter: `milestone`, `milestone_name`)
- Read `.planning/ROADMAP.md` for phase ranges
- List git tags (`git tag --list`)
- Ask user: **current milestone or archived?**
  - Current → `.planning/ROADMAP.md` + `.planning/phases/`
  - Archived → `.planning/milestones/v{X}-ROADMAP.md` + `v{X}-phases/`
- Determine git diff range from consecutive tags (e.g., `v1.3..v1.3.1`)

### Step 2 — Deep exploration (parallel Explore agents)

Spawn four agents in parallel:

- **Agent A — Source diff**: `git diff {prev}..{tag} --stat`, group changes into themes
- **Agent B — Warning/error inventory**: search service layer for all warning/error strings, record pattern + trigger condition. Focus on NEW strings vs prev tag.
- **Agent C — Existing suite review**: read all suites in `.claude/skills/uat-regression/tests/`, catalog test counts and coverage domains
- **Agent D — Planning context**: read milestone ROADMAP, phase CONTEXT files, understand what was *intended*

### Step 3 — Gap analysis

- Per-suite: what new tests are needed, what assertions are broken (with line references)
- Cross-reference every warning/error string against existing suite coverage
- Determine if new suites or composite restructuring is needed
- **New suite detection**: if the analysis identifies that a new suite file is needed, flag it — this affects how chunks are structured (see Step 4)

### Step 4 — Chunk the work

- Group by suite affinity (shared themes/setup)
- ~15 new tests + ~10 assertion fixes max per chunk
- **New suite registration**: when a chunk creates a NEW suite file, that same chunk MUST include instructions to:
  1. Add the suite to the uat-regression SKILL.md skill table (name, file path, test count, coverage description)
  2. Add the suite to the appropriate combined suite (reads-combined or writes-combined) — or flag if a new combined suite is needed or an existing one should be split
  - Do NOT defer registration to a later chunk — the suite must be discoverable the moment it exists
- If composites need deeper restructuring beyond adding a row, create a separate chunk for that
- Always end with a "Delete this file" checkbox

### Step 5 — Write seed file

- Write `UAT-SUITE-ANALYSIS.md` at repo root following the **Seed File Template** section below
- Commit: `docs: add UAT suite gap analysis for v{version}`
- **No suite editing in this mode** — the seed file IS the deliverable

### Edge case — No gaps found

If research shows suites are already up to date, say so with evidence (which warnings are covered, which assertions are current). Don't produce an empty seed file.

## Worker Mode

Pick up the next chunk from the seed file and execute it.

### Step 1 — Orient

- Read `UAT-SUITE-ANALYSIS.md`, find first unchecked content chunk
- **Version check**: compare version in seed title against `.planning/STATE.md` — warn if mismatched
- Read the uat-regression skill (`.claude/skills/uat-regression/SKILL.md`) silently to internalize conventions
- Read the specific suite files being updated in this chunk

### Step 2 — Targeted research

- Verify warning strings and code paths from the seed against current source
- Don't re-research the whole milestone — the seed has that context
- **Line number drift**: verify line refs against actual files (earlier chunks may have shifted them)

### Step 3 — Execute

- Write/update suite files per chunk instructions
- Match existing suite format exactly (see **Suite Conventions** below)

### Step 4 — Verification

After writing the suite changes, identify assumptions that need live verification (e.g., exact warning text, filter behavior, edge cases).

1. **Present assumptions**: list each assumption with what you'd check and how
2. **Offer self-verification**: ask the user "Want me to run these checks myself against your live OmniFocus?"
3. **If user approves**:
   - Create minimal test tasks in inbox via MCP `add_tasks` (use a `UAT-Verify-` prefix for isolation)
   - Run the MCP tool calls that exercise the assumptions
   - Report results: confirmed or discrepancy found
   - **Clean up**: create `⚠️ DELETE THIS AFTER UAT` in inbox (or reuse if one exists), move all verification tasks under it, tell user to delete it. Same cleanup protocol as the main uat-regression skill.
   - If a discrepancy is found: update the suite file before proceeding to Step 5
4. **If user declines** (or wants to check manually): proceed to Step 5 — list the spot-checks for them as before

**Never run verification autonomously.** Always present assumptions first, always ask permission, always wait for explicit approval before touching OmniFocus.

### Step 5 — Completion protocol

1. **Summarize**: files modified, tests added, assertions fixed. If self-verification ran, include results.
2. **Wait for user sign-off** — user reviews the changes (and verification results if applicable)
3. **On approval**:
   - Commit suite changes: `test(uat): ...`
   - Mark chunk done in separate commit: `chore: mark chunk N complete in UAT suite analysis`
4. **If all content chunks now done**: inform user, suggest triggering this skill again for Completion mode

### Edge case — Concurrent workers

The checkbox mechanism isn't atomic. If a chunk was just checked by another session, move to the next unchecked chunk.

## Completion Mode

All content chunks are done. Archive the seed file and wrap up.

1. Create `.research/uat-suite-seeds/` directory if it doesn't exist
2. Archive: `git mv UAT-SUITE-ANALYSIS.md .research/uat-suite-seeds/v{version}.md`
3. Commit: `chore: archive UAT suite analysis for v{version}`
4. Remind user to merge the worktree branch to main and clean up the worktree

## Ad-hoc Override

If the user names a specific suite and a specific change ("just add X to edit-operations.md"), skip mode detection entirely. Read the target suite, follow uat-regression conventions, make the change. No seed file involved.

## Seed File Template

The seed file must follow this exact structure. See the real `UAT-SUITE-ANALYSIS.md` in the repo for a concrete example.

```markdown
# UAT Suite Analysis — v{version} "{milestone_name}"

## How to Use This File

This file is the output of a research session that analyzed what v{version} changed vs what existing UAT suites cover. It contains everything a fresh agent needs to update the suites without re-doing the research.

**Workflow:** Run `/uat-suite-updater` in a new session. The skill auto-detects this file and enters Worker mode — it will find the next unchecked chunk, do targeted research, execute the changes, and mark the chunk done.

**Important:** The agent still needs to do its own targeted research for the specific suites it's updating — the gap tables below are a starting point, not exhaustive. The agent should verify against actual source code, especially for exact warning strings.

---

## Progress

- [ ] Chunk 1 — {title}
- [ ] Chunk 2 — {title}
- [ ] ...
- [ ] **Delete this file** (all chunks done, everything merged)

---

## Chunks — Task List

### Chunk completion protocol

After finishing the suite edits for a chunk, the agent does NOT commit. Instead:

1. **Present assumptions** — list any assumptions about live behavior that the suite relies on (exact warning text, filter results, edge cases)
2. **Offer self-verification** — "Want me to run these checks myself against your live OmniFocus?" If approved, the agent creates minimal test tasks via MCP, runs the checks, reports results, and cleans up (see Worker Mode Step 4 in the skill for the full protocol). If a discrepancy is found, the agent updates the suite before proceeding.
3. **Summarize changes** — list every file modified, tests added, assertions fixed, and verification results if applicable
4. **Wait for sign-off** — user reviews the changes
5. **On approval**: commit the suite changes, then update the Progress checklist above (check the box)

---

### Chunk 1: {title}

**Suites:** {list of suite files}

**What to do:**
- {detailed instructions per suite — new tests, assertion fixes, with line references}

**Est. scope:** ~N new tests + ~M assertion fixes.

---

{repeat for each chunk}

---

## Reference Material

Everything below is research output — the chunks above reference it.

---

## What v{version} Built

{Themes with bullet points — what changed and why}

---

## Gap Analysis by Suite

### {suite name} ({N} tests) — {NEEDS UPDATES | UP TO DATE}

**New scenarios needed:**

| Category | Test | Why |
|----------|------|-----|
| ... | ... | ... |

**Existing tests that may need assertion updates:**
- {test reference — what changed}

---

{repeat for each suite}

### Suites that DON'T need changes

| Suite | Why it's fine |
|-------|---------------|
| ... | ... |

---

## Warning/Error Inventory

Every new warning/error from v{version} that needs at least one UAT test:

### Errors
| ID | Text Pattern | Covered By |
|----|-------------|------------|
| ... | ... | ... |

### Warnings
| ID | Text Pattern | Covered By |
|----|-------------|------------|
| ... | ... | ... |

---

## Combined Suite Strategy

{If composites need restructuring — rationale and plan. Omit if no changes needed.}

---

## Summary of Work

| Suite | Action | New Tests | Assertion Fixes |
|-------|--------|-----------|-----------------|
| ... | ... | ... | ... |
| **Total** | | **~N** | **~M** |

---

## Final Cleanup

Once ALL chunks are complete and committed, and the user has validated everything:

1. Run `/uat-suite-updater` one more time — it will enter Completion mode and archive this file
2. The worktree branch is now ready for the user to review and merge to main
```

## Suite Conventions

Workers must follow these conventions when writing or updating suite files. Read at least one existing suite in `.claude/skills/uat-regression/tests/` to internalize the patterns.

### Suite file structure

```
# [Suite Name] Test Suite

[One-line description]

## Conventions
- Inbox only, 1-item limit, plus any suite-specific rules

## Setup
### Task Hierarchy
[ASCII tree of tasks to create, with notes on pre-configured state]
### Manual Actions
[What the user needs to do in OmniFocus before tests run]

## Tests
### 1. [Category]
#### Test 1a: [Name]
1. [Step]
2. PASS if: [criteria]

## Report Table Rows
| # | Test | Description | Result |
|---|------|-------------|--------|
```

### Key conventions

- Every test has explicit "PASS if" criteria
- Error tests say "**Run INDIVIDUALLY**" (Claude Code cancels sibling calls on error)
- Tests that modify shared state include cleanup steps
- Report table has one row per test (no grouping), with a Description column
- Task names use `T[N]-[ShortName]` format

### Warning/error inventory cross-reference

The single most important gap-finding mechanism. Take the warning/error inventory and check each entry against existing tests. For every warning or error string with no test triggering it, add one. Warnings are first-class citizens in this codebase — every one deserves a UAT test.

Pay special attention to **cross-feature interactions**:
- What happens when **this feature's data** is on a task that undergoes **other operations** (lifecycle, move, etc.)?
- What happens when **other operations** interact with a task that **has this feature active**?
- If the codebase distinguishes completed vs dropped (it does — different warning strings, different code paths), make sure BOTH are tested.

### Additional coverage patterns

After the inventory cross-reference, also consider:

- **Type/variant variety**: all relevant variants exercised, not just the simplest
- **Round-trip verification**: every write test verifies via `get_task` that data survived the round-trip
- **No-op detection**: sending identical data → "no changes" warning
- **Error message cleanliness**: no "type=", "pydantic", "input_value" leaking
- **Combo scenarios**: feature + field edit in same call; feature no-op + field edit (warning present but field still applied)
- **Merge/partial update**: if partial updates are supported, test same-type merges AND type changes
- **Edge cases from automated tests**: anything in pytest that should be verified live
- **Completed vs dropped**: both states tested, not just one
