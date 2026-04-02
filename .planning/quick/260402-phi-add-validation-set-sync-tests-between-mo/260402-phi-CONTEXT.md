# Quick Task 260402-phi: Add validation set sync tests between models and contracts - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Task Boundary

Add validation set sync tests between models and contracts. Ensure `_VALID_DAY_CODES`, `_VALID_DAY_NAMES`, and a new `_VALID_FREQUENCY_TYPES` set stay in sync with their `Literal` type alias counterparts (`DayCode`, `DayName`, `FrequencyType`) in contracts/shared/repetition_rule.py.

</domain>

<decisions>
## Implementation Decisions

### Test location
- Add sync tests as a new `TestValidationSetSync` class in `tests/test_type_boundary.py` (same file). Both are type-boundary tests — one enforces the boundary structurally (AST), the other enforces value sync across it (runtime).

### Frequency.type validator
- Add full runtime validator: `_VALID_FREQUENCY_TYPES` set + `@field_validator` on `Frequency.type` that raises `ValueError` with `REPETITION_INVALID_FREQUENCY_TYPE`. Matches the pattern of `normalize_day_codes`/`normalize_day_name` exactly.

### Claude's Discretion
- Naming of the shared validation function (e.g., `validate_frequency_type` to match `normalize_day_codes` pattern)
- Whether to also export `_VALID_FREQUENCY_TYPES` in `__all__` (follow existing pattern for `_VALID_DAY_CODES`/`_VALID_DAY_NAMES` — they're private, not exported)

</decisions>

<specifics>
## Specific Ideas

- Sync tests use `set(get_args(DayCode)) == _VALID_DAY_CODES` pattern (from the todo)
- Reuse existing `REPETITION_INVALID_FREQUENCY_TYPE` error message from `agent_messages/errors.py`
- The `_validate_frequency_type` in contracts already exists — model-side validator should be independent (checks against `_VALID_FREQUENCY_TYPES` set, not `get_args()`)

</specifics>

<canonical_refs>
## Canonical References

- `.planning/todos/pending/2026-04-02-add-validation-set-sync-tests-between-models-and-contracts.md` — original todo with full problem/solution spec

</canonical_refs>
