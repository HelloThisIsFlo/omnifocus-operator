---
created: 2026-03-30T18:11:18.146Z
title: Introduce read-side contract boundary split (RepoQuery / RepoResult)
area: contracts
files:
  - docs/model-taxonomy.md
  - docs/architecture.md
  - src/omnifocus_operator/contracts/use_cases/list_entities.py
---

## Problem

The read-side currently has no service boundary split — the same `ListTasksQuery` flows from server → service → repo unchanged. But the service needs to:
1. Detect whether filter values are names or IDs and route to separate repo query fields (`tags` vs `tag_ids`, `project` vs `project_id`, `folder` vs `folder_id`)
2. Add warnings/suggestions to results ("did you mean?" for zero-result name filters)

Without the split, the repo receives ambiguous instructions and there's no place for service-level result enrichment. The write side already has this split (`Command → RepoPayload`, `Result ← RepoResult`); the read side should mirror it per the service boundary principle documented in `docs/model-taxonomy.md`.

## Solution

**Structural refactor (no behavioral changes):**

- Introduce `List<Noun>RepoQuery` for tasks, projects, tags, folders — repo-facing queries with separate name/ID fields. Every entity gets a RepoQuery even if identical to Query today (Structure Over Discipline — divergence becomes "add a field," not a design decision). Perspectives: no query (D-09).
- Introduce `ListRepoResult[T]` alongside `ListResult[T]` — repo result has no warnings, agent result does (mirrors `AddTaskRepoResult` vs `AddTaskResult`). Both inherit `OmniFocusBaseModel` (outbound, no strict validation).
- Reorganize `contracts/use_cases/` into per-use-case packages:
  ```
  contracts/use_cases/
      list/
          __init__.py
          common.py          # ListResult[T], ListRepoResult[T]
          tasks.py           # ListTasksQuery, ListTasksRepoQuery
          projects.py        # ListProjectsQuery, ListProjectsRepoQuery
          tags.py            # ListTagsQuery, ListTagsRepoQuery
          folders.py         # ListFoldersQuery, ListFoldersRepoQuery
          perspectives.py    # (no query)
      add/
          __init__.py
          tasks.py           # AddTaskCommand, AddTaskRepoPayload, AddTaskResult, AddTaskRepoResult
      edit/
          __init__.py
          tasks.py           # EditTaskCommand, EditTaskActions, EditTaskRepoPayload, EditTaskRepoResult, EditTaskResult
  ```
- Update all imports across the codebase
- `list_entities.py` is removed (replaced by the package structure)
- `add/` and `edit/` gain `common.py` only when shared types emerge naturally

**Already done:** `docs/model-taxonomy.md` extracted and updated with the new taxonomy (service boundary principle, RepoQuery/RepoResult, `<noun>Filter` pattern, Scenarios D/E/F). `docs/architecture.md` package structure updated.

**Related:** Pairs with the existing "Migrate tag filter to accept names at repository level" todo — that becomes Phase 35.2 (behavioral change using the new RepoQuery contract). This todo is Phase 35.1 (structural refactor enabling it).
