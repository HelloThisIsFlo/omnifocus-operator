---
created: 2026-04-01T12:41:26.600Z
title: Reserve Literal and Annotated types for contract models only
area: models
files:
  - src/omnifocus_operator/models/repetition_rule.py
  - src/omnifocus_operator/contracts/shared/repetition_rule.py
---

## Problem

We have two audiences for Pydantic model fields:

- **Contract models** (`contracts/`) face agents — their JSON Schema must be self-documenting. `Literal` types emit `enum`, `Annotated[int, Field(ge=..., le=...)]` emits `minimum`/`maximum`. This is exactly where structure-over-discipline pays off.
- **Core models** (`models/`) are also used internally by parsers and builders that construct instances from dynamic data (e.g., `str.split(",")` returns `list[str]`, not `list[Literal["MO", ...]]`). Putting Literal/Annotated types here forces type escape hatches (`cast`, `type: ignore`) at every internal construction site — and this codebase currently has zero of either.

Currently `DayCode` (Literal) and `OnDate` (Annotated) are used on both the core `Frequency` model and the contract specs. A quick fix reverted the core model to plain types, but the convention isn't documented or audited across the codebase.

## Solution

Establish and enforce: **Literal and Annotated constraint types live on contract models, core models use plain types.** Runtime validation (via `mode="before"` validators) still enforces correctness on core models — the type system just doesn't over-promise to the static checker.

Concretely:
- Audit all `Literal[...]` and `Annotated[..., Field(ge=..., le=...)]` usages across `models/` — any that exist solely for JSON Schema benefit should move to `contracts/` only
- Example: `Frequency.on_days` should be `list[str]` in core, `list[DayCode]` in contracts
- Ensure the shared validation functions (e.g., `check_frequency_cross_type_fields`) use signatures compatible with both (`Sequence[str]` instead of `list[DayCode]`)
- Document this convention (probably in `docs/model-taxonomy.md` since it already covers model vs contract boundaries)
