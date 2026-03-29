# Milestone v1.2.3 — Repetition Rule Write Support

**Generated:** 2026-03-29
**Purpose:** Team onboarding and project review

---

## 1. Project Overview

**OmniFocus Operator** is a Python MCP server that exposes OmniFocus (macOS task manager) as structured task infrastructure for AI agents. Reads via SQLite cache (~46ms), writes via OmniJS bridge. Six MCP tools: `get_all`, `get_task`, `get_project`, `get_tag`, `add_tasks`, `edit_tasks`.

**Core value:** Reliable, simple, debuggable access to OmniFocus data for AI agents — executive function infrastructure that works at 7:30am.

**v1.2.3 focus:** Enable agents to set, modify, and remove repetition rules on tasks via structured fields — symmetric read/write model, no raw RRULE strings exposed. No new tools added; existing `add_tasks` and `edit_tasks` gained repetition rule support.

**State:** All 4 phases complete, 39/39 requirements satisfied, milestone shipped.

---

## 2. Architecture & Technical Decisions

- **Custom RRULE parser over python-dateutil** — Purpose-built for OmniFocus RRULE subset, 79 spike tests, zero new runtime deps. Round-trip validated against 15 golden master strings.
  - **Why:** OmniFocus uses a specific RRULE dialect; general parsers add complexity and a dependency for unused features
  - **Phase:** 32 (Read Model Rewrite)

- **Flat Frequency model over discriminated union** — Single model with 6 types and optional specialization fields (`onDays`, `on`, `onDates`) replaces 9-subtype Pydantic discriminated union
  - **Why:** Pydantic requires the discriminator field for union construction, making partial/type-optional edits impossible. Flat model solves merge cleanly
  - **Phase:** 33.1 (Flat Frequency Refactor)

- **FrequencyEditSpec as pure patch container** — No validators on edit spec; validation fires on Frequency construction from merged result
  - **Why:** Keeps edit path flexible — agent sends only changed fields, service merges with existing, validation runs once on the final object
  - **Phase:** 33.1

- **@field_validator over Field(ge=1) for interval/occurrences** — Custom validators produce clean educational errors; Field constraints generate opaque Pydantic messages
  - **Why:** Agent-facing error quality is a core design principle — errors should teach, not confuse
  - **Phase:** 33.1

- **@field_serializer on parent model (RepetitionRule.frequency)** — Avoids JSON Schema erasure from @model_serializer
  - **Why:** MCP clients validate output against JSON Schema; @model_serializer erases type structure to `{"type": "object"}`
  - **Phase:** 32.1 (Output Schema Validation Gap)

- **Output schema regression via jsonschema** — Tests serialize tool output and validate with the same JSON Schema validator MCP clients use, not Pydantic
  - **Why:** Catches @model_serializer schema erasure that Pydantic validation alone would miss — caught a real regression during development
  - **Phase:** 32.1

- **Shared `rrule/` module** — Single `parse_rrule` + `build_rrule` consumed by both SQLite and bridge read paths, plus write path
  - **Why:** No duplicated parsing logic across read paths; write path builds RRULE strings using the same module
  - **Phase:** 32

---

## 3. Phases Delivered

| Phase | Name | Status | One-Liner |
|-------|------|--------|-----------|
| 32 | Read Model Rewrite | Complete | Structured frequency fields replace ruleString on both read paths |
| 32.1 | Output Schema Validation Gap | Complete | Schema-vs-data tests, derive_schedule DRY, WeeklyOnDays split |
| 33 | Write Model, Validation & Bridge | Complete | Full write pipeline for repetition rules with partial updates and educational errors |
| 33.1 | Flat Frequency Refactor | Complete | Flat model replaces 9-subtype union, enabling type-optional edits |

**Execution arc:** Read model (32) → Output safety nets (32.1) → Write pipeline (33) → Architectural refactor when union hit a wall (33.1)

Phase 32.1 was **inserted** after Phase 32 exposed a @model_serializer schema erasure bug — the output schema tests it introduced caught a real regression.

Phase 33.1 was **inserted** after Phase 33 revealed that Pydantic's discriminated union requirement made type-optional edits impossible. The flat Frequency model resolved this cleanly.

---

## 4. Requirements Coverage

**39/39 requirements satisfied** — audit passed with zero gaps.

### Read Model (READ) — 4/4

