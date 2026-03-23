---
name: uat-suite-updater
description: Create or update UAT regression test suites for OmniFocus Operator. Use when the user says "add UAT suite", "new UAT tests", "update UAT tests", "UAT for [feature]", "add tests to [suite]", "create regression tests", or wants to add/expand test coverage for a feature. Also use when the user mentions a verifier agent's output and wants to turn it into a test suite. This skill handles the full workflow — research the feature, gather user's known tests, suggest additional coverage, write the suite file, and register it in the UAT skill.
---

# UAT Suite Updater

Create or update UAT regression test suites for the `uat-regression` skill. This skill captures the workflow for going from "I built a feature" to "I have a comprehensive UAT suite for it."

## When to use

- User wants a **new** test suite for a feature (creates a new file in `tests/`)
- User wants to **expand** an existing suite with more tests
- User has test ideas from a verifier agent and wants them formalized into a suite

## Workflow

### Step 1 — Learn the format

Read the UAT regression skill and at least one existing suite to internalize the conventions:

- `.claude/skills/uat-regression/SKILL.md` — shared conventions, report template, flow
- `.claude/skills/uat-regression/tests/` — pick one or two suites to understand the structure (conventions section, setup with task hierarchy, numbered tests with "PASS if" criteria, report table rows at the end)

Do this silently — no need to narrate what you're reading. The goal is to internalize the patterns so your output matches exactly.

### Step 2 — Research the feature

This is where the real value comes from. Before suggesting tests, deeply understand what was built. Use the Explore agent to investigate:

- **Models**: Pydantic models for the feature — field types, validators, defaults, aliases
- **Service layer**: Every code path that produces warnings, errors, or special behavior. Find exact warning strings and the conditions that trigger them.
- **Bridge layer**: How the feature talks to OmniFocus via OmniJS
- **Existing automated tests**: What's already covered by pytest/vitest — look for edge cases the automated tests exercise (these hint at what UAT should also verify live)
- **No-op detection**: How does the service detect "nothing changed"? What warning does it produce?
- **Status interactions**: What happens when the feature is used on completed/dropped tasks?
- **Validation errors**: What invalid inputs are caught, and are the error messages clean (no pydantic internals)?

**Critical — build a warning/error inventory.** Collect every distinct warning string and every error message the feature can produce. Write them down as a checklist (string + trigger condition). This inventory is the primary input for Step 4 — every string in the list must have at least one test that triggers it.

### Step 3 — Collect the user's known tests

Ask the user:

> "What tests do you already have in mind? If your verifier agent gave you a list, paste it here — I'll use those as the starting point and then suggest additional coverage."

Wait for their response. Parse whatever format they provide (numbered list, bullet points, prose descriptions) and extract the core test cases.

### Step 4 — Suggest additional tests

Based on your research in Step 2 and the user's tests from Step 3, identify gaps. The goal is **maximum coverage** — every code path, every warning string, every error, every edge case that touches live OmniFocus.

#### 4a. Warning/error inventory cross-reference (do this first)

Take the warning/error inventory from Step 2 and check each entry against the user's test list from Step 3. For every warning or error string that has no test triggering it, add one. This is the single most important gap-finding mechanism — warnings are first-class citizens in this codebase (see `docs/architecture.md`, Educational Warnings section), and every one deserves a UAT test.

Pay special attention to **cross-feature interactions**. A feature doesn't exist in isolation — the service layer often has explicit code paths for when features intersect (e.g., lifecycle actions on tasks that happen to have repetition rules, or editing a feature field on completed/dropped tasks). These intersection warnings are easy to miss when thinking about one feature at a time. Check both directions:
- What happens when **this feature's data** is on a task that undergoes **other operations** (lifecycle, move, etc.)?
- What happens when **other operations** interact with a task that **has this feature active**?

Also check: if the codebase distinguishes completed vs dropped (it does — different warning strings, different code paths), make sure BOTH are tested, not just one.

#### 4b. Additional coverage patterns

After the inventory cross-reference, also consider:

- **Type/variant variety**: Are all relevant variants exercised? Don't just test the simplest case.
- **Round-trip verification**: Does every write test verify via `get_task` that the data survived the round-trip through OmniFocus?
- **No-op detection**: Is there a test for sending identical data and getting the "no changes" warning?
- **Error message cleanliness**: Are validation errors tested for clean output (no "type=", "pydantic", "input_value" leaking)?
- **Combo scenarios**: Feature + field edit in same call? Feature no-op + field edit (warning present but field still applied)?
- **Merge/partial update**: If the feature supports partial updates, are same-type merges AND type changes tested?
- **Edge cases from automated tests**: Anything interesting in pytest that should be verified live?

#### 4c. Present and wait

Present the full proposed test list (user's tests + your additions) organized by category. For each addition, briefly explain why it matters — what warning string, code path, or cross-feature interaction it exercises that the user's tests don't cover.

Wait for user sign-off before writing. They may add, remove, or modify tests.

### Step 5 — Write the suite

Create (or update) the test suite file following the exact format of existing suites:

**For a new suite:**
1. Write the suite file to `.claude/skills/uat-regression/tests/<suite-name>.md`
2. Update `.claude/skills/uat-regression/SKILL.md`:
   - Add the suite to the "Available Test Suites" table
   - Add relevant trigger phrases to the `description` field in frontmatter
3. Remind the user to add the new suite to any relevant composite manifests (e.g., `tests/v1.2-combined.md`). Composite suites (files with a `## Composite Suite` heading) are manifests that reference base suites — don't modify them as if they contain tests.

**For updating an existing suite:**
1. Edit the existing file — add new test sections, update the report table rows
2. Update the test count in `SKILL.md` if it changed

**Suite file structure** (match existing suites exactly):

```
# [Suite Name] Test Suite

[One-line description of what's tested]

## Conventions
- Inbox only, 1-item limit, plus any suite-specific rules

## Setup
### Task Hierarchy
[ASCII tree of tasks to create, with notes on which have pre-configured state]
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

Key conventions to follow:
- Every test has explicit "PASS if" criteria
- Error tests say "Run INDIVIDUALLY" (Claude Code cancels sibling calls on error)
- Tests that modify shared state include cleanup steps
- Report table has one row per test (no grouping), with a Description column
- Task names use `T[N]-[ShortName]` format
