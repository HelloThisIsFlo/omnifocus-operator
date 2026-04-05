---
phase: quick-260401-twg
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/omnifocus_operator/agent_messages/descriptions.py
  - src/omnifocus_operator/contracts/use_cases/add/tasks.py
  - src/omnifocus_operator/contracts/use_cases/edit/tasks.py
  - src/omnifocus_operator/contracts/shared/repetition_rule.py
  - tests/test_descriptions.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "Every write-side date field shows an ISO 8601 example instead of timezone prose"
    - "Enum fields (schedule, basedOn) have per-value one-liner documentation"
    - "Tag field descriptions are short format hints only (error behavior in tool doc only)"
    - "get_all tool warns agents to prefer list_tasks/list_projects"
    - "Previously bare fields (estimatedMinutes, flagged, name, note, id) have descriptions"
    - "on/onDates/onDays descriptions clarify scope, mutual exclusivity, and optionality"
  artifacts:
    - path: "src/omnifocus_operator/agent_messages/descriptions.py"
      provides: "All updated and new description constants"
      contains: "DATE_EXAMPLE"
    - path: "tests/test_descriptions.py"
      provides: "Enforcement that examples= values come from centralized constants"
  key_links:
    - from: "contracts/use_cases/add/tasks.py"
      to: "descriptions.py"
      via: "Field(examples=[DATE_EXAMPLE])"
      pattern: "examples=\\[DATE_EXAMPLE\\]"
    - from: "contracts/use_cases/edit/tasks.py"
      to: "descriptions.py"
      via: "Field(examples=[DATE_EXAMPLE])"
      pattern: "examples=\\[DATE_EXAMPLE\\]"
---

<objective>
Improve MCP tool schema descriptions and field documentation across descriptions.py and all consuming models.

Purpose: Agent-facing schemas should be precise, non-redundant, and self-documenting. Timezone prose gets replaced with examples, enums get per-value docs, bare fields get descriptions, get_all gets a last-resort warning.

Output: Updated descriptions.py, updated contract files with examples= on date Fields, new test enforcement for examples centralization.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/quick/260401-twg-improve-mcp-tool-schema-descriptions-and/260401-twg-CONTEXT.md
@src/omnifocus_operator/agent_messages/descriptions.py
@src/omnifocus_operator/contracts/use_cases/add/tasks.py
@src/omnifocus_operator/contracts/use_cases/edit/tasks.py
@src/omnifocus_operator/contracts/shared/repetition_rule.py
@tests/test_descriptions.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update descriptions.py and wire examples/descriptions into consuming models</name>
  <files>
    src/omnifocus_operator/agent_messages/descriptions.py
    src/omnifocus_operator/contracts/use_cases/add/tasks.py
    src/omnifocus_operator/contracts/use_cases/edit/tasks.py
    src/omnifocus_operator/contracts/shared/repetition_rule.py
  </files>
  <action>
CRITICAL: CONTEXT.md contains exact locked phrasings. Use them VERBATIM -- do not rephrase.

**In descriptions.py**, make these changes:

1. **Add DATE_EXAMPLE constant:**
   ```python
   DATE_EXAMPLE = "2026-03-15T17:00:00Z"
   ```

2. **Replace write-side date descriptions** (remove timezone sentence, use locked phrasings exactly):
   - DUE_DATE_WRITE = "Deadline with real consequences if missed. Not for intentions -- use plannedDate instead."
   - DEFER_DATE_WRITE = "Task cannot be acted on until this date. Hidden from most views until then. Not for 'I don't want to work on it yet' -- use plannedDate for that."
   - PLANNED_DATE_WRITE = "When you intend to work on this task. No urgency signal, no visibility change, no penalty for missing it."

3. **Replace tag descriptions** (short format hint only, per locked phrasings):
   - TAGS_ADD_COMMAND = "Tag names (case-insensitive) or IDs; you can mix both."
   - TAG_ACTION_ADD = "Tag names (case-insensitive) or IDs to add; you can mix both."
   - TAG_ACTION_REMOVE = "Tag names (case-insensitive) or IDs to remove; you can mix both."
   - TAG_ACTION_REPLACE = "Replace all tags with this list. Tag names (case-insensitive) or IDs; you can mix both. Pass null or [] to clear all tags."

4. **Replace SCHEDULE_DOC and BASED_ON_DOC** with locked phrasings from CONTEXT.md (multi-line with per-value one-liners; SCHEDULE_DOC has WIP tag, BASED_ON_DOC does not).

5. **Replace ON_DATE** with locked phrasing:
   - ON_DATE = "Days of the month. Valid values: -1 (last day of month), 1-31."

6. **Replace ON_DAYS** with locked phrasing:
   - ON_DAYS = "Days of the week for weekly recurrence. Only valid when type is 'weekly'; rejected for other types."

7. **Add new description constants for previously bare fields:**
   - ESTIMATED_MINUTES = "Time estimate in minutes."
   - FLAGGED = "Mark task for priority attention. Surfaces in Flagged perspective."
   - NAME_ADD_COMMAND = "Task name. Leading/trailing whitespace is stripped."
   - NAME_EDIT_COMMAND = "New task name. Leading/trailing whitespace is stripped; empty names rejected."
   - NOTE_ADD_COMMAND = "Plain-text note attached to the task."
   - NOTE_EDIT_COMMAND = "Plain-text note. Set to null to clear."
   - ID_EDIT_COMMAND = "OmniFocus task ID to edit."
   - FLAGGED_EDIT_COMMAND = "Mark task for priority attention. Surfaces in Flagged perspective."
   - ESTIMATED_MINUTES_EDIT = "Time estimate in minutes. Set to null to clear."

