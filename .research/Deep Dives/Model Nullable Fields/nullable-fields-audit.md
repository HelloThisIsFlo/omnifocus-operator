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

### Critical Discovery: OmniFocus Enum Objects Are Opaque

**Validated against live OmniFocus database (2026-03-03).**

OmniFocus Automation enum objects (e.g. `Task.Status.Available`, `Project.Status.Active`) are
opaque native objects with **no accessible properties**:

```javascript
Object.getOwnPropertyNames(Task.Status.Available)  // → []
Task.Status.Available.name       // → undefined
String(Task.Status.Available)    // → undefined
Task.Status.Available.toString() // → undefined
JSON.stringify(Task.Status.Available) // → undefined
```

This means `.name` **cannot be used** to convert any OmniFocus enum to a string. The only
working approach is manual `===` comparison against enum constants (switch-style), as the
existing `ts()` function already does for `TaskStatus`.

**Impact:** The inline `x.status ? x.status.name : null` pattern on projects, tags, and
folders is **actively broken** — it always produces `undefined`, which `JSON.stringify`
silently drops, causing Pydantic to default to `None`. This is an existing bug masked by the
nullable type annotation.

> **Note:** The 02-CONTEXT.md requirement to "remove the `ts()` switch function, use `.name`
> property instead" is **invalidated** by this finding. Update that doc when executing this
> todo.

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

**ACTIVE BUG:** The bridge uses `p.status ? p.status.name : null` — but `.name` returns
`undefined` on OmniFocus enum objects (see "Critical Discovery" above). Since `p.status` is
truthy, the expression evaluates to `undefined`, which `JSON.stringify` silently drops. The
Pydantic model then defaults to `None`. **Every entity's status is currently `None` in the
parsed models.** The nullable `| None = None` annotation is hiding this bug.

**Fix order:** Fix the bridge first (add an `es()` switch function like `ts()`), then make
the model field required.

---

## Bridge Script Audit

The bridge (`bridge.js`) uses 5 helper functions plus inline patterns to serialize OmniFocus
objects. This section audits each one, incorporating the opaque enum discovery.

**Fail-fast rule for switch functions:** All enum switch functions should **throw** on unknown
values instead of returning `null`. The `dispatch()` function's global try-catch (lines 187-208)
catches the error and writes a structured `{success: false, error: "..."}` response, so
throwing is safe and gives immediate, clear error messages.

### `d(v)` — Date helper (line 18)

```javascript
function d(v) { return v ? v.toISOString() : null; }
```

**Used by:** All date fields on tasks, projects, tags, folders (20+ call sites).

**Verdict: Keep as-is.** Correctly returns null for absent dates. Date objects are not enums —
`.toISOString()` works fine. Confirmed by live testing: `added`/`modified` always return valid
dates.

### `pk(v)` — Primary key helper (line 22)

```javascript
function pk(v) { return v ? v.id.primaryKey : null; }
```

**Used by:** `project`, `parent`, `assignedContainer`, `nextTask`, `folder`, tag/folder `parent`.

**Verdict: Keep as-is.** All relationship fields are legitimately nullable.

### `ts(s)` — Task status helper (line 39)

```javascript
function ts(s) {
    if (s === Task.Status.Available) return "Available";
    if (s === Task.Status.Blocked) return "Blocked";
    // ... 5 more cases ...
    return null;  // ← should throw instead
}
```

**Used by:** `status` on tasks (line 80), `taskStatus` on projects (line 116).

**Verdict: Keep the switch, change fallback to throw.** The switch is the only working way to
convert `Task.Status` enums to strings (`.name` returns `undefined`). However, the `return null`
fallback should become `throw new Error("Unknown TaskStatus: " + s)` for fail-fast. An unknown
status is either a bug or a new OmniFocus version — either way we want to know immediately.

The 02-CONTEXT.md requirement to "remove `ts()` and use `.name`" is **invalidated** — `.name`
does not work on OmniFocus enum objects.

**Values (7):**

| OmniFocus Constant | String | Python `TaskStatus` |
|---|---|---|
| `Task.Status.Available` | `"Available"` | `AVAILABLE` |
| `Task.Status.Blocked` | `"Blocked"` | `BLOCKED` |
| `Task.Status.Completed` | `"Completed"` | `COMPLETED` |
| `Task.Status.Dropped` | `"Dropped"` | `DROPPED` |
| `Task.Status.DueSoon` | `"DueSoon"` | `DUE_SOON` |
| `Task.Status.Next` | `"Next"` | `NEXT` |
| `Task.Status.Overdue` | `"Overdue"` | `OVERDUE` |

### NEW: `es(s)` — Entity status helper (to be created)

**Replaces:** Broken inline `x.status ? x.status.name : null` on lines 115, 156, 170.

```javascript
function es(s) {
    if (s === Project.Status.Active) return "Active";
    if (s === Project.Status.Done) return "Done";
    if (s === Project.Status.Dropped) return "Dropped";
    throw new Error("Unknown EntityStatus: " + s);
}
```

**Will be used by:**
- `status: es(p.status)` on projects (line 115)
- `status: es(g.status)` on tags (line 156)
- `status: es(f.status)` on folders (line 170)

