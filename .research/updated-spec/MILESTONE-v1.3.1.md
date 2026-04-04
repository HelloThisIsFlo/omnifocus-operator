# Milestone v1.3.1 — Inbox as First-Class Value

## Goal

Eliminate null overloading for inbox across the entire API surface. Today, `null` means three different things depending on context: "this task is in the inbox" (parent field, move destination), "clear this value" (patch semantics), and "no filter" (query parameters). The internal type system (`PatchOrNone` vs `PatchOrClear`) disambiguates, but agents see raw JSON where all three look like `null`.

After this milestone, inbox has a single, explicit representation everywhere: the system location `$inbox`. A new `project` field on tasks provides containing-project information at any nesting depth. The `inInbox` boolean disappears from output (derivable from `project.id == "$inbox"`) but remains as a filter parameter. The `PatchOrNone` type alias is eliminated.

No new tools. This milestone changes contracts, models, and the resolver — not the tool surface.

---

## What to Build

### System Location Namespace: the `$` Prefix

The `$` character is reserved as a prefix for system locations. Strings starting with `$` bypass name resolution entirely — they are never interpreted as OmniFocus IDs or entity names. Currently, `$inbox` is the only system location.

**Resolver precedence** (applies to all fields that accept entity references — `parent`, `moveTo`, `project` filter, etc.):

1. **`$`-prefixed** → system location lookup. No name resolution, no substring matching. Immediate.
2. **Exact ID match** → OmniFocus-generated identifier (e.g., `pJKx9xL5beb`).
3. **Name substring match** → case-insensitive. Error if multiple matches.

This precedence order means `$inbox` never collides with name resolution, regardless of what projects exist in the user's OmniFocus database.

**Collision policy:** The `$` prefix is reserved. A project or task whose name literally starts with `$` (e.g., a project named `$inbox` or `$budget`) can only be referenced by its OmniFocus ID. This is an intentional trade-off: the edge case is extremely niche (who names a project `$inbox` when OmniFocus already has an Inbox?), and the escape hatch (use the ID) always works.

### New Model Types: `ProjectRef` and `TaskRef`

Two new reference types replace the single `ParentRef`:

```python
class ProjectRef(OmniFocusBaseModel):
    id: str
    name: str

class TaskRef(OmniFocusBaseModel):
    id: str
    name: str
```

These follow the existing `TagRef(id, name)` pattern — minimal, no redundant fields. They replace the existing `ParentRef(type, id, name)` model, which is removed after this milestone.

**Parent field:** `parent` on Task uses a **tagged object** pattern for discrimination — the key name identifies the parent type:

```json
{"parent": {"project": {"id": "pXyz", "name": "Work"}}}
{"parent": {"task": {"id": "tAbc", "name": "Buy Groceries"}}}
```

Exactly one key (`project` or `task`) must be present — same "exactly one key" validation pattern used by `MoveAction`. No `type` field needed; the key IS the discriminator. This avoids `exclude_defaults` issues that occur with `Literal` discriminator fields when serializing with Pydantic's `exclude_defaults=True`.

**Project field:** The new `project` field on Task always uses `ProjectRef` directly (flat, no wrapper). No union needed — it's always a project (or `$inbox`).

### Task Output Model Changes

**New field: `project`** — `ProjectRef`, always present.

The containing project for this task, resolved by walking up the hierarchy. For tasks at any nesting depth within a project, this points to the project. For tasks at any nesting depth within the inbox, this is `ProjectRef(id="$inbox", name="Inbox")`.

The data source already exists: the SQLite column `containingProjectInfo` tracks containing project independently from the direct parent. No new queries needed.

**Changed field: `parent`** — `ProjectRef | TaskRef`, always present, never null.

The direct structural parent. For root-level tasks, this is a project (or `$inbox`). For subtasks, this is the parent task. The field is never null — every task has a parent (the inbox virtual container acts as the parent for root inbox tasks).

**Removed field: `inInbox`** — removed from output.

Derivable from `project.id == "$inbox"`. Keeping it would create redundancy with the new `project` field.

