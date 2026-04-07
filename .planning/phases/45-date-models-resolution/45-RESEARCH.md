# Phase 45: Date Models & Resolution - Research

**Researched:** 2026-04-07
**Domain:** Pydantic v2 contract models, date resolution logic, StrEnum unions
**Confidence:** HIGH

## Summary

Phase 45 delivers three things: (1) a `DateFilter` contract model with validators, (2) field-specific shortcut StrEnums, and (3) a pure `resolve_date_filter()` function. No database access, no bridge calls, no pipeline integration. The codebase has strong precedents for every pattern needed -- `MoveAction` for flat-model mutual exclusion, `ReviewDueFilter` for duration parsing, `AvailabilityFilter` for StrEnum filter conventions, and `Patch[Union[...]]` for multi-form input fields.

Key verified finding: Pydantic v2's union discrimination works correctly with `Patch[StrEnum | DateFilter]` -- string inputs match the StrEnum, dicts match the model, and invalid strings produce `ValidationError`. No custom discriminator needed. JSON Schema output is also clean: `anyOf` with separate `$ref` entries.

**Primary recommendation:** Follow existing codebase conventions exactly. DateFilter is a flat QueryModel with model_validator for mutual exclusion (like MoveAction). Shortcut enums are StrEnums (like AvailabilityFilter). Resolver is a standalone pure function in a new module. All descriptions/errors go in `agent_messages/`.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** DateFilter is a flat model with validators, following MoveAction/Frequency convention. Five optional keys: `this`, `last`, `next`, `before`, `after`. Model validator enforces mutual exclusion. Inherits `QueryModel`, lives in `contracts/use_cases/list/`.
- **D-02:** String shortcuts use field-specific StrEnum/Literal types. Each date field on ListTasksQuery has its own shortcut type.
- **D-03:** Shortcut grouping: `due` gets overdue/soon/today; `completed`/`dropped` get any/today; `defer`/`planned`/`added`/`modified` get today only.
- **D-04:** "overdue" and "soon" resolve to timestamps, NOT OmniFocus pre-computed columns.
- **D-05:** `"overdue"` resolves to `DateRange(end=now)`.
- **D-06:** `"soon"` resolves using DueSoonInterval + DueSoonGranularity (two modes: rolling vs calendar-aligned).
- **D-07:** Primary source: Settings table via SQLite. Fallback: `OPERATOR_DUE_SOON_THRESHOLD` env var. Fail fast if neither.
- **D-08:** Fallback env var for bridge-only mode.
- **D-09:** Resolver is a pure function; config injection is caller's responsibility (Phase 46).
- **D-10:** Resolved output = flat `_after`/`_before` datetime fields on ListTasksRepoQuery. 7 fields x 2 = 14 new fields.
- **D-11:** `"any"` shortcut does NOT produce date fields -- expands availability list instead.
- **D-12:** `"overdue"` and `"soon"` resolve to same `_before` field as any other date filter.
- **D-13:** `"none"` (IS NULL) scoped out of v1.3.2.
- **D-14:** `OPERATOR_WEEK_START` env var, default Monday.
- **D-15/D-16:** Requirements updates needed (RESOLVE-11/12 rewritten, DATE-06/07/08 "none" removed).
- **D-17:** `"today"` = syntactic sugar for `{this: "d"}`, available on all 7 fields.
- **D-18:** Resolver signature concept provided (pure function, accepts `now`, `week_start`, `due_soon_interval`, `due_soon_granularity`).

### Claude's Discretion
- Exact StrEnum class names and grouping (how many enum types, shared vs per-field)
- Whether DurationUnit from projects.py is reused or a new one created
- Internal structure of resolver module (single function vs class)
- Error message wording (follows existing educational tone)

