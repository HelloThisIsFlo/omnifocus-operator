# Phase 18: Write Model Strictness - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Write models catch agent mistakes at validation time by rejecting unknown fields (`extra="forbid"`) instead of silently discarding them. Read models remain permissive. Additionally, consolidate all warning strings across the codebase into a single reviewable file. No new tools, no behavioral changes visible to agents beyond stricter validation.

</domain>

<decisions>
## Implementation Decisions

### Config architecture
- New `WriteModel` base class with `model_config = ConfigDict(extra="forbid")`
- `WriteModel` lives in `write.py` (not `base.py`) — keeps write concerns together
- All write specs inherit from `WriteModel` instead of `OmniFocusBaseModel`
- Phase 20 (Model Taxonomy) builds on this foundation

### Strictness scope
- **Strict (extra="forbid")**: TaskCreateSpec, TaskEditSpec, MoveToSpec, TagActionSpec, ActionsSpec, and any write-side sub-models
- **Strict for writes**: RepetitionRuleSpec (shared model in common.py) — needs write-side variant or restructuring so reads stay permissive
- **Permissive (unchanged)**: All read models (Task, Project, Tag, Folder), result models (TaskCreateResult, TaskEditResult), common read-side models
- Rule: if it accepts agent input, it's strict. If it's server output or from OmniFocus, it's permissive.

### Error experience
- Follow existing project conventions — agent-first, self-explanatory, no exposed internals
- Study current warning/error patterns in the codebase and match them
- Unknown field errors should read naturally to both humans and LLM agents

### Warning string consolidation
- Extract ALL warning strings across the codebase into a single file (e.g., `warnings.py` or similar)
- Each warning referenced as a constant from that file
- Purpose: lets the project owner review all agent-facing messages in one place
- Includes existing warnings (no-op detection, educational hints) AND new strictness warnings

### Sentinel behavior
- UNSET sentinel must continue supporting three-way patch semantics (omitted / null / value)
- Implementation details are flexible — if sentinel needs changes to work with `extra="forbid"`, that's fine
- Behavior must not change: omitted fields = no change, null = clear, value = set

### Claude's Discretion
- Exact file name and structure for consolidated warnings
- Whether RepetitionRuleSpec needs a write-side copy or can be restructured in-place
- Technical approach to making sentinel work with forbid (if any changes needed)
- Error message wording (within existing convention)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Models & validation
- `src/omnifocus_operator/models/base.py` — OmniFocusBaseModel with ConfigDict (the base all models inherit from)
- `src/omnifocus_operator/models/write.py` — All write specs, UNSET sentinel, sub-models (MoveToSpec, TagActionSpec, ActionsSpec)
- `src/omnifocus_operator/models/common.py` — Shared models including RepetitionRuleSpec (dual read/write use)

### Requirements
- `.planning/REQUIREMENTS.md` — STRCT-01, STRCT-02, STRCT-03 definitions

### Existing patterns (study for convention)
- `src/omnifocus_operator/service.py` — Current warning generation patterns, agent-first error handling
- `tests/test_service.py` lines 417-433 — `test_unknown_fields_ignored` (UAT #20) — this test asserts the OLD behavior and must be updated

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `OmniFocusBaseModel` (base.py): Shared base with alias_generator, validate_by_name/alias — WriteModel inherits this
- `_Unset` sentinel (write.py): Singleton with `__get_pydantic_core_schema__` — already Pydantic-aware
- Existing warning patterns in service.py: Educational messages for no-ops, lifecycle hints

### Established Patterns
- All models inherit from `OmniFocusBaseModel` — single config inheritance point
- Write models override `model_json_schema()` to clean UNSET from JSON schema output
- Warnings returned as `list[str] | None` in result models

### Integration Points
- MCP tool handlers call `model_validate()` on incoming JSON — this is where forbid kicks in
- Service layer generates warnings for no-ops — these strings need extracting to the consolidated file
- `tests/test_models.py` (lines 860-933) and `tests/test_service.py` — write model test coverage

</code_context>

<specifics>
## Specific Ideas

- "Warnings are a first-class citizen in this project — they're really carefully crafted"
- Warning consolidation is about reviewability: one file to scan all agent-facing messages
- User wants to personally review warning strings, so the file should be scannable

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 18-write-model-strictness*
*Context gathered: 2026-03-16*