**Inbox representation in both fields:**
- `id`: `"$inbox"`
- `name`: `"Inbox"` (human-readable display name, not the system prefix)

**Examples at every nesting level:**

```json
// Root inbox task ("Buy Groceries")
{"parent": {"project": {"id": "$inbox", "name": "Inbox"}},
 "project": {"id": "$inbox", "name": "Inbox"}}

// Subtask of inbox task ("Get Milk", child of "Buy Groceries")
{"parent": {"task": {"id": "tBuyGroceries", "name": "Buy Groceries"}},
 "project": {"id": "$inbox", "name": "Inbox"}}

// Root project task ("Write Report", in project "Work")
{"parent": {"project": {"id": "pXyz", "name": "Work"}},
 "project": {"id": "pXyz", "name": "Work"}}

// Subtask of project task ("Draft Intro", child of "Write Report")
{"parent": {"task": {"id": "tWriteReport", "name": "Write Report"}},
 "project": {"id": "pXyz", "name": "Work"}}
```

For root-level tasks, `parent` and `project` point to the same entity (both the project, or both `$inbox`). For subtasks, they diverge: `parent` is the parent task, `project` is the containing project.

### Write Changes: `add_tasks`

The `parent` parameter accepts `"$inbox"` as an explicit inbox destination.

| Input | Behavior |
|-------|----------|
| `parent` omitted | Inbox. Natural default — most tasks start in inbox. |
| `parent: null` | Inbox + warning: "To target the inbox explicitly, use `$inbox` or omit the `parent` field." |
| `parent: "$inbox"` | Inbox. Explicit form. |
| `parent: "pXyz123"` | That container (project or task ID). |
| `parent: "My Project"` | Name resolution — case-insensitive substring match. Error if multiple matches. |

The `null` behavior is not backward compatibility — it's **intuitive compatibility**. An agent sending `null` is saying "I have no parent for this," which naturally results in inbox. The warning educates without blocking.

### Write Changes: `edit_tasks` Move Actions

The `beginning` and `ending` fields on `MoveAction` accept `"$inbox"` as a container value.

| Input | Behavior |
|-------|----------|
| `ending: "$inbox"` | Move to inbox (end). |
| `beginning: "$inbox"` | Move to inbox (beginning). |
| `ending: "pXyz123"` | Move to that container. |
| `ending: null` | **Error.** Not deprecated — hard error. |
| UNSET | No move. |

`before` and `after` are unchanged — they take sibling task **IDs only** (not project IDs, not `$inbox`). These fields position a task relative to a sibling within the same container. `$inbox` is a container, not a sibling — using it in `before`/`after` is a type error.

**Type system change:** `beginning` and `ending` change from `PatchOrNone[str]` to `Patch[str]`. The `PatchOrNone` type alias (`Union[T, None, _Unset]`) existed solely because these fields needed null to carry domain meaning. With `"$inbox"` replacing null-as-inbox, the fields become simple `Patch[str]` (`Union[T, _Unset]`) — either set to a string value or unset.

**`PatchOrNone` elimination:** After this change, `PatchOrNone` has no remaining uses and can be removed from `contracts/base.py`. One less concept in the type vocabulary.

### Filter Changes: `list_tasks`

**`inInbox` boolean filter — kept:**

| Value | Meaning |
|-------|---------|
| `true` | Inbox tasks only |
| `false` | Non-inbox tasks only |
| omitted | No filter (all tasks) |

The boolean survives because it's the only way to express `false` (negation). There is no equivalent of "NOT $inbox" in the project filter.

**`project` filter — accepts `$inbox`:**

`project: "$inbox"` is accepted and equivalent to `inInbox: true`. The resolver detects the `$` prefix and routes to system location handling instead of name substring matching.

`project: "inbox"` (no `$` prefix) does name substring matching against project names only — it does NOT match the real inbox. A project named "Finance Inbox" would match; the OmniFocus inbox would not.

**Contradictory filter handling:**

