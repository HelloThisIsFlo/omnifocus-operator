# OmniFocus Bridge Specification

> The complete spec for the OmniFocus Operator bridge layer — what to extract, how to access it, and what to leave for Python.
>
> Derived from 27 empirical audit scripts run against a live OmniFocus database (v4.8.8 / 185.9.1).
> Every access path, type, and caveat is backed by script output, not documentation.

---

## 1. Principles

### Dumb Bridge, Smart Python
The bridge runs inside OmniFocus as Omni Automation (OmniJS). It is **untestable** — no unit tests, no TDD, no CI. Every line of logic in the bridge is a line we can't verify automatically.

**But testability is only half the reason.** OmniJS is catastrophically slow — roughly **1ms per task per operation**. A simple boolean lookup across 2800 tasks takes 1.2 seconds, during which the entire OmniFocus UI is frozen. Benchmarked on a live database (2825 tasks, 368 projects):
- Building a project ID index from 368 projects: **172ms**
- Scanning 2825 tasks with a single property lookup per task: **1,264ms**

This is not premature optimization — it's a hard constraint. Every line of logic added to the bridge has a measurable, user-visible cost. The bridge must do the absolute minimum: read fields, resolve enums (because `===` only works inside OmniJS), serialize to JSON. Everything else belongs in Python where it's instantaneous.

**Bridge responsibility:** Extract raw data. Read from the correct accessors, resolve opaque enums to strings, serialize to JSON. No filtering, no transformation, no derived computations beyond enum resolution.

**Python responsibility:** All interpretation, validation, model mapping, filtering, and business logic. This is where we have TDD, type checking, and full control — and where operations on 2800 tasks take microseconds, not seconds.

**Rule of thumb:** If there's ambiguity about where logic belongs, it belongs in Python.

### Date Serialization
All OmniJS `Date` objects must be serialized via `.toISOString()` — ISO 8601 format with UTC timezone (e.g., `"2024-01-15T10:30:00.000Z"`). Nullable date fields serialize as `null`.

### Fail Fast on Nulls
Every field is classified as **required** or **nullable**. If a required field returns `null`/`undefined`, the bridge must throw — not silently propagate a null that causes downstream bugs. The nullable/required classification for every field is specified in the entity sections below.

### Enum Resolution via `===`
OmniFocus enums are opaque objects. `.name` returns `undefined`. The only reliable resolution is `===` comparison against known constants. Each entity type has its own isolated enum namespace — `Project.Status.Active !== Tag.Status.Active`. The bridge must use per-type resolvers and serialize enums as strings (e.g., `"Active"`, `"OnHold"`).

If the bridge encounters an unknown enum value, it must **throw an error** with the `String()` representation (which returns `"[object Type: Value]"` — parseable for diagnostics). Do not silently return null or "UNKNOWN".

---

## 2. Entity Specifications

### 2.1 Task

The richest entity type. OmniJS exposes 49 getters total; the bridge extracts the ~30 listed below. The remainder are either deferred (Section 7), deprecated (Section 3), or explicitly excluded ("Do NOT use" list).

#### Fields

