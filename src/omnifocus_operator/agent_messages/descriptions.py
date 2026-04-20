"""Consolidated description strings for all agent-facing field and class descriptions.

Every Field(description=...) string and agent-visible class docstring is defined here.
This makes it easy to review, audit, and maintain all agent-facing schema text
in one place.
"""

# --- Dates: Read-Side ---

DUE_DATE = "Deadline with real consequences if missed."

DEFER_DATE = "Task cannot be acted on until this date; hidden from most views until then."

PLANNED_DATE = (
    "When the user intends to work on this. No urgency signal, no penalty for missing it."
)

_INHERITED_FIELD_DESC = "Inherited from parent hierarchy when not set directly on this task."

INHERITED_FLAGGED = _INHERITED_FIELD_DESC

INHERITED_DUE_DATE = _INHERITED_FIELD_DESC

INHERITED_DEFER_DATE = _INHERITED_FIELD_DESC

INHERITED_PLANNED_DATE = _INHERITED_FIELD_DESC

INHERITED_DROP_DATE = _INHERITED_FIELD_DESC

INHERITED_COMPLETION_DATE = _INHERITED_FIELD_DESC

# --- Reusable Fragments ---

_STRIPPING_NOTE = """\
Response stripping: null values, empty arrays, empty strings, false booleans, and "none" urgency are omitted. Absent field = not set."""

_INHERITED_TASKS_EXPLANATION = """\
inherited* fields: OmniFocus's resolved value after applying inheritance from the ancestor chain (parent task -> project -> folder). Both direct and inherited can coexist. Resolution rules vary by field (dueDate = tightest, deferDate = latest, plannedDate/dropDate/completionDate = nearest ancestor). inherited fields are read-only; to edit, use the direct field (dueDate, not inheritedDueDate)."""

_COUNT_ONLY_TIP = "Count-only: use limit: 0 to get {items: [], total: N} without fetching data."

_FILTERS_AND_LOGIC = "All filters combine with AND logic."

_LIFECYCLE_FILTER_NOTE = """\
completed/dropped filters include those lifecycle states in results (excluded by default). All other filters only restrict.
The 'soon' shortcut uses your OmniFocus due-soon threshold preference."""

_TAGS_INPUT_NOTE = """\
Tags accept names (case-insensitive) or IDs; you can mix both. Non-existent names are rejected. Ambiguous names (case-insensitive collision) return an error."""

_BATCH_RETURNS = """\
Returns: array of per-item results. Each item: status ('success' | 'error' | 'skipped'), id (success + edit errors/skips), name (success only), warnings (any status), error (error only)."""

_BATCH_CROSS_ITEM_NOTE = """\
Items are independent: batch items cannot reference other items created or edited in the same batch. For hierarchies (parent-child), use sequential calls."""

_BATCH_CONCURRENCY_NOTE = "Note: concurrent batch calls from separate agents are not serialized."

_WRITE_RETURNS = _BATCH_RETURNS

# Behavioral semantics — single source of truth, reused across field
# descriptions and tool-doc bullets.
_IS_SEQUENTIAL_SEMANTIC = (
    "Only the next-in-line child is available; later children are blocked "
    "until earlier ones complete."
)

_DEPENDS_ON_CHILDREN_SEMANTIC = (
    "Blocked until all children are done, then must be completed manually. "
    "Treat as discrete work, not a collapsible grouping."
)

_TASK_TYPE_SEMANTIC = "'parallel' | 'sequential'. Controls how children's availability is computed."

_COMPLETES_WITH_CHILDREN_SEMANTIC = (
    "When true, auto-completes as soon as the last child finishes. "
    "When false, this is genuine work waiting on children."
)

_BEHAVIORAL_FLAGS_NOTE = f"""\
Behavioral flags (default response):
  - isSequential: {_IS_SEQUENTIAL_SEMANTIC}
  - dependsOnChildren: {_DEPENDS_ON_CHILDREN_SEMANTIC}"""

# Project-scoped behavioral flag note (Phase 56-08 / G1). Covers isSequential
# only because dependsOnChildren stays tasks-only — projects are always
# containers, so the "real unit of work waiting on children" semantic does
# not apply to them.
_PROJECT_BEHAVIORAL_FLAGS_NOTE = f"""\
Behavioral flag (default response):
  - isSequential: {_IS_SEQUENTIAL_SEMANTIC}"""

