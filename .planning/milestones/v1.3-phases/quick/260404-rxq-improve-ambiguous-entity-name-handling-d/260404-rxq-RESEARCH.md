# Quick Task 260404-rxq: Improve Ambiguous Entity Name Handling — Research

**Researched:** 2026-04-04
**Domain:** Service-layer name resolution (write-side errors + read-side warnings) and performance optimization
**Confidence:** HIGH

## Summary

All code paths are well-understood. The task touches 4 files for production code and 2-3 test files. The architecture already has warning infrastructure (`_ReadPipeline._warnings`, `ListResult.warnings`) and error message centralization (`agent_messages/errors.py`). The main risk is the performance optimization: `list_tags`/`list_projects`/`list_folders` default to filtered availability, while `get_all()` returns all entities. The resolver needs ALL entities (including dropped) to properly match names/IDs.

**Primary recommendation:** Start with the perf optimization (it changes how entity data is fetched, which both error and warning changes depend on), then write-side error generalization, then read-side multi-match warnings.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Write-side: generic `AMBIGUOUS_ENTITY` error with "specify by ID" guidance, generalize `_match_tag` to `_match_by_name(name, entities, entity_type)`
- Read-side: warn on any multi-match (`len(resolved) > 1`) from `resolve_filter`, covering project/tags/folder filters only (not search)
- Performance: replace `get_all()` with targeted `list_tags`/`list_projects`/`list_folders` calls (limit=None) in both resolver and read pipelines
- Scope exclusions: no warnings on get_task/get_project/get_tag, no output scanning on list_tags/list_projects, no warnings on search params

### Claude's Discretion
- Implementation ordering within the task
- Test structure and naming

### Deferred Ideas (OUT OF SCOPE)
- None listed
</user_constraints>

## Architecture: Current State

### Write-side tag resolution (`resolve.py`)
- `resolve_tags(tag_names)` calls `get_all()`, iterates names through `_match_tag`
- `_match_tag(name, tags)` does: exact case-insensitive name match → ambiguous error (>1 match) → ID fallback → not found
- Error constant: `AMBIGUOUS_TAG = "Ambiguous tag '{name}': multiple matches ({ids})"` in `errors.py` line 24
- `_match_tag` is tag-specific today -- needs generalization to `_match_by_name(name, entities, entity_type)`

### Read-side filter resolution (`resolve.py`)
- `resolve_filter(value, entities)` returns `list[str]` (IDs): ID match → substring match → empty
- `resolve_filter_list(values, entities)` returns flat deduped `list[str]`
- `find_unresolved(values, entities)` returns values that matched nothing
- **No multi-match awareness today** -- returns all matches silently, never warns

### Read-side pipelines (`service.py`)
- `_ReadPipeline` base class provides `_warnings: list[str]` and `_result_from_repo()` which injects warnings into `ListResult`
- `_ListTasksPipeline.execute()` calls `self._repository.get_all()`, then uses `self._all_data.projects` and `self._all_data.tags` for resolution
- `_ListProjectsPipeline.execute()` calls `self._repository.get_all()`, then uses `self._all_data.folders` for resolution
- Both pipelines already generate no-match/did-you-mean warnings via `_build_warning()`

### Warning flow
- `ListResult` has `warnings: list[str] | None = None` [VERIFIED: codebase]
- ListResult is returned directly from MCP tool functions -- warnings flow automatically via Pydantic serialization [VERIFIED: server.py]

## Common Pitfalls

### Pitfall 1: Availability filtering on list calls
**What goes wrong:** `list_tags(limit=None)` with default `ListTagsRepoQuery` excludes `DROPPED` tags. `list_folders(limit=None)` excludes `DROPPED` folders. The resolver needs ALL entities to match names, including dropped ones.
**Why it happens:** Default availability filters:
- `ListTagsRepoQuery.availability` = `[AVAILABLE, BLOCKED]` (missing `DROPPED`) [VERIFIED: contracts/use_cases/list/tags.py]
- `ListFoldersRepoQuery.availability` = `[AVAILABLE]` (missing `DROPPED`) [VERIFIED: contracts/use_cases/list/folders.py]
- `get_all()` returns everything regardless of availability [VERIFIED: hybrid.py, bridge_only.py]
**How to avoid:** When calling list methods for resolution purposes, explicitly pass ALL availability values:
```python
ListTagsRepoQuery(
    availability=[TagAvailability.AVAILABLE, TagAvailability.BLOCKED, TagAvailability.DROPPED],
    limit=None,
)
```
**Warning signs:** Tests pass with InMemoryBridge (no availability filtering) but fail with real data when dropped entities exist.

