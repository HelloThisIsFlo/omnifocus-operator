---
created: 2026-04-01T12:41:26.600Z
title: Centralize field descriptions into constants like warnings and errors
area: models
files:
  - src/omnifocus_operator/agent_messages/errors.py
  - src/omnifocus_operator/agent_messages/warnings.py
  - src/omnifocus_operator/agent_messages/descriptions.py (new)
---

## Problem

Pydantic uses class docstrings and `Field(description=...)` strings as the `description` field in JSON Schema. When these models are nested inside MCP tool input/output schemas, **every docstring and field description becomes agent-visible documentation**. Currently these are scattered as inline strings across `models/` and `contracts/`, which means:

- It's easy to forget a docstring isn't just developer docs — it's agent-facing schema text
- Descriptions can silently drift between the core model and its contract counterpart (e.g., `on_days` appears on both `Frequency` and `FrequencyAddSpec`)
- There's no single place to review all agent-facing descriptions at a glance
- It's inconsistent with how we handle warnings and errors, which already live in centralized constant files under `agent_messages/`

## Solution

Create `agent_messages/descriptions.py` following the exact same pattern as `errors.py` and `warnings.py`.

### Mechanism

Two types of descriptions need centralizing:

1. **Class docstrings** → use `__doc__ = CONSTANT` as the first line of the class body
   ```python
   from omnifocus_operator.agent_messages.descriptions import MOVE_ACTION
   
   class MoveAction(CommandModel):
       __doc__ = MOVE_ACTION
   ```
   This works — confirmed by experiment (`__doc__` assignment from a constant produces the same JSON Schema `description` as a regular docstring).

2. **Field descriptions** → use `Field(description=CONSTANT)` (already natural)
   ```python
   from omnifocus_operator.agent_messages.descriptions import DUE_DATE
   
   due_date: AwareDatetime | None = Field(default=None, description=DUE_DATE)
   ```

### What to centralize

Both `models/` (output schema) and `contracts/` (input schema) descriptions. When the same concept appears in both (e.g., `on_days`, date fields), they share the same constant — single source of truth.

### What NOT to centralize

- Docstrings on internal/non-agent-facing classes (e.g., `_Unset`, `OmniFocusBaseModel`, `RepetitionRuleRepoPayload`) — these don't appear in MCP tool schemas
- Docstrings on internal helper functions (e.g., `_validate_frequency_type`)

### Deciding what's agent-facing

- **Input schema**: Models reachable from `AddTaskCommand`, `EditTaskCommand`, and their nested specs/actions. These appear in the MCP tool's `inputSchema`.
- **Output schema**: Models reachable from tool return types (`AddTaskResult`, `EditTaskResult`, `ListResult`, `Task`, `Project`, `Tag`, `Folder`, `Perspective`, `AllEntities`). These appear in `outputSchema`.
- **Internal-only**: `RepoPayload`, `RepoResult`, `RepoQuery` models — these are service↔repo contracts, never serialized to the agent. Leave their docstrings as regular inline strings.

## Inventory

### Field descriptions (24 instances)

**Shared across models and contracts (use same constant):**
- `on_days`: "Days of the week for weekly recurrence." — used in `Frequency`, `FrequencyAddSpec`, `FrequencyEditSpec`
- `on_dates` (via `OnDate` type alias): "Days of the month. Use -1 for last day." — used in `repetition_rule.py` models
- `due_date`: "Deadline with real consequences if missed. Not for intentions -- use plannedDate instead. ..." — used in `ActionableEntity`, `AddTaskCommand`, `EditTaskCommand`
- `defer_date`: "Task cannot be acted on until this date. Hidden from most views until then. ..." — same locations
- `planned_date`: "When you intend to work on this task. No urgency signal, ..." — same locations
- `effective_flagged`: "Inherited from parent project if not set directly on this task."
- `effective_due_date` / `effective_defer_date` / `effective_planned_date` / `effective_drop_date`: "Inherited from parent project or task if not set directly on this entity."
- `effective_completion_date`: "Inherited from parent project or task if not set directly on this task."

