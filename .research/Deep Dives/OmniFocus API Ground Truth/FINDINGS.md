# OmniFocus API Ground Truth — Findings

> Empirical findings from running audit scripts against a live OmniFocus database.
> Each section is filled in during the guided audit session (`/omnifocus-api-ground-truth-audit`).
> Every finding below is backed by script output — not documentation, not assumptions.

**Audit date:** 2026-03-04
**OmniFocus version:** 4.8.8 (v185.9.1)
**Database size:** 368 projects, 2822 tasks, 65 tags, 79 folders

## Design Principle: Dumb Bridge, Smart Python

The bridge (OmniJS running inside OmniFocus) is **untestable** — no unit tests, no TDD, no CI. Every line of logic in the bridge is a line we can't verify automatically. So the bridge should be as thin as possible:

- **Bridge responsibility:** Extract raw data faithfully. Read from the correct accessors, resolve opaque enums to strings (because we must — `===` only works inside OmniJS), serialize to JSON. That's it.
- **Python responsibility:** All interpretation, deduplication, validation, model mapping, and business logic. This is where we have TDD, type checking, and full control.
- **Rule of thumb:** If there's ambiguity about where logic belongs, it belongs in Python. The bridge only does what *cannot* be done elsewhere (accessing OmniFocus objects, comparing opaque enums).

Examples:
- Enum → string resolution: **bridge** (opaque enums only work with `===` inside OmniJS)
- Perspective deduplication: **Python** (policy decision, not data extraction)
- `effectiveActive` interpretation (self-drop vs inherited-drop): **Python**
- Reading `p.task.added` instead of `p.added`: **bridge** (accessor choice)

---

## 1. OmniFocus Enum System

> Source: Script 03 (Status Enum Discovery)

### Opaque Enum Behavior
Confirmed: `.name` on individual enum values returns `undefined`. However, `String()` returns a parseable format: `"[object Task.Status: Active]"` (discovered in Script 25c). This could be used for diagnostics but is NOT suitable for production enum resolution (performance concern — OmniFocus freezes on large datasets). The bridge should use `===` comparison against hardcoded known constants and throw on unknown values.

Every enum namespace has an `.all` array (e.g., `Task.Status.all` returns all 7 constants). Useful for reference but do NOT iterate at runtime for the same performance reason.

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
| nextTask                 | 266     | 102  | Nullable — but when non-null, may return the root task itself (same ID as project) for OnHold/Dropped/Done projects. Don't treat non-null as "has actionable work." |
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
- **"Overdue masks Blocked" is OmniFocus's deliberate design.** Empirically confirmed: a sequentially-blocked task with a past due date reports `Task.Status.Overdue`, not Blocked. Same for DueSoon. OmniFocus prioritizes urgency over availability in the status field. The bridge should faithfully report the status OmniFocus returns. A service layer `isActionable` computation is needed to determine if a task is actually workable (checking sequential position, defer date, children).
- **Status override hierarchy (empirically confirmed):**
  - Dropped project → all children forced to Dropped (overrides everything)
  - OnHold project → all children forced to Blocked (suppresses Overdue/DueSoon)
  - For Active projects: Overdue/DueSoon > sequential blocking / defer blocking / has-children blocking
  - Future defer does NOT suppress Overdue (Overdue + future defer → Overdue)
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

RepetitionRule has 4 readable properties: `ruleString` (RRULE format), `scheduleType` (opaque enum: Regularly, FromCompletion, None), `anchorDateKey` (opaque enum: DueDate, DeferDate, PlannedDate), and `catchUpAutomatically` (boolean). Plus `firstDateAfterDate(date)` method. The `fixedInterval` and `unit` fields do not exist — they were likely confused with project `reviewInterval`. Full details in Section 9.1.

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
- [ ] RepetitionRule: serialize all 4 properties (`ruleString`, `scheduleType`, `anchorDateKey`, `catchUpAutomatically`) — `fixedInterval`/`unit` don't exist. Full details in Section 9.1
- [ ] `scheduleType` is an opaque enum — needs `===` comparison against `Task.RepetitionScheduleType.Regularly`, `.FromCompletion`, `.None`
- [ ] `anchorDateKey` is an opaque enum — needs `===` comparison against `Task.AnchorDateKey.DueDate`, `.DeferDate`, `.PlannedDate`
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

