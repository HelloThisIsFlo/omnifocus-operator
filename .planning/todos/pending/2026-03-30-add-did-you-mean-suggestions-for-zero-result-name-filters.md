---
created: 2026-03-30T10:45:00.000Z
updated: 2026-03-30T21:45:00.000Z
title: Add did-you-mean suggestions for unresolved name filters
area: service
files:
  - src/omnifocus_operator/service/service.py
  - src/omnifocus_operator/agent_messages/warnings.py
---

## Problem

When a name-based filter (project, folder, tags) can't be resolved due to a typo or near-miss, the agent gets an empty list with no guidance. This is a silent failure — the agent doesn't know whether the filter genuinely matched nothing or the user misspelled something.

Applies uniformly to all name-based filters:
- `list_tasks(project="Personl")` → 0 results, no hint
- `list_projects(folder="Wrok")` → 0 results, no hint
- `list_tasks(tags=["Erand"])` → 0 results, no hint

## Solution

**Where it fires:** Step 3 of the service-layer resolution cascade (see "Uniform name-vs-ID resolution" todo). When a name reference fails both ID matching and substring matching, fuzzy matching runs as a fallback.

**How it works:**
1. Service resolves entity reference — ID match? No. Substring match? No.
2. Entity list is already in memory from prior resolution steps
3. `difflib.get_close_matches(query_value, entity_names, n=3, cutoff=0.6)` — stdlib, zero new deps
4. If close matches found → attach warning to `ListResult.warnings`
5. Skip the unresolved filter (don't pass it to repo — it can't match anything)

**Example:**
```python
# During resolution, after ID and substring checks fail
close = difflib.get_close_matches(value, all_names, n=3, cutoff=0.6)
if close:
    warnings.append(
        f'No match for project "{value}". Did you mean: {", ".join(close)}?'
    )
# Filter is skipped — repo never sees it
```

**Covers:** project, folder, tags filters (and any future name-based filters)

**Depends on:** Uniform name-vs-ID resolution todo (provides the resolution cascade where this plugs in)

**Requirement:** INFRA-07 (Phase 37)
