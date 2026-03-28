# Phase 33: Write Model, Validation & Bridge - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-28
**Phase:** 33-write-model-validation-bridge
**Areas discussed:** Edit partial update design, Write model topology, Bridge OmniJS strategy, Warning & error catalog, Tool descriptions

---

## Edit Partial Update Design

| Option | Description | Selected |
|--------|-------------|----------|
| Nested wrapper | `PatchOrClear[RepetitionRuleEditSpec]` with inner Patch fields. Groups related fields, agent sends `{schedule: "from_completion"}` for partial updates. Follows actions block precedent. | ✓ |
| Flat root fields | schedule, basedOn, end, frequency as separate PatchOrClear fields on EditTaskCommand. Each independently patchable but clutters command model. | |
| Separate clear + set | Explicit `clear_repetition_rule` action. Unambiguous but breaks PatchOrClear symmetry. | |

**User's choice:** Nested wrapper
**Notes:** Milestone spec lines 37-48 explicitly describe this approach: `repetitionRule: null` = remove, omit = no change, root fields independently updatable within the wrapper. User reviewed code examples of all three options before deciding. Flat root fields couldn't express "clear the whole rule" cleanly.

---

## Write Model Topology

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse read model for add | AddTaskCommand embeds RepetitionRule directly. Same shape, minor extra="forbid" gap. | |
| Dedicated write model for both | RepetitionRuleAddSpec + RepetitionRuleEditSpec. Full strictness on both paths. | ✓ |
| Reuse for add, dedicated for edit | Hybrid approach. Minimal new types but conceptual split. | |

**User's choice:** Dedicated write models for both add and edit
**Notes:** User wanted `extra="forbid"` enforcement on both paths. Architecture doc (line 287) already had `RepetitionRuleSpec (future)` as a planned example. User chose noun-first naming (`RepetitionRuleAddSpec` / `RepetitionRuleEditSpec`) over verb-first (`AddRepetitionRuleSpec`). Rationale stress-tested against existing patterns: top-level commands are verb-primary (AddTaskCommand), nested value objects are noun-primary (TagAction, MoveAction). RepetitionRule is the first domain concept needing separate add/edit nested models — previous concepts (tags, move) use fundamentally different structures per use case, not different shapes of the same concept. User requested instructions for another agent to update the architecture doc naming taxonomy.

---

## Bridge OmniJS Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| 4-field bridge format | Python sends {ruleString, scheduleType, anchorDateKey, catchUpAutomatically}. Symmetric with read path. | ✓ |
| Structured passthrough | Python sends internal model shape. Bridge decodes. | |
| RRULE-only | Python sends only RRULE string. Bridge can't derive metadata. | |

**User's choice:** 4-field bridge format
**Notes:** Spec-mandated (milestone spec line 52, architecture.md line 639). User asked to surface any uncertainties — three were identified and resolved by reading the OmniJS API guide together: (1) Constructor takes 5 params with deprecated null second arg, (2) scheduleType and anchorDateKey are OmniJS enum objects requiring reverse lookups, (3) `task.repetitionRule = null` confirmed for clearing. All RepetitionRule properties are read-only — modification = construct new + assign.

---

## Warning & Error Catalog

| Option | Description | Selected |
|--------|-------------|----------|
| Catalog as presented | Errors for structurally invalid input, warnings for suspect-but-valid operations. | ✓ |

**User's choice:** Catalog accepted with one refinement
**Notes:** User asked about `monthly_day_in_month` with empty `onDates` — confirmed it should normalize to plain `monthly` at the service layer (not just warn). The warning educates the agent; the normalization ensures clean round-trip (write as monthly, read back as monthly).

---

## Tool Descriptions

| Option | Description | Selected |
|--------|-------------|----------|
| Full inline | ~15 lines listing every type, field, constraint. Self-contained. | ✓ |
| Key patterns + examples | Example-driven, doesn't list every type. | |
| Minimal + schema | Brief mention, rely on JSON Schema. | |

**User's choice:** Full inline
**Notes:** Major discovery during discussion: the inputSchema is completely opaque. Write tools use `items: list[dict[str, Any]]`, so agents see `{"type": "array", "items": {"additionalProperties": true, "type": "object"}}` — zero field information. The docstring is the ONLY guidance. This made full inline documentation mandatory, not optional. Multiple iterations on format: (1) interval shown as `N` on every frequency type for clarity, (2) `weekly` vs `weekly_on_days` distinction clarified ("no specific day constraint" vs "specific days"), (3) `monthly_day_in_month` onDates range and -1 on separate line for readability, (4) 2-3 examples per tool, (5) `end` uses "omit for no end" on add_tasks, "null to clear" on edit_tasks. User captured the inputSchema gap context document for separate investigation (typed parameters + custom errors via FastMCP middleware).

---

## Claude's Discretion

- Service pipeline step ordering and internal merge algorithm
- Bridge JS implementation details (reverse enum lookups)
- Test structure and organization
- Exact warning/error message wording
- RRULE builder inverse function placement

## Deferred Ideas

- Architecture doc naming taxonomy update (instructions provided to user for separate agent)
- Typed inputSchema for write tools (full context document provided to user for research)
- Old test names referencing FrequencySpec (from Phase 32.1)
