# OmniFocus API Ground Truth — Findings

> Empirical findings from running audit scripts against a live OmniFocus database.
> Each section is filled in during the guided audit session (`/omnifocus-api-ground-truth-audit`).
> Every finding below is backed by script output — not documentation, not assumptions.

**Audit date:** 2026-03-04
**OmniFocus version:** 4.8.8 (v185.9.1)
**Database size:** 368 projects, 2822 tasks, 65 tags, 79 folders

---

## 1. OmniFocus Enum System

> Source: Script 03 (Status Enum Discovery)

### Opaque Enum Behavior
Confirmed: all status values show as `[object: object]`. No string conversion works — `.name`, `String()`, `.toString()` all return useless output. Only `===` comparison against known constants works.

### Project.Status Constants
All 4 constants confirmed. Sum = 368/368.

| Constant | Exists? | Count in DB |
|----------|---------|-------------|
| Active   | Yes     | 340         |
| OnHold   | Yes     | 21          |
| Done     | Yes     | 6           |
| Dropped  | Yes     | 1           |

### Task.Status Constants
All 7 constants confirmed to exist. Sample of first 500 tasks (full distribution in Script 09).

| Constant  | Exists? | Count in Sample (500) |
|-----------|---------|----------------------|
| Available | Yes     | 205                  |
| Blocked   | Yes     | 176                  |
| Completed | Yes     | 25                   |
| Dropped   | Yes     | 37                   |
| DueSoon   | Yes     | 0 (exists but not seen in sample) |
| Next      | Yes     | 37                   |
| Overdue   | Yes     | 20                   |

### Tag.Status Constants
All 3 constants confirmed. Sum = 65/65.

| Constant | Exists? | Count in DB |
|----------|---------|-------------|
| Active   | Yes     | 60          |
| OnHold   | Yes     | 5           |
| Dropped  | Yes     | 0 (constant exists, no dropped tags in DB) |

### Folder.Status Constants
Both constants confirmed. Sum = 79/79.

| Constant | Exists? | Count in DB |
|----------|---------|-------------|
| Active   | Yes     | 77          |
| Dropped  | Yes     | 2           |

### Cross-Type Compatibility
**All cross-type comparisons are FALSE:**
- `Project.Status.Active === Tag.Status.Active` → false
- `Project.Status.Dropped === Tag.Status.Dropped` → false
- `Project.Status.Active === Folder.Status.Active` → false
- `Tag.Status.Active === Folder.Status.Active` → false

**A single switch function CANNOT handle all entity types.** Each type has its own isolated enum namespace. The bridge must either use separate resolvers per entity type, or build a combined resolver that tests against all type-specific constants.

### Bridge Action Items
- [ ] Fix status resolution — current `.name` approach is broken (always null). Must use `===` against known constants
- [ ] Implement per-entity-type status resolution (no cross-type sharing)
- [ ] Add `OnHold` to EntityStatus enum — currently missing from the Python model
- [ ] Add `DueSoon` to task status handling — constant exists even if rare
- [ ] Consider a combined resolver that tests value against all 4 entity type constants and returns a string

---

## 2. Project Type

> Source: Scripts 01, 02, 04, 06, 07

### Root Task Relationship
Confirmed: `p.id.primaryKey === p.task.id.primaryKey` for all 368/368 projects. The project and its root task share the same identity. Zero mismatches.

### Task-Only Fields (undefined on p.*, defined on p.task.*)
All 4 task-only fields are undefined/null on `p.*` and always defined on `p.task.*` across 368/368 projects. This is 100% consistent — no exceptions.

| Field           | On p.*          | On p.task.*     | Always present? |
|-----------------|-----------------|-----------------|-----------------|
| added           | undef/null 368  | defined 368     | Yes             |
| modified        | undef/null 368  | defined 368     | Yes             |
| active          | undef/null 368  | defined 368     | Yes             |
| effectiveActive | undef/null 368  | defined 368     | Yes             |

active distribution (on p.task): true=367, false=1
effectiveActive distribution (on p.task): true=345, false=23
Divergence (active but not effectiveActive): 22 — caused by folder inheritance (project is active but parent folder is on hold/dropped).

### Effective Fields Bug
**No bug exists.** All 6 effective fields work identically on `p.*` and `p.task.*`. Zero `undefined` values, zero divergences across 368 projects. Preliminary research was wrong.

| Field                   | On p.*               | On p.task.*          | Broken? | Distribution |
|-------------------------|----------------------|----------------------|---------|--------------|
| effectiveDueDate        | Works (null or Date) | Works (null or Date) | No      | null=351, match=17 |
| effectiveDeferDate      | Works (null or Date) | Works (null or Date) | No      | null=358, match=10 |
| effectiveCompletedDate  | Works (null or Date) | Works (null or Date) | No      | null=362, match=6 |
| effectivePlannedDate    | Works (null or Date) | Works (null or Date) | No      | null=368 (all null) |
| effectiveDropDate       | Works (null or Date) | Works (null or Date) | No      | null=345, match=23 |
| effectiveFlagged        | Works (boolean)      | Works (boolean)      | No      | match=368 (always boolean, never null) |

