# Phase 49: Implement naive-local datetime contract for all date inputs - Research

**Researched:** 2026-04-10
**Domain:** Python datetime handling, Pydantic contract types, MCP JSON Schema
**Confidence:** HIGH

## Summary

Phase 49 replaces UTC-anchored timestamps with naive-local datetime throughout write contracts, filter resolution, and service layer. The codebase changes are well-scoped: 8 source files + architecture docs + tests. The core technical challenges are (1) choosing the right local timezone API (`datetime.now().astimezone()`, NOT `ZoneInfo("localtime")`), (2) changing Pydantic types from `AwareDatetime` to `str` without breaking downstream consumers, and (3) adding a domain-layer normalization function that parses date strings, detects format, and normalizes to naive local.

**Primary recommendation:** Use `datetime.now().astimezone()` for local timezone. The helper should return a tz-aware local datetime (not naive) so CF epoch subtraction in `query_builder.py` works unchanged. Strip tzinfo only at the bridge boundary for write operations.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Naive-local is the preferred format for ALL date inputs across the entire API -- write-side fields (add/edit) AND read-side filter bounds (before/after). Aware datetimes (with timezone offset) are accepted as a convenience and silently converted to local time.
- **D-01b:** This overrides Phase 48's `_reject_naive_datetime` BeforeValidator on `_DateBound`. Phase 48 was designed before the timezone deep-dive; the todo's design document (based on 430-task empirical evidence) supersedes all prior timezone decisions.
- **D-01c:** The `_reject_naive_datetime` validator and its error message constant are dead code after this phase -- remove them.
- **D-07:** All write-side date fields (`dueDate`, `deferDate`, `plannedDate`) change from `AwareDatetime` to `str` on both `AddTaskCommand` and `EditTaskCommand`. This drops `format: "date-time"` from JSON Schema.
- **D-07b:** Read-side `_DateBound` in `AbsoluteRangeFilter` also changes to `str` (from `Literal["now"] | AwareDatetime | date`).
- **D-07c:** `PatchOrClear[AwareDatetime]` on edit fields becomes `PatchOrClear[str]`.
- **D-02:** Date-only strings intercepted and converted to midnight local before bridge.
- **D-02b/c/d:** Avoids JS bridge date-only quirk; clean upgrade path for settings API.
- **D-03:** Centralized local timezone helper with rationale docstring.
- **D-04:** `DATE_EXAMPLE` changes from `"2026-03-15T17:00:00Z"` to `"2026-03-15T17:00:00"`.
- **D-05/D-05b:** Brief inline note in each write tool doc framing dates as local time.
- **D-06:** Aware->local normalization lives in `domain.py` (product decision). Contract layer validates syntax only. Domain interprets semantics.

### Claude's Discretion
- Internal naming of the local timezone helper function
- Exact format validation regex/parsing approach in the contract validator
- Whether to extract a shared date-string validator or duplicate per field
- How `_validate_bounds` in AbsoluteRangeFilter adapts to `str` inputs
- Test file organization and migration approach
- Exact wording of the tool-level description note
- Where the `local_now()` helper lives (config.py, service utility, or new module)
- How the CF epoch math in `query_builder.py` adapts

### Deferred Ideas (OUT OF SCOPE)
- **Use OmniFocus settings API for date preferences and due-soon threshold** -- depends on Phase 49, separate scope
- **Add date filters to list_projects** -- different capability, reuses v1.3.2 infrastructure after it's stable
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LOCAL-01 | Write-side date fields and read-side filter bounds use `str` type -- no `format: "date-time"` in JSON Schema | Type change AwareDatetime -> str verified to drop format constraint; see Standard Stack / Architecture Patterns |
| LOCAL-02 | Naive datetime strings accepted and treated as local time on all date inputs | `datetime.fromisoformat()` parses naive correctly (verified); domain normalization passes through as-is |
| LOCAL-03 | Aware datetime strings accepted on all date inputs, silently converted to naive local time | `dt.astimezone().replace(tzinfo=None)` verified; domain.py normalization function handles this |
| LOCAL-04 | Date-only strings accepted on write-side with midnight local appended | Format detection via `'T' not in s`; append `T00:00:00` before fromisoformat parse |
| LOCAL-05 | All `now` timestamps use local timezone | `datetime.now().astimezone()` returns tz-aware local; verified CF epoch math works unchanged |
| LOCAL-06 | Aware->local normalization is domain-layer product decision | Matches architecture.md litmus test; contracts validate syntax, domain interprets semantics |
| LOCAL-07 | Write tool descriptions and JSON Schema examples frame dates as naive local | `DATE_EXAMPLE` change + inline note per tool; matches existing descriptions.py pattern |
| LOCAL-08 | `architecture.md` documents naive-local principle with rationale | New section alongside existing design philosophy sections |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.12.5 | Contract validation, JSON Schema generation | Already in project; `str` type produces schema without `format: "date-time"` [VERIFIED: uv run] |
| datetime (stdlib) | Python 3.12 | Date parsing, timezone conversion | `fromisoformat()` handles all target formats (naive, aware, date-only) [VERIFIED: runtime test] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| No new dependencies | -- | -- | Phase uses only existing project dependencies |