- ✅ **READ-01**: Structured frequency fields replace ruleString
- ✅ **READ-02**: All 9 frequency types correctly parsed from RRULE strings
- ✅ **READ-03**: Single rrule/ module shared by both read paths
- ✅ **READ-04**: parse_rrule ↔ build_rrule round-trip correctness

### Creation — add_tasks (ADD) — 14/14

- ✅ **ADD-01**: Create task with structured repetition rule (frequency + schedule + basedOn)
- ✅ **ADD-02**: All 9 frequency types supported
- ✅ **ADD-03**: Interval > 1 (e.g., every 2 weeks)
- ✅ **ADD-04**: Weekly onDays with day codes (MO-SU), case-insensitive
- ✅ **ADD-05**: Weekly without onDays repeats every N weeks
- ✅ **ADD-06**: monthly_day_of_week with ordinal/day (e.g., second tuesday)
- ✅ **ADD-07**: monthly_day_in_month with onDates (1-31, -1 for last)
- ✅ **ADD-08**: Empty onDates triggers warning suggesting plain monthly
- ✅ **ADD-09**: All 3 schedule values (regularly, regularly_with_catch_up, from_completion)
- ✅ **ADD-10**: All 3 basedOn values (due_date, defer_date, planned_date)
- ✅ **ADD-11–13**: End by date, end by occurrences, no end (open-ended)
- ✅ **ADD-14**: Interval defaults to 1 when omitted

### Editing — edit_tasks (EDIT) — 16/16

- ✅ **EDIT-01**: Set rule on non-repeating task
- ✅ **EDIT-02**: Remove rule (repetitionRule: null)
- ✅ **EDIT-03**: Omit = no change (UNSET semantics)
- ✅ **EDIT-04–05**: Change schedule/basedOn without resending frequency
- ✅ **EDIT-06–08**: Add/remove/change end conditions
- ✅ **EDIT-09–12**: Same-type merge (interval, onDays, on, onDates preserved)
- ✅ **EDIT-13**: Type change requires full frequency object
- ✅ **EDIT-14**: Incomplete type change → clear error
- ✅ **EDIT-15**: No existing rule + partial → clear error
- ✅ **EDIT-16**: No-op detection with educational warning

### Validation (VALID) — 5/5

- ✅ **VALID-01**: Invalid structures rejected (missing fields, bad enums)
- ✅ **VALID-02**: Type-specific constraints enforced (cross-type field rejection, valid ranges)
- ✅ **VALID-03**: Educational error messages in agent_messages style
- ✅ **VALID-04**: Tool descriptions document schema for LLM construction
- ✅ **VALID-05**: Anchor date warnings (basedOn references unset date)

### Audit Verdict

**PASSED** — 39/39 requirements, 4/4 phases, 5/5 E2E flows, Nyquist compliant.

---

## 5. Key Decisions Log

| # | Decision | Phase | Rationale |
|---|----------|-------|-----------|
| 1 | Custom RRULE parser (no python-dateutil) | 32 | OmniFocus-specific RRULE subset; zero new deps; 79 spike tests proved viability |
| 2 | Shared rrule/ module for both read paths | 32 | Eliminates duplicated parsing logic between SQLite and bridge paths |
| 3 | Output schema tests via jsonschema (not Pydantic) | 32.1 | Same validation MCP clients perform; caught @model_serializer erasure |
| 4 | WeeklyOnDays split from WeeklyFrequency | 32.1 | Clean separation: bare weekly (repeat every N weeks) vs. weekly with specific days |
| 5 | derive_schedule extracted to rrule/schedule.py | 32.1 | DRY — schedule derivation shared by both read paths and write path |
| 6 | 9-subtype discriminated union (Phase 33) | 33 | Initial approach — type safety per frequency type |
| 7 | **Replaced** union with flat Frequency model (6 types) | 33.1 | Union made type-optional edits impossible; flat model with optional fields solves merge |
| 8 | FrequencyEditSpec as pure patch container | 33.1 | No validators on edit — validation deferred to merged Frequency construction |
| 9 | auto_clear_monthly_mutual_exclusion | 33.1 | Operates on merged dict before model validation; prevents stale cross-fields |
| 10 | @field_validator for educational error messages | 33.1 | Field(ge=1) produces opaque errors; custom validators teach agents |

---

