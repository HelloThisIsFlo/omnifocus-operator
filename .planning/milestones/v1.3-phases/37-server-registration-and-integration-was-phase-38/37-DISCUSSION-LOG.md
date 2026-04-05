# Phase 37: Server Registration and Integration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-03
**Phase:** 37-server-registration-and-integration
**Areas discussed:** Search expansion, Tool descriptions, Perspectives query, Test strategy, Protocol updates, Cross-path equivalence, Todo triage

---

## Search Expansion

### Search field naming

| Option | Description | Selected |
|--------|-------------|----------|
| search (Recommended) | Same field name across all 5 query models. Agent doesn't need to remember which entities support notes search. | ✓ |
| name | More precise — name-only match. Breaks consistency with tasks/projects. | |

**User's choice:** search
**Notes:** Consistency across all entity types. Tool description explains what each matches.

### Search scope within Phase 37

| Option | Description | Selected |
|--------|-------------|----------|
| All in Phase 37 (Recommended) | Search expansion is in requirements (SRCH-01..04) and success criteria. | ✓ |
| Split out search | Keep Phase 37 focused on server wiring only. | |

**User's choice:** All in Phase 37

### RepoQuery field propagation (from advisor research)

| Option | Description | Selected |
|--------|-------------|----------|
| Full symmetry | search on all RepoQuery models, both repo implementations. Follows tasks precedent. | ✓ |
| Service-layer strip | search stays agent-side only, service filters post-repo. Breaks total counts. | |

**User's choice:** Full symmetry
**Notes:** User also agreed to non-ASCII cross-path equivalence test to catch COLLATE NOCASE vs .lower() divergence. Noted asymmetry between search (repo-level LIKE) and "Did You Mean" (service-level fuzzy matching) — different purposes, accepted.

---

## Tool Descriptions

### Description layering approach

| Option | Description | Selected |
|--------|-------------|----------|
| Hybrid (behavioral + response shape) | Matches get_task/get_project read tool precedent. | |
| Layered split (edit_tasks pattern) | Tool desc = behavioral rules, Field(desc) = per-field semantics, class docstring = minimal. Zero overlap. | ✓ |

**User's choice:** Layered split following edit_tasks pattern
**Notes:** User directed to study how edit_tasks balances rich schema with description — they don't overlap. Tool description carries behavioral rules (filter interaction, defaults, pagination, response shape, camelCase). Field descriptions carry per-field semantics. Query docstring stays minimal. This is the established pattern, not a new decision.

---

## Perspectives Query

### Query model approach

| Option | Description | Selected |
|--------|-------------|----------|
| Full query model pair | ListPerspectivesQuery / ListPerspectivesRepoQuery with search field. Uniform with tags/folders. SC#7 names them. | ✓ |
| Inline param on method signature | Fewer files, breaks uniformity, contradicts SC#7. | |

**User's choice:** Full query model pair
**Notes:** Service method signature changes from no-args to accepting ListPerspectivesQuery.

---

## Test Strategy

### Server-level test depth

| Option | Description | Selected |
|--------|-------------|----------|
| Thin tests only | Wire-only: registration, output shape, annotations. | |
| Thin + one golden-path filter | Thin tests plus one filter test per tool proving end-to-end flow. | ✓ |
| Fat filter tests | Full filter combination coverage at server layer. | |

**User's choice:** Thin + one golden-path filter test per tool

---

## Quick-fire: Protocol Updates

| Option | Description | Selected |
|--------|-------------|----------|
| Straightforward wiring | Update protocols, implementations follow. Same pattern as tags/folders availability. | ✓ |

**User's choice:** Straightforward wiring

## Quick-fire: Cross-path Equivalence for Search

| Option | Description | Selected |
|--------|-------------|----------|
| Extend existing tests | Add search term to existing cross-path test cases. | |
| Separate search tests | Dedicated cross-path tests for search alone. | |
| You decide | Claude picks based on test structure. | ✓ |

**User's choice:** Claude's discretion

## Quick-fire: Todo Triage

| Option | Description | Selected |
|--------|-------------|----------|
| Mark covered | "Add search tool for projects" is exactly SRCH-01, mark as addressed. | ✓ |
| Fold in explicitly | Add as explicit scope item. | |

**User's choice:** Mark covered

---

## Claude's Discretion

- Cross-path equivalence test organization for search (extend vs separate)
- Exact field description content (fluency test application)
- Pipeline step organization for search in pass-through service methods

## Deferred Ideas

None — discussion stayed within phase scope.