**No new packages needed.** All datetime operations use Python stdlib. No `dateutil`, no `arrow`, no `pendulum`.

## Architecture Patterns

### Data Flow: Write Side (after Phase 49)

```
Agent sends str  -->  Contract validates syntax  -->  Domain normalizes  -->  Payload formats  -->  Bridge
  "17:00:00"          (is it parseable?)             (aware->local,           (isoformat str)        (JS new Date)
  "17:00:00Z"                                         date-only->midnight,
  "2026-07-15"                                         naive->passthrough)
```

### Data Flow: Read Side (after Phase 49)

```
Agent sends str/shortcut  -->  Contract validates  -->  Service: now=local_now()  -->  resolve_dates  -->  query_builder
  "now"                        (str or "now")            (tz-aware local)              (same math)         (CF epoch: same)
  "2026-07-15"
  "2026-07-15T17:00:00"
```

### Pattern 1: Local Timezone Helper

**What:** Single function encapsulating the "use local time" decision
**When to use:** Every `datetime.now()` call in service layer, every "now" resolution
**Recommended location:** `src/omnifocus_operator/service/local_time.py` (new module, or inline in `config.py`)

```python
# Source: verified against project patterns + runtime tests
from datetime import datetime

def local_now() -> datetime:
    """Return current time as a tz-aware local datetime.

    OmniFocus stores all dates as naive local time. The server runs on
    the same Mac. Using local time means the API matches OmniFocus's
    mental model: "5pm" means 5pm, period.

    Returns tz-aware (not naive) so arithmetic with UTC-anchored values
    (CF epoch subtraction in query_builder) works correctly -- Python
    handles the offset automatically in tz-aware subtraction.

    Evidence: timezone deep-dive proved the conversion formula across
    430 tasks in both BST and GMT. See .research/deep-dives/timezone-behavior/
    """
    return datetime.now().astimezone()
```

[VERIFIED: runtime test] -- `datetime.now().astimezone()` returns tz-aware local datetime with correct offset. CF epoch subtraction produces identical results to UTC-anchored datetimes for the same absolute moment.

### Pattern 2: Date String Normalization in Domain

**What:** Parse agent-provided date string, detect format, normalize to naive local
**When to use:** All write-side date processing in domain.py

```python
# Source: design from CONTEXT.md D-06, verified against fromisoformat behavior
from datetime import datetime

def normalize_date_input(value: str) -> str:
    """Normalize a date input string to naive local ISO format for the bridge.

    Three cases:
    - Date-only ("2026-07-15"): append T00:00:00 (midnight local)
    - Naive datetime ("2026-07-15T17:00:00"): pass through as-is
    - Aware datetime ("2026-07-15T17:00:00Z"): convert to local, strip tz
    """
    if "T" not in value:
        # Date-only: append midnight local (interim; settings API will upgrade)
        return f"{value}T00:00:00"

    dt = datetime.fromisoformat(value)
    if dt.tzinfo is not None:
        # Aware: convert to local, strip tzinfo
        local_dt = dt.astimezone()  # converts to system local
        return local_dt.replace(tzinfo=None).isoformat()

    # Naive: already local by contract
    return value
```

[VERIFIED: fromisoformat handles all three formats correctly]

### Pattern 3: Contract Syntax Validator

**What:** Validate that a string is a parseable date/datetime before Pydantic accepts it
**When to use:** BeforeValidator on all date `str` fields in contracts

```python
# Source: project convention (contracts are pure data, no transformation)
from datetime import datetime

def _validate_date_string(v: object) -> object:
    """Validate that a string is a parseable ISO date or datetime."""
    if not isinstance(v, str):
        return v
    try:
        datetime.fromisoformat(v)
    except ValueError:
        raise ValueError(
            f"Invalid date format '{v}'. Expected ISO date ('2026-07-15'), "
            f"ISO datetime ('2026-07-15T17:00:00'), or datetime with "
            f"timezone ('2026-07-15T17:00:00Z')."
        )
    return v
```

