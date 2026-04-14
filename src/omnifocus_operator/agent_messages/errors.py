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

# --- Batch Limit ---

ADD_TASKS_BATCH_LIMIT = "add_tasks currently accepts exactly 1 item, got {count}"

EDIT_TASKS_BATCH_LIMIT = "edit_tasks currently accepts exactly 1 item, got {count}"

# --- Validation Fallback ---

INVALID_INPUT = "Invalid input"

# --- Domain: Move ---

CIRCULAR_REFERENCE = "Cannot move task: would create circular reference"

NO_POSITION_KEY = "No position key set on move action"

# --- Validation: Lifecycle ---

LIFECYCLE_INVALID_VALUE = "Invalid lifecycle action '{value}' -- must be 'complete' or 'drop'"

# --- Validation: Unknown Field ---

UNKNOWN_FIELD = "Unknown field '{field}'"

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

MOVE_NULL_CONTAINER = (
    "{field} cannot be null. To move a task to the inbox, use '$inbox'. "
    "To move into a project or task, provide its name or ID."
)

MOVE_NULL_ANCHOR = (
    "{field} cannot be null. before/after positions require a task reference "
    "(name or ID). To move into a container, use 'beginning' or 'ending' instead."
)

# --- Validation: AddTaskCommand ---

ADD_PARENT_NULL = (
    "parent cannot be null. Omit the field to create a task in the inbox, "
    "or provide a project/task name or ID."
)

# --- Repetition Rule ---

REPETITION_NO_EXISTING_RULE = (
    "Cannot partially update a repetition rule -- this task has no existing rule. "
    "To set a repetition rule, provide all required fields: "
    "frequency (with type), schedule, and basedOn."
)

REPETITION_INVALID_DAY_CODE = (
    "Invalid day code '{code}' in onDays. Valid codes: MO, TU, WE, TH, FR, SA, SU"
)

REPETITION_AT_MOST_ONE_ORDINAL = (
    'on must specify exactly one ordinal (e.g. {{"last": "friday"}}), got {count} keys'
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

REPETITION_FIELD_WRONG_TYPE_WEEKLY = (
    "{field} is not valid for type '{type}'. {field} can only be used with type 'weekly'."
)

REPETITION_FIELD_WRONG_TYPE_MONTHLY = (
    "{field} is not valid for type '{type}'. {field} can only be used with type 'monthly'."
)

REPETITION_ON_AND_ON_DATES_EXCLUSIVE = (
    "on and on_dates are mutually exclusive on monthly frequency. "
    "Use on for day-of-week patterns (e.g., {{'second': 'tuesday'}}) "
    "or onDates for specific dates (e.g., [1, 15])."
)

REPETITION_INVALID_INTERVAL = "Interval must be >= 1 (got {value})"

REPETITION_INVALID_END_OCCURRENCES = "End occurrences must be >= 1 (got {value})"

REPETITION_INVALID_END_EMPTY = (
    "end requires either 'date' (ISO-8601 string) or 'occurrences' (integer >= 1)"
)

# --- Validation: Date Input ---

_DATE_FORMAT_EXAMPLES = (
    "ISO date ('2026-07-15'), ISO datetime ('2026-07-15T17:00:00'), "
    "or datetime with offset ('2026-07-15T17:00:00+01:00')"
)

INVALID_DATE_FORMAT = "Invalid date format '{value}'. Expected " + _DATE_FORMAT_EXAMPLES + "."

# --- Validation: Date Filters ---

DATE_FILTER_RANGE_EMPTY = (
    "Date range filter requires at least one of: before or after. "
    "Each accepts " + _DATE_FORMAT_EXAMPLES + ", or 'now'."
)

DATE_FILTER_INVALID_DURATION = (
    "Invalid duration '{value}' -- use a number followed by d/w/m/y (e.g. '3d', '2w', 'm'). "
    "Count defaults to 1 when omitted, so 'w' means '1w'."
)

REVIEW_DUE_WITHIN_INVALID = (
    "Invalid reviewDueWithin '{value}' -- "
    "valid formats: 'now', or a duration like '1w', '2m', '30d'. "
    "Count defaults to 1 when omitted, so 'w' means '1w'."
)

DATE_FILTER_ZERO_NEGATIVE = (
    "Duration count must be positive (got '{value}'). "
    "Use a positive number followed by d/w/m/y (e.g. '1d', '2w')."
)

DATE_FILTER_REVERSED_BOUNDS = (
    "Invalid date range: 'after' ({after}) is later than 'before' ({before}). "
    'Swap the values, or use a shorthand like {{"this": "d"}} for a single day.'
)

# --- Validation: List Filters ---

FILTER_NULL = "'{field}' cannot be null. To skip this filter, simply omit the field."

TAGS_EMPTY = "'{field}' cannot be empty. To ignore this filter, simply omit the field."

AVAILABILITY_EMPTY = "'{field}' cannot be empty -- include at least one status value, or use [\"ALL\"] for all statuses."

# --- Validation: List Query ---

OFFSET_REQUIRES_LIMIT = "offset requires limit -- set limit when using offset"

# --- Name Resolution ---

AMBIGUOUS_NAME_MATCH = (
    "Ambiguous {entity_type} '{name}': multiple matches: {matches}. "
    "Use the ID to specify which one."
)

NAME_NOT_FOUND = "No {entity_type} found matching '{name}'.{suggestions}"

RESERVED_PREFIX = (
    "'{value}' starts with '{prefix}' which is reserved for system locations. "
    "Valid system locations: {valid_locations}. "
    "If your entity name starts with '{prefix}', refer to it by ID instead."
)

# --- Filter: Contradictory Inbox ---

CONTRADICTORY_INBOX_FALSE = (
    "Contradictory filters: 'project=\"$inbox\"' selects inbox tasks, "
    "but 'inInbox=false' excludes them. Use one or the other."
)
CONTRADICTORY_INBOX_PROJECT = (
    "Contradictory filters: 'inInbox=true' selects tasks with no project. "
    "Combining with a 'project' filter always yields nothing. Use one or the other."
)

# --- Project Tool: Inbox Guard ---

GET_PROJECT_INBOX_ERROR = (
    "The '$inbox' appears as a project on tasks but is not a real OmniFocus project "
    "\u2014 it has no review schedule, status, or other project properties. "
    "To query inbox tasks, use list_tasks with 'inInbox=true'."
)

ENTITY_TYPE_MISMATCH = "'{value}' resolved to {resolved_type}, but only {accepted} is accepted here"

ENTITY_TYPE_MISMATCH_ANCHOR = (
    "'{value}' is a {resolved_type}. "
    "Anchor positions (before/after) require a task reference. "
    "To move into {value}, use 'ending' or 'beginning' instead."
)

DATE_INPUT_INVALID_TYPE = (
    "Input should be {shortcuts}, "
    'or a date filter like {{"this": "d"}}, {{"last": "3d"}}, {{"next": "2w"}}'
)

# --- Validation: Field Selection ---

INCLUDE_INVALID_TASK = (
    "Unknown field group(s): {groups}. Valid groups: notes, metadata, hierarchy, time, *"
)

INCLUDE_INVALID_PROJECT = (
    "Unknown field group(s): {groups}. Valid groups: notes, metadata, hierarchy, time, review, *"
)