### Pitfall 2: resolve_filter returns IDs only, warning needs names
**What goes wrong:** The multi-match warning needs to show entity names alongside IDs (e.g., "Filter 'Work' matched 2 tags: aaa (Work), bbb (Homework)"). `resolve_filter` returns `list[str]` (IDs only).
**How to avoid:** The entities list is already available in the pipeline context (`self._all_data.tags`, etc.). Build a name lookup from the entities list and map IDs back to names for the warning message. Or pass entities into a helper that resolves and builds warnings in one step.

### Pitfall 3: resolve_filter_list aggregates across values
**What goes wrong:** For tags, `resolve_filter_list` aggregates matches across multiple tag values. A multi-match warning should be per-value, not per-aggregate. E.g., `tags=["Work", "Home"]` -- "Work" matching 2 entities is a multi-match, but the combined result having 3 IDs is expected.
**How to avoid:** The warning logic needs to call `resolve_filter` per-value (which the pipeline already does indirectly via `resolve_filter_list`). Add warning check inside the per-value loop, not on the aggregate result.

### Pitfall 4: _ListTasksPipeline._resolve_tags uses resolve_filter_list
**What goes wrong:** `_resolve_tags` in `_ListTasksPipeline` calls `resolve_filter_list` which internally loops over values. To add per-value multi-match warnings, the pipeline needs to call `resolve_filter` per-value itself (similar to how `find_unresolved` works).
**How to avoid:** Refactor `_resolve_tags` to loop over values, calling `resolve_filter` on each, checking `len(resolved) > 1` per value, then collecting IDs and warnings.

## Code Patterns to Follow

### Existing warning pattern in `_ReadPipeline`
```python
# From _ListTasksPipeline._resolve_project (service.py line 298-313)
def _resolve_project(self) -> None:
    self._project_ids: list[str] | None = None
    if self._query.project is None:
        return
    resolved = self._resolver.resolve_filter(self._query.project, self._all_data.projects)
    if resolved:
        self._project_ids = resolved
    else:
        self._warnings.append(
            self._build_warning("project", self._query.project,
                [p.name for p in self._all_data.projects])
        )
```
The new multi-match warning should follow the same pattern: append to `self._warnings` after checking `len(resolved) > 1`.

### Existing error pattern for ambiguity (`resolve.py`)
```python
# From _match_tag (resolve.py line 110-125)
def _match_tag(self, name: str, tags: list[Tag]) -> str:
    matches = [t for t in tags if t.name.lower() == name.lower()]
    if len(matches) == 1:
        return matches[0].id
    if len(matches) > 1:
        ids = ", ".join(m.id for m in matches)
        msg = AMBIGUOUS_TAG.format(name=name, ids=ids)
        raise ValueError(msg)
    # ... ID fallback ...
```
Generalizing to `_match_by_name(name, entities, entity_type)` requires: `entities` typed as `Sequence[_HasIdAndName]`, parameterize the error message with `entity_type`.

### Warning message template (from CONTEXT.md specifics)
```python
# New constant in warnings.py:
FILTER_MULTI_MATCH = (
    "Filter '{value}' matched {count} {entity_type}s: {matches}. "
    "For exact results, filter by ID."
)
```
Where `matches` looks like: `aaa (Work), bbb (Homework)`.

### Entity name lookup for warnings
```python
# Build id→name map from entities list
name_map = {e.id: e.name for e in entities}
match_details = ", ".join(f"{eid} ({name_map[eid]})" for eid in resolved)
```

## Implementation Sequence

1. **Performance optimization** — Replace `get_all()` calls with targeted list calls
   - `_ListTasksPipeline.execute()`: replace `self._all_data = await self._repository.get_all()` with two targeted calls for tags and projects (all availabilities, limit=None)
   - `_ListProjectsPipeline.execute()`: replace `self._all_data = await self._repository.get_all()` with one call for folders (all availabilities, limit=None)
   - `resolve_tags()` in resolve.py: replace `get_all()` with a targeted list_tags call via the repository
   - **Key decision:** The pipelines currently store `self._all_data` (AllEntities). After the change, they'll store individual entity lists (e.g., `self._tags`, `self._projects`). Update all downstream references.