# --- Dates: Write-Side ---

DATE_EXAMPLE = "2026-03-15T17:00:00"

_DATE_INPUT_NOTE = """\
All dates use local time. Timezone offsets are accepted. Date-only inputs (no time) use your OmniFocus default time for that field."""

_DATE_INPUT_NOTE_FULL = """\
All dates use local time. Timezone offsets are accepted. Date-only inputs (no time) use your OmniFocus default time for that field. Date/time preferences are read from OmniFocus on server start; restart if you change them."""

DUE_DATE_WRITE = (
    "Deadline with real consequences if missed. Not for intentions -- use plannedDate instead."
)

DEFER_DATE_WRITE = """\
Task cannot be acted on until this date. Hidden from most views until then. Not for 'I don't want to work on it yet' -- use plannedDate for that."""

PLANNED_DATE_WRITE = """\
When you intend to work on this task. Not a target completion date -- just when you plan to give it attention. No urgency signal, no visibility change, no penalty for missing it."""

# --- Tags ---

TAGS_ADD_COMMAND = "Tag names (case-insensitive) or IDs; you can mix both."

TAGS_OUTPUT = "Tags applied to this entity, each with id and name."

TAG_ACTION_ADD = "Tag names (case-insensitive) or IDs to add; you can mix both."

TAG_ACTION_REMOVE = "Tag names (case-insensitive) or IDs to remove; you can mix both."

TAG_ACTION_REPLACE = """\
Replace all tags with this list. Tag names (case-insensitive) or IDs; you can mix both. Pass null or [] to clear all tags."""

CHILDREN_ARE_MUTUALLY_EXCLUSIVE = (
    "When true, child tags behave like radio buttons -- assigning one removes siblings."
)

# --- Repetition ---

ON_DAYS = """\
Days of the week for weekly recurrence. Only valid when type is 'weekly'; rejected for other types."""

ON_DATE = """\
Days of the month. Valid values: -1 (last day of month), 1-31. Mutually exclusive with on (day-of-week patterns)."""

ON_WEEKDAY_PATTERN = """\
Ordinal weekday pattern for monthly recurrence (e.g. last friday). Optional -- omit to repeat on the calendar date. Mutually exclusive with onDates."""

END_BY_DATE_DATE = "Repeat until this date."

# --- Order ---

ORDER_FIELD = """\
Hierarchical position among siblings (dotted notation like '2.3.1'). Each dot level is the 1-based position at that depth within the parent project or inbox. null when ordering data is unavailable (degraded mode)."""

# --- Presence & derived flags (Phase 56-05 / FLAG-01..05, FLAG-07) ---

HAS_NOTE_DESC = "True when the note is non-empty. Fetch via include=['notes']."

HAS_REPETITION_DESC = "True when a repetition rule is set. Fetch via include=['time']."

HAS_ATTACHMENTS_DESC = (
    "True when at least one attachment is present. Attachment content is never returned inline."
)

IS_SEQUENTIAL_DESC = f"True when type == 'sequential'. {_IS_SEQUENTIAL_SEMANTIC}"

DEPENDS_ON_CHILDREN_DESC = (
    "Tasks-only. True when the task has children AND does not complete with children. "
    f"{_DEPENDS_ON_CHILDREN_SEMANTIC}"
)

COMPLETES_WITH_CHILDREN_DESC = _COMPLETES_WITH_CHILDREN_SEMANTIC

TASK_TYPE_DESC = _TASK_TYPE_SEMANTIC

PROJECT_TYPE_DESC = (
    "'parallel' | 'sequential' | 'singleActions'. "
    "A 'singleActions' project is a flat bag of independent items with no shared intent."
)

# --- Write-side descriptions (Phase 56-06 / PROP-01..06) ---
#
# Write-side mirrors the read-side semantics, plus the omit-behavior
# (resolved from the user's OmniFocus preference when omitted).

COMPLETES_WITH_CHILDREN_WRITE = (
    f"{_COMPLETES_WITH_CHILDREN_SEMANTIC} Omit to use the user's OmniFocus default."
)

TASK_TYPE_WRITE = (
    f"{_TASK_TYPE_SEMANTIC} Use 'sequential' when children must be done in order. "
    "Omit to use the user's OmniFocus default."
)

