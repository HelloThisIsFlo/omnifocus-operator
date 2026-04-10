---
phase: 49-implement-naive-local-datetime-contract-for-all-date-inputs
verified: 2026-04-10T22:30:00Z
status: passed
score: 8/8
overrides_applied: 0
gaps: []
---

# Phase 49: Naive-Local DateTime Contract — Verification Report

**Phase Goal:** All date inputs (write fields + filter bounds) use naive-local datetime as the preferred format, aware inputs are silently converted to local, and `now` timestamps align with local timezone — making the API match OmniFocus's naive-local storage model
**Verified:** 2026-04-10T22:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Write-side date fields use `str` type — no `format: "date-time"` in JSON Schema | VERIFIED | `AddTaskCommand.due_date: str | None`, `EditTaskCommand.due_date: PatchOrClear[str]`. `json.dumps(AddTaskCommand.model_json_schema())` contains no `"date-time"`. EditTaskCommand schema also confirmed clean. |
| 2 | Naive datetime strings accepted on all date inputs; aware strings silently converted to naive local | VERIFIED | `AddTaskCommand(name='test', due_date='2026-07-15T17:00:00')` validates. `normalize_date_input('2026-07-15T16:00:00Z')` returns naive local string (no Z/offset). All 3 formats validated programmatically. |
| 3 | Date-only strings on write side intercepted and converted to midnight local before bridge | VERIFIED | `normalize_date_input('2026-07-15')` returns `'2026-07-15T00:00:00'`. Called in `_AddTaskPipeline._normalize_dates()` and `_EditTaskPipeline._normalize_dates()` before payload construction. |
| 4 | Read-side `_DateBound` uses `str`, `_reject_naive_datetime` removed | VERIFIED | `_DateBound = Annotated[Literal["now"] | str, BeforeValidator(_validate_date_bound_string)]`. `grep -rn "_reject_naive_datetime"` returns no matches in `src/`. |
| 5 | All `now` timestamps in service layer use local timezone — "today" and period boundaries align with local calendar | VERIFIED | `service.py` imports and calls `local_now()` in both `_ListTasksPipeline._resolve_date_filters()` and `_ListProjectsPipeline._build_repo_query()`. No `datetime.now(UTC)` remaining in `service.py`. |
| 6 | Local timezone choice centralized in a named helper function with explanatory docstring | VERIFIED | `local_now()` in `config.py` lines 117–131. Full docstring explains OmniFocus naive-local storage rationale, tz-aware return type reason, and evidence reference. |
| 7 | Write tool descriptions and examples use naive-local format; brief note about timezone acceptance | VERIFIED | `DATE_EXAMPLE = "2026-03-15T17:00:00"` (no Z). `ADD_TASKS_TOOL_DOC` contains "All dates are local time (no timezone needed). Timezone offsets also accepted". `EDIT_TASKS_TOOL_DOC` contains "Dates are local time. Offsets accepted and converted." `ABSOLUTE_RANGE_BEFORE/AFTER` both say "Dates are local time." |
| 8 | `architecture.md` documents the naive-local principle with rationale | VERIFIED | Section "Naive-Local DateTime Principle" at line 245 of `docs/architecture.md`. Contains OmniFocus storage rationale, evidence reference (430 tasks, deep-dive), contract table (naive/aware/date-only behavior), and architecture breakdown mentioning `normalize_date_input()` and `local_now()`. |

