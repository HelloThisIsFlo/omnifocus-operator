# Phase 32: Read Model Rewrite - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-28
**Phase:** 32-read-model-rewrite
**Areas discussed:** Frequency object shape, End condition shape, Breaking change strategy, MINUTELY/HOURLY handling, BYDAY parsing, Schedule derivation, Malformed RRULE handling, Interval emit behavior, Golden master impact, monthly_day_of_week vocabulary, Module structure

---

## Frequency Object Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Typed discriminated union | Each frequency type is its own Pydantic model with only its relevant fields. 8 subtypes. | ✓ |
| Flat with all optional fields | Single model class, type field + all possible fields (null when irrelevant). | |

**User's choice:** Typed discriminated union
**Notes:** Agent-first design — LLM sees exactly what applies, no null noise. Pydantic v2 `Field(discriminator="type")` handles this natively.

---

## End Condition Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Single-key dict (moveTo pattern) | Key IS the type, value IS the data. null for no end. | ✓ |
| Tagged union | Explicit type discriminator field. Consistent with frequency pattern. | |
| Separate fields | Flat nullable fields (endDate, endOccurrences). | |

**User's choice:** Single-key dict
**Notes:** User initially leaned this way, then asked to check the milestone spec. Spec line 34 already locked this decision. User confirmed: "I see, option one is the best." Also confirmed "omit for no end" per spec.

---

## Breaking Change Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Clean break | Replace ruleString with structured fields. No transition period. | ✓ |
| Transition period | Keep ruleString alongside for one version, remove in v1.3. | |

**User's choice:** Clean break
**Notes:** Pre-release, single user, installed from source. Spec line 56 confirms acceptable.

---

## MINUTELY/HOURLY Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Parse like any other type | Simple frequency objects with just type + interval. No special treatment. | ✓ |
| Parse but warn | Include a warning noting unusual frequency types. | |
| Reject with error | Treat as unsupported. | |

**User's choice:** Parse like any other type
**Notes:** User confirmed: "Yes, it's an official option. I actually use it not often, but I do use it."

---

## BYDAY Parsing (Positional Prefix)

| Option | Description | Selected |
|--------|-------------|----------|
| Prefix form only | Parse BYDAY=2TU. Error with clear message for BYSETPOS. | ✓ |
| Both forms | Handle both prefix (BYDAY=2TU) and BYSETPOS (BYDAY=TU;BYSETPOS=2). | |

**User's choice:** Prefix form only
**Notes:** User explicitly wanted YAGNI: "I don't like to be defensive just without any reason." The only scenario for BYSETPOS would be someone writing raw OmniJS — near zero probability since this server is the primary programmatic interface.

---

## Schedule 3-Value Derivation

| Option | Description | Selected |
|--------|-------------|----------|
| Crash on impossible combination | from_completion + catchUp=true = error (impossible UI state) | ✓ |
| Treat as from_completion | Silently ignore catchUp when from_completion. | |
| Treat as from_completion + warn | Map to from_completion, include warning. | |

**User's choice:** Crash on impossible combination
**Notes:** User: "If this happens, we should literally crash and send an error message, because it's literally not an option in the UI, so that's not supposed to happen."

---

## Malformed RRULE Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Fail-fast with error | ValueError with educational message. | ✓ |
| Degrade to raw string | Return unparseable ruleString as-is in fallback field. | |

**User's choice:** Fail-fast with error
**Notes:** Consistent with project's fail-fast philosophy.

---

## Interval Emit Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Always emit | Every frequency object includes interval, even when 1. | |
| Omit when 1 | interval only appears when > 1. Cleaner output. | ✓ |

**User's choice:** Omit when 1
**Notes:** None.

---

## Golden Master Impact

Discussion explored whether the golden master needed changes for Phase 32. Key finding: golden master operates at raw bridge layer, not model layer. `repetitionRule` was `null` in all existing scenarios because no repeating tasks existed.

**Outcome:** User decided to capture 30 new golden master scenarios in `08-repetition/` covering all frequency types, schedule variations, and completion lifecycle. Updated InMemoryBridge to match. This was done as prerequisite work before Phase 32 planning.

---

## monthly_day_of_week Vocabulary

| Option | Description | Selected |
|--------|-------------|----------|
| Lowercase English | first/second/third/fourth/fifth/last + monday-sunday/weekday/weekend_day | ✓ |
| Let me think about it | Different vocabulary idea. | |

**User's choice:** Lowercase English
**Notes:** User confirmed: "I don't care about uppercase or lowercase; whatever the spec says is good, but yes, let's normalise. Yes, the weekend is Saturday and Sunday, and a weekday is Monday to Friday."

---

## Module Structure

Not presented as formal question — arose from user's follow-up comment.

**User's input:** "Since the repetition rule is quite significant, let's put it in its own module."
**Claude's recommendation:** Agreed — `common.py` has small types (2-3 fields each); the discriminated union + parser would dwarf everything. Own module keeps boundary clean.
**Decision:** Repetition rule gets its own module. Exact structure is Claude's discretion.

---

## Claude's Discretion

- RRULE utility function wiring and internal structure
- Pydantic model names and hierarchy
- Exact error message wording
- Test structure
- Module/package layout within "own module" boundary

## Deferred Ideas

None — discussion stayed within phase scope
