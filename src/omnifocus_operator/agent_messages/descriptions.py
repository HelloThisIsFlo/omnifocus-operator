"""Consolidated description strings for all agent-facing field and class descriptions.

Every Field(description=...) string and agent-visible class docstring is defined here.
This makes it easy to review, audit, and maintain all agent-facing schema text
in one place.

Field descriptions are static text -- no parameterized strings needed.
"""

# --- Dates: Read-Side ---

DUE_DATE = "Deadline with real consequences if missed."

DEFER_DATE = (
    "Task cannot be acted on until this date; hidden from most views until then."
)

PLANNED_DATE = (
    "When the user intends to work on this. "
    "No urgency signal, no penalty for missing it."
)

EFFECTIVE_FLAGGED = (
    "Inherited from parent project if not set directly on this task."
)

EFFECTIVE_DUE_DATE = (
    "Inherited from parent project or task if not set directly on this entity."
)

EFFECTIVE_DEFER_DATE = (
    "Inherited from parent project or task if not set directly on this entity."
)

EFFECTIVE_PLANNED_DATE = (
    "Inherited from parent project or task if not set directly on this entity."
)

EFFECTIVE_DROP_DATE = (
    "Inherited from parent project or task if not set directly on this entity."
)

EFFECTIVE_COMPLETION_DATE = (
    "Inherited from parent project or task if not set directly on this task."
)

# --- Dates: Write-Side ---

DUE_DATE_WRITE = (
    "Deadline with real consequences if missed. "
    "Not for intentions -- use plannedDate instead. "
    "Requires timezone (ISO 8601 with offset or Z); naive datetimes are rejected."
)

DEFER_DATE_WRITE = (
    "Task cannot be acted on until this date. "
    "Hidden from most views until then. "
    "Not for 'I don't want to work on it yet' -- use plannedDate for that. "
    "Requires timezone (ISO 8601 with offset or Z); naive datetimes are rejected."
)

PLANNED_DATE_WRITE = (
    "When you intend to work on this task. "
    "No urgency signal, no visibility change, no penalty for missing it. "
    "Requires timezone (ISO 8601 with offset or Z); naive datetimes are rejected."
)

# --- Tags ---

TAGS_ADD_COMMAND = (
    "Tag names (case-insensitive) or IDs; you can mix both in one list. "
    "Non-existent names are rejected. "
    "Ambiguous names (case-insensitive collision) return an error."
)

TAGS_OUTPUT = "Tags applied to this entity, each with id and name."

TAG_ACTION_ADD = (
    "Tag names (case-insensitive) or IDs to add; you can mix both. "
    "Non-existent names are rejected. Ambiguous names return an error."
)

TAG_ACTION_REMOVE = (
    "Tag names (case-insensitive) or IDs to remove; you can mix both. "
    "Non-existent names are rejected. Ambiguous names return an error."
)

TAG_ACTION_REPLACE = (
    "Replace all tags with this list. Tag names (case-insensitive) or IDs; "
    "you can mix both. Non-existent names are rejected. Ambiguous names return an error. "
    "Pass null or [] to clear all tags."
)

CHILDREN_ARE_MUTUALLY_EXCLUSIVE = (
    "When true, child tags behave like radio buttons "
    "-- assigning one removes siblings."
)

# --- Repetition ---

ON_DAYS = "Days of the week for weekly recurrence."

ON_DATE = "Days of the month. Use -1 for last day."

END_BY_DATE_DATE = "Repeat until this date."

# --- Entities ---

PARENT = "Project or task ID to place this task under. Omit for inbox."

NEXT_TASK = "ID of the first available task in this project, if any."

# --- Class Docstrings: Entities ---

TAG_REF_DOC = "Reference to a tag with both id and name for ergonomics."

PARENT_REF_DOC = (
    "Reference to a parent entity (project or task) with type, id, and name.\n"
    "\n"
    'type is "project" for tasks directly in a project, "task" for subtasks.\n'
    "Inbox tasks have no ParentRef (represented as None at the Task level)."
)

REVIEW_INTERVAL_DOC = "Review interval for project review scheduling."

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

SCHEDULE_DOC = "Repetition schedule type."

BASED_ON_DOC = "Anchor date for repetition rules."

# --- Class Docstrings: Repetition ---

ORDINAL_WEEKDAY_DOC = (
    "Typed ordinal-weekday model for monthly day-of-week patterns."
)

FREQUENCY_DOC = (
    "How often the task repeats: type + interval, with optional day/date refinements."
)

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

EDIT_TASK_ACTIONS_DOC = "Stateful operations grouped under the actions block."

# --- Class Docstrings: Repetition Specs ---

FREQUENCY_ADD_SPEC_DOC = "Frequency specification for creating a repetition rule."

FREQUENCY_EDIT_SPEC_DOC = (
    "Patch individual frequency sub-fields; omit fields to leave unchanged."
)

REPETITION_RULE_ADD_SPEC_DOC = (
    "All-required spec for creating a repetition rule on a new task."
)

REPETITION_RULE_EDIT_SPEC_DOC = (
    "Patch repetition rule fields; omit fields to leave unchanged, set to null to clear."
)

ORDINAL_WEEKDAY_SPEC_DOC = (
    "Write-side ordinal-weekday model for monthly day-of-week patterns."
)

# --- Class Docstrings: Results and Queries ---

ADD_TASK_RESULT_DOC = "Agent-facing outcome of task creation."

EDIT_TASK_RESULT_DOC = "Agent-facing outcome of task editing."

LIST_RESULT_DOC = (
    "Agent-facing result container for all list operations.\n"
    "\n"
    "Includes optional warnings for agent guidance (e.g. name resolution ambiguity)."
)

LIST_TASKS_QUERY_DOC = (
    "Agent-facing: validated filter + pagination for task listing."
)

LIST_PROJECTS_QUERY_DOC = (
    "Agent-facing: validated filter + pagination for project listing."
)

LIST_TAGS_QUERY_DOC = (
    "Agent-facing: validated filter for tag listing. No pagination."
)

LIST_FOLDERS_QUERY_DOC = (
    "Agent-facing: validated filter for folder listing. No pagination."
)

DURATION_UNIT_DOC = "Unit for duration-based filters."

REVIEW_DUE_FILTER_DOC = "Parsed duration for review_due_within filter."
