---
created: 2026-03-30T10:45:00.000Z
title: Add did-you-mean suggestions for zero-result name filters
area: service
files:
  - src/omnifocus_operator/service/service.py
  - src/omnifocus_operator/agent_messages/warnings.py
  - src/omnifocus_operator/contracts/use_cases/list/tasks.py
---

## Problem

When a name-based filter (project, folder, tags) returns zero results due to a typo or near-miss, the agent gets an empty list with no guidance. This is a silent failure — the agent doesn't know whether the filter genuinely matched nothing or the user misspelled something.

Applies uniformly to all name-based filters:
- `list_tasks(project="Personl")` → 0 results, no hint
- `list_projects(folder="Wrok")` → 0 results, no hint
- `list_tasks(tags=["Erand"])` → 0 results, no hint

## Solution

**Where it lives:** Service layer (`service.py` list methods or future `_ListTasksPipeline`). The repo returns `ListRepoResult(total=0)`, the service detects zero results + active name filter, fetches the full entity list, computes similarity, and attaches a warning via the existing `agent_messages` system when building the `ListResult`.

**How it works:**
1. Pipeline gets `result.total == 0` from repo
2. Check which name-based filters were active (project, folder, tags)
3. For each active filter, fetch the full entity list (cheap — tags ~64, folders ~79, projects ~300 even for power users)
4. Use `difflib.get_close_matches(query_value, entity_names, n=3, cutoff=0.6)` — stdlib, zero new deps
5. If close matches found, emit warning: `No tasks found for project "Personl". Did you mean: "Personal"?`

**Example implementation sketch:**
```python
# In _ListTasksPipeline, after repo call
if result.total == 0 and query.project:
    all_projects = await self._repo.list_projects(ListProjectsQuery())
    names = [p.name for p in all_projects.items]
    close = difflib.get_close_matches(query.project, names, n=3, cutoff=0.6)
    if close:
        result.warnings.append(
            f'No tasks match project "{query.project}". Did you mean: {", ".join(close)}?'
        )
```

**Covers:** project, folder, tags filters (and any future name-based filters)

**Requirement:** INFRA-07 (Phase 37)
