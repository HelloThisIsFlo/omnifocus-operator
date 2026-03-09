---
created: 2026-03-09T20:00:00.000Z
title: "Simplify bridge.js tag handling: diff-based approach"
area: bridge
priority: high
files:
  - src/omnifocus_operator/bridge/bridge.js
  - src/omnifocus_operator/service.py
  - tests/test_service.py
  - tests/bridge/test_bridge_edit.test.js
---

## Problem

The bridge has 4 tag modes (replace, add, remove, add_remove), each with its own handler in bridge.js (~45 lines, lines 272-316) with separate logic for resolving tag IDs. The `removeTags` bug (ISSUE-1 from Phase 16 UAT, `params.tagIds` vs `params.removeTagIds`) happened precisely because of this complexity. This logic lives in the lowest-trust layer — only verifiable via manual UAT against real OmniFocus.

## Solution — Diff-Based Approach

Move all tag set computation to Python (high-trust, fully covered by `test_service`). Bridge receives only `removeTagIds` and `addTagIds` — no mode field, no branching.

### Service layer (Python)

1. Service already reads the current task (including tags) before editing
2. Compute `final_set` from user input:
   - `tags: ["A", "B"]` → final = {A, B}
   - `addTags: ["X"]` → final = current ∪ {X}
   - `removeTags: ["B"]` → final = current - {B}
   - `addTags: ["X"] + removeTags: ["B"]` → final = (current ∪ {X}) - {B}
   - `tags: null` or `tags: []` → final = {} (clear all)
3. Compute diff: `to_remove = current - final`, `to_add = final - current`
4. Both empty → no-op, skip bridge call entirely
5. Send only `removeTagIds` and `addTagIds` to bridge

### Bridge (JavaScript, ~4 lines)

```javascript
if (params.removeTagIds.length) task.removeTags(resolve(params.removeTagIds));
if (params.addTagIds.length) task.addTags(resolve(params.addTagIds));
```

Replaces the current 4-branch ~45-line tag handling block.

### Why Diff Instead of Always-Replace

- **Always-replace** (`clearTags()` + `addTags(final)`) works but is wasteful: adding 1 tag to a task with 5 tags means clearing 5, resolving 6, re-adding 6
- **Diff** computes the minimal delta: same operation resolves 1 tag and calls `addTags([1])`
- No `replaceTags()` in OmniJS — confirmed via Omni Automation docs. Available: `addTag`, `addTags`, `removeTag`, `removeTags`, `clearTags` (v3.8+)
- `addTags`/`removeTags` are idempotent — safe even with race conditions

### What Stays the Same

- **API surface**: `TaskEditSpec` fields (`tags`, `addTags`, `removeTags`, mutual exclusivity validator) — unchanged. Agents see no difference.
- **Warning logic**: "tag already present" / "tag not on task" warnings stay in Python — already fully testable

## Why This Matters

Moves logic from a **low-trust zone** (bridge.js, manual UAT only) to a **high-trust zone** (Python service, `test_service` proves correctness). Net simplification that directly increases confidence.

## Resolved Unknowns — Ready to Implement

- No `replaceTags()` in OmniJS — confirmed
- `addTags`/`removeTags` are idempotent — confirmed
- `tags: null` works naturally with diff (to_remove = all current, to_add = {}) — no special case
- No-op detection is trivial (both diffs empty → skip bridge call)
- Atomicity tradeoff is moot — already non-atomic at service level

## Relationship to Other Todos

- **Supersedes**: `.planning/todos/done/2026-03-08-consider-simplifying-bridge-js-to-always-replace-tag-mode.md` — we considered it, decided yes, refined to diff-based
- **#8 (Extract validation layer)**: Agreed to wait. Service isn't cluttered enough yet. Revisit if this change makes it noticeably heavier.
