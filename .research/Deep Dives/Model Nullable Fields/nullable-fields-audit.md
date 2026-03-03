# Model Nullable Fields Audit

Audit of every `| None` field across all Pydantic models. Goal: enforce fail-fast by ensuring
only fields that are **genuinely optional in the OmniFocus domain** are nullable.

> **Audit date:** 2026-03-03
> **Outcome:** 8 fields identified as incorrectly nullable — should be required.

---

## How the Bridge Produces Nulls

The JXA bridge script (`bridge.js`) uses helper functions that return `null` for falsy values:

```javascript
function d(v)  { return v ? v.toISOString() : null; }   // dates
function pk(v) { return v ? v.id.primaryKey : null; }    // relationship IDs
function rr(v) { if (!v) return null; /* ... */ }        // repetition rules
function ri(v) { return v ? { steps: v.steps, unit: v.unit } : null; }  // review interval
```

The Python models mirror this defensiveness with `| None = None`. But in many cases, OmniFocus
**always** provides the value — the JS truthiness check is just paranoia, not a real domain
possibility. For those fields, the model should be required so Pydantic blows up immediately
if something unexpected happens.

---

## Verdict: Legitimately Nullable (24 fields)

These fields are nullable because the **OmniFocus domain** genuinely allows absence.

### ActionableEntity — Dates (10 fields)

All inherited by both Task and Project.

| Field | Why None is valid |
|-------|-------------------|
| `due_date` | Not every task has a due date |
| `defer_date` | Not every task is deferred |
| `effective_due_date` | Computed — None when no due date exists up the hierarchy |
| `effective_defer_date` | Computed — None when no defer date exists up the hierarchy |
| `completion_date` | None if not yet completed |
| `effective_completion_date` | Computed — None if not completed |
| `planned_date` | Not every task has a planned date |
| `effective_planned_date` | Computed — None when no planned date exists |
| `drop_date` | None if not dropped |
| `effective_drop_date` | Computed — None if not dropped |

### ActionableEntity — Other (2 fields)

| Field | Why None is valid |
|-------|-------------------|
| `estimated_minutes` | Users don't always set duration estimates |
| `repetition_rule` | Most tasks/projects don't repeat |

### Task — Relationships (3 fields)

| Field | Why None is valid |
|-------|-------------------|
| `project` | Inbox tasks have no containing project |
| `parent` | Only subtasks have a parent task |
| `assigned_container` | Inbox tasks may have no assigned container |

### Project — Review (3 fields)

| Field | Why None is valid |
|-------|-------------------|
| `last_review_date` | A never-reviewed project has no last review date |
| `next_review_date` | A never-reviewed project has no next review date either |
| `review_interval` | OmniFocus defaults to weekly, but the bridge `ri()` function returns null for falsy — edge case projects may not expose one |

### Project — Relationships (2 fields)

| Field | Why None is valid |
|-------|-------------------|
| `next_task` | Empty or fully-completed projects have no next action |
| `folder` | Projects can live at the library root, outside any folder |

### Tag / Folder — Relationships (2 fields)

| Field | Model | Why None is valid |
|-------|-------|-------------------|
| `parent` | Tag | Top-level tags have no parent |
| `parent` | Folder | Root-level folders have no parent |

### Perspective (1 field)

| Field | Why None is valid |
|-------|-------------------|
| `id` | Builtin perspectives (Inbox, Projects, etc.) have no user-facing identifier. This is why Perspective extends `OmniFocusBaseModel` instead of `OmniFocusEntity`. |

### RepetitionRule (1 field)

| Field | Why None is valid |
|-------|-------------------|
| `schedule_type` | **TEMPORARY** — model is known-incomplete. Tracked for redesign in `.research/Deep Dives/Repetition Rule/`. Will become required after the RepetitionRule model is redesigned. |

---

## Verdict: Should Be Required (8 fields)