`project: "$inbox"` combined with `inInbox: false` is an error: "Contradictory filters — `project: '$inbox'` selects inbox tasks, but `inInbox: false` excludes them."

`project: "$inbox"` combined with `inInbox: true` is redundant but accepted silently.

**Cross-filter composition:** `inInbox: true` combined with a real project filter (e.g., `project: "Work"`) is AND-composed. The intersection is always empty (inbox tasks have no project), so the result is empty — but the system returns a warning: "No results: `inInbox: true` selects tasks with no project, so combining with a project filter always yields an empty set." This is not an error — the filters are logically valid, just pointless together.

### Name-Based Resolution for Entity References

All fields that accept entity references (`parent` on add_tasks, `beginning`/`ending`/`before`/`after` on edit_tasks move, `project`/`folder` on list filters) gain name-based resolution. Currently these fields only accept OmniFocus IDs; after this milestone, agents can use human-readable names.

**Resolution follows the three-step precedence defined above:**
1. `$`-prefixed → system location (immediate)
2. Exact OmniFocus ID match (checked against the database)
3. Case-insensitive substring name match → error if multiple matches, error if zero matches

**Applies to:** projects, folders, parent tasks (in `parent` field), and container references (in move actions). Tags already resolve by name (implemented in v1.2).

**Error on multiple matches:** Same pattern as existing tag resolution. If `parent: "Work"` matches both "Work - Personal" and "Work - Professional", the error lists all matches with their IDs so the agent can disambiguate.

**Error on zero matches:** Helpful error with suggestions if a close match exists, or guidance to check the entity list.

**Interaction with `$` prefix:** Name resolution is never attempted on `$`-prefixed strings. This is the guarantee that makes `$inbox` collision-proof — the `$` check happens at step 1, before name resolution at step 3.

### Project Tool Behavior

**`get_project("$inbox")` — descriptive error:**

Inbox is a system location, not a project. The `Project` model has required fields that don't apply to inbox (review dates, review interval, urgency, availability, etc.). Fabricating these values would be dishonest and could mislead agents into trying to edit inbox "project" properties.

Error message: "Inbox is a system location, not a project. Use `list_tasks` with `project: '$inbox'` or `inInbox: true` to query inbox tasks."

**`list_projects` — excludes inbox:**

Inbox does not appear in `list_projects` results. Same reasoning: inbox can't conform to the `Project` model without fabrication.

**Warning when search would have matched "Inbox":** Only when a name filter is provided: if the filter string would have substring-matched "Inbox" (using the same case-insensitive substring logic as regular project matching), the response includes a warning: "Your search also matched the system Inbox, which is not a project. Use `list_tasks` with `inInbox: true` or `project: '$inbox'` to query inbox tasks." No name filter = no warning.

Real projects that happen to match are still returned normally — only the inbox match triggers the warning.

---

## Key Design Decisions

