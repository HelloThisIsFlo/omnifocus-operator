# Pydantic Model — Updated Design

> Two-axis status model applied to all entity models. What stays, what goes, what changes.

**Contents:**
[1. Models](#1-models) · [2. New Enums](#2-new-enums) · [3. Fields Removed](#3-fields-removed) · [4. Fallback Mode](#4-fallback-mode) · [5. Class Hierarchy](#5-class-hierarchy)

---

## 1. Models

### ActionableEntity (shared by Task and Project)

```
# Two-axis status
urgency: Urgency                              # overdue / due_soon / none
availability: Availability                    # available / blocked / completed / dropped

# Identity (from OmniFocusEntity)
id: str
name: str
url: str
added: AwareDatetime
modified: AwareDatetime

# Content
note: str

# Flags
flagged: bool
effective_flagged: bool

# Dates
due_date: AwareDatetime | None
defer_date: AwareDatetime | None
effective_due_date: AwareDatetime | None
effective_defer_date: AwareDatetime | None
completion_date: AwareDatetime | None
effective_completion_date: AwareDatetime | None
planned_date: AwareDatetime | None
effective_planned_date: AwareDatetime | None
drop_date: AwareDatetime | None
effective_drop_date: AwareDatetime | None

# Metadata
estimated_minutes: float | None
has_children: bool

# Relationships
tags: list[TagRef]
repetition_rule: RepetitionRule | None
```

### Task (own fields only)

```
in_inbox: bool
project: str | None
parent: str | None
```

### Project (own fields only)

```
last_review_date: AwareDatetime
next_review_date: AwareDatetime
review_interval: ReviewInterval
next_task: str | None
folder: str | None
```

### Tag

```
id, name, url, added, modified                             # from OmniFocusEntity
status: TagStatus                                          # Active / OnHold / Dropped
children_are_mutually_exclusive: bool
parent: str | None
```

### Folder

```
id, name, url, added, modified                             # from OmniFocusEntity
status: FolderStatus                                       # Active / Dropped
parent: str | None
```

### Perspective — unchanged

```
id: str | None
name: str
builtin: bool  # computed from id
```

---

## 2. New Enums

Replace `TaskStatus` and `ProjectStatus` with two shared enums on `ActionableEntity`:

**Urgency** (is this pressing?):
```
overdue    — past due date
due_soon   — approaching due date
none       — no time pressure
```

**Availability** (can this be worked on?):
```
available  — ready to work on
blocked    — structurally blocked (sequential, on hold, future defer, etc.)
completed  — done
dropped    — dropped
```

Both Task and Project share these. The agent's question is always the same: "can I work on this?" and "is this urgent?" — regardless of whether it's a task or project.

### Mapping from old enums

**TaskStatus → Urgency + Availability:**

| Old TaskStatus | Urgency | Availability |
|---|---|---|
| Available | `none` | `available` |
| Next | `none` | `available` |
| Blocked | `none` | `blocked` |
| DueSoon | `due_soon` | (from SQLite `blocked` column) |
| Overdue | `overdue` | (from SQLite `blocked` column) |
| Completed | `none` | `completed` |
| Dropped | `none` | `dropped` |

**ProjectStatus → Availability:**

| Old ProjectStatus | Availability |
|---|---|
| Active | `available` |
| OnHold | `blocked` |
| Done | `completed` |
| Dropped | `dropped` |

---

## 3. Fields Removed

**From `OmniFocusEntity` (all models):**
- `active` — subsumed by `availability` (Task/Project) or `status` (Tag/Folder)
- `effective_active` — same; inheritance info not worth the complexity

**From `ActionableEntity`:**
- `completed` (bool) — subsumed by `availability == completed`, also derivable from `completion_date is not None`
- `sequential` — OmniFocus uses this internally to compute blocking; agents don't need it (see rationale below)
- `completed_by_children` — same; internal OmniFocus behavior, not agent-relevant state
- `should_use_floating_time_zone` — no SQLite column; always `true` in observed data via bridge. Not worth a bridge call for a field that never varies.

**From `Task`:**
- `status: TaskStatus` — replaced by `urgency` + `availability`

**From `Project`:**
- `status: ProjectStatus` — mapped into `availability`
- `task_status: TaskStatus` — replaced by `urgency` + `availability`
- `contains_singleton_actions` — distinguishes single-action lists from parallel/sequential projects; internal to OmniFocus's blocking logic (see rationale below)

**From `Tag`:**
- `allows_next_action` — redundant with `status` (`Active` = allows, `OnHold` = doesn't)

**Enums deleted:** `TaskStatus`, `ProjectStatus`

### Rationale: project type fields (`sequential`, `contains_singleton_actions`)

OmniFocus has three project types: single-action list, parallel, and sequential. These affect how OmniFocus computes which tasks are blocked. Since we get blocking state directly from SQLite (the `availability` axis), the agent doesn't need to know *why* something is blocked — just *whether* it is.

Could be added back if: a contributor demonstrates a concrete agent workflow that needs project type info (e.g., reordering tasks in a sequential project, or an agent that reasons about task dependencies). Open a PR with the use case.

### Rationale: `completed_by_children`

Controls whether a parent task/project auto-completes when all children are done. This is OmniFocus write-path behavior — the agent reads `availability == completed` and doesn't need to know the trigger mechanism.

Could be added back if: an agent needs to predict "will completing this subtask also complete the parent?" Unlikely in practice.

### Fields kept (were considered for removal but staying)

- `estimated_minutes` — rare but not redundant, useful for workload estimation
- `has_children` — cheap, useful for "is this an action group?" queries
- All raw + effective date pairs — raw needed for writes, effective for reads

---

## 4. Fallback Mode (OmniJS Bridge)

When running on the OmniJS bridge instead of SQLite:

- **Urgency:** fully populated — derivable from the bridge's single-winner enum (Overdue always beats Blocked)
- **Availability:** reduced to three values:
  - `completed` = `completed` boolean field from bridge
  - `dropped` = `not effective_active` from bridge
  - `available` = everything else (caveat: may actually be `blocked`, but we can't tell)
  - `blocked` is **never returned** in fallback mode

This is acceptable because urgency is ~90% of real agent queries, and the only loss is the `blocked` vs `available` distinction.

---

## 5. Class Hierarchy

`active`/`effective_active` are removed from `OmniFocusEntity` entirely. All models use their own status representation:
- Task/Project → `urgency` + `availability` (on `ActionableEntity`)
- Tag → `status: TagStatus`
- Folder → `status: FolderStatus`
