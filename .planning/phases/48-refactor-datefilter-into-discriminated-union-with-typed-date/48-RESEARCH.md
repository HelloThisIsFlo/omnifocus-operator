# Phase 48: Refactor DateFilter into discriminated union with typed date bounds - Research

**Researched:** 2026-04-10
**Domain:** Pydantic v2 discriminated unions, contract refactoring, typed date bounds
**Confidence:** HIGH

## Summary

Phase 48 replaces the flat 5-field `DateFilter` class with a 4-model discriminated union using Pydantic v2's callable `Discriminator`. The refactor eliminates runtime validators that enforce mutual exclusion (now structural), types `before`/`after` as `Literal["now"] | AwareDatetime | date | None` (rejecting naive datetimes structurally), and cascades changes through resolver, domain, descriptions, errors, and tests.

All key technical unknowns are resolved. Pydantic v2.12.5 (current) supports `Discriminator` + `Tag` correctly. Spike results from the design document are verified: date-only strings parse as `date`, tz-aware strings parse as `AwareDatetime`, naive datetimes are rejected, and JSON Schema renders clean `const`/`format` annotations. One critical finding: the discriminator function must NOT raise `ValueError` for non-dict input -- it must route to `absolute_range` as fallback so Pydantic wraps the rejection as `ValidationError` (compatible with the middleware).

**Primary recommendation:** Implement as designed in CONTEXT.md with one correction: discriminator non-dict fallback should route to `absolute_range` (not raise ValueError) to maintain middleware compatibility.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Phase 48 is structural consistency only. Full commit to `AwareDatetime` types on `before`/`after` fields.
- **D-02:** Timezone interpretation stays unchanged in `resolve_dates.py`.
- **D-03:** Companion timezone todo is a separate future phase.
- **D-04:** Use Pydantic v2 callable `Discriminator` for the `DateFilter` union.
- **D-05:** Rationale: `AbsoluteRangeFilter` has all-optional fields causing noisy multi-branch errors.
- **D-06:** JSON Schema unchanged -- callable discriminators are Python-side routing.
- **D-07:** Implementation shape: `_route_date_filter` function dispatching on dict keys.
- **D-08:** New pattern in codebase. Two union patterns justified by two different union shapes.
- **D-09:** `AbsoluteRangeFilter` keeps `after <= before` model_validator with type-dispatch normalization.
- **D-10:** `Literal["now"]` on either side -> skip ordering comparison.
- **D-11:** Best-effort early catch, not authoritative. No false rejections.
- **D-12:** `BeforeValidator` (mode="before") on `before`/`after` to intercept naive datetime strings.
- **D-13:** Educational error: "Datetime must include timezone..."
- **D-14:** `mode="after"` won't work for naive interception.
- **D-15:** Delete 4 dead error constants.
- **D-16:** New `ABSOLUTE_RANGE_FILTER_EMPTY` replaces `DATE_FILTER_EMPTY`.
- **D-17:** Check if `DATE_FILTER_EMPTY` is still referenced elsewhere.
- **D-17b:** New `DATE_FILTER_INVALID_TYPE` for discriminator's non-dict fallback.
- **D-18:** `isinstance(value, DateFilter)` at `domain.py:187` must change to `isinstance(value, AbsoluteRangeFilter)`.
- **D-19:** Move `AbsoluteRangeFilter` import out of `TYPE_CHECKING` block.

### Claude's Discretion
- Internal naming of the discriminator routing function
- Whether `_validate_duration` is duplicated or extracted to shared helper
- Test file organization and migration approach
- Exact placement of the `BeforeValidator` (field-level vs shared helper)
- Whether `DATE_FILTER_EMPTY` is still referenced elsewhere (delete or keep)
- Minor wording adjustments to error messages

### Deferred Ideas (OUT OF SCOPE)
- Rethink timezone handling strategy for date filter inputs -- separate future phase
- Add date filters to list_projects -- different scope, reuses infrastructure after stable