**Perspective-specific properties — probed names ALL undefined:**
`fileURL`, `color`, `iconName`, `window`, `originalIconName`, `sidebar`, `contents`, `filter`, `focus`, `grouping`, `sorting`, `layout`, `containerType`, `customFilterFormula` — none accessible via Omni Automation under these names.

**However, Script 25 (reflection) found filter config under different names:**
- `archivedFilterRules` (Array) — filter rules are accessible
- `archivedTopLevelFilterAggregation` (string) — filter aggregation type
- `iconColor` (object) — perspective color

The API does expose some perspective configuration — the earlier probes just used wrong property names.

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

### Duplicate Names
OmniFocus allows creating multiple perspectives with identical names (even exact same case). This is an edge case but means name alone is not a unique key.

### Bridge Action Items
- [ ] Use `Perspective.all` as the canonical access path — it returns the most consistent count
- [ ] Bridge exposes `name` and `id` (identifier) — keep bridge dumb, handle deduplication in Python
- [ ] Built-in vs custom: `identifier === null` means built-in — expose as `isBuiltIn` flag in Python model
- [ ] No status, active, or configuration fields exist on perspectives — do not attempt to read them
- [ ] `added`/`modified` are undefined for built-in perspectives — bridge must handle null for these
- [ ] Perspective filter config IS partially accessible: `archivedFilterRules`, `archivedTopLevelFilterAggregation`, `iconColor` — found via reflection (Script 25, Section 9.13). Earlier probes used wrong property names.

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

### Status Masking Behavior (Comprehensive Test — Script 05 v2)
Empirically confirmed with controlled test hierarchy (8 projects, 56 tasks):

**Project-level overrides:**
- **Dropped project:** All children forced to `Dropped`, `effectiveActive=false`. Overrides everything including Overdue.
- **OnHold project:** Active incomplete children forced to `Blocked`, but `active=true, effectiveActive=true`. Suppresses Overdue — an overdue task in an OnHold project shows Blocked. Exception: Completed tasks stay `Completed`, Dropped tasks stay `Dropped`.

**Task-level status (Active projects):**
- **Overdue masks sequential blocking:** Task 3 (third in sequential project, past due) → Overdue, not Blocked
- **DueSoon masks sequential blocking:** Task 4 (fourth in sequential project, due soon) → DueSoon, not Blocked
- **Overdue + future defer → Overdue:** Future defer does NOT suppress Overdue
- **Overdue + past defer → Overdue:** Past defer is irrelevant

**Next is project-level only:**
- First incomplete task in a sequential project → Next
- First incomplete task in a sequential action group → Available (not Next)
- First task in a parallel project → Next (OmniFocus picks one)

**completedByChildren behavior:**
- `completedByChildren=true` (default) + all children complete → parent auto-completes
- `completedByChildren=false` + all children complete → parent stays Available (not auto-completed)

**Parent tasks with children:**
- Parent with incomplete children → Blocked (regardless of parallel/sequential)
- Overdue parent with incomplete children → Overdue (urgency overrides has-children blocking)

### Date Inheritance (effectiveDueDate)
**Soonest wins, not "own value wins."** Empirically confirmed:
- Child with `dueDate=Mar 25`, parent with `dueDate=Mar 12` → child's `effectiveDueDate=Mar 12` (parent's earlier date wins)
- Child with `dueDate=Mar 8`, parent with `dueDate=Mar 12` → child's `effectiveDueDate=Mar 8` (own earlier date wins)
- Child with no `dueDate`, parent with `dueDate=Mar 12` → child's `effectiveDueDate=Mar 12` (inherited)
- Rule: `effectiveDueDate = min(own dueDate, parent's effectiveDueDate)` — earliest deadline in the ancestry chain

