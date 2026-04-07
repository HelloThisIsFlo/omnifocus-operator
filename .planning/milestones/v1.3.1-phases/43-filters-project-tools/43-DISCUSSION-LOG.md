# Phase 43: Filters & Project Tools - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-07
**Phase:** 43-filters-project-tools
**Areas discussed:** Filter interception, Contradictory filter UX, Project tool guardrails, Description updates

---

## Filter Interception

| Option | Description | Selected |
|--------|-------------|----------|
| Pipeline checks before resolve_filter | Guard in `_resolve_project` checks for `$` prefix, maps to `in_inbox=True`. Resolver stays pure entity-list search | |
| Extend resolve_filter with $-prefix | Add system location handling to `resolve_filter`, return `["$inbox"]`, pipeline normalizes after | |
| New `resolve_inbox` method on Resolver | Takes `(in_inbox, project)`, returns `(effective_in_inbox, remaining_project)`. Centralizes all inbox/$ logic in Resolver | ✓ |
| model_validator on ListTasksQuery | Catch at validation time | Ruled out -- violates "contracts are pure data" rule |

**User's choice:** `resolve_inbox()` on the Resolver
**Notes:** User initially explored extending `resolve_filter` but realized the filter pipeline is different from write-side resolution. The key insight: `$inbox` in a project filter needs to normalize to the `in_inbox` boolean dimension, not resolve to a project ID. A dedicated method keeps this clean. User explicitly wanted all `$`-prefix logic centralized in the Resolver, not scattered in pipelines.

---

## Contradictory Filter UX

| Option | Description | Selected |
|--------|-------------|----------|
| Split: validator for errors, domain for warnings | Model validator catches hard contradictions (FILT-03), domain.py emits warning for always-empty (FILT-05) | |
| All in resolve_inbox, errors only | All contradictory cases are errors in `resolve_inbox`. No warnings, no split across layers | ✓ |

**User's choice:** All errors in `resolve_inbox`
**Notes:** User argued for symmetry: scenario 3 (`$inbox` + `inInbox: false`) and scenario 5 (`inInbox: true` + real project) are both impossible intersections. Making one an error and the other a warning would be inconsistent. Errors are simpler to implement (all in one method) and more helpful for agents (clear failure > empty result with warning). FILT-05 changed from milestone spec's "warning" to "error."

---

## Project Tool Guardrails

| Option | Description | Selected |
|--------|-------------|----------|
| Guard in lookup_project (Resolver) | $-prefix check before repo call, educational error + redirect | ✓ (PROJ-01) |
| No code for list_projects exclusion | Inbox is virtual, never in results | ✓ (PROJ-02) |
| Warning on search matching "Inbox" | Warning (not error) in _ListProjectsPipeline when search substring-matches inbox name | ✓ (PROJ-03) |

**User's choice:** All three as described
**Notes:** User clarified PROJ-03 intent: the warning is for agents that search for "Inbox" expecting to find it as a project. Educational redirect to `list_tasks`. Warning not error because the search might legitimately match real projects like "Finance Inbox." Trigger is `search` field only, not `folder` filter (folder = containing folder, irrelevant to inbox).

---

## Description Updates

| Option | Description | Selected |
|--------|-------------|----------|
| Mention $inbox in filter descriptions | Both PROJECT_FILTER_DESC and IN_INBOX_FILTER_DESC reference $inbox | |
| Don't mention $inbox in filter descriptions | Filter descriptions stay clean. $inbox filter is intuitive compatibility, not advertised | ✓ (DESC-03) |
| GET_PROJECT_TOOL_DOC with error + redirect | Mention $inbox is not a valid project, redirect to list_tasks | ✓ (DESC-04) |

**User's choice:** No filter description changes; only GET_PROJECT_TOOL_DOC updated
**Notes:** User's philosophy: `$inbox` in the project filter works because agents may naturally try it after seeing `project.id: "$inbox"` in task output. But `inInbox: true/false` is the canonical path. Same philosophy as Phase 41's `parent: null` handling -- intuitive compatibility without promotion. "We make it work because we're nice; we don't want to encourage it."

---

## Claude's Discretion

- Exact error message wording for contradictory filter templates
- Whether resolve_inbox delegates to _resolve_system_location or duplicates the check
- Placement of list_projects search warning within _ListProjectsPipeline

## Deferred Ideas

- **Patch semantics for list query fields** -- All `T | None = None` filter fields should become `Patch[T] = UNSET` to prevent agents from explicitly sending null. User will add as a todo.