- **`$` prefix, not plain string.** A plain `"inbox"` sentinel collides with name-based resolution (upcoming feature). The `project` filter already does substring matching — `project: "inbox"` would match projects named "Finance Inbox." And when name-based resolution for `parent`/`moveTo` arrives, `parent: "inbox"` becomes ambiguous: sentinel or name lookup? The `$` prefix creates a syntactically disjoint namespace that can never collide with name resolution.
- **`$inbox` works in the `list_tasks` project filter.** Consistency: `$inbox` should work everywhere it can. Agents that think of inbox as a container naturally reach for `project: "$inbox"`. The boolean filter remains for negation (`inInbox: false`), which the project filter can't express.
- **`inInbox` boolean removed from output, kept as filter.** On the output side, `project.id == "$inbox"` carries the same information — the boolean is redundant. On the filter side, the boolean is irreplaceable: `inInbox: false` has no equivalent in the project filter (you can't negate a project match). Different survival criteria, different outcomes.
- **Error, not deprecation, for `ending: null`.** No one is using this API yet — there are no agents to break. Deprecation warnings are for production APIs with existing consumers. This is pre-release: the right time to make breaking changes is now.
- **Warning, not error, for `parent: null` on add_tasks.** This is "intuitive compatibility" — an agent sending `null` is expressing a natural intent ("no parent specified"), and inbox is the correct result. The warning educates toward `$inbox` without blocking the operation.
- **`get_project("$inbox")` errors, `list_projects` excludes inbox.** The `Project` model has required fields (review dates, review interval, urgency, availability) that are meaningless for inbox. Fabricating values would create a "virtual project" that agents might try to edit — leading to confusing errors downstream. Inbox is project-like *on tasks* (parent, project fields, filtering) but not project-like *as an entity* (no review schedule, no status, no dates). The abstraction extends exactly as far as the data supports.
- **New `project` field on Task, not just updated `parent`.** The `parent` field is the direct structural parent (task or project). The `project` field is the containing project at any nesting depth. These are different information: for subtasks, `parent` is the parent task while `project` is the containing project. Without the `project` field, a subtask of an inbox task has no way to signal "I'm in the inbox" — its parent is a task, not `$inbox`. The `project` field solves this cleanly using data already available in the SQLite `containingProjectInfo` column.
- **`name: "Inbox"`, not `name: "$inbox"`.** The `$` prefix is an API convention for the ID — a system reference. The name is a human-readable display label. OmniFocus calls it "Inbox", not "$inbox". Same pattern as every other entity: ID is for API calls, name is for display.
- **`parent` is never null.** Every task in OmniFocus is either in a project or in the inbox. With inbox represented as `ProjectRef(id="$inbox", name="Inbox")`, there's no case where parent has no value. This simplifies the type: `ProjectRef | TaskRef` with no optionality.

---

## Key Acceptance Criteria

### Task Output

- Every task has a `project` field with `id` and `name`. Never null, never absent.
- Inbox tasks at any nesting depth have `project: {id: "$inbox", name: "Inbox"}`.
- Project tasks at any nesting depth have `project: {id: "<projectId>", name: "<projectName>"}`.
- Every task has a `parent` field. Never null, never absent.
- Root inbox tasks: `parent` represents `$inbox` as a project-type parent.
- Root project tasks: `parent` represents the project.
- Subtasks: `parent` represents the parent task.
- Agents can distinguish project parents from task parents in the JSON (discriminator mechanism present).
- `inInbox` field no longer appears in task output (not in JSON, not in JSON Schema).
- `parent` and `project` are identical for root-level tasks (both point to the same project or `$inbox`).
- `parent` and `project` diverge for subtasks (`parent` = parent task, `project` = containing project).

### Writes

- `add_tasks` with `parent: "$inbox"` creates task in inbox.
- `add_tasks` with `parent` omitted creates task in inbox.
- `add_tasks` with `parent: null` creates task in inbox and returns a warning.
- `edit_tasks` with `ending: "$inbox"` moves task to inbox.
- `edit_tasks` with `beginning: "$inbox"` moves task to inbox (beginning).
- `edit_tasks` with `ending: null` returns an error (not a warning, not accepted).
- `edit_tasks` with `beginning: null` returns an error.
- `before` and `after` on `MoveAction` do not accept `$inbox` (they take sibling task IDs).

### Filters

- `list_tasks(inInbox=true)` returns inbox tasks (including full hierarchy — subtasks of inbox tasks).
- `list_tasks(inInbox=false)` returns non-inbox tasks only.
- `list_tasks(project="$inbox")` returns the same results as `inInbox: true`.
- `list_tasks(project="inbox")` does NOT return inbox tasks — only tasks in projects whose name contains "inbox".
- `list_tasks(project="$inbox", inInbox=false)` returns an error (contradictory).
- `list_tasks(project="$inbox", inInbox=true)` works (redundant but accepted).

### Project Tools

- `get_project("$inbox")` returns a descriptive error, not a project.
- `list_projects` results never include an inbox entry.
- `list_projects` with a name filter that would have substring-matched "Inbox" includes a warning about the system inbox.

### Type System

- `PatchOrNone` type alias is removed from `contracts/base.py`.
- `MoveAction.beginning` and `MoveAction.ending` use `Patch[str]` (not `PatchOrNone[str]`).
- `ProjectRef` and `TaskRef` models exist as standalone types (like `TagRef`).
- `ParentRef` model is removed (replaced by `ProjectRef | TaskRef` union).

### Resolver

- Any string starting with `$` is treated as a system location, not a name or ID.
- `$inbox` resolves to the inbox in all contexts where entity references are accepted.
- An unrecognized system location (e.g., `$trash`) returns a helpful error listing valid system locations.
- A project literally named `$inbox` is not reachable by name — only by its OmniFocus ID.

### Name Resolution

- `add_tasks` with `parent: "My Project"` resolves to the project via case-insensitive substring match.
- `add_tasks` with `parent: "Work"` where multiple projects match "Work" returns an error listing all matches with IDs.
- `add_tasks` with `parent: "nonexistent"` returns a helpful error.
- `edit_tasks` with `ending: "My Project"` resolves the container by name (same resolution logic).
- `edit_tasks` with `before: "Task Name"` resolves the sibling task by name.
- Name resolution follows the three-step precedence: `$` prefix → ID match → name match.
- `$`-prefixed strings never enter name resolution (step 1 short-circuits).
- Resolution works for projects, folders, and tasks in all relevant fields.

---

## Decision Log

This log captures the major design decisions made during the v1.3.1 design conversation, including alternatives considered, what changed minds, and where the final call was opinionated. Ordered roughly by the flow of discussion, not by importance.

### DL-1: String sentinel instead of null overloading

**Decision:** Use an explicit string value to represent inbox, replacing `null` in all contexts where null previously meant "inbox."

**Alternatives considered:**
- **Option A — String sentinel** (chosen direction): Replace null-as-inbox with a string like `"inbox"`.
- **Option B — Structured inbox object** (`{"inbox": true}`): Type-safe but heavyweight. Rejected — too verbose for write operations.
- **Option C — Lean into the boolean**: Keep `inInbox: true` as the canonical read-side signal, use sentinel only for writes. Partially adopted (boolean kept for filters) but the string sentinel became the primary representation.
- **Option D — Status quo** (better docs only): The overload is technically consistent internally (`PatchOrNone` exists). But agent-facing JSON doesn't carry type metadata — all nulls look the same. Rejected.

**What decided it:** The internal type system already disambiguated (`PatchOrNone` vs `PatchOrClear`), but agents see raw JSON. An agent reading `"ending": null` has no way to know this is "inbox" vs "clear." Explicit > implicit.

### DL-2: `$inbox` with prefix, not plain `"inbox"`

**Decision:** Use `$inbox` (dollar-sign prefix) instead of plain `"inbox"`.

**The initial position** was plain `"inbox"` — simple, readable, and "collision is a non-issue because OmniFocus IDs are opaque."

**What changed the mind:** Two things:
1. The `list_tasks` project filter already does **case-insensitive substring matching**. `project: "inbox"` would match projects named "Finance Inbox." If `"inbox"` were also the inbox sentinel, the same string would mean two different things in the same field.
2. **Name-based resolution is coming** (planned todo). Once `parent: "My Project"` works, `parent: "inbox"` becomes genuinely ambiguous: is it the sentinel or a name lookup for a project containing "inbox"?

The `$` prefix creates a syntactically disjoint namespace. The resolver checks for `$` *before* any name resolution — no ambiguity is possible.

**Why not a more exotic prefix** (`==INBOX==`, unicode, etc.)? The `$` convention is well-known in programming (shell variables, template expressions). It signals "system value" without being ugly. The collision scenario (someone naming a project `$inbox`) is extremely niche, and the escape hatch (use the OmniFocus ID) always works.

### DL-3: Keep `inInbox` as a filter, remove from output

**Decision:** `inInbox: bool` stays on `list_tasks` as a filter parameter. `inInbox` is removed from the Task output model.

**Why keep the filter:** The `project` filter can't express negation. `inInbox: false` ("give me non-inbox tasks") has no equivalent — you can't say `project: "NOT $inbox"`. The boolean is the only way to express this.

**Why remove from output:** With the new `project` field, `inInbox` is redundant in output. `project.id == "$inbox"` carries the same information. Two fields expressing the same thing is noise.

**The hesitation:** Initially leaned toward removing `inInbox` from output early in the conversation. Then wavered when considering subtasks of inbox tasks (they have `parent: TaskRef`, not `$inbox`). The new `project` field resolved this — it always shows the containing project regardless of nesting depth, making the boolean truly redundant.

### DL-4: `project: "$inbox"` works in the list_tasks filter

**Decision:** Accept `$inbox` in the `project` filter parameter on `list_tasks`, equivalent to `inInbox: true`.

**The dilemma:** `$inbox` works everywhere else (writes, output). Not accepting it in the project filter felt inconsistent — "you can use `$inbox` to move a task, you can see `$inbox` in the output, but you can't filter by `$inbox`?"

**The counterargument (initially favored):** The project filter does name matching. Inbox isn't a project. Mixing them adds magic. A helpful error could guide agents to `inInbox: true`.

**What tipped it:** Consistency won. The resolver already handles `$` prefix — it just needs to work in the filter context too. Agents that think "inbox is a container" naturally reach for `project: "$inbox"`. The boolean exists for the negation case that `project` can't express. Two valid entry points to the same behavior.

### DL-5: Error, not deprecation, for `ending: null`

**Decision:** `ending: null` and `beginning: null` on move actions produce a hard error.

**Why not deprecation with warning?** No one is using this API yet. Deprecation is for production APIs with existing consumers. This project explicitly does not care about backward compatibility at this stage — the goal is the cleanest possible interface.

**Philosophical note:** `ending: null` was arguably consistent with patch semantics ("clear the container" → "no container" → inbox). The counter: the agent thinks "move to inbox," not "clear the container reference which as a side effect places the task in inbox." Aligning syntax with intent — not just with side effects — prevents confusion when the intent/effect distinction matters later.

**Additional supporting observation:** The action fields already don't have full patch semantics. `lifecycle: null` doesn't work. `ending: null` was the odd one out, not the norm. Removing it makes actions more internally consistent.

### DL-6: `parent: null` on add_tasks — warning, not error

**Decision:** On `add_tasks`, `parent: null` is accepted (results in inbox) with a warning suggesting `$inbox` or omitting the field.

**Framing:** This is not backward compatibility — it's **intuitive compatibility**. An agent sending `parent: null` is saying "I don't have a parent for this task," which naturally means inbox. Erroring on this would be needlessly hostile for a correct intent.

**Why not silent acceptance?** The warning educates agents toward the explicit `$inbox` syntax, which will matter more when name-based resolution arrives and the `parent` field becomes more expressive.

### DL-7: New `project` field on Task output

**Decision:** Add a `project` field (`ProjectRef`) to the Task output model, alongside the existing `parent` field.

**The problem it solves:** Without this field, a subtask of an inbox task shows `parent: TaskRef(...)` — there's nothing in the output indicating it's in the inbox. The agent would need to recursively walk up the parent chain to discover the root container. With the `project` field, the containing project (or `$inbox`) is always one field access away, regardless of nesting depth.

**Why it's cheap:** The SQLite database already tracks `containingProjectInfo` as a separate column from `parent`. The current `_build_parent_ref` function reads both but collapses them into one field. This change stops collapsing and exposes both.

**Relationship between `parent` and `project`:**
- Root-level tasks: identical (both point to the project or `$inbox`)
- Subtasks: diverge (`parent` = parent task, `project` = containing project)

### DL-8: `get_project("$inbox")` errors, `list_projects` excludes inbox

**Decision:** Inbox is NOT a virtual project in the project tools.

**The initial position** was "make it work" — include inbox in `list_projects`, make `get_project("$inbox")` return a project. The reasoning: if inbox behaves like a project on tasks, it should behave like a project everywhere.

**What changed the mind immediately:** The `Project` model has required fields that are meaningless for inbox: `last_review_date`, `next_review_date`, `review_interval` (all required, per BRIDGE-SPEC), plus `urgency`, `availability`, `url`, `added`, `modified`. Fabricating these values would create a "virtual project" that:
1. Contains dishonest data (when was "inbox" created? what's its review interval?)
2. Tempts agents to edit inbox properties (set review schedule, change availability)
3. Requires special-case handling for every project operation

**The principle:** Inbox is project-like *where it makes sense* (task containment, parent references, filtering) but not where it would require fabrication (entity-level operations). The abstraction extends exactly as far as the data supports — no further.

### DL-9: `parent` is never null

**Decision:** The `parent` field on Task is always populated — `ProjectRef | TaskRef`, no `None`.

**Why this works:** Every task in OmniFocus is either in a project or in the inbox. With inbox represented as `ProjectRef(id="$inbox", name="Inbox")`, there's no case where a task lacks a parent. This eliminates null from the parent field entirely — one fewer thing agents need to check.

### DL-10: `name: "Inbox"` not `name: "$inbox"`

**Decision:** The `$` prefix is for the ID (system reference). The name is the human-readable display label: `"Inbox"`.

**Rationale:** Same pattern as every other entity. A project's ID is `pJKx9xL5beb` but its name is "Work." The ID is for API calls, the name is for display. Putting `$` in the display name would be like showing the database primary key in the UI.

### DL-11: Separate `ProjectRef` / `TaskRef` types instead of single `ParentRef`

**Decision:** Replace the single `ParentRef(type, id, name)` with separate `ProjectRef(id, name)` and `TaskRef(id, name)` types. The `parent` field is a union of both.

**Why:** The `project` field on Task is always a project — it doesn't need a `type` discriminator. Using `ProjectRef(id, name)` (matching the existing `TagRef` pattern) is cleaner than `ParentRef(type="project", id, name)` where the type is always the same value. The `parent` field needs discrimination (is it a project or task parent?), which the union provides — implementation decides the JSON discriminator mechanism.

### DL-12: Tagged object discriminator for `parent` field

**Decision:** Use a tagged object pattern (`{"project": {...}}` vs `{"task": {...}}`) instead of a `type` field to discriminate the parent union.

**Alternatives considered:**
- **(a) `type` field with no default**: Boilerplate at every construction site.
- **(b) `type` field with Literal default**: Broken by Pydantic's `exclude_defaults=True` — the discriminator gets stripped during serialization. This has bitten the project before.
- **(c) Different field names** (`project_id` vs `task_id`): Breaks the clean `{id, name}` pattern.
- **(d) Tagged object** (chosen): Key IS the discriminator. No `type` field, no defaults, no `exclude_defaults` risk.

**What decided it:** Prior experience with `exclude_defaults` stripping Literal discriminator fields. The tagged object pattern is already proven in the codebase (MoveAction uses the same "exactly one key" validation). The `project` field stays flat (always ProjectRef, no wrapper needed) — only `parent` needs the tagged wrapper.

### DL-13: Bundle name-based resolution into this milestone

**Decision:** Include name-based resolution for projects, folders, and parent tasks in v1.3.1, not as a separate milestone.

**The alternative** was to implement name resolution as its own milestone or as an urgent phase in the current milestone (v1.3, which is about to finish and was never designed for this).

**What decided it:** The resolver is designed as a unit — the three-step precedence (`$` prefix → ID → name) is the core of this milestone's design. Building only step 1 without 2 and 3 creates a partial resolver that gets reworked later. Testing `$inbox` alongside name resolution validates the collision-proof design. And the scope increase is bounded: tags already resolve by name (v1.2), `project` filter already does substring matching (v1.3). The new work is mainly `parent` on add_tasks and `moveTo` on edit_tasks.

---

## Tools After This Milestone

Unchanged from v1.3: `get_all`, `get_task`, `get_project`, `get_tag`, `add_tasks`, `edit_tasks`, `list_tasks`, `list_projects`, `list_tags`, `list_folders`, `list_perspectives`, `count_tasks`, `count_projects`.

No new tools. This milestone changes contracts and models, not the tool surface.
