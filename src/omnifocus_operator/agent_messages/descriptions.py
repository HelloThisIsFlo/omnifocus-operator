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

EFFECTIVE_FLAGGED = "Inherited from parent project if not set directly on this task."

EFFECTIVE_DUE_DATE = "Inherited from parent project or task if not set directly on this entity."

EFFECTIVE_DEFER_DATE = "Inherited from parent project or task if not set directly on this entity."

EFFECTIVE_PLANNED_DATE = "Inherited from parent project or task if not set directly on this entity."

EFFECTIVE_DROP_DATE = "Inherited from parent project or task if not set directly on this entity."

EFFECTIVE_COMPLETION_DATE = (
    "Inherited from parent project or task if not set directly on this task."
)

# --- Dates: Write-Side ---

DATE_EXAMPLE = "2026-03-15T17:00:00Z"

DUE_DATE_WRITE = (
    "Deadline with real consequences if missed. Not for intentions -- use plannedDate instead."
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

# --- Tags ---

TAGS_ADD_COMMAND = "Tag names (case-insensitive) or IDs; you can mix both."

TAGS_OUTPUT = "Tags applied to this entity, each with id and name."

TAG_ACTION_ADD = "Tag names (case-insensitive) or IDs to add; you can mix both."

TAG_ACTION_REMOVE = "Tag names (case-insensitive) or IDs to remove; you can mix both."

TAG_ACTION_REPLACE = (
    "Replace all tags with this list. Tag names (case-insensitive) or IDs; "
    "you can mix both. Pass null or [] to clear all tags."
)

CHILDREN_ARE_MUTUALLY_EXCLUSIVE = (
    "When true, child tags behave like radio buttons -- assigning one removes siblings."
)

# --- Repetition ---

ON_DAYS = (
    "Days of the week for weekly recurrence. "
    "Only valid when type is 'weekly'; rejected for other types."
)

ON_DATE = (
    "Days of the month. Valid values: -1 (last day of month), 1-31. "
    "Mutually exclusive with on (day-of-week patterns)."
)

ON_WEEKDAY_PATTERN = (
    "Ordinal weekday pattern for monthly recurrence (e.g. last friday). "
    "Optional -- omit to repeat on the calendar date. "
    "Mutually exclusive with onDates."
)

END_BY_DATE_DATE = "Repeat until this date."

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

NOTE_EDIT_COMMAND = "Plain-text note. Set to null to clear."

ID_EDIT_COMMAND = "OmniFocus task ID to edit."

FLAGGED_EDIT_COMMAND = "Mark task for priority attention. Surfaces in Flagged perspective."

ESTIMATED_MINUTES_EDIT = "Time estimate in minutes. Set to null to clear."

# --- Date Filter Models ---

DATE_FILTER_DOC = (
    "Date range filter. Use a shorthand period (this/last/next with a duration like '3d', 'w', '2m') "
    "or absolute bounds (before/after with ISO dates or 'now'). "
    "Cannot mix shorthand and absolute in the same filter."
)

DUE_DATE_SHORTCUT_DOC = "Shortcut for filtering by due date: overdue, soon, or today."

LIFECYCLE_DATE_SHORTCUT_DOC = (
    "Shortcut for filtering by lifecycle date: all (every task in that state) or today."
)

DUE_FILTER_DESC = (
    'Filter by due date. String shortcut ("overdue", "soon", "today") '
    "or DateFilter object. 'overdue' = due before now. "
    "'soon' = due within your OmniFocus due-soon threshold."
)

COMPLETED_FILTER_DESC = (
    'Filter by completion date. "any" includes all completed tasks regardless of date. '
    '"today" filters to completed today. Or use a DateFilter object for a custom range.'
)

DROPPED_FILTER_DESC = (
    'Filter by drop date. "any" includes all dropped tasks regardless of date. '
    '"today" filters to dropped today. Or use a DateFilter object for a custom range.'
)

DEFER_FILTER_DESC = (
    'Filter by defer date. "today" matches tasks deferred to today. '
    "Or use a DateFilter object for a custom range."
)

PLANNED_FILTER_DESC = (
    'Filter by planned date. "today" matches tasks planned for today. '
    "Or use a DateFilter object for a custom range."
)

ADDED_FILTER_DESC = (
    'Filter by date added. "today" matches tasks added today. '
    "Or use a DateFilter object for a custom range."
)

MODIFIED_FILTER_DESC = (
    'Filter by date modified. "today" matches tasks modified today. '
    "Or use a DateFilter object for a custom range."
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

AVAILABILITY_DOC = (
    "Which lifecycle states to include. "
    "'remaining' (default) = available + blocked. "
    "Empty list [] = no remaining tasks (combine with completed/dropped filters for lifecycle-only results). "
    "Completed/dropped tasks are included via their own date filters, not here."
)

TAG_AVAILABILITY_DOC = (
    "Is this tag active? "
    "blocked = on hold, always blocks tagged tasks. "
    "dropped = hidden from hierarchy, blocks tasks only if their sole tag."
)

FOLDER_AVAILABILITY_DOC = "Is this folder active?"

# Edge cases (INTERVAL≥2, early completion, same-day eligibility) differ between modes.
# See docs/byday-edge-cases.md for the full breakdown.
SCHEDULE_DOC = (
    "Repetition schedule type.\n\n"
    "- regularly: fixed calendar dates; if late, "
    "past occurrences must be completed one by one\n"
    "- regularly_with_catch_up: fixed calendar dates, "
    "but skips overdue to next future date "
    "(recommended for most recurring tasks)\n"
    "- from_completion: next date calculated from when "
    "you complete this occurrence; use when the gap "
    "between occurrences matters more than hitting "
    "specific calendar days. "
    "Caution with day-of-week patterns (onDays): "
    "from_completion skips same-day matches, resets "
    "biweekly/monthly grids from the completion date, "
    "and can dismiss early completions -- prefer "
    "regularly_with_catch_up for day-of-week schedules"
)

BASED_ON_DOC = (
    "Which date field anchors the repetition schedule. "
    "Other date fields shift relatively, preserving their "
    "current offset from the anchor.\n\n"
    "Choose the date field the recurrence is 'about':\n"
    "- due_date: deadline recurs (e.g. due every Friday)\n"
    "- defer_date: availability recurs (e.g. becomes available every Monday)\n"
    "- planned_date: intention recurs (e.g. plan for the same day each week)"
)

# --- Class Docstrings: Repetition ---

ORDINAL_WEEKDAY_DOC = "Ordinal weekday pattern for monthly day-of-week patterns."

FREQUENCY_DOC = "How often the task repeats: type + interval, with optional day/date refinements."

END_BY_DATE_DOC = "End condition: repeat until a specific date."

END_BY_OCCURRENCES_DOC = "End condition: repeat a fixed number of times."

REPETITION_RULE_DOC = "Structured repetition rule for recurring tasks and projects."

# --- Class Docstrings: Actions ---

TAG_ACTION_DOC = (
    "Tag operations for task editing.\n"
    "\n"
    "Either ``replace`` (standalone) or ``add``/``remove`` (combinable).\n"
    "Incompatible modes are rejected."
)

MOVE_ACTION_DOC = "Specify where to move a task. Exactly one key must be set."

MOVE_BEGINNING = (
    "Container to move into (project name/ID, task name/ID, or '$inbox'). "
    "Task is placed at the beginning of the container."
)

MOVE_ENDING = (
    "Container to move into (project name/ID, task name/ID, or '$inbox'). "
    "Task is placed at the end of the container."
)

MOVE_BEFORE = "Sibling task to position relative to (task name/ID). Parent container is inferred."

MOVE_AFTER = "Sibling task to position relative to (task name/ID). Parent container is inferred."

EDIT_TASK_ACTIONS_DOC = "Lifecycle changes (complete/drop), tag edits, and task movement. All three can be combined freely in one call."

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

LIST_RESULT_DOC = (
    "Result container for list operations.\n"
    "\n"
    "Includes optional warnings (e.g. name resolution ambiguity)."
)

LIST_TASKS_QUERY_DOC = "Filter and paginate tasks."

LIST_PROJECTS_QUERY_DOC = "Filter and paginate projects."

LIST_TAGS_QUERY_DOC = "Filter and paginate tags."

LIST_FOLDERS_QUERY_DOC = "Filter and paginate folders."

LIST_PERSPECTIVES_QUERY_DOC = "Filter and paginate perspectives."

DURATION_UNIT_DOC = "Unit for duration-based filters."

REVIEW_DUE_FILTER_DOC = "Duration threshold for the review_due_within filter."

# --- Field Descriptions: Query Models ---

SEARCH_FIELD_NAME_NOTES = "Case-insensitive substring match on name and notes."

SEARCH_FIELD_NAME_ONLY = "Case-insensitive substring match on name."

# --- Field Descriptions: List Tool Filters ---

FLAGGED_FILTER_DESC = "true = flagged only, false = unflagged only, omit = skip filter."

IN_INBOX_FILTER_DESC = (
    "true = Inbox tasks only (not assigned to a project), "
    "false = non-Inbox only, omit = skip filter."
)

ESTIMATED_MINUTES_MAX_DESC = (
    "Include tasks with estimate <= this value (minutes). Tasks with no estimate are excluded."
)

LIMIT_DESC = "Max items to return. Pass null to return all."

OFFSET_DESC = "Skip this many items. Requires limit to be set."

REVIEW_DUE_WITHIN_DESC = (
    'Review due within this window. "now" or "N<unit>" (unit: d/w/m/y). Examples: "1w", "2m".'
)

# --- Field Descriptions: Entity-Reference Filters ---

PROJECT_FILTER_DESC = (
    "Project ID or name. Names use case-insensitive substring matching -- "
    "if multiple projects match, tasks from all are included."
)

TAGS_FILTER_DESC = "Tag names or IDs (OR logic). Names use case-insensitive substring matching."

FOLDER_FILTER_DESC = (
    "Folder ID or name. Names use case-insensitive substring matching -- "
    "if multiple folders match, projects from all are included."
)

# --- Perspectives: Temporary Notes ---

# TODO(v1.5): Remove when built-in perspectives are supported
_PERSPECTIVES_BUILTIN_NOTE = (
    "Currently returns custom perspectives only; built-in perspectives are not yet available."
)

# --- Tool Descriptions ---

GET_ALL_TOOL_DOC = (
    "Return the full OmniFocus database as structured data.\n"
    "\n"
    "WARNING: This is a last-resort/debugging tool. Prefer list_tasks or\n"
    "list_projects for filtered, paginated results. get_all returns the\n"
    "entire database and should only be used when you need a complete\n"
    "snapshot.\n"
    "\n"
    "Response contains: tasks, projects, tags, folders, perspectives arrays.\n"
    "The response uses camelCase field names."
)

GET_TASK_TOOL_DOC = (
    "Look up a single task by its ID.\n"
    "\n"
    "Fields: urgency, availability, dueDate, deferDate, plannedDate, "
    "effectiveDueDate, flagged, effectiveFlagged, "
    "tags [{id, name}], parent (project {id, name} or task {id, name}), "
    "project {id, name}, repetitionRule.\n"
    "\n"
    "parent: direct container — a project or parent task.\n"
    "project: containing project at any nesting depth, or $inbox.\n"
    "effective*: inherited from the parent hierarchy when not set directly."
)

GET_PROJECT_TOOL_DOC = (
    "Look up a single project by its ID.\n"
    "\n"
    "$inbox is not a real project and cannot be looked up here \u2014 "
    "it has no review schedule, status, or other project properties. "
    "To query inbox tasks, use list_tasks with inInbox=true.\n"
    "\n"
    "Fields: urgency, availability, dueDate, deferDate, plannedDate, "
    "effectiveDueDate, flagged, effectiveFlagged, "
    "tags [{id, name}], nextTask {id, name}, folder {id, name}, "
    "reviewInterval, nextReviewDate.\n"
    "\n"
    "nextTask: first available (unblocked) task \u2014 useful for identifying what to work on next.\n"
    "effective*: inherited from the parent hierarchy when not set directly."
)

GET_TAG_TOOL_DOC = (
    "Look up a single tag by its ID.\n"
    "\n"
    "Fields: availability, childrenAreMutuallyExclusive, parent {id, name}.\n"
    "\n"
    "childrenAreMutuallyExclusive: when true, child tags behave like radio buttons."
)

ADD_TASKS_TOOL_DOC = (
    "Create tasks in OmniFocus. Limited to 1 item per call.\n"
    "\n"
    "Tags accept names (case-insensitive) or IDs; you can mix both.\n"
    "Non-existent names are rejected. Ambiguous names (case-insensitive\n"
    "collision) return an error.\n"
    "\n"
    "repetitionRule requires all three root fields (frequency, schedule,\n"
    "basedOn) when creating. on and onDates within frequency are\n"
    "mutually exclusive.\n"
    "\n"
    "Examples (repetitionRule):\n"
    "  Every 3 days from completion:\n"
    "    {\n"
    '      frequency: {type: "daily", interval: 3},\n'
    '      schedule: "from_completion",\n'
    '      basedOn: "defer_date"\n'
    "    }\n"
    "\n"
    "  Every 2 weeks on Mon and Fri, stop after 10:\n"
    "    {\n"
    "      frequency: {\n"
    '        type: "weekly",\n'
    "        interval: 2,\n"
    '        onDays: ["MO", "FR"]\n'
    "      },\n"
    '      schedule: "regularly_with_catch_up",\n'
    '      basedOn: "due_date",\n'
    "      end: {occurrences: 10}\n"
    "    }\n"
    "\n"
    "  Last Friday of every month:\n"
    "    {\n"
    "      frequency: {\n"
    '        type: "monthly",\n'
    '        on: {"last": "friday"}\n'
    "      },\n"
    '      schedule: "regularly",\n'
    '      basedOn: "due_date"\n'
    "    }\n"
    "\n"
    "\n"
    "Returns: [{success, id, name, warnings?}]"
)

LIST_TASKS_TOOL_DOC = (
    "List and filter tasks. All filters combine with AND logic.\n"
    "\n"
    "Returns a flat list. Reconstruct hierarchy using parent (direct container) "
    "or project (containing project at any depth). "
    "For root tasks both point to the same project; for subtasks they diverge. "
    'Inbox tasks use project id="$inbox".\n'
    "\n"
    "Response: {items, total, hasMore, warnings?}\n"
    "\n"
    "Fields per task: urgency, availability, flagged, effectiveFlagged, "
    "dueDate, deferDate, plannedDate, effectiveDueDate, effectiveDeferDate, "
    "estimatedMinutes, tags [{id, name}], "
    "parent (project {id, name} or task {id, name}), "
    "project {id, name}, hasChildren, repetitionRule, completionDate.\n"
    "\n"
    "parent: direct container — a project or parent task.\n"
    "project: containing project at any nesting depth, or $inbox.\n"
    "effective*: inherited from the parent hierarchy when not set directly."
)

LIST_PROJECTS_TOOL_DOC = (
    "List and filter projects. All filters combine with AND logic.\n"
    "\n"
    "Response: {items, total, hasMore, warnings?}\n"
    "\n"
    "Fields per project: urgency, availability, flagged, effectiveFlagged, "
    "dueDate, deferDate, plannedDate, effectiveDueDate, "
    "tags [{id, name}], folder {id, name}, nextTask {id, name}, "
    "reviewInterval, nextReviewDate, hasChildren, repetitionRule, completionDate.\n"
    "\n"
    "nextTask: first available (unblocked) task — useful for identifying what to work on next.\n"
    "effective*: inherited from the parent hierarchy when not set directly."
)

LIST_TAGS_TOOL_DOC = (
    "List and filter tags.\n"
    "\n"
    "Returns a flat list. Each tag includes a parent field {id, name} "
    "that can be used to reconstruct hierarchy.\n"
    "\n"
    "Response: {items, total, hasMore}\n"
    "\n"
    "Fields per tag: availability, childrenAreMutuallyExclusive, parent {id, name}.\n"
    "\n"
    "childrenAreMutuallyExclusive: when true, child tags behave like radio buttons."
)

LIST_FOLDERS_TOOL_DOC = (
    "List and filter folders.\n"
    "\n"
    "Returns a flat list. Each folder includes a parent field {id, name} "
    "that can be used to reconstruct hierarchy.\n"
    "\n"
    "Response: {items, total, hasMore}\n"
    "\n"
    "Fields per folder: availability, parent {id, name}."
)

LIST_PERSPECTIVES_TOOL_DOC = (
    f"List perspectives. {_PERSPECTIVES_BUILTIN_NOTE}\n"
    "\n"
    "Response: {items, total, hasMore}\n"
    "\n"
    "Key fields per perspective: id, name.\n"
    "The response uses camelCase field names."
)

EDIT_TASKS_TOOL_DOC = (
    "Edit existing tasks in OmniFocus using patch semantics. Max 1 item per call.\n"
    "\n"
    "Patch: omit = no change, null = clear, value = update.\n"
    "\n"
    "Tags (in all tag fields) accept names (case-insensitive) or IDs;\n"
    "you can mix both. Non-existent names are rejected. Ambiguous names\n"
    "(case-insensitive collision) return an error.\n"
    "\n"
    "repetitionRule partial updates:\n"
    "  - Task has no existing rule: all three root fields required\n"
    "    (frequency, schedule, basedOn) -- same as creation.\n"
    "  - Task has existing rule: omitted root fields are preserved.\n"
    "  - frequency.type can be omitted (inferred from existing rule)\n"
    "    unless changing to a different type.\n"
    "  - Same type: omitted frequency sub-fields preserved.\n"
    "  - Different type: full replacement with creation defaults.\n"
    "  - on and onDates are mutually exclusive -- setting one clears\n"
    "    the other.\n"
    "  - null clears the entire repetition rule.\n"
    "\n"
    "Examples (repetitionRule):\n"
    "  Change just the interval (type inferred from existing):\n"
    "    {frequency: {interval: 5}}\n"
    "\n"
    "  Add specific days to a weekly task (no type change):\n"
    '    {frequency: {onDays: ["MO", "WE", "FR"]}}\n'
    "\n"
    "  Remove day constraint from weekly:\n"
    "    {frequency: {onDays: null}}\n"
    "\n"
    "  Switch monthly from dates to weekday pattern (onDates auto-cleared):\n"
    '    {frequency: {on: {"last": "friday"}}}\n'
    "\n"
    "  Change from daily to weekly (type required):\n"
    '    {frequency: {type: "weekly", onDays: ["MO", "FR"]}}\n'
    "\n"
    "  Clear:\n"
    "    null\n"
    "\n"
    "actions.move: exactly one key must be set. Use ending/beginning with\n"
    "'$inbox' to move to inbox, or a project/task name or ID.\n"
    "\n"
    "actions.lifecycle:\n"
    '  - "complete": marks the task as complete.\n'
    '  - "drop": skips/cancels the task without completing it.\n'
    "  On repeating tasks, both actions apply to the current occurrence\n"
    "  only -- the next occurrence is automatically created. Dropping an\n"
    "  entire repeating sequence is not supported via this API.\n"
    "\n"
    "actions.tags: replace is standalone. add/remove are combinable with\n"
    "each other but not with replace.\n"
    "\n"
    "\n"
    "Returns: [{success, id, name, warnings?}]"
)