</user_constraints>

## Standard Stack

No new dependencies. All tools already in the project:

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| Pydantic | 2.12.5 | Model validation, discriminated union, `AwareDatetime` | Already installed [VERIFIED: uv run python -c "import pydantic; print(pydantic.__version__)"] |
| `pydantic.Discriminator` | 2.12.5 | Callable discriminator for union routing | Verified working in spike [VERIFIED: local spike] |
| `pydantic.Tag` | 2.12.5 | Branch tagging for discriminated unions | Verified working in spike [VERIFIED: local spike] |
| `pydantic.AwareDatetime` | 2.12.5 | Timezone-aware datetime type | Already used on write side [VERIFIED: codebase grep] |
| `pydantic.BeforeValidator` | 2.12.5 | Pre-validation interception for naive datetime | Verified working in spike [VERIFIED: local spike] |

## Architecture Patterns

### Current structure (before)

```
_date_filter.py:
  DateFilter(QueryModel)       # flat class, 5 optional fields
    - this/last/next/before/after: str | None
    - _validate_duration()      # field_validator for last/next
    - _validate_this_unit()     # field_validator for this
    - _validate_absolute()      # field_validator for before/after
    - _validate_groups()        # model_validator for mutual exclusion + ordering
  _parse_to_comparable()        # module-level helper
```

### Target structure (after)

```
_date_filter.py:
  ThisPeriodFilter(QueryModel)      # required field: this: Literal["d","w","m","y"]
  LastPeriodFilter(QueryModel)      # required field: last: str + _validate_duration
  NextPeriodFilter(QueryModel)      # required field: next: str + _validate_duration
  AbsoluteRangeFilter(QueryModel)   # before/after: Literal["now"] | AwareDatetime | date | None
    - BeforeValidator on before/after for naive datetime interception
    - model_validator: at least one field set + ordering check
  _route_date_filter()              # callable discriminator function
  DateFilter = Annotated[Union[...], Discriminator(_route_date_filter)]  # type alias
```

### Key pattern: Discriminated union with callable routing [VERIFIED: Pydantic 2.12.5]

```python
from pydantic import Discriminator, Tag
from typing import Annotated, Union, Any

def _route_date_filter(v: Any) -> str:
    if isinstance(v, dict):
        if "this" in v: return "this_period"
        if "last" in v: return "last_period"
        if "next" in v: return "next_period"
        return "absolute_range"
    return "absolute_range"  # non-dict -> route to absolute_range, Pydantic rejects type

DateFilter = Annotated[
    Union[
        Annotated[ThisPeriodFilter, Tag("this_period")],
        Annotated[LastPeriodFilter, Tag("last_period")],
        Annotated[NextPeriodFilter, Tag("next_period")],
        Annotated[AbsoluteRangeFilter, Tag("absolute_range")],
    ],
    Discriminator(_route_date_filter),
]
```

### Key pattern: BeforeValidator for naive datetime interception [VERIFIED: Pydantic 2.12.5]

```python
from pydantic import BeforeValidator

def _reject_naive_datetime(v: Any) -> Any:
    if isinstance(v, str) and "T" in v:
        if not (v.endswith("Z") or "+" in v[19:] or "-" in v[19:]):
            raise ValueError(err.DATE_FILTER_NAIVE_DATETIME)
    return v

BoundType = Annotated[
    Literal["now"] | AwareDatetime | date | None,
    BeforeValidator(_reject_naive_datetime),
]
```

### Anti-Patterns to Avoid

