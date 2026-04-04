---
created: 2026-04-04T13:49:52.656Z
title: Add built-in perspectives to list_perspectives
area: repository
files:
  - src/omnifocus_operator/repository/hybrid/hybrid.py
  - src/omnifocus_operator/bridge/bridge.js
resolution: deferred
---

## Problem

`list_perspectives` only returns custom perspectives. Built-in perspectives (Inbox, Projects, Tags, Forecast, Flagged, Review) are missing. The SQLite `Perspective` table only stores custom perspectives; built-ins are application-level constructs only available via OmniJS `Perspective.all`.

Diagnosed in phase 37 UAT. Debug session has full root cause analysis.

## Resolution

Deferred to v1.5 (UI & Perspectives). Will be implemented as part of a `BridgePerspectiveMixin` that handles all bridge-backed perspective operations:
- `list_perspectives` (built-in + custom) — solves this gap
- Perspective content reads (task IDs from current view) — for `list_tasks(current_perspective_only)`
- Future: perspective rule parsing for richer presentation (tasks vs projects)

The mixin approach keeps all perspective bridge logic cohesive in the repository layer, while pure UI operations (`show_perspective`, `get_current_perspective`) stay at the service layer.

Accepted gap: until v1.5, agents only see custom perspectives. This is fine because there are no perspective interaction tools yet — listing built-ins without being able to act on them adds no value.
