# Phase 43: Filters & Project Tools - Research

**Researched:** 2026-04-07
**Domain:** Service-layer filter resolution, contradictory filter detection, project tool guards, tool descriptions
**Confidence:** HIGH

## Summary

Phase 43 is a service-layer-only phase. All changes live in `resolve.py`, `service.py`, `errors.py`, `descriptions.py`, and `warnings.py`. No model changes, no repo changes, no new tools. The CONTEXT.md provides locked implementation code for every requirement -- this is a "wire it up and test thoroughly" phase.

The core addition is `resolve_inbox()` on the Resolver, which normalizes `project="$inbox"` into `in_inbox=True` before the existing `_resolve_project` step. Contradictory filter detection (inbox + project, `$inbox` + `inInbox: false`) raises errors. The `get_project("$inbox")` guard and `list_projects` search warning are straightforward additions.

**Primary recommendation:** Implement in four plans: (1) `resolve_inbox` + pipeline integration, (2) `get_project` guard, (3) `list_projects` search warning, (4) description updates. Each plan is independently testable.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01 to D-05:** `resolve_inbox` method on Resolver with exact signature and implementation (see CONTEXT.md for locked code)
- **D-06 to D-10:** All contradictory filter combos are errors (not warnings). FILT-05 changed from spec's "warning" to "error" for symmetry
- **D-11:** `project: "inbox"` (no `$`) flows through normal `resolve_filter` -- no special handling
- **D-12 to D-14:** `get_project("$inbox")` guard in `lookup_project` with locked error template
- **D-15:** No code needed for PROJ-02 -- inbox is virtual, never in SQLite or bridge
- **D-16 to D-19:** `list_projects` search warning in `_ListProjectsPipeline` with locked warning template
- **D-21 to D-23:** Filter descriptions intentionally omit `$inbox`. Only `GET_PROJECT_TOOL_DOC` gets updated (DESC-04)
- **D-24:** NRES-07 already satisfied by v1.3's `resolve_filter`

### Locked Error/Warning Templates
All templates provided in CONTEXT.md: `CONTRADICTORY_INBOX_FALSE`, `CONTRADICTORY_INBOX_PROJECT`, `GET_PROJECT_INBOX_ERROR`, `LIST_PROJECTS_INBOX_WARNING`

### Claude's Discretion
- Placement of `list_projects` search warning check within `_ListProjectsPipeline`
- Internal naming of pipeline fields (`self._in_inbox`, `self._project_to_resolve`, etc.)

### Deferred Ideas (OUT OF SCOPE)
- Patch semantics for list query fields (captured as todo)
- NRES-07 requirement status update

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FILT-01 | `list_tasks(project="$inbox")` returns same as `inInbox: true` | `resolve_inbox` normalizes `$inbox` to `(True, None)` before `_resolve_project` |
| FILT-02 | `list_tasks(project="inbox")` does NOT match system inbox | No special handling -- `resolve_filter` only matches real project names |
| FILT-03 | `project: "$inbox"` + `inInbox: false` -> error | `resolve_inbox` raises `CONTRADICTORY_INBOX_FALSE` |
| FILT-04 | `project: "$inbox"` + `inInbox: true` -> accepted silently | `resolve_inbox` returns `(True, None)` -- redundant but harmless |
| FILT-05 | `inInbox: true` + real project -> error (changed from warning) | `resolve_inbox` raises `CONTRADICTORY_INBOX_PROJECT` |
| PROJ-01 | `get_project("$inbox")` -> descriptive error | Guard in `lookup_project` with `GET_PROJECT_INBOX_ERROR` |
| PROJ-02 | `list_projects` never includes inbox | No code needed -- inbox is virtual |
| PROJ-03 | `list_projects` name filter matching "Inbox" -> warning | Search warning in `_ListProjectsPipeline` with `LIST_PROJECTS_INBOX_WARNING` |
| NRES-07 | List filter fields accept entity names | Already done in v1.3 via `resolve_filter` |
| DESC-03 | Descriptions document `$inbox` usage in relevant fields | Intentionally omitted per D-21 -- `$inbox` is intuitive compatibility, not documented path |
| DESC-04 | `get_project` description mentions `$inbox` error behavior | Update `GET_PROJECT_TOOL_DOC` |

</phase_requirements>

## Architecture Patterns

### Integration Points (all verified from codebase)

**Resolver (`service/resolve.py`):**
- New `resolve_inbox()` method -- called by `_ListTasksPipeline` before `_resolve_project`
- Guard in `lookup_project()` -- checks `$` prefix before repo call
- Uses existing `_resolve_system_location()` for `$`-prefix validation
- Uses `SYSTEM_LOCATION_PREFIX` and `SYSTEM_LOCATIONS` from `config.py` [VERIFIED: codebase grep]

