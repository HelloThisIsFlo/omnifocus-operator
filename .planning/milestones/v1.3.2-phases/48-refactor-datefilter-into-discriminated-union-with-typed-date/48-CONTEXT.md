# Phase 48: Refactor DateFilter into discriminated union with typed date bounds - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the flat 5-field `DateFilter` with a 4-model discriminated union (`ThisPeriodFilter | LastPeriodFilter | NextPeriodFilter | AbsoluteRangeFilter`). Type `before`/`after` as `Literal["now"] | AwareDatetime | date | None` to structurally reject naive datetimes. Cascade changes through resolver, domain, descriptions, errors, and tests.

This phase is purely structural. No new filter capabilities, no timezone strategy changes, no new date fields.

</domain>

<decisions>
## Implementation Decisions

### Timezone scope
- **D-01:** Phase 48 is structural consistency only. Full commit to `AwareDatetime` types on `before`/`after` fields.
- **D-02:** Timezone interpretation (date-only → which midnight?) stays unchanged in `resolve_dates.py`. The resolver's existing behavior of inheriting `now.tzinfo` for date-only inputs persists.
- **D-03:** The companion timezone todo (`.planning/todos/pending/2026-04-10-rethink-timezone-handling-strategy-for-date-filter-inputs.md`) is a separate future phase. Not folded into Phase 48.

