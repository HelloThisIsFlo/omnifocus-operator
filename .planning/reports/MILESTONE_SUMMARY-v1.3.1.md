# Milestone v1.3.1 — First-Class References: Project Summary

**Generated:** 2026-04-12
**Purpose:** Team onboarding and project review

---

## 1. Project Overview

OmniFocus Operator is a Python MCP server exposing OmniFocus (macOS task manager) as structured task infrastructure for AI agents. Reads via SQLite cache (~46ms), writes via OmniJS bridge. 11 MCP tools, agent-first design with educational warnings, typed query models, and patch semantics.

**Core value:** Reliable, simple, debuggable access to OmniFocus data for AI agents — executive function infrastructure that works at 7:30am.

**v1.3.1 milestone goal:** Eliminate null overloading for inbox across the entire API surface — `$inbox` becomes the single, explicit representation everywhere. Rich `{id, name}` references on all output models. Name-based resolution for all write fields.

**State at milestone start:** v1.3 (Read Tools) shipped — 5 list tools, SQL filtering, name-to-ID resolution, description centralization. 1,528 pytest tests, 94% coverage.

**State at milestone end:** 1,693 pytest tests, ~98% coverage. 204 commits in 3 days. All 61 requirements passed with zero code gaps.

---

## 2. Architecture & Technical Decisions

- **`$` prefix namespace for system locations** — `$inbox` is an ID-level convention, not a display name. Three-step resolver: system location -> ID -> name. Extensible to future `$forecast`, `$flagged`. (Phase 39-40)
  - **Why:** Clean separation of API convention from display. Agents write `$inbox`, never need to know internal representation.

- **Tagged parent discriminator over nullable union** — `{"project": {id,name}}` / `{"task": {id,name}}` instead of `{type, id} | null`. Inbox = `{project: {id: "$inbox", name: "Inbox"}}`. Never null. (Phase 42)
  - **Why:** Self-describing output — agents see the shape and know the type. No null ambiguity anywhere in the response.

- **Rich `{id, name}` refs on all cross-entity fields** — Every foreign reference is an object, not a bare ID. Agents never need a second lookup. (Phase 42)
  - **Why:** Eliminates an entire class of follow-up API calls.

- **Null elimination from agent-facing schemas** — All write fields and list query filters use `Patch[T]` with UNSET default. Null rejected with educational error. Service translates UNSET->None at repo boundary. (Phase 41, 44)
  - **Why:** Clean three-way semantics (unset/null/value) everywhere. Agents can't accidentally send null when they mean "no change."

- **AvailabilityFilter enums with ALL shorthand** — `["all"]` expands to full `list(Availability)` at service layer. Mixed `["all", "available"]` accepted with warning. (Phase 44)
  - **Why:** Ergonomic for agents — single value instead of listing every enum member.

- **`resolve_inbox` as synchronous pre-resolution step** — Converts `$inbox` to `in_inbox=True` before pipeline resolution cascade. Keeps the resolver simple. (Phase 43)
  - **Why:** `$inbox` is a display concept, not an entity ID — translating it before the pipeline means no special-casing downstream.

- **PatchOrNone elimination** — Replaced with `Patch[str]` plus null-rejection validators. Fewer type aliases, stronger validation. (Phase 41)
  - **Why:** `PatchOrNone` was a legacy artifact from v1.2 that permitted null in places where it shouldn't be accepted.

---

## 3. Phases Delivered

| Phase | Name | Status | One-Liner |
|-------|------|--------|-----------|
| 39 | Foundation — Constants & Reference Models | Complete | System location constants and new typed reference models (ProjectRef, TaskRef, FolderRef) |
| 40 | Resolver — System Location & Name Resolution | Complete | $-prefix routing, write-side name resolution for all entity fields |
| 41 | Write Pipeline — $inbox in Add/Edit | Complete | $inbox write support, PatchOrNone elimination, container error handling |
| 42 | Read Output Restructure | Complete | Tagged parent discriminator, project field, inInbox removal, rich {id, name} refs on all entities |
| 43 | Filters & Project Tools | Complete | $inbox in list_tasks filters, contradictory filter detection, project tool guardrails |
| 44 | Patch Query Filter Migration | Complete | Null eliminated from all agent-facing list query schemas, AvailabilityFilter enums |

---

## 4. Requirements Coverage

**61/61 requirements satisfied.** Audit passed with zero code gaps — only documentation-level findings.

### System Locations (3/3)
- SLOC-01: `$` prefix constant and `$inbox` defined in config
- SLOC-02: Resolver routes `$`-prefixed strings to system location lookup
- SLOC-03: Unrecognized system location returns error listing valid locations

### Models & Type System (10/10)
- MODL-01 through MODL-03: ProjectRef, TaskRef, FolderRef models exist
- MODL-04/05: Task parent uses tagged discriminator, never null (inbox = ProjectRef)
- MODL-06: Task has `project` field — containing project at any depth
- MODL-07: `inInbox` removed from Task output
- MODL-08: `ParentRef` model removed
- MODL-09/10: PatchOrNone eliminated, MoveAction uses Patch[str]

### Write Pipeline (8/8)
- WRIT-01 through WRIT-08: Full $inbox support in add/edit, null rejection with educational errors, before/after container ID error

### Read Pipeline (7/7)
- READ-01 through READ-07: Rich {id, name} refs across all entities and all tools

### Filters (5/5)
- FILT-01 through FILT-05: $inbox filter integration, contradictory filter detection

