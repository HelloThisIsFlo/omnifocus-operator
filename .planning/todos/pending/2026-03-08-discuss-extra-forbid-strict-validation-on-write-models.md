---
created: 2026-03-08T01:51:46.055Z
title: Discuss extra=forbid strict validation on write models
area: models
priority: medium
files:
  - src/omnifocus_operator/models/base.py:29-33
  - src/omnifocus_operator/models/write.py:18-34
  - src/omnifocus_operator/server.py:152-168
---

## Problem

Write models (e.g. `TaskCreateSpec`) silently drop unknown fields because `OmniFocusBaseModel` uses Pydantic's default `extra="ignore"`. An agent sending `{"name": "Test", "repetitionRule": "weekly"}` gets no error — the field is silently discarded and the agent believes it worked.

Discovered during Phase 15 UAT (ISSUE-4). Debug session: `.planning/debug/tool-description-boundaries.md`.

## Solution

Discuss in a `/gsd:discuss-phase` before planning fixes. Key questions:

- Should we add a `WriteModel(OmniFocusBaseModel)` intermediate base with `extra="forbid"`?
- Or set it directly on each write spec (`TaskCreateSpec`, future `TaskEditSpec`, etc.)?
- Read models must stay permissive (`extra="ignore"`) — OmniFocus may return fields we don't model yet
- Also consider: should the `add_tasks` tool docstring explicitly declare supported field boundaries?
- Interaction with ISSUE-4 tool description fix — both address the same agent confusion, from different angles (runtime vs documentation)