### Pattern 4: Adapted `_validate_bounds` for str inputs

**What:** AbsoluteRangeFilter's ordering check must parse `str` before comparing
**When to use:** `_validate_bounds` model validator on AbsoluteRangeFilter

The current `_validate_bounds` asserts non-str after handling `"now"`. With `_DateBound` becoming `Literal["now"] | str`, both values are str. Parse with `fromisoformat` to compare:

```python
# Sketch -- exact implementation at executor's discretion
if before == "now" or after == "now":
    return self
# Both are date/datetime strings -- parse and compare
after_dt = datetime.fromisoformat(after)
before_dt = datetime.fromisoformat(before)
# Strip tz for comparison (naive ordering is sufficient)
after_cmp = after_dt.replace(tzinfo=None) if after_dt.tzinfo else after_dt
before_cmp = before_dt.replace(tzinfo=None) if before_dt.tzinfo else before_dt
if after_cmp > before_cmp:
    raise ValueError(...)
```

### Anti-Patterns to Avoid
- **`ZoneInfo("localtime")`**: Does NOT work on macOS without `tzdata` package installed. Use `datetime.now().astimezone()` instead. [VERIFIED: ZoneInfoNotFoundError on this system]
- **Naive datetime for `now` in service layer**: CF epoch subtraction (`datetime - _CF_EPOCH`) requires both sides to be tz-aware or both naive. Since `_CF_EPOCH` is `datetime(2001, 1, 1, tzinfo=UTC)`, `now` must also be tz-aware.
- **`NaiveDatetime` or `datetime` in Pydantic fields**: Both produce `format: "date-time"` in JSON Schema, identical to `AwareDatetime`. Only `str` avoids the format constraint. [VERIFIED: CONTEXT.md empirical evidence]
- **Transformation logic in contracts**: Per project convention, contracts are pure data. Validation checks syntax only; domain.py owns semantic interpretation.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ISO date/datetime parsing | Custom regex parser | `datetime.fromisoformat()` | Handles all ISO 8601 variants since Python 3.11 including `Z` suffix |
| Local timezone detection | `ZoneInfo("localtime")` or env var parsing | `datetime.now().astimezone()` | Works on all platforms without extra packages |
| Aware-to-local conversion | Manual offset arithmetic | `dt.astimezone()` (no args = local) | Handles DST transitions correctly |
| Date format detection | Complex regex classification | `"T" in value` check | Date-only strings never contain `T`; all ISO datetimes do |

## Common Pitfalls

### Pitfall 1: ZoneInfo("localtime") not available on macOS
**What goes wrong:** `ZoneInfoNotFoundError: 'No time zone found with key localtime'`
**Why it happens:** macOS CPython 3.12 without `tzdata` package can't resolve the "localtime" key
**How to avoid:** Use `datetime.now().astimezone()` which uses C-level `localtime()` directly
**Warning signs:** Tests pass in CI (Linux with tzdata) but fail on macOS

### Pitfall 2: Naive datetime breaks CF epoch subtraction
**What goes wrong:** `TypeError: can't subtract offset-naive and offset-aware datetimes`
**Why it happens:** `_CF_EPOCH = datetime(2001, 1, 1, tzinfo=UTC)` is tz-aware; subtracting a naive datetime fails
**How to avoid:** `local_now()` must return tz-aware local datetime, not naive
**Warning signs:** Tests for query_builder.py fail with TypeError

### Pitfall 3: PayloadBuilder still calls `.isoformat()` on date values
**What goes wrong:** `AttributeError: 'str' object has no attribute 'isoformat'`
**Why it happens:** `payload.py:_add_dates_if_set` calls `value.isoformat()` assuming datetime objects
**How to avoid:** With `str` type, dates arrive as strings. PayloadBuilder must pass strings through (or domain pre-normalizes to string)
**Warning signs:** Any add/edit test with dates fails after type change

### Pitfall 4: `_to_utc_ts` in domain.py has stale assertion
**What goes wrong:** `AssertionError: naive datetime '...' -- callers must pass aware`
**Why it happens:** `_to_utc_ts` (used by no-op detection in `_all_fields_match`) asserts `dt.tzinfo is not None` when parsing ISO strings from repo payloads. After the type change, payload dates are naive-local strings.
**How to avoid:** Update `_to_utc_ts` to handle naive strings (treat as local, convert to UTC timestamp) or change the comparison approach entirely
**Warning signs:** Edit no-op detection tests fail

