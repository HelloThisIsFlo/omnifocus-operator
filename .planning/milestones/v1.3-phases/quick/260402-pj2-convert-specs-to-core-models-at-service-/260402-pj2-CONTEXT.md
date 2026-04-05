# Quick Task 260402-pj2: Convert specs to core models at service boundary - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Task Boundary

Convert spec types (FrequencyAddSpec, EndConditionSpec) to core models (Frequency, EndCondition) at the service boundary. Remove union signatures and hasattr duck-typing from payload.py and builder.py. Document the convention.

Related todo: `.planning/todos/pending/2026-04-02-convert-specs-to-core-models-at-service-boundary.md`

</domain>

<decisions>
## Implementation Decisions

### Conversion site
- New `service/convert.py` module — dedicated spec→core conversion functions
- Structure-over-discipline: the module's existence IS the documentation; agents see the module and know where conversion goes
- Both pipelines (add + edit) import from the same source — no duplication risk
- Dependency direction is clean: service layer already depends on both `contracts/` and `models/`

### Frequency round-trip elimination
- The add pipeline currently converts FrequencyAddSpec→Frequency for normalization, then converts BACK to FrequencyAddSpec (service.py:466-472) — this is wrong
- After conversion, keep the core Frequency directly on `self`, don't re-attach to the command
- The round-trip was an artifact of the agent taking the shortest path ("put things back the way they were") rather than restructuring — exactly the kind of problem structure-over-discipline prevents

### Convention documentation
- Update `docs/architecture.md` package structure to list `convert.py` with its responsibility
- Reinforce the existing rule in `docs/model-taxonomy.md` (line 98 already states "the pipeline resolves the Spec into the core model before the repo boundary")
- Do NOT add to CLAUDE.md — it already routes agents to both docs; CLAUDE.md is the routing layer, not the content layer

</decisions>

<specifics>
## Specific Ideas

- `convert.py` contains pure functions: `frequency_from_spec(FrequencyAddSpec) -> Frequency` and `end_condition_from_spec(EndConditionSpec | None) -> EndCondition | None`
- `payload.py::_build_repetition_rule_payload` signature changes from union types to core-only: `frequency: Frequency`, `end: EndCondition | None`
- `builder.py::build_rrule` signature changes similarly — removes union types, restores `isinstance` dispatch for end condition
- FrequencyEditSpec in domain.py:merge_frequency() is NOT in scope — it carries UNSET/None/value semantics, outputs Frequency, and is fine as-is

</specifics>

<canonical_refs>
## Canonical References

- `docs/model-taxonomy.md:98` — "the pipeline resolves the Spec into the core model before the repo boundary"
- `docs/structure-over-discipline.md` — module boundaries as decision guides
- `docs/architecture.md` — service layer module responsibilities, package structure
- `.planning/todos/pending/2026-04-02-convert-specs-to-core-models-at-service-boundary.md` — original todo with problem statement

</canonical_refs>
