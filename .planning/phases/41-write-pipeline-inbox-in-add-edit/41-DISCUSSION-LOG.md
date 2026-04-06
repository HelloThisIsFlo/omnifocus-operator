# Phase 41: Write Pipeline -- $inbox in Add/Edit - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-04-06
**Phase:** 41-write-pipeline-inbox-in-add-edit
**Mode:** discuss (interactive)
**Areas discussed:** PatchOrNone elimination, Null rejection layer, before/after container detection, Warning/error messages

## Gray Areas Identified

1. PatchOrNone elimination — how TagAction.replace handles clearing after PatchOrNone deletion
2. Null rejection layer — where null is rejected (contract vs service) for MoveAction and AddTaskCommand
3. before/after container detection — how to detect project IDs misused in anchor fields
4. Warning/error message wording — exact agent-facing messages for null errors

## Discussion Summary

### PatchOrNone Elimination
- **User insight:** `TagAction.replace: null` was always a clear operation, never "domain meaning." `PatchOrNone` was a misnomer from the start — should have been `PatchOrClear`
- **Decision:** Switch `TagAction.replace` to `PatchOrClear[list[str]]`, delete `PatchOrNone` entirely
- **Rationale:** The docstring distinguished "None carries domain meaning" vs "None means clear," but for tags, null→[]→no tags is definitionally clearing

### Null Rejection Layer
- **Initial question:** Contract-layer Pydantic rejection (generic error) vs service-layer check (educational error)?
- **User referenced:** `docs/architecture.md` — structural validation belongs at the contract layer
- **User found:** `@field_validator(mode="before")` has precedent in `FrequencyAddSpec` (`_validate_interval`, `_normalize_day_codes`, `_validate_on_dates`)
- **Decision:** `@field_validator(mode="before")` on MoveAction for beginning/ending, raises ValueError with educational message from errors.py. Follows existing pattern exactly.
- **Error flow:** field_validator → ValueError → Pydantic wraps in ValidationError → `ValidationReformatterMiddleware` extracts message → agent sees clean ToolError

### before/after Container Detection
- **Resolved before discussion:** User's refactor (commits `0b9f338`..`7de1c69`) added cross-type mismatch detection to `_resolve` — when anchor resolution fails in accepted types, searches non-accepted types and raises `EntityTypeMismatchError`
- **No decisions needed:** WRIT-08 is already fully handled by the Phase 40 refactor

### AddTaskCommand Parent — Omit vs Null vs $inbox
- **Key discovery:** `parent: str | None = None` can't distinguish omitted from explicit null
- **User's design process:**
  1. Initially considered PatchOrClear/PatchOrNone for null detection + warning
  2. Questioned whether the warning provides value ("agents don't remember across contexts")
  3. Arrived at: just make null an error, same as edit side
  4. Asked: "Can the schema say string-optional-but-not-nullable?" → Yes, `Patch[str] = UNSET`
- **Decision:** `parent` becomes `Patch[str] = UNSET`. Schema shows `{"type": "string"}`, optional. Null rejected by field_validator with educational error
- **WRIT-03 requirement change:** "parent: null → inbox + warning" becomes "parent: null → error"
- **Description:** Stays as-is: `"Project or task to place this task under. Omit for inbox."` — don't advertise `$inbox` in description; it's a safety net, not the primary API

### Error Message Wording
- Deferred to after context capture — placeholder in CONTEXT.md (D-14, D-15)

## Requirement Changes

- **WRIT-03:** Changed from "creates task in inbox + warning" to "returns error (null not accepted)"

## External Research

None required — all decisions informed by codebase analysis.
