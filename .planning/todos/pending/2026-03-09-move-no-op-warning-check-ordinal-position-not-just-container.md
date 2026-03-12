---
created: 2026-03-09T23:43:40.983Z
title: Move no-op warning check ordinal position not just container
area: service
files:
  - src/omnifocus_operator/service/
---

## Problem

The edit_tasks move no-op detection only checks if the task is already a child of the target parent. It doesn't distinguish beginning vs ending position — so moving the last child to "beginning" of the same parent gets flagged as a no-op when it would actually reorder.

## Solution

- Query sibling order (SQLite rank column or snapshot children list) to determine current ordinal position
- Compare requested position (beginning/ending) against actual position before flagging no-op
- Low priority — the warning is transparent about the limitation

## Related

- **[Fix same-container move by translating to moveBefore/moveAfter](2026-03-12-fix-same-container-move-by-translating-to-movebefore-moveafter.md)** — fixes the move itself. This todo is about the warning accuracy; that one is about the operation actually working. Both need ordering data.
- **[Add position field to expose child task ordering](2026-03-08-add-position-field-to-expose-child-task-ordering.md)** — exposing an `order` field on task responses would provide the sibling ordering data this fix needs. Consider implementing together.
