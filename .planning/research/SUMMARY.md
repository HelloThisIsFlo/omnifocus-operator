# Project Research Summary

**Project:** OmniFocus Operator v1.2.3 — Repetition Rule Write Support
**Domain:** Structured recurrence model + read/write integration for OmniFocus MCP server
**Researched:** 2026-03-27
**Confidence:** HIGH

## Executive Summary

This milestone adds structured repetition rule read/write to an existing, well-architected MCP server. The work naturally splits into two ordered phases: a read model rewrite (replacing raw `ruleString` with a structured `Frequency` discriminated union) and a write model + bridge pipeline. Phase 1 is a breaking internal change that ripples across 56+ test files and both read paths (SQLite + bridge). Phase 2 slots cleanly into existing patterns (`PatchOrClear`, `DomainLogic`, `PayloadBuilder`). Zero new runtime dependencies are needed — the spike-validated custom RRULE parser (~200 lines, 79 tests) is directly portable.

The recommended approach: port the spike RRULE utilities to a standalone `rrule/` package, rewrite the read model first (letting Pydantic validation errors guide the cascade), then build the write model on top. Pydantic v2 discriminated unions with `extra="forbid"` give type-specific field validation for free, matching the existing `CommandModel` patterns exactly.

The key risks are concentrated in Phase 1: the BYDAY positional prefix form (`BYDAY=-1SA`) will crash the parser on real OmniFocus data if not handled, and the `schedule` field (3 values) must be derived from two SQLite columns (`scheduleType` + `catchUpAutomatically`). Silent data corruption is the failure mode — wrong schedule type means tasks repeat without catch-up when they should, or vice versa, with no error surfaced.

## Key Findings

### Recommended Stack

Zero new dependencies. Everything builds on existing infrastructure: Pydantic v2.12.5 (discriminated unions + alias_generator verified working), the spike RRULE parser (portable as-is with model type substitution), and the existing `UNSET`/`Patch`/`PatchOrClear` lifecycle pattern. The custom parser wins over `python-dateutil` on every dimension relevant to this use case: scope match, component extraction, string building, OmniFocus-specific subset validation, and zero transitive deps.

**Core technologies:**
- **Custom RRULE parser** (`rrule/parser.py`, ~200 lines) — parse RRULE strings to typed `Frequency`; purpose-built for OmniFocus's RRULE subset, 79 spike tests, directly portable
- **Pydantic v2 discriminated unions** — 8 frequency type variants with `type: Literal[...]` discriminator; `extra="forbid"` gives cross-type field rejection for free
- **Existing `PatchOrClear[T]`** — three-way UNSET/null/value semantics for `repetition_rule` on `EditTaskCommand`; no new infrastructure needed
- **Existing `DomainLogic`** — merge/no-op detection; new `process_repetition()` follows same pattern as `compute_tag_diff`, `process_move`

### Expected Features

**Must have (table stakes):**
- Structured frequency model (not raw RRULE) — every modern task API abstracts RRULE; agents shouldn't construct `FREQ=WEEKLY;BYDAY=MO,WE,FR`
- Create task with repetition rule — can't call it "supported" without the add path
- Edit existing rule (partial update within type) — modify interval without re-sending `onDays`
- Clear repetition rule (`null` clears) — standard across all APIs
- All 3 schedule modes (`regularly`, `regularly_with_catch_up`, `from_completion`)
- Symmetric read/write model — same shape for reads and writes
- Type-specific validation — reject `onDays` on a `daily` frequency
- Educational error messages — consistent with existing `agent_messages` pattern

**Should have (differentiators):**
- Partial update within frequency type — Microsoft Graph requires full resend; we can merge
- No-op detection for repetition — consistent with existing `edit_tasks` no-op pattern
- End condition support (`date` or `occurrences`) — most APIs don't expose this
- Type-change detection with clear error — fail loudly instead of silently producing garbage

**Defer:**
- `minutely`/`hourly` frequency writes — accept on reads, reject on writes (no practical use)
- Project repetition writes — deferred to v1.4.3
- Per-occurrence editing — OmniFocus limitation, out of scope

### Architecture Approach

Repetition rule support integrates at the boundary between the agent-facing structured model and OmniFocus's internal RRULE format. A new standalone `rrule/` package (alongside `models/`, `contracts/`) hosts the parse/build utilities. Both read paths (SQLite `hybrid.py` and bridge `adapter.py`) call `parse_rrule`. The write path calls `build_rrule` in `PayloadBuilder`, producing a flat bridge-ready payload. Merge logic lives in `DomainLogic.process_repetition()`, following the established Method Object pattern.

