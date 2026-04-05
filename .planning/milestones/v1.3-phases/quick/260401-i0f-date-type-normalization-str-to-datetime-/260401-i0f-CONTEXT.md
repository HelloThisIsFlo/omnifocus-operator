# Quick Task 260401-i0f: EndByDate.date — str → date normalization - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Task Boundary

Change `EndByDate.date` from `str` to Python's `datetime.date`. This is the only model-layer date field still stored as a bare string — all other dates already use `AwareDatetime`. The OmniFocus UI only allows picking a calendar date (no time) for "end repeat by," so the contract should reflect that.

</domain>

<decisions>
## Implementation Decisions

### Scope — Single field, not cross-cutting
- Original ticket framed as "all date fields" but audit showed only `EndByDate.date` is `str` in models
- The 6 `*RepoPayload` str fields are deliberately `str` at the bridge boundary — untouched
- All 15 other model-layer date fields already use `AwareDatetime`

### Type choice — `datetime.date`, not `AwareDatetime`
- OmniFocus UI only lets you pick a calendar date for "end repeat by" — no time component
- `datetime.date` is semantically correct; `AwareDatetime` would mislead agents into thinking time matters
- JSON Schema auto-emits `"format": "date"` — agents see it's a date

### Output format — Clean break
- Output changes from `"2026-12-31T00:00:00Z"` to `"2026-12-31"`
- No backwards compatibility needed — project is in development, single user

### Input validation — Strict date only
- Only accept `"2026-12-31"` format (ISO date)
- If agent sends datetime, Pydantic rejects it — clean contract, no silent coercion

### RRULE builder — Internal conversion
- Builder converts `date` → `YYYYMMDDT000000Z` format internally
- The `T000000Z` is an implementation detail of the RRULE spec, not a user choice

### Domain code — Simplification
- `domain.py` currently does `datetime.fromisoformat(end.date.replace("Z", "+00:00"))` — this manual parsing goes away
- Direct comparison with `datetime.now().date()` or similar

</decisions>

<specifics>
## Specific Ideas

- Parser (`_convert_until_to_iso`) should return a `date` object instead of an ISO string
- Builder (`_convert_iso_to_until`) becomes something like `_convert_date_to_until(d: date) -> str`
- Domain warning check: `end.date < date.today()` instead of manual fromisoformat parsing

</specifics>
