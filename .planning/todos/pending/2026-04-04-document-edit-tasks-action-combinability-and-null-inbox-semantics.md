---
created: 2026-04-04T13:49:52.656Z
title: Document edit_tasks action combinability and null-inbox semantics
area: docs
files:
  - src/omnifocus_operator/agent_messages/descriptions.py
---

## Problem

Two documentation gaps in `edit_tasks`:

1. **Combinable actions**: The `actions` object nests lifecycle (complete/drop), move (reposition), and tags (add/remove/replace). The docs explain each individually but never state whether they can be combined in a single call. Callers have to guess or make multiple calls.

2. **null=inbox in move**: The `actions.move` description says "ending/beginning with null moves to inbox." Everywhere else in edit_tasks, null means "clear this field" (patch semantics). Here it means a specific destination. A brief parenthetical would clarify: "beginning/ending with null moves to inbox (i.e. removes from any project)."

## Solution

- Add a sentence to `EDIT_TASKS_TOOL_DOC` or the actions description: "lifecycle, move, and tags can be combined freely in one call."
- Add inline clarification to the move description: "beginning/ending with null moves to inbox (i.e. removes from any project)."