# --- Entities ---

PARENT = "Project or task ID to place this task under. Omit for inbox."

NEXT_TASK = "First available (unblocked) task in this project."

FOLDER_PARENT_DESC = "Parent folder in the folder hierarchy."

PROJECT_FOLDER_DESC = "Folder containing this project."

TAG_PARENT_DESC = "Parent tag in the tag hierarchy."

TASK_PROJECT_DESC = "Project for this task, even for subtasks."

PARENT_REF_PROJECT_FIELD = "Parent project."

PARENT_REF_TASK_FIELD = "Parent task, when this is a subtask."

# --- Fields: Previously Bare ---

ESTIMATED_MINUTES = "Time estimate in minutes."

FLAGGED = "Mark task for priority attention. Surfaces in Flagged perspective."

NAME_ADD_COMMAND = "Task name. Leading/trailing whitespace is stripped."

NAME_EDIT_COMMAND = "New task name. Leading/trailing whitespace is stripped; empty names rejected."

NOTE_ADD_COMMAND = "Plain-text note attached to the task."

ID_EDIT_COMMAND = "OmniFocus task ID to edit."

ESTIMATED_MINUTES_EDIT = "Time estimate in minutes. Set to null to clear."

# --- Date Filter Models ---

THIS_PERIOD_FILTER_DOC = "Filter to today, this week, this month, or this year."
LAST_PERIOD_FILTER_DOC = "Filter to a recent window ending now."
NEXT_PERIOD_FILTER_DOC = "Filter to an upcoming window starting now."
ABSOLUTE_RANGE_FILTER_DOC = "Filter by explicit date bounds. Set before, after, or both."

THIS_PERIOD_UNIT = "When? d (today), w (this week), m (this month), y (this year)."
_DURATION_FORMAT = '"N<unit>" (unit: d/w/m/y). Omit count for 1. Examples: "3d", "2w", "m".'
LAST_PERIOD_DURATION = f"How far back from now. {_DURATION_FORMAT}"
NEXT_PERIOD_DURATION = f"How far ahead from now. {_DURATION_FORMAT}"
ABSOLUTE_RANGE_BEFORE = "Upper bound (inclusive). ISO date, ISO datetime, or 'now'."
ABSOLUTE_RANGE_AFTER = "Lower bound (inclusive). ISO date, ISO datetime, or 'now'."

DUE_DATE_SHORTCUT_DOC = "Shortcut for filtering by due date: overdue, soon, or today."

LIFECYCLE_DATE_SHORTCUT_DOC = (
    "Shortcut for filtering by lifecycle date: all (every task in that state) or today."
)

DATE_SHORTCUT_DOC = "Shortcut for date field filtering: today (tasks matching today's date)."

DUE_FILTER_DESC = """\
Filter by due date (inherited). Due date = deadline with real consequences if missed. 'overdue' = due before now. 'soon' = due within threshold (includes overdue). 'today' = due today. Or use a period/range filter."""

DEFER_FILTER_DESC = """\
Filter by defer date (inherited). Defer date = task hidden and unavailable until this date. For timing questions ('what becomes available this week?'), not availability state -- use availability: 'blocked' for all unavailable tasks. 'today' = deferred to today. Or use a period/range filter."""

PLANNED_FILTER_DESC = """\
Filter by planned date (inherited). Planned date = when you intend to work on this; no urgency, no penalty for missing it. 'today' = planned for today. Or use a period/range filter."""

COMPLETED_FILTER_DESC = """\
Inclusion filter: adds completed items to results (excluded by default). 'all' = every completed item regardless of date. 'today' = completed today. Or use a period/range filter."""

DROPPED_FILTER_DESC = """\
Inclusion filter: adds dropped items to results (excluded by default). 'all' = every dropped item regardless of date. 'today' = dropped today. Or use a period/range filter."""

ADDED_FILTER_DESC = "Filter by date added. 'today' = added today. Or use a period/range filter."

MODIFIED_FILTER_DESC = (
    "Filter by date modified. 'today' = modified today. Or use a period/range filter."
)

# --- Class Docstrings: Entities ---

TAG_REF_DOC = "Reference to a tag with both id and name."

PROJECT_REF_DOC = (
    'Reference to a project with id and name. The system inbox uses id="$inbox", name="Inbox".'
)