### Bridge Action Items
- [ ] Writes can go through either `p.*` or `p.task.*` — both directions proxy. Bridge can use whichever is more convenient
- [ ] Use `markComplete()`/`markIncomplete()` for completion toggling, not direct property assignment
- [ ] Use `p.status = Project.Status.OnHold` (etc.) for status changes — these are the only way to set status
- [ ] When deleting a project, delete via the project object, not the root task — avoids cascade surprises
- [ ] `containingProject` is the correct task→project accessor (not `project`, which returns null for child tasks)
- [ ] Bridge reports `taskStatus` as OmniFocus returns it — masking is OmniFocus's design, not a bug to fix
- [ ] Service layer (M2) needs `isActionable` logic: check sequential position, defer date, children status — cannot rely on taskStatus alone
- [ ] `effectiveDueDate` uses min() semantics — document that it's the earliest deadline in the ancestry, not just inheritance
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
- [ ] **Perspective filter config is accessible** — `archivedFilterRules` (full query language), `archivedTopLevelFilterAggregation`, `iconColor` exist (Sections 6, 9.13). **Decision: document but do NOT implement in bridge for now** — too complex for current milestone. Future potential.
- [ ] **Tag/folder `note` is always null** — unlike task/project where note is always a string (empty or non-empty). Bridge must handle both patterns (Sections 4, 5)
- [ ] **Collections (linkedFileURLs, notifications, attachments)** exist as empty arrays on tasks — valid fields but rarely populated. Defer to later milestone (Section 3)

### Model Changes
- [ ] **Model hierarchy redesign:** All 4 entity types share `id`, `name`, `added`, `modified`, `active`, `effectiveActive` → extract `BaseEntity`. Tasks and projects share dates, flags, tags, notes, estimates, repetition → extract `ActionableEntity(BaseEntity)`. Tags and folders are thin organizational types extending `BaseEntity` directly.
- [ ] **Project model:** Add `reviewInterval` (string "N:unit"), `nextTask` (nullable), `repetitionRule` (ruleString + scheduleType). `containsSingletonActions`, `lastReviewDate`, `nextReviewDate` always present (Section 2)
- [ ] **Task model:** `note` is non-nullable string (never null, can be empty). `estimatedMinutes` is null or positive (never zero). `name` can be empty (4 tasks). `shouldUseFloatingTimeZone` always true — omit or hardcode (Section 3)
- [ ] **Task RepetitionRule:** 4 readable properties: `ruleString` (RRULE string), `scheduleType` (opaque enum: Regularly, FromCompletion, None), `anchorDateKey` (opaque enum: DueDate, DeferDate, PlannedDate), `catchUpAutomatically` (boolean). Plus `firstDateAfterDate(date)` method for forecasting. `fixedInterval`/`unit` do not exist. RepetitionRule is immutable — modify by creating new and reassigning. (Sections 3, 9.1)
- [ ] **Tag model:** Minimal — id, name, status, active, effectiveActive, allowsNextAction, parent. No dates, flags, or completion (Section 4)
- [ ] **Folder model:** Minimal — id, name, status, active, effectiveActive, parent. No dates, flags, completion, or OnHold status (Section 5)
- [ ] **Perspective model:** id, name, identifier (null for built-in), added/modified (only for custom). Filter config is accessible (`archivedFilterRules`) but not included in bridge for now (Section 6, 9.13)
- [ ] **`active`/`effectiveActive` are low-signal for most agent use cases** — include in model but flag as secondary. `status` is the primary field agents should use. `effectiveActive=false` mainly indicates "inside inactive container" (e.g., template projects in dropped folders). Useful for filtering, not for decision-making.
- [ ] **`inInbox` on tasks:** 49/2822 tasks (1.7%) are inbox tasks. Always false on project root tasks (Section 3)
- [ ] **`completedByChildren`:** true for 1505/2822 tasks. Defaults to true on new projects (Section 3)

### Enum Changes
- [ ] **Replace single `EntityStatus` with separate enums per entity type** — `ProjectStatus` (4 values), `TaskStatus` (7 values), `TagStatus` (3 values), `FolderStatus` (2 values). No hierarchy — flat, independent enums. Duplication of shared values (Active, Dropped) is intentional for type safety. Each entity's `status` field uses its own enum type, so invalid assignments are caught by the type checker.
  - ProjectStatus: Active, OnHold, Done, Dropped
  - TaskStatus: Available, Blocked, Completed, Dropped, DueSoon, Next, Overdue
  - TagStatus: Active, OnHold, Dropped
  - FolderStatus: Active, Dropped
- [ ] **DueSoon empirically confirmed** — 1 instance in DB after creating a task with a near-future due date. Threshold-based (computed by OmniFocus, not user-set).
- [ ] **RepetitionRule scheduleType** is an opaque enum — needs `===` comparison. Known values: `Task.RepetitionScheduleType.Regularly`, `.FromCompletion`, `.None`. `.name` returns `undefined` (Section 9.1)
- [ ] **RepetitionRule anchorDateKey** is an opaque enum — needs `===` comparison. Known values: `Task.AnchorDateKey.DueDate`, `.DeferDate`, `.PlannedDate`. `.name` returns `undefined` (Section 9.1)
- [ ] **`allowsNextAction` on tags** perfectly correlates with OnHold status (false=OnHold, true=Active) — can derive one from other but safer to serialize both (Section 4)