- **Raising `ValueError` in discriminator function:** Pydantic does NOT wrap discriminator `ValueError` as `ValidationError` -- it propagates as raw `ValueError`, bypassing the `ValidationReformatterMiddleware`. Route to a fallback tag instead. [VERIFIED: local spike]
- **`isinstance(value, DateFilter)` after refactor:** `DateFilter` becomes a type alias (`Annotated[Union[...]]`). Python's `isinstance()` works with `types.UnionType` in 3.12, but it would match ANY filter variant -- the real bug is that only `AbsoluteRangeFilter` has `.after`/`.before` fields. [VERIFIED: per D-18]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Union dispatch | Manual if/elif on dict keys at parse time | `Discriminator(_route)` | Pydantic handles validation, error formatting, schema generation |
| Naive datetime rejection | Regex-based datetime parsing | `AwareDatetime` type + `BeforeValidator` | Pydantic's built-in type handles parsing; BeforeValidator intercepts edge case |
| Date vs datetime parsing | `datetime.fromisoformat()` + `_is_date_only()` | `date` type in union | Pydantic parses `"2026-04-01"` as `date`, not `datetime` [VERIFIED: spike] |

## Common Pitfalls

### Pitfall 1: Discriminator ValueError propagation
**What goes wrong:** `ValueError` raised inside the discriminator function bypasses Pydantic's error handling and propagates as a raw `ValueError` instead of `ValidationError`.
**Why it happens:** Pydantic's callable discriminator is Python-side routing, not a validator. It's expected to return a tag string, not raise.
**How to avoid:** Return `"absolute_range"` for non-dict input. Pydantic then rejects the type mismatch as a proper `ValidationError`.
**Warning signs:** Tests that catch `ValueError` instead of `ValidationError` on non-dict inputs.
**Evidence:** [VERIFIED: local spike -- `ValueError` from discriminator propagates raw, not wrapped]

### Pitfall 2: Schema shape change
**What goes wrong:** The outer field schema changes from `anyOf[enum, single-ref]` to `anyOf[enum, oneOf[4 refs]]`. The discriminator generates `oneOf` instead of `anyOf` for the union branches.
**Why it happens:** Pydantic uses `oneOf` for discriminated unions (correct behavior -- exactly one branch matches).
**How to avoid:** This is expected and correct. Verify schema looks clean but don't try to force `anyOf`.
**Warning signs:** `test_output_schema.py` failures if it snapshots exact schema structure.
**Evidence:** [VERIFIED: local spike -- `oneOf` for discriminator union, `anyOf` for regular union]

### Pitfall 3: Middleware loc path noise
**What goes wrong:** Discriminated union errors include `tagged-union[...]` in the loc path, which `_clean_loc` doesn't strip.
**Why it happens:** `tagged-union[...]` starts with lowercase `t`, so `_clean_loc`'s filter keeps it.
**How to avoid:** This is acceptable -- the middleware's `_format_validation_errors` uses `e["msg"]` for non-`extra_forbidden` errors, so the loc noise doesn't affect agent-facing messages. No middleware changes needed.
**Evidence:** [VERIFIED: local spike -- middleware filters work correctly with discriminator errors]

### Pitfall 4: Test construction changes
**What goes wrong:** Tests that construct `DateFilter(this="d")` still work because `ThisPeriodFilter` etc. are separate classes. But `DateFilter` is now a type alias, so `DateFilter(this="d")` will fail -- you can't instantiate a type alias.
**Why it happens:** `DateFilter` is `Annotated[Union[...], Discriminator(...)]`, not a class.
**How to avoid:** Update all test constructions to use the concrete classes: `ThisPeriodFilter(this="d")`, `LastPeriodFilter(last="3d")`, `AbsoluteRangeFilter(before="2026-04-14")`. Or construct via dict: `{"this": "d"}` in model_validate calls.
**Warning signs:** `TypeError: 'type' object is not callable` or similar at test time.
**Evidence:** [VERIFIED: DateFilter becomes Annotated type alias, not instantiable]