**Pipeline (`service/service.py`):**
- `_ListTasksPipeline.execute()` line 292: insert `resolve_inbox` call before `_resolve_project` (line 292-295)
- `_ListTasksPipeline._build_repo_query()` line 330-340: use resolved `in_inbox` instead of `self._query.in_inbox`
- `_ListTasksPipeline._resolve_project()` line 297-308: use resolved project instead of `self._query.project`
- `_ListProjectsPipeline`: add search warning check after `_delegate()` [VERIFIED: codebase read]

**Error/Warning templates (`agent_messages/`):**
- New constants in `errors.py`: `CONTRADICTORY_INBOX_FALSE`, `CONTRADICTORY_INBOX_PROJECT`, `GET_PROJECT_INBOX_ERROR`
- New constant in `warnings.py`: `LIST_PROJECTS_INBOX_WARNING`
- All templates locked in CONTEXT.md [VERIFIED: CONTEXT.md]

### Pipeline Flow After Changes

```
_ListTasksPipeline.execute():
  1. Fetch tags + projects (existing)
  2. resolve_inbox(query.in_inbox, query.project) -> (effective_in_inbox, remaining_project)  [NEW]
  3. _resolve_project() using remaining_project  [MODIFIED]
  4. _resolve_tags() (existing)
  5. _build_repo_query() using effective_in_inbox  [MODIFIED]
  6. _delegate() (existing)
```

### Pipeline Modification Pattern

The `_ListTasksPipeline` currently stores query fields directly. After `resolve_inbox`:
- `self._in_inbox` replaces `self._query.in_inbox` in `_build_repo_query`
- `self._project_to_resolve` replaces `self._query.project` in `_resolve_project`
- Naming follows existing pipeline conventions (mutable state on `self`) [VERIFIED: codebase pattern]

### Anti-Patterns to Avoid
- **Pushing `$inbox` to repo layer:** Normalization is entirely service-layer. `ListTasksRepoQuery` never sees `$inbox` as a string -- it only sees `in_inbox: True` [VERIFIED: D-05]
- **Special-casing in resolve_filter:** `resolve_filter` is read-side name matching against real entities. `$inbox` is handled before it, in `resolve_inbox` [VERIFIED: D-04]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| `$`-prefix validation | Custom prefix parser | `_resolve_system_location()` | Already handles unknown locations with educational error |
| Substring matching for search warning | Custom string comparison | Same pattern as `resolve_filter`: `value.lower() in name.lower()` | Consistency with existing codebase |

## Common Pitfalls

### Pitfall 1: resolve_inbox Must Run Before _resolve_project
**What goes wrong:** If `_resolve_project` runs first with `$inbox`, it tries to substring-match against real projects and either finds nothing (empty filter) or matches a project literally named "inbox"
**How to avoid:** Insert `resolve_inbox` call in `execute()` before the existing `_resolve_project` call. Use returned values for both `in_inbox` and the project filter
**Warning signs:** Tests pass for basic cases but `$inbox` filter returns wrong tasks

### Pitfall 2: _resolve_project Must Use Resolved Project, Not Query
**What goes wrong:** If `_resolve_project` still reads `self._query.project`, `resolve_inbox`'s normalization is ignored
**How to avoid:** Store `resolve_inbox` output in `self._project_to_resolve` and `self._in_inbox`. Modify `_resolve_project` to use `self._project_to_resolve`. Modify `_build_repo_query` to use `self._in_inbox`

### Pitfall 3: list_projects Search vs Folder
**What goes wrong:** Warning triggers on `folder` filter instead of `search` filter
**How to avoid:** D-17 is explicit: trigger on `search` field only. `search` is the free-text name/notes field; `folder` is the containing-folder filter. Check `self._query.search`, not `self._query.folder`

### Pitfall 4: PROJ-02 Testing Trap
**What goes wrong:** Writing a test that tries to add inbox to `list_projects` results -- inbox is virtual and never present
**How to avoid:** PROJ-02 needs no code. If a test is desired, it's a "confirm existing behavior" test -- just verify `list_projects` results contain no `$inbox` entries. The bridge never produces one

### Pitfall 5: Error Message Anti-Regression
**What goes wrong:** Error messages hardcode "inbox" or "$inbox" instead of referencing `SYSTEM_LOCATIONS` constant
**How to avoid:** D-10 requires tests verify error messages reference the proper system location name. Templates use literal strings (locked) but tests should assert the message content matches expected patterns

## Code Examples

### resolve_inbox Integration in Pipeline

```python
# In _ListTasksPipeline.execute(), after fetching tags/projects, before _resolve_project:
# Source: CONTEXT.md locked implementation

self._in_inbox, self._project_to_resolve = self._resolver.resolve_inbox(
    self._query.in_inbox, self._query.project
)
```

### Modified _resolve_project

```python
# Source: existing pattern in service.py, modified per CONTEXT.md

def _resolve_project(self) -> None:
    self._project_ids: list[str] | None = None
    if self._project_to_resolve is None:  # was: self._query.project
        return
    resolved = self._resolver.resolve_filter(self._project_to_resolve, self._projects)
    # ... rest unchanged, using self._project_to_resolve for warnings
```

### Modified _build_repo_query