---

## 9. Supplementary Findings

> Source: Scripts 13-24 (Part 4 — Supplementary Audits)

### 9.1 RepetitionRule Full Enumeration (Script 13)

**Total tasks with repetitionRule:** 352/2822 (12.5%)

**RepetitionRule has 4 readable properties + 1 method** (not 2 as previously recorded):
- `ruleString` — RRULE string (RFC 5545)
- `scheduleType` — opaque enum (`Task.RepetitionScheduleType`)
- `anchorDateKey` — opaque enum (`Task.AnchorDateKey`) — which date is updated on repetition
- `catchUpAutomatically` — boolean — whether missed occurrences are auto-skipped
- `firstDateAfterDate(date)` — method (function) — computes next occurrence after given date

**`.name` accessor is broken on RepetitionRule enums too.** Both `scheduleType.name` and `anchorDateKey.name` return `undefined`. The repetition-rule-guide's claim that `.name` works is empirically wrong. The bridge must use `===` comparison, consistent with all other OmniFocus opaque enums (Section 1).

**RepetitionRule is immutable** — all properties are read-only. To modify, create a new `Task.RepetitionRule` and reassign to `task.repetitionRule`. Constructor takes 5 params: `(ruleString, null, scheduleType, anchorDateKey, catchUpAutomatically)` — 2nd param is deprecated (always null).

#### ScheduleType Constants
3 constants exist (not 2 as previously assumed):

| Constant | Exists? | Count in DB | Notes |
|----------|---------|-------------|-------|
| Regularly | Yes | 163 | Fixed-schedule repeats |
| FromCompletion | Yes | 189 | Repeat N days after completion |
| None | Yes | 0 | Constant exists but no tasks use it — likely internal default/placeholder |

Sum: 352/352. Zero UNKNOWN values. All other probed names (DeferAnother, DueAnother, Fixed, DeferUntil, DueDate, Daily, Weekly, Monthly, Yearly, EveryNDays, EveryNWeeks, EveryNMonths, AfterCompletion, RepeatEvery, DeferAnotherFromCompletion, DueAgainAfterCompletion) are `undefined`.

#### AnchorDateKey Constants
3 constants exist:

| Constant | Exists? | Count in DB | Notes |
|----------|---------|-------------|-------|
| DueDate | Yes | 149 | Repetition updates the due date |
| DeferDate | Yes | 203 | Repetition updates the defer/start date |
| PlannedDate | Yes | 0 | Constant exists, no tasks use it (v4.7+ feature) |

Sum: 352/352. Zero UNKNOWN values. Probed names CompletionDate, DropDate, StartDate, EndDate, None are all `undefined`.

#### ScheduleType × AnchorDateKey Cross-Tabulation
All 4 combinations of scheduleType × anchorDateKey are valid and occur in the database:

| Combination | Count |
|-------------|-------|
| FromCompletion × DeferDate | 178 |
| Regularly × DueDate | 138 |
| Regularly × DeferDate | 25 |
| FromCompletion × DueDate | 11 |

The bridge must support all combinations — scheduleType and anchorDateKey are independent axes.

#### catchUpAutomatically
Always a boolean (true or false), never null/undefined. Both values present in the database (true=5, false=347). For `Regularly` tasks, controls whether missed occurrences are auto-skipped. For `FromCompletion`, catch-up is not meaningful since the next occurrence is relative to the completion moment — but the property is still present and readable.

