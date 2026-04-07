# Project Research Summary

**Project:** OmniFocus Operator — v1.3.1 First-Class References
**Domain:** MCP server API contract evolution — system locations, name resolution, rich references
**Researched:** 2026-04-05
**Confidence:** HIGH

## Executive Summary

v1.3.1 is a focused API contract cleanup milestone, not a feature addition. The central problem is null overloading: `null` currently means three different things in the API (no parent, inbox, field not set), and agents cannot distinguish them in raw JSON. The solution is a coherent system: `$inbox` as an explicit named location, tagged object discriminators for `parent` (`{"project": {...}}` vs `{"task": {...}}`), and `{id, name}` rich references everywhere. Anthropic's own tool design guidance directly validates both the rich reference pattern and name-based resolution as first-class agent ergonomics.

No new dependencies are needed. Everything required is already in the stack — Pydantic 2.12.5 (via fastmcp), sqlite3, and existing resolver infrastructure. The key implementation decisions have been validated locally: the wrapper-model tagged-object pattern works correctly with `exclude_defaults=True` and produces clean, MCP-interpretable JSON Schema. The `$` prefix approach is syntactically disjoint from valid OmniFocus IDs, making system locations collision-proof.

The primary risks are structural: model changes have blast radius across the entire test suite (1,528 tests, 26-field task factory), golden master fixtures will need human re-capture, and the `$inbox` concept must stay strictly service-layer and never leak to the repository or bridge. These are all mitigatable with correct ordering: build models first, resolver second, wire writes third, rewire reads fourth, filter changes fifth, and descriptions last.

## Key Findings

### Recommended Stack

No stack changes required. The existing stack handles everything v1.3.1 needs. The critical Pydantic pattern choice — wrapper model with `@model_validator` over `Discriminator`/`Tag` — has been verified against the installed version and is already proven in the codebase via `MoveAction`.

**Core technologies:**
- **Python 3.12+**: Runtime — unchanged
- **fastmcp >= 3.1.1 / Pydantic 2.12.5**: Model validation and JSON Schema — wrapper model pattern verified locally against installed version
- **sqlite3 (stdlib)**: Read path — no query changes needed; inbox detection reuses existing `inInbox` SQL column
- **Existing `Resolver` class**: Name resolution infrastructure — extensions only, no rewrites

**Key pattern decision:** Use `TaskParent(project: ProjectRef | None, task: TaskRef | None)` with `@model_validator(mode="after")`. Do NOT use `Discriminator` + `Tag` (opaque JSON Schema) or `Literal` discriminator fields (`exclude_defaults=True` strips them — prior codebase bug DL-12).

### Expected Features

All features in this milestone are tightly coupled and form a single coherent contract change. No deferral is recommended.

**Must have (table stakes):**
- `$inbox` system location constant + resolver `$`-prefix short-circuit — eliminates null overloading
- `ProjectRef`, `TaskRef`, `FolderRef` as `{id, name}` typed models — agents need names to reason, not bare IDs
- `Task.parent` as tagged object (never null) — removes ambiguity about parent type
- `Task.project` field (never null, `$inbox` for inbox tasks) — agents can determine containment without walking parent chain
- `inInbox` field removal — replaced by `project: {id: "$inbox", ...}`, one fewer boolean to track
- `$inbox` in `add_tasks` and `edit_tasks` write fields — what agents read, they can write back
- Name-based resolution for write fields (`parent`, `beginning`, `ending`) — consistent with tags (v1.2) and filters (v1.3)
- `PatchOrNone` type elimination — `$inbox` replaces the null-as-inbox semantic

**Should have (differentiators):**
- Three-step resolver precedence (`$` -> ID -> name) — single unified resolution model across all fields
- Contradictory filter detection (`project: "$inbox"` + `inInbox: false` -> error) — prevents silent empty results
- Educational error messages for `before`/`after` with container IDs — teaches the correct field
- `get_project("$inbox")` descriptive error — teaches agents the right tool
- `list_projects` inbox warning on name filter — prevents agents from searching for a non-existent project
- Write/read vocabulary symmetry — what you write (`"$inbox"`), you read back (`{id: "$inbox", name: "Inbox"}`)

**Explicit anti-features (do not build):**
- Virtual inbox project in `get_project` / `list_projects` — fabricated data with meaningless required fields
- Deprecation warnings for `ending: null` — pre-release, break cleanly instead
- `$trash`, `$archive`, or other system locations — only `$inbox` has a concrete use case; `$` namespace supports extension later
- Fuzzy/Levenshtein name matching — case-insensitive substring sufficient; fuzzy is planned for v1.4.x

### Architecture Approach

The change touches 6 layers (config, models, contracts, resolver, domain logic, mappers) but the dependency chain is clean and linear. The architectural principle is strict: `$inbox` is a service-layer concept only. The bridge never sees it (PayloadBuilder converts to `None`). The repository never sees it (service converts `$inbox` filter to `in_inbox: True` before repo boundary). Mappers emit `$inbox` on the read path; the resolver consumes it on the write path — enabling full round-trip consistency.