These fields are currently `| None = None` but OmniFocus **always** provides them. Making them
required enforces fail-fast: if the bridge ever returns null for one of these, Pydantic
validation raises immediately at the system boundary instead of silently propagating `None`.

### Timestamps: `added` and `modified` (6 fields)

**Affected models:** Task (`_task.py:34-35`), Tag (`_tag.py:25-26`), Folder (`_folder.py:25-26`)

```python
# Current (wrong):
added: AwareDatetime | None = None
modified: AwareDatetime | None = None

# Should be:
added: AwareDatetime
modified: AwareDatetime
```

**Reasoning:** OmniFocus automatically sets `added` when any entity is created and updates
`modified` on every change. These are system-managed timestamps, not user-optional fields.
A JS `Date` object is always truthy, so the bridge's `d()` helper only returns null if the
OmniFocus property itself is `null`/`undefined` — which doesn't happen for `added`/`modified`
on any entity type. If it ever did, that would be a data corruption scenario that should
surface as a validation error, not a silent `None`.

### Status: `status` (3 fields)

**Affected models:** Project (`_project.py:31`), Tag (`_tag.py:29`), Folder (`_folder.py:29`)

Note: Task.status is already correctly required (`status: TaskStatus` with no `| None`).

```python
# Current (wrong):
status: EntityStatus | None = None

# Should be:
status: EntityStatus
```

**Reasoning:** Every project, tag, and folder in OmniFocus has a lifecycle status:
- Projects: Active, Done, Dropped, On Hold
- Tags: Active, Dropped
- Folders: Active, Dropped

The bridge checks `p.status ? p.status.name : null` — but `p.status` is an Omni Automation
enum object, which is always truthy. There is no "statusless" entity in OmniFocus. A null
status would indicate data corruption or a bridge bug and should fail loudly.

---

## Bridge Script Audit

The bridge (`bridge.js`) uses 5 helper functions plus inline patterns to serialize OmniFocus
objects. This section audits each one for consistency with the fail-fast model changes above.

### `d(v)` — Date helper (line 18)

```javascript
function d(v) { return v ? v.toISOString() : null; }
```

**Used by:** All date fields on tasks, projects, tags, folders (20+ call sites).

**Verdict: Keep as-is.** The function itself is fine — it correctly returns null for absent dates.
The issue isn't the helper; it's that the Python model was nullable for fields where `d()` never
actually returns null (i.e. `added`/`modified`). Tightening the Python model is sufficient; if
`d()` ever returns null for `added`/`modified`, Pydantic catches it.

### `pk(v)` — Primary key helper (line 22)

```javascript
function pk(v) { return v ? v.id.primaryKey : null; }
```

**Used by:** `project`, `parent`, `assignedContainer`, `nextTask`, `folder`, tag `parent`,
folder `parent`.

**Verdict: Keep as-is.** All relationship fields are legitimately nullable. The helper is correct.

### `ts(s)` — Task status helper (line 39)

```javascript
function ts(s) {
    if (s === Task.Status.Available) return "Available";
    if (s === Task.Status.Blocked) return "Blocked";
    // ... 5 more cases ...
    return null;
}
```

**Used by:** `status` on tasks (line 80), `taskStatus` on projects (line 116).

**Verdict: Should be simplified.** This redundant if-chain manually maps every `Task.Status`
enum value to the exact string that `.name` already produces. The documented requirement
(02-CONTEXT.md) says:

> Bridge script simplification: remove the `ts()` switch function, use `.name` property
> instead — deferred to Phase 8 but confirms models should validate against the same string
> values `.name` produces

Replace with:

```javascript
// Task status — just pass the string, let Pydantic validate via TaskStatus enum
status: t.taskStatus.name,        // tasks (line 80)
taskStatus: p.taskStatus.name,    // projects (line 116)
```

This is better for fail-fast: if OmniFocus ever adds a new `Task.Status` value, the current
`ts()` silently returns `null` (line 47), which would pass Python validation since `Task.status`
is required — causing a confusing Pydantic error about null on a required field. With `.name`,
the bridge passes the new string through and Pydantic rejects it with a clear "value is not a
valid enumeration member" error naming the unexpected value.