**Note:** Uses `Project.Status.*` constants. Need to verify via UAT whether Tag and Folder
status enums use the same constants or have their own (e.g. `Tag.Status.Active`). If they
differ, may need separate helpers or additional comparisons.

**Values (3):**

| OmniFocus Constant | String | Python `EntityStatus` |
|---|---|---|
| `Project.Status.Active` | `"Active"` | `ACTIVE` |
| `Project.Status.Done` | `"Done"` | `DONE` |
| `Project.Status.Dropped` | `"Dropped"` | `DROPPED` |

### `rr(v)` — Repetition rule helper (line 26)

```javascript
function rr(v) {
    if (!v) return null;
    var st = v.scheduleType;
    return {
        ruleString: v.ruleString,
        scheduleType: st && st.name ? st.name : null,  // BROKEN: .name → undefined
    };
}
```

**Used by:** `repetitionRule` on tasks (line 100) and projects (line 136).

**Verdict: Deferred to RepetitionRule redesign.** The `scheduleType` extraction is broken for
the same reason (`.name` returns `undefined` on enum objects). Will need its own switch function
when the RepetitionRule model is redesigned. The `scheduleType` field is currently always `None`
in parsed models — same hidden bug as EntityStatus.

See `.research/Deep Dives/Repetition Rule/` and debug session
`repetition-rule-validation-failure.md`.

**Known values for future `sst()` switch:**

| OmniFocus Constant | String | Notes |
|---|---|---|
| `Task.RepetitionScheduleType.Regularly` | `"Regularly"` | Fixed calendar schedule |
| `Task.RepetitionScheduleType.FromCompletion` | `"FromCompletion"` | Relative to completion |

### `ri(v)` — Review interval helper (line 35)

```javascript
function ri(v) { return v ? { steps: v.steps, unit: v.unit } : null; }
```

**Used by:** `reviewInterval` on projects (line 139).

**Verdict: Keep as-is.** ReviewInterval is legitimately nullable. The `steps` and `unit`
properties are plain numbers/strings, not enum objects.

### Perspective: `p.identifier || null` (line 177)

```javascript
id: p.identifier || null,
```

**Verdict: Keep as-is.** Builtin perspectives genuinely have no identifier. `identifier` is a
plain string, not an enum.

---

## Enum Switch Inventory

All OmniFocus Automation enum types that need manual switch functions in bridge.js:

| Enum Type | Switch Function | Status | Values | Used On |
|-----------|----------------|--------|--------|---------|
| `Task.Status` | `ts()` | Exists (fix fallback) | 7 | Task.status, Project.taskStatus |
| `Project.Status` | `es()` | **Needs creation** | 3 | Project.status, Tag.status, Folder.status |
| `Task.RepetitionScheduleType` | `sst()` | Deferred | 2 | RepetitionRule.scheduleType |

**Common rule for all switch functions:** Throw on unknown values instead of returning null.
The `dispatch()` try-catch handles errors gracefully.

---

## Summary of Bridge Changes

| Helper / Pattern | Lines | Action |
|-----------------|-------|--------|
| `d(v)` | 18-20 | Keep as-is |
| `pk(v)` | 22-24 | Keep as-is |
| `ts(s)` | 39-48 | **Keep switch, change `return null` → `throw`** |
| `rr(v)` | 26-33 | Deferred — will be rewritten in RepetitionRule redesign |
| `ri(v)` | 35-37 | Keep as-is |
| `x.status ? x.status.name : null` | 115, 156, 170 | **Replace with `es()` switch function** |
| `p.identifier \|\| null` | 177 | Keep as-is |

---

## Action Items

### Bridge changes (JavaScript) — do first

1. **Create `es()` function** — EntityStatus switch using `Project.Status.*` constants, with
   `throw` on unknown values. Replace broken inline `.status.name` on projects (line 115),
   tags (line 156), and folders (line 170).
2. **Fix `ts()` fallback** — Change `return null` to `throw new Error("Unknown TaskStatus: " + s)`.
3. **Verify `Project.Status.*` constants work for tags and folders** — Need UAT to confirm
   whether `g.status === Project.Status.Active` works, or if tags/folders use different
   constants (e.g. `Tag.Status.Active`).

### Model changes (Python) — after bridge is fixed

4. **Make 6 timestamp fields required** — Remove `| None = None` from `added`/`modified` on
   Task, Tag, Folder. These are confirmed always-present by live testing.
5. **Make 3 status fields required** — Remove `| None = None` from `status: EntityStatus` on
   Project, Tag, Folder. Only do this AFTER the bridge `es()` function is working.
6. **Update tests** — Remove test cases that set `added=None`, `modified=None`, or
   `status=None` — those scenarios don't exist in the real domain.

### Deferred

7. **RepetitionRule.schedule_type** — Will be addressed in RepetitionRule model redesign.
   The `rr()` helper's `.name` access is broken for the same reason; needs its own switch.
8. **Update 02-CONTEXT.md** — Remove the invalidated requirement about replacing `ts()`
   with `.name`.
