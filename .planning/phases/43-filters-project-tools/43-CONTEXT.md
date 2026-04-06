# Phase 43: Filters & Project Tools - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Agents can filter tasks by `$inbox` as a project, with contradictory filter detection, correct project tool behavior, and complete tool documentation for $inbox usage. No new tools, no write changes, no model structure changes.

</domain>

<decisions>
## Implementation Decisions

### resolve_inbox on Resolver (FILT-01, FILT-03, FILT-04, FILT-05)
- **D-01:** New method `resolve_inbox(in_inbox: bool | None, project: str | None) -> tuple[bool | None, str | None]` on the `Resolver` class
- **D-02:** Returns `(effective_in_inbox, remaining_project_filter)`. If project is `$inbox`, returns `(True, None)` -- project is "consumed," no further resolution needed
- **D-03:** Unknown `$`-prefixed values (e.g., `$trash`) delegate to existing `_resolve_system_location` which raises with educational error listing valid locations
- **D-04:** `_ListTasksPipeline` calls `resolve_inbox` BEFORE `_resolve_project`. Uses returned values for `in_inbox` and the project to resolve. Pipeline never touches `$` prefix logic directly
- **D-05:** Repo layer (`ListTasksRepoQuery`) never sees `$inbox` as a string. Normalization happens entirely at the service layer

**Locked implementation** -- executor MUST follow this shape:

```python
# In Resolver (service/resolve.py)

def resolve_inbox(
    self, in_inbox: bool | None, project: str | None
) -> tuple[bool | None, str | None]:
    """Resolve inbox filter state from in_inbox and project filter params.

    Returns (effective_in_inbox, remaining_project_to_resolve).
    If project is "$inbox", it is consumed: returns (True, None).
    Unknown $-prefix raises. Contradictory combos raise.
    """
    if project is not None and project.startswith(SYSTEM_LOCATION_PREFIX):
        self._resolve_system_location(project, [EntityType.PROJECT])
        # Scenario 3: $inbox + inInbox=false → contradictory
        if in_inbox is False:
            raise ValueError(CONTRADICTORY_INBOX_FALSE)
        # Scenarios 6 & 7: $inbox consumed → in_inbox=True
        return (True, None)

    # Scenario 5: inInbox=true + real project → contradictory
    if in_inbox is True and project is not None:
        raise ValueError(CONTRADICTORY_INBOX_PROJECT)

    # Scenarios 1, 2, 4: pass through unchanged
    return (in_inbox, project)
```

```python
# In _ListTasksPipeline (service/service.py)
# Called in execute() BEFORE _resolve_project():

self._in_inbox, self._project_to_resolve = self._resolver.resolve_inbox(
    self._query.in_inbox, self._query.project
)

# _resolve_project() uses self._project_to_resolve instead of self._query.project
# _build_repo_query() uses self._in_inbox instead of self._query.in_inbox
```

### Contradictory Filter Detection -- All Errors, Not Warnings
- **D-06:** Scenario 3 (`project: "$inbox"` + `inInbox: false`) -- **error** in `resolve_inbox`. See locked implementation above
- **D-07:** Scenario 5 (`inInbox: true` + any real project filter) -- **error** in `resolve_inbox`. Symmetric with scenario 3. Rule: inbox filter and project filter are mutually exclusive
- **D-08:** Scenario 6 (`project: "$inbox"` + `inInbox: true`) -- silently accepted, returns `(True, None)`. Redundant but not harmful
- **D-09:** FILT-05 changed from spec's "warning" to "error". Rationale: symmetry with FILT-03, simpler implementation (everything in `resolve_inbox`), agent-first (clear error > empty result + warning)
- **D-10:** Error messages use educational pattern with templates in `agent_messages/errors.py`. Tests must verify error messages reference the proper system location name (anti-regression)

**Locked error message templates** -- add to `agent_messages/errors.py`:

```python
CONTRADICTORY_INBOX_FALSE = (
    "Contradictory filters: 'project=\"$inbox\"' selects inbox tasks, "
    "but 'inInbox=false' excludes them. Use one or the other."
)
CONTRADICTORY_INBOX_PROJECT = (
    "Contradictory filters: 'inInbox=true' selects tasks with no project. "
    "Combining with a 'project' filter always yields nothing. Use one or the other."
)
```

### FILT-02: Name Matching Without $
- **D-11:** `project: "inbox"` (no `$` prefix) flows through normal `resolve_filter` -- substring matches project names only. System inbox is never matched. No special handling needed -- this is the existing behavior

### get_project("$inbox") Guard (PROJ-01)
- **D-12:** Guard in `lookup_project` on the Resolver. Checks `$` prefix before repo call
- **D-13:** Error message: educational + redirect
- **D-14:** Error template in `agent_messages/errors.py`, consistent with other dead-end error patterns

**Locked implementation:**

```python
# In Resolver.lookup_project (service/resolve.py)

async def lookup_project(self, project_id: str) -> Project:
    if project_id.startswith(SYSTEM_LOCATION_PREFIX):
        raise ValueError(GET_PROJECT_INBOX_ERROR)
    # ... existing repo lookup
```

**Locked error message template:**

```python
GET_PROJECT_INBOX_ERROR = (
    "The inbox appears as a project on tasks but is not a real OmniFocus project "
    "— it has no review schedule, status, or other project properties. "
    "To query inbox tasks, use list_tasks with 'inInbox=true'."
)
```

### list_projects Inbox Exclusion (PROJ-02)
- **D-15:** No code needed. Inbox is virtual -- not in SQLite, not in bridge dump. Can never appear in `list_projects` results

### list_projects Search Warning (PROJ-03)
- **D-16:** Warning (not error) when `search` field substring-matches `SYSTEM_LOCATIONS["inbox"].name` (case-insensitive)
- **D-17:** Trigger is `search` field only, not `folder` filter. `search` is the free-text name/notes search; `folder` filters by containing folder (irrelevant to inbox)
- **D-18:** Uses same substring logic as `resolve_filter` for consistency: `search.lower() in SYSTEM_LOCATIONS["inbox"].name.lower()`
- **D-19:** Lives in `_ListProjectsPipeline`, appended to response warnings after results are built. Real results still returned normally

**Locked warning message template:**

```python
LIST_PROJECTS_INBOX_WARNING = (
    "The system Inbox is not a project and won't appear in results. "
    "To query inbox tasks, use list_tasks with inInbox: true."
)
```

### Description Updates (DESC-03, DESC-04)
- **D-21:** Filter field descriptions (`PROJECT_FILTER_DESC`, `IN_INBOX_FILTER_DESC`) do NOT mention `$inbox`. Intentional: `$inbox` in project filter is intuitive compatibility (agents discover it from output), not the canonical path. `inInbox` is the documented way to filter by inbox
- **D-22:** `GET_PROJECT_TOOL_DOC` updated with `$inbox` error behavior: states it's not a valid project, redirects to `list_tasks` with `inInbox: true` (DESC-04)
- **D-23:** No other description changes needed for Phase 43. Write-side descriptions (Phase 41) and output descriptions (Phase 42) already cover `$inbox`

### NRES-07: Already Satisfied
- **D-24:** List filter fields already accept entity names via `resolve_filter` (built in v1.3). No Phase 43 work needed. Mark as inherited/done

### Claude's Discretion
- Placement of the `list_projects` search warning check within `_ListProjectsPipeline` (after results, before return)
- Internal naming of pipeline fields (`self._in_inbox`, `self._project_to_resolve`, etc.) -- follow existing pipeline conventions

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone Spec
- `.research/updated-spec/MILESTONE-v1.3.1.md` -- Full milestone design, decision log, acceptance criteria. Sections on filter changes, project tool behavior, and name resolution are directly relevant

### Architecture & Patterns
- `docs/architecture.md` -- Three-layer architecture, method object pattern for service pipelines
- `docs/model-taxonomy.md` -- Model naming conventions (Command/RepoPayload/RepoResult/Result)