### Shared Fields (proxied identically p.* ↔ p.task.*)
Zero divergences across all 368 projects on all shared fields (name, note, dueDate, deferDate, completionDate, dropDate, flagged, estimatedMinutes, completedByChildren, sequential, etc.). Tags also match: p.tags vs p.task.tags divergence = 0.

### Status Cross-Reference
From Script 04 — 368 projects.

| Project.Status | Count | task.active | task.effectiveActive | task.Status | Notes |
|----------------|-------|-------------|----------------------|-------------|-------|
| Active | 340 | true (340/340) | true=321, false=19 | Blocked=263, Next=32, Available=21, Dropped=19, Overdue=5 | 19 false/Dropped caused by folder inheritance |
| OnHold | 21 | true (21/21) | true=18, false=3 | Blocked=18, Dropped=3 | active stays true! Indistinguishable from Active at task level |
| Done | 6 | true (6/6) | true=6 | Completed=6 | active stays true! Only Task.Status reveals completion |
| Dropped | 1 | false (1/1) | false=1 | Dropped=1 | Only status that sets active=false |

**Key finding:** `task.active` is only `false` for Dropped projects. OnHold and Done projects still have `active=true`. The bridge MUST use `Project.Status` directly — `task.active` alone cannot distinguish Active, OnHold, or Done projects.

**Folder inheritance:** 22 projects have `effectiveActive=false` while `active=true` (19 Active + 3 OnHold). These are inside dropped/on-hold parent folders. Their root task shows `Task.Status=Dropped` despite the project itself not being dropped.

### Nullable Fields
From Script 01: `nextTask` (102/368 null), `repetitionRule` (359/368 null), `effectiveCompletedDate` (362/368 null). All other project-specific fields are always present.

### Project-Specific Fields
All distributions from 368 projects.

| Field                    | Present | Null | Notes |
|--------------------------|---------|------|-------|
| containsSingletonActions | 368     | 0    | true=86, false=282 (boolean, always present) |
| lastReviewDate           | 368     | 0    | Always present |
| nextReviewDate           | 368     | 0    | Always present |
| reviewInterval           | 368     | 0    | Format: "N:unit" (e.g., "2:weeks", "1:months"). 26 distinct values. |
| nextTask                 | 266     | 102  | Nullable — null when project has no available next action |
| folder                   | 368     | 0    | All projects are inside folders (none top-level in this DB) |
| repetitionRule           | 9       | 359  | Rare. Format: ruleString=RRULE (e.g., FREQ=DAILY;INTERVAL=26), scheduleType=opaque enum |

### Bridge Action Items
- [ ] Read added/modified/active/effectiveActive from `p.task.*` not `p.*` — undefined on project object
- [ ] Tags can be read from either `p.tags` or `p.task.tags` — they always match (368/368)
- [ ] `nextTask` is nullable — bridge must handle null
- [ ] `repetitionRule` has sub-fields: `ruleString` (RRULE format) and `scheduleType` (opaque enum) — needs proper serialization
- [ ] `reviewInterval` is a string in "N:unit" format — bridge should expose as-is or parse into structured type
- [ ] `inInbox` is always false on project root tasks — can be omitted or hardcoded for projects

---

## 3. Task Type

> Source: Script 09

### Field Map
Total tasks: 2822

| Field | Type | Present | Missing/Null | Distribution/Notes |
|-------|------|---------|-------------|-------------------|
| added | Date | 2822 | 0 | Always present |
| modified | Date | 2822 | 0 | Always present |
| active | boolean | 2822 | 0 | true=2686, false=136 |
| effectiveActive | boolean | 2822 | 0 | true=2158, false=664 |
| inInbox | boolean | 2822 | 0 | true=49, false=2773 |
| completed | boolean | 2822 | 0 | true=203, false=2619 |
| flagged | boolean | 2822 | 0 | true=0, false=2822 (none flagged in DB) |
| effectiveFlagged | boolean | 2822 | 0 | true=0, false=2822 |
| sequential | boolean | 2822 | 0 | true=64, false=2758 |
| completedByChildren | boolean | 2822 | 0 | true=1505, false=1317 |
| hasChildren | boolean | 2822 | 0 | true=794, false=2028 |
| shouldUseFloatingTimeZone | boolean | 2822 | 0 | true=2822 (always true) |
| name | string | 2818 | 4 empty | 4 tasks with empty name |
| note | string | 2822 | 0 | empty_string=1805, non_empty=1017 (never null) |
| dueDate | Date/null | 284 | 2538 null | 10.1% have a due date |
| deferDate | Date/null | 392 | 2430 null | 13.9% have a defer date |
| completionDate | Date/null | 203 | 2619 null | Matches completed=true count |
| plannedDate | Date/null | 24 | 2798 null | Rare (0.9%) |
| dropDate | Date/null | 136 | 2686 null | Matches active=false count |
| effectiveDueDate | Date/null | 724 | 2098 null | 25.7% — more than dueDate due to inheritance |
| effectiveDeferDate | Date/null | 468 | 2354 null | 16.6% — more than deferDate due to inheritance |
| effectiveCompletedDate | Date/null | 265 | 2557 null | More than completionDate (62 inherited) |
| effectivePlannedDate | Date/null | 30 | 2792 null | Slightly more than plannedDate |
| effectiveDropDate | Date/null | 664 | 2158 null | Matches effectiveActive=false count |
| estimatedMinutes | number/null | 1067 | 1755 null | zero=0, all present values are positive |
| repetitionRule | object/null | 352 | 2470 null | 12.5% have repetition rules |
| tags | array | 2822 | 0 | zero=640, one=976, multi=1206, max=5 |