### Pitfall 5: Domain defer hint detection
**What goes wrong:** `domain.py:187` checks `isinstance(value, DateFilter)` and then accesses `value.after`/`value.before`. After refactor, `isinstance(value, DateFilter)` matches ANY filter type. Accessing `.after` on `ThisPeriodFilter` raises `AttributeError`.
**Why it happens:** D-18 correctly identifies this. Must change to `isinstance(value, AbsoluteRangeFilter)`.
**How to avoid:** Import `AbsoluteRangeFilter` at runtime (not in `TYPE_CHECKING`) and use it in `isinstance()`.
**Evidence:** [VERIFIED: codebase inspection of domain.py:187-191]

### Pitfall 6: Resolve dates TYPE_CHECKING import
**What goes wrong:** `resolve_dates.py` imports `DateFilter` inside `TYPE_CHECKING`. After refactor, `isinstance` dispatch needs `ThisPeriodFilter`, `LastPeriodFilter`, `NextPeriodFilter`, `AbsoluteRangeFilter` at runtime.
**Why it happens:** Current code uses attribute probing (`if df.this is not None`), which doesn't need runtime types. New code uses `isinstance`, which does.
**How to avoid:** Move imports out of `TYPE_CHECKING` block for all 4 concrete classes.
**Evidence:** [VERIFIED: resolve_dates.py:16-17 uses TYPE_CHECKING for DateFilter import]

## Code Examples

### 1. Concrete filter model with typed bounds [VERIFIED: local spike]

```python
class AbsoluteRangeFilter(QueryModel):
    __doc__ = ABSOLUTE_RANGE_FILTER_DOC
    before: Annotated[
        Literal["now"] | AwareDatetime | date | None,
        BeforeValidator(_reject_naive_datetime),
    ] = Field(default=None, description=ABSOLUTE_RANGE_BEFORE)
    after: Annotated[
        Literal["now"] | AwareDatetime | date | None,
        BeforeValidator(_reject_naive_datetime),
    ] = Field(default=None, description=ABSOLUTE_RANGE_AFTER)
```

### 2. Resolver isinstance dispatch (replaces attribute probing)

```python
# Before:
if df.this is not None:
    after, before = _resolve_this(df.this, now, week_start=week_start)
# After:
if isinstance(df, ThisPeriodFilter):
    after, before = _resolve_this(df.this, now, week_start=week_start)
```

### 3. Absolute parse with typed input (replaces string parsing)

```python
# Before: value is str, needs fromisoformat() + _is_date_only()
def _parse_absolute_after(value: str, now: datetime) -> datetime:
    if value == "now": return now
    if _is_date_only(value):
        d = date.fromisoformat(value)
        return datetime(d.year, d.month, d.day, tzinfo=now.tzinfo)
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None and now.tzinfo is not None:
        return dt.replace(tzinfo=now.tzinfo)  # WR-01 defensive fix
    return dt

# After: value is Literal["now"] | AwareDatetime | date, already parsed
def _parse_absolute_after(value: Literal["now"] | AwareDatetime | date, now: datetime) -> datetime:
    if value == "now": return now
    if isinstance(value, date) and not isinstance(value, datetime):
        return datetime(value.year, value.month, value.day, tzinfo=now.tzinfo)
    assert value.tzinfo is not None  # contract guarantees AwareDatetime
    return value
```

### 4. Domain isinstance fix

```python
# Before (domain.py:187):
if field_name == "defer" and isinstance(value, DateFilter):
    if value.after == "now": ...

# After:
from omnifocus_operator.contracts.use_cases.list._date_filter import AbsoluteRangeFilter
if field_name == "defer" and isinstance(value, AbsoluteRangeFilter):
    if value.after == "now": ...
```

### 5. Bound ordering validator with type dispatch

