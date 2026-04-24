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

EDIT_NO_CHANGES_DETECTED = """\
No changes detected -- the task already has these values. \
If you don't want to change a field, omit it from the request."""

MOVE_ALREADY_AT_POSITION = (
    "Task is already at the {position} of its container -- no reordering needed."
)

# --- Lifecycle ---

LIFECYCLE_ALREADY_IN_STATE = (
    "Task is already {state_word} -- nothing changed. Omit actions.lifecycle to skip."
)

LIFECYCLE_CROSS_STATE = """\
Task was already {prior_state} -- lifecycle action applied, \
task is now {new_state}. Confirm with user that this was intended."""

LIFECYCLE_REPEATING_COMPLETE = (
    "Repeating task -- this occurrence completed, next occurrence created."
)

LIFECYCLE_REPEATING_DROP = """\
Repeating task -- this occurrence was skipped, \
next occurrence created.
If the user wanted to drop the entire repeating \
sequence, let them know this must be done in the \
OmniFocus UI (intentional restriction against \
destructive operations)."""

# --- Tags ---

TAGS_ALREADY_MATCH = "Tags already match the requested set -- no tag changes applied"

TAG_ALREADY_ON_TASK = "Tag '{display}' ({tag_id}) is already on this task"

TAG_NOT_ON_TASK = "Tag '{display}' ({tag_id}) is not on this task"

# --- Note ---

NOTE_APPEND_EMPTY = (
    "Empty or whitespace-only append is a no-op (OmniFocus normalizes whitespace to empty) -- "
    "omit actions.note.append to skip, or pass non-whitespace text to append."
)

NOTE_REPLACE_ALREADY_CONTENT = "Note already has this content -- omit actions.note.replace to skip."

NOTE_ALREADY_EMPTY = "Note is already empty -- omit actions.note.replace to skip."

# --- Repetition Rule ---

REPETITION_END_DATE_PAST = """\
The end date {date} is in the past -- the repetition rule was set, \
but no future occurrences will be generated. Was this intentional?"""

REPETITION_EMPTY_ON_DATES = """\
monthly with empty onDates is equivalent to plain monthly (no date constraint). \
The empty onDates was ignored. Omit onDates or use type 'monthly' directly next time."""

REPETITION_EMPTY_ON_DAYS = """\
weekly with empty onDays is equivalent to plain weekly (no day constraint). \
The empty onDays was ignored. Omit onDays or use type 'weekly' directly next time."""

REPETITION_EMPTY_ON = """\
monthly with empty on is equivalent to plain monthly (no weekday constraint). \
The empty on was ignored. Omit on or use type 'monthly' directly next time."""

REPETITION_AUTO_CLEAR_ON_DATES = """\
on and onDates are mutually exclusive on monthly. \
Since on was set, onDates was automatically cleared."""

REPETITION_AUTO_CLEAR_ON = """\
on and onDates are mutually exclusive on monthly. \
Since onDates was set, on was automatically cleared."""

REPETITION_NO_OP = """\
The repetition rule is identical to the existing one -- no changes applied. \
Omit repetitionRule from the request if you don't want to change it."""

REPETITION_FROM_COMPLETION_BYDAY = """\
from_completion with day-of-week patterns (onDays) can produce \
counterintuitive results: same-day completions are skipped (never \
lands on today), biweekly/monthly grids reset from the completion \
date, and early completions can land back on the original due date. \
Consider regularly_with_catch_up for day-of-week schedules unless \
the minimum gap between occurrences is what matters."""

REPETITION_ANCHOR_DATE_MISSING = """\
basedOn is '{based_on}' but no {date_field} is set on this task -- \
OmniFocus will create the missing {date_field} on the next occurrence \
using the completion date and the user's default time for that date type \
(configured in Settings > Dates & Times). This produces a valid but \
potentially surprising schedule. Set the {date_field} explicitly for \
predictable repetition behavior."""

# --- Date Resolution ---

DUE_SOON_THRESHOLD_NOT_DETECTED = """\
Due-soon threshold was not detected from OmniFocus preferences. \
Defaulting to 2 days (OmniFocus factory default). \
Restart the server if you changed this setting."""