#### firstDateAfterDate Method
Present as a function on all 352/352 rules. Can be used for forecasting (computing next occurrence without parsing RRULE in Python). Runs inside OmniJS — the bridge would need to call it and return the result.

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
- [ ] RepetitionRule has 4 properties to serialize, not 2: `ruleString`, `scheduleType`, `anchorDateKey`, `catchUpAutomatically`
- [ ] Add `AnchorDateKey` enum with 3 values: DueDate, DeferDate, PlannedDate
- [ ] `anchorDateKey` resolver needs `===` against `Task.AnchorDateKey.DueDate`, `.DeferDate`, `.PlannedDate` — `.name` does NOT work
- [ ] Add `None` to `RepetitionScheduleType` enum — third constant exists alongside Regularly and FromCompletion
- [ ] `scheduleType` resolver needs `===` against `Task.RepetitionScheduleType.Regularly`, `.FromCompletion`, `.None` — `.name` does NOT work
- [ ] `catchUpAutomatically` is always a boolean (never null) — serialize directly
- [ ] `firstDateAfterDate(date)` exists on all rules — consider exposing as a bridge capability for next-occurrence forecasting
- [ ] Store `ruleString` as raw RRULE string — 49 distinct patterns are too varied to decompose; use standard parsers
- [ ] Handle `FREQ=HOURLY` — unexpected but valid (1 task in this DB)
- [ ] Update repetition-rule-guide: `.name` accessor claims are empirically wrong — must use `===` comparison

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

### 9.13 Method Enumeration (Script 25)

JavaScript reflection (`Object.getOwnPropertyNames` + prototype chain walking) used to enumerate all properties and methods on every entity type. This script was added to close a gap: earlier scripts only tested known properties and never systematically probed for callable methods.

#### Summary by Entity Type

| Entity | Methods | Getters | Notes |
|--------|---------|---------|-------|
| Task | 22 | 49 | Richest API surface |
| Project | 15 | 46 | No `active`/`effectiveActive`/`added`/`modified` getters (confirms Section 2) |
| Tag | 7 | 25 | Has `availableTasks`, `remainingTasks` query getters |
| Folder | 5 | 21 | Simplest — named lookup methods only |
| Perspective | 2 | 9 | Filter config IS accessible (contradicts Section 6 partially) |
| RepetitionRule | 1 | 5 | Confirms Section 9.1 — `firstDateAfterDate()` + 4 properties + deprecated `method` |
| Document | 11 | 8 | `sync()`, `undo()`, `redo()`, `createOmniLinkURL()` |
| Application | 1 | 9 | `openDocument()`, version info, key state |

#### New Discoveries — Previously Unknown Getters

**Task:**
- `effectiveCompletionDate` AND `effectiveCompletedDate` both exist — two getters with near-identical names. Needs testing: are they aliases returning the same value?
- `noteText` (object) — rich text representation, distinct from `note` (plain string)
- `url` — OmniFocus URL scheme link for the task. Useful for deep linking in agent responses.
- `after`, `before`, `beginning`, `ending` — insertion location objects (for ordering)
- `beginningOfTags`, `endingOfTags` — tag insertion location objects

**Project:**
- `defaultSingletonActionHolder` (boolean) — different from `containsSingletonActions`. Needs investigation.
- `parentFolder` — the folder containing this project. Alternative to navigating the folder hierarchy.
- `url` — OmniFocus URL scheme link.
- `taskStatus` — project exposes the root task's status directly as a getter.

**Tag:**
- `availableTasks` — returns available tasks for this tag (query getter, not a method)
- `remainingTasks` — returns remaining tasks for this tag
- `projects` — projects associated with this tag
- `childrenAreMutuallyExclusive` (boolean) — e.g., energy levels where only one applies
- `url` — OmniFocus URL scheme link.

**Folder:**
- `folders`, `projects`, `sections` — child collections
- `flattenedFolders`, `flattenedProjects`, `flattenedSections`, `flattenedChildren` — deep recursive collections
- `url` — OmniFocus URL scheme link.

**Perspective:**
- `archivedFilterRules` (Array) — filter rules ARE accessible! Section 6 said filter config was inaccessible — it probed for `filter`/`sorting`/`grouping` but the actual property names are different.
- `archivedTopLevelFilterAggregation` (string) — top-level filter aggregation type.
- `iconColor` (object) — perspective color.

**Document:**
- `sync()` — trigger OmniFocus sync programmatically
- `undo()` / `redo()` — undo/redo support. Potentially useful for "cancel that" scenarios.
- `createOmniLinkURL()` — create OmniFocus links
- `canRedo`, `canUndo` — check if undo/redo is available
- `fileURL`, `writableTypes` — document metadata

#### New Discoveries — Methods