### Name Resolution (8/8)
- NRES-01 through NRES-08: Case-insensitive substring matching for all write fields, $-prefix bypass, error handling

### Project Tools (3/3)
- PROJ-01: `get_project("$inbox")` returns descriptive error
- PROJ-02: `list_projects` never includes inbox
- PROJ-03: Name filter matching "Inbox" triggers warning

### Tool Descriptions (4/4)
- DESC-01 through DESC-04: All descriptions document hierarchy, enriched refs, $inbox usage

### Patch Query Migration (13/13)
- PATCH-01 through PATCH-13: All filter fields migrated to Patch[T], AvailabilityFilter enums, service boundary translation

**Audit verdict:** PASSED — 61/61 requirements, 6/6 phases, 6/6 E2E flows, Nyquist compliant.

---

## 5. Key Decisions Log

| # | Decision | Phase | Rationale |
|---|----------|-------|-----------|
| 1 | `$` prefix namespace for system locations | 39-40 | Extensible pattern — `$inbox` today, `$forecast`/`$flagged` later. API convention in IDs, not display names |
| 2 | Tagged parent discriminator (`{project: {...}}`) | 42 | Self-describing shapes; same validator as MoveAction exactly-one pattern; never null |
| 3 | Rich `{id, name}` on all cross-entity refs | 42 | Eliminates follow-up lookups. Every reference is an object, not a bare ID |
| 4 | Null elimination via Patch[T] everywhere | 41, 44 | Consistent three-way semantics across all write fields and list query filters |
| 5 | PatchOrNone deletion | 41 | Legacy type alias permitted null where it shouldn't be accepted; replaced with Patch[str] + null-rejection |
| 6 | `resolve_inbox` as synchronous pre-resolution | 43 | Translates display concept before pipeline — no special-casing downstream |
| 7 | AvailabilityFilter enums with ALL shorthand | 44 | Ergonomic for agents. `["all"]` expands to full list; mixed accepted with warning |
| 8 | Contradictory filter detection (symmetric errors) | 43 | `$inbox + inInbox:false` and `inInbox:true + real project` both return errors — symmetric, not asymmetric warnings |
| 9 | `adapt_snapshot` bridge-only filter for project root tasks | 43 | Parity with SQL LEFT JOIN ProjectInfo — bridge path was returning extra root tasks |
| 10 | `reject_null_filters` shared helper | 44 | model_validator(mode="before") null rejection — DRY across all query models |

---

## 6. Tech Debt & Deferred Items

### Pre-existing (not from this milestone)
- `descriptions.py:325` — `TODO(v1.5): Remove when built-in perspectives are supported`

### Documentation Debt
- REQUIREMENTS.md: 46/48 checkboxes still unchecked despite all being code-verified
- 28 requirements missing from SUMMARY.md frontmatter `requirements_completed` fields
- Phase 40 VERIFICATION.md references stale constant name (`INVALID_SYSTEM_LOCATION` vs `RESERVED_PREFIX`)
- Phase 39 SUMMARY.md describes individual constants that became dict-based implementation

### Deferred Work (from retrospective)
- Golden master re-capture needed after Phase 42 mapper rewrites — blocked on human-only GOLD-01 rule
- Manual requirement checkboxes drift systemically — consider dropping checkboxes entirely in favor of automated enforcement

### Lessons Learned
- "Eliminate null" is bigger than it looks — null appeared in write fields, read output, filter schemas, and availability lists. Each surface needed its own elimination strategy
- Cross-path equivalence tests pay compound dividends — Phase 42's mapper rewrites caught 3 regressions during development
- Late-discovered requirements are fine when scoped — Phase 44 was a clean addition that completed the "null elimination" theme

---

## 7. Getting Started

- **Run the project:** `uv sync` to install, then configure Claude Desktop with the MCP server
- **Run tests:** `uv run pytest` (2,041 tests at milestone end, ~98% coverage)
- **Key directories:**
  - `src/omnifocus_operator/` — main source (models, service, repository, server)
  - `src/omnifocus_operator/service/` — service package (Resolver, DomainLogic, PayloadBuilder, orchestrator)
  - `src/omnifocus_operator/contracts/` — per-use-case contract packages (list/, add/, edit/)
  - `src/omnifocus_operator/agent_messages/` — centralized descriptions and warning strings
  - `src/omnifocus_operator/config.py` — system location constants (`$inbox`, `SYSTEM_LOCATIONS`)
  - `tests/doubles/` — InMemoryBridge, StubBridge, SimulatorBridge
- **Where to look first:**
  - `src/omnifocus_operator/server.py` — MCP tool registration (11 tools)
  - `src/omnifocus_operator/service/orchestrator.py` — service orchestration
  - `src/omnifocus_operator/models/` — core domain models (Task, Project, Tag, Folder)
  - `src/omnifocus_operator/config.py` — `SYSTEM_LOCATIONS` dict, `$inbox` constant
  - `src/omnifocus_operator/service/resolver.py` — name resolution and system location detection
- **Dev commands:** Always use `uv run` — never bare `pytest` or `python`

---

## Stats

- **Timeline:** 2026-04-05 -> 2026-04-07 (3 days)
- **Phases:** 6 / 6 complete
- **Plans:** 15 executed
- **Commits:** 204
- **Files changed:** 312 (+22,889 / -2,353)
- **Tests:** 1,528 -> 1,693 pytest (+165 tests)
- **Contributors:** Flo Kempenich
