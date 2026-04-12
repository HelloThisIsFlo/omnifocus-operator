# Milestone v1.3.2 — Date Filtering

**Generated:** 2026-04-12
**Purpose:** Team onboarding and project review

---

## 1. Project Overview

**OmniFocus Operator** is a Python MCP server exposing OmniFocus (macOS task manager) as structured task infrastructure for AI agents. It reads via SQLite cache (~46ms), writes via OmniJS bridge, and provides 11 MCP tools for full task management.

**Core value:** Reliable, simple, debuggable access to OmniFocus data for AI agents — executive function infrastructure that works at 7:30am.

v1.3.2 adds **date filtering** — agents can now filter tasks by any of 7 date dimensions (due, defer, planned, completed, dropped, added, modified) using string shortcuts (`"today"`, `"overdue"`, `"soon"`), shorthand periods (`{last: "2w"}`), or absolute bounds (`{after: "2026-04-01", before: "2026-04-14"}`). The milestone also established the **naive-local datetime contract** and integrated with the **OmniFocus settings API** for user preferences.

All 6 phases complete. 56/56 requirements satisfied. Milestone audit passed.

---

## 2. Architecture & Technical Decisions

- **DateFilter discriminated union** — 4 concrete filter classes (ThisPeriodFilter, LastPeriodFilter, NextPeriodFilter, AbsoluteRangeFilter) with callable `Discriminator` routing. Invalid states unrepresentable at parse time.
  - **Why:** Flat DateFilter initially, refactored in Phase 48. Pydantic's callable discriminator pattern routes input to the correct class without requiring an explicit `type` field. Eliminates runtime `TypeError` from malformed filter shapes.
  - **Phase:** 48

- **Naive-local datetime contract** — All date inputs use `str` type (no `format: "date-time"` in JSON Schema). Aware datetimes silently converted to local. All `now` timestamps use local timezone.
  - **Why:** OmniFocus stores naive local datetimes internally. Server is co-located with OmniFocus on the same Mac. Adding timezone handling would be unnecessary complexity that could cause bugs. Deep-dive research confirmed this.
  - **Phase:** 49

- **OmniFocusPreferences module** — Lazy-loaded singleton reading OmniJS `settings.objectForKey()`, domain-typed output (DueSoonSetting enum, typed default times), factory-default fallback with warning.
  - **Why:** Replaced 3 fragile mechanisms (SQLite plist parsing, `OPERATOR_DUE_SOON_THRESHOLD` env var, hardcoded factory defaults). Single authoritative source for user preferences, matches what users configure in OmniFocus UI.
  - **Phase:** 50

- **Calendar-aware period arithmetic** — `add_duration` helper with day clamping (Jan 31 + 1m → Feb 28). Shared across all duration consumers (`last`/`next` filters, `review_due_within`).
  - **Why:** Naive 30-day/365-day approximation was originally planned but produced incorrect boundaries. Calendar-aware math is worth the complexity for user-facing date ranges.
  - **Phase:** 45 (resolver), upgraded in 46-05

- **Field-aware date normalization** — `normalize_date_input(value, default_time)` applies per-field default times from preferences (dueDate → DefaultDueTime, deferDate → DefaultStartTime, plannedDate → DefaultPlannedTime).
  - **Why:** Matches OmniFocus UI behavior. When a user types a date-only value, each field gets the same default time OmniFocus would apply. Domain-layer product decision per architecture litmus test.
  - **Phase:** 50

- **Lifecycle auto-include** — Using `completed` or `dropped` date filter automatically includes those lifecycle states in results without the agent setting availability.
  - **Why:** Agent intent is clear — if they filter by completion date, they want completed tasks. Removes a common source of empty-result confusion.
  - **Phase:** 46

- **DueSoonSetting enum** — 7-member enum with `.days` and `.calendar_aligned` domain properties. Replaces raw SQLite interval/granularity integers.
  - **Why:** Consumers see domain concepts, never leaked storage format. Clean domain API.
  - **Phase:** 45 (model), 50 (wired to preferences)

- **pydantic-settings consolidation** — All 7 `OPERATOR_*` env vars consolidated from 5 scattered files into single `BaseSettings` class with `get_settings()` singleton.
  - **Why:** Single source of truth for configuration. Pydantic-settings provides type validation, env var reading, and default values in one place.
  - **Phase:** 45-05

---

## 3. Phases Delivered