```python
# Source: existing pattern in service.py, modified per CONTEXT.md

def _build_repo_query(self) -> None:
    self._repo_query = ListTasksRepoQuery(
        in_inbox=self._in_inbox,  # was: self._query.in_inbox
        # ... rest unchanged
    )
```

### list_projects Search Warning

```python
# Source: CONTEXT.md D-16 to D-19
# In _ListProjectsPipeline, after _delegate()

from omnifocus_operator.config import SYSTEM_LOCATIONS
from omnifocus_operator.agent_messages.warnings import LIST_PROJECTS_INBOX_WARNING

# After results are built:
if (self._query.search is not None
    and self._query.search.lower() in SYSTEM_LOCATIONS["inbox"].name.lower()):
    self._warnings.append(LIST_PROJECTS_INBOX_WARNING)
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pyproject.toml` |
| Quick run command | `uv run pytest tests/test_list_pipelines.py tests/test_service_resolve.py -x -q` |
| Full suite command | `uv run pytest -x -q` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FILT-01 | `project="$inbox"` returns same as `inInbox: true` | unit (Resolver) + integration (pipeline) | `uv run pytest tests/test_service_resolve.py -x -q -k resolve_inbox` | Wave 0 |
| FILT-02 | `project="inbox"` (no $) -> normal name match only | integration (pipeline) | `uv run pytest tests/test_list_pipelines.py -x -q -k inbox_no_prefix` | Wave 0 |
| FILT-03 | `$inbox` + `inInbox: false` -> error | unit (Resolver) | `uv run pytest tests/test_service_resolve.py -x -q -k contradictory_false` | Wave 0 |
| FILT-04 | `$inbox` + `inInbox: true` -> accepted | unit (Resolver) | `uv run pytest tests/test_service_resolve.py -x -q -k redundant` | Wave 0 |
| FILT-05 | `inInbox: true` + real project -> error | unit (Resolver) | `uv run pytest tests/test_service_resolve.py -x -q -k contradictory_project` | Wave 0 |
| PROJ-01 | `get_project("$inbox")` -> error | unit (Resolver) | `uv run pytest tests/test_service_resolve.py -x -q -k get_project_inbox` | Wave 0 |
| PROJ-02 | `list_projects` never includes inbox | N/A | No test needed -- inbox is virtual | N/A |
| PROJ-03 | `list_projects` search "Inbox" -> warning | integration (pipeline) | `uv run pytest tests/test_list_pipelines.py -x -q -k inbox_search_warning` | Wave 0 |
| NRES-07 | List filters accept names | N/A | Already satisfied | Existing tests |
| DESC-03 | `$inbox` in field descriptions | manual-only | Visual review of description constants | N/A |
| DESC-04 | `get_project` description mentions `$inbox` error | unit (schema) | `uv run pytest tests/test_output_schema.py -x -q` | Existing |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_list_pipelines.py tests/test_service_resolve.py -x -q`
- **Per wave merge:** `uv run pytest -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- Tests for `resolve_inbox` scenarios (FILT-01 through FILT-05) -- add to `test_service_resolve.py`
- Tests for `get_project("$inbox")` guard (PROJ-01) -- add to `test_service_resolve.py`
- Tests for `list_projects` search warning (PROJ-03) -- add to `test_list_pipelines.py`
- Tests for pipeline integration (verify `_ListTasksPipeline` uses `resolve_inbox` output) -- add to `test_list_pipelines.py`

## Test Fixture Patterns

Existing test infrastructure is well-established [VERIFIED: codebase read]:
- `@pytest.mark.snapshot(...)` with `make_task_dict`, `make_project_dict` etc. for pipeline integration tests
- Direct `InMemoryBridge` + `BridgeOnlyRepository` + `Resolver` for unit tests of Resolver
- `pytest.raises(ValueError)` for error path testing
- All tests use `InMemoryBridge` per SAFE-01

### Key Test Data Patterns

```python
# Inbox task (no project):
make_task_dict(id="t-inbox", name="Inbox task")  # parent/project omitted = inbox

# Task in project:
make_task_dict(id="t-proj", name="Project task", project="proj-1")
```

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| -- | -- | -- | -- |

All claims in this research were verified against the codebase or cited from CONTEXT.md -- no user confirmation needed.

## Open Questions

None. CONTEXT.md provides locked implementations for every requirement. All integration points verified in codebase.

## Sources

### Primary (HIGH confidence)
- Codebase: `service/resolve.py`, `service/service.py`, `agent_messages/errors.py`, `agent_messages/warnings.py`, `agent_messages/descriptions.py`, `config.py`, `contracts/use_cases/list/tasks.py`, `contracts/use_cases/list/projects.py`
- Test files: `tests/test_list_pipelines.py`, `tests/test_service_resolve.py`
- CONTEXT.md: all locked decisions and implementation code

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all existing code
- Architecture: HIGH -- integration points verified in codebase, locked implementations provided
- Pitfalls: HIGH -- straightforward changes with clear ordering requirements

**Research date:** 2026-04-07
**Valid until:** 2026-05-07 (stable -- internal codebase changes only)
