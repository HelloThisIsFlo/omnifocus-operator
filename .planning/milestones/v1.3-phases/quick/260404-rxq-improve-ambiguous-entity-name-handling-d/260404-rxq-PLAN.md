---
phase: 260404-rxq
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/omnifocus_operator/agent_messages/errors.py
  - src/omnifocus_operator/agent_messages/warnings.py
  - src/omnifocus_operator/service/resolve.py
  - src/omnifocus_operator/service/service.py
  - tests/test_service_resolve.py
  - tests/test_service.py
  - tests/test_list_pipelines.py
autonomous: true
requirements: [TODO-20, TODO-21]

must_haves:
  truths:
    - "Write-side ambiguous entity error says 'specify by ID' and includes entity type"
    - "Read-side multi-match filter produces a warning with entity names and IDs"
    - "Read-side multi-match still returns results (warning, not error)"
    - "Resolver and pipelines no longer call get_all() -- use targeted list methods"
    - "Existing tests pass unchanged (behavioral equivalence for perf optimization)"
  artifacts:
    - path: "src/omnifocus_operator/agent_messages/errors.py"
      provides: "AMBIGUOUS_ENTITY constant replacing AMBIGUOUS_TAG"
      contains: "AMBIGUOUS_ENTITY"
    - path: "src/omnifocus_operator/agent_messages/warnings.py"
      provides: "FILTER_MULTI_MATCH warning constant"
      contains: "FILTER_MULTI_MATCH"
    - path: "src/omnifocus_operator/service/resolve.py"
      provides: "Generalized _match_by_name method, targeted list calls in resolve_tags"
      contains: "_match_by_name"
    - path: "src/omnifocus_operator/service/service.py"
      provides: "Targeted list calls instead of get_all(), multi-match warning logic"
  key_links:
    - from: "src/omnifocus_operator/service/resolve.py"
      to: "src/omnifocus_operator/agent_messages/errors.py"
      via: "AMBIGUOUS_ENTITY import"
      pattern: "AMBIGUOUS_ENTITY"
    - from: "src/omnifocus_operator/service/service.py"
      to: "src/omnifocus_operator/agent_messages/warnings.py"
      via: "FILTER_MULTI_MATCH import"
      pattern: "FILTER_MULTI_MATCH"
---

<objective>
Improve ambiguous entity name handling across write-side errors and read-side warnings, plus replace get_all() with targeted list calls for performance.

Purpose: Agents currently get an unhelpful ambiguous tag error with no resolution guidance, and read-side filters silently broaden when multiple entities match. This makes the agent smarter about disambiguation and avoids loading thousands of tasks for resolution.

Output: Updated resolve.py, service.py, errors.py, warnings.py with tests.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/quick/260404-rxq-improve-ambiguous-entity-name-handling-d/260404-rxq-CONTEXT.md
@.planning/quick/260404-rxq-improve-ambiguous-entity-name-handling-d/260404-rxq-RESEARCH.md
@src/omnifocus_operator/service/resolve.py
@src/omnifocus_operator/service/service.py
@src/omnifocus_operator/agent_messages/errors.py
@src/omnifocus_operator/agent_messages/warnings.py
@tests/test_service_resolve.py
@tests/test_list_pipelines.py
@tests/test_service.py

<interfaces>
<!-- Key types and contracts the executor needs -->

From src/omnifocus_operator/models/enums.py:
```python
class TagAvailability(StrEnum):
    AVAILABLE = "available"
    BLOCKED = "blocked"
    DROPPED = "dropped"

class FolderAvailability(StrEnum):
    AVAILABLE = "available"
    DROPPED = "dropped"

class Availability(StrEnum):  # Projects
    AVAILABLE = "available"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    DROPPED = "dropped"
```

From src/omnifocus_operator/contracts/use_cases/list/tags.py:
```python
class ListTagsRepoQuery(QueryModel):
    availability: list[TagAvailability] = Field(default_factory=lambda: [TagAvailability.AVAILABLE, TagAvailability.BLOCKED])
    search: str | None = None
    limit: int | None = DEFAULT_LIST_LIMIT
    offset: int | None = None
```

From src/omnifocus_operator/contracts/use_cases/list/folders.py:
```python
class ListFoldersRepoQuery(QueryModel):
    availability: list[FolderAvailability] = Field(default_factory=lambda: [FolderAvailability.AVAILABLE])
    search: str | None = None
    limit: int | None = DEFAULT_LIST_LIMIT
    offset: int | None = None
```

From src/omnifocus_operator/contracts/use_cases/list/projects.py:
```python
class ListProjectsRepoQuery(QueryModel):
    availability: list[Availability] = Field(default_factory=lambda: [...])
    # ... other fields
```

