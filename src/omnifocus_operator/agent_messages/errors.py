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

# --- Validation: TagAction ---

TAG_REPLACE_WITH_ADD_REMOVE = (
    "Cannot use 'replace' with 'add' or 'remove' -- use either replace mode or add/remove mode"
)

TAG_NO_OPERATION = "tags must specify at least one of: add, remove, replace"

# --- Validation: MoveAction ---

MOVE_EXACTLY_ONE_KEY = "moveTo must have exactly one key (beginning, ending, before, or after)"

# --- Repetition Rule ---

REPETITION_TYPE_CHANGE_INCOMPLETE = (
    "Changing frequency type requires a complete frequency object for the new type. "
    "When switching types (e.g., daily -> weekly_on_days), provide all required fields "
    "for the new type -- omitted fields cannot be carried over from a different type."
)

REPETITION_NO_EXISTING_RULE = (
    "Cannot partially update a repetition rule on a task that has no existing rule. "
    "When creating a new repetition rule, provide all required fields: frequency, schedule, basedOn."
)