### Callable Discriminator for union dispatch
- **D-04:** Use a Pydantic v2 callable `Discriminator` for the `DateFilter` union — not a simple `X | Y | Z` type alias. Routes to exactly one branch based on which key is present in the input dict. Default route → `AbsoluteRangeFilter`.
- **D-05:** Rationale: `AbsoluteRangeFilter` has all-optional fields, which causes Pydantic's default smart-union dispatch to produce noisy multi-branch errors for malformed input (`{}`, mixed keys). The discriminator ensures clean single-branch errors, preserving the project's educational error philosophy.
- **D-06:** JSON Schema is unchanged — callable discriminators are Python-side routing, not schema annotations. Agents see the same `anyOf`.
- **D-07:** Implementation shape:
  ```python
  from pydantic import Discriminator, Tag
  from typing import Annotated, Union

  def _route_date_filter(v: Any) -> str:
      if isinstance(v, dict):
          if "this" in v: return "this_period"
          if "last" in v: return "last_period"
          if "next" in v: return "next_period"
          return "absolute_range"
      raise ValueError("Expected an object")

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
- **D-08:** New pattern in the codebase. `EndConditionSpec` keeps its simple union (different problem shape — no all-optional variant). Two union patterns is justified by two different union shapes.

### Typed bound ordering validator
- **D-09:** `AbsoluteRangeFilter` keeps the `after <= before` model_validator. Normalize both to naive `datetime` for comparison: `date` → `datetime(midnight)`, `AwareDatetime` → `.replace(tzinfo=None)`. Replace `_parse_to_comparable` with a type-dispatch helper.
- **D-10:** `Literal["now"]` on either side → skip comparison (can't know "now" at validation time).
- **D-11:** Best-effort early catch, not authoritative. Mixed-type edge cases (e.g., date vs AwareDatetime on the same day) may not be perfectly compared due to timezone ambiguity. The resolver is the authoritative check. Priority: no false rejections for valid queries.

### Naive datetime error UX
- **D-12:** Add a `BeforeValidator` (`mode="before"`) on `before` and `after` fields to intercept naive datetime strings before Pydantic's union dispatch. Pattern detection only — check if string contains `T` and lacks timezone indicator. No actual datetime parsing.
- **D-13:** Produces a clean educational error: "Datetime must include timezone (e.g. '2026-04-01T14:00:00Z' or '2026-04-01T14:00:00+02:00'). Date-only ('2026-04-01') is also accepted."
- **D-14:** `mode="after"` won't work — the value fails all union branches before an after-validator runs. `mode="before"` is the only option for input interception.

### Error constant cleanup
- **D-15:** Delete 4 dead error constants: `DATE_FILTER_MIXED_GROUPS`, `DATE_FILTER_MULTIPLE_SHORTHAND`, `DATE_FILTER_INVALID_THIS_UNIT`, `DATE_FILTER_INVALID_ABSOLUTE`. The union makes these structurally unreachable.
- **D-16:** New `ABSOLUTE_RANGE_FILTER_EMPTY` replaces `DATE_FILTER_EMPTY` for the AbsoluteRangeFilter model_validator:
  ```
  "AbsoluteRangeFilter requires at least one of: before or after.
   Each accepts an ISO date ('2026-04-01'), ISO datetime with timezone
   ('2026-04-01T14:00:00Z'), or 'now'."
  ```
- **D-17:** `DATE_FILTER_EMPTY` itself may become dead (check during implementation — depends on whether any other code path references it).
- **D-17b:** New `DATE_FILTER_INVALID_TYPE` for the discriminator's non-dict fallback:
  ```
  "Date filter must be an object. Use a shorthand period
   ({\"this\": \"w\"}, {\"last\": \"3d\"}, {\"next\": \"1m\"})
   or absolute bounds ({\"before\": \"...\", {\"after\": \"...\"})."
  ```

### domain.py isinstance fix
- **D-18:** `isinstance(value, DateFilter)` at `domain.py:187` must change to `isinstance(value, AbsoluteRangeFilter)`. The todo's reasoning (TypeError) is incorrect — Python 3.12 supports `isinstance` with `types.UnionType`. The real bug: `isinstance(value, DateFilter)` matches ANY filter type, then `value.after` raises `AttributeError` on non-AbsoluteRangeFilter types.
- **D-19:** Move `AbsoluteRangeFilter` import out of any `TYPE_CHECKING` block — `isinstance` needs it at runtime.

### Claude's Discretion
- Internal naming of the discriminator routing function
- Whether `_validate_duration` is duplicated on `LastPeriodFilter`/`NextPeriodFilter` or extracted to a shared private helper
- Test file organization and migration approach (which files to update, order of changes)
- Exact placement of the `BeforeValidator` (field-level vs shared helper)
- Whether `DATE_FILTER_EMPTY` is still referenced elsewhere (delete or keep)
- Minor wording adjustments to error messages

### Folded Todos
- **Refactor DateFilter into discriminated union with typed date bounds** (`.planning/todos/pending/2026-04-10-refactor-datefilter-into-discriminated-union-with-typed-date.md`) — this IS the phase. The todo serves as the design document. Everything specified in the todo is in scope unless overridden by decisions above.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design document (PRIMARY)
- `.planning/todos/pending/2026-04-10-refactor-datefilter-into-discriminated-union-with-typed-date.md` — Complete design: model structure, field types, spike results, validator migration, cascading changes. This CONTEXT.md captures discussion decisions that refine or override the todo.

### Source files (in scope)
- `src/omnifocus_operator/contracts/use_cases/list/_date_filter.py` — Current flat DateFilter model (the refactor target)
- `src/omnifocus_operator/contracts/use_cases/list/__init__.py` — Exports (add 4 new model classes)
- `src/omnifocus_operator/agent_messages/descriptions.py` — Description constants (remove DATE_FILTER_DOC, add 9 new constants per todo)
- `src/omnifocus_operator/agent_messages/errors.py` — Error constants (delete 4 dead, add ABSOLUTE_RANGE_FILTER_EMPTY)
- `src/omnifocus_operator/service/resolve_dates.py:118-252` — Resolver dispatch rewrite (field-probing → isinstance), remove WR-01, remove `_is_date_only`, remove `_parse_to_comparable`
- `src/omnifocus_operator/service/domain.py:187-191` — isinstance fix (DateFilter → AbsoluteRangeFilter)

### Companion todo (explicitly deferred)
- `.planning/todos/pending/2026-04-10-rethink-timezone-handling-strategy-for-date-filter-inputs.md` — Timezone strategy. Separate phase. Phase 48 does not touch timezone interpretation.

### Test files (in scope)
- `tests/test_resolve_dates.py` — Make NOW fixture tz-aware (UTC), update test constructions
- `tests/test_date_filter_contracts.py` — Update to union shape
- `tests/test_date_filter_constants.py` — Update to union shape
- `tests/test_cross_path_equivalence.py` — Update to union shape
- `tests/test_list_pipelines.py` — Update to union shape
- `tests/test_service_domain.py` — Update to union shape

### Architecture & conventions
- `docs/model-taxonomy.md` — Model naming conventions (`<noun>Filter` for read-side value objects)
- `src/omnifocus_operator/contracts/shared/repetition_rule.py:70-87` — `EndConditionSpec` pattern reference (simple union — contrast with DateFilter's discriminator approach)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `EndConditionSpec = EndByDateSpec | EndByOccurrencesSpec` in `repetition_rule.py` — union pattern reference (simpler shape, no discriminator needed)
- `QueryModel` base class — provides `extra="forbid"` and model config for read-side query models
- `_DATE_DURATION_PATTERN` and `_THIS_UNIT_PATTERN` regexes — stay at module level, reused by split validators
- `ValidationReformatterMiddleware` — reformats Pydantic errors for agent consumption (may need awareness of discriminator errors)

### Established Patterns
- `AwareDatetime` already used on write side (`add_tasks`, `edit_tasks` contract models) — same import, same rejection semantics
- `@field_validator` + educational error constants — every validator produces a crafted message
- `Literal` types for constrained enums — used in lifecycle (`Literal["complete", "drop"]`)
- Description centralization in `agent_messages/descriptions.py` with AST enforcement tests

### Integration Points
- `ListTasksQuery.due`, `.defer`, `.planned`, etc. — fields typed as `str | DateFilter`. After refactor, `DateFilter` is the Annotated union. The outer field type doesn't change syntactically.
- `_resolve_date_filter_obj()` in `resolve_dates.py` — entry point for resolution dispatch. Signature stays, body rewrites to isinstance.
- `DomainLogic.resolve_date_filters()` in `domain.py` — defer hint detection. isinstance target changes.

</code_context>

<specifics>
## Specific Ideas

### The discriminator is a learning investment
The callable `Discriminator` pattern is new to this codebase. It's added here because DateFilter's union shape (one variant with all-optional fields) produces noisy errors without it. But it's also a pattern worth knowing for future unions with similar shapes.

### Phase 48 output is pre-ship only
The date filter contract is not yet shipped to external users. Phase 48 establishes the structural shape. The timezone todo (separate phase) must be resolved before shipping date filter support publicly.

</specifics>

<deferred>
## Deferred Ideas

### Reviewed Todos (not folded)
- **Rethink timezone handling strategy for date filter inputs** — Explicitly deferred per D-03. Separate future phase. Phase 48 does not touch timezone interpretation.
- **Add date filters to list_projects** — Different scope (new capability, not structural refactor). Reuses v1.3.2 infrastructure after it's stable.

</deferred>

---

*Phase: 48-refactor-datefilter-into-discriminated-union-with-typed-date*
*Context gathered: 2026-04-10*