| Phase | Name | Status | One-Liner |
|-------|------|--------|-----------|
| 45 | Date Models & Resolution | Complete | DateFilter contract, StrEnum shortcuts, pure resolver with calendar-aware arithmetic |
| 46 | Pipeline & Query Paths | Complete | Service pipeline integration, SQL date predicates, bridge in-memory filtering |
| 47 | Cross-Path Equivalence & Breaking Changes | Complete | AvailabilityFilter trimming, lifecycle shortcut rename, defer hints, cross-path tests |
| 48 | Discriminated Union Refactor | Complete | Replace flat DateFilter with 4-model discriminated union, isinstance dispatch |
| 49 | Naive-Local DateTime Contract | Complete | All date inputs use str type, aware→local conversion, local_now() |
| 50 | OmniFocus Settings API | Complete | Bridge get_settings command, OmniFocusPreferences module, field-aware default times |

---

## 4. Requirements Coverage

**56 active requirements, all satisfied.**

### Date Filter Models & Validation (7/7)
- DATE-01: 7-field string/object union type
- DATE-02: Shorthand `this`/`last`/`next` with `[N]unit` duration
- DATE-03: Absolute `before`/`after` with ISO8601, date-only, or `"now"`
- DATE-04: Shorthand and absolute mutually exclusive per field
- DATE-05: Zero/negative count educational error
- DATE-06: Field-specific shortcuts (`"overdue"`/`"soon"` → due only, `"any"` → completed/dropped only)
- DATE-09: `after` must be earlier than `before`

### Date Resolution (10/10)
- RESOLVE-01 through RESOLVE-06: Calendar-aligned periods, `"now"` consistency, configurable week start
- RESOLVE-07 (revised): Calendar-aware arithmetic with day clamping
- RESOLVE-08 through RESOLVE-10: Date-only boundary handling, inclusive ranges
- RESOLVE-11 (revised): `"overdue"` via timestamp comparison, not pre-computed columns

### Query Execution (10/10)
- EXEC-01: SQL predicates on effective CF epoch columns
- EXEC-02: Bridge in-memory filtering with shared resolution
- EXEC-03/04: Lifecycle auto-include for completed/dropped
- EXEC-05/06: `"any"` includes all tasks in lifecycle state
- EXEC-07: NULL dates excluded from matches
- EXEC-09: Date filters AND-combine with each other and base filters
- EXEC-10/11: Cross-path equivalence with inherited effective dates

### Breaking Changes & Agent Guidance (8/8)
- BREAK-01: `urgency` removed with educational error
- BREAK-02: `completed` boolean rejected → date filter guidance
- BREAK-03: `COMPLETED`/`DROPPED` removed from AvailabilityFilter
- BREAK-04/05: Defer filter hints (future → `"blocked"`, past → `"available"`)
- BREAK-06/08: `availability: "any"`/`"all"` educational errors
- BREAK-07: Tool descriptions updated

### Naive-Local DateTime (7/7)
- LOCAL-01: `str` type, no `format: "date-time"` in schema
- LOCAL-02: Naive strings accepted as local time
- LOCAL-03: Aware strings silently converted to local
- LOCAL-05: All `now` timestamps use local timezone
- LOCAL-06: Normalization is domain-layer product decision
- LOCAL-07: Descriptions frame dates as naive local
- LOCAL-08: architecture.md documents the principle

### OmniFocus Preferences (13/13)
- PREF-01: Bridge `get_settings` via OmniJS
- PREF-02: Lazy load, domain-typed, cached for server lifetime
- PREF-03: Factory-default fallback with warning
- PREF-04/05/06: Date-only enrichment per field (due→DefaultDueTime, defer→DefaultStartTime, planned→DefaultPlannedTime)
- PREF-07: Field-aware normalization in domain.py
- PREF-08/09: DueSoon from preferences, TWO_DAYS fallback
- PREF-10: `get_due_soon_setting()` removed from Repository protocol
- PREF-11/12: Legacy SQLite plist + env var deleted
- PREF-13: Tool descriptions updated

### Scoped Out
- DATE-07, DATE-08: `"none"` on always-valued fields (niche)
- EXEC-08: `"none"` IS NULL filtering (deferred)
- RESOLVE-12: Superseded by PREF-08/09
- LOCAL-04: Superseded by PREF-04/05/06

### Audit Verdict
**Passed** — 56/56 requirements, 6/6 phases, 18/18 integration points, 3/3 E2E flows, 6/6 Nyquist compliant. Human verification confirmed for Phase 50 (live OmniFocus tests).

---

## 5. Key Decisions Log