SETTINGS_FALLBACK_WARNING = """\
Could not read OmniFocus preferences (app may not be running). \
Using factory defaults for date/time settings. \
Restart the server after OmniFocus is available."""

SETTINGS_UNKNOWN_DUE_SOON_PAIR = """\
OmniFocus due-soon preference has an unrecognized value. \
Defaulting to 2 days (OmniFocus factory default)."""

# --- Defer Hints ---

_DEFER_HINT = (
    "Tip: This shows tasks {description}. "
    "For all {adjective} tasks regardless of reason, use availability: '{filter}'. "
    "Defer is one of four blocking reasons."
)

DEFER_AFTER_NOW_HINT = _DEFER_HINT.format(
    description="with a future defer date",
    adjective="unavailable",
    filter="blocked",
)

DEFER_BEFORE_NOW_HINT = _DEFER_HINT.format(
    description="whose defer date has passed",
    adjective="currently available",
    filter="available",
)

# --- Filter Resolution ---

FILTER_MULTI_MATCH = (
    "Filter '{value}' matched {count} {entity_type}s: {matches}. For exact results, filter by ID."
)

# --- Project Tool: Inbox Search ---

LIST_PROJECTS_INBOX_WARNING = """\
The '$inbox' appears as a project on tasks but is not a real OmniFocus project \
and won't appear in results. \
To query inbox tasks, use list_tasks with 'inInbox=true'."""

# --- Task Tool: Inbox Project Filter ---

LIST_TASKS_INBOX_PROJECT_WARNING = """\
The 'project="{value}"' filter also matches the OmniFocus Inbox by name, \
but the Inbox is a virtual location, not a named project. \
Inbox tasks are not included in these results. \
Use 'inInbox=true' to query them."""

# --- Task Tool: Parent Filter (Phase 57-02) ---

PARENT_RESOLVES_TO_PROJECT_WARNING = """\
The 'parent="{value}"' filter resolved only to projects. \
Consider using 'project' instead -- it's the canonical filter for \
project-level scoping and makes intent clearer."""

# --- Task Tool: Scope Filter Semantics (Phase 57-03) ---

# WARN-01: verbatim text from MILESTONE-v1.4.1.md line 180 -- DO NOT paraphrase.
FILTERED_SUBTREE_WARNING = """\
Filtered subtree: resolved parent tasks are always included, \
but intermediate and descendant tasks not matching your other filters \
(tags, dates, etc.) are excluded. Each returned task's `parent` field \
still references its true parent -- fetch separately if you need data \
for an excluded intermediate."""

# WARN-03: soft heads-up when both scope filters specified together.
PARENT_PROJECT_COMBINED_WARNING = """\
Both 'project' and 'parent' filters are set. \
Results are the intersection of their task scopes. \
If you meant only one scope, omit the other."""

# Quick task 260424-j63 (2026-04-24): supersedes EMPTY_SCOPE_INTERSECTION_WARNING
# and FILTER_NO_MATCH. Fires whenever ``list_tasks`` resolves to zero items AND
# at least one query field is non-default. Parameterized by the active-filter
# names the agent sent (camelCase aliases, alphabetically sorted). See
# .planning/quick/260424-j63-unify-empty-result-warning-surface/ for the
# two-layer model and the 8-case test matrix.
EMPTY_RESULT_WARNING_SINGLE = "The '{filters}' filter resolved to zero tasks. No results."

EMPTY_RESULT_WARNING_MULTI = (
    "The combination of filters {filters} resolved to zero tasks. No results."
)

# --- Availability Filter ---

AVAILABILITY_MIXED_ALL = (
    "'ALL' already includes every status -- no need to combine it with other values."
)

AVAILABILITY_REMAINING_INCLUDES_AVAILABLE = (
    "'remaining' already includes 'available' -- no need to combine them."
)

AVAILABILITY_REMAINING_INCLUDES_BLOCKED = (
    "'remaining' already includes 'blocked' -- no need to combine them."
)

FILTER_DID_YOU_MEAN = "Did you mean: {suggestions}? (no {entity_type} matched '{value}')"
