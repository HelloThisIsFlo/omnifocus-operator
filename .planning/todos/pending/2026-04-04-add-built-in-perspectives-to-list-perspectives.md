---
created: 2026-04-04T13:49:52.656Z
title: Add built-in perspectives to list_perspectives
area: repository
files:
  - src/omnifocus_operator/repository/hybrid/hybrid.py
  - src/omnifocus_operator/bridge/bridge.js
  - .planning/debug/perspectives-missing-builtin.md
---

## Problem

`list_perspectives` only returns custom perspectives. Built-in perspectives (Inbox, Projects, Tags, Forecast, Flagged, Review) are missing. The SQLite `Perspective` table only stores custom perspectives; built-ins are application-level constructs only available via OmniJS `Perspective.all`.

Diagnosed in phase 37 UAT. Debug session has full root cause analysis.

## Solution

Needs discussion — interface change. Options identified:
1. Hard-code built-in perspective names and merge with SQLite results (id=None)
2. Fall back to bridge for perspectives (table is tiny, perf cost negligible)
3. Merge both sources on `get_all`

Deferred from phase 37 gap closure to allow proper design discussion first.
