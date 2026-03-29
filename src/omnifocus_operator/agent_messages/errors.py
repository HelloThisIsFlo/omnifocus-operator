"""Consolidated error strings for all agent-facing error messages.

Every ValueError message the OmniFocus Operator raises to agents is defined here.
This makes it easy to review, audit, and maintain the tone and content
of all agent-facing error responses in one place.

Parameterized errors use {placeholder} syntax -- call .format() at the usage site.
"""

# --- Lookup: Not Found ---

TASK_NOT_FOUND = "Task not found: {id}"

PROJECT_NOT_FOUND = "Project not found: {id}"

TAG_NOT_FOUND = "Tag not found: {name}"

PARENT_NOT_FOUND = "Parent not found: {id}"

ANCHOR_TASK_NOT_FOUND = "Anchor task not found: {id}"

# --- Lookup: Ambiguous ---

AMBIGUOUS_TAG = "Ambiguous tag '{name}': multiple matches ({ids})"

# --- Batch Limit ---

ADD_TASKS_BATCH_LIMIT = "add_tasks currently accepts exactly 1 item, got {count}"

EDIT_TASKS_BATCH_LIMIT = "edit_tasks currently accepts exactly 1 item, got {count}"

# --- Validation Fallback ---

INVALID_INPUT = "Invalid input"

# --- Domain: Move ---

CIRCULAR_REFERENCE = "Cannot move task: would create circular reference"

NO_POSITION_KEY = "No position key set on move action"

# --- Validation: Task Name ---

TASK_NAME_REQUIRED = "Task name is required"

TASK_NAME_EMPTY = "Task name cannot be empty"

# --- Validation: TagAction ---

TAG_REPLACE_WITH_ADD_REMOVE = (
    "Cannot use 'replace' with 'add' or 'remove' -- use either replace mode or add/remove mode"
)

TAG_NO_OPERATION = "tags must specify at least one of: add, remove, replace"

# --- Validation: MoveAction ---

MOVE_EXACTLY_ONE_KEY = "moveTo must have exactly one key (beginning, ending, before, or after)"

# --- Repetition Rule ---

REPETITION_NO_EXISTING_RULE = (
    "Cannot partially update a repetition rule -- this task has no existing rule. "
    "To set a repetition rule, provide all required fields: "
    "frequency (with type), schedule, and basedOn."
)

REPETITION_INVALID_DAY_CODE = (
    "Invalid day code '{code}' in onDays. Valid codes: MO, TU, WE, TH, FR, SA, SU"
)

REPETITION_INVALID_ORDINAL = (
    "Invalid ordinal '{ordinal}' in on field. "
    "Valid ordinals: first, second, third, fourth, fifth, last"
)

REPETITION_INVALID_DAY_NAME = (
    "Invalid day name '{day}' in on field. "
    "Valid days: monday, tuesday, wednesday, thursday, friday, "
    "saturday, sunday, weekday, weekend_day"
)

REPETITION_INVALID_ON_DATE = (
    "Invalid date value {value} in onDates. Valid range: -1, 1 to 31 (use -1 for last day of month)"
)

REPETITION_INVALID_FREQUENCY_TYPE = (
    "Invalid frequency type '{freq_type}' -- "
    "valid types: minutely, hourly, daily, weekly, monthly, yearly"
)

REPETITION_INVALID_INTERVAL = "Interval must be >= 1 (got {value})"

REPETITION_INVALID_END_OCCURRENCES = "End occurrences must be >= 1 (got {value})"

REPETITION_INVALID_END_EMPTY = (
    "end requires either 'date' (ISO-8601 string) or 'occurrences' (integer >= 1)"
)