2. **Write-side error generalization** — `_match_tag` → `_match_by_name`
   - Add `AMBIGUOUS_ENTITY` to `errors.py`, remove/deprecate `AMBIGUOUS_TAG`
   - Rename `_match_tag` → `_match_by_name(name, entities, entity_type)` on Resolver
   - Update `resolve_tags` to call `_match_by_name(name, all_tags, "tag")`

3. **Read-side multi-match warnings** — Add warnings when `len(resolved) > 1`
   - Add `FILTER_MULTI_MATCH` to `warnings.py`
   - In `_ListTasksPipeline._resolve_project()`: after `resolve_filter`, if `len(resolved) > 1`, build and append warning
   - In `_ListTasksPipeline._resolve_tags()`: refactor to per-value loop, check each for multi-match
   - In `_ListProjectsPipeline._resolve_folder()`: same pattern as project

## Test Patterns

### Existing test infrastructure [VERIFIED: test_service_resolve.py, test_list_pipelines.py]
- `@pytest.mark.snapshot(tags=[...], projects=[...], ...)` fixtures for pipeline tests
- `InMemoryBridge` + `BridgeOnlyRepository` for resolver unit tests
- `make_tag_dict`, `make_project_dict`, `make_folder_dict` helpers in conftest

### Tests to add
- **Write-side:** Test `_match_by_name` with entity_type="tag" produces `AMBIGUOUS_ENTITY` error (update existing `test_resolve_tags_ambiguous` and `test_tag_ambiguous`)
- **Read-side multi-match:**
  - `_ListTasksPipeline`: project filter matching 2 projects → warning with names/IDs, results still include tasks from both
  - `_ListTasksPipeline`: tag filter where one tag name matches 2 tags → warning per-value, results still filter correctly
  - `_ListProjectsPipeline`: folder filter matching 2 folders → warning with names/IDs
- **Performance:** Tests should pass unchanged (behavioral equivalence) -- the optimization is internal

### Key: tests use BridgeOnlyRepository, not HybridRepository
The resolver tests and pipeline tests all use `BridgeOnlyRepository` + `InMemoryBridge`. The `list_tags`/`list_projects`/`list_folders` methods on `BridgeOnlyRepository` call `get_all()` internally anyway (fetch-all + Python filter). So the behavioral change is transparent -- tests don't need to change for the perf optimization, only for the new warning/error behavior. [VERIFIED: bridge_only.py lines 237-259]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The pipeline refactor from `self._all_data` to individual entity lists won't break any downstream references beyond the ones identified | Implementation Sequence | Medium -- could miss a reference, but grep will catch it |

## Open Questions

1. **Should `_match_by_name` live on Resolver or be a standalone function?**
   - Currently `_match_tag` is a method on Resolver (accesses no instance state beyond parameters)
   - Could be a module-level function since it's pure logic
   - Recommendation: keep as Resolver method for consistency -- it's part of the resolution responsibility

2. **How to handle the entity list in `resolve_tags` after perf optimization?**
   - Currently: `all_data = await self._repo.get_all()` → `all_data.tags`
   - After: needs `await self._repo.list_tags(ListTagsRepoQuery(availability=[ALL], limit=None))`
   - Resolver currently doesn't import ListTagsRepoQuery -- new dependency. Alternative: add a convenience method to Repository protocol like `get_all_tags()`. Recommendation: just import the query model directly, it's a clean dependency.

## Sources

### Primary (HIGH confidence)
- `src/omnifocus_operator/service/resolve.py` — full Resolver implementation
- `src/omnifocus_operator/service/service.py` — pipeline implementation, warning accumulation
- `src/omnifocus_operator/agent_messages/errors.py` — AMBIGUOUS_TAG constant
- `src/omnifocus_operator/agent_messages/warnings.py` — existing warning patterns
- `src/omnifocus_operator/contracts/use_cases/list/tags.py` — ListTagsRepoQuery defaults
- `src/omnifocus_operator/contracts/use_cases/list/folders.py` — ListFoldersRepoQuery defaults
- `src/omnifocus_operator/repository/hybrid/hybrid.py` — list method implementations
- `src/omnifocus_operator/repository/bridge_only/bridge_only.py` — fallback list implementations
- `tests/test_service_resolve.py` — resolver test patterns
- `tests/test_list_pipelines.py` — pipeline test patterns

## Metadata

**Confidence breakdown:**
- Architecture understanding: HIGH — all code paths read and verified
- Pitfall identification: HIGH — availability filter gap is concrete and verified
- Implementation approach: HIGH — follows existing patterns exactly
**Research date:** 2026-04-04
**Valid until:** 2026-05-04