### Always-Present Fields
All boolean fields and timestamps are always present (never null/undefined): `added`, `modified`, `active`, `effectiveActive`, `inInbox`, `completed`, `flagged`, `effectiveFlagged`, `sequential`, `completedByChildren`, `hasChildren`, `shouldUseFloatingTimeZone`, `name`, `note`, `tags`.

### Nullable Fields

| Field | % null | Notes |
|-------|--------|-------|
| dueDate | 89.9% | Most tasks have no direct due date |
| deferDate | 86.1% | Most tasks have no defer date |
| completionDate | 92.8% | Only set for completed tasks |
| plannedDate | 99.1% | Very rare |
| dropDate | 95.2% | Only set for self-dropped tasks |
| effectiveDueDate | 74.3% | 440 tasks inherit due dates from parents |
| effectiveDeferDate | 83.4% | 76 tasks inherit defer dates |
| effectiveCompletedDate | 90.6% | 62 more than completionDate (inherited) |
| effectivePlannedDate | 98.9% | 6 more than plannedDate |
| effectiveDropDate | 76.5% | Matches effectiveActive=false — container inheritance |
| estimatedMinutes | 62.2% | Majority of tasks have no estimate |
| repetitionRule | 87.5% | Majority of tasks don't repeat |

### Status Distribution
Full database (2822 tasks). Definitive — supersedes Script 03's 500-task sample.

| Status | Count | % |
|--------|-------|---|
| Blocked | 838 | 29.7% |
| Dropped | 664 | 23.5% |
| Available | 598 | 21.2% |
| Completed | 265 | 9.4% |
| Overdue | 253 | 9.0% |
| Next | 204 | 7.2% |
| DueSoon | 0 | 0.0% |
| **Sum** | **2822** | **100%** ✅ |

Note: DueSoon has 0 tasks despite the constant existing. This is database-specific — other databases may have DueSoon tasks depending on OmniFocus's due-soon threshold setting.

### Status × Active × EffectiveActive Cross-Reference
**The most important table for Milestone 2 service layer design.**

| taskStatus | active | effectiveActive | Count | Interpretation |
|------------|--------|-----------------|-------|----------------|
| Blocked | true | true | 838 | Normal blocked tasks (sequential, deferred, etc.) |
| Available | true | true | 598 | Workable tasks |
| Dropped | true | false | 528 | Active tasks in inactive containers (inherited drop) |
| Completed | true | true | 265 | Completed tasks — active stays true |
| Overdue | true | true | 253 | Genuinely overdue in active containers |
| Next | true | true | 204 | First available in project |
| Dropped | false | false | 136 | Self-dropped tasks (user action) |

**Key findings:**
- **ALL Overdue tasks (253/253) have effectiveActive=true.** OmniFocus forces tasks in inactive containers to Dropped status, never Overdue. The service layer does NOT need to check container state for Overdue tasks.
- **active=false only occurs for Dropped tasks** (136/136). No other status has active=false.
- **effectiveActive=false only occurs for Dropped tasks** (528+136=664). Container inheritance is fully captured by the Dropped status override.
- **The "Overdue masks Blocked" problem is NOT solved by active/effectiveActive.** Task-level blocking conditions (future defer date, sequential predecessor, incomplete children) do not affect these fields. The Milestone 2 recovery logic is still required for those three checks.
- **Two flavors of Dropped:** `active=false` (136) = task itself dropped; `active=true, effectiveActive=false` (528) = task OK but container inactive. Useful for distinguishing user action from inheritance.

### Inbox Tasks
49 tasks (1.7%) have `inInbox=true`. These are tasks with no project assignment. `containingProject` is null for inbox tasks (confirmed: 119 tasks have null containingProject, which includes inbox tasks plus likely root tasks of projects).

### Relationship Fields

| Accessor | Present | Null | Notes |
|----------|---------|------|-------|
| containingProject | 2703 | 119 | Null for inbox tasks and project root tasks |
| parent | 2405 | 417 | Null for top-level tasks (first level in project or inbox) |
| assignedContainer | 0 | 2822 | **Always null** across all 2822 tasks |

