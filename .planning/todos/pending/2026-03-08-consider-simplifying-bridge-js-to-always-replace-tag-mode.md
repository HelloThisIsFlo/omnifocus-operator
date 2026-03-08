---
created: 2026-03-08T11:51:37.290Z
title: Consider simplifying bridge.js to always-replace tag mode
area: bridge
priority: high
files:
  - src/omnifocus_operator/bridge/bridge.js
  - src/omnifocus_operator/service.py
---

## Problem

The bridge has 4 tag modes (replace, add, remove, add_remove), each with its own handler in bridge.js with separate logic for resolving tag IDs, calling addTags()/removeTags()/etc. The service layer decides which mode to use based on user input (tags vs addTags vs removeTags vs addTags+removeTags).

## Proposal

Move all tag set computation to the Python service layer. The bridge only ever receives "replace" mode with a complete, final tag list. The service already fetches the current task (including its tags) before editing.

### How each user operation maps:
- `tags: ["A", "B"]` → replace with ["A", "B"] (unchanged)
- `addTags: ["X"]` → read current [A, B], compute [A, B, X], replace
- `removeTags: ["B"]` → read current [A, B], compute [A], replace
- `addTags: ["X"] + removeTags: ["B"]` → read current [A, B], compute [A, X], replace
- `tags: []` → replace with [] (unchanged)

### What changes:
- bridge.js tag handling: 4 branches (~40 lines) → 1 branch (~5 lines)
- Service layer does set arithmetic (union, difference) in Python
- Bridge tests simplify dramatically — one tag code path
- The removeTags bug (params.tagIds vs params.removeTagIds) becomes impossible

### Benefits:
- All tag logic in Python — easier to test, type-check, evolve
- No more mode dispatch in bridge.js — fewer moving parts, fewer contract mismatches
- No-op detection becomes trivial: compare computed set vs current set
- New tag operations (e.g., toggle) only require Python changes
- The removeTags crash (ISSUE-1 from UAT) would never have happened with this design

### Tradeoffs:
- Not atomic: if another process adds a tag between read and write, we overwrite. But the current approach has the same race — already non-atomic at the service level.
- Slightly more data over the bridge (full tag list vs deltas). Negligible for realistic tag counts.
- OmniFocus addTags()/removeTags() APIs are more surgical, but bridge-level atomicity doesn't matter since we're already non-atomic at the service level.

### Broader principle
Part of a larger question: how dumb should the bridge be? The bridge currently does hasOwnProperty patch semantics for fields (appropriate — avoids overwriting untouched fields with undefined). But for tags, the service layer already has full context — it could compute the final state and just tell the bridge "set exactly this."

### Decisions needed
- Is the simplicity gain worth the (theoretical, already-present) atomicity tradeoff?
- Should we apply always-replace to other bridge operations in the future?
- Or capture as a hard requirement in the spec so milestone audits catch bridge logic creep?
