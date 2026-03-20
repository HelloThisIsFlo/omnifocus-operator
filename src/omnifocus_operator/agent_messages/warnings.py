"""Consolidated warning strings for all agent-facing messages.

Every warning the OmniFocus Operator sends to agents is defined here.
This makes it easy to review, audit, and maintain the tone and content
of all agent-facing guidance in one place.

Parameterized warnings use {placeholder} syntax -- call .format() at the usage site.
"""

# --- Edit: Status ---

EDIT_COMPLETED_TASK = (
    "This task is {status} -- your changes were applied, "
    "but please confirm with the user that they intended to edit a {status} task."
)

# --- Edit: No-op ---

EDIT_NO_CHANGES_SPECIFIED = (
    "No changes specified -- if you intended to change fields, include them in the request"
)

EDIT_NO_CHANGES_DETECTED = (
    "No changes detected -- the task already has these values. "
    "If you don't want to change a field, omit it from the request."
)

# --- Move ---

MOVE_SAME_CONTAINER = (
    "Task is already in this container. OmniFocus API "
    "limitation: 'beginning'/'ending' moves within the "
    "same container does not change position.\n"
    "This will be fixed in a future release.\n"
    "Workaround: use 'before' or 'after' with a sibling "
    "task ID to control ordering within a container."
)

# --- Lifecycle ---

LIFECYCLE_ALREADY_IN_STATE = (
    "Task is already {state_word} -- nothing changed. Omit actions.lifecycle to skip."
)

LIFECYCLE_CROSS_STATE = (
    "Task was already {prior_state} -- lifecycle action applied, "
    "task is now {new_state}. Confirm with user that this was intended."
)

LIFECYCLE_REPEATING_COMPLETE = (
    "Repeating task -- this occurrence completed, next occurrence created."
)

LIFECYCLE_REPEATING_DROP = (
    "Repeating task \u2014 this occurrence was skipped, "
    "next occurrence created.\n"
    "If the user wanted to drop the entire repeating "
    "sequence, let them know this must be done in the "
    "OmniFocus UI (intentional restriction against "
    "destructive operations)."
)

LIFECYCLE_INVALID_VALUE = "Invalid lifecycle action '{value}' -- must be 'complete' or 'drop'"

# --- Validation ---

UNKNOWN_FIELD = "Unknown field '{field}'"

# --- Tags ---

TAGS_ALREADY_MATCH = "Tags already match the requested set -- no tag changes applied"

TAG_ALREADY_ON_TASK = "Tag '{display}' ({tag_id}) is already on this task"

TAG_NOT_ON_TASK = "Tag '{display}' ({tag_id}) is not on this task"