**Mutator methods (known from write scripts):**
- `markComplete()`, `markIncomplete()`, `drop()` on Task
- `markComplete()`, `markIncomplete()` on Project
- `addTag()`, `addTags()`, `removeTag()`, `removeTags()`, `clearTags()` on Task and Project
- `addAttachment()`, `removeAttachmentAtIndex()`, `addLinkedFileURL()`, `removeLinkedFileWithURL()` on Task and Project
- `addNotification()`, `removeNotification()` on Task and Project
- `appendStringToNote()` on Task and Project

**Ordering/insertion methods:**
- Task: `afterTag()`, `beforeTag()`, `moveTag()`, `moveTags()` — tag ordering within a task
- Tag: `afterTask()`, `beforeTask()`, `moveTask()`, `moveTasks()` — task ordering within a tag

**Named lookup methods:**
- Task: `childNamed()`, `taskNamed()`
- Tag: `childNamed()`, `tagNamed()`
- Folder: `childNamed()`, `folderNamed()`, `projectNamed()`, `sectionNamed()`

**`apply()` method** on Task, Tag, Folder — purpose unclear from reflection alone.

**Perspective:** `fileWrapper()`, `writeFileRepresentationIntoDirectory()` — export/backup.

#### Static / Class-Level Members

**Lookup by ID (all entity types):**
- `Task.byIdentifier()`, `Project.byIdentifier()`, `Tag.byIdentifier()`, `Folder.byIdentifier()` — direct ID-based lookup. In the current architecture (full snapshot), these aren't the primary access pattern, but useful to know they exist.

**Task creation from text:**
- `Task.byParsingTransportText()` — create tasks from text, likely TaskPaper format. Powerful for batch creation with hierarchy. Worth exploring for future write operations.

**Special objects:**
- `Tag.forecastTag` — the special Forecast tag as a static property (full Tag instance with 25 props)
- `Perspective.favorites` — 17 favorite perspectives. Could derive `isFavorite` boolean by scanning this collection.

**Enum object structure (confirmed via Script 25c):**

