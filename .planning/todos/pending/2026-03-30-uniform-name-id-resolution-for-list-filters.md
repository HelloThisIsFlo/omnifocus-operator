---
created: 2026-03-30T10:39:56.173Z
updated: 2026-03-30T21:30:00.000Z
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

**Principle**: The service layer determines whether the agent passed a name or an ID. The RepoQuery is always explicit about which one it received.

**Agent-facing Query** (unchanged): Single field per dimension. Agent passes whatever they have — name or ID.

**Service layer**: For each name-based filter, fetches the entity list (cheap — SQLite cached), checks if the string matches any entity's ID.
- Match → it's an ID → route to the ID field on RepoQuery
- No match → it's a name → route to the name field on RepoQuery

**RepoQuery fields** — explicit, mutually exclusive:

| Filter | RepoQuery fields | Repo behavior |
|--------|-----------------|---------------|
| project | `project_name` / `project_id` (exclusive) | name → LIKE match, ID → exact match |
| folder | `folder_name` / `folder_id` (exclusive) | name → LIKE match, ID → exact match |
| tags | `tag_ids` only | always exact ID match |

**Why tags are ID-only**: Project/folder name matching is a query semantic (partial LIKE match — "Work" matches "Work Projects", "Homework"). Tag name matching is just entity resolution (find the tag named exactly "Errand", get its ID). The repo doesn't need tag name matching — the service resolves all tag references (names or IDs, case-insensitive) down to IDs before the repo sees them. Mixing names and IDs in the agent's tag list works naturally — the service resolves each entry individually.

**Validation**: Pydantic model validator on RepoQuery enforces mutual exclusivity for project and folder fields (exactly one of name/ID, not both).

## Example flow

```
Agent Query              Service                    RepoQuery
────────────            ─────────────              ──────────────────────
project: "Work"     →   not an ID → name        →  project_name: "Work"
                                                    project_id: None

project: "pJK.."    →   matches ID → ID         →  project_name: None
                                                    project_id: "pJK.."

tags: ["Errand",    →   resolve each:            →  tag_ids: ["abc", "xyz"]
       "kFj9xL5"]       "Errand" → name → "abc"
                         "kFj9xL5" → ID → "xyz"
```

## Scope

- This is the first real behavioral divergence between Query and RepoQuery (Phase 35.1 created the structural split)
- Candidate for Phase 35.2
- Related: "did-you-mean" suggestions todo depends on this (service already has entity lists from resolution)