From src/omnifocus_operator/contracts/protocols.py:
```python
class RepositoryProtocol:
    async def list_tags(self, query: ListTagsRepoQuery) -> ListRepoResult[Tag]: ...
    async def list_projects(self, query: ListProjectsRepoQuery) -> ListRepoResult[Project]: ...
    async def list_folders(self, query: ListFoldersRepoQuery) -> ListRepoResult[Folder]: ...
```

From src/omnifocus_operator/service/resolve.py:
```python
@runtime_checkable
class _HasIdAndName(Protocol):
    @property
    def id(self) -> str: ...
    @property
    def name(self) -> str: ...
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Generalize write-side error and replace get_all() in resolver</name>
  <files>
    src/omnifocus_operator/agent_messages/errors.py,
    src/omnifocus_operator/service/resolve.py,
    tests/test_service_resolve.py,
    tests/test_service.py
  </files>
  <behavior>
    - Test: _match_by_name with entity_type="tag" and two matching entities raises ValueError containing "Ambiguous tag" AND "specify by ID instead of name"
    - Test: _match_by_name with entity_type="project" and two matching entities raises ValueError containing "Ambiguous project" AND "specify by ID"
    - Test: resolve_tags still works for single match, ID fallback, not found (existing tests updated to match new message format)
    - Test: test_tag_ambiguous in test_service.py updated to match new message format including "specify by ID"
  </behavior>
  <action>
    1. In errors.py: Replace `AMBIGUOUS_TAG` with `AMBIGUOUS_ENTITY`:
       ```python
       AMBIGUOUS_ENTITY = (
           "Ambiguous {entity_type} '{name}': multiple matches ({ids}). "
           "For ambiguous {entity_type}s, specify by ID instead of name."
       )
       ```
       Remove the old `AMBIGUOUS_TAG` constant.

    2. In resolve.py: Rename `_match_tag` to `_match_by_name(self, name: str, entities: Sequence[_HasIdAndName], entity_type: str) -> str`. Update the error to use `AMBIGUOUS_ENTITY.format(entity_type=entity_type, name=name, ids=ids)`. Update `resolve_tags` to call `self._match_by_name(name, all_tags, "tag")`.

    3. Performance optimization in resolve.py: Replace `get_all()` in `resolve_tags` with a targeted list call. Import `ListTagsRepoQuery` and `TagAvailability`. Call `self._repo.list_tags(ListTagsRepoQuery(availability=list(TagAvailability), limit=None))` to get ALL tags (including dropped). Extract `.items` from the `ListRepoResult`. CRITICAL: pass all availability values -- default query excludes DROPPED tags.

    4. Update test_service_resolve.py: `test_resolve_tags_ambiguous` -- match against "Ambiguous tag" and verify "specify by ID" is in the message. Add a new test `test_match_by_name_generic_entity_type` that creates a resolver and calls `_match_by_name` with entity_type="project" to verify entity_type parameterization works.

    5. Update test_service.py: `test_tag_ambiguous` -- match against "Ambiguous tag" and verify "specify by ID" is in the error message.
  </action>
  <verify>
    <automated>cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && uv run pytest tests/test_service_resolve.py tests/test_service.py -x -q</automated>
  </verify>
  <done>
    - AMBIGUOUS_TAG replaced with AMBIGUOUS_ENTITY in errors.py
    - _match_tag renamed to _match_by_name with entity_type parameter
    - resolve_tags uses list_tags instead of get_all
    - Error message includes "specify by ID instead of name" guidance
    - All existing resolver and service tests pass with updated assertions
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add read-side multi-match warnings and replace get_all() in pipelines</name>
  <files>
    src/omnifocus_operator/agent_messages/warnings.py,
    src/omnifocus_operator/service/service.py,
    tests/test_list_pipelines.py
  </files>
  <behavior>
    - Test: list_tasks with project filter matching 2 projects -> results include tasks from both, warnings contains multi-match message with both project names and IDs
    - Test: list_tasks with tag filter where one tag name matches 2 tags (e.g. "Work" matching "Work" and "Homework") -> warning for that value, results still filter correctly
    - Test: list_projects with folder filter matching 2 folders -> warning with both folder names and IDs
    - Test: list_tasks with project filter matching exactly 1 project -> NO multi-match warning (no regression)
    - Test: Existing no-match and did-you-mean warnings still work
  </behavior>
  <action>
    1. In warnings.py: Add the multi-match warning constant:
       ```python
       FILTER_MULTI_MATCH = (
           "Filter '{value}' matched {count} {entity_type}s: {matches}. "
           "For exact results, filter by ID."
       )
       ```

    2. Performance optimization in service.py `_ListTasksPipeline.execute()`:
       - Remove `self._all_data = await self._repository.get_all()`
       - Replace with two targeted calls using the internal `_InternalRepository` protocol:
         ```python
         tags_result = await self._repository.list_tags(
             ListTagsRepoQuery(availability=list(TagAvailability), limit=None)
         )
         self._tags = tags_result.items
         projects_result = await self._repository.list_projects(
             ListProjectsRepoQuery(availability=list(Availability), limit=None)
         )
         self._projects = projects_result.items
         ```
       - Update all `self._all_data.tags` references to `self._tags` and `self._all_data.projects` to `self._projects`
       - CRITICAL: pass ALL availability values to include dropped entities for proper name resolution

    3. Performance optimization in service.py `_ListProjectsPipeline.execute()`:
       - Remove `self._all_data = await self._repository.get_all()`
       - Replace with:
         ```python
         folders_result = await self._repository.list_folders(
             ListFoldersRepoQuery(availability=list(FolderAvailability), limit=None)
         )
         self._folders = folders_result.items
         ```
       - Update `self._all_data.folders` references to `self._folders`

    4. Add multi-match warning logic to `_resolve_project()`:
       After `resolved = self._resolver.resolve_filter(...)`, if `len(resolved) > 1`:
       ```python
       name_map = {p.id: p.name for p in self._projects}
       match_details = ", ".join(f"{eid} ({name_map.get(eid, '?')})" for eid in resolved)
       self._warnings.append(
           FILTER_MULTI_MATCH.format(
               value=self._query.project, count=len(resolved),
               entity_type="project", matches=match_details
           )
       )
       ```

    5. Add multi-match warning logic to `_resolve_tags()`:
       Refactor to per-value loop instead of using `resolve_filter_list`. For each tag value in `self._query.tags`, call `resolve_filter` individually. If `len(resolved) > 1` for any value, build and append a per-value warning. Collect IDs and unresolved values as before.

    6. Add multi-match warning logic to `_resolve_folder()`: Same pattern as `_resolve_project()`.

    7. In test_list_pipelines.py: Add tests in `TestListTasksResolution`:
       - `test_project_multi_match_warns`: snapshot with two projects whose names contain the filter substring, verify warning includes both names/IDs and results still returned
       - `test_tag_multi_match_warns`: snapshot with tags where one filter value substring-matches multiple tags (e.g. "Work" matching "Work" and "Homework"), verify per-value warning
       - `test_single_match_no_multi_match_warning`: verify existing single-match case produces no warning (no regression)

    8. In `TestListProjectsResolution`:
       - `test_folder_multi_match_warns`: snapshot with two folders matching filter, verify warning

    Import `FILTER_MULTI_MATCH` from warnings.py in test assertions.
  </action>
  <verify>
    <automated>cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && uv run pytest tests/test_list_pipelines.py tests/test_service_resolve.py tests/test_service.py -x -q</automated>
  </verify>
  <done>
    - FILTER_MULTI_MATCH constant added to warnings.py
    - _ListTasksPipeline and _ListProjectsPipeline use targeted list calls instead of get_all()
    - Multi-match warnings emitted for project, tag, and folder filters when len(resolved) > 1
    - Warning includes entity names, IDs, and "filter by ID" guidance
    - Results still returned alongside warnings (warning, not error)
    - Existing no-match and did-you-mean warnings unaffected
    - All pipeline and service tests pass
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

No new trust boundaries introduced. This change modifies agent-facing messages only -- no new input surface, no new data access paths.

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-rxq-01 | I (Information Disclosure) | AMBIGUOUS_ENTITY error message | accept | Entity IDs and names are already agent-visible in all tool responses -- no new information exposed |
| T-rxq-02 | I (Information Disclosure) | FILTER_MULTI_MATCH warning | accept | Same as above -- matched IDs/names are from entities the agent can already see via list tools |
</threat_model>

<verification>
```bash
# Full test suite
cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && uv run pytest -x -q

# Verify AMBIGUOUS_TAG no longer referenced anywhere in production code
grep -r "AMBIGUOUS_TAG" src/

# Verify get_all() no longer called in resolve.py or pipeline sections of service.py
grep -n "get_all()" src/omnifocus_operator/service/resolve.py
grep -n "get_all()" src/omnifocus_operator/service/service.py
# Should only remain in get_all_data delegation, NOT in pipelines or resolver

# Verify output schema still valid
uv run pytest tests/test_output_schema.py -x -q
```
</verification>

<success_criteria>
- `uv run pytest -x -q` passes with 0 failures
- `AMBIGUOUS_TAG` no longer exists in production code (replaced by `AMBIGUOUS_ENTITY`)
- `get_all()` no longer called in resolve.py or pipeline code in service.py
- New tests cover multi-match warnings for project, tag, and folder filters
- Error messages include actionable "specify by ID" guidance
</success_criteria>

<output>
After completion, create `.planning/quick/260404-rxq-improve-ambiguous-entity-name-handling-d/260404-rxq-SUMMARY.md`
</output>