### Deferred Ideas (OUT OF SCOPE)
- `"none"` shortcut (IS NULL filtering) -- future milestone
- pydantic-settings consolidation -- not blocking

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATE-01 | Agent can pass string shortcut or object form for each of 7 date fields | Pydantic v2 `Patch[StrEnum \| DateFilter]` union verified -- string inputs match enum, dicts match model |
| DATE-02 | Shorthand object form accepts this/last/next with [N]unit duration | Existing `_DURATION_PATTERN` regex and `parse_review_due_within()` precedent in projects.py |
| DATE-03 | Absolute object form accepts before/after with ISO8601, date-only, or "now" | Pydantic v2 handles datetime/str parsing; field_validator for "now" acceptance |
| DATE-04 | Shorthand and absolute groups mutually exclusive | MoveAction `_exactly_one_key` model_validator pattern |
| DATE-05 | Zero/negative count returns educational error | Validator pattern from `_validate_interval` in repetition_rule.py |
| DATE-06 | Field-specific shortcuts validated (revised: no "none") | Per-field StrEnum/Literal types on union enforce via JSON Schema + Pydantic validation |
| DATE-09 | after < before when both specified | Model validator on DateFilter, compare parsed datetimes |
| RESOLVE-01 | "today" = calendar-aligned current day | Resolver produces `(midnight_today, midnight_tomorrow)` |
| RESOLVE-02 | {this: unit} = calendar-aligned period boundaries | Resolver with week_start config for "w", naive 30d/365d for "m"/"y" |
| RESOLVE-03 | {last: "[N]unit"} = midnight N periods ago through now | Day-snapped lower bound, now upper bound |
| RESOLVE-04 | {next: "[N]unit"} = now through midnight N+1 periods from now | Now lower bound, day-snapped upper bound |
| RESOLVE-05 | "now" evaluated once at query start | Caller passes `now: datetime` to resolver -- single timestamp |
| RESOLVE-06 | Week start configurable via OPERATOR_WEEK_START | Config pattern from existing OPERATOR_* env vars |
| RESOLVE-07 | Month ~30d, year ~365d (naive) | Note: differs from _expand_review_due which uses calendar-aware month/year |
| RESOLVE-08 | Absolute before with date-only = start of next day (end-of-day inclusive) | Resolver adds 1 day to date-only before values |
| RESOLVE-09 | Absolute after with date-only = start of that day (start-of-day inclusive) | Resolver uses midnight of date-only after values |
| RESOLVE-10 | Both before and after inclusive | Both bounds expanded to include full days via midnight snapping |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **SAFE-01/02**: No automated test may touch `RealBridge`. Use `InMemoryBridge` or `SimulatorBridge` only.
- **Model taxonomy**: Read `docs/model-taxonomy.md` before creating models. DateFilter = `<noun>Filter` (QueryModel). Lives in `contracts/use_cases/list/`.
- **Agent messages**: All description/error strings in `agent_messages/descriptions.py` and `errors.py`. Class docstrings use `__doc__ = CONSTANT`.
- **Service layer convention**: Method Object pattern for pipelines. But resolver is a pure function (not a pipeline -- Phase 45 is models + resolver, not pipeline integration).
- **Output schema test**: After modifying models in tool output, run `uv run pytest tests/test_output_schema.py -x -q`. (DateFilter is input-only, but RepoQuery changes could affect output indirectly.)

## Architecture Patterns

### Recommended Project Structure

New/modified files for this phase:

```
src/omnifocus_operator/
├── contracts/use_cases/list/
│   ├── _enums.py              # ADD: DueDateShortcut, LifecycleDateShortcut StrEnums
│   ├── _date_filter.py        # NEW: DateFilter model + duration parsing
│   └── tasks.py               # MODIFY: add 7 date fields to ListTasksQuery, 14 to RepoQuery
├── service/
│   └── resolve_dates.py       # NEW: resolve_date_filter() pure function
├── config.py                  # MODIFY: add OPERATOR_WEEK_START
└── agent_messages/
    ├── descriptions.py        # MODIFY: add date filter field/class descriptions
    └── errors.py              # MODIFY: add date filter validation errors
```

### Pattern 1: Flat Model + Model Validator (DateFilter)
**What:** DateFilter follows MoveAction's exactly-one-key pattern for mutual exclusion
**When to use:** When a model has mutually exclusive field groups
**Example:**
```python
# Source: verified against src/omnifocus_operator/contracts/shared/actions.py
class DateFilter(QueryModel):
    __doc__ = DATE_FILTER_DOC

    this: str | None = None
    last: str | None = None
    next: str | None = None
    before: str | None = None
    after: str | None = None

    @model_validator(mode="after")
    def _validate_groups(self) -> DateFilter:
        shorthand = [self.this, self.last, self.next]
        absolute = [self.before, self.after]
        has_shorthand = any(v is not None for v in shorthand)
        has_absolute = any(v is not None for v in absolute)

        if has_shorthand and has_absolute:
            raise ValueError(DATE_FILTER_MIXED_GROUPS)
        if has_shorthand:
            count = sum(1 for v in shorthand if v is not None)
            if count != 1:
                raise ValueError(DATE_FILTER_MULTIPLE_SHORTHAND)
        if not has_shorthand and not has_absolute:
            raise ValueError(DATE_FILTER_EMPTY)
        return self
```
[VERIFIED: codebase pattern from MoveAction]

