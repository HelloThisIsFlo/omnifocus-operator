---
created: 2026-03-30T10:39:56.173Z
updated: 2026-03-30T21:45:00.000Z
title: Uniform name-vs-ID resolution at service boundary for all list filters
area: service, contracts
files:
  - src/omnifocus_operator/contracts/use_cases/list/tasks.py
  - src/omnifocus_operator/contracts/use_cases/list/projects.py
  - src/omnifocus_operator/contracts/use_cases/list/tags.py
  - src/omnifocus_operator/contracts/use_cases/list/folders.py
  - src/omnifocus_operator/service/service.py
  - src/omnifocus_operator/repository/query_builder.py
---

## Problem

Inconsistent handling of name-based filters across the list pipeline:

- **project/folder**: Agent passes a string → repo assumes it's a name, does SQL `LIKE` match. No way to filter by ID. If an agent passes a project ID, it silently matches nothing (or accidentally matches a project whose name contains that substring).
- **tags**: Agent passes strings → service resolves names to IDs → repo filters by IDs only. The only filter where the service does resolution.
- **search**: Text search, stays as-is (not an entity reference).

The repo contract is split between "pass human-readable strings" (project/folder) and "pass resolved IDs" (tags). The agent-facing Query gives no indication whether a string is a name or an ID.

## Solution

**Principle**: The service layer resolves ALL entity references to IDs. The RepoQuery is always IDs-only. The repo does pure data retrieval — no name matching, no LIKE, no ambiguity.

**Agent-facing Query** (unchanged): Single field per dimension. Agent passes whatever they have — name or ID.

**Service layer resolution cascade** (for each entity reference filter):

1. **ID match** — string matches an entity ID → resolve to that single ID
2. **Substring match** (case-insensitive) — replicates current LIKE behavior in Python → resolve to one or more IDs
3. **No match** → fuzzy match via `difflib.get_close_matches` → attach "did you mean?" warning (see related todo)

All entities are already in memory (fetched for ID checking). Substring matching and fuzzy matching are trivial in Python with these counts (~300 projects, ~79 folders, ~64 tags).

**RepoQuery fields** — IDs only, uniform across all filters:

| Filter | RepoQuery field | Type |
|--------|----------------|------|
| project | `project_ids` | `list[str]` (one for exact, multiple for substring match) |
| folder | `folder_ids` | `list[str]` (one for exact, multiple for substring match) |
| tags | `tag_ids` | `list[str]` (resolved from names/IDs, case-insensitive) |

Repo does `WHERE x IN (?, ?, ?)` for all of them. Uniform, simple.

## Example flow

```
Agent Query              Service                          RepoQuery
────────────            ──────────────────               ──────────────
project: "Work"     →   not an ID                     →  project_ids: ["p1", "p2", "p3"]
                         substring match: "Work",
                         "Work Projects", "Homework"

project: "pJK.."    →   matches ID                    →  project_ids: ["pJK.."]

project: "Personl"  →   not an ID, no substring match →  (skip / empty)
                         fuzzy: "Did you mean Personal?"
                         → warning attached

tags: ["Errand",    →   resolve each:                 →  tag_ids: ["abc", "xyz"]
       "kFj9xL5"]       "Errand" → name → "abc"
                         "kFj9xL5" → ID → "xyz"

tags: ["Erand"]     →   not an ID, no exact match     →  (skip / empty)
                         fuzzy: "Did you mean Errand?"
                         → warning attached
```

## Scope

- This is the first real behavioral divergence between Query and RepoQuery (Phase 35.1 created the structural split)
- Candidate for Phase 35.2
- Related: "did-you-mean" suggestions todo — fires during step 3 of the resolution cascade above