8. **Add on/onDates mutual exclusivity cross-reference** to at least one of ON_DATE or the on field. Add to ON_DATE description: append " Mutually exclusive with on (day-of-week patterns)." Similarly consider adding to a new ON_ORDINAL_WEEKDAY constant if one is needed for the `on` field.

9. **Add frequency sub-field optionality note.** Add a constant for the `on` field on FrequencyAddSpec/FrequencyEditSpec:
   - ON_WEEKDAY_PATTERN = "Ordinal weekday pattern for monthly recurrence (e.g. last friday). Optional -- omit to repeat on the calendar date. Mutually exclusive with onDates."

10. **Update GET_ALL_TOOL_DOC** -- add last-resort warning referencing list_tasks, list_projects as preferred alternatives. Write as if list tools already exist.

11. **Remove timezone paragraphs from ADD_TASKS_TOOL_DOC and EDIT_TASKS_TOOL_DOC** -- delete the two-line block "All date fields require timezone info...Naive datetimes are rejected." from both.

**In contracts/use_cases/add/tasks.py:**
- Import DATE_EXAMPLE and the new field description constants
- Add `examples=[DATE_EXAMPLE]` to due_date, defer_date, planned_date Fields
- Add `description=NAME_ADD_COMMAND` to the name Field
- Add `description=FLAGGED` and keep `default=False` on flagged Field (use Field())
- Add `description=ESTIMATED_MINUTES` to estimated_minutes Field (use Field())
- Add `description=NOTE_ADD_COMMAND` to note Field (use Field())

**In contracts/use_cases/edit/tasks.py:**
- Import DATE_EXAMPLE and the new field description constants
- Add `examples=[DATE_EXAMPLE]` to due_date, defer_date, planned_date Fields
- Add `description=ID_EDIT_COMMAND` to id Field (use Field())
- Add `description=NAME_EDIT_COMMAND` to name Field (use Field())
- Add `description=FLAGGED_EDIT_COMMAND` to flagged Field (use Field())
- Add `description=NOTE_EDIT_COMMAND` to note Field (use Field())
- Add `description=ESTIMATED_MINUTES_EDIT` to estimated_minutes Field (use Field())

**In contracts/shared/repetition_rule.py:**
- Import ON_DATE, ON_WEEKDAY_PATTERN, and any new constants needed
- Add `description=ON_DATE` to on_dates Fields on FrequencyAddSpec and FrequencyEditSpec
- Add `description=ON_WEEKDAY_PATTERN` to on Fields on FrequencyAddSpec and FrequencyEditSpec
  </action>
  <verify>
    <automated>cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && uv run pytest tests/test_descriptions.py tests/test_output_schema.py -x -q</automated>
  </verify>
  <done>
    - All locked phrasings from CONTEXT.md used verbatim
    - Write-side date fields have examples=[DATE_EXAMPLE], no timezone prose
    - Tag field descriptions are short format hints (error behavior only in tool docs)
    - get_all warns about list_tasks/list_projects as preferred alternatives
    - Previously bare fields (name, flagged, estimatedMinutes, note, id) have descriptions
    - ON_DATE, ON_DAYS, on field descriptions clarify scope/mutual exclusivity/optionality
    - SCHEDULE_DOC and BASED_ON_DOC have per-value one-liners
    - Timezone paragraphs removed from ADD_TASKS_TOOL_DOC and EDIT_TASKS_TOOL_DOC
    - Existing description tests pass
    - Output schema tests pass
  </done>
</task>

<task type="auto">
  <name>Task 2: Add examples= enforcement test</name>
  <files>tests/test_descriptions.py</files>
  <action>
Add a new test to TestDescriptionConsolidation (or a new TestExamplesEnforcement class) in test_descriptions.py.

The test should:
1. Walk all consumer modules (same _CONSUMER_MODULES list)
2. For each module, parse with ast and find Field(...) calls
3. For any Field() call that has an `examples=` keyword:
   - The value must be a list literal (ast.List)
   - Each element in the list must be an ast.Name (a constant reference), NOT an ast.Constant (inline value)
4. Collect violations and assert none exist

This mirrors the existing `test_no_inline_field_descriptions_in_agent_models` pattern but for `examples=` instead of `description=`.

Test name: `test_no_inline_examples_in_agent_models`

Also add DATE_EXAMPLE to the imports in the test file if needed for any reference checks.
  </action>
  <verify>
    <automated>cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && uv run pytest tests/test_descriptions.py -x -q</automated>
  </verify>
  <done>
    - New test enforces that examples= values on Fields come from centralized constants
    - Test passes with the changes from Task 1
    - Test would catch any future inline example values
  </done>
</task>

</tasks>

<verification>
Run the full test suite to ensure no regressions:

```bash
cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && uv run pytest tests/test_descriptions.py tests/test_output_schema.py -x -q
```

Quick smoke check that tool descriptions stay under 2048-byte limit (already covered by existing test_tool_descriptions_within_client_byte_limit).
</verification>

<success_criteria>
- All locked phrasings from CONTEXT.md appear verbatim in descriptions.py
- Write-side date Fields show examples=[DATE_EXAMPLE] instead of timezone prose
- Tag descriptions are short format hints; error behavior stays in tool docs only
- get_all warns agents to use list_tasks/list_projects instead
- All previously bare fields now have descriptions
- Repetition fields (onDates, onDays, on) clarify scope, mutual exclusivity, optionality
- New test prevents inline examples= values from creeping back
- All existing tests pass (descriptions + output schema)
</success_criteria>

<output>
After completion, create `.planning/quick/260401-twg-improve-mcp-tool-schema-descriptions-and/260401-twg-SUMMARY.md`
</output>