### Pattern 2: Field-Specific StrEnum on Union Type
**What:** Each date field gets its own shortcut type so JSON Schema is field-specific
**When to use:** When different fields accept different string shortcuts
**Example:**
```python
# Source: verified against contracts/use_cases/list/_enums.py AvailabilityFilter pattern
class DueDateShortcut(StrEnum):
    __doc__ = DUE_DATE_SHORTCUT_DOC
    OVERDUE = "overdue"
    SOON = "soon"
    TODAY = "today"

class LifecycleDateShortcut(StrEnum):
    __doc__ = LIFECYCLE_DATE_SHORTCUT_DOC
    ANY = "any"
    TODAY = "today"

# On ListTasksQuery:
due: Patch[DueDateShortcut | DateFilter] = Field(default=UNSET, description=DUE_FILTER_DESC)
completed: Patch[LifecycleDateShortcut | DateFilter] = Field(default=UNSET, description=COMPLETED_FILTER_DESC)
defer: Patch[Literal["today"] | DateFilter] = Field(default=UNSET, description=DEFER_FILTER_DESC)
```
[VERIFIED: Pydantic v2 union discrimination tested -- string->StrEnum, dict->model, invalid->ValidationError]

### Pattern 3: Pure Resolver Function
**What:** Stateless function that converts input forms to `(after, before)` tuple
**When to use:** When resolution logic is complex but has no side effects
**Example:**
```python
# New module: service/resolve_dates.py
def resolve_date_filter(
    value: StrEnum | DateFilter,
    field_name: str,
    now: datetime,
    *,
    week_start: str = "monday",
    due_soon_interval: int | None = None,
    due_soon_granularity: int | None = None,
) -> tuple[datetime | None, datetime | None]:
    """Returns (after_bound, before_bound). Pure function, no I/O."""
```
[VERIFIED: D-18 in CONTEXT.md, follows _expand_review_due precedent]

### Anti-Patterns to Avoid
- **Don't embed resolution logic in the model**: DateFilter validates input shape only. Resolution is a separate concern in service layer.
- **Don't use a single StrEnum for all fields**: Different fields have different shortcuts. Using one big enum means agents see invalid options in JSON Schema.
- **Don't use calendar-aware month/year math**: RESOLVE-07 explicitly mandates naive 30d/365d. Note `_expand_review_due` uses calendar-aware math -- the date filter resolver intentionally differs.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Duration string parsing | Custom regex | Extend `_DURATION_PATTERN` from projects.py | Already handles `[N]unit` format, reuse the pattern |
| ISO8601 datetime parsing | Custom parser | Pydantic v2's built-in datetime coercion | Handles ISO strings, date-only, timezone-aware |
| JSON Schema generation | Manual schema | Pydantic v2 model_json_schema() | StrEnum/Literal/model unions produce correct anyOf schema automatically |
| "now" string handling | Special sentinel type | `field_validator` that converts "now" string | Keep it simple -- validator on before/after fields |

## Common Pitfalls

### Pitfall 1: Union Ordering with Pydantic v2
**What goes wrong:** If `DateFilter` comes before `StrEnum` in the union, a string like `"overdue"` might be coerced into a DateFilter with `this="overdue"` (all fields are `str | None`).
**Why it happens:** Pydantic v2 tries union members left-to-right. A string can match `str | None` fields on the model.
**How to avoid:** Always put StrEnum/Literal BEFORE DateFilter in the union: `Patch[DueDateShortcut | DateFilter]`.
**Warning signs:** String shortcuts silently become DateFilter objects instead of enum values.
[VERIFIED: tested with Pydantic 2.12.5 -- StrEnum first correctly matches strings]

