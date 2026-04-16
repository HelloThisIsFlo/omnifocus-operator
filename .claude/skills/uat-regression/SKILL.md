---
name: uat-regression
description: Run UAT regression tests for OmniFocus Operator MCP tools against the live OmniFocus database. Choose from test suites covering edit operations, tag operations, move operations, lifecycle, inheritance, repetition rules, date filtering, list/filter tools, validation/error formatting, and more. Trigger when the user says "run UAT", "UAT regression", "regression test", "test edits", "test tags", "test tag operations", "test moves", "test movement", "test lifecycle", "test complete/drop", "test reads", "test filters", "test add_tasks", "run edit tests", "test inheritance", "test effective fields", "effective field inheritance", "test repetition", "test repetition rules", "test repeating tasks", "test rrule", "test list tasks", "test list_tasks", "test filtering", "test search", "test pagination", "test resolution", "test availability", "test list projects", "test list_projects", "test folders", "test folder filter", "test review due", "test review_due_within", "test list tags", "test list_tags", "test list folders", "test list_folders", "test list perspectives", "test list_perspectives", "test perspectives", "test simple list", "test validation", "test errors", "test error formatting", "test validation errors", "test middleware", "test clean errors", "test list tools", "test date filtering", "test date filters", "test due date", "test overdue", "test due soon", "test lifecycle dates", "test defer date", "test shorthand periods", "run writes", "run reads", "write regression", "read regression", "full regression", "test batch", "test batch processing", "test batch operations", "test mega batch", "run batch test", or wants to verify tool behavior after code changes. This skill requires the omnifocus-operator MCP server to be running.
---

# UAT Regression

**⚠️ This skill operates against the user's real OmniFocus database.** It must ONLY be run when explicitly requested by the user. An agent must never autonomously decide to invoke this skill (e.g., after code changes, as part of a verification step, etc.).

Run UAT regression tests for OmniFocus Operator MCP tools against live OmniFocus. Tests are organized into domain-specific suites that run independently.

## Available Test Suites

| Suite | File | Tests | Covers |
|-------|------|------:|--------|
| **Writes Combined** *(composite)* | `tests/writes-combined.md` | 154 | **Full write-side regression** — lookups, creation, edits, tags, moves, lifecycle, integration, inheritance, repetition rules |
| **Reads Combined** *(composite)* | `tests/reads-combined.md` | 169 | **Full read-side regression** — list tasks, date filtering, list projects, simple list tools, validation & error formatting |
| **Batch Processing** *(standalone)* | `tests/batch-processing.md` | 2 | **50-item mega-batch** — create 50 flat inbox tasks, reorganize into 4-level hierarchy inside a GM project in a single call, verify all 50 succeed and `list_tasks` shows `estimatedMinutes` 1→50 in depth-first outline order |
| Read Lookups | `tests/read-lookups.md` | 8 | get_task, get_project, get_tag — happy path, not-found errors, $inbox guard, enriched references |
| Task Creation | `tests/task-creation.md` | 17 | add_tasks — inbox, $inbox parent, all fields, tag resolution, null/system-location errors, batch limit, enriched response shape |
| Integration Flows | `tests/integration-flows.md` | 8 | End-to-end write-through: create→edit→move→tags→lifecycle→get_all |
| Edit Operations | `tests/edit-operations.md` | 23 | Field editing, patch semantics, no-ops, status warnings, errors, combos |
| Tag Operations | `tests/tag-operations.md` | 15 | Tag add/remove/replace, ambiguity, no-ops, errors |
| Move Operations | `tests/move-operations.md` | 23 | All 5 move modes, $inbox moves, null rejection, anchor errors, cross-level, circular refs, completed/dropped movement |
| Lifecycle | `tests/lifecycle.md` | 12 | Complete, drop, cross-state, repeating tasks, validation |
| Inheritance | `tests/inheritance.md` | 8 | Effective field inheritance — dueDate, deferDate, plannedDate, flagged from projects through task chains |
| Repetition Rules | `tests/repetition-rules.md` | 40 | Creation, read model, set/clear/partial update/type change, no-ops, status warnings, lifecycle, normalization, validation errors, combos, regression guards |
| List Tasks | `tests/list-tasks.md` | 46 | list_tasks — project/tag/$inbox/flagged/availability (available/blocked/remaining)/estimate/search filters, lifecycle date filter auto-inclusion, availability redundancy warnings, null/empty rejection, contradictions, name resolution warnings, pagination, AND-logic combos, enriched response shape |
| Date Filtering | `tests/date-filtering.md` | 35 | list_tasks date filters — due shortcuts (overdue/soon/today), lifecycle date filters (completed/dropped with auto-inclusion), shorthand periods (this/last/next), absolute bounds, boundary inclusivity, combos, defer hints, non-due fields (defer, added, modified, planned), inherited effective dates, edge cases |
| List Projects | `tests/list-projects.md` | 33 | list_projects — folder filter, review_due_within duration, flagged, availability, ALL shorthand, $inbox warning, null/empty rejection, search, folder resolution warnings, pagination, combos, enriched response shape |
| Simple List Tools | `tests/simple-list-tools.md` | 23 | list_tags, list_folders, list_perspectives — availability defaults (tags vs folders), ALL shorthand, null/empty rejection, search, pagination, parent hierarchy, builtin flag, cross-tool consistency, enriched references |
| Validation & Errors | `tests/validation-errors.md` | 35 | Cross-tool error formatting — unknown fields, invalid types, batch limits, filter null/empty, $inbox guard, system locations, reserved prefix, middleware reformatting, no pydantic internals, camelCase in errors, DateFilter validation, breaking change rejections |