### `rr(v)` — Repetition rule helper (line 26)

```javascript
function rr(v) {
    if (!v) return null;
    var st = v.scheduleType;
    return {
        ruleString: v.ruleString,
        scheduleType: st && st.name ? st.name : null,
    };
}
```

**Used by:** `repetitionRule` on tasks (line 100) and projects (line 136).

**Verdict: Will change in RepetitionRule redesign.** The null check (`if (!v) return null`) is
correct — not all items repeat. The internal `scheduleType` extraction is a known workaround
(see `.research/Deep Dives/Repetition Rule/` and debug session
`repetition-rule-validation-failure.md`). This entire helper will be rewritten when the
RepetitionRule model is redesigned. Leave as-is for now.

### `ri(v)` — Review interval helper (line 35)

```javascript
function ri(v) { return v ? { steps: v.steps, unit: v.unit } : null; }
```

**Used by:** `reviewInterval` on projects (line 139).

**Verdict: Keep as-is.** ReviewInterval is legitimately nullable.

### Inline status: `x.status ? x.status.name : null` (lines 115, 156, 170)

```javascript
status: p.status ? p.status.name : null,   // Project (line 115)
status: g.status ? g.status.name : null,   // Tag (line 156)
status: f.status ? f.status.name : null,   // Folder (line 170)
```

**Verdict: Simplify to `.status.name`.** Since we're making `status: EntityStatus` required on
the Python models, the bridge should match. OmniFocus always provides a status on projects, tags,
and folders — the ternary is defensive JS that masks potential issues. Replace with:

```javascript
status: p.status.name,   // Project
status: g.status.name,   // Tag
status: f.status.name,   // Folder
```

If `.status` is ever null (data corruption), crashing in the bridge is better than propagating
null to Python. Fail-fast at the earliest possible point.

### Perspective: `p.identifier || null` (line 177)

```javascript
id: p.identifier || null,
name: p.name,
builtin: !p.identifier,
```

**Verdict: Keep as-is.** Builtin perspectives genuinely have no identifier.

---

## Summary of Bridge Changes

| Helper / Pattern | Lines | Action |
|-----------------|-------|--------|
| `d(v)` | 18-20 | Keep as-is |
| `pk(v)` | 22-24 | Keep as-is |
| `ts(s)` | 39-48 | **Remove.** Replace calls with `.taskStatus.name` / `.name` |
| `rr(v)` | 26-33 | Leave for now — will change in RepetitionRule redesign |
| `ri(v)` | 35-37 | Keep as-is |
| `x.status ? x.status.name : null` | 115, 156, 170 | **Simplify to `.status.name`** |
| `p.identifier \|\| null` | 177 | Keep as-is |

---

## Action Items

### Model changes (Python)

1. **Make 8 fields required** — Remove `| None = None` from the 6 timestamp fields and 3
   status fields listed above.
2. **Update tests** — Any test that explicitly sets `added=None`, `modified=None`, or
   `status=None` for these models is testing a scenario that doesn't exist in the real domain.
   Remove those test cases or replace them with valid values.

### Bridge changes (JavaScript)

3. **Remove `ts()` function** — Replace `ts(t.taskStatus)` with `t.taskStatus.name` on tasks
   (line 80) and `ts(p.taskStatus)` with `p.taskStatus.name` on projects (line 116). Delete
   the `ts` function definition (lines 39-48) and its test export.
4. **Simplify inline status** — Replace `x.status ? x.status.name : null` with `x.status.name`
   on projects (line 115), tags (line 156), and folders (line 170).

### Deferred

5. **RepetitionRule.schedule_type** — Will be addressed separately when the RepetitionRule
   model is redesigned (see `.research/Deep Dives/Repetition Rule/`).
6. **`rr()` helper** — Will be rewritten as part of the same RepetitionRule redesign.