| Decision | Phase | Rationale |
|----------|-------|-----------|
| Callable Discriminator for DateFilter union routing | 48 | First usage of Pydantic's `Discriminator(callable)` — routes input to correct class without explicit `type` field |
| `local_now()` as centralized local timezone source | 49 | Single import for all timezone-aware "now" usage, lives in `config.py` |
| OmniFocusPreferences via bridge OmniJS API (not SQLite) | 50 | SQLite plist parsing was fragile (binary plist, schema assumptions). OmniJS API is the official interface |
| Field-aware `normalize_date_input(value, default_time)` | 50 | Domain layer product decision — each date field gets its configured default time |
| `add_duration` for calendar-aware arithmetic | 45-46 | Shared helper prevents divergence between `last`/`next` filters and `review_due_within` |
| Timestamp comparison for "overdue"/"soon" (not pre-computed columns) | 46 | Pre-computed `dueSoon` column excludes overdue tasks — doesn't match expected behavior |
| Pre-release = no migration burden | 47 | `urgency` and `completed: true` simply removed from schema. No backward compatibility needed |
| Naive-local datetime contract | 49 | Deep-dive research proved: OmniFocus stores naive local, server co-located, TZ conversion is unnecessary complexity |
| pydantic-settings for config consolidation | 45-05 | 7 env vars scattered across 5 files → single BaseSettings class |
| ResolvedDateBounds rich type | 46-05 | Type-safe `*_after`/`*_before` kwargs replace fragile tuple unpacking |

---

## 6. Tech Debt & Deferred Items

### Remaining Tech Debt
- Pre-existing `TODO(v1.5)` comment in `descriptions.py` — v1.5 scope, not actionable now

### Deferred Features
- `count_tasks` date filters (COUNT-01) — future milestone
- `"none"` IS NULL filtering — scoped out, add if requested
- Non-local timezone support — naive-local is correct for co-located server

### Lessons from Retrospective
- **Deep-dive research changes scope for the better** — timezone research proved naive-local correct and surfaced the OmniFocus settings API opportunity
- **Make invalid states unrepresentable** — discriminated union replaced runtime errors with parse-time validation
- **Single source of truth for settings** — OmniFocus settings API replaced env var + SQLite plist + factory defaults
- **Calendar-aware arithmetic is worth the complexity** — `{last: "1m"}` on Jan 31 → Feb 28, not Jan 1
- **RESOLVE-12 went through 3 spec changes** (pre-computed columns → SQLite plist → OmniJS API) — original scope didn't anticipate the settings API discovery

### Closed During Milestone
- INT-01: `get_warnings()` not called from service pipelines — fixed via quick task
- WR-02: `repository._bridge` private access — fixed (bridge passed directly)

---

## 7. Getting Started

- **Run the project:** `uv sync && uv run python -m omnifocus_operator` (or via MCP client config)
- **Run tests:** `uv run pytest` (2,041 pytest tests at milestone end)
- **Key directories:**
  - `src/omnifocus_operator/` — main package
  - `src/omnifocus_operator/service/` — service layer (Resolver, DomainLogic, PayloadBuilder, orchestrator)
  - `src/omnifocus_operator/contracts/` — per-use-case contract models
  - `src/omnifocus_operator/models/` — core Pydantic models
  - `src/omnifocus_operator/repository/` — HybridRepository (SQLite + bridge)
  - `src/omnifocus_operator/agent_messages/` — all agent-facing strings + descriptions
  - `tests/doubles/` — test doubles (InMemoryBridge, StubBridge)
- **Date filtering entry points:**
  - Contract: `contracts/use_cases/list/query.py` — `ListTasksQuery` with 7 date filter fields
  - Models: `contracts/use_cases/list/date_filter.py` — discriminated union (4 filter classes)
  - Resolver: `service/resolve_dates.py` — `resolve_date_filter()` pure function
  - Preferences: `service/preferences.py` — `OmniFocusPreferences` module
  - SQL: `repository/query_builder.py` — date predicates on effective CF epoch columns
- **Where to look first:** `server.py` (MCP tool registration), `service/orchestrator.py` (pipeline dispatch)

---

## Stats

- **Timeline:** 2026-04-07 → 2026-04-11 (5 days)
- **Phases:** 6/6 complete
- **Plans:** 23 executed
- **Commits:** 362
- **Files changed:** 246 (+39,891 / -2,237)
- **Tests at completion:** 1,977 (1,951 pytest + 26 vitest)
- **Coverage:** ~94%
- **Contributors:** Flo Kempenich