### Pitfall 5: `_parse_absolute_after/before` in resolve_dates.py assumes typed inputs
**What goes wrong:** `isinstance(value, date)` checks fail; `value.tzinfo` attribute errors
**Why it happens:** These functions expect `AwareDatetime | date` but will receive `str` after type change
**How to avoid:** Parse the string first, then apply existing logic. Or rewrite to handle strings directly.
**Warning signs:** Any absolute range date filter test fails

### Pitfall 6: Test fixtures use `datetime(2026, ..., tzinfo=UTC)` for date fields
**What goes wrong:** Tests pass `AwareDatetime` objects to commands that now expect `str`
**Why it happens:** Widespread test fixture pattern using UTC-anchored datetime objects
**How to avoid:** Audit and update all test fixtures that construct AddTaskCommand/EditTaskCommand with date fields, and all date filter contract tests
**Warning signs:** Dozens of tests fail with ValidationError on date fields

## Code Examples

### Change Map (files -> changes)

| File | Current | Target | Lines |
|------|---------|--------|-------|
| `contracts/use_cases/add/tasks.py` | `AwareDatetime \| None` | `str \| None` + validator | L55-69 |
| `contracts/use_cases/edit/tasks.py` | `PatchOrClear[AwareDatetime]` | `PatchOrClear[str]` + validator | L72-86 |
| `contracts/use_cases/list/_date_filter.py` | `Literal["now"] \| AwareDatetime \| date` | `Literal["now"] \| str` | L26-38 |
| `service/service.py` | `datetime.now(UTC)` | `local_now()` | L389, L481 |
| `service/domain.py` | (none) | Add normalization function | new |
| `service/payload.py` | `value.isoformat()` | Pass string through (or receive pre-normalized) | L48-52, L107-112 |
| `service/resolve_dates.py` | Expects `AwareDatetime \| date` | Parse `str` first | L225-256 |
| `agent_messages/descriptions.py` | `DATE_EXAMPLE = "...Z"` | `DATE_EXAMPLE = "..."` naive | L35 |
| `agent_messages/errors.py` | `DATE_FILTER_NAIVE_DATETIME` | Remove (dead code) | L138-141 |
| `docs/architecture.md` | (no naive-local section) | Add principle + rationale section | new |
| `repository/hybrid/query_builder.py` | `_CF_EPOCH` UTC subtraction | No change needed (tz-aware math works) | L14, L59-69 |

### Critical Verification: CF Epoch Math

```python
# VERIFIED: tz-aware subtraction handles offset automatically
from datetime import datetime, UTC, timezone, timedelta
_CF_EPOCH = datetime(2001, 1, 1, tzinfo=UTC)
bst = timezone(timedelta(hours=1))
local_dt = datetime(2026, 7, 15, 17, 0, 0, tzinfo=bst)   # BST 17:00
utc_dt   = datetime(2026, 7, 15, 16, 0, 0, tzinfo=UTC)    # UTC 16:00
assert (local_dt - _CF_EPOCH).total_seconds() == (utc_dt - _CF_EPOCH).total_seconds()
# Both = 805824000.0 -- same absolute moment, same CF seconds
```

### Critical Verification: ZoneInfo("localtime") fails on macOS