**Major components:**
1. **`rrule/` package** — standalone parse/build utilities; called by both read paths and the write path; zero import entanglements
2. **`models/common.py` (modified)** — new `RepetitionRule` with structured fields (`frequency`, `schedule`, `based_on`, `end`) replacing `ruleString`; breaking change propagates to `Task` and `Project`
3. **`service/domain.py` (modified)** — `process_repetition()` handles merge logic, type-change detection, no-op detection; synchronous (no async needed — current task already fetched)
4. **`service/payload.py` (modified)** — `PayloadBuilder` expands structured spec to flat bridge fields (`ruleString`, `scheduleType`, `anchorDateKey`, `catchUpAutomatically`)
5. **`contracts/` (modified)** — `EditTaskCommand` gains `PatchOrClear[RepetitionRuleSpec]`; `AddTaskCommand` gains `RepetitionRuleSpec | None`
6. **`bridge/` + `repository/` (modified)** — each read path updated to call `parse_rrule` on inbound RRULE strings

### Critical Pitfalls

1. **BYDAY positional prefix form** (`BYDAY=-1SA`) — crashes the spike parser; RFC 5545 allows integer prefixes on BYDAY values; must be handled in Phase 1; test against all 49 distinct ruleStrings from real data
2. **Breaking change ripple** — replacing `ruleString` with structured fields hits 56+ test files; change the model first, let Pydantic validation errors guide the cascade
3. **Schedule field collapse asymmetry** — `schedule` (3 values) must be derived from two SQLite columns (`scheduleType` + `catchUpAutomatically`); wrong mapping = silent data corruption (tasks repeat without catch-up when they should)
4. **OmniJS `RepetitionRule` immutability** — all properties are read-only; bridge must always construct a new `Task.RepetitionRule(...)` and assign it; partial mutation is silently ignored with no error
5. **`.name` accessor broken on RepetitionRule enums** — `r.scheduleType.name` returns `undefined`; bridge must use `===` comparison against enum constants; the existing `rr()` function already does this correctly — write path must follow the same pattern

## Implications for Roadmap

Based on research, the milestone decomposes into exactly 2 phases with a clear dependency boundary.

### Phase 1: Read Model Rewrite

**Rationale:** The structured frequency model is the foundation for everything else. Write path, command models, merge logic, and bridge handler all depend on having correct `Frequency` types. Phase 1 is independently shippable — read tools work end-to-end with structured output before any write support exists.

**Delivers:** Structured `RepetitionRule` in `get_all`, `get_task`, `get_project` responses; both SQLite and bridge read paths return `frequency`, `schedule`, `based_on`, `end` fields instead of `ruleString`.

**Addresses:** Structured frequency model (table stakes), symmetric read model (first half), all 3 schedule modes (read side).

**Build order:**
1. `rrule/parser.py` — port spike, add BYDAY positional prefix and HOURLY/MINUTELY support
2. New model types — `Frequency` discriminated union, `Schedule`, `BasedOn`, `RepetitionEnd`, new `RepetitionRule`
3. SQLite read path (`hybrid.py::_build_repetition_rule`) — derive 3-value `schedule` from two columns
4. Bridge read path (`adapter.py::_adapt_repetition_rule`)
5. Update test fixtures + golden master re-capture (GOLD-01)

**Must avoid:** Pitfall 1 (BYDAY prefix), Pitfall 2 (breaking change ripple), Pitfall 8 (HOURLY missing from parser), Pitfall 12 (SQLite schedule collapse)

### Phase 2: Write Model + Service + Bridge

**Rationale:** Depends on Phase 1's `Frequency` types. Slots cleanly into existing patterns — no new infrastructure, just new fields on existing models and a new pipeline step.

**Delivers:** `add_tasks` and `edit_tasks` accept `repetitionRule` field; partial updates within same frequency type; clear rule via `null`; no-op detection; educational warnings.

**Build order:**
1. `rrule/builder.py` — port spike; round-trip validation with parser
2. Command models — `RepetitionRuleSpec` on `EditTaskCommand` (`PatchOrClear`) and `AddTaskCommand` (optional)
3. RepoPayload models — flat RRULE fields on both payload types
4. `service/domain.py::process_repetition()` — merge logic, no-op detection
5. `service/payload.py` — `build_edit`/`build_add` gain repetition handling
6. Pipeline wiring — `_process_repetition()` step in both pipelines
7. `InMemoryBridge` — handle repetition params in `_handle_edit_task` and `_handle_add_task`
8. `bridge.js` — construct new `Task.RepetitionRule(...)` for writes (always new, never mutate)
9. Golden master — new scenarios for set/modify/clear repetition rule (GOLD-01)
10. Tool descriptions — update `add_tasks` and `edit_tasks` docstrings