```python
@model_validator(mode="after")
def _validate_ordering(self) -> AbsoluteRangeFilter:
    if self.before is None or self.after is None:
        return self
    if self.before == "now" or self.after == "now":
        return self  # D-10: skip when either is "now"
    # Normalize to naive datetime for comparison
    after_dt = _to_naive(self.after)
    before_dt = _to_naive(self.before)
    if after_dt > before_dt:
        raise ValueError(err.DATE_FILTER_REVERSED_BOUNDS.format(after=self.after, before=self.before))
    return self

def _to_naive(v: AwareDatetime | date) -> datetime:
    if isinstance(v, datetime):
        return v.replace(tzinfo=None)
    return datetime(v.year, v.month, v.day)
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` |
| Quick run command | `uv run pytest tests/test_date_filter_contracts.py tests/test_date_filter_constants.py tests/test_resolve_dates.py tests/test_service_domain.py -x -q` |
| Full suite command | `uv run pytest -x -q` |

### Phase Requirements -> Test Map

Phase 48 has no formal requirement IDs in REQUIREMENTS.md -- it's a structural refactor. The test map covers the behavioral contracts that must be preserved:

| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| Shorthand filter construction (this/last/next) | unit | `uv run pytest tests/test_date_filter_contracts.py -x -q` | Yes (rewrite needed) |
| Absolute filter construction (before/after) | unit | `uv run pytest tests/test_date_filter_contracts.py -x -q` | Yes (rewrite needed) |
| Naive datetime rejection | unit | `uv run pytest tests/test_date_filter_contracts.py -x -q` | New tests needed |
| Typed bound parsing (date vs AwareDatetime) | unit | `uv run pytest tests/test_date_filter_contracts.py -x -q` | New tests needed |
| Empty filter rejection | unit | `uv run pytest tests/test_date_filter_contracts.py -x -q` | Yes (update error message match) |
| Reversed bounds rejection | unit | `uv run pytest tests/test_date_filter_contracts.py -x -q` | Yes (update to typed inputs) |
| Discriminator routing | unit | `uv run pytest tests/test_date_filter_contracts.py -x -q` | Rewrite from union discrimination tests |
| Resolver dispatch (isinstance) | unit | `uv run pytest tests/test_resolve_dates.py -x -q` | Yes (update constructions) |
| Domain defer hint detection | unit | `uv run pytest tests/test_service_domain.py -x -q` | Yes (update constructions) |
| Error constants (dead removal, new additions) | unit | `uv run pytest tests/test_date_filter_constants.py -x -q` | Yes (rewrite for new constants) |
| Cross-path equivalence | integration | `uv run pytest tests/test_cross_path_equivalence.py -x -q` | Yes (update if constructions used) |
| List pipeline integration | integration | `uv run pytest tests/test_list_pipelines.py -x -q` | Yes (update if constructions used) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_date_filter_contracts.py tests/test_date_filter_constants.py tests/test_resolve_dates.py tests/test_service_domain.py -x -q`
- **Per wave merge:** `uv run pytest -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
None -- existing test infrastructure covers all phase requirements. Tests need updating (new constructions, new test cases for typed bounds / naive rejection), not new framework setup.

## Scope Inventory

### Files to modify (source)

| File | Change | Complexity |
|------|--------|------------|
| `_date_filter.py` | Replace flat class with 4 models + discriminator | HIGH -- core of the refactor |
| `descriptions.py` | Remove `DATE_FILTER_DOC`, add 9 new constants, update 6 field descs | MEDIUM |
| `errors.py` | Delete 4 dead constants, add `ABSOLUTE_RANGE_FILTER_EMPTY`, add `DATE_FILTER_INVALID_TYPE` | LOW |
| `__init__.py` | Add 4 new class exports | LOW |
| `resolve_dates.py` | Rewrite dispatch to isinstance, rewrite parse functions for typed input, remove `_is_date_only`, remove WR-01 | MEDIUM |
| `domain.py` | Change isinstance target, move import out of TYPE_CHECKING | LOW |

### Files to modify (tests)

