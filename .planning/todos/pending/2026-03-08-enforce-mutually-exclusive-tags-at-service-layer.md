---
created: 2026-03-08T01:52:00.000Z
title: Enforce mutually exclusive tags at service layer
area: service
priority: medium
files:
  - src/omnifocus_operator/service.py
---

## Problem

OmniJS allows assigning multiple mutually exclusive sibling tags to a task. OmniFocus only enforces exclusivity at the UI level. Agents using `add_tasks` can create tasks in states the UI wouldn't normally allow.

Discovered during Phase 15 UAT (ISSUE-3, Test #10). UAT file: `.planning/phases/15-write-pipeline-task-creation/15-UAT.md`.

## Solution

Discuss in a `/gsd:discuss-phase` before planning. Key questions:

- How to detect mutual exclusivity? Tags in OmniFocus can be marked as "exclusive" at the parent level — need to check if this metadata is accessible via OmniJS or SQLite
- Should the service layer validate before writing, or warn after?
- Edge case: what if the agent intentionally wants to override exclusivity?
- Scope: applies to `add_tasks` and future `edit_tasks`
- OmniFocus self-corrects when user later adds a tag from the same group via UI, so this is low severity