## Flow

1. **Present the suites** — show the table above and ask which suite to run
2. **Suite-driven setup** — run the discovery script with the selected suite:
   ```
   uv run python3 .claude/skills/uat-regression/discover.py \
     --suite .claude/skills/uat-regression/tests/<suite>.md
   ```
   The JSON output contains everything needed for setup: `setup` instructions, `entities`, `manual_actions`, `computed_values`, `user_prompts`. Follow the setup instructions to create tasks, handle unmatched entities, present user prompts and manual actions.
3. **Read the suite file** — load the test file to get `## Conventions`, `## Tests`, and `## Report Table Rows` sections.
4. **Execute two phases:**
   - **Phase 1 — Autonomous testing**: Run all tests in the suite, collect results (PASS/FAIL/SKIP). After a test that modifies state, clean up if the task is reused later (e.g., rename back, remove tags).
   - **Phase 2 — Report**: Generate the report using the template below.
5. **Cleanup consolidation**: After the report, consolidate all test artifacts into a single deletable task:
   1. Check if `⚠️ DELETE THIS AFTER UAT` already exists (via `get_all` or by tracking its ID from earlier in the session). Reuse it if found; only create a new one if it doesn't exist.
   2. Move all top-level test parents (e.g., `UAT-v1.2`, `UAT-v1.2-Alt`) under it — children follow automatically
   3. Move any stray leaf tasks created during testing (e.g., B1-InboxTask, B4-TagByName — tasks created in the inbox without a test parent) under it too
   4. Tell the user: "All test tasks are now under '⚠️ DELETE THIS AFTER UAT' in your inbox. Delete that one task to clean up everything."
   5. **If moves fail** (e.g., move operations are broken): skip consolidation and instead list all task names/IDs the user needs to manually delete.

## Composite Suite Handling

When a selected suite file contains a `## Composite Suite` heading, it is a manifest referencing multiple base suites — not a test file itself. Use this flow instead of the standard single-suite flow.

1. **Detection**: After reading the selected suite file, check for the `## Composite Suite` heading. If present, parse the manifest table to get the ordered list of base suite file paths, their section prefixes, and suite names.

2. **Suite-driven discovery**: Run the discovery script with all base suite paths:

   ```
   uv run python3 .claude/skills/uat-regression/discover.py \
     --suite .claude/skills/uat-regression/tests/list-tasks.md \
     --suite .claude/skills/uat-regression/tests/date-filtering.md \
     ... (one --suite per base suite)
   ```

   The script reads YAML frontmatter from each suite, consolidates discovery needs, queries SQLite, and returns JSON with: resolved entities + setup instructions + manual actions + computed values per suite.

   **Do not read individual suite files or the script source.** The JSON output is the complete setup context.

3. **Handle unmatched**: If `unmatched` is non-empty, prompt the user to create/configure the missing entities before proceeding.

4. **User prompts**: If any suite has `user_prompts`, present them to the user and store answers.

5. **Compute dynamic values**: For suites with `computed_values`, compute the actual values using `user_prompts` answers and current time.

6. **Create all task hierarchies**: Follow each suite's `setup` instructions to create tasks. Each base suite keeps its own parent task name (UAT-ReadLookups, UAT-EditOps, etc.) — do not rename or renumber them. Build a unified **task ID map** (task name → OmniFocus ID) across all suites.

7. **Consolidated manual actions**: Collect all `manual_actions` from all suites, present once as a numbered list. Get one confirmation, then proceed.

8. **Sequential sub-agent execution**: For each base suite in manifest order:
   a. Build the sub-agent prompt using the **Sub-Agent Prompt Template** below, filling in the suite name, prefix, file path, entity map, task ID map, and computed values.
   b. Spawn a **general-purpose sub-agent** (via the Agent tool) with the built prompt.
   c. Wait for the sub-agent to complete.
   d. Parse the structured results from the sub-agent's response.
   e. **If the sub-agent fails** (crash, timeout, unparseable output): record all tests from this suite as SKIP with reason "Sub-agent execution failed" and continue to the next suite.