| Field | Access Path | Type | Required | Notes |
|-------|------------|------|----------|-------|
| `id` | `t.id.primaryKey` | string | ✅ | Unique identifier |
| `name` | `t.name` | string | ✅ | Can be empty string (4 tasks observed) but never null |
| `note` | `t.note` | string | ✅ | Never null — empty string if no note |
| `status` | `t.taskStatus` | enum → string | ✅ | Resolve via `===` against `Task.Status.*` (7 values) |
| `active` | `t.active` | boolean | ✅ | Always present. `false` only for self-dropped tasks |
| `effectiveActive` | `t.effectiveActive` | boolean | ✅ | `false` = task is in an inactive container |
| `completed` | `t.completed` | boolean | ✅ | Always present |
| `flagged` | `t.flagged` | boolean | ✅ | Always present |
| `effectiveFlagged` | `t.effectiveFlagged` | boolean | ✅ | Inherits from parent/project |
| `sequential` | `t.sequential` | boolean | ✅ | Whether this task's children are sequential |
| `completedByChildren` | `t.completedByChildren` | boolean | ✅ | Controls auto-completion. Defaults to `true` |
| `hasChildren` | `t.hasChildren` | boolean | ✅ | Whether this task is an action group |
| `inInbox` | `t.inInbox` | boolean | ✅ | `true` = inbox task (no project) |
| `shouldUseFloatingTimeZone` | `t.shouldUseFloatingTimeZone` | boolean | ✅ | Always `true` in observed data — can omit from model |
| `added` | `t.added` | Date | ✅ | Always present on tasks |
| `modified` | `t.modified` | Date | ✅ | Always present on tasks |
| `dueDate` | `t.dueDate` | Date | nullable | Direct due date |
| `deferDate` | `t.deferDate` | Date | nullable | Direct defer/start date |
| `completionDate` | `t.completionDate` | Date | nullable | Set when completed |
| `dropDate` | `t.dropDate` | Date | nullable | Set when dropped |
| `plannedDate` | `t.plannedDate` | Date | nullable | v4.7+ feature |
| `effectiveDueDate` | `t.effectiveDueDate` | Date | nullable | Inherited: `min(own, parent's effective)` — soonest wins |
| `effectiveDeferDate` | `t.effectiveDeferDate` | Date | nullable | Inherited from project or parent task |
| `effectiveCompletionDate` | `t.effectiveCompletionDate` | Date | nullable | Use this, NOT `effectiveCompletedDate` (they're aliases) |
| `effectivePlannedDate` | `t.effectivePlannedDate` | Date | nullable | Inherited |
| `effectiveDropDate` | `t.effectiveDropDate` | Date | nullable | Matches `effectiveActive=false` |
| `estimatedMinutes` | `t.estimatedMinutes` | number | nullable | Null = no estimate. Never zero — range is 1-300 |
| `containingProject` | `t.containingProject` | Project ref → id | nullable | Null for inbox tasks. Use this, NOT `project` |
| `parent` | `t.parent` | Task ref → id | nullable | Null for inbox tasks and project root tasks. Tasks directly inside a project have `parent` = the project's root task. `parentTask` does NOT exist |
| `tags` | `t.tags` | array of Tag refs → ids | ✅ | Always present (can be empty array) |
| `repetitionRule` | `t.repetitionRule` | object | nullable | See RepetitionRule section below |
| `url` | `t.url` | URL | ✅ | OmniFocus URL scheme link — useful for deep linking |
| `notifications` | `t.notifications` | array | ✅ | **Deferred** — exclude from initial implementation. See Section 7 |
| `attachments` | `t.attachments` | array | ✅ | **Deferred** — exclude from initial implementation. See Section 7 |
| `linkedFileURLs` | `t.linkedFileURLs` | array | ✅ | **Deferred** — exclude from initial implementation. See Section 7 |

**Do NOT use:**
- `t.project` — returns null for child tasks; use `t.containingProject`
- `t.parentTask` — does not exist in Omni Automation; use `t.parent`
- `t.assignedContainer` — always null on all tasks (2825/2825)
- `t.effectiveCompletedDate` — alias for `effectiveCompletionDate`, use the latter
- `t.completedDate` — does not exist (undefined)

#### Task Status Enum

7 values. Resolve via `===` against `Task.Status.*`:

| Value | String | Notes |
|-------|--------|-------|
| `Task.Status.Available` | `"Available"` | Workable |
| `Task.Status.Blocked` | `"Blocked"` | Sequential position, future defer, parent children, OnHold tag |
| `Task.Status.Completed` | `"Completed"` | Done |
| `Task.Status.Dropped` | `"Dropped"` | Dropped (self or inherited from container) |
| `Task.Status.DueSoon` | `"DueSoon"` | Near due date (threshold not readable from API) |
| `Task.Status.Next` | `"Next"` | First available in project (project-level concept only) |
| `Task.Status.Overdue` | `"Overdue"` | Past due date |

### 2.2 Project

A project wraps a "root task" (`p.task`). They share the same `id`. Some fields only exist on the root task — the bridge MUST read those from `p.task.*`.

#### Fields

| Field | Access Path | Type | Required | Notes |
|-------|------------|------|----------|-------|
| `id` | `p.id.primaryKey` | string | ✅ | Same as `p.task.id.primaryKey` |
| `name` | `p.name` | string | ✅ | Proxied — `p.name === p.task.name` |
| `note` | `p.note` | string | ✅ | Proxied — never null |
| `status` | `p.status` | enum → string | ✅ | Resolve via `===` against `Project.Status.*` (4 values) |
| `taskStatus` | `p.task.taskStatus` | enum → string | ✅ | The root task's status — reveals blocking state |
| `active` | **`p.task.active`** | boolean | ✅ | ⚠️ Undefined on `p.*` — MUST read from `p.task` |
| `effectiveActive` | **`p.task.effectiveActive`** | boolean | ✅ | ⚠️ Undefined on `p.*` — MUST read from `p.task` |
| `added` | **`p.task.added`** | Date | ✅ | ⚠️ Undefined on `p.*` — MUST read from `p.task` |
| `modified` | **`p.task.modified`** | Date | ✅ | ⚠️ Undefined on `p.*` — MUST read from `p.task` |
| `completed` | `p.completed` | boolean | ✅ | Proxied |
| `flagged` | `p.flagged` | boolean | ✅ | Proxied |
| `effectiveFlagged` | `p.effectiveFlagged` | boolean | ✅ | Proxied |
| `sequential` | `p.sequential` | boolean | ✅ | Whether project tasks are sequential |
| `completedByChildren` | `p.completedByChildren` | boolean | ✅ | Proxied |
| `containsSingletonActions` | `p.containsSingletonActions` | boolean | ✅ | Single-action list (no sequential ordering) |
| `dueDate` | `p.dueDate` | Date | nullable | Proxied |
| `deferDate` | `p.deferDate` | Date | nullable | Proxied |
| `completionDate` | `p.completionDate` | Date | nullable | Proxied |
| `dropDate` | `p.dropDate` | Date | nullable | Proxied |
| `plannedDate` | `p.plannedDate` | Date | nullable | Proxied |
| `effectiveDueDate` | `p.effectiveDueDate` | Date | nullable | Works on both `p.*` and `p.task.*` |
| `effectiveDeferDate` | `p.effectiveDeferDate` | Date | nullable | Works on both |
| `effectiveCompletionDate` | `p.effectiveCompletionDate` | Date | nullable | Works on both |
| `effectivePlannedDate` | `p.effectivePlannedDate` | Date | nullable | Works on both |
| `effectiveDropDate` | `p.effectiveDropDate` | Date | nullable | Works on both |
| `estimatedMinutes` | `p.estimatedMinutes` | number | nullable | Proxied |
| `lastReviewDate` | `p.lastReviewDate` | Date | ✅ | Always present |
| `nextReviewDate` | `p.nextReviewDate` | Date | ✅ | Always present |
| `reviewInterval` | `p.reviewInterval` | object | ✅ | Has `steps` (number) and `unit` (string, e.g., "weeks", "months") |
| `nextTask` | `p.nextTask` | Task ref → id | nullable | May return root task itself for non-Active projects |
| `folder` | `p.parentFolder` | Folder ref → id | nullable | OmniJS accessor is `parentFolder`, not `folder`. All projects had folders in observed data |
| `tags` | `p.tags` | array of Tag refs → ids | ✅ | Proxied — `p.tags === p.task.tags` |
| `repetitionRule` | `p.repetitionRule` | object | nullable | See RepetitionRule section |
| `url` | `p.url` | URL | ✅ | OmniFocus URL scheme link |

**Critical: 4 fields MUST read from `p.task.*`:**
- `active` — undefined on `p.*` (368/368)
- `effectiveActive` — undefined on `p.*` (368/368)
- `added` — undefined on `p.*` (368/368)
- `modified` — undefined on `p.*` (368/368)

All other fields are proxied and can be read from either side.

#### Project Status Enum

4 values. Resolve via `===` against `Project.Status.*`:

| Value | String | Notes |
|-------|--------|-------|
| `Project.Status.Active` | `"Active"` | Normal state |
| `Project.Status.OnHold` | `"OnHold"` | Paused — children forced to Blocked |
| `Project.Status.Done` | `"Done"` | Completed |
| `Project.Status.Dropped` | `"Dropped"` | Dropped — only status that sets `active=false` |

**`task.active` cannot distinguish Active, OnHold, or Done** — all three have `active=true`. Only Dropped sets `active=false`. Always use `Project.Status` directly.

### 2.3 Tag

Minimal entity — no dates, flags, or completion.

#### Fields

| Field | Access Path | Type | Required | Notes |
|-------|------------|------|----------|-------|
| `id` | `t.id.primaryKey` | string | ✅ | Unique identifier |
| `name` | `t.name` | string | ✅ | Always present, non-empty. Unique in observed data but OmniFocus allows duplicates |
| `status` | `t.status` | enum → string | ✅ | Resolve via `===` against `Tag.Status.*` (3 values) |
| `active` | `t.active` | boolean | ✅ | Always `true` for Active and OnHold tags |
| `effectiveActive` | `t.effectiveActive` | boolean | ✅ | Does NOT inherit from parent — always `true` for Active/OnHold |
| `allowsNextAction` | `t.allowsNextAction` | boolean | ✅ | `false` = OnHold, `true` = Active. Per-tag, not inherited |
| `added` | `t.added` | Date | ✅ | Always present |
| `modified` | `t.modified` | Date | ✅ | Always present |
| `parent` | `t.parent` | Tag ref → id | nullable | Null for top-level tags (27/65) |
| `childrenAreMutuallyExclusive` | `t.childrenAreMutuallyExclusive` | boolean | ✅ | E.g., energy levels where only one applies |
| `url` | `t.url` | URL | ✅ | OmniFocus URL scheme link |

**Dropped tags:** Zero Dropped tags were observed in the database — `active`/`effectiveActive` behavior for Dropped tags is unconfirmed (presumably `false` by analogy with folders, but not empirically verified).

**Tag notes excluded (design decision):** `t.note` exists in OmniJS but returns null on all 65 observed tags. Even if OmniFocus allows tag notes in some edge case, this is niche enough to ignore. The bridge does NOT extract tag notes.

**Tag hierarchy:** OnHold does NOT propagate to child tags. A child tag inside an OnHold parent retains `Active` status, `effectiveActive=true`, `allowsNextAction=true`. Tag-based blocking is purely per-tag — no need to walk the hierarchy.

#### Tag Status Enum

3 values. Resolve via `===` against `Tag.Status.*`:

| Value | String | Notes |
|-------|--------|-------|
| `Tag.Status.Active` | `"Active"` | Default |
| `Tag.Status.OnHold` | `"OnHold"` | Forces all directly-tagged tasks to Blocked |
| `Tag.Status.Dropped` | `"Dropped"` | Deactivated |

### 2.4 Folder

Simplest entity type — organizational container only.

#### Fields

| Field | Access Path | Type | Required | Notes |
|-------|------------|------|----------|-------|
| `id` | `f.id.primaryKey` | string | ✅ | Unique identifier |
| `name` | `f.name` | string | ✅ | Always present, non-empty |
| `status` | `f.status` | enum → string | ✅ | Resolve via `===` against `Folder.Status.*` (2 values) |
| `active` | `f.active` | boolean | ✅ | `false` only for Dropped folders |
| `effectiveActive` | `f.effectiveActive` | boolean | ✅ | Inherits — active folders inside dropped folders get `false` |
| `added` | `f.added` | Date | ✅ | Always present |
| `modified` | `f.modified` | Date | ✅ | Always present |
| `parent` | `f.parent` | Folder ref → id | nullable | Null for top-level folders (7/79) |
| `url` | `f.url` | URL | ✅ | OmniFocus URL scheme link |

**Folder notes excluded (design decision):** `f.note` exists in OmniJS but returns null on all 79 observed folders (same as tags). The bridge does NOT extract folder notes.

#### Folder Status Enum

2 values only — no OnHold, no Done. Simplest enum:

| Value | String | Notes |
|-------|--------|-------|
| `Folder.Status.Active` | `"Active"` | Default |
| `Folder.Status.Dropped` | `"Dropped"` | Folder and all contents deactivated |

### 2.5 Perspective

Perspectives have split behavior: built-in vs custom.

#### Fields

| Field | Access Path | Type | Required | Notes |
|-------|------------|------|----------|-------|
| `id` | `p.id.primaryKey` | string | **undefined for built-in** | ⚠️ Built-in perspectives have `undefined` id in OmniJS (not `null`). Bridge serializes as `null` in JSON. Use truthiness check, not `=== null` |
| `name` | `p.name` | string | ✅ | Always present |
| `identifier` | `p.identifier` | string | nullable | Null for built-in, present for custom |
| `builtin` | `!p.identifier` | boolean | ✅ | **Derived field.** `true` when `identifier` is null/undefined. Convenience for Python — avoids re-deriving from `identifier` |
| `added` | `p.added` | Date | nullable | Only on custom perspectives (undefined for built-in → null in JSON) |
| `modified` | `p.modified` | Date | nullable | Only on custom perspectives (undefined for built-in → null in JSON) |
| `url` | `p.url` | URL | ✅ | OmniFocus URL scheme link |

**Access path:** Use `Perspective.all` (57 perspectives = 7 built-in + 50 custom). Do NOT use `BuiltIn.all + Custom.all` — they sum to 58 ("Search" is in BuiltIn but excluded from `.all`).

**Built-in vs custom:** `identifier === null` → built-in. Built-in perspectives have no `id` (undefined in OmniJS, null in JSON) — must be keyed by name.

**Built-in perspectives (7):** Inbox, Projects, Tags, Forecast, Flagged, Nearby, Review.

**No status, active, or configuration fields** exist on perspectives in the standard API.

### 2.6 RepetitionRule

An immutable sub-object on tasks/projects. 4 readable properties + 1 method.

| Field | Access Path | Type | Required | Notes |
|-------|------------|------|----------|-------|
| `ruleString` | `r.ruleString` | string | ✅ | RFC 5545 RRULE format (e.g., `FREQ=WEEKLY;BYDAY=MO`) |
| `scheduleType` | `r.scheduleType` | enum → string | ✅ | Resolve via `===` against `Task.RepetitionScheduleType.*` |
| `anchorDateKey` | `r.anchorDateKey` | enum → string | ✅ | Resolve via `===` against `Task.AnchorDateKey.*` |
| `catchUpAutomatically` | `r.catchUpAutomatically` | boolean | ✅ | Never null — always true or false |

**Store `ruleString` as-is** — 49 distinct patterns observed. Parse in Python with standard RRULE libraries (e.g., `python-dateutil`).

**`firstDateAfterDate(date)` method** exists on all rules. Computes next occurrence after a given date without parsing RRULE. Could be exposed as a bridge capability for forecasting.

**RepetitionRule is immutable** — all properties are read-only. To modify, create a new `Task.RepetitionRule(ruleString, null, scheduleType, anchorDateKey, catchUpAutomatically)` and reassign to `task.repetitionRule`.

#### ScheduleType Enum

3 values. Resolve via `===` against `Task.RepetitionScheduleType.*`:

| Value | String |
|-------|--------|
| `Task.RepetitionScheduleType.Regularly` | `"Regularly"` |
| `Task.RepetitionScheduleType.FromCompletion` | `"FromCompletion"` |
| `Task.RepetitionScheduleType.None` | `"None"` |

#### AnchorDateKey Enum

3 values. Resolve via `===` against `Task.AnchorDateKey.*`:

| Value | String |
|-------|--------|
| `Task.AnchorDateKey.DueDate` | `"DueDate"` |
| `Task.AnchorDateKey.DeferDate` | `"DeferDate"` |
| `Task.AnchorDateKey.PlannedDate` | `"PlannedDate"` |

---

## 3. Enum Summary

All enums are opaque — `.name` returns `undefined`. Resolve with `===` only. Each entity type has its own namespace — no cross-type sharing.

| Enum | Values | Entity |
|------|--------|--------|
| `Task.Status` | Available, Blocked, Completed, Dropped, DueSoon, Next, Overdue | Task |
| `Project.Status` | Active, OnHold, Done, Dropped | Project |
| `Tag.Status` | Active, OnHold, Dropped | Tag |
| `Folder.Status` | Active, Dropped | Folder |
| `Task.RepetitionScheduleType` | Regularly, FromCompletion, None | RepetitionRule |
| `Task.AnchorDateKey` | DueDate, DeferDate, PlannedDate | RepetitionRule |

**On unknown values:** Throw an error. Include `String(value)` in the error message — it returns `"[object Type: Value]"` which reveals the type and name for diagnostics. Do NOT iterate `.all` arrays at runtime (OmniFocus freezes on large datasets).

**Per-entity resolvers (bridge):** Each entity type has its own isolated enum namespace — `Project.Status.Active !== Tag.Status.Active`. The bridge MUST use separate resolver functions per entity type (e.g., `resolveProjectStatus()`, `resolveTagStatus()`, `resolveFolderStatus()`). A single shared resolver will not work.

**Per-entity status enums (Python):** The valid status values differ per entity type. Python models MUST use separate enum types — not a shared `EntityStatus`:
- `ProjectStatus`: Active, OnHold, Done, Dropped
- `TagStatus`: Active, OnHold, Dropped
- `FolderStatus`: Active, Dropped
- `TaskStatus`: Available, Blocked, Completed, Dropped, DueSoon, Next, Overdue

**Deprecated:** `Task.RepetitionMethod` (4 values: None, Fixed, DeferUntilDate, DueDate) — old pre-4.7 API. Ignore in favor of `scheduleType` + `anchorDateKey`.

---

## 4. Write Operations

### Methods

| Method | Entity | Effect |
|--------|--------|--------|
| `markComplete()` | Task, Project | Sets `completed=true`, `completionDate`. `active` stays `true` |
| `markIncomplete()` | Task, Project | Reverts completion. `completionDate=null` |
| `drop(true)` | Task | Drops all occurrences (for repeating tasks). Sets `active=false`, `effectiveActive=false`, `dropDate`. `markIncomplete()` silently no-ops — use `document.undo()` to revert |
| `drop(false)` | Task | Skips this occurrence only (for repeating tasks). For non-repeating tasks, equivalent to `drop(true)` |
| `addTag(tag)` | Task, Project | Adds tag. Proxied on projects (`p.tags ↔ p.task.tags`) |
| `removeTag(tag)` | Task, Project | Removes tag |
| `clearTags()` | Task, Project | Removes all tags |
| `appendStringToNote(str)` | Task, Project | Appends to note |
| `addNotification(...)` | Task, Project | Add notification |
| `removeNotification(...)` | Task, Project | Remove notification |
| `addAttachment(...)` | Task, Project | Add attachment |
| `deleteObject(entity)` | Any | Deletes entity. Projects cascade to all child tasks |

### Property Writes

All property writes on projects are **fully bidirectional** — setting `p.dueDate` updates `p.task.dueDate` and vice versa. Write to whichever is convenient.

| Property | Write Path | Notes |
|----------|-----------|-------|
| `dueDate` | `t.dueDate = date` | Set or clear (`null`) |
| `deferDate` | `t.deferDate = date` | Set or clear |
| `flagged` | `t.flagged = bool` | Toggles flag |
| `name` | `t.name = str` | Rename |
| `note` | `t.note = str` | Replace note |
| `estimatedMinutes` | `t.estimatedMinutes = num` | Set or clear (`null`) |
| `status` (Project) | `p.status = Project.Status.X` | Only way to change project status |
| `sequential` | `t.sequential = bool` | Toggle sequential/parallel |
| `completedByChildren` | `t.completedByChildren = bool` | Toggle auto-completion |
| `repetitionRule` | `t.repetitionRule = new Rule(...)` | Replace (immutable objects) |

### Creation

| Operation | Code | Notes |
|-----------|------|-------|
| New project | `new Project(name)` | Status=Active, taskStatus=Blocked (root task has no children yet) |
| New task in project | `new Task(name, project)` | First task = Next, subsequent = Blocked (parallel) or Available |
| New tag | `new Tag(name)` | Active by default |
| New task from text | `Task.byParsingTransportText(text)` | TaskPaper format — supports hierarchy |

### Deletion

| Operation | Code | Notes |
|-----------|------|-------|
| Delete project | `deleteObject(project)` | Cascades to all child tasks |
| Delete task | `deleteObject(task)` | ⚠️ Deleting a project's root task also deletes the project |
| Delete tag | `deleteObject(tag)` | Tags survive project/task deletion — independent lifecycle |

**Safe deletion order:** Delete project first, then orphan tasks, then tags.

### Key Write Caveats

- **`markIncomplete()` on Dropped task:** Silent no-op. No error, no state change. Dropping is permanent for standalone tasks.
- **`active` stays `true` after completion:** Do not use `active` to detect completed tasks.
- **Overdue + future defer = still Overdue:** Setting `deferDate` on an Overdue task does NOT change status to Blocked. Urgency wins.
- **`document.sync()`** — triggers OmniFocus sync programmatically.
- **`document.undo()` / `document.redo()`** — available for reverting operations.
- **No transactions:** OmniJS applies changes immediately. If a script throws partway through, already-applied changes persist. For multi-step writes, consider single-operation scripts or use `document.undo()` for rollback.

---

## 5. Status Override Hierarchy

OmniFocus has a deterministic priority system for `taskStatus`. Understanding this is critical — the bridge reports status faithfully, and Python interprets it.

### Priority (highest to lowest)

1. **Dropped project** → all children forced to `Dropped`, `effectiveActive=false`
2. **OnHold project** → active incomplete children forced to `Blocked` (suppresses Overdue/DueSoon). Exception: Completed/Dropped children are immune
3. **Urgency** (Active projects only) → `Overdue` / `DueSoon` override all forms of blocking (sequential, defer, parent-children)
4. **Blocking sources** → `Blocked` from: sequential position, future defer date, parent with incomplete children, OnHold tag
5. **Available / Next** → unblocked tasks. `Next` is the first available in a project (project-level concept only — action groups use `Available`)

### Five Sources of Blocking

A task shows `Blocked` when any of these apply:

1. **Sequential position** — not the first incomplete task in a sequential container
2. **Parent has incomplete children** — parent tasks (action groups) are always Blocked
3. **Future defer date** — `deferDate` is in the future
4. **OnHold tag** — any assigned tag has `Tag.Status === Tag.Status.OnHold`
5. **Container state** — project is OnHold (forces Blocked) or Dropped (forces Dropped)

### Overdue-Masks-Blocked

**`taskStatus = Overdue` does NOT guarantee actionability.** A sequentially-blocked task with a past effective due date shows `Overdue`, not `Blocked`. Same for `DueSoon`. This is OmniFocus's deliberate design — urgency takes display priority.

Confirmed in real data: 8/12 Overdue tasks in sequential projects were NOT the first incomplete task. Masking happens through **date inheritance** — tasks with `dueDate=null` can show Overdue via inherited `effectiveDueDate`.

---

## 6. Not Available in the API (Service Layer Responsibility)

These capabilities cannot be provided by the bridge. They must be implemented in Python.

### DueSoon Threshold
The number of days before a due date that triggers `DueSoon` status. **Not readable from the API.** Every probe (app, document, Settings, Preferences) returned undefined or errored. Must be a user-configurable parameter.

### True Actionability
`taskStatus` alone is insufficient for determining if a task can actually be worked on. The service layer needs an `isActionable` computation that checks:

- **For Overdue/DueSoon tasks:** Is this the first incomplete task in its sequential container? If not, it's masked — actually blocked despite showing Overdue/DueSoon.
- **Sequential containers** include both projects (`p.sequential=true`) and action groups (tasks with `sequential=true` and children). 37 sequential projects + 60 sequential action groups observed.
- **All other statuses can be taken at face value:** Available, Next = actionable. Blocked, Completed, Dropped = not actionable.

### Blocking Source Identification
The bridge reports `Blocked` status but not *why* a task is blocked. To determine the source, Python must check:
1. Sequential position among siblings
2. Whether the task is a parent with incomplete children
3. Whether `deferDate` is in the future
4. Whether any assigned tag has `Tag.Status.OnHold`
5. Whether the containing project is OnHold or Dropped

### Inherited Drop vs Self-Drop
Two flavors of Dropped exist:
- `active=false` (136 tasks) = task itself was dropped
- `active=true, effectiveActive=false` (528 tasks) = task is fine but container is inactive

The bridge exposes both `active` and `effectiveActive` — Python distinguishes them.

### Date Inheritance Semantics
`effectiveDueDate = min(own dueDate, parent's effectiveDueDate)` — soonest deadline in the ancestry chain wins, not just direct inheritance. OmniFocus computes this internally; the bridge reads the result.

---

## 7. Deferred (Possible But Not Implemented)

These capabilities exist in the API and are documented for future use.

### Notifications (18/2825 tasks)
`Task.Notification` objects — 13 properties. `kind` enum (`Absolute` vs `DueRelative`) determines which fire date field to access:
- Absolute: `absoluteFireDate` (Date). Accessing `relativeFireOffset` **throws**.
- DueRelative: `relativeFireOffset` (number, seconds before due). Accessing `absoluteFireDate` **throws**.

Other properties: `id`, `isSnoozed`, `repeatInterval`, `usesFloatingTimeZone`, `initialFireDate`, `nextFireDate`, `task`, `added`, `modified`, `url`.

### Attachments (6/2825 tasks)
`FileWrapper` objects — not a custom type. Properties: `type` (enum: File, Directory, Link), `preferredFilename`, `filename`, `contents` (raw data), `children`, `destination`. Standard property names (`name`, `size`, `url`) are `undefined` on FileWrapper.

Serializing `contents` (raw file data) may be impractical — consider metadata only (filename, type).

### LinkedFileURLs (0/2825 tasks)
Valid empty array on all tasks. No data observed but the collection is functional.

### Perspective Filter Rules
`archivedFilterRules` exposes a complete query language — a recursive tree of filter conditions (availability, status, tags, projects, dates, duration, search, nested AND/OR/NOT groups). `archivedTopLevelFilterAggregation` controls top-level logic ("all" = AND, null = separator). `iconColor` provides perspective color.

Too complex for initial bridge implementation. Fully documented in FINDINGS.md Section 9.13.

### Additional Tag Properties
- `tag.availableTasks` / `tag.remainingTasks` — query getters that return filtered task lists
- `tag.projects` — projects associated with this tag
- `Tag.forecastTag` — the special Forecast tag (static property)

### Additional Document/App Capabilities
- `Task.byParsingTransportText(text)` — batch task creation from TaskPaper format
- `Task.byIdentifier(id)`, `Project.byIdentifier(id)`, etc. — direct ID-based lookup
- `Perspective.favorites` — 17 favorite perspectives (could derive `isFavorite` flag)
- `project.defaultSingletonActionHolder` — purpose unclear, needs investigation vs `containsSingletonActions`

### Additional Enum Types (discovered but not needed yet)
- `Task.Notification.Kind` — Absolute, DueRelative (at minimum)
- `FileWrapper.Type` — File (at minimum, likely also Directory, Link)

---

## 8. Data Access Patterns

### Listing All Entities
| Entity | Access Path | Notes |
|--------|-----------|-------|
| Tasks | `flattenedTasks` | All tasks in database (2825) — **includes project root tasks**. Bridge extracts all of them without filtering (OmniJS iteration is expensive). Python filters root tasks using the project ID set — root tasks share `id.primaryKey` with their project |
| Projects | `flattenedProjects` | All projects (368) |
| Tags | `flattenedTags` | All tags (65) |
| Folders | `flattenedFolders` | All folders (79) |
| Perspectives | `Perspective.all` | All perspectives (57) — canonical source |

### ID Format
All entity IDs are accessed via `entity.id.primaryKey` (string). Exception: built-in perspectives have `undefined` id — key by name instead.

### Reference Serialization
When a field references another entity (e.g., `task.containingProject`), serialize as the referenced entity's `id.primaryKey`. For tags array, serialize as array of tag `id.primaryKey` values.
