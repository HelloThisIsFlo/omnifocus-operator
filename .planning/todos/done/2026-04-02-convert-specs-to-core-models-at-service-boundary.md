---
created: 2026-04-02T14:46:20.410Z
title: Convert specs to core models at service boundary
area: service
files:
  - src/omnifocus_operator/service/payload.py:66-70
  - src/omnifocus_operator/service/payload.py:120-123
  - src/omnifocus_operator/rrule/builder.py:70-71
  - src/omnifocus_operator/rrule/builder.py:103-108
---

## Problem

Contract spec types leak past the service boundary into lower layers (builder, payload). This forces union signatures (`Frequency | FrequencyAddSpec`, `EndCondition | EndConditionSpec`) and in the case of `EndConditionSpec`, caused `isinstance` dispatch to be replaced with `hasattr` duck-typing in `builder.py`.

The service layer should work with core models internally. Specs are the agent's language; core models are the system's language. The conversion should happen early — once you're past the command boundary, everything is core models.

**Pre-existing (on main):**
- `builder.py:70` — `frequency: Frequency | FrequencyAddSpec`
- `payload.py:120` — `frequency: Frequency | FrequencyAddSpec`

**Added by phase 36.4:**
- `builder.py:71` — `end: EndByDate | EndByOccurrences | EndConditionSpec | None`
- `payload.py:123` — `end: EndCondition | EndConditionSpec | None`
- `builder.py:103-108` — `hasattr` duck-typing replacing `isinstance`

Note: `FrequencyEditSpec` in `domain.py:merge_frequency()` is different — it carries UNSET/None/value semantics needed for the merge. The output is already a `Frequency`. This is fine as-is.

## Solution (proposal)

Convert specs to core models in the payload builder before passing to lower layers. The service already does a similar round-trip for frequency normalization (service.py:461) — extend that pattern to the payload boundary.

This should also restore `isinstance` dispatch in builder.py and remove the union signatures.

## Convention update

Document this as a convention — the service layer operates on core models, not specs. Candidate locations: `docs/architecture.md` (service layer section), `docs/model-taxonomy.md` (type constraint boundary section), or `CLAUDE.md` (service layer convention). Decide during implementation which is the right home.