**Major components changed:**
1. **`config.py`** — 3 new constants (`SYSTEM_LOCATION_PREFIX`, `INBOX_ID`, `INBOX_DISPLAY_NAME`); imported by all affected layers
2. **`models/common.py`** — `ProjectRef`, `TaskRef`, `FolderRef` (follow `TagRef` pattern); `TaskParent` tagged wrapper; `ParentRef` removed
3. **`service/resolve.py`** — `_resolve_system_location()`, `resolve_entity()` (write-side, exact-one-or-error), `resolve_container()`, `resolve_anchor()`; `resolve_filter()` extended for `$`-prefix
4. **`service/domain.py`** — `_process_container_move` update, contradictory filter detection, `get_project("$inbox")` guard, `list_projects` inbox warning
5. **`repository/hybrid/hybrid.py`** — `_build_parent_ref` rewrite, new `_build_project_ref`, mapper enrichment for folder/tag/task/project references; new folder name lookup
6. **`repository/bridge_only/adapter.py`** — parallel mapper changes (bridge path must produce identical output shapes for cross-path equivalence tests)
7. **`contracts/base.py` + `contracts/shared/actions.py`** — `PatchOrNone` deleted, `MoveAction.beginning`/`ending` -> `Patch[str]`

### Critical Pitfalls

1. **Tagged object + `exclude_defaults` interaction** — `Task.parent` must NOT have a default value. Never add `@model_serializer` to the wrapper (project rule: contracts are pure data). Add dedicated content-level serialization tests — `test_output_schema.py` catches schema drift but not runtime serialization bugs.

2. **Test factory blast radius** — `make_model_task_dict()` hardcodes `"inInbox": True` and `"parent": None` across 1,528 tests. Update atomically with model changes. Grep for `"inInbox"` and `"parent": None` across all test files — non-factory usages are easy to miss.

3. **`$inbox` leaking to bridge payloads** — Bridge expects `null` for inbox, not the string `"$inbox"`. PayloadBuilder must translate before constructing repo payload. All write paths (add_tasks, edit_tasks, moveTo fields) need explicit test coverage.

4. **`inInbox` removal ordering** — Add `project` field FIRST (alongside `inInbox`), verify, THEN remove `inInbox`. Never ship a state where inbox status is unrepresented in output. Or do both atomically in a single phase commit.

5. **Golden master breakage** — All 43 golden master fixture scenarios use the old bare-ID format for `folder`, `next_task`, `parent`. Re-capture is human-only (GOLD-01 constraint). Plan an explicit UAT re-capture step in Phase 4.

## Implications for Roadmap

Based on research, the dependency chain drives a natural 6-phase structure. Phases 3 and 4 are independent of each other (writes vs reads) and could be parallelized, but sequential ordering enables full `$inbox` round-trip testing.

### Phase 1: Foundation — Constants + New Models
**Rationale:** Zero-risk pure additions. No existing code changes. Every subsequent phase imports from here.
**Delivers:** `config.py` constants, `ProjectRef`/`TaskRef`/`FolderRef` in `models/common.py`, `TaskParent` tagged wrapper, unit tests for exactly-one-key validation.
**Addresses:** Prerequisite for all other phases
**Avoids:** P2 (`model_rebuild` namespace) — add to `_ns` and `model_rebuild()` in the same commit that defines the types

### Phase 2: Resolver — System Locations + Write-Side Name Resolution
**Rationale:** Central integration point. Both write pipelines and filter pipelines depend on the resolver. Build before consumers for clean testing.
**Delivers:** `_resolve_system_location()`, `resolve_entity()`, `resolve_container()`, `resolve_anchor()`, updated `resolve_filter()`, new error message constants.
**Avoids:** P8 (wrong entity type for `before`/`after`) — `resolve_anchor()` is task-only, `resolve_container()` covers projects + `$inbox`; P11 (double resolution) — every entry point implements the full three-step cascade

### Phase 3: Write Pipeline Updates
**Rationale:** Requires Phase 2 resolver. Self-contained — doesn't affect read output. Tests verify `$inbox` write behavior before the higher-blast-radius read-side changes.
**Delivers:** `$inbox` in `add_tasks`/`edit_tasks`, `parent: null` warning, `PatchOrNone` deleted, `MoveAction` type change, `_process_container_move` and `_process_anchor_move` updates, PayloadBuilder `$inbox` -> `None` conversion.
**Avoids:** P3 (ordering) — `PatchOrNone` elimination happens after `$inbox` write support is confirmed; P5 (`$inbox` bridge leakage) — PayloadBuilder conversion tested explicitly; P6 (dangling imports) — grep before deleting `PatchOrNone`

### Phase 4: Read Output — Model Changes + Mapper Rewrites
**Rationale:** Highest-risk phase. Requires Phase 1 models. Independent of write changes. Placing after writes enables full `$inbox` round-trip tests.
**Delivers:** `Task.parent` tagged object (never null), `Task.project` field (never null), `inInbox` removal, rich `{id, name}` references on all entities, `ParentRef` removed, bridge-only adapter updated, InMemoryBridge updated. Includes explicit UAT step for golden master re-capture.
**Avoids:** P1 (serialization) — no defaults on parent field, dedicated content-level serialization tests; P4 (test factory) — update `make_model_task_dict` atomically, grep for hardcoded values; P7 (golden master) — UAT re-capture planned explicitly; P14 (ParentRef removal) — grep all sites before deleting