TASK_REF_DOC = "Reference to a task with id and name."

FOLDER_REF_DOC = "Reference to a folder with id and name."

PARENT_REF_DOC = "Direct parent of this task. Exactly one key present: 'project' or 'task'."

REVIEW_INTERVAL_DOC = "How often OmniFocus prompts the user to review this project."

TASK_DOC = "A single OmniFocus task with all fields."

PROJECT_DOC = "A single OmniFocus project with all fields."

TAG_DOC = "A single OmniFocus tag with all fields."

FOLDER_DOC = "A single OmniFocus folder with all fields."

PERSPECTIVE_DOC = "A single OmniFocus perspective."

ALL_ENTITIES_DOC = "All OmniFocus entities from a repository."

# --- Class Docstrings: Enums ---

URGENCY_DOC = "Time pressure axis -- is this task/project pressing?"

AVAILABILITY_DOC = """\
Which lifecycle states to include. 'remaining' (default) = available + blocked. Empty list [] = no remaining tasks (combine with completed/dropped filters for lifecycle-only results). Completed/dropped tasks are included via their own date filters, not here."""

TAG_AVAILABILITY_DOC = """\
Is this tag active? blocked = on hold, always blocks tagged tasks. dropped = hidden from hierarchy, blocks tasks only if their sole tag."""

FOLDER_AVAILABILITY_DOC = "Is this folder active?"

# Edge cases (INTERVAL≥2, early completion, same-day eligibility) differ between modes.
# See docs/byday-edge-cases.md for the full breakdown.
SCHEDULE_DOC = """\
Repetition schedule type.

- regularly: fixed calendar dates; if late, past occurrences must be completed one by one
- regularly_with_catch_up: fixed calendar dates, but skips overdue to next future date (recommended for most recurring tasks)
- from_completion: next date calculated from when you complete this occurrence; use when the gap between occurrences matters more than hitting specific calendar days. Caution with day-of-week patterns (onDays): from_completion skips same-day matches, resets biweekly/monthly grids from the completion date, and can dismiss early completions -- prefer regularly_with_catch_up for day-of-week schedules"""

BASED_ON_DOC = """\
Which date field anchors the repetition schedule. Other date fields shift relatively, preserving their current offset from the anchor.

Choose the date field the recurrence is 'about':
- due_date: deadline recurs (e.g. due every Friday)
- defer_date: availability recurs (e.g. becomes available every Monday)
- planned_date: intention recurs (e.g. plan for the same day each week)"""

# --- Class Docstrings: Repetition ---

ORDINAL_WEEKDAY_DOC = "Ordinal weekday pattern for monthly day-of-week patterns."

FREQUENCY_DOC = "How often the task repeats: type + interval, with optional day/date refinements."

END_BY_DATE_DOC = "End condition: repeat until a specific date."

END_BY_OCCURRENCES_DOC = "End condition: repeat a fixed number of times."

REPETITION_RULE_DOC = "Structured repetition rule for recurring tasks and projects."

# --- Class Docstrings: Actions ---

TAG_ACTION_DOC = """\
Tag operations for task editing.

Either ``replace`` (standalone) or ``add``/``remove`` (combinable). Incompatible modes are rejected."""

MOVE_ACTION_DOC = "Specify where to move a task. Exactly one key must be set."

MOVE_BEGINNING = """\
Container to move into (project name/ID, task name/ID, or '$inbox'). Task is placed at the beginning of the container."""

MOVE_ENDING = """\
Container to move into (project name/ID, task name/ID, or '$inbox'). Task is placed at the end of the container."""

MOVE_BEFORE = "Sibling task to position relative to (task name/ID). Parent container is inferred."

MOVE_AFTER = "Sibling task to position relative to (task name/ID). Parent container is inferred."

NOTE_ACTION_DOC = """\
Note operations for task editing.

Either ``append`` (add text on a new line) or ``replace`` (set entire note content). The two modes are mutually exclusive."""

NOTE_ACTION_APPEND = """\
Text to append to the existing note. Joined with a newline (\\n) separator; prepend your own \\n for a blank-line break. If the note is empty or whitespace-only, the text is set directly (no leading separator). Whitespace-only or empty text is a no-op (OmniFocus trims whitespace on write)."""

