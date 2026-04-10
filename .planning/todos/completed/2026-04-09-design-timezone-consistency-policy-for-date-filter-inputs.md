---
created: 2026-04-09T14:21:54.667Z
title: Design timezone consistency policy for date filter inputs
area: contracts
files:
  - src/omnifocus_operator/contracts/use_cases/list/_date_filter.py:52-69
  - src/omnifocus_operator/contracts/use_cases/add/tasks.py:55-69
  - src/omnifocus_operator/contracts/use_cases/edit/tasks.py:72-86
  - src/omnifocus_operator/service/resolve_dates.py:215-246
  - src/omnifocus_operator/service/domain.py
  - tests/test_resolve_dates.py
---

## Problem

The date filter system has no explicit policy on timezone awareness for datetime inputs. The contract validator accepts any valid ISO datetime string — naive or tz-aware — but production code passes a UTC-aware `now` timestamp. When a naive datetime string reaches the resolver and gets compared against tz-aware model fields, Python raises `TypeError: can't compare offset-naive and offset-aware datetimes`.

A defensive fix was applied (WR-01 from Phase 47 code review) that silently inherits `now.tzinfo` when the parsed datetime is naive. This masks the ambiguity instead of surfacing it. A design decision is needed on what the contract should require and how violations should be handled.

## Scenarios where this surfaces

1. **Agent sends full datetime without timezone**: `{before: "2026-04-01T14:00:00"}` — contract validator accepts it (`datetime.fromisoformat()` succeeds), resolver gets a naive datetime, production `now` is UTC-aware → mismatch
2. **Agent sends full datetime with timezone**: `{before: "2026-04-01T14:00:00Z"}` or `{before: "2026-04-01T14:00:00+02:00"}` — works fine, no issue
3. **Agent sends date-only string**: `{before: "2026-04-01"}` — resolver already has explicit tz-inheritance logic for this case (pre-existing design, not from WR-01)
4. **Agent sends "now" literal**: returns `now` directly, always consistent

Scenario 1 is the only problematic case. It's realistic — AI agents commonly emit ISO datetimes without timezone suffixes.

## Current state across the codebase

- **Contract validator** (`_date_filter.py:52-69`): Calls `datetime.fromisoformat(v)` to check validity. Does not inspect `.tzinfo`. Accepts both naive and aware strings.
- **Contract ordering check** (`_date_filter.py:107-117`): `_parse_to_comparable` also uses naive datetimes for before/after ordering validation — internally consistent but disconnected from production's tz-aware context.
- **Resolver** (`resolve_dates.py:215-246`): Three paths for `_parse_absolute_after` / `_parse_absolute_before`:
  - `"now"` → returns `now` (always consistent)
  - Date-only → constructs datetime with `tzinfo=now.tzinfo` (explicit design)
  - Full datetime → `datetime.fromisoformat(value)` + WR-01 defensive fix (the part in question)
- **Production `now`**: Always UTC-aware. Set by the service pipeline in `domain.py`.
- **Test `NOW` fixture** (`test_resolve_dates.py`): Uses naive datetime. The naive-vs-aware mismatch path was never exercised by tests until WR-01 was identified.

## Write side: existing approach

The write contracts (`add_tasks`, `edit_tasks`) use Pydantic's `AwareDatetime` type for all date fields (`due_date`, `defer_date`, `planned_date`). This rejects naive datetimes at the contract boundary — if an agent sends `"2026-04-01T14:00:00"` without a timezone, Pydantic returns a validation error before it reaches the service layer.

This is one opinionated choice. The read/filter side (`_date_filter.py`) took a different approach: `before`/`after` are plain `str` fields with a custom validator that only checks parseability, not timezone awareness. The two sides of the API have divergent policies on the same kind of input.

## Decisions needed

- Unify the timezone policy across read and write contracts, or accept the divergence with explicit rationale
- Review whether `AwareDatetime` is the right choice on the write side too (it's the current policy, but hasn't been explicitly validated as a design decision)
- What should the contract boundary require for `before`/`after` datetime strings? (reject naive? accept and normalize? require explicit timezone?)
- What should the resolver assume about its inputs? (trust the contract? assert? be defensive?)
- Should the defensive WR-01 fix be kept, replaced with a contract-level check, or replaced with an assertion?
- Does the `_parse_to_comparable` ordering check in the contract need to be updated for consistency?