**Score:** 8/8 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/omnifocus_operator/config.py` | `local_now()` helper function | VERIFIED | `def local_now() -> datetime:` at line 117. Returns `datetime.now().astimezone()` (tz-aware). |
| `src/omnifocus_operator/contracts/use_cases/add/tasks.py` | `str`-typed date fields on AddTaskCommand | VERIFIED | `due_date: str | None`, `defer_date: str | None`, `planned_date: str | None`. `_validate_date_string` + `field_validator` on all 3. No `AwareDatetime` import. |
| `src/omnifocus_operator/contracts/use_cases/edit/tasks.py` | `PatchOrClear[str]` date fields on EditTaskCommand | VERIFIED | `due_date: PatchOrClear[str]`, `defer_date: PatchOrClear[str]`, `planned_date: PatchOrClear[str]`. No `AwareDatetime` import. |
| `src/omnifocus_operator/contracts/use_cases/list/_date_filter.py` | `str`-typed `_DateBound`, no `_reject_naive_datetime` | VERIFIED | `_DateBound = Annotated[Literal["now"] | str, BeforeValidator(_validate_date_bound_string)]`. `_reject_naive_datetime` and `_to_naive` absent. No `AwareDatetime` import. |
| `src/omnifocus_operator/agent_messages/descriptions.py` | Updated `DATE_EXAMPLE` and local-time notes | VERIFIED | `DATE_EXAMPLE = "2026-03-15T17:00:00"`. Tool docs and bound descriptions all updated. |
| `src/omnifocus_operator/service/domain.py` | `normalize_date_input()` + updated `_to_utc_ts` | VERIFIED | `def normalize_date_input(value: str) -> str:` at line 123. `_to_utc_ts` handles naive strings via `dt.astimezone()` without assertion. |
| `src/omnifocus_operator/service/payload.py` | String passthrough (no `.isoformat()`) | VERIFIED | `_add_dates_if_set` passes `value` directly (`kwargs[field] = value`). `build_add` does `kwargs["due_date"] = command.due_date`. No `.isoformat()` calls anywhere in file. |
| `src/omnifocus_operator/service/resolve_dates.py` | String parsing in `_parse_absolute_after/before` | VERIFIED | Both functions accept `str`, use `datetime.fromisoformat(value)`. Date-only (no "T"): start-of-day. Naive: inherits `now.tzinfo`. Aware: used as-is. "now" returns `now`. No old `isinstance(value, date)` pattern. |
| `src/omnifocus_operator/service/service.py` | `local_now()` usage | VERIFIED | Imports `local_now` from `config`. Called in `_ListTasksPipeline._resolve_date_filters()` and `_ListProjectsPipeline._build_repo_query()`. Both add/edit pipelines call `_normalize_dates()` before payload build. |
| `docs/architecture.md` | Naive-Local DateTime Principle section | VERIFIED | Section present at line 245. Includes rationale, evidence ref, contract table, architecture breakdown. |
| `tests/test_contracts_field_constraints.py` | `TestDateFieldStrType` class | VERIFIED | Class at line 154. 11 tests pass. |
| `tests/test_output_schema.py` | `TestWriteSchemaNoDateTimeFormat` class | VERIFIED | Class at line 658. 2 tests pass, guard against `format: "date-time"` in write schemas. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `contracts/use_cases/add/tasks.py` | `agent_messages/descriptions.py` | `DATE_EXAMPLE` import | VERIFIED | `from omnifocus_operator.agent_messages.descriptions import ... DATE_EXAMPLE`. Field uses `examples=[DATE_EXAMPLE]`. |
| `service/service.py` | `config.py` | `local_now` import | VERIFIED | `from omnifocus_operator.config import get_week_start, local_now`. Called in both list pipelines. |
| `service/domain.py` | `service/service.py` | `normalize_date_input` called before payload build | VERIFIED | `from omnifocus_operator.service.domain import DomainLogic, normalize_date_input`. Called in `_normalize_dates()` in both add/edit pipelines. |
| `service/service.py:_resolve_date_filters` | `service/resolve_dates.py` | `now` parameter is tz-aware local | VERIFIED | `self._now = local_now()` in `_resolve_date_filters`. This local-aware `now` flows to `resolve_date_filter(...)` and into `_parse_absolute_after/before`. |

---

### Data-Flow Trace (Level 4)

Not applicable — this phase is contract/service layer (not UI rendering). Key data flows verified via behavioral spot-checks below.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Naive datetime accepted on AddTaskCommand | `AddTaskCommand(name='test', due_date='2026-07-15T17:00:00')` | `cmd.due_date == '2026-07-15T17:00:00'` | PASS |
| Aware datetime accepted on AddTaskCommand | `AddTaskCommand(name='test', due_date='2026-07-15T17:00:00Z')` | accepted without error | PASS |
| Date-only accepted on AddTaskCommand | `AddTaskCommand(name='test', due_date='2026-07-15')` | `cmd.due_date == '2026-07-15'` | PASS |
| Invalid date rejected | `AddTaskCommand(name='test', due_date='not-a-date')` | raises `ValidationError` | PASS |
| JSON Schema has no format:date-time | `json.dumps(AddTaskCommand.model_json_schema())` | `'date-time' not in result` | PASS |
| `local_now()` returns tz-aware | `local_now().tzinfo is not None` | True | PASS |
| `normalize_date_input` date-only | `normalize_date_input('2026-07-15')` | `'2026-07-15T00:00:00'` | PASS |
| `normalize_date_input` naive passthrough | `normalize_date_input('2026-07-15T17:00:00')` | `'2026-07-15T17:00:00'` | PASS |
| `normalize_date_input` aware->local | `normalize_date_input('2026-07-15T16:00:00Z')` | naive string (no Z or offset) | PASS |
| `_to_utc_ts` naive string | `_to_utc_ts('2026-07-15T17:00:00')` | returns `float` (no assertion error) | PASS |
| `_to_utc_ts` None | `_to_utc_ts(None)` | `None` | PASS |
| `_parse_absolute_after` date-only | `_parse_absolute_after('2026-07-15', now_bst)` | `datetime(2026, 7, 15, 0, 0, 0, tzinfo=bst)` | PASS |
| `_parse_absolute_before` date-only | `_parse_absolute_before('2026-07-15', now_bst)` | `datetime(2026, 7, 16, 0, 0, 0, tzinfo=bst)` | PASS |
| `_parse_absolute_after` naive | `_parse_absolute_after('2026-07-15T17:00:00', now_bst)` | datetime with bst tzinfo | PASS |
| `_parse_absolute_after` 'now' | `_parse_absolute_after('now', now_bst)` | returns `now_bst` | PASS |
| Full test suite | `uv run pytest tests/ --no-cov -q` | 1952 passed, 0 failed | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| LOCAL-01 | 49-01 | Write-side date fields and read-side filter bounds use `str` type — no `format: "date-time"` in JSON Schema | SATISFIED | `str | None` on AddTaskCommand, `PatchOrClear[str]` on EditTaskCommand, `Literal["now"] | str` on `_DateBound`. Schema verified programmatically. |
| LOCAL-02 | 49-01 | Naive datetime strings accepted and treated as local time on all date inputs | SATISFIED | `_validate_date_string` uses `fromisoformat` — accepts naive. Contract tests `TestDateFieldStrType` verify explicitly. |
| LOCAL-03 | 49-02 | Aware datetime strings accepted on all date inputs, silently converted to naive local time | SATISFIED | `normalize_date_input` converts aware via `dt.astimezone().replace(tzinfo=None).isoformat()`. Called before payload build in both write pipelines. |
| LOCAL-04 | 49-02 | Date-only strings on write-side intercepted, midnight local appended before bridge | SATISFIED | `normalize_date_input('2026-07-15')` returns `'2026-07-15T00:00:00'`. Verified programmatically. |
| LOCAL-05 | 49-02 | All `now` timestamps use local timezone — "today" and period boundaries align with local calendar | SATISFIED | `local_now()` used in `_ListTasksPipeline._resolve_date_filters` and `_ListProjectsPipeline._build_repo_query`. No `datetime.now(UTC)` in service.py. |
| LOCAL-06 | 49-02 | Aware→local normalization is a domain-layer product decision | SATISFIED | `normalize_date_input` in `domain.py`. Docstring says "This is a product decision". Contract layer only validates syntax; domain interprets semantics. |
| LOCAL-07 | 49-01 | Write tool descriptions and JSON Schema examples frame dates as naive local time | SATISFIED | `DATE_EXAMPLE = "2026-03-15T17:00:00"`. ADD/EDIT tool docs say "local time". Bound descriptions updated. |
| LOCAL-08 | 49-03 | `architecture.md` documents naive-local principle with rationale | SATISFIED | Section "Naive-Local DateTime Principle" at line 245 with full rationale, evidence, contract table. |

**All 8 LOCAL requirements satisfied.**

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `tests/test_descriptions.py` (pre-existing) | — | `test_tool_descriptions_within_client_byte_limit` — edit_tasks description noted as 48 bytes over limit in SUMMARY | Info | Pre-existing issue, not introduced by Phase 49. Test passes in full suite run (1952 passed). No impact on phase goal. |

No blockers or warnings from Phase 49 changes.

---

### Human Verification Required

None. All success criteria are verifiable programmatically and confirmed above.

---

## Gaps Summary

None. All 8 roadmap success criteria verified. All must-haves from all three plans confirmed in codebase. Full test suite passes (1952/1952). Dead code confirmed absent. Key links confirmed wired.

---

_Verified: 2026-04-10T22:30:00Z_
_Verifier: Claude (gsd-verifier)_