## 6. Tech Debt & Deferred Items

### Tech Debt (6 items — all cosmetic/documentation)

- **ROADMAP.md drift**: Phase 33 shows `33-05-PLAN.md` unchecked and status "In Progress" — plan was executed and verified
- **Phase 33 VERIFICATION.md**: Retains `gaps_found` status — gap architecturally closed by Phase 33.1
- **VALID-05 description**: REQUIREMENTS.md narrower than implementation (also covers anchor-date-missing warnings)
- **WeeklyFrequency reference**: Stale docstring comment in `tests/test_service.py:368` — cosmetic
- **SUMMARY frontmatter**: `requirements_completed` underutilized — only 12/39 REQ-IDs populated
- **Human UAT status**: Phase 33 and 33.1 VERIFICATIONs note UAT required — completion status unknown

### Deferred Items

- **Task reactivation** (markIncomplete) — OmniJS API unreliable (deferred since v1.2)
- **Repetition rules on projects** — tasks only for v1.2.3, deferred to v1.4.3

### Lessons Learned (from RETROSPECTIVE.md)

1. **Discriminated unions are poor write models** — Pydantic requires the discriminator for construction, making partial updates impossible
2. **Output schema testing catches real bugs** — jsonschema-vs-data found @model_serializer erasure
3. **Research spikes prevent rework** — RRULE parser spike (79 tests) had zero surprises during execution
4. **UAT finds what unit tests miss** — both BYMONTHDAY multi-value and no-op suppression were real user-observable bugs
5. **Insert phases early when architecture doesn't fit** — Phase 33.1 was cheaper than workarounds

---

## 7. Getting Started

### Run the project

```bash
cd omnifocus-operator
uv sync                    # install dependencies
uv run pytest              # run 1,113 pytest tests + 26 vitest
uv run python -m omnifocus_operator  # start the MCP server
```

### Key directories

```
src/omnifocus_operator/
├── server.py          # MCP server entry point (6 tools)
├── service/           # Service layer (Resolver, DomainLogic, PayloadBuilder, orchestrator)
├── contracts/         # Cross-layer types (Command, RepoPayload, Result models)
├── models/            # Core domain models (Task, Project, Tag, Folder, RepetitionRule, Frequency)
├── rrule/             # RRULE parser/builder (parse_rrule, build_rrule, derive_schedule)
├── repository/        # HybridRepository (SQLite + bridge), BridgeRepository
├── bridge/            # OmniJS bridge protocol and implementations
├── agent_messages/    # Educational warnings and error message constants
├── middleware.py      # ToolLoggingMiddleware (cross-cutting concern)
└── simulator/         # SimulatorBridge for IPC testing
```

### Where to look first (for v1.2.3 specifically)

- **Repetition rule models**: `src/omnifocus_operator/models/repetition_rule.py` — `Frequency` flat model, `RepetitionRule`
- **RRULE parser/builder**: `src/omnifocus_operator/rrule/` — `parse_rrule()`, `build_rrule()`, `derive_schedule()`
- **Write contracts**: `src/omnifocus_operator/contracts/` — `FrequencyAddSpec`, `FrequencyEditSpec`
- **Service merge logic**: `src/omnifocus_operator/service/domain.py` — frequency merge, type-change detection
- **Output schema tests**: `tests/test_output_schema.py` — jsonschema regression guards

### Tests

```bash
uv run pytest                           # all 1,113 tests
uv run pytest tests/test_output_schema.py  # output schema regression
uv run pytest tests/test_rrule/         # RRULE parser/builder tests
uv run pytest -k repetition             # all repetition-related tests
```

### Safety rules

- **SAFE-01/02**: No automated test or agent may touch `RealBridge`. All automated testing uses `InMemoryBridge` or `SimulatorBridge`. UAT scripts in `uat/` are human-initiated only.

---

## Stats

- **Timeline:** 2026-03-26 → 2026-03-29 (3 days)
- **Phases:** 4/4 complete
- **Plans:** 15/15 executed (~7.7 min avg, ~116 min total)
- **Commits:** 212
- **Files changed:** 222 (+89,458 / -1,516)
- **Requirements:** 39/39 satisfied
- **Tests at completion:** 1,113 pytest + 26 vitest = 1,139 total
- **Coverage:** ~94%
- **Contributors:** Flo Kempenich
