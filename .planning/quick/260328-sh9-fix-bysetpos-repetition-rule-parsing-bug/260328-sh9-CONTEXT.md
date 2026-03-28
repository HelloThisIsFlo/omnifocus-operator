# Quick Task 260328-sh9: Fix BYSETPOS repetition rule parsing bug - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Task Boundary

Fix the BYSETPOS rejection in the rrule parser (D-05). The parser currently rejects ALL BYSETPOS rules, but OmniFocus produces BYSETPOS for multi-day positional rules (weekday/weekend day picks in the monthly repeat UI). This is a read-side parser fix only.

The full BYSETPOS matrix is 2 day groups × 6 ordinals = 12 combinations:
- `BYDAY=MO,TU,WE,TH,FR;BYSETPOS=N` → Nth weekday
- `BYDAY=SU,SA;BYSETPOS=N` → Nth weekend day
- Ordinals: 1–5 and -1 (last)

</domain>

<decisions>
## Implementation Decisions

### Day Group Values
- Use `weekday` and `weekend_day` as values in the `on` dict
- Same shape as single-day: `{"second": "weekday"}`, `{"first": "weekend_day"}`
- Consistent with existing `{"second": "tuesday"}` pattern

### BYSETPOS Scope
- Only recognize the two known OmniFocus day groups:
  - `MO,TU,WE,TH,FR` → weekday
  - `SU,SA` (or `SA,SU`) → weekend_day
- Unknown multi-day BYSETPOS combos → educational ValueError
- Single-day BYDAY stays prefix-only (no change needed)

### Ordinal Support
- Support all 6 ordinals (1st–5th + last) for BYSETPOS
- Reuse existing `_POS_TO_ORDINAL` map — zero new ordinal code needed
- OmniFocus UI likely offers all 6 for weekday/weekend_day just like single days

</decisions>

<specifics>
## Specific Ideas

- Remove `_validate_no_bysetpos()` blanket rejection
- Route BYSETPOS rules through a new `_parse_monthly_bysetpos()` helper
- Map BYDAY day sets to group names via lookup (frozenset matching)
- Test cases: both day groups × representative ordinals, unknown combos → error

</specifics>

<canonical_refs>
## Canonical References

- Todo: `.planning/todos/pending/2026-03-28-fix-repetition-rule-parsing-bug.md` — root cause analysis with real database evidence
- Parser: `src/omnifocus_operator/rrule/parser.py` — current implementation with `_validate_no_bysetpos()`
- Model: `src/omnifocus_operator/models/repetition_rule.py` — `MonthlyDayOfWeekFrequency` with `on: dict[str, str]`

</canonical_refs>