NOTE_ACTION_REPLACE = """\
Replace the entire note with this content. Pass null or '' to clear the note."""

EDIT_TASK_ACTIONS_DOC = "Lifecycle changes (complete/drop), tag edits, task movement, and note operations (append/replace). All four can be combined freely in one call."

LIFECYCLE_ACTION_DESC = (
    '"complete" = I did this task. "drop" = I\'m intentionally not doing this; '
    "the task stays in OmniFocus marked as dropped (not deleted). "
    "Repeating tasks: drop applies to the current occurrence only; next occurrence auto-created. "
    "Deletion and dropping an entire repeating series are intentionally not exposed."
)

# --- Class Docstrings: Repetition Specs ---

FREQUENCY_ADD_SPEC_DOC = "Frequency specification for creating a repetition rule."

FREQUENCY_EDIT_SPEC_DOC = "Patch individual frequency sub-fields; omit fields to leave unchanged."

REPETITION_RULE_ADD_SPEC_DOC = "All-required spec for creating a repetition rule on a new task."

REPETITION_RULE_EDIT_SPEC_DOC = (
    "Patch repetition rule fields; omit fields to leave unchanged, set to null to clear."
)

ORDINAL_WEEKDAY_SPEC_DOC = (
    "Ordinal weekday pattern for monthly day-of-week patterns (e.g. first monday, last friday)."
)

# --- Class Docstrings: Results and Queries ---

ADD_TASK_RESULT_DOC = "Outcome of task creation."

EDIT_TASK_RESULT_DOC = "Outcome of task editing."

LIST_RESULT_DOC = """\
Result container for list operations.

Includes optional warnings (e.g. name resolution ambiguity)."""

LIST_TASKS_QUERY_DOC = "Filter and paginate tasks."

LIST_PROJECTS_QUERY_DOC = "Filter and paginate projects."

LIST_TAGS_QUERY_DOC = "Filter and paginate tags."

LIST_FOLDERS_QUERY_DOC = "Filter and paginate folders."

LIST_PERSPECTIVES_QUERY_DOC = "Filter and paginate perspectives."

# --- Field Descriptions: Query Models ---

SEARCH_FIELD_NAME_NOTES = "Case-insensitive substring match on name and notes."

SEARCH_FIELD_NAME_ONLY = "Case-insensitive substring match on name."

# --- Field Descriptions: List Tool Filters ---

FLAGGED_FILTER_DESC = "true = flagged only, false = unflagged only, omit = skip filter."

IN_INBOX_FILTER_DESC = """\
true = Inbox tasks only (not assigned to a project), false = non-Inbox only, omit = skip filter."""

ESTIMATED_MINUTES_MAX_DESC = (
    "Include tasks with estimate <= this value (minutes). Tasks with no estimate are excluded."
)

LIMIT_DESC = "Max items to return. Pass null to return all. Tip: pass 0 for count only."

OFFSET_DESC = "Skip this many items. Requires limit to be set."

# --- Field Selection ---

INCLUDE_FIELD_DESC = """\
Add field groups to the response, on top of defaults. See tool description for available groups."""

ONLY_FIELD_DESC = """\
Return only these fields (plus id, always included). Mutually exclusive with include. Use case: targeted high-volume queries (prefer include for most use cases). Null/empty values are still stripped -- absent field means not set."""

REVIEW_DUE_WITHIN_DESC = f'Review due within this window. "now" or {_DURATION_FORMAT}'

# --- Field Descriptions: Entity-Reference Filters ---

PROJECT_FILTER_DESC = """\
Project ID or name. Names use case-insensitive substring matching -- if multiple projects match, tasks from all are included."""

PARENT_FILTER_DESC = """\
Task or project ID or name. Names use case-insensitive substring matching -- returns the resolved entity's full descendant subtree (tasks at any depth). If multiple entities match, their subtrees are unioned."""

TAGS_FILTER_DESC = "Tag names or IDs (OR logic). Names use case-insensitive substring matching."

FOLDER_FILTER_DESC = """\
Folder ID or name. Names use case-insensitive substring matching -- if multiple folders match, projects from all are included."""

# --- Perspectives: Temporary Notes ---

# TODO(v1.5): Remove when built-in perspectives are supported
_PERSPECTIVES_BUILTIN_NOTE = (
    "Currently returns custom perspectives only; built-in perspectives are not yet available."
)