### Existing Implementation (read these to understand integration points)
- `src/omnifocus_operator/service/resolve.py` -- Resolver class with `_resolve`, `_resolve_system_location`, `resolve_filter`. New `resolve_inbox` method goes here
- `src/omnifocus_operator/service/service.py` -- `_ListTasksPipeline` and `_ListProjectsPipeline`. Integration points for resolve_inbox and search warning
- `src/omnifocus_operator/contracts/use_cases/list/tasks.py` -- `ListTasksQuery` and `ListTasksRepoQuery`
- `src/omnifocus_operator/config.py` -- `SYSTEM_LOCATIONS`, `SYSTEM_LOCATION_PREFIX` constants
- `src/omnifocus_operator/agent_messages/errors.py` -- Error message templates
- `src/omnifocus_operator/agent_messages/descriptions.py` -- Tool and field description constants

### Prior Phase Context
- `.planning/phases/40-resolver-system-location-detection-name-resolution/40-CONTEXT.md` -- Resolver cascade design, error patterns
- `.planning/phases/41-write-pipeline-inbox-in-add-edit/41-CONTEXT.md` -- Null rejection patterns, error message wording, PatchOrNone elimination
- `.planning/phases/42-read-output-restructure/42-CONTEXT.md` -- Tagged parent, project field, inInbox removal from output

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Resolver._resolve_system_location()` -- Already handles `$`-prefix validation and unknown location errors. `resolve_inbox` delegates to this
- `Resolver.resolve_filter()` -- Read-side name/ID cascade. Used by `_resolve_project` after `resolve_inbox` normalizes
- `DomainLogic.check_filter_resolution()` -- Generates "did you mean?" warnings for unresolved filters. Used after resolve_filter, not affected by resolve_inbox
- Error templates in `agent_messages/errors.py` -- Follow `{field}` placeholder pattern with educational messages

### Established Patterns
- Method Object pipeline: `execute() -> _normalize() -> _resolve() -> _build_repo_query() -> _delegate()`
- Resolver returns IDs (or None for inbox), pipeline maps to repo query fields
- Warnings appended to `self._warnings` list, included in response

### Integration Points
- `_ListTasksPipeline.execute()` -- Insert `resolve_inbox` call before `_resolve_project`
- `_ListTasksPipeline._build_repo_query()` -- Use resolved `in_inbox` from `resolve_inbox` instead of `self._query.in_inbox`
- `Resolver.lookup_project()` -- Add `$`-prefix guard before repo call
- `_ListProjectsPipeline` -- Add search warning check after results are built

</code_context>

<specifics>
## Specific Ideas

- Error messages must reference the system location name from `SYSTEM_LOCATIONS` constant, not hardcoded strings. Tests verify this (anti-regression)
- `resolve_inbox` shape: `(in_inbox: bool | None, project: str | None) -> tuple[bool | None, str | None]` -- first element is effective in_inbox, second is remaining project (None if consumed)
- FILT-05 deliberately changed from milestone spec's "warning" to "error" for symmetry with FILT-03 and implementation simplicity
- Filter descriptions intentionally omit `$inbox` -- same philosophy as Phase 41's `parent: null` handling (intuitive compatibility, not advertised)

</specifics>

<deferred>
## Deferred Ideas

- **Patch semantics for list query fields** -- All list query fields (e.g., `in_inbox: bool | None`, `project: str | None`, `flagged: bool | None`) should use `Patch[T] = UNSET` instead of `T | None = None`. This prevents agents from explicitly sending `null` (which the schema currently allows). Omitting = no filter, providing a value = filter. Same philosophy as Phase 41's write-side Patch conversion. Captured as a todo, not Phase 43 scope.
- **NRES-07 requirement status** -- Already satisfied by v1.3's `resolve_filter`. Should be marked as done in REQUIREMENTS.md

</deferred>

---

*Phase: 43-filters-project-tools*
*Context gathered: 2026-04-07*
