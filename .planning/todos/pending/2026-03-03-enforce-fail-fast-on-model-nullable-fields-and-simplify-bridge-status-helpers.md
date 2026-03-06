---
created: 2026-03-03T22:10:26.827Z
title: Enforce fail-fast on model nullable fields and simplify bridge status helpers
area: models
files:
  - src/omnifocus_operator/models/_task.py:34-35
  - src/omnifocus_operator/models/_tag.py:25-26,29
  - src/omnifocus_operator/models/_folder.py:25-26,29
  - src/omnifocus_operator/models/_project.py:31
  - src/omnifocus_operator/bridge/bridge.js:39-48,80,115-116,156,170
  - src/omnifocus_operator/models/_enums.py
  - .research/Deep Dives/OmniFocus API Ground Truth/BRIDGE-SPEC.md
---

## Problem

An audit of all 32 nullable model fields found 8 that are incorrectly nullable — OmniFocus
always provides these values, so `| None = None` masks potential data corruption instead of
failing fast.

Additionally, live testing revealed that **OmniFocus Automation enum objects are opaque** —
`.name` returns `undefined`. The inline `x.status.name` pattern on projects/tags/folders is
therefore **actively broken**, always producing `None`. The nullable type annotation hides this bug.

**BRIDGE-SPEC also reveals broader issues:**
- The shared `EntityStatus` enum is wrong — each entity type has a **different set of valid
  statuses** and OmniFocus uses **separate enum namespaces** per type (`Project.Status.Active !==
  Tag.Status.Active`). A single shared resolver or Python enum cannot work.
- Current `EntityStatus` (Active, Done, Dropped) is **missing `OnHold`** — used by both
  Project and Tag.
- Project is **missing 4 fields** that BRIDGE-SPEC marks required: `active`, `effectiveActive`,
  `added`, `modified`. These are undefined on `p.*` and MUST be read from `p.task.*`.

**Source of truth:** `.research/Deep Dives/OmniFocus API Ground Truth/BRIDGE-SPEC.md`

## Solution

### 1. Bridge: per-entity status resolvers (JavaScript) — do first

The bridge MUST use **separate resolver functions per entity type** because enum namespaces
are isolated (`Project.Status.Active !== Tag.Status.Active`). A single `es()` will not work.

Create three resolvers:

- **`ps(s)` — Project status** (4 values): `Project.Status.Active` -> `"Active"`,
  `Project.Status.OnHold` -> `"OnHold"`, `Project.Status.Done` -> `"Done"`,
  `Project.Status.Dropped` -> `"Dropped"`. Throw on unknown with `String(s)`.
- **`gs(s)` — Tag status** (3 values): `Tag.Status.Active` -> `"Active"`,
  `Tag.Status.OnHold` -> `"OnHold"`, `Tag.Status.Dropped` -> `"Dropped"`.
  Throw on unknown with `String(s)`.
- **`fs(s)` — Folder status** (2 values): `Folder.Status.Active` -> `"Active"`,
  `Folder.Status.Dropped` -> `"Dropped"`. Throw on unknown with `String(s)`.

Replace the broken inline patterns:
- Project line 115: `p.status ? p.status.name : null` -> `ps(p.status)`
- Tag line 156: `g.status ? g.status.name : null` -> `gs(g.status)`
- Folder line 170: `f.status ? f.status.name : null` -> `fs(f.status)`

### 2. Bridge: fix `ts()` fallback

Change `return null` (line 47) to `throw new Error("Unknown TaskStatus: " + String(s))`.
All enum resolvers must throw on unknown values — fail-fast at the bridge boundary.

### 3. Bridge: add missing Project fields from `p.task.*`

BRIDGE-SPEC confirms 4 fields are undefined on `p.*` but always present on `p.task.*`:
- `active: p.task.active`
- `effectiveActive: p.task.effectiveActive`
- `added: d(p.task.added)`
- `modified: d(p.task.modified)`

Add these to the project mapping in handleSnapshot().

### 4. Python: split `EntityStatus` into per-entity enums

Replace the single `EntityStatus` in `_enums.py` with three separate enums matching
BRIDGE-SPEC Section 3:

- **`ProjectStatus`**: Active, OnHold, Done, Dropped
- **`TagStatus`**: Active, OnHold, Dropped
- **`FolderStatus`**: Active, Dropped

Update model imports:
- `_project.py`: `status: ProjectStatus`
- `_tag.py`: `status: TagStatus`
- `_folder.py`: `status: FolderStatus`

### 5. Python: make 9 fields required (remove `| None = None`)

**6 timestamp fields** (confirmed always-present by BRIDGE-SPEC):
- Task: `added`, `modified`
- Tag: `added`, `modified`
- Folder: `added`, `modified`

**3 status fields** (after per-entity resolvers are working):
- Project: `status: ProjectStatus` (was `EntityStatus | None`)
- Tag: `status: TagStatus` (was `EntityStatus | None`)
- Folder: `status: FolderStatus` (was `EntityStatus | None`)

### 6. Python: add 4 new required fields to Project model

- `active: bool`
- `effective_active: bool`
- `added: AwareDatetime`
- `modified: AwareDatetime`

### 7. Update tests

- Remove test cases that set the 9 fields to `None`
- Add tests for the 3 new Python enum types
- Add bridge tests for each per-entity resolver
- Add tests for new Project fields

### 8. Cleanup

- Delete `EntityStatus` from `_enums.py` (replaced by 3 per-entity enums)
- Remove any references to `EntityStatus` across codebase