# --- Tool Descriptions ---

GET_ALL_TOOL_DOC = f"""\
Return the full OmniFocus database as structured data.

WARNING: This is a last-resort/debugging tool. Prefer list_tasks or list_projects for filtered, paginated results. get_all returns the entire database and should only be used when you need a complete snapshot.

{_STRIPPING_NOTE}

Response contains: tasks, projects, tags, folders, perspectives arrays.
Each task includes an order field (dotted notation like '2.3.1') showing hierarchical position within its project or inbox."""

GET_TASK_TOOL_DOC = f"""\
Look up a single task by its ID.

{_STRIPPING_NOTE}

Fields: urgency, availability, dueDate, deferDate, plannedDate, inheritedDueDate, flagged, inheritedFlagged, hasNote, hasRepetition, hasAttachments, isSequential, dependsOnChildren, tags [{{id, name}}], parent (project {{id, name}} or task {{id, name}}), project {{id, name}}, order, repetitionRule.

order: hierarchical position in dotted notation (e.g. '2.3.1'). Null in degraded mode.

parent: direct container -- a project or parent task.
project: containing project at any nesting depth, or $inbox.

{_BEHAVIORAL_FLAGS_NOTE}

{_INHERITED_TASKS_EXPLANATION}"""

GET_PROJECT_TOOL_DOC = f"""\
Look up a single project by its ID.

$inbox is not a real project and cannot be looked up here. It has no review schedule, status, or other project properties. To query inbox tasks, use list_tasks with inInbox=true.

{_STRIPPING_NOTE}

Fields: urgency, availability, dueDate, deferDate, plannedDate, flagged, tags [{{id, name}}], isSequential, nextTask {{id, name}}, folder {{id, name}}, reviewInterval, nextReviewDate.

{_PROJECT_BEHAVIORAL_FLAGS_NOTE}

nextTask: first available (unblocked) task. Useful for identifying what to work on next."""

GET_TAG_TOOL_DOC = f"""\
Look up a single tag by its ID.

{_STRIPPING_NOTE}

Fields: availability, childrenAreMutuallyExclusive, parent {{id, name}}.

childrenAreMutuallyExclusive: when true, child tags behave like radio buttons."""

ADD_TASKS_TOOL_DOC = f"""\
Create tasks in OmniFocus.

Best-effort: all items are processed regardless of earlier failures. \
Each item gets its own status (success or error).

{_DATE_INPUT_NOTE_FULL}

{_TAGS_INPUT_NOTE}

repetitionRule requires all three root fields (frequency, schedule, basedOn) when creating. on and onDates within frequency are mutually exclusive.

Examples (repetitionRule):
  Every 3 days from completion:
    {{
      frequency: {{type: "daily", interval: 3}},
      schedule: "from_completion",
      basedOn: "defer_date"
    }}

  Every 2 weeks on Mon and Fri, stop after 10:
    {{
      frequency: {{
        type: "weekly",
        interval: 2,
        onDays: ["MO", "FR"]
      }},
      schedule: "regularly_with_catch_up",
      basedOn: "due_date",
      end: {{occurrences: 10}}
    }}

  Last Friday of every month:
    {{
      frequency: {{
        type: "monthly",
        on: {{"last": "friday"}}
      }},
      schedule: "regularly",
      basedOn: "due_date"
    }}

{_BATCH_CROSS_ITEM_NOTE}

{_BATCH_CONCURRENCY_NOTE}

{_BATCH_RETURNS}"""

LIST_TASKS_TOOL_DOC = f"""\
List and filter tasks. {_FILTERS_AND_LOGIC}

{_STRIPPING_NOTE}

include: optional array of field groups, additive on top of defaults.
  - "notes": note
  - "metadata": added, modified, completionDate (+inherited), dropDate (+inherited), url
  - "hierarchy": parent, hasChildren, type, completesWithChildren
  - "time": estimatedMinutes, repetitionRule
  - "*": all fields
Default fields: id, name, availability, order, project, dueDate, inheritedDueDate, deferDate, inheritedDeferDate, plannedDate, inheritedPlannedDate, flagged, inheritedFlagged, urgency, tags, hasNote, hasRepetition, hasAttachments, isSequential, dependsOnChildren.

{_BEHAVIORAL_FLAGS_NOTE}

{_COUNT_ONLY_TIP}

{_DATE_INPUT_NOTE}

Flat list; reconstruct hierarchy via order (dotted, e.g. '2.3.1') and project {{id, name}}. Filtered results may have sparse order (non-matching siblings omitted). Inbox tasks use project id="$inbox".

inherited* fields: OmniFocus's resolved value from the ancestor chain (parent task -> project -> folder). Resolution rules vary by field (dueDate=tightest, deferDate=latest, others=nearest). Read-only; to edit, set the direct field.

Response: {{items, total, hasMore, warnings?}}. Filters use inherited values.

{_LIFECYCLE_FILTER_NOTE}"""