9. **Consolidated report**: Assemble one report from all sub-agent results:
   - **Report table**: One table with section prefixes (A-1, A-2a, B-1, B-2a, C-1, ...). Insert bold section-header rows between suites (e.g., **`A — Read Lookups`**). Use each sub-agent's report rows. Totals: sum all sub-agent pass/fail/skip counts.
   - **User Report warnings/errors**: Merge all sub-agent warning and error inventories. Deduplicate entries with identical warning/error text — combine their "Triggered By" fields. Merge observations.

10. **Single cleanup umbrella**: Create one `⚠️ DELETE THIS AFTER UAT` task. Move all parent tasks from all suites under it. Same cleanup rules as the standard flow.

## Sub-Agent Prompt Template

When spawning a sub-agent for step 8 of Composite Suite Handling, construct the prompt from this template. Replace all `{placeholders}` with actual values.

---

**Start of template:**

# UAT Test Runner — {suite_name} (Prefix: {prefix})

You are a black-box QA tester executing OmniFocus MCP tool tests. You interact with OmniFocus exclusively through MCP tools and report what you observe.

**Rules:**
- Do NOT read source code (.py, .js, test files) — you don't know the implementation
- Do NOT debug failures — record what happened vs expected and move on
- Do NOT fix anything — bugs are test results, not tasks
- Stop early if fundamentally broken (server down, basic operations failing) — mark remaining tests as SKIP with reason
- No parallel error calls — Claude Code cancels sibling calls when one errors. Run error-expecting calls individually, never mixed with calls that must succeed.

## Step 1 — Load MCP Tools

Call ToolSearch with query "+omnifocus" to load the OmniFocus MCP tools before running any tests.

## Step 2 — Read Suite File

Read the test suite at:

`{suite_file_path}`

- Read the `## Conventions` section — follow its domain-specific rules during test execution.
- Execute ONLY the `## Tests` section, in order.
- **Skip any cleanup instructions** — the orchestrator handles cleanup after all suites complete.
- Read the `## Report Table Rows` section — use it as the template for your results output.

## Step 3 — Run All Tests

Use these reference data maps wherever the suite references discovered entities or test tasks:

### Entity Map
```json
{entity_map_json}
```

### Task ID Map
```json
{task_id_map_json}
```

### Computed Values
```json
{computed_values_json}
```

(If Computed Values is empty `{}`, the suite has no computed values.)

## Step 4 — Return Results

After executing all tests, return results in this format:

### Report Rows

