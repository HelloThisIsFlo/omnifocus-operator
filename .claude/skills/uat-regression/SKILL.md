---
name: uat-regression
description: Run UAT regression tests for OmniFocus Operator MCP tools against the live OmniFocus database. Choose from test suites covering edit operations, tag operations, move operations, lifecycle, and more. Trigger when the user says "run UAT", "UAT regression", "regression test", "test edits", "test tags", "test tag operations", "test moves", "test movement", "test lifecycle", "test complete/drop", "test reads", "test filters", "test add_tasks", "run edit tests", or wants to verify tool behavior after code changes. This skill requires the omnifocus-operator MCP server to be running.
---

# UAT Regression

Run UAT regression tests for OmniFocus Operator MCP tools against live OmniFocus. Tests are organized into domain-specific suites that run independently.

## Available Test Suites

| Suite | File | Tests | Covers |
|-------|------|------:|--------|
| Edit Operations | `tests/edit-operations.md` | 23 | Field editing, patch semantics, no-ops, status warnings, errors, combos |
| Tag Operations | `tests/tag-operations.md` | 15 | Tag add/remove/replace, ambiguity, no-ops, errors |
| Move Operations | `tests/move-operations.md` | 16 | All 5 move modes, cross-level, circular refs, completed/dropped movement |
| Lifecycle | `tests/lifecycle.md` | 10 | Complete, drop, cross-state, repeating tasks, validation |

## Flow

1. **Present the suites** — show the table above and ask which suite to run
2. **Read the selected suite** — load the test file from the `tests/` directory (relative to this skill file)
3. **Execute three phases:**
   - **Phase 1 — Interactive setup**: Create test tasks as described in the suite's Setup section. Ask the user for any manual actions. Wait for confirmation.
   - **Phase 2 — Autonomous testing**: Run all tests in the suite, collect results (PASS/FAIL/SKIP). After a test that modifies state, clean up if the task is reused later (e.g., rename back, remove tags).
   - **Phase 3 — Report**: Generate the report using the template below.
4. **Cleanup reminder** (if applicable): If the suite created test tasks, remind the user to delete the test parent and its children in OmniFocus when ready (`delete_tasks` is not implemented yet).

## Role: Black-Box Tester

You are an external QA tester. You do not know the implementation. You interact with OmniFocus Operator exclusively through its MCP tools and report what you observe.

**What this means in practice:**

- **Do NOT read source code.** Never open `.py`, `.js`, or test files to understand how something works. You don't need to know why a test fails — only that it failed and what you observed.
- **Do NOT debug.** If a test fails, record the failure (what happened vs what was expected) and move on to the next test. Do not investigate root causes, read stack traces beyond the error message, or try to figure out what went wrong in the code.
- **Do NOT fix anything.** If you notice a bug, that's a test result, not a task. Report it and continue.
- **Stop early if fundamentally broken.** If setup fails or the first several tests fail catastrophically (e.g., the MCP server is down, the tool is returning errors on basic operations), mark remaining tests as SKIP with a reason like "blocked by setup failure" and proceed directly to the report. There is no value in running 20 more tests against a broken foundation.
- **Keep the session clean.** This session is purely about testing and reporting. No code exploration, no architecture discussion, no improvement suggestions beyond what the report template asks for.

The value of UAT comes from this separation. If you understand the implementation, you will unconsciously interpret ambiguous behavior charitably and work around bugs instead of surfacing them. Stay outside the box.

## Shared Conventions

These apply to ALL test suites:

- **No parallel error calls.** Claude Code cancels all sibling calls when one errors. Never mix calls that might fail (nonexistent IDs, validation errors) with calls that must succeed. Run error-expecting calls individually.

Each suite lists its own domain-specific conventions in its `## Conventions` section.

## Report Template

After all tests complete, output TWO clearly separated sections. Each section MUST be inside a markdown code block (triple backticks) so the user can copy-paste them independently.

### Section 1: UAT Report (inside a code block)

The table must include a "Description" column. Every test gets its own row (no grouping). Use the "Report Table Rows" from the test suite file and fill in the Result column.

Title format: `## UAT Regression Results — [Suite Name]`

Include after the table:
- **Total**: X PASS, Y FAIL, Z SKIP
- **Failures**: What happened vs expected, for each failure
- **Skipped Tests**: Why they were skipped
- **Observations**: Warning tone, error message quality, anything noteworthy. If any warnings looked problematic (unclear, misleading, missing info), flag them here — the full inventory lives in the User Report below.
- **Cleanup**: "Please manually delete [parent task name] and all its children in OmniFocus when ready."

### Separator

After the UAT code block, output this visual separator (NOT inside any code block):

```
⠀
⠀
⠀
═══════════════════════════════════════════════════════════════
═══════════════════════════════════════════════════════════════
⠀
  ▲ UAT REPORT (above) — copy-paste to share with reviewer
⠀
  ▼ USER REPORT (below) — warnings inventory + improvement notes
⠀
═══════════════════════════════════════════════════════════════
═══════════════════════════════════════════════════════════════
⠀
⠀
⠀
```

### Section 2: User Report (NOT in a code block — render as normal markdown)

```
## User Report

### Warnings Observed

Every distinct warning encountered during this test suite. Always populated — even when all warnings look correct.

The "Agent Interpretation" column is key: read the warning with shoshin (beginner's mind) — pretend you know nothing about the implementation or the test that triggered it. What would an agent understand it to mean? What action would it take next? If the interpretation doesn't match reality, that's a signal the warning text needs improvement. Be honest — if the warning is unclear, say so.

| Warning Text | Triggered By | Looks Correct? | Agent Interpretation | Notes |
|---|---|---|---|---|

### Tool / Server Improvements
- (Bugs, error message quality, API design, missing validations)

### Skill / Test Coverage Improvements
- (Missing test cases, edge cases not covered, skill clarity)

### Other Observations
- (UX patterns, anything else noteworthy)
```

The **Warnings Observed** section is always populated (it's an inventory, not just problems). The other subsections only include actually-observed items — if a section is empty, omit it.

**IMPORTANT:** Do NOT repeat bugs already captured in the Failures section. The subsections below Warnings Observed are for observations beyond what the test suite covers — wording improvements, UX polish, missing coverage, architectural suggestions.
