# Milestone v1.2.1 -- Architectural Cleanup

## Goal

Clean up write pipeline asymmetries and decompose the service layer into well-bounded modules. The service class currently mixes orchestration with validation, domain logic (urgency/availability computation, repetition rule format conversion), and payload construction. Define what the service layer owns, then draw internal boundaries so each concern lives in its own cohesive module. Also: unify write pipeline signatures, reject unknown fields on write models, and remove test-only code from production exports. No new tools, no behavioral changes -- pure internal quality.

## What to Build

### Unify Service-Repository Write Interface

The two write paths have different type signatures and responsibility splits at the service-repository boundary:

| | `add_task` (current) | `edit_task` (current) |
|---|---|---|
| **Service passes** | `TaskCreateSpec` + `resolved_tag_ids` + `resolved_repetition_rule` kwargs | `dict[str, Any]` (fully bridge-ready payload) |
| **Who serializes to bridge format** | Repository (`model_dump(by_alias=True)`) | Service (builds dict field-by-field) |
| **Repository role** | `model_dump` spec, pop/swap resolved values | Pass-through |
| **Return type** | `TaskCreateResult` (typed) | `dict[str, Any]` (raw) |

Both paths ultimately call `bridge.send_command(command, payload)` with a `dict[str, Any]`, but arrive at that dict differently.

**Target:** Symmetric protocol signatures where both write operations follow the same pattern for who builds the bridge payload, what types cross the boundary, and what the repository's role is.

**Key conversions to unify:**
- Tag resolution (names -> IDs for add, diff computation for edit -- both in service)
- Repetition rule conversion (`RepetitionRuleSpec` -> bridge dict -- currently via band-aid `resolved_repetition_rule` kwarg)
- Field serialization (snake_case -> camelCase -- split between repo and service)
- Key renaming (`tags` -> `tagIds`, `repetitionRule` swap -- split between repo and service)

See: `2026-03-15-unify-write-interface-at-service-repository-boundary.md` for full asymmetry map.

### Decompose the Service Layer

The service class currently owns everything between "MCP tool called" and "bridge command sent." That includes validation, domain logic, format conversion, and orchestration -- all inline. The goal is to define what the service layer's responsibilities are, then extract cohesive modules within it.

**The service class should orchestrate.** It coordinates the flow (validate -> resolve -> convert -> delegate), but the individual concerns should be their own modules.

**Candidates for extraction (not exhaustive -- discover during planning):**

- **Validation**: input constraints, mutually exclusive fields, no-op detection, ID existence checks, lifecycle guards
- **Domain logic / policies**: urgency vs availability computation, status model rules, tag diff computation, repetition rule format and merge semantics (see MILESTONE-v1.2.3) -- these are our domain choices, not OmniFocus constraints
- **Format conversion**: snake_case ↔ camelCase payload construction -- mechanical transformations

The key distinction: validation checks "is this request valid?", domain logic implements "what are our rules?", format conversion handles "how do we serialize for the bridge?". Today they're all interleaved in service methods.

**Benefits:** Service methods stay focused on happy-path orchestration. Each concern is testable in isolation. New logic doesn't bloat service methods. Boundaries make it clear where new features plug in.

See: `2026-03-08-extract-validation-and-pre-checks-from-service-into-dedicated-layer.md` (captures the validation angle; the broader decomposition is new)

### Strict Write Model Validation (`extra="forbid"`)

Write models silently drop unknown fields because `OmniFocusBaseModel` uses Pydantic's default `extra="ignore"`. An agent sending `{"name": "Test", "repetitionRule": "weekly"}` gets no error -- the field is silently discarded.

**Fix:** Add a `WriteModel` intermediate base (or set directly on each write spec) with `extra="forbid"`. Read models must stay permissive (`extra="ignore"`) since OmniFocus may return fields we don't model yet.

See: `2026-03-08-discuss-extra-forbid-strict-validation-on-write-models.md`

### Remove InMemoryBridge from Production Exports

`InMemoryBridge` is a test-only double (call tracking, error simulation, hardcoded data) but lives in production code and is registered as a bridge factory option.

**Two-step cleanup:**
1. Remove from public surface -- drop from `bridge/__init__.py` exports, remove `"inmemory"` branch from factory. Update test imports to use direct module paths.
2. Move file to `tests/` -- physically relocate `in_memory.py` out of `src/`.

See: `2026-03-10-remove-inmemorybridge-from-production-exports-and-factory.md`

## Key Acceptance Criteria

- `add_task` and `edit_task` have symmetric protocol signatures at the service-repository boundary
- Both write paths follow the same pattern for bridge payload construction
- Service class orchestrates but delegates to extracted modules for validation, domain logic, and format conversion
- Each extracted module is independently testable
- Write models reject unknown fields with clear errors (`extra="forbid"`)
- Read models remain permissive (`extra="ignore"`)
- `InMemoryBridge` is not importable from `omnifocus_operator.bridge` -- only via direct module path in tests
- All existing tests pass -- no behavioral changes
- No new tools

## Tools After This Milestone

Six (unchanged from v1.2): `get_all`, `get_task`, `get_project`, `get_tag`, `add_tasks`, `edit_tasks`.
