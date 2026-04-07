---
created: "2026-04-07T00:16:53.000Z"
title: Migrate list query filters to Patch semantics — eliminate null from agent-facing schemas
area: contracts
files:
  - src/omnifocus_operator/contracts/use_cases/list/tasks.py
  - src/omnifocus_operator/contracts/use_cases/list/projects.py
  - src/omnifocus_operator/contracts/use_cases/list/tags.py
  - src/omnifocus_operator/contracts/use_cases/list/folders.py
  - src/omnifocus_operator/contracts/use_cases/list/perspectives.py
  - src/omnifocus_operator/contracts/use_cases/list/_validators.py
---

## Problem

All agent-facing list query models use `T | None = None` for optional filter fields. This means the JSON Schema includes `null` in the type union, which teaches agents that `null` is a valid input. But for filter fields, `null` and "omitted" mean the same thing ("no filter") — there's no semantic distinction. This creates ambiguity: agents may think `null` carries meaning (like it does for `limit`, where `null` = "no limit").

The write side already solved this with `Patch[T] = UNSET` (Phase 41): the schema shows only the base type, omitting = UNSET, null = validation error. The read side should follow the same pattern.

## Solution

### Design principle

**Null is only allowed when it means something different from omitting the field.** For filters, null = omit = "no filter" (redundant, eliminate null). For `limit`, null = "no limit" while omit = "use default 50" (genuinely different, keep null).

### Migration rule

| Current pattern | New pattern | Reason |
|----------------|-------------|--------|
| `T \| None = None` (filter) | `Patch[T] = UNSET` | null = same as omit, eliminate |
| `list[T] \| None = None` (filter) | `Patch[list[T]] = UNSET` + reject `[]` | Same, plus empty list = always a mistake |
| `list[T] = [real_defaults]` (availability) | **KEEP type**, add empty-list validator | Real default, null already rejected by type |
| `int \| None = DEFAULT_LIST_LIMIT` (limit) | **KEEP** | null = "no limit" (distinct from omit) |
| `int \| None = None` (offset) | `int = 0` | Zero = "start from beginning" |

### Per-model field inventory

**ListTasksQuery** (tasks.py):
- `in_inbox: bool | None = None` -> `Patch[bool] = UNSET`
- `flagged: bool | None = None` -> `Patch[bool] = UNSET`
- `project: str | None = None` -> `Patch[str] = UNSET`
- `tags: list[str] | None = None` -> `Patch[list[str]] = UNSET` + reject `[]`
- `estimated_minutes_max: int | None = None` -> `Patch[int] = UNSET`
- `search: str | None = None` -> `Patch[str] = UNSET`
- `availability: list[Availability] = [AVAILABLE, BLOCKED]` -> KEEP, add empty-list validator
- `limit: int | None = DEFAULT_LIST_LIMIT` -> KEEP (null = no limit)
- `offset: int | None = None` -> `int = 0`

**ListProjectsQuery** (projects.py):
- `folder: str | None = None` -> `Patch[str] = UNSET`
- `review_due_within: ReviewDueFilter | None = None` -> `Patch[ReviewDueFilter] = UNSET`
- `flagged: bool | None = None` -> `Patch[bool] = UNSET`
- `search: str | None = None` -> `Patch[str] = UNSET`
- `availability: list[Availability] = [AVAILABLE, BLOCKED]` -> KEEP, add empty-list validator
- `limit: int | None = DEFAULT_LIST_LIMIT` -> KEEP
- `offset: int | None = None` -> `int = 0`

**ListTagsQuery** (tags.py):
- `search: str | None = None` -> `Patch[str] = UNSET`
- `availability: list[TagAvailability] = [AVAILABLE, BLOCKED]` -> KEEP, add empty-list validator
- `limit: int | None = DEFAULT_LIST_LIMIT` -> KEEP
- `offset: int | None = None` -> `int = 0`

**ListFoldersQuery** (folders.py):
- `search: str | None = None` -> `Patch[str] = UNSET`
- `availability: list[FolderAvailability] = [AVAILABLE]` -> KEEP, add empty-list validator
- `limit: int | None = DEFAULT_LIST_LIMIT` -> KEEP
- `offset: int | None = None` -> `int = 0`

**ListPerspectivesQuery** (perspectives.py):
- `search: str | None = None` -> `Patch[str] = UNSET`
- `limit: int | None = DEFAULT_LIST_LIMIT` -> KEEP
- `offset: int | None = None` -> `int = 0`

### Additional changes

- **Empty-list rejection**: Add `validate_non_empty_list` to `_validators.py`. Apply to `tags` (ListTasksQuery) and `availability` (all 4 models that have it). Error: educational message like "tags cannot be empty. Provide at least one tag or omit the field."
- **Offset validator**: `validate_offset_requires_limit` changes from `if offset is not None` to `if offset > 0` check.
- **`review_due_within` field_validator**: Update to pass through UNSET instead of None (`if v is UNSET: return v`).
- **Service pipelines**: Change `if field is None: skip` to `if field is UNSET: skip`. When building repo queries (which stay `T | None`), translate UNSET -> None.
- **Repo-level queries**: UNTOUCHED. They are internal contracts, not agent-facing.

### Summary counts
- 13 fields migrated to Patch across 5 models
- 5 empty-list validators added (1 tags + 4 availability)
- 5 offset fields changed to `int = 0`
- 5 limit fields kept as `int | None` (null = no limit)
- 0 repo queries changed
