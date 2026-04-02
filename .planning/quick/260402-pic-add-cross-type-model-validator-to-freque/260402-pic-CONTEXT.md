# Quick Task 260402-pic: Add cross-type model validator to FrequencyEditSpec - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Task Boundary

Add a `@model_validator` to `FrequencyEditSpec` that calls `check_frequency_cross_type_fields()` with `is_set()` guards, mirroring `FrequencyAddSpec` but respecting patch semantics.

</domain>

<decisions>
## Implementation Decisions

### Validation scope
- Follow existing codebase pattern (TagAction, MoveAction): only validate when both sides are present in the patch
- When `type` is UNSET, skip the check entirely — service layer catches contradictions after merging
- Use `is_set()` guards, passing `None` for UNSET fields

### Error messages
- Reuse `check_frequency_cross_type_fields()` directly — no duplicate or custom messages
- Same function, same errors as add path — just guarded by `is_set()`

### Claude's Discretion
- Test structure and coverage depth

</decisions>

<specifics>
## Specific Ideas

- Existing precedent: `TagAction._validate_incompatible_tag_edit_modes` (actions.py:44) uses `is_set()` guards for cross-field validation on patch models
- Service layer already validates merged result at service.py:707-710 via `Frequency.model_validate(merged)` — this fix adds earlier feedback for obviously contradictory patches

</specifics>

<canonical_refs>
## Canonical References

- `src/omnifocus_operator/contracts/shared/repetition_rule.py` — FrequencyAddSpec (has validator), FrequencyEditSpec (missing it)
- `src/omnifocus_operator/models/repetition_rule.py:149` — `check_frequency_cross_type_fields()` shared function
- `src/omnifocus_operator/contracts/shared/actions.py:44` — TagAction pattern precedent

</canonical_refs>