**Must avoid:** Pitfall 4 (OmniJS immutability), Pitfall 5 (.name accessor), Pitfall 3 (schedule decomposition), Pitfall 6 (nested merge semantics), Pitfall 11 (bridge expects flat payload)

### Phase Ordering Rationale

- Parser must precede all other work — both read paths and the builder depend on it
- Read model must be complete before write model — command/payload types reference `Frequency` from models
- `DomainLogic.process_repetition()` requires both parser (read current state) and builder (produce output) — naturally lands in Phase 2
- InMemoryBridge and bridge.js are mechanical — last in Phase 2 because they just receive what the service layer sends
- Golden master re-capture required at end of each phase (GOLD-01 constraint)

### Research Flags

Phases with well-documented patterns (skip research-phase):
- **Phase 1:** RRULE parsing is fully spike-validated (79 tests); existing `hybrid.py` and `adapter.py` patterns are clear; no external unknowns
- **Phase 2:** Discriminated union patterns verified working on project's Pydantic version; `PatchOrClear`/`DomainLogic` patterns well-established; bridge write pattern is established

No phases need additional research. All unknowns are resolved: OmniJS API is ground-truth verified (352 real tasks), RRULE parser is spike-validated, Pydantic patterns are confirmed compatible.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Zero new deps; all patterns verified in project's actual environment (Pydantic 2.12.5) |
| Features | HIGH | OmniJS API fully documented in spike; ecosystem comparison grounded in official docs |
| Architecture | HIGH | Based entirely on codebase analysis; component boundaries follow established patterns |
| Pitfalls | HIGH | Ground truth from 352 real OmniFocus tasks (49 distinct ruleStrings); OmniJS API verified empirically |

**Overall confidence:** HIGH

### Gaps to Address

- **BYDAY+BYMONTHDAY combined** (`FREQ=MONTHLY;BYDAY=MO;BYMONTHDAY=15`): valid RFC 5545, unclear if OmniFocus generates it. Recommendation: reject with clear error (conflicting type signals).
- **`from_completion` + `catchUpAutomatically=true`**: technically valid in OmniJS but semantically meaningless. Recommendation: silently normalize to `false` with no user-facing warning.
- **End condition partial update**: `end: null` clears end; `end` omitted preserves it. Must be enumerated explicitly in the merge decision table or it will be missed in implementation.

## Sources

### Primary (HIGH confidence)
- `.research/deep-dives/rrule-validator/rrule_validator.py` + tests — RRULE parser/builder spike, 79 tests, directly portable
- `.research/deep-dives/omnifocus-api-ground-truth/FINDINGS.md` — 352 real OmniFocus tasks, 49 distinct ruleStrings, empirical ground truth
- `.research/deep-dives/repetition-rule/repetition-rule-guide.md` — OmniJS API reference, hand-verified
- [Pydantic v2 Unions docs](https://docs.pydantic.dev/latest/concepts/unions/) — discriminated union patterns, Field(discriminator=...) syntax
- [Microsoft Graph recurrencePattern](https://learn.microsoft.com/en-us/graph/api/resources/recurrencepattern?view=graph-rest-1.0) — ecosystem comparison
- [Todoist REST API v2](https://developer.todoist.com/rest/v2/) — ecosystem comparison
- `.research/updated-spec/MILESTONE-v1.2.3.md` — milestone specification

### Secondary (MEDIUM confidence)
- [python-dateutil issue #938](https://github.com/dateutil/dateutil/issues/938) — UNTIL date handling limitation (confirmed issue, informs library rejection)
- [Microsoft Graph partial update Q&A](https://learn.microsoft.com/en-us/answers/questions/806339/unable-to-patch-a-todo-task-with-a-recurrence-patt) — community reports on partial update behavior
- RFC 5545 (iCalendar RRULE) — BYDAY positional prefix form, verified against real OmniFocus behavior

### Tertiary (LOW confidence)
- [TickTick developer docs](https://developer.ticktick.com/) — limited official API docs; ecosystem comparison only

---
*Research completed: 2026-03-27*
*Ready for roadmap: yes*
