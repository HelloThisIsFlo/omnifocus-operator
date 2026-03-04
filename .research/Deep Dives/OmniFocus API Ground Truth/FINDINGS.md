# OmniFocus API Ground Truth — Findings

> Empirical findings from running audit scripts against a live OmniFocus database.
> Each section is filled in during the guided audit session (`/omnifocus-api-audit`).
> Every finding below is backed by script output — not documentation, not assumptions.

**Audit date:** _TO BE FILLED_
**OmniFocus version:** _TO BE FILLED_
**Database size:** _TO BE FILLED_ (projects, tasks, tags, folders)

---

## 1. OmniFocus Enum System

> Source: Script 03 (Status Enum Discovery)

### Opaque Enum Behavior
_TO BE FILLED — confirm that .name, String(), .toString() all fail_

### Project.Status Constants
_TO BE FILLED — list all discovered constants_

| Constant | Exists? | Count in DB |
|----------|---------|-------------|
| Active   |         |             |
| OnHold   |         |             |
| Done     |         |             |
| Dropped  |         |             |

### Task.Status Constants
_TO BE FILLED — list all discovered constants_

| Constant  | Exists? | Count in DB |
|-----------|---------|-------------|
| Available |         |             |
| Blocked   |         |             |
| Completed |         |             |
| Dropped   |         |             |
| DueSoon   |         |             |
| Next      |         |             |
| Overdue   |         |             |

### Tag.Status Constants
_TO BE FILLED_

| Constant | Exists? | Count in DB |
|----------|---------|-------------|
| Active   |         |             |
| OnHold   |         |             |
| Dropped  |         |             |

### Folder.Status Constants
_TO BE FILLED_

| Constant | Exists? | Count in DB |
|----------|---------|-------------|
| Active   |         |             |
| Dropped  |         |             |

### Cross-Type Compatibility
_TO BE FILLED — is Project.Status.Active === Tag.Status.Active?_
_Can one switch function handle all entity types?_

### Bridge Action Items
- [ ] _TO BE FILLED_

---

## 2. Project Type

> Source: Scripts 01, 02, 04, 06, 07

### Root Task Relationship
_TO BE FILLED — confirm p.id() === p.task.id()_

### Task-Only Fields (undefined on p.*, defined on p.task.*)
_TO BE FILLED — list fields, confirm always present_

| Field           | On p.* | On p.task.* | Always present? |
|-----------------|--------|-------------|-----------------|
| added           |        |             |                 |
| modified        |        |             |                 |
| active          |        |             |                 |
| effectiveActive |        |             |                 |

### Effective Fields Bug
_TO BE FILLED — which effective* fields are broken on p.*?_

| Field                   | On p.*    | On p.task.* | Broken? |
|-------------------------|-----------|-------------|---------|
| effectiveDueDate        |           |             |         |
| effectiveDeferDate      |           |             |         |
| effectiveCompletionDate |           |             |         |
| effectivePlannedDate    |           |             |         |
| effectiveDropDate       |           |             |         |
| effectiveFlagged        |           |             |         |

### Shared Fields (proxied identically p.* ↔ p.task.*)
_TO BE FILLED — list all confirmed-proxied fields_

### Status Cross-Reference
_TO BE FILLED — from Script 04_

| Project.Status | task.active | task.effectiveActive | task.Status |
|----------------|-------------|----------------------|-------------|
| Active         |             |                      |             |
| OnHold         |             |                      |             |
| Done           |             |                      |             |
| Dropped        |             |                      |             |

### Nullable Fields
_TO BE FILLED — which fields are legitimately nullable?_

### Bridge Action Items
- [ ] _TO BE FILLED_

---

## 3. Task Type

> Source: Script 09

### Field Map
_TO BE FILLED — complete list with types and distributions_

### Always-Present Fields
_TO BE FILLED — fields that are never null/undefined_

### Nullable Fields
_TO BE FILLED — fields that can be null, with % null_

### Status Distribution
_TO BE FILLED_

### Relationship Fields
_TO BE FILLED — project, parentTask, assignedContainer_

### Bridge Action Items
- [ ] _TO BE FILLED_

---

## 4. Tag Type

> Source: Script 10

### Field Map
_TO BE FILLED_

### Status Enum
_TO BE FILLED — Tag.Status constants and their meanings_

### Relationship to Project Status
_TO BE FILLED — cross-type comparison results_

### Bridge Action Items
- [ ] _TO BE FILLED_

---

## 5. Folder Type

> Source: Script 11

### Field Map
_TO BE FILLED_

### Status Enum
_TO BE FILLED — Folder.Status constants_

### Bridge Action Items
- [ ] _TO BE FILLED_

---

## 6. Perspective Type

> Source: Script 12

### Field Map
_TO BE FILLED — which properties exist beyond id/name_

### Built-in vs Custom
_TO BE FILLED — how to distinguish, identifier behavior_

### Bridge Action Items
- [ ] _TO BE FILLED_

---

## 7. Write Behavior

> Source: Scripts 05, 06, 07, 08

### Property Proxying Rules
_TO BE FILLED — which side to read from, which side to write to_

| Operation                  | Result      |
|----------------------------|-------------|
| Set p.dueDate → t.dueDate  |             |
| Clear p.dueDate → t.dueDate|             |
| Set t.flagged → p.flagged  |             |
| Set p.completed = true     |             |
| Set p.completed = false    |             |
| Set p.status = OnHold      |             |
| Set p.status = Active      |             |

### Creation Behavior
_TO BE FILLED — how newly created entities look in the API_

### Deletion Behavior
_TO BE FILLED — order of deletion, verification_

### Bridge Action Items
- [ ] _TO BE FILLED_

---

## 8. Bridge Implications

> Summary of all bridge changes needed, derived from findings above.

### Critical Fixes (correctness bugs)
- [ ] _TO BE FILLED_

### Improvements (data quality)
- [ ] _TO BE FILLED_

### Model Changes
- [ ] _TO BE FILLED_

### Enum Changes
- [ ] _TO BE FILLED_
