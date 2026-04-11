# Quick Task 260411-fv2: Make date filter before/after bounds inclusive for datetime - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Task Boundary

Bump datetime `before` bounds by +1 minute in `_parse_absolute_before` so the SQL `<` comparison includes the agent's boundary value. Date-only bounds already use +1 day — this extends the same pattern to datetimes.

</domain>

<decisions>
## Implementation Decisions

### Bump increment size
- **+1 minute** for datetime `before` bounds
- Matches OmniFocus scheduling granularity (tasks aren't scheduled to the second)
- Consistent with the todo's own suggestion

### `after` bound treatment
- **Leave as-is** — SQL `>=` is already inclusive, no code change needed

### Docstring alignment
- **Already done** — user updated `ResolvedDateBounds` docstring to explain the two-layer contract:
  - Agent: inclusive-inclusive
  - Repo: half-open (`>= after`, `< before`)
  - Resolution step pre-bumps `before` to bridge the gap
- This is committed and not part of the remaining work

</decisions>

<specifics>
## Specific Ideas

- Fix lives in `_parse_absolute_before` in `resolve_dates.py`
- Add `+ timedelta(minutes=1)` for datetime strings (where `T` is present)
- Existing date-only path (`+ timedelta(days=1)`) unchanged

</specifics>