`assignedContainer` is universally null — do not use it. `containingProject` is the correct accessor for determining project membership.

### RepetitionRule Deep Inspection
352/2822 tasks (12.5%) have repetition rules. Inspected first 5:

| Sub-field | Type | Example Values | Always Present? |
|-----------|------|---------------|-----------------|
| ruleString | string | `FREQ=WEEKLY;BYDAY=MO`, `FREQ=MONTHLY;BYDAY=SU,SA;BYSETPOS=1` | Yes (on rules that exist) |
| scheduleType | opaque enum | `Task.RepetitionScheduleType: Regularly`, `Task.RepetitionScheduleType: FromCompletion` | Yes |
| fixedInterval | undefined | — | No (does not exist) |
| unit | undefined | — | No (does not exist) |

RepetitionRule has exactly 2 useful sub-fields: `ruleString` (RRULE format) and `scheduleType` (opaque enum with at least Regularly and FromCompletion values). The `fixedInterval` and `unit` fields do not exist — they were likely confused with project `reviewInterval`.

### Collections (linkedFileURLs, notifications, attachments)
Sampled first 500 tasks:

| Collection | Non-empty | Empty | Error |
|------------|-----------|-------|-------|
| linkedFileURLs | 0 | 500 | 0 |
| notifications | 0 | 500 | 0 |
| attachments | 0 | 500 | 0 |

All three collections exist as empty arrays on every task. None populated in this database's sample. They are valid fields but rarely used.

### Accessor Equivalence
Tested first 10 tasks:
- `project` vs `containingProject`: **match=10, differ=0** — both return the same value (both null for the sampled tasks)
- `parentTask` does **not exist** in Omni Automation — only `parent` works. The script confirmed this: "parentTask does not exist."

### Bridge Action Items
- [ ] `added`/`modified` are always present on tasks (unlike projects where they require `p.task.*`) — read directly from task object
- [ ] `assignedContainer` is always null on tasks — do not include in bridge or model
- [ ] Use `containingProject` (not `project`) for task→project relationship — both work but `containingProject` is the documented accessor
- [ ] Use `parent` (not `parentTask`) for task→parent — `parentTask` does not exist in Omni Automation
- [ ] `note` is never null, always a string (empty or non-empty) — bridge can treat as non-nullable string
- [ ] `estimatedMinutes` is null or positive, never zero — bridge can use null for "no estimate"
- [ ] RepetitionRule: serialize `ruleString` and `scheduleType` only — `fixedInterval`/`unit` don't exist
- [ ] `scheduleType` is an opaque enum — needs `===` comparison against `Task.RepetitionScheduleType.Regularly` and `.FromCompletion` (at minimum)
- [ ] Collections (linkedFileURLs, notifications, attachments) exist but are rarely populated — consider deferring to a later milestone
- [ ] 4 tasks have empty names — bridge should handle gracefully (empty string, not null)
- [ ] `effectiveActive=false` reliably indicates "in inactive container" — can be used to distinguish inherited-drop from self-drop without hierarchy walking
- [ ] `shouldUseFloatingTimeZone` is always true — can be omitted from the model or hardcoded

---

## 4. Tag Type

> Source: Script 10

### Field Map
Total tags: 65

| Field | Type | Present | Missing/Null | Distribution/Notes |
|-------|------|---------|-------------|-------------------|
| id | ObjectIdentifier | 65 | 0 | Always present |
| name | string | 65 | 0 | Always present, all non-empty |
| added | Date | 65 | 0 | Always present |
| modified | Date | 65 | 0 | Always present |
| active | boolean | 65 | 0 | true=65 (all active in this DB) |
| effectiveActive | boolean | 65 | 0 | true=65, zero divergence from active |
| allowsNextAction | boolean | 65 | 0 | true=60, false=5 |
| note | null | 0 | 65 null | **Always null** — unlike tasks where note is always a string |
| parent | Tag/null | 38 | 27 null | 38 nested tags, 27 top-level |
| tags (children) | array | 18 have children | 47 leaf | Via `tag.tags` accessor |

**Notable:** Tags have no date fields (dueDate, deferDate, etc.), no flagged, no completed, no estimatedMinutes, no repetitionRule. Tags are much simpler than tasks or projects.

### Status Enum
3 constants exist for Tag.Status. Sum = 65/65.

| Constant | Exists? | Count in DB | Notes |
|----------|---------|-------------|-------|
| Active | Yes | 60 | Default state |
| OnHold | Yes | 5 | Tag is paused — `allowsNextAction=false` for all 5 |
| Dropped | Yes | 0 | Constant exists, no dropped tags in this DB |
| Done | No (undefined) | — | Does not exist for tags |
| Blocked | No (undefined) | — | Does not exist for tags |
| Available | No (undefined) | — | Does not exist for tags |

**Key observation:** OnHold tags have `allowsNextAction=false` (5/5). Active tags have `allowsNextAction=true` (60/60). These two fields are perfectly correlated — `allowsNextAction` is effectively the boolean equivalent of "is this tag Active vs OnHold."