**Contract-only field descriptions:**
- `tags` (AddTaskCommand): "Tag names (case-insensitive) or IDs; you can mix both in one list. ..."
- `parent` (AddTaskCommand): "Project or task ID to place this task under. Omit for inbox."
- `TagAction.add`: "Tag names (case-insensitive) or IDs to add; ..."
- `TagAction.remove`: "Tag names (case-insensitive) or IDs to remove; ..."
- `TagAction.replace`: "Replace all tags with this list. ..."

**Model-only field descriptions:**
- `tags` (ActionableEntity): "Tags applied to this entity, each with id and name."
- `next_task` (Project): "ID of the first available task in this project, if any."
- `children_are_mutually_exclusive` (Tag): "When true, child tags behave like radio buttons -- assigning one removes siblings."
- `EndByDate.date`: "Repeat until this date."

### Class docstrings — agent-facing (need centralizing)

**Output models (`models/`):**
- `OrdinalWeekday`: "Typed ordinal-weekday model for monthly day-of-week patterns. ..."
- `Frequency`: "How often the task repeats: type + interval, with optional day/date refinements."
- `EndByDate`: "End condition: repeat until a specific date."
- `EndByOccurrences`: "End condition: repeat a fixed number of times."
- `RepetitionRule`: "Structured repetition rule for recurring tasks and projects."
- `TagRef`: "Reference to a tag with both id and name for ergonomics."
- `ParentRef`: "Reference to a parent entity (project or task) with type, id, and name. ..."
- `ReviewInterval`: "Review interval for project review scheduling. ..."
- `OmniFocusEntity`: "Base fields shared by all OmniFocus entity types: id, name, url, timestamps."
- `ActionableEntity`: "Shared fields for tasks and projects: status, dates, flags, tags, repetition rules."
- `Task`: "A single OmniFocus task with all fields."
- `Project`: "A single OmniFocus project with all fields."
- `Tag` (model): "A single OmniFocus tag with all fields."
- `Folder`: "A single OmniFocus folder with all fields. ..."
- `Perspective`: "A single OmniFocus perspective. ..."
- `AllEntities`: "All OmniFocus entities from a repository. ..."
- Enums: `Urgency`, `Availability`, `TagAvailability`, `FolderAvailability`, `Schedule`, `BasedOn` — short one-liners

**Input models (`contracts/`):**
- `TagAction`: "Tag operations for task editing. Either replace (standalone) or add/remove (combinable). ..."
- `MoveAction`: "Specifies where to move a task. Exactly one key must be set. ..."
- `ListResult`: "Agent-facing result container for all list operations. ..."
- `EditTaskActions`: "Stateful operations grouped under the actions block."
- Query models: `ListTasksQuery`, `ListProjectsQuery`, `ListTagsQuery`, `ListFoldersQuery` — short one-liners

### Class docstrings — internal-only (leave as-is)

- `OmniFocusBaseModel`, `StrictModel`, `CommandModel`, `QueryModel`, `_Unset`
- All `RepoPayload`, `RepoResult`, `RepoQuery` classes
- `AddTaskResult`, `EditTaskResult` (result docstrings are brief, but worth reviewing — they do appear in output schema)
- `ListRepoResult`, `ReviewDueFilter`, `DurationUnit`

## File structure

`agent_messages/descriptions.py` should be organized by domain, same as errors/warnings:

```python
"""Consolidated description strings for all agent-facing schema documentation.

Every Field(description=...) and class __doc__ that appears in MCP tool
input or output schemas is defined here. This makes it easy to review,
audit, and maintain the agent-facing documentation in one place.

Shared descriptions (used by both core models and contract specs) are
defined once -- single source of truth across input and output schemas.
"""

# --- Dates ---
DUE_DATE = "..."
DEFER_DATE = "..."
PLANNED_DATE = "..."
# ...

# --- Tags ---
TAG_ACTION_ADD = "..."
# ...

# --- Repetition ---
FREQUENCY = "..."
ON_DAYS = "..."
# ...

# --- Entities ---
TASK = "..."
PROJECT = "..."
# ...
```

## Tests

Mirror the existing error/warning constant tests:
- All constants are non-empty strings
- No unused constants (every constant is imported somewhere)
- No inline description strings remain in agent-facing models (grep check)
