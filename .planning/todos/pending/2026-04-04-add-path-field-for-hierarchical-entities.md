---
created: 2026-04-04T13:49:52.656Z
title: Add path field for hierarchical entities
area: models
files:
  - src/omnifocus_operator/models/
---

## Problem

When listing folders, projects, and tasks, the hierarchy is represented via a flat list with `parent` IDs. Reconstructing the tree requires cross-referencing all items. Referenced entities return both ID and name (tags on tasks, parent on tasks), but folder on projects returns a bare ID — inconsistent.

## Solution

Add a `path` field alongside `name` for hierarchical entities, e.g. `"path": "Core / Mari / Baby"`. Gives the full hierarchy at a glance without reconstruction from flat data. Also make folder reference on projects consistent (return both ID and name like other references).
