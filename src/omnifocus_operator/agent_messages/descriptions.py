"""Consolidated description strings for all agent-facing field and class descriptions.

Every Field(description=...) string and agent-visible class docstring is defined here.
This makes it easy to review, audit, and maintain all agent-facing schema text
in one place.

Field descriptions are static text -- no parameterized strings needed.
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

NEXT_TASK = "ID of the first available task in this project, if any."

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

# --- Class Docstrings: Entities ---

TAG_REF_DOC = "Reference to a tag with both id and name."

PARENT_REF_DOC = (
    "Reference to a parent entity (project or task) with type, id, and name.\n"
    "\n"
    'type is "project" for tasks directly in a project, "task" for subtasks.\n'
    "Inbox tasks have no ParentRef (represented as None at the Task level)."
)

REVIEW_INTERVAL_DOC = "How often OmniFocus prompts the user to review this project."

TASK_DOC = "A single OmniFocus task with all fields."

PROJECT_DOC = "A single OmniFocus project with all fields."

TAG_DOC = "A single OmniFocus tag with all fields."

FOLDER_DOC = "A single OmniFocus folder with all fields."

PERSPECTIVE_DOC = "A single OmniFocus perspective."

ALL_ENTITIES_DOC = "All OmniFocus entities from a repository."

# --- Class Docstrings: Enums ---

URGENCY_DOC = "Time pressure axis -- is this task/project pressing?"

AVAILABILITY_DOC = "Work readiness axis -- can this be worked on?"

TAG_AVAILABILITY_DOC = "Availability status for tags."

FOLDER_AVAILABILITY_DOC = "Availability status for folders."

# Edge cases (INTERVAL≥2, early completion, time anchoring) differ between modes.
# See docs/omnifocus-concepts.md "Schedule (Recurrence Mode)" for full details.
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
    "specific calendar days"
)

BASED_ON_DOC = (
    "Which date field anchors the repetition schedule. "
    "Other date fields shift relatively, preserving their "
    "current offset from the anchor.\n\n"
    "- due_date: schedule based on due date\n"
    "- defer_date: schedule based on defer date\n"
    "- planned_date: schedule based on planned date"
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

MOVE_ACTION_DOC = (
    "Specifies where to move a task.\n"
    "\n"
    "Exactly one key must be set. The key doubles as both the position\n"
    "and the reference point:\n"
    "\n"
    "- ``beginning``/``ending``: ID of the container (project or task),\n"
    "  or ``null`` for inbox.\n"
    "- ``before``/``after``: ID of a sibling task (parent is inferred)."
)

EDIT_TASK_ACTIONS_DOC = "Lifecycle changes (complete/drop), tag edits, and task movement."

# --- Class Docstrings: Repetition Specs ---

FREQUENCY_ADD_SPEC_DOC = "Frequency specification for creating a repetition rule."

FREQUENCY_EDIT_SPEC_DOC = "Patch individual frequency sub-fields; omit fields to leave unchanged."

REPETITION_RULE_ADD_SPEC_DOC = "All-required spec for creating a repetition rule on a new task."

REPETITION_RULE_EDIT_SPEC_DOC = (
    "Patch repetition rule fields; omit fields to leave unchanged, set to null to clear."
)

ORDINAL_WEEKDAY_SPEC_DOC = "Ordinal weekday pattern for monthly day-of-week patterns (e.g. first monday, last friday)."

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

LIST_TAGS_QUERY_DOC = "Filter tags."

LIST_FOLDERS_QUERY_DOC = "Filter folders."

LIST_PERSPECTIVES_QUERY_DOC = "Filter perspectives."

DURATION_UNIT_DOC = "Unit for duration-based filters."

REVIEW_DUE_FILTER_DOC = "Duration threshold for the review_due_within filter."

# --- Field Descriptions: Query Models ---

SEARCH_FIELD_NAME_NOTES = "Case-insensitive substring match on name and notes."

SEARCH_FIELD_NAME_ONLY = "Case-insensitive substring match on name."

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
    "Key fields: urgency, availability, dueDate, deferDate, plannedDate,\n"
    "effectiveDueDate (inherited from parent), flagged, effectiveFlagged,\n"
    "tags (array of {id, name}), parent ({type, id, name} or null for inbox),\n"
    "repetitionRule, inInbox.\n"
    "The response uses camelCase field names."
)

GET_PROJECT_TOOL_DOC = (
    "Look up a single project by its ID.\n"
    "\n"
    "Key fields: urgency, availability, dueDate, deferDate, plannedDate,\n"
    "effectiveDueDate (inherited from parent), flagged, effectiveFlagged,\n"
    "tags (array of {id, name}), nextTask (ID of first available task),\n"
    "folder (name or null), reviewInterval, nextReviewDate.\n"
    "The response uses camelCase field names."
)

GET_TAG_TOOL_DOC = (
    "Look up a single tag by its ID.\n"
    "\n"
    "Key fields: availability, childrenAreMutuallyExclusive (child tags\n"
    "behave like radio buttons when true), parent (parent tag name or null).\n"
    "The response uses camelCase field names."
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
    '      schedule: "regularly",\n'
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
    "actions.move: exactly one key must be set. ending/beginning with\n"
    "null moves to inbox.\n"
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
