---
created: 2026-03-30T10:39:56.173Z
title: Migrate tag filter to accept names at repository level
area: repository
files:
  - src/omnifocus_operator/contracts/use_cases/list_entities.py:40
  - src/omnifocus_operator/repository/query_builder.py
  - src/omnifocus_operator/repository/hybrid.py
---

## Problem

Contract inconsistency in `ListTasksQuery.tags`: project, folder, and search filters all do case-insensitive name matching in SQL at the repository level, but tags expects the caller (service layer) to resolve names to IDs first. This makes the codebase harder to reason about — the repo contract is split between "pass human-readable strings" and "pass resolved IDs" depending on the filter.

The contract comment on line 40 says `# tag names (OR logic), service resolves to IDs` — but this resolution is a database concern (lookup), not domain logic.

## Solution

- Change `build_list_tasks_sql` to resolve tag names to IDs via SQL subquery (same pattern as project/folder name matching)
- Tags filter should accept either tag name or tag ID at the repo level
- Update tests to use realistic tag names (not ID-looking strings like "tag-001")
- Remove tag name→ID resolution responsibility from service layer contract
- Consider doing this as an urgent phase before the BridgeRepository fallback phase (36), so the bridge repo gets the correct contract from the start