Every enum object follows the same pattern: `name` (string — the enum's full name), `prototype` (prototype object), the named constants, and `all` (Array of all constant values).

| Enum Object | Props | Structure |
|-------------|-------|-----------|
| Task.Status | 10 | name + prototype + 7 constants + all(7) |
| Task.RepetitionScheduleType | 6 | name + prototype + 3 constants + all(3) |
| Task.AnchorDateKey | 6 | name + prototype + 3 constants + all(3) |
| Task.RepetitionMethod | 7 | name + prototype + 4 constants + all(4) — deprecated |
| Project.Status | 7 | name + prototype + 4 constants + all(4) |
| Tag.Status | 6 | name + prototype + 3 constants + all(3) |
| Folder.Status | 5 | name + prototype + 2 constants + all(2) |
| Task.TagInsertionLocation | 2 | name + prototype only (no named constants) |
| Task.ChildInsertionLocation | 2 | name + prototype only |
| Tag.ChildInsertionLocation | 2 | name + prototype only |
| Tag.TaskInsertionLocation | 2 | name + prototype only |
| Folder.ChildInsertionLocation | 2 | name + prototype only |
| Project.ReviewInterval | 2 | name + prototype only |
| Task.Notification | 3 | name + prototype + Kind sub-namespace |

**`String()` on enum values reveals the name.** `String(Task.Status.Active)` returns `"[object Task.Status: Active]"`. This contradicts the Section 1 finding that `.toString()` returns "useless output" — the output actually contains the type and value name. `.name` on individual values is still `undefined`, but the string representation is parseable. The bridge could use this as a fallback for unknown enum values.

**`all` array on every status enum.** The bridge can iterate `Task.Status.all` (etc.) instead of maintaining hardcoded constant lists. This is forward-compatible: if OmniFocus adds a new status, `all` will include it, and the bridge can use `String()` to extract its name.

**Deprecated enum: `Task.RepetitionMethod`** — the old pre-4.7 API. 4 constants: None, Fixed, DeferUntilDate, DueDate. Still exists for backward compatibility but should be ignored in favor of `scheduleType` + `anchorDateKey`.

**InsertionLocation and ReviewInterval** — have only `name` + `prototype`, no named constants. These are constructor types (e.g., used for `task.beginning`, `task.ending`), not enumerations.

**Perspective filter config (confirmed via Script 25c):**

`archivedFilterRules` is a recursive tree structure forming a complete query language. Rule types found:

| Rule Type | Value Type | Example Values |
|-----------|-----------|----------------|
| `actionAvailability` | string | `"available"`, `"remaining"`, `"completed"`, `"dropped"` |
| `actionStatus` | string | `"flagged"`, `"due"` |
| `actionHasAnyOfTags` | array of tag IDs | `["d56-9LNYh_w"]` |
| `actionWithinFocus` | array of IDs | `["hc4DsZJoueT"]` |
| `actionHasProjectWithStatus` | string | `"active"`, `"onHold"`, `"stalled"` |
| `actionHasNoProject` | boolean | `true` |
| `actionMatchingSearch` | array of strings | `["brag"]` |
| `actionWithinDuration` | number (minutes) | `15` |
| `actionHasDueDate` | boolean | `true` |
| `actionHasDeferDate` | boolean | `true` |
| `actionHasDuration` | boolean | `true` |
| `actionIsLeaf` | boolean | `true` |
| `actionDateField` | string | `"defer"`, `"due"`, `"planned"`, `"modified"` |
| `actionDateIsInThePast` | object | (date spec) |
| `actionDateIsAfterDateSpec` | object | (date spec) |
| `actionDateIsBeforeDateSpec` | object | (date spec) |
| `actionDateIsInTheNext` | object | (date spec) |
| `disabledRule` | object | (disabled rule, kept but inactive) |
| `comment` | string | User-visible comment embedded in filter |
| `aggregateRules` + `aggregateType` | array + string | Nested groups: `"all"` (AND), `"any"` (OR), `"none"` (NOT) |

`archivedTopLevelFilterAggregation`: `"all"` (AND logic) or `null` (separator perspectives).
`iconColor`: object with `colorSpace`, `red/green/blue`, `hue/saturation/brightness`, `alpha`, `hex` — or `null`.
Built-in perspectives return `undefined` for all three properties.

#### Corrections to Earlier Findings

- **Section 6 (Perspectives):** "Perspective filter/sorting/grouping configuration is NOT accessible" is partially wrong. `archivedFilterRules` and `archivedTopLevelFilterAggregation` exist and are readable. The earlier probes used wrong property names.
- **Section 3 (Tasks):** `effectiveCompletedDate` and `effectiveCompletionDate` are aliases returning identical values (265/265 match, Script 25b). Use `effectiveCompletionDate` as canonical. `completedDate` (non-effective) is `undefined` — does not exist.
- **Section 1 (Enums):** `.toString()` / `String()` on enum values is NOT useless — it returns `"[object Task.Status: Active]"` format, which contains the type and value name. `.name` on individual values is still `undefined`. The `all` property on every enum namespace provides the complete list of valid constants.

#### Bridge Action Items
- [ ] `url` getter exists on Task, Project, Tag, Folder, Perspective — expose in model for deep linking in agent responses
- [ ] `Task.byParsingTransportText()` — explore for batch task creation with hierarchy (TaskPaper format)
- [ ] `Perspective.favorites` — can derive `isFavorite` boolean by checking membership
- [ ] `Tag.forecastTag` — document as special static tag
- [ ] `tag.childrenAreMutuallyExclusive` — expose in tag model
- [ ] `tag.availableTasks` / `tag.remainingTasks` — query getters available on tags (not needed for snapshot architecture but good to document)
- [ ] `document.sync()` — can trigger sync programmatically
- [ ] `document.undo()` / `document.redo()` — available for reverting operations
- [ ] `effectiveCompletionDate` and `effectiveCompletedDate` are aliases (265/265 match, Script 25b). Use `effectiveCompletionDate` as canonical — matches `completionDate` at the non-effective level. `completedDate` (non-effective) is `undefined` and does not exist.
- [ ] Investigate `project.defaultSingletonActionHolder` vs `containsSingletonActions`
- [ ] `noteText` (rich text object) exists alongside `note` (plain string) — bridge uses `note` for now
- [ ] Every enum has an `.all` array containing all valid constants — documented for reference but do NOT iterate at runtime (OmniFocus performance is poor — freezes for seconds on 2000+ tasks). Bridge should use hardcoded `===` checks and throw an error on unknown values so they can be added manually.
- [ ] `String()` on enum values returns `"[object Type: Value]"` — documented for reference. Could be used as a diagnostic tool when debugging unknown enum values, but not for production enum resolution.
- [ ] Perspective filter rules (`archivedFilterRules`) expose a complete query language — documented in Section 9.13 but NOT implementing in bridge for now (too complex). Future milestone potential.
