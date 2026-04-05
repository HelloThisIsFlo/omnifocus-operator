# Quick Task 260401-twg: Improve MCP tool schema descriptions and field documentation - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Task Boundary

Improve agent-facing MCP tool schemas: fix semantic gaps, add missing descriptions, clean up redundancy, and add get_all warning. Single pass through `agent_messages/descriptions.py` and consuming models/contracts.

</domain>

<decisions>
## Implementation Decisions

### onDates schema edge case
- Description-only fix. No schema type changes — runtime validator already rejects 0.
- **Locked phrasing:**
  ```python
  ON_DATE = "Days of the month. Valid values: -1 (last day of month), 1–31."
  ```

### Enum documentation (schedule, basedOn)
- Field-level only — expand SCHEDULE_DOC and BASED_ON_DOC with per-value one-liners.
- **schedule values get a WIP tag** — edge cases with day-of-week patterns are unresolved (see todo #14).
- **basedOn has no WIP tag** — semantics are settled.
- **Locked phrasings:**
  ```python
  BASED_ON_DOC = (
      "Which date field anchors the repetition schedule. "
      "Other date fields shift relatively, preserving their "
      "current offset from the anchor.\n\n"
      "- due_date: schedule based on due date\n"
      "- defer_date: schedule based on defer date\n"
      "- planned_date: schedule based on planned date"
  )

  SCHEDULE_DOC = (
      "Repetition schedule type. "
      "[WIP: day-of-week edge cases under review]\n\n"
      "- regularly: fixed calendar dates; every missed "
      "occurrence must be individually resolved\n"
      "- regularly_with_catch_up: fixed calendar dates, "
      "but skips overdue to next future date\n"
      "- from_completion: next date calculated from when "
      "you complete this occurrence"
  )
  ```

### Timezone redundancy
- Remove timezone prose from both tool descriptions AND field descriptions.
- Replace with `examples=[DATE_EXAMPLE]` on each write-side date Field.
- The example value is a centralized constant in `descriptions.py`.
- Update `tests/test_descriptions.py` to enforce that `examples=` values come from centralized constants.
- **Locked phrasings** (timezone sentence removed, rest unchanged):
  ```python
  DATE_EXAMPLE = "2026-03-15T17:00:00Z"

  DUE_DATE_WRITE = (
      "Deadline with real consequences if missed. "
      "Not for intentions -- use plannedDate instead."
  )

  DEFER_DATE_WRITE = (
      "Task cannot be acted on until this date. "
      "Hidden from most views until then. "
      "Not for 'I don't want to work on it yet' -- use plannedDate for that."
  )

  PLANNED_DATE_WRITE = (
      "When you intend to work on this task. "
      "No urgency signal, no visibility change, no penalty for missing it."
  )
  ```
  Each write-side date Field gets: `Field(..., examples=[DATE_EXAMPLE])`

### Tag redundancy
- Field descriptions: short format hint only. Error behavior moves to tool doc only.
- **Locked phrasings (fields):**
  ```python
  TAGS_ADD_COMMAND = "Tag names (case-insensitive) or IDs; you can mix both."

  TAG_ACTION_ADD = "Tag names (case-insensitive) or IDs to add; you can mix both."

  TAG_ACTION_REMOVE = "Tag names (case-insensitive) or IDs to remove; you can mix both."

  TAG_ACTION_REPLACE = (
      "Replace all tags with this list. Tag names (case-insensitive) or IDs; "
      "you can mix both. Pass null or [] to clear all tags."
  )
  ```
- **Tool doc tag paragraphs stay as-is** (already have format hint + error behavior):
  ```python
  # In ADD_TASKS_TOOL_DOC:
  "Tags accept names (case-insensitive) or IDs; you can mix both.\n"
  "Non-existent names are rejected. Ambiguous names (case-insensitive\n"
  "collision) return an error.\n"

  # In EDIT_TASKS_TOOL_DOC:
  "Tags (in all tag fields) accept names (case-insensitive) or IDs;\n"
  "you can mix both. Non-existent names are rejected. Ambiguous names\n"
  "(case-insensitive collision) return an error.\n"
  ```

### Timezone removal from tool docs
- Remove the following paragraph from BOTH ADD_TASKS_TOOL_DOC and EDIT_TASKS_TOOL_DOC:
  ```python
  # DELETE this from both tool docs:
  "All date fields require timezone info (ISO 8601 with offset or Z).\n"
  "Naive datetimes are rejected.\n"
  ```
- Date format is now conveyed exclusively via `examples=[DATE_EXAMPLE]` on each write-side date Field.

### get_all warning
- Add full last-resort/debugging warning now, written as if list tools already exist. Reference list_tasks, list_projects by name as preferred alternatives.

### Missing descriptions
- Add descriptions for: estimatedMinutes (confirm units), flagged (semantic meaning), name, note, id (edit_tasks).

### Test enforcement for examples
- Update `tests/test_descriptions.py` to enforce that `examples=` values on Pydantic Fields come from centralized constants in `descriptions.py`, not hardcoded inline. Same pattern as the existing description enforcement — scan all agent-facing Fields, verify example values match a known constant.

### on field (OrdinalWeekday)
- Already fixed in quick-260401-hz9 — no action needed.

### onDays scope
- **Locked phrasing:**
  ```python
  ON_DAYS = "Days of the week for weekly recurrence. Only valid when type is 'weekly'; rejected for other types."
  ```

### on/onDates mutual exclusivity
- Cross-reference on at least one field description, not just tool doc.

### Empty on/{} and omitted onDays
- Clarify that sub-fields within frequency are optional constraints, not required refinements.

</decisions>

<specifics>
## Specific Ideas

- get_all doc should reference list_tasks, list_projects by name as preferred alternatives
- Schedule WIP tag format: `[WIP: day-of-week edge cases under review]`

</specifics>

<canonical_refs>
## Canonical References

- `docs/omnifocus-concepts.md` — authoritative source for schedule/basedOn semantics (just updated with repetition rules section)
- `.planning/todos/pending/2026-04-01-clarify-repetition-schedule-and-repeat-mode-edge-cases.md` — todo tracking the WIP items
- `.planning/todos/pending/2026-04-01-improve-mcp-tool-schema-descriptions-and-field-documentation.md` — original todo driving this task

</canonical_refs>