### Pitfall 2: "today" Shortcut Duplicated in Both StrEnum and Literal
**What goes wrong:** `"today"` appears in DueDateShortcut AND as the Literal["today"] for other fields. If not careful, could have inconsistent resolution.
**Why it happens:** "today" is available on all 7 fields per D-17.
**How to avoid:** All "today" resolution goes through the same code path in the resolver: `resolve_shortcut("today") -> resolve_date_filter(DateFilter(this="d"))`. Whether it comes from a StrEnum member or a Literal, the resolver treats it identically.
[ASSUMED]

### Pitfall 3: Month/Year Approximation vs Calendar Math
**What goes wrong:** Using `_expand_review_due`'s calendar-aware month/year math instead of naive 30d/365d.
**Why it happens:** Natural instinct to reuse existing code. But RESOLVE-07 explicitly specifies naive approximation.
**How to avoid:** Use `timedelta(days=count * 30)` for months, `timedelta(days=count * 365)` for years. Document the intentional difference from `_expand_review_due`.
[VERIFIED: RESOLVE-07 in REQUIREMENTS.md]

### Pitfall 4: Absolute date-only vs datetime Boundary Logic
**What goes wrong:** `{before: "2026-04-14"}` treated as midnight START of April 14 instead of END (midnight of April 15).
**Why it happens:** Confusion between "up to and including April 14" and "strictly before April 14 midnight".
**How to avoid:** RESOLVE-08 says date-only `before` = start of NEXT day. RESOLVE-09 says date-only `after` = start of THAT day. Both make the range inclusive of the specified dates.
[VERIFIED: RESOLVE-08, RESOLVE-09, RESOLVE-10 in REQUIREMENTS.md]

### Pitfall 5: "soon" Without Due-Soon Config
**What goes wrong:** Agent sends `due: "soon"` but no DueSoonInterval/DueSoonGranularity is available.
**Why it happens:** Bridge-only mode, no env var set, Settings table not readable.
**How to avoid:** D-08 says fail fast. Resolver raises ValueError with educational message when `due_soon_interval` is None and shortcut is "soon". The error guides the agent: "The 'soon' shortcut requires OmniFocus due-soon threshold configuration."
[VERIFIED: D-07, D-08 in CONTEXT.md]

### Pitfall 6: `reject_null_filters` Doesn't Cover Date Fields
**What goes wrong:** Date fields should NOT reject null via `reject_null_filters` because they use `Patch[Union[...]]` where UNSET (not None) means "don't filter." But null should still be rejected since "clear the date filter" makes no sense.
**Why it happens:** The existing `_PATCH_FIELDS` list needs extending, or date fields need their own null rejection.
**How to avoid:** Add all 7 date field names to `_PATCH_FIELDS` in tasks.py. The `reject_null_filters` validator already handles camelCase variants.
[VERIFIED: existing _PATCH_FIELDS pattern in tasks.py]

## Code Examples

### Duration Parsing (reuse existing pattern)
```python
# Source: contracts/use_cases/list/projects.py lines 32, 53-74
_DURATION_PATTERN = re.compile(r"^(\d+)([dwmy])$")

# For DateFilter, extend to handle implicit count: "w" -> "1w"
_DATE_DURATION_PATTERN = re.compile(r"^(\d*)([dwmy])$")

def parse_duration(value: str) -> tuple[int, str]:
    match = _DATE_DURATION_PATTERN.match(value)
    if not match:
        raise ValueError(DATE_FILTER_INVALID_DURATION.format(value=value))
    count_str, unit = match.group(1), match.group(2)
    count = int(count_str) if count_str else 1  # default count = 1
    if count <= 0:
        raise ValueError(DATE_FILTER_ZERO_NEGATIVE.format(value=value))
    return count, unit
```
[VERIFIED: projects.py pattern, extended for implicit count per MILESTONE-v1.3.2]

### Week Start Resolution
```python
# Source: D-14 in CONTEXT.md
import os

WEEK_START_MAP = {"monday": 0, "sunday": 6}  # Python weekday values

def get_week_start() -> int:
    """Return Python weekday int for configured week start. Default Monday."""
    raw = os.environ.get("OPERATOR_WEEK_START", "monday").lower()
    if raw not in WEEK_START_MAP:
        # Fail fast with guidance
        raise ValueError(f"Invalid OPERATOR_WEEK_START '{raw}' -- use 'monday' or 'sunday'")
    return WEEK_START_MAP[raw]
```
[ASSUMED -- env var pattern follows existing OPERATOR_* convention]