### Relationship to Project Status
**All cross-type comparisons are FALSE** — confirmed again (also verified in Script 03):
- `Tag.Status.Active === Project.Status.Active` → false
- `Tag.Status.OnHold === Project.Status.OnHold` → false
- `Tag.Status.Dropped === Project.Status.Dropped` → false

Tag status enums are in a completely separate namespace. The bridge must use Tag-specific status resolution.

### Name Uniqueness
**All 65 tag names are unique.** Zero duplicates. The bridge's approach of serializing tags by name (not ID) is safe for this database. However, OmniFocus does allow creating duplicate tag names in different hierarchy levels — the bridge should be aware this is possible even if not present here.

### Bridge Action Items
- [ ] Tag `note` is always null (unlike task/project where it's always a string) — bridge should handle null notes for tags
- [ ] `allowsNextAction` perfectly correlates with status (false=OnHold, true=Active) — could derive one from the other, but safer to serialize both
- [ ] Tag.Status needs its own resolver — 3 constants (Active, OnHold, Dropped), no cross-type sharing
- [ ] Tags have a hierarchical structure (parent/children via `tag.tags`) — bridge should expose parent relationship
- [ ] Tag name uniqueness holds in this DB but is not guaranteed by OmniFocus — consider ID-based lookup as fallback
- [ ] Tags lack date fields, flagged, completed, estimatedMinutes — tag model is much simpler than task model

---

## 5. Folder Type

> Source: Script 11

### Field Map
Total folders: 79

| Field | Type | Present | Missing/Null | Distribution/Notes |
|-------|------|---------|-------------|-------------------|
| id | ObjectIdentifier | 79 | 0 | Always present |
| name | string | 79 | 0 | Always present, all non-empty |
| added | Date | 79 | 0 | Always present |
| modified | Date | 79 | 0 | Always present |
| active | boolean | 79 | 0 | true=77, false=2 |
| effectiveActive | boolean | 79 | 0 | true=67, false=12 |
| note | null | 0 | 79 null | **Always null** — same as tags |
| parent | Folder/null | 72 | 7 null | 72 nested, 7 top-level |

**Hierarchy stats:** 70/79 folders contain projects (368 total), 22/79 contain subfolders (72 total). Folders are the simplest entity type — even simpler than tags.

**active/effectiveActive divergence:** 10 folders have `active=true` but `effectiveActive=false`. These are active folders nested inside the 2 dropped folders. Same inheritance pattern as projects: container state propagates downward through `effectiveActive`.

### Status Enum
Only 2 constants exist for Folder.Status. Sum = 79/79.

| Constant | Exists? | Count in DB | Notes |
|----------|---------|-------------|-------|
| Active | Yes | 77 | Default state |
| Dropped | Yes | 2 | Folder and all contents deactivated |
| OnHold | No (undefined) | — | **Does not exist** for folders (unlike projects and tags) |
| Done | No (undefined) | — | Does not exist |

**Key difference from other types:** Folders have NO OnHold status. Only Active or Dropped. This is the simplest status enum of all 4 entity types. Cross-type comparisons all false (confirmed again).

### Bridge Action Items
- [ ] Folder.Status resolver needs only 2 constants (Active, Dropped) — simplest of all types
- [ ] Folder `note` is always null — same as tags, handle accordingly
- [ ] `effectiveActive` inheritance works the same as for projects/tasks — 10 active folders inside 2 dropped folders show effectiveActive=false
- [ ] Folders have no date fields, no flagged, no completed — model is minimal (id, name, status, active, effectiveActive, parent)
- [ ] 7 top-level folders — these are the root organizational containers

---

## 6. Perspective Type

> Source: Script 12

### Field Map
Total perspectives: 57 (via `Perspective.all`)

| Field | Type | Present | Missing/Null | Notes |
|-------|------|---------|-------------|-------|
| id | ObjectIdentifier | 57 | 0 | Always present |
| name | string | 57 | 0 | Always present |
| identifier | string/null | 50 | 7 null | Custom perspectives have identifiers, built-in do not |
| added | Date | 50 | 7 | Only on custom perspectives (built-in return undefined) |
| modified | Date | 50 | 7 | Only on custom perspectives |
| active | undefined | 0 | 57 | Always undefined — not applicable to perspectives |
| effectiveActive | undefined | 0 | 57 | Always undefined |
| status | undefined | 0 | 57 | Always undefined — perspectives have no status |
| note | undefined | 0 | 57 | Always undefined |
| parent | undefined | 0 | 57 | Always undefined |
| completed | undefined | 0 | 57 | Always undefined |
| flagged | undefined | 0 | 57 | Always undefined |

**Perspective-specific properties — ALL undefined:**
`fileURL`, `color`, `iconName`, `window`, `originalIconName`, `sidebar`, `contents`, `filter`, `focus`, `grouping`, `sorting`, `layout`, `containerType`, `customFilterFormula` — none accessible via Omni Automation. The API exposes perspective identity (name, id, identifier) but not configuration.

### Built-in vs Custom
**Distinguishing rule:** Built-in perspectives have `identifier=null`, custom perspectives have a non-null identifier string.

**Built-in perspectives (7 — no identifier):**
Review, Projects, Tags, Forecast, Inbox, Nearby, Flagged

**Custom perspectives (50 — have identifier):**
50 user-created perspectives with unique identifier strings (e.g., `hNJJsekW_nE`, `d0qrXt1fR-A`). Two notable identifiers look semantic rather than random: `ProcessRecentChanges` ("Changed") and `ProcessCompleted` ("Completed") — possibly OmniFocus-generated perspectives.

### Access Paths
Three access paths tested:

| Path | Count | Notes |
|------|-------|-------|
| `Perspective.all` | 57 | Main collection |
| `Perspective.BuiltIn.all` | 8 | One more than the 7 with null identifier |
| `Perspective.Custom.all` | 50 | Matches identifier-present count |
| BuiltIn + Custom | 58 | **Mismatch: 58 ≠ 57** |

**Mismatch analysis:** `BuiltIn.all` returns 8 perspectives but only 7 appear in `Perspective.all` with null identifiers. One built-in perspective is in `BuiltIn.all` but not in `Perspective.all`, or it has an identifier that makes it look custom. The bridge should use `Perspective.all` as the canonical source (57 perspectives).

### Bridge Action Items
- [ ] Use `Perspective.all` as the canonical access path — it returns the most consistent count
- [ ] Distinguish built-in vs custom via `identifier` (null = built-in, non-null = custom)
- [ ] Perspective model is minimal: `id`, `name`, `identifier`, `added`, `modified` (last two only for custom)
- [ ] No status, active, or configuration fields exist on perspectives — do not attempt to read them
- [ ] `added`/`modified` are undefined for built-in perspectives — bridge must handle null for these
- [ ] Perspective filter/sorting/grouping configuration is NOT accessible via Omni Automation — cannot expose "what does this perspective show"

---

## 7. Write Behavior

> Source: Scripts 05, 06, 07, 08

### Property Proxying Rules
Writes are **fully bidirectional** between `p.*` and `p.task.*`. Setting a property on either side immediately updates the other. The bridge can write to whichever is more convenient — both are equivalent.

| Operation                  | Result      |
|----------------------------|-------------|
| Set p.dueDate → t.dueDate  | Proxied ✅ — t.dueDate updates immediately |
| Clear p.dueDate → t.dueDate| Proxied ✅ — t.dueDate becomes null |
| Set t.flagged → p.flagged  | Proxied ✅ — p.flagged updates immediately |
| Set p.completed = true     | p.status→Done, t.taskStatus→Completed, t.active stays true |
| Set p.completed = false    | Reverts cleanly to Active/Blocked, t.active stays true |
| Set p.status = OnHold      | Only p.status changes. t.taskStatus stays Blocked, t.active stays true |
| Set p.status = Active      | Reverts cleanly. No task-level side effects |

**Key finding from status transitions:** `task.active` and `task.effectiveActive` do NOT change during markComplete(), markIncomplete(), or OnHold transitions. They remain `true` throughout. Only Dropped sets `active=false` (confirmed in Script 04). The bridge MUST use `Project.Status` directly — `task.active` cannot distinguish Active, OnHold, or Done.

### Creation Behavior
From Script 05/06: newly created entities are immediately available in the API with all properties set. Observations:
- `new Project(name)` creates a project with `status=Active`, `taskStatus=Blocked` (root task has children)
- `new Task(name, project)` creates a task inside the project. `taskStatus` depends on position: first task = Next, subsequent = Blocked (in parallel project)
- `project.addTag(tag)` applies to both `p.tags` and `p.task.tags` (proxied)
- `added` and `modified` are auto-set to creation time on the root task (undefined on `p.*`)
- `completedByChildren` defaults to `true` for new projects
- `sequential` defaults to `false` (parallel)
- `reviewInterval` defaults to `steps=1, unit=weeks`
- `inInbox` is `false` for project root tasks
- Child task `project` accessor returns `null`; use `containingProject` to get the parent project
- Child task `assignedContainer` returns `null` for tasks inside projects

### Deletion Behavior
From Script 08: deletion order matters due to cascading.
- Deleting a project's root task (found via `flattenedTasks`) **cascades** — removes the project object and all child tasks. This was discovered empirically when `deleteObject(rootTask)` invalidated the `Project` object.
- The safe deletion order is: delete the **project** first (via `deleteObject(project)`), then clean up any orphan tasks, then delete the tag last.
- After deletion, `flattenedTasks`/`flattenedProjects` immediately reflect the removal — no refresh needed.
- Tags survive project/task deletion (they're independent entities).

### Bridge Action Items
- [ ] Writes can go through either `p.*` or `p.task.*` — both directions proxy. Bridge can use whichever is more convenient
- [ ] Use `markComplete()`/`markIncomplete()` for completion toggling, not direct property assignment
- [ ] Use `p.status = Project.Status.OnHold` (etc.) for status changes — these are the only way to set status
- [ ] When deleting a project, delete via the project object, not the root task — avoids cascade surprises
- [ ] `containingProject` is the correct task→project accessor (not `project`, which returns null for child tasks)
- [ ] `assignedContainer` returns null for tasks inside projects — do not rely on it for project membership

---

## 8. Bridge Implications

> Summary of all bridge changes needed, derived from findings above.

### Critical Fixes (correctness bugs)
- [ ] **Status resolution is broken** — current `.name` approach returns null for all entity types. Must use `===` comparison against known constants (Section 1)
- [ ] **Per-entity-type status resolution required** — no cross-type enum sharing. `Project.Status.Active !== Tag.Status.Active !== Folder.Status.Active`. Each entity type needs its own resolver (Section 1)
- [ ] **Project added/modified/active/effectiveActive must read from `p.task.*`** — these are undefined on `p.*` for all 368 projects (Section 2)
- [ ] **Use `containingProject` not `project` for task→project relationship** — `project` returns null for child tasks; `containingProject` is the correct accessor (Section 7)
- [ ] **Use `parent` not `parentTask` for task→parent relationship** — `parentTask` does not exist in Omni Automation (Section 3)
- [ ] **`assignedContainer` is always null** on all 2822 tasks — do not use for project membership (Section 3)

### Improvements (data quality)
- [ ] **Bidirectional write proxying confirmed** — bridge can read/write from either `p.*` or `p.task.*`, both sync immediately. Simplifies implementation (Section 7)
- [ ] **`effectiveActive` reliably encodes container state** — false means task is in inactive container. Can distinguish inherited-drop (`active=true, effectiveActive=false`) from self-drop (`active=false`) without hierarchy walking (Section 3)
- [ ] **Use `markComplete()`/`markIncomplete()` for completion** — not direct property assignment. Use `p.status = Project.Status.X` for status changes (Section 7)
- [ ] **Delete projects via project object, not root task** — root task deletion cascades and invalidates the project object (Section 7)
- [ ] **Tags survive entity deletion** — independent lifecycle, must be deleted separately (Section 7)
- [ ] **`Perspective.all` is the canonical perspective access path** — BuiltIn+Custom counts don't match Perspective.all (Section 6)
- [ ] **Tag/folder `note` is always null** — unlike task/project where note is always a string (empty or non-empty). Bridge must handle both patterns (Sections 4, 5)
- [ ] **Collections (linkedFileURLs, notifications, attachments)** exist as empty arrays on tasks — valid fields but rarely populated. Defer to later milestone (Section 3)

### Model Changes
- [ ] **Project model:** Add `reviewInterval` (string "N:unit"), `nextTask` (nullable), `repetitionRule` (ruleString + scheduleType). `containsSingletonActions`, `lastReviewDate`, `nextReviewDate` always present (Section 2)
- [ ] **Task model:** `note` is non-nullable string (never null, can be empty). `estimatedMinutes` is null or positive (never zero). `name` can be empty (4 tasks). `shouldUseFloatingTimeZone` always true — omit or hardcode (Section 3)
- [ ] **Task RepetitionRule:** Only 2 sub-fields exist: `ruleString` (RRULE string) and `scheduleType` (opaque enum: Regularly, FromCompletion). `fixedInterval`/`unit` do not exist (Section 3)
- [ ] **Tag model:** Minimal — id, name, status, active, effectiveActive, allowsNextAction, parent. No dates, flags, or completion (Section 4)
- [ ] **Folder model:** Minimal — id, name, status, active, effectiveActive, parent. No dates, flags, completion, or OnHold status (Section 5)
- [ ] **Perspective model:** id, name, identifier (null for built-in), added/modified (only for custom). No status, active, configuration, or filter fields accessible (Section 6)
- [ ] **`inInbox` on tasks:** 49/2822 tasks (1.7%) are inbox tasks. Always false on project root tasks (Section 3)
- [ ] **`completedByChildren`:** true for 1505/2822 tasks. Defaults to true on new projects (Section 3)

### Enum Changes
- [ ] **Add `OnHold` to EntityStatus** — currently missing. Needed for projects (21 OnHold) and tags (5 OnHold) (Section 1)
- [ ] **Add `DueSoon` to task status handling** — constant exists, 0 instances in this DB but valid in others (Section 1)
- [ ] **Status constants per entity type:**
  - Project.Status: Active, OnHold, Done, Dropped (4 values)
  - Task.Status: Available, Blocked, Completed, Dropped, DueSoon, Next, Overdue (7 values)
  - Tag.Status: Active, OnHold, Dropped (3 values)
  - Folder.Status: Active, Dropped (2 values — NO OnHold)
- [ ] **RepetitionRule scheduleType** is an opaque enum — needs `===` comparison. Known values: `Task.RepetitionScheduleType.Regularly`, `Task.RepetitionScheduleType.FromCompletion` (Section 3)
- [ ] **`allowsNextAction` on tags** perfectly correlates with OnHold status (false=OnHold, true=Active) — can derive one from other but safer to serialize both (Section 4)

---

## 9. Supplementary Findings

> Source: Scripts 13-24 (Part 4 — Supplementary Audits)

### 9.1 RepetitionRule Full Enumeration (Script 13)

**Total tasks with repetitionRule:** 352/2822 (12.5%)

#### ScheduleType Constants
3 constants exist (not 2 as previously assumed):

| Constant | Exists? | Count in DB | Notes |
|----------|---------|-------------|-------|
| Regularly | Yes | 163 | Fixed-schedule repeats |
| FromCompletion | Yes | 189 | Repeat N days after completion |
| None | Yes | 0 | Constant exists but no tasks use it — likely internal default/placeholder |

Sum: 352/352. Zero UNKNOWN values. All other probed names (DeferAnother, DueAnother, Fixed, DeferUntil, DueDate, Daily, Weekly, Monthly, Yearly, EveryNDays, EveryNWeeks, EveryNMonths, AfterCompletion, RepeatEvery, DeferAnotherFromCompletion, DueAgainAfterCompletion) are `undefined`.

#### FREQ Pattern Distribution
5 distinct FREQ values found:

| FREQ | Count | % of repeating tasks | Notes |
|------|-------|---------------------|-------|
| DAILY | 217 | 61.6% | Most common — includes INTERVAL=N for multi-day |
| WEEKLY | 84 | 23.9% | Often with BYDAY modifiers |
| YEARLY | 27 | 7.7% | Annual recurrences |
| MONTHLY | 23 | 6.5% | Includes BYDAY, BYSETPOS, BYMONTHDAY modifiers |
| HOURLY | 1 | 0.3% | Surprising — 1 task repeats hourly |

#### RRULE Complexity
49 distinct ruleStrings. Notable patterns:
- **Simple:** `FREQ=DAILY` (101 tasks), `FREQ=WEEKLY` (6), `FREQ=MONTHLY` (4), `FREQ=YEARLY` (26)
- **With INTERVAL:** `FREQ=DAILY;INTERVAL=3` (44), `FREQ=WEEKLY;INTERVAL=2` (10)
- **With BYDAY:** `FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR` (21 — weekdays), `FREQ=WEEKLY;BYDAY=MO` (10)
- **Complex monthly:** `FREQ=MONTHLY;BYDAY=SU,SA;BYSETPOS=1` (1st weekend day), `FREQ=MONTHLY;BYDAY=-1SA` (last Saturday)
- **With BYMONTHDAY:** `FREQ=MONTHLY;BYMONTHDAY=14` (fixed day of month)
- **Maximum INTERVAL:** `FREQ=DAILY;INTERVAL=88` (every 88 days — 1 task)

RRULE strings follow RFC 5545 standard. The bridge should store `ruleString` as-is and let consumers parse it with standard RRULE libraries (e.g., `python-dateutil`).

#### Bridge Action Items
- [ ] Add `None` to `RepetitionScheduleType` enum — third constant exists alongside Regularly and FromCompletion
- [ ] Store `ruleString` as raw RRULE string — 49 distinct patterns are too varied to decompose; use standard parsers
- [ ] Handle `FREQ=HOURLY` — unexpected but valid (1 task in this DB)
- [ ] `scheduleType` resolver needs 3 constants: `Task.RepetitionScheduleType.Regularly`, `.FromCompletion`, `.None`

### 9.2 Tag-Based Blocking (Script 14)
_TO BE FILLED — does OnHold tag affect taskStatus? Critical for M2 recovery logic_

### 9.3 Tag Hierarchy Inheritance (Script 15)
_TO BE FILLED — does OnHold/Dropped propagate to child tags via effectiveActive?_

### 9.4 Sequential Projects (Script 16)
_TO BE FILLED — task ordering patterns, Overdue-masks-Blocked instances_

### 9.5 Perspective Mismatch (Script 17)
_TO BE FILLED — which perspective differs between collections_

### 9.6 Collections Full Scan (Script 18)
_TO BE FILLED — linkedFileURLs/notifications/attachments across all tasks_

### 9.7 completedByChildren Semantics (Script 19)
_TO BE FILLED — does completedByChildren control auto-completion?_

### 9.8 Inbox Tasks (Script 20)
_TO BE FILLED — inbox-specific field patterns_

### 9.9 Task-Level Writes (Script 21)
_TO BE FILLED — task complete/drop/defer/flag write behavior_

### 9.10 Application Settings (Script 22)
_TO BE FILLED — accessible configuration, DueSoon threshold_

### 9.11 Estimated Minutes Distribution (Script 23)
_TO BE FILLED — min/max/mean/median/buckets_

### 9.12 Date Inheritance Patterns (Script 24)
_TO BE FILLED — inheritance tracing for due/defer dates_
