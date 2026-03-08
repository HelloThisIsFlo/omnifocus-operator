---
created: 2026-03-08T11:51:37.290Z
title: Add position field to expose child task ordering
area: models
priority: high
files:
  - src/omnifocus_operator/models/
  - src/omnifocus_operator/service/
---

## Problem

The agent has no way to see child ordering — `get_task` shows the parent but not siblings or their position. During UAT, verifying task order after moves was impossible without manual OmniFocus inspection. Workaround: set `estimatedMinutes` to 1, 2, 3... as position markers, then asked user to visually confirm sequential numbers.

## Solution

**Near-term (v1.3 — list/filter tools)**:
- Add an explicit `position` integer field to task responses
- When listing children of a parent, return them in display order with position
- Example: `[{"id": "abc", "name": "Design", "position": 0, "parent": "xyz"}, ...]`

**Later (v1.4 — TaskPaper format)**:
- TaskPaper output naturally shows hierarchy and order via indentation
- Gives the agent a complete structural snapshot without multiple queries

Both approaches are complementary: position field for programmatic use, TaskPaper for full-hierarchy comprehension.