(One row per test from the suite's Report Table Rows. Fill in the Result column.)

| # | Test | Description | Result |
|---|------|-------------|--------|
| {prefix}-1a | test name | description | PASS/FAIL/SKIP |
| ... | ... | ... | ... |

### Totals

X PASS, Y FAIL, Z SKIP

### Failures

(For each FAIL — test ID, expected behavior, actual behavior. Omit section if no failures.)

### Skipped

(For each SKIP — test ID, reason. Omit section if no skips.)

### Warnings Observed

Every distinct warning encountered during this suite — even if they all look correct.

| Warning Text | Triggered By | Looks Correct? | Agent Interpretation | Notes |
|---|---|---|---|---|
| exact text | test {prefix}-Xa | Yes/No | what an agent would understand | any concerns |

### Errors Observed

Every distinct error encountered during this suite — even if they all look correct.

| Error Text | Triggered By | Looks Correct? | Agent Interpretation | Notes |
|---|---|---|---|---|
| exact text | test {prefix}-Xa | Yes/No | what an agent would understand | any concerns |

### Observations

(Bullet list: warning tone, error message quality, UX patterns, anything noteworthy. Omit if nothing to note.)

**End of template.**

---

**Template usage notes:**
- Pass the **full** entity map and task ID map to every sub-agent — don't filter per suite. The extra tokens from unrelated suites' entries are negligible (~500 tokens), and it eliminates the risk of missing a cross-reference.
- For the date-filtering suite, computed values include: OVERDUE_DUE, SOON_DUE, TODAY_DUE, FUTURE_DUE, TODAY_DEFER, TOMORROW_DATE, YESTERDAY_DATE, TODAY_DATE_STR, plus the due-soon threshold setting.
- The sub-agent prompt uses markdown output format (not JSON) because the orchestrator is also an LLM — markdown tables are natural to produce and consume, and align with the final report format.

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

These apply to ALL test suites AND any ad-hoc verification tasks:

- **No parallel error calls.** Claude Code cancels all sibling calls when one errors. Never mix calls that might fail (nonexistent IDs, validation errors) with calls that must succeed. Run error-expecting calls individually.
- **Cleanup = consolidate under umbrella task. Always.** Every task you create in OmniFocus — whether during a full suite run, a quick verification, or a one-off retest — is a test artifact that the user must manually delete. Dropping or completing tasks is NOT cleanup; those tasks still exist in the database. The ONLY acceptable cleanup is: create `⚠️ DELETE THIS AFTER UAT` in the inbox (or reuse one if it already exists), move all test artifacts under it, and tell the user to delete that one task. This applies even for a single temp task.

Each suite lists its own domain-specific conventions in its `## Conventions` section.

## Shared Setup Procedures

Reusable setup patterns that suites can reference by name instead of repeating inline.

### Project Discovery

Some suites need real OmniFocus projects (not just inbox tasks). When a suite's setup says "Follow the **Project Discovery** procedure," use this flow:

1. Call `get_all` and scan the projects list. Look for `🧪 GM-` prefixed projects first — these are the golden master test infrastructure.
2. The suite declares **project profiles** — named requirements like `dated-project: dueDate set, deferDate set, flagged=true`. Match discovered projects against these profiles.
3. Present candidates to the user in a table (project name, ID, and the fields relevant to the profiles). Ask for confirmation before proceeding.
4. If the best candidate for a profile is missing required fields, tell the user exactly which field(s) to set and wait for them to fix it.
5. After confirmation, call `get_project` on each selected project (can be parallel) to get fresh data. Store the field values needed for assertions.
6. Validate all profiles are satisfied. If any precondition still fails, tell the user which field is wrong and wait.

### Discovery Script

Entity discovery uses `discover.py` instead of `get_all`. The script queries the OmniFocus SQLite cache directly and returns compact JSON (~2-5KB vs ~50-100KB from `get_all`).

**Location**: `discover.py` (same directory as this skill file)

**Primary interface** (suite-driven — used by composite and single-suite flows):
```
uv run python3 discover.py --suite PATH [--suite PATH]... [--db PATH]
```
Reads YAML frontmatter from each suite file, consolidates discovery needs, and returns JSON with resolved entities, setup instructions, manual actions, computed values, and user prompts per suite. **Do not read the script source or individual suite files** — the JSON output is the complete setup context.

**Ad-hoc interface** (for manual discovery outside suite context):
```
uv run python3 discover.py [--need SPEC]... [--count SPEC]... [--find-ambiguous TYPES] [--db PATH]
```

- `--need TYPE:LABEL[:COUNT]:FILTER[,FILTER,...]` — find first N entities matching all filters
- `--count LABEL:TYPE[:FILTER,...]` — count matching entities
- `--find-ambiguous TYPE[,TYPE,...]` — detect ambiguous names (tags: exact duplicates, projects/folders: substring overlap)

The two interfaces are mutually exclusive.

**Filter reference**:
- Project: `active`, `completed`, `dropped`, `blocked`, `has_due`, `no_due`, `has_defer`, `no_defer`, `has_planned`, `no_planned`, `flagged`, `not_flagged`, `in_folder`, `review_soon`
- Tag: `available`, `blocked`, `dropped`, `not_dropped`, `unambiguous`
- Folder: `available`, `dropped`, `has_parent`, `has_children`
- Perspective: (none — any custom perspective matches)

**Match priority**: `🧪 GM-` prefixed entities sort first.

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
- **Cleanup**: "All test tasks consolidated under '⚠️ DELETE THIS AFTER UAT' in your inbox — delete that one task to clean up."

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
  ▼ USER REPORT (below) — warnings & errors inventory + improvement notes
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

### Errors Observed

Every distinct error encountered during this test suite. Always populated — even when all errors look correct.

Same "Agent Interpretation" lens as warnings: read the error with shoshin. Would an agent understand what went wrong and how to fix its input? Does the error leak internals (pydantic types, _Unset, snake_case field names)? If the error is confusing or misleading, that's a finding.

| Error Text | Triggered By | Looks Correct? | Agent Interpretation | Notes |
|---|---|---|---|---|

### Tool / Server Improvements
- (Bugs, error message quality, API design, missing validations)

### Skill / Test Coverage Improvements
- (Missing test cases, edge cases not covered, skill clarity)

### Other Observations
- (UX patterns, anything else noteworthy)
```

The **Warnings Observed** and **Errors Observed** sections are always populated (they're inventories, not just problems). The other subsections only include actually-observed items — if a section is empty, omit it.

**IMPORTANT:** Do NOT repeat bugs already captured in the Failures section. The subsections below the inventories are for observations beyond what the test suite covers — wording improvements, UX polish, missing coverage, architectural suggestions.
