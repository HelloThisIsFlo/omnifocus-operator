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
    "Repeating task -- this occurrence was skipped, "
    "next occurrence created.\n"
    "If the user wanted to drop the entire repeating "
    "sequence, let them know this must be done in the "
    "OmniFocus UI (intentional restriction against "
    "destructive operations)."
)

# --- Tags ---

TAGS_ALREADY_MATCH = "Tags already match the requested set -- no tag changes applied"

TAG_ALREADY_ON_TASK = "Tag '{display}' ({tag_id}) is already on this task"

TAG_NOT_ON_TASK = "Tag '{display}' ({tag_id}) is not on this task"

# --- Repetition Rule ---

REPETITION_END_DATE_PAST = (
    "The end date {date} is in the past -- the repetition rule was set, "
    "but no future occurrences will be generated. Was this intentional?"
)

REPETITION_EMPTY_ON_DATES = (
    "monthly with empty onDates is equivalent to plain monthly (no date constraint). "
    "The empty onDates was ignored. Omit onDates or use type 'monthly' directly next time."
)

REPETITION_EMPTY_ON_DAYS = (
    "weekly with empty onDays is equivalent to plain weekly (no day constraint). "
    "The empty onDays was ignored. Omit onDays or use type 'weekly' directly next time."
)

REPETITION_EMPTY_ON = (
    "monthly with empty on is equivalent to plain monthly (no weekday constraint). "
    "The empty on was ignored. Omit on or use type 'monthly' directly next time."
)

REPETITION_AUTO_CLEAR_ON_DATES = (
    "on and onDates are mutually exclusive on monthly. "
    "Since on was set, onDates was automatically cleared."
)

REPETITION_AUTO_CLEAR_ON = (
    "on and onDates are mutually exclusive on monthly. "
    "Since onDates was set, on was automatically cleared."
)

REPETITION_NO_OP = (
    "The repetition rule is identical to the existing one -- no changes applied. "
    "Omit repetitionRule from the request if you don't want to change it."
)

REPETITION_FROM_COMPLETION_BYDAY = (
    "from_completion with day-of-week patterns (onDays) can produce "
    "counterintuitive results: same-day completions are skipped (never "
    "lands on today), biweekly/monthly grids reset from the completion "
    "date, and early completions can land back on the original due date. "
    "Consider regularly_with_catch_up for day-of-week schedules unless "
    "the minimum gap between occurrences is what matters."
)

REPETITION_ANCHOR_DATE_MISSING = (
    "basedOn is '{based_on}' but no {date_field} is set on this task -- "
    "OmniFocus will create the missing {date_field} on the next occurrence "
    "using the completion date and the user's default time for that date type "
    "(configured in Settings > Dates & Times). This produces a valid but "
    "potentially surprising schedule. Set the {date_field} explicitly for "
    "predictable repetition behavior."
)

# --- Filter Resolution ---

FILTER_MULTI_MATCH = (
    "Filter '{value}' matched {count} {entity_type}s: {matches}. For exact results, filter by ID."
)

FILTER_NO_MATCH = "No {entity_type} found matching '{value}'. This filter was skipped."

# --- Project Tool: Inbox Search ---

LIST_PROJECTS_INBOX_WARNING = (
    "The '$inbox' appears as a project on tasks but is not a real OmniFocus project "
    "and won't appear in results. "
    "To query inbox tasks, use list_tasks with 'inInbox=true'."
)

# --- Task Tool: Inbox Project Filter ---

LIST_TASKS_INBOX_PROJECT_WARNING = (
    "The 'project=\"{value}\"' filter also matches the OmniFocus Inbox by name, "
    "but the Inbox is a virtual location, not a named project. "
    "Inbox tasks are not included in these results. "
    "Use project='$inbox' or 'inInbox=true' to query them."
)

# --- Availability Filter ---

AVAILABILITY_MIXED_ALL = (
    "'ALL' already includes every status -- no need to combine it with other values."
)

FILTER_DID_YOU_MEAN = (
    "No {entity_type} found matching '{value}'. "
    "Did you mean: {suggestions}? "
    "This filter was skipped."
)