### Phase 5: Filter Updates
**Rationale:** Requires Phase 2 (resolver `$`-prefix) and Phase 4 (output models — test assertions use new shapes).
**Delivers:** `project: "$inbox"` in `list_tasks`, contradictory filter detection, `get_project("$inbox")` error, `list_projects` inbox warning.
**Avoids:** P9 (two SQL code paths) — `$inbox` -> `in_inbox: True` at service layer, never reaches repo; P10 (contradiction scope creep) — implement only the two specified contradictions; P15 (`get_project` guard before resolver, not inside it)

### Phase 6: Descriptions + Cleanup
**Rationale:** Descriptions must reference the completed API field shapes. Writing them last ensures accuracy.
**Delivers:** 7 tool descriptions updated for `{id, name}` format, `parent` vs `project` explanation for subtasks, stale description constants removed, output schema tests updated, cross-path equivalence tests updated.
**Avoids:** Description drift — changes verified against already-working implementation

### Phase Ordering Rationale

- Phase 1 first — constants and models are pure additions; everything depends on them
- Phase 2 before writes and filters — resolver is the shared `$`-prefix gateway; build once, wire in both directions
- Phase 3 (writes) before Phase 5 (filters) — `$inbox` in writes should be proven before wiring the filter path
- Phase 4 (reads) is independent of Phase 3 (writes) — placed after writes to enable round-trip tests, but order is reversible
- Phase 6 last — descriptions cannot be written accurately until the API is finalized

### Research Flags

Phases with well-understood patterns (no additional research needed):
- **Phase 1:** Pure model additions following existing `TagRef` pattern
- **Phase 2:** Extending existing `Resolver` class — pattern is established in codebase
- **Phase 3:** Write pipeline wiring — same pattern as v1.2 write features
- **Phase 5:** Filter logic — same pattern as v1.3 filter features
- **Phase 6:** Description updates — no unknowns

Phase warranting careful implementation review (not research, but execution vigilance):
- **Phase 4:** Highest complexity — touches every output model and mapper, golden master impact, InMemoryBridge must stay in sync. Not unknown territory, but highest blast radius. Benefit from detailed per-mapper checklist.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified against installed Pydantic 2.12.5; no new dependencies; wrapper model pattern tested locally |
| Features | HIGH | Backed by Anthropic tool design guidance, Abseil sentinel value principles, GitHub GraphQL precedent; anti-features explicitly argued |
| Architecture | HIGH | Direct codebase analysis; all integration points traced; data flow diagrams verified against actual code |
| Pitfalls | HIGH | Grounded in prior codebase bugs (DL-12 discriminator issue, Frequency.type lesson), specific file/line references, project conventions |

**Overall confidence:** HIGH

### Gaps to Address

- **Golden master re-capture timing:** GOLD-01 requires human re-capture. The exact UAT step (run after Phase 4 mappers, before Phase 5 tests that assert on output shapes) needs to be scheduled explicitly in the roadmap. Process gap, not a technical unknown.
- **`TagAction.replace` type audit:** STACK.md notes this field may be `PatchOrNone` or `PatchOrClear` — needs a one-line verification before `PatchOrNone` is deleted to confirm it can be retyped to `PatchOrClear` without behavior change.
- **InMemoryBridge update scope:** The bridge doubles in `tests/doubles/` must produce the same output shapes. Exact fields needing updates should be audited during Phase 4 planning to avoid surprise cross-path failures.

## Sources

### Primary (HIGH confidence)
- Local Pydantic 2.12.5 testing — wrapper model behavior with `exclude_defaults`, `by_alias`, JSON Schema output
- Codebase analysis — `service/resolve.py`, `service/domain.py`, `models/__init__.py`, `repository/hybrid/hybrid.py`, `contracts/base.py`, `tests/conftest.py`
- Milestone spec — `.research/updated-spec/MILESTONE-v1.3.1.md`

### Secondary (MEDIUM confidence)
- [Anthropic: Writing Tools for Agents](https://www.anthropic.com/engineering/writing-tools-for-agents) — rich references and name-based input validation
- [Abseil Tip #171: Avoid Sentinel Values](https://abseil.io/tips/171) — `$` prefix vs in-band sentinel design
- [GitHub GraphQL: Using Global Node IDs](https://docs.github.com/en/graphql/guides/using-global-node-ids) — dual ID/name access pattern precedent
- [Tool Calling Optimization](https://www.statsig.com/perspectives/tool-calling-optimization) — agent tool design patterns
- [Pydantic v2 Unions docs](https://docs.pydantic.dev/latest/concepts/unions/) — discriminated union options and trade-offs

---
*Research completed: 2026-04-05*
*Ready for roadmap: yes*