LIST_PROJECTS_TOOL_DOC = f"""\
List and filter projects. {_FILTERS_AND_LOGIC}

{_STRIPPING_NOTE}

include: optional array of field groups, additive on top of defaults.
  - "notes": note
  - "metadata": added, modified, completionDate, dropDate, url
  - "hierarchy": folder, hasChildren, type, completesWithChildren
  - "time": estimatedMinutes, repetitionRule
  - "review": nextReviewDate, reviewInterval, lastReviewDate, nextTask
  - "*": all fields
Default fields (always returned): id, name, availability, dueDate, deferDate, plannedDate, flagged, urgency, tags, hasNote, hasRepetition, hasAttachments, isSequential.

{_PROJECT_BEHAVIORAL_FLAGS_NOTE}

dependsOnChildren is tasks-only (projects are always containers); projects expose the full type enum (incl. singleActions) via include=['hierarchy'].

{_COUNT_ONLY_TIP}

{_DATE_INPUT_NOTE}

Response: {{items, total, hasMore, warnings?}}

nextTask (in review group): first available (unblocked) task. Useful for identifying what to work on next.

{_LIFECYCLE_FILTER_NOTE}"""

LIST_TAGS_TOOL_DOC = f"""\
List and filter tags.

{_STRIPPING_NOTE}

Returns a flat list. Each tag includes a parent field {{id, name}} that can be used to reconstruct hierarchy.

Response: {{items, total, hasMore}}

Fields per tag: availability, childrenAreMutuallyExclusive, parent {{id, name}}.

childrenAreMutuallyExclusive: when true, child tags behave like radio buttons."""

LIST_FOLDERS_TOOL_DOC = f"""\
List and filter folders.

{_STRIPPING_NOTE}

Returns a flat list. Each folder includes a parent field {{id, name}} that can be used to reconstruct hierarchy.

Response: {{items, total, hasMore}}

Fields per folder: availability, parent {{id, name}}."""

LIST_PERSPECTIVES_TOOL_DOC = f"""\
List perspectives. {_PERSPECTIVES_BUILTIN_NOTE}

{_STRIPPING_NOTE}

Response: {{items, total, hasMore}}

Key fields per perspective: id, name."""

EDIT_TASKS_TOOL_DOC = f"""\
Edit existing tasks in OmniFocus using patch semantics.

Fail-fast: processing stops at the first error. Earlier items are committed; later items get status 'skipped' with a warning referencing the failed item.

{_DATE_INPUT_NOTE_FULL}

Patch: omit = no change, null = clear, value = update.

{_TAGS_INPUT_NOTE}

repetitionRule partial updates:
  - No existing rule: all root fields required (frequency, schedule, basedOn).
  - Has existing rule: omitted root fields preserved.
  - Same type: sub-fields preserved. Different type: full replacement.
  - frequency.type omittable (inferred) unless changing type.
  - on/onDates mutually exclusive. null clears the rule.

Examples (repetitionRule):
  Change interval: {{frequency: {{interval: 5}}}}
  Add days: {{frequency: {{onDays: ["MO", "WE", "FR"]}}}}
  Remove days: {{frequency: {{onDays: null}}}}
  Change type: {{frequency: {{type: "weekly", onDays: ["MO", "FR"]}}}}
  Clear: null

actions.move: one key (ending/beginning with '$inbox'/name/ID, or before/after).
actions.tags: replace (standalone) or add/remove (combinable).
actions.note: append or replace content (mutually exclusive).

{_BATCH_CROSS_ITEM_NOTE}

{_BATCH_CONCURRENCY_NOTE}

{_BATCH_RETURNS}"""
