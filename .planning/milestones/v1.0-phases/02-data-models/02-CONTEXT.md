# Phase 2: Data Models - Context

**Gathered:** 2026-03-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Typed Pydantic models for every OmniFocus entity that match the bridge script output shape exactly, with camelCase serialization aliases. Models are the shared language of the entire system — every layer depends on them. No business logic, no bridge interaction, no MCP wiring.

</domain>

<decisions>
## Implementation Decisions

### Date handling
- All date fields typed as `datetime | None` (not raw strings)
- Timezone-aware: use Pydantic's `AwareDatetime` or equivalent to enforce UTC
- `shouldUseFloatingTimeZone` stored as a plain boolean field — does not affect date typing (semantic interpretation deferred to service layer)
- Serialization: ISO 8601 strings (Pydantic default for datetime)

### Status representation
- Use Python `StrEnum` for status values
- Two separate enums: `TaskStatus` (Available, Blocked, Completed, Dropped, DueSoon, Next, Overdue) and `EntityStatus` (Active, Done, Dropped)
- Task `status` field is **required** (not nullable) — bridge should always provide a value; null means a bug
- Project model includes **both** `status` (EntityStatus, lifecycle) and `task_status` (TaskStatus, computed availability)
- Tag and Folder `status` fields use `EntityStatus | None` (bridge returns null when not set)

### Response density
- `exclude_none=True` applied at **serialization time** (caller decides), not baked into model config
- Empty lists (e.g., `tags: []`) stay visible in JSON output — not excluded
- Rationale: `exclude_none` is built-in Pydantic, zero custom code; excluding empty lists would require custom serializer

### Model granularity
- Inheritance hierarchy: `OmniFocusBaseModel` → `OmniFocusEntity` (id, name) → `ActionableEntity` (shared dates, flags, status for Task/Project)
- Tag and Folder extend `OmniFocusEntity` directly with their specific fields
- `RepetitionRule` and `ReviewInterval` are standalone Pydantic models (not nested classes)
- Perspective is a simple standalone model (id, name, builtin) — no shared base needed

### Claude's Discretion
- Unknown enum value handling strategy (fail-fast validation error vs. fallback)
- Model file layout (one file per entity vs. consolidated — architecture research suggests separate files)
- Exact field ordering within models
- Whether to add `py.typed` marker for type stub support
- Test fixture design (factories, builders, raw dicts)

</decisions>

<specifics>
## Specific Ideas

- Bridge script simplification: remove the `ts()` switch function, use `.name` property instead — deferred to Phase 8 but confirms models should validate against the same string values `.name` produces
- Philosophy: "if nothing, don't show it" for serialization — aligns with eventual TaskPaper format (M5+) where absent fields are omitted
- Models match bridge dump exactly — no invented fields (Anti-Pattern 3 from architecture research)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pyproject.toml` already configures `pydantic.mypy` plugin with `init_forbid_extra`, `init_typed`, `warn_required_dynamic_aliases`
- `mcp>=1.26.0` dependency bundles Pydantic v2 — no additional dependency needed
- `pytest-asyncio` configured in auto mode for async test support

### Established Patterns
- Ruff lint rules: E, F, I, N, UP, B, SIM, TCH, RUF — models must pass these
- mypy strict mode — all type annotations required, no `Any` without justification
- Architecture research prescribes: `alias_generator=to_camel`, `populate_by_name=True` on base config

### Integration Points
- Bridge script (`.research/operatorBridgeScript.js`) is the schema source of truth for field names and types
- Models will be imported by: Bridge (Phase 3), Repository (Phase 4), Service (Phase 5), MCP Server (Phase 5)
- `DatabaseSnapshot` model is the return type of `list_all` tool (Phase 5)
- Test fixtures created here will be reused across all subsequent phase tests

</code_context>

<deferred>
## Deferred Ideas

- Bridge script simplification: replace `ts()` switch with `.name` property for task status — Phase 8 (RealBridge)
- Empty list exclusion from serialization — revisit if token density becomes a real concern
- TaskPaper serialization format — Milestone 5+ (alternative output format for token reduction)

</deferred>

---

*Phase: 02-data-models*
*Context gathered: 2026-03-01*
