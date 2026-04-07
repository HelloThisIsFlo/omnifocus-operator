---
created: 2026-03-08T11:51:37.290Z
title: Consider unified position concept across create edit get APIs
area: api-design
priority: high
files:
  - src/omnifocus_operator/models/
  - src/omnifocus_operator/service/
---

## Problem

Positioning uses three different shapes across the API:
- `add_tasks`: `parent` field (string ID, always appends to end)
- `edit_tasks`: `moveTo` object with `beginning/ending/before/after` keys
- `get_task`: returns `parent` object but no ordering info

This works but is inconsistent and harder to learn.

## Solution

Unify under a single `position` concept used consistently across create/edit/get:
- Create: `{"name": "New Task", "position": {"parent": "abc", "order": 3}}`
- Edit: `{"id": "xyz", "position": {"parent": "abc", "after": "sibling-id"}}`
- Get: `{"id": "xyz", "position": {"parent": "abc", "order": 3}}`

Design considerations:
- Support both absolute (`order: 3`) and relative (`after: "id"`) positioning
- Relative is more robust for parallel/concurrent calls (no off-by-one risk)
- `position: {"parent": null}` = inbox
- Omitting `position` entirely = no move (edit) or inbox at end (create)
- Current `parent` field on `add_tasks` covers 90% of cases — unified `position` is a superset

**Priority**: Low — consider for v2.0 API design. Current separate shapes work fine, but unification would make the API more cohesive. Not worth a breaking change now.