| File | Change | Test Count |
|------|--------|------------|
| `test_date_filter_contracts.py` | Rewrite constructions, add naive datetime tests, update error matches | ~40 tests |
| `test_date_filter_constants.py` | Rewrite for new constants (dead ones removed) | ~5 tests |
| `test_resolve_dates.py` | Update NOW to tz-aware, update constructions to concrete classes | ~40 tests |
| `test_service_domain.py` | Update DateFilter constructions to concrete classes | ~15 tests |
| `test_cross_path_equivalence.py` | Check for DateFilter constructions (likely none -- uses RepoQuery) | Inspection needed |
| `test_list_pipelines.py` | Check for DateFilter constructions | Inspection needed |

### Import graph (who imports what from `_date_filter.py`)

| Importer | Current import | After refactor |
|----------|---------------|----------------|
| `__init__.py` | `DateFilter` | `DateFilter, ThisPeriodFilter, LastPeriodFilter, NextPeriodFilter, AbsoluteRangeFilter` |
| `tasks.py` | `DateFilter` | `DateFilter` (unchanged -- type alias used in field annotation) |
| `resolve_dates.py` | `DateFilter` (TYPE_CHECKING) | `ThisPeriodFilter, LastPeriodFilter, NextPeriodFilter, AbsoluteRangeFilter` (runtime) |
| `domain.py` | `DateFilter` (runtime) | `AbsoluteRangeFilter` (runtime) |
| `test_resolve_dates.py` | `DateFilter` | Concrete classes |
| `test_service_domain.py` | `DateFilter` | Concrete classes |
| `test_date_filter_contracts.py` | `DateFilter` | `DateFilter` + concrete classes |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `test_cross_path_equivalence.py` and `test_list_pipelines.py` use `ListTasksRepoQuery` (not `DateFilter`) and don't need construction changes | Scope Inventory | LOW -- easy to fix if they do construct DateFilter directly |
| A2 | `_clean_loc` in middleware passes discriminator error locs through without issues | Common Pitfalls | LOW -- verified that middleware uses `e["msg"]` not loc for non-extra_forbidden errors |

## Open Questions

1. **`DATE_FILTER_EMPTY` reference check (D-17)**
   - What we know: Currently used only in `_date_filter.py:79`. After refactor, `AbsoluteRangeFilter` uses new `ABSOLUTE_RANGE_FILTER_EMPTY`.
   - What's unclear: Whether any other code path references `DATE_FILTER_EMPTY` outside the refactored file.
   - Recommendation: Grep during implementation. If no other references, delete. If referenced, keep with deprecation comment. [ASSUMED: likely no other references based on grep showing only `_date_filter.py` usage]

2. **D-17b implementation approach**
   - What we know: Discriminator cannot safely raise `ValueError` for non-dict input (bypasses middleware). Must route to `absolute_range` as fallback for Pydantic compatibility.
   - What's unclear: Whether the D-17b custom error message can still be achieved, or if the generic Pydantic `model_type` error is sufficient.
   - Recommendation: The generic error ("Input should be a valid dictionary or instance of AbsoluteRangeFilter") is adequate for the non-dict case since agents always send JSON objects. The `DATE_FILTER_INVALID_TYPE` constant defined in D-17b can be added as documentation but may not be reachable in the discriminator function without breaking middleware compatibility. Consider: if a custom message is important, use a `before` validator on the outer union field instead of the discriminator. This is a Claude's-discretion area.

## Sources

### Primary (HIGH confidence)
- Pydantic 2.12.5 -- verified locally via `uv run python` spikes
- Codebase: `_date_filter.py`, `resolve_dates.py`, `domain.py`, `middleware.py` -- direct inspection
- CONTEXT.md / design todo -- decisions D-01 through D-19

### Secondary (MEDIUM confidence)
- Spike results from design document -- reproduced and verified in this session

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all tools already in project, verified working
- Architecture: HIGH -- design fully specified in CONTEXT.md, all spikes verified
- Pitfalls: HIGH -- each pitfall verified with local spikes against Pydantic 2.12.5

**Research date:** 2026-04-10
**Valid until:** 2026-05-10 (stable -- Pydantic 2.x API unlikely to change)