```python
# VERIFIED: ZoneInfoNotFoundError on macOS without tzdata
from zoneinfo import ZoneInfo
ZoneInfo("localtime")  # --> ZoneInfoNotFoundError

# Working alternative:
from datetime import datetime
local_now = datetime.now().astimezone()  # BST 2026-04-10 22:14:23+01:00
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `AwareDatetime` on write contracts | `str` (no format constraint) | Phase 49 | JSON Schema drops `format: "date-time"`, agents stop sending TZ |
| `datetime.now(UTC)` in service | `local_now()` (tz-aware local) | Phase 49 | "today" = local today, period boundaries = local calendar |
| `_reject_naive_datetime` validator | Removed | Phase 49 | Naive datetimes are now the *preferred* format |
| UTC-anchored date filter bounds | Local-anchored bounds | Phase 49 | Tasks near midnight local no longer misclassified |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `datetime.now().astimezone()` uses the correct local timezone in all deployment scenarios (macOS, login vs cron) | Architecture Patterns | Wrong timezone applied to all dates; mitigated by macOS-only target and always-interactive use |
| A2 | `datetime.fromisoformat()` accepts all ISO 8601 date/datetime formats agents would realistically send | Architecture Patterns | Agent sends unexpected format, gets validation error; low risk since examples guide format |
| A3 | No other callers of `datetime.now(UTC)` in the codebase beyond the two identified | Change Map | Missed UTC anchor continues producing wrong "today" boundary; verify with grep during implementation |

**A1 note:** `datetime.now().astimezone()` is the standard Python 3 pattern for local time. It works correctly on macOS whether the process is interactive or launched by launchd. The system timezone is read from `/etc/localtime` symlink at the C level. [VERIFIED: runtime test, but only in current BST context]

## Open Questions

1. **Where should the `local_now()` helper live?**
   - What we know: Needs to be importable from `service/service.py`, `service/domain.py`, and potentially `service/resolve_dates.py`
   - Options: `config.py` (alongside `get_week_start`), new `service/local_time.py`, or `service/domain.py` itself
   - Recommendation: `config.py` -- it's already the home for environment-level settings, and local timezone is a system-level concern similar to `OPERATOR_WEEK_START`

2. **Should `_to_utc_ts` in domain.py be rewritten or replaced?**
   - What we know: Used by no-op detection (`_all_fields_match`) to compare date values. Currently asserts tz-aware. After Phase 49, repo payload dates are naive-local strings.
   - Recommendation: Rewrite to parse ISO strings and compare as naive datetimes (since both sides are now local). UTC conversion no longer needed for same-timezone comparison.

3. **Shared validator vs per-field validator for date strings?**
   - What we know: AddTaskCommand has 3 date fields, EditTaskCommand has 3, AbsoluteRangeFilter has 2 (total: 8 fields)
   - Recommendation: Extract a shared `_validate_date_string` BeforeValidator function. The validation logic is identical across all fields. Avoids 8x duplication.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pydantic test fixtures |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LOCAL-01 | str type, no format: date-time in schema | unit | `uv run pytest tests/test_output_schema.py -x -q` | Exists (needs update) |
| LOCAL-02 | Naive datetime accepted on all inputs | unit | `uv run pytest tests/test_contracts_field_constraints.py -x -q` | Exists (needs update) |
| LOCAL-03 | Aware datetime silently converted to local | unit | `uv run pytest tests/test_service_domain.py -x -q` | Exists (needs new tests) |
| LOCAL-04 | Date-only intercepted with midnight local | unit | `uv run pytest tests/test_service_domain.py -x -q` | Needs new tests |
| LOCAL-05 | now timestamps use local timezone | unit | `uv run pytest tests/test_list_pipelines.py -x -q` | Exists (needs update) |
| LOCAL-06 | Normalization in domain layer | unit | `uv run pytest tests/test_service_domain.py -x -q` | Needs new tests |
| LOCAL-07 | Tool descriptions use naive local examples | unit | `uv run pytest tests/test_descriptions.py -x -q` | Exists (needs update) |
| LOCAL-08 | architecture.md documents naive-local | manual | Read the doc | N/A |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] New tests for domain-layer normalization function (naive/aware/date-only scenarios)
- [ ] Updated contract tests for str-typed date fields on add/edit commands
- [ ] Updated date filter contract tests for str-typed `_DateBound`
- [ ] Updated payload builder tests for string passthrough
- [ ] Updated resolve_dates tests for string input handling

## Sources

### Primary (HIGH confidence)
- Runtime verification on project system (macOS, Python 3.12, Pydantic 2.12.5)
- Project source code: all 8 target files read and analyzed
- CONTEXT.md: complete decision record from discuss phase
- Todo design document: scenario matrix (W1-W6, R1-R8, E1-E3) with empirical evidence
- Deep-dive results: `.research/deep-dives/timezone-behavior/RESULTS.md` -- 430-task proof

### Secondary (MEDIUM confidence)
- Python datetime stdlib behavior for `fromisoformat()`, `astimezone()` -- verified via runtime tests but only in current BST timezone

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all stdlib
- Architecture: HIGH -- all patterns verified against live codebase, CF epoch math proven
- Pitfalls: HIGH -- 5/6 pitfalls verified by reading actual code and running tests
- Local timezone API: HIGH -- `datetime.now().astimezone()` verified, `ZoneInfo("localtime")` failure confirmed

**Research date:** 2026-04-10
**Valid until:** 2026-05-10 (stable domain, no external dependency changes expected)
