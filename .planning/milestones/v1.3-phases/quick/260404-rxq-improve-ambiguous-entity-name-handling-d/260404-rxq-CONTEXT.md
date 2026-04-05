# Quick Task 260404-rxq: Improve ambiguous entity name handling — Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Task Boundary

Combines two pending todos (#11 and #15) plus a performance optimization:

1. **Write-side error guidance (#15):** Improve the ambiguous entity error message to tell the agent how to resolve it ("specify by ID instead of name").
2. **Read-side disambiguation warnings (#11):** Add warnings when `resolve_filter` matches multiple entities, so the agent knows its filter was broader than a single entity.
3. **Performance optimization:** Replace `get_all()` calls in the Resolver and read-side pipelines with targeted entity-specific list calls to avoid loading thousands of tasks unnecessarily.

Source todos:
- `.planning/todos/pending/2026-04-04-add-disambiguation-warnings-for-ambiguous-entity-names.md`
- `.planning/todos/pending/2026-04-04-improve-ambiguous-tag-error-message-with-resolution-guidance.md`

</domain>

<decisions>
## Implementation Decisions

### Write-side error message (currently tags only)
- Make the error message **generic** — parameterize by entity type: `AMBIGUOUS_ENTITY = "Ambiguous {entity_type} '{name}': multiple matches ({ids}). For ambiguous {entity_type}s, specify by ID instead of name."`
- Replace `AMBIGUOUS_TAG` with `AMBIGUOUS_ENTITY` in `agent_messages/errors.py`
- Generalize `_match_tag` → `_match_by_name(name, entities, entity_type)` on the Resolver so future entity types (projects, folders) get disambiguation for free
- Keep the same resolution strategy: exact case-insensitive name match → ambiguous error → ID fallback → not found

### Read-side disambiguation warnings
- Warn on **any multi-match** from `resolve_filter` (not just exact-name duplicates) — `len(resolved) > 1` triggers a warning
- This is a **warning** (results still returned), not an error — distinct from the write-side which raises ValueError
- Covers these filter parameters that go through `resolve_filter`:
  - `list_tasks`: `project`, `tags`
  - `list_projects`: `folder`
- Does **NOT** cover `search` parameters — search is expected to match multiple things, no warning needed
- Warning message should include entity type, the filter value, and the matched IDs with names so the agent can disambiguate

### Performance optimization: replace get_all() with targeted list calls
- **Write-side** `resolve_tags` in `resolve.py`: replace `get_all()` → `list_tags(limit=None)` (only needs tags)
- **Read-side** `_ListTasksPipeline` in `service.py`: replace `get_all()` → `list_tags(limit=None)` + `list_projects(limit=None)` (can be async parallel; needs tags + projects for filter resolution)
- **Read-side** `_ListProjectsPipeline` in `service.py`: replace `get_all()` → `list_folders(limit=None)` (only needs folders)
- Rationale: `get_all()` loads thousands of tasks which none of these code paths use. Tags/projects/folders are typically 20-50 items each — orders of magnitude cheaper.

### Discussed and decided: scope exclusions

**get_task / get_project / get_tag — no warnings needed:**
Considered proactive warnings (e.g., get_task returns a tag name that's ambiguous — warn so the agent doesn't hit an error on a later write). Rejected because TagRef already returns both ID and name in the response — the agent has everything it needs to disambiguate. And if it does use the name on a write, the write-side error will catch it anyway.

**list_tags / list_projects output scanning — not worth it:**
Initially considered scanning list responses for entities sharing a name (e.g., two tags both named "TestDupe" in list_tags output). Rejected because: (a) it's obvious from the list itself — both entries are visible with different IDs, and (b) these tools don't go through `resolve_filter`, so it would require a separate output-scanning mechanism, not a reuse of the filter warning logic.

**Substring broadening — warn, don't suppress:**
Debated whether to warn only on exact-name duplicates or on any multi-match (including substring broadening like "Work" matching "Work" + "Homework"). Decided: **warn on any multi-match**. It's one line of logic, doesn't hurt, and the agent can ignore it. Better to over-inform than silently broaden.

**`search` parameters — excluded:**
Search is inherently "give me anything that matches" — multiple results are expected, not surprising. No warning needed. This applies to `search` on list_tasks, list_tags, list_projects, list_folders, list_perspectives.

### Future context
Name-based resolution for projects and folders on the write side is planned for the near future. The generic `_match_by_name` and `AMBIGUOUS_ENTITY` are designed to be ready for that without further refactoring.

</decisions>

<specifics>
## Specific Ideas

- The read-side warning should be informative but concise, e.g.: "Filter 'Work' matched 2 tags: aaa (Work), bbb (Homework)"
- Add the new warning template to `agent_messages/warnings.py` alongside existing warning constants
- `resolve_filter` currently returns `list[str]` (IDs only) — the pipeline will need entity names for the warning message; the entities list is already available in the pipeline context

</specifics>

<canonical_refs>
## Canonical References

- `src/omnifocus_operator/service/resolve.py` — Resolver with `_match_tag`, `resolve_filter`, `resolve_tags`
- `src/omnifocus_operator/agent_messages/errors.py` — `AMBIGUOUS_TAG` constant (line 24)
- `src/omnifocus_operator/agent_messages/warnings.py` — existing warning constants
- `src/omnifocus_operator/service/service.py` — `_ListTasksPipeline` (line 285), `_ListProjectsPipeline` (line 353)
- `src/omnifocus_operator/contracts/use_cases/list/tags.py` — `ListTagsRepoQuery`

</canonical_refs>
