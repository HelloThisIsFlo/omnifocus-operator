---
created: 2026-04-04T13:49:52.656Z
title: Return full inbox hierarchy from inInbox query
area: repository
files:
  - src/omnifocus_operator/repository/hybrid/hybrid.py
  - src/omnifocus_operator/repository/hybrid/query_builder.py
---

## Problem

`list_tasks` with `inInbox: true` only returns root-level inbox tasks. Child tasks (subtasks) are not included, even when they contain meaningful data (completed subtasks with repetition rules, due dates, etc.).

This is inconsistent with project queries, which return the full task hierarchy within the project. An inbox task like "TEST: Instant Edge Cases" with multiple children (Q1, Q2, Q4, Q5) only shows the parent — children are invisible unless you already know to query by parent ID.

Especially important for parallel/autodone action groups where the parent is just a container and real work lives in subtasks.

## Solution

When returning inbox tasks, include the full hierarchy (parent + children) — same behavior as project queries. Pre-existing repo/service behavior, not introduced by phase 37.

## Resolution

Covered by **Milestone v1.3.1 — Inbox as First-Class Value**, acceptance criteria: "`list_tasks(inInbox=true)` returns inbox tasks (including full hierarchy — subtasks of inbox tasks)." See `.research/updated-spec/MILESTONE-v1.3.1.md`.