### "this" Period Calendar Alignment
```python
# Example: {this: "w"} on Wednesday 2026-04-09, week_start=monday
# -> (2026-04-07 00:00, 2026-04-14 00:00)  # Monday to next Monday

def _resolve_this(unit: str, now: datetime, week_start: int) -> tuple[datetime, datetime]:
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if unit == "d":
        return today, today + timedelta(days=1)
    if unit == "w":
        days_since_start = (today.weekday() - week_start) % 7
        start = today - timedelta(days=days_since_start)
        return start, start + timedelta(days=7)
    if unit == "m":
        start = today.replace(day=1)
        end = start + timedelta(days=30)  # naive per RESOLVE-07
        return start, end
    if unit == "y":
        start = today.replace(month=1, day=1)
        end = start + timedelta(days=365)  # naive per RESOLVE-07
        return start, end
```
[ASSUMED -- resolution logic derived from CONTEXT.md resolution examples]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| OmniFocus `dueSoon` column for "soon" | Timestamp resolution from Settings table values | v1.3.2 (D-04) | Resolver needs DueSoonInterval + DueSoonGranularity params |
| `COMPLETED`/`DROPPED` in AvailabilityFilter | Date filter `completed`/`dropped` fields with "any" shortcut | v1.3.2 (D-11) | "any" manipulates availability list, not date bounds |
| `"none"` IS NULL filtering | Scoped out | v1.3.2 (D-13) | Simpler model, fewer edge cases |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2+ with pytest-asyncio |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_list_contracts.py -x -q` |
| Full suite command | `uv run pytest -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATE-01 | String/object union on 7 fields | unit | `uv run pytest tests/test_date_filter_contracts.py -x -q` | No -- Wave 0 |
| DATE-02 | Shorthand [N]unit parsing | unit | `uv run pytest tests/test_date_filter_contracts.py -x -q` | No -- Wave 0 |
| DATE-03 | Absolute before/after with ISO/"now" | unit | `uv run pytest tests/test_date_filter_contracts.py -x -q` | No -- Wave 0 |
| DATE-04 | Shorthand/absolute mutual exclusion | unit | `uv run pytest tests/test_date_filter_contracts.py -x -q` | No -- Wave 0 |
| DATE-05 | Zero/negative count error | unit | `uv run pytest tests/test_date_filter_contracts.py -x -q` | No -- Wave 0 |
| DATE-06 | Field-specific shortcut enforcement | unit | `uv run pytest tests/test_date_filter_contracts.py -x -q` | No -- Wave 0 |
| DATE-09 | after < before validation | unit | `uv run pytest tests/test_date_filter_contracts.py -x -q` | No -- Wave 0 |
| RESOLVE-01 | "today" -> calendar day | unit | `uv run pytest tests/test_resolve_dates.py -x -q` | No -- Wave 0 |
| RESOLVE-02 | {this: unit} -> period boundaries | unit | `uv run pytest tests/test_resolve_dates.py -x -q` | No -- Wave 0 |
| RESOLVE-03 | {last: "Nd"} -> midnight-N to now | unit | `uv run pytest tests/test_resolve_dates.py -x -q` | No -- Wave 0 |
| RESOLVE-04 | {next: "Nd"} -> now to midnight+N+1 | unit | `uv run pytest tests/test_resolve_dates.py -x -q` | No -- Wave 0 |
| RESOLVE-05 | "now" consistent across filters | unit | `uv run pytest tests/test_resolve_dates.py -x -q` | No -- Wave 0 |
| RESOLVE-06 | OPERATOR_WEEK_START config | unit | `uv run pytest tests/test_resolve_dates.py -x -q` | No -- Wave 0 |
| RESOLVE-07 | month=30d, year=365d | unit | `uv run pytest tests/test_resolve_dates.py -x -q` | No -- Wave 0 |
| RESOLVE-08 | date-only before -> next day midnight | unit | `uv run pytest tests/test_resolve_dates.py -x -q` | No -- Wave 0 |
| RESOLVE-09 | date-only after -> that day midnight | unit | `uv run pytest tests/test_resolve_dates.py -x -q` | No -- Wave 0 |
| RESOLVE-10 | Both bounds inclusive | unit | `uv run pytest tests/test_resolve_dates.py -x -q` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_date_filter_contracts.py tests/test_resolve_dates.py -x -q`
- **Per wave merge:** `uv run pytest -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_date_filter_contracts.py` -- DateFilter model validation, union behavior on ListTasksQuery, field-specific shortcuts
- [ ] `tests/test_resolve_dates.py` -- resolver function for all input forms, boundary conditions, week start config
- [ ] No framework install needed -- pytest already configured

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | "today" from all StrEnum/Literal types routes through same resolver code path | Pitfall 2 | Inconsistent day boundaries across fields |
| A2 | OPERATOR_WEEK_START env var uses lowercase string values "monday"/"sunday" | Code Examples | Config parsing fails or is case-sensitive |
| A3 | `{this: "m"}` starts at day=1 of current month, `{this: "y"}` at month=1 day=1 | Code Examples | Wrong calendar alignment for month/year periods |

## Open Questions (RESOLVED)

1. **DurationUnit reuse vs new enum**
   - What we know: `DurationUnit(StrEnum)` exists in projects.py with d/w/m/y values
   - What's unclear: Whether to import and reuse it for DateFilter or create a separate one
   - Recommendation: **Reuse** -- same values, same purpose, reduces duplication. Import from projects.py or extract to `_enums.py`.
   - RESOLVED: Plans create new field-specific enums (DueDateShortcut, LifecycleDateShortcut) rather than reusing DurationUnit — these enums carry shortcut values (overdue, soon, any, today) not duration units.

2. **"this" month/year end boundary with naive math**
   - What we know: RESOLVE-07 says 30d/365d naive approximation
   - What's unclear: For `{this: "m"}`, does the end = `start_of_month + 30d` or `start_of_next_calendar_month`? The former can miss days in 31-day months. The latter is calendar-aware.
   - Recommendation: `{this: "m"}` should use calendar-aware start (first of month) and calendar-aware end (first of next month). The naive 30d/365d applies to `{last: "1m"}` and `{next: "1m"}` where the anchor is "now" and the range is approximate. `{this: ...}` is "which period am I in?" which has exact calendar boundaries.
   - RESOLVED: Plan 03 uses calendar-aware boundaries for `{this: "m"/"y"}` (first of month → first of next month, Jan 1 → Jan 1 next year). Naive 30d/365d applies only to `{last: "Nm"/"Ny"}` and `{next: "Nm"/"Ny"}`.

3. **Where to put the resolver module**
   - What we know: It's a pure function with no I/O, called by the service pipeline in Phase 46
   - What's unclear: `service/resolve_dates.py` vs `contracts/use_cases/list/_resolve.py`
   - Recommendation: `service/resolve_dates.py` -- it's resolution logic (business logic), not contract validation. The service layer is where `_expand_review_due` lives too.
   - RESOLVED: Plan 03 places resolver in `service/resolve_dates.py` — business logic, not contract validation.

## Sources

### Primary (HIGH confidence)
- Codebase: `contracts/shared/actions.py` -- MoveAction flat model + model_validator pattern
- Codebase: `contracts/use_cases/list/_enums.py` -- AvailabilityFilter StrEnum pattern
- Codebase: `contracts/use_cases/list/projects.py` -- DurationUnit, _DURATION_PATTERN, parse_review_due_within
- Codebase: `contracts/use_cases/list/tasks.py` -- ListTasksQuery/ListTasksRepoQuery current state
- Codebase: `contracts/base.py` -- UNSET, Patch, QueryModel infrastructure
- Codebase: `service/service.py:472-495` -- _expand_review_due precedent
- Codebase: `docs/model-taxonomy.md` -- Scenario F is exact pattern for DateFilter
- Live test: Pydantic 2.12.5 `Patch[StrEnum | Model]` union discrimination confirmed working
- Research: `.research/deep-dives/direct-database-access-date-filters/6-due-soon-spike/FINDINGS.md` -- DueSoonGranularity two-mode formula

### Secondary (MEDIUM confidence)
- `.research/updated-spec/MILESTONE-v1.3.2.md` -- period resolution semantics (last/next boundary rules)

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all Pydantic v2, no new dependencies, patterns verified in codebase
- Architecture: HIGH -- every pattern has a direct codebase precedent
- Pitfalls: HIGH -- union ordering and boundary logic verified via live testing

**Research date:** 2026-04-07
**Valid until:** 2026-05-07 (stable -- no external dependencies, all internal patterns)
