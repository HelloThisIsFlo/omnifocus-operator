# Phase 50: Use OmniFocus settings API for date preferences and due-soon threshold - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the fragile SQLite plist-parsing path for the DueSoon threshold with the clean OmniJS `settings.objectForKey()` API, and upgrade date-only write inputs from midnight-local to the user's configured default times (`DefaultDueTime`, `DefaultStartTime`, `DefaultPlannedTime`).

Two deliverables:
1. **Bridge settings command** — New `get_settings` bridge command reading date-related preferences via OmniJS
2. **Apply preferences in service layer** — DueSoon threshold uses bridge settings; date-only write inputs get enriched with user-configured default times instead of midnight

</domain>

<decisions>
## Implementation Decisions

### Fallback behavior: OmniFocus defaults + warning
- **D-01:** When settings cannot be read from OmniFocus (bridge failure, app not running), fall back to OmniFocus's documented factory defaults and emit a warning. The agent's request still succeeds — never error-serving mode for missing settings.
- **D-01b:** OmniFocus factory defaults: `DefaultDueTime=17:00`, `DefaultStartTime=00:00`, `DefaultPlannedTime=09:00`, `DueSoonInterval=172800` (2 days), `DueSoonGranularity=1`.
- **D-01c:** This applies consistently to BOTH date-only default times (write side) AND DueSoon threshold (read side). Same pattern everywhere.
- **D-01d:** DueSoon fallback upgrades from current behavior (fall back to TODAY bounds) to OmniFocus default (TWO_DAYS). Warning message updated accordingly.

### Settings data source: bridge only, delete SQLite plist path
- **D-02:** Both HybridRepository and BridgeOnlyRepository use the same bridge-based settings source. The SQLite `Setting` table plist-parsing code is deleted entirely — `_read_due_soon_setting_sync()`, `_SETTING_MAP`, `plistlib` imports.
- **D-02b:** The `OPERATOR_DUE_SOON_THRESHOLD` env var in `config.py` is also deleted. One source of truth: the bridge.
- **D-02c:** `get_due_soon_setting()` is removed from the Repository protocol. The service gets DueSoon from the preferences module, not the repository.

### Settings cache: lazy singleton, restart to refresh
- **D-03:** Settings are loaded on first use (lazy), cached for the lifetime of the server process (singleton). No background refresh, no TTL, no reload endpoint.
- **D-03b:** If OmniFocus preferences change mid-session, the next MCP server restart picks them up. MCP servers are lightweight processes — Claude Desktop restarts them per conversation.
- **D-03c:** No reload tool. The complexity of any refresh mechanism is disproportionate to the frequency of settings changes (essentially never).

### Architecture: separate preferences module, injected into service
- **D-04:** A dedicated preferences module (not the service itself, not the repository) encapsulates the bridge settings call + lazy caching. Injected with a Bridge instance at construction.
- **D-04b:** This module is injected into OperatorService as a collaborator alongside `_repository`, `_resolver`, `_domain`, `_payload`. The service accesses settings through it.
- **D-04c:** Rationale: OmniFocus preferences are not entity CRUD (not a repository concern) — they're config loading (infrastructure) that the service consumes. Similar to how `config.py` handles env vars, but this one needs a bridge.
- **D-04d:** The module exposes typed settings: default times per date field, DueSoonSetting enum. Consumers don't deal with raw bridge responses.

### Date-only normalization: field-aware, in domain.py
- **D-05:** `normalize_date_input()` (or its replacement) must become field-aware — it needs to know whether it's normalizing a due date, defer date, or planned date to apply the correct default time.
- **D-05b:** This is a product decision per the architecture litmus test: "Would another OmniFocus tool apply user-configured default times?" — No → domain.py.
- **D-05c:** The exact mechanism for passing field context (parameter, caller provides the time, etc.) is Claude's discretion, guided by keeping domain.py focused on product decisions.

### Claude's Discretion
- Bridge command name and response shape (e.g., `get_settings` returning a dict of key-value pairs)
- Which OmniFocus settings keys to fetch (at minimum: `DefaultDueTime`, `DefaultStartTime`, `DefaultPlannedTime`, `DueSoonInterval`, `DueSoonGranularity`)
- Preferences module naming and package placement (e.g., `service/preferences.py`, top-level module, etc.)
- `normalize_date_input()` signature change approach (field name parameter vs caller-provided default time)
- `_SETTING_MAP` migration from hybrid.py to preferences module (bridge returns raw interval/granularity → map to DueSoonSetting enum)
- InMemoryBridge handler for `get_settings` command in tests
- Time format parsing for varying OmniFocus formats (`"19:00:00"`, `"09:00"`)
- Warning message wording for settings-unavailable fallback
- How `list_projects` pipeline adapts (also uses `get_due_soon_setting()` today)

### Folded Todos
- **Use OmniFocus settings API for date preferences and due-soon threshold** (`.planning/todos/pending/2026-04-10-use-omnifocus-settings-api-for-date-preferences-and-due-soon.md`) — this IS the phase. The todo is the primary design document with the complete problem statement and solution outline.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design document (PRIMARY)
- `.planning/todos/pending/2026-04-10-use-omnifocus-settings-api-for-date-preferences-and-due-soon.md` — Complete problem statement and solution outline. THIS CONTEXT.md captures discussion decisions that refine the todo.

### Settings API evidence (CRITICAL)
- `.research/deep-dives/timezone-behavior/05-settings-api/FINDINGS.md` — Full OmniJS settings API findings: 66 keys, actual user values vs defaults, date/time settings table. The empirical source for factory default values.

### Architecture (normalization placement + service patterns)
- `docs/architecture.md` §"Product Decisions vs Plumbing" — litmus test for domain.py placement
- `docs/architecture.md` §"Dumb Bridge, Smart Python" — bridge is a relay, Python owns logic
- `docs/architecture.md` §"Method Object Pattern" — pipeline conventions for service use cases
- `docs/model-taxonomy.md` — model naming rules (if new models are needed for preferences)

### Phase 49 output (predecessor — interim behavior being upgraded)
- `.planning/phases/49-implement-naive-local-datetime-contract-for-all-date-inputs/49-CONTEXT.md` — D-02: midnight local as interim for date-only inputs (this phase upgrades it). D-06: normalization lives in domain.py.

### Phase 46 output (original DueSoon integration)
- `.planning/phases/46-pipeline-query-paths/46-CONTEXT.md` — D-01 through D-03: original `get_due_soon_setting()` design on Repository protocol (being replaced by preferences module)

### Source files (in scope for deletion/modification)
- `src/omnifocus_operator/repository/hybrid/hybrid.py:1002-1044` — SQLite plist-parsing to DELETE
- `src/omnifocus_operator/repository/hybrid/hybrid.py:67-75` — `_SETTING_MAP` to migrate
- `src/omnifocus_operator/repository/bridge_only/bridge_only.py:352-359` — env var path to DELETE
- `src/omnifocus_operator/contracts/protocols.py` — `get_due_soon_setting()` to REMOVE from Repository protocol
- `src/omnifocus_operator/config.py` — `due_soon_threshold` field to DELETE
- `src/omnifocus_operator/service/domain.py:123-148` — `normalize_date_input()` to make field-aware
- `src/omnifocus_operator/service/domain.py:236-243` — DueSoon fallback to upgrade (TODAY → TWO_DAYS)
- `src/omnifocus_operator/service/service.py:314-320` — Pipeline DueSoon resolution to rewire
- `src/omnifocus_operator/bridge/bridge.js` — Add `get_settings` command handler

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DueSoonSetting(Enum)` in `models/enums.py` — 7-member enum with `.days` and `.calendar_aligned`. Stays as-is, just sourced differently.
- `_SETTING_MAP` in `hybrid.py:67-75` — maps `(interval_seconds, granularity)` tuples to enum members. Migrates to preferences module.
- `resolve_date_filter()` in `service/resolve_dates.py` — pure resolver, already accepts `DueSoonSetting | None`. No changes needed.
- `agent_messages/warnings.py` — centralized warning system. Add new warning for settings-fallback.
- Bridge dispatch pattern in `bridge.js:375-404` — `handleGetSettings()` + `else if` branch follows existing convention.

### Established Patterns
- **Service DI:** `OperatorService.__init__` receives collaborators (`_repository`, `_resolver`, `_domain`, `_payload`). Preferences module fits this pattern.
- **Bridge commands:** `handleGetAll()`, `handleAddTask()`, `handleEditTask()` — each is a function called from `dispatch()`. New `handleGetSettings()` follows the same shape.
- **Domain owns product decisions:** `normalize_date_input()` already in domain.py. Adding field-awareness extends it, doesn't move it.
- **Conditional I/O in pipelines:** `service.py:315-320` only calls `get_due_soon_setting()` when `due: "soon"` is detected. Similar pattern applies for preferences: only load when a date-only write or "soon" query is detected.

### Integration Points
- `server.py` wiring — needs to create preferences module with bridge, inject into service
- `service.py` pipeline — rewire DueSoon resolution from `self._repository.get_due_soon_setting()` to `self._preferences`
- `domain.py` — upgrade `normalize_date_input()` with field-aware default times from preferences
- `bridge.js` — add `get_settings` operation handler
- `list_projects` pipeline — also uses `get_due_soon_setting()`, needs same rewiring

</code_context>

<specifics>
## Specific Ideas

### The todo IS the design document
The todo was written alongside the settings API deep-dive. It describes both the DueSoon threshold replacement and the date-only default time enrichment. The decisions in this CONTEXT.md refine the todo's solution (especially the architecture: preferences module vs direct bridge call).

### Clean upgrade from Phase 49
Phase 49 explicitly flagged midnight-local as interim: `"settings API todo will upgrade to DefaultDueTime"` (domain.py:131). The interception point is already in place — this phase swaps the hardcoded midnight with the user's configured time.

### No error-serving mode impact
Current behavior already uses fallback + warning for missing DueSoon (domain.py:237-243). No code triggers degraded/error-serving mode for missing settings. This phase keeps that pattern.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 50-use-omnifocus-settings-api-for-date-preferences-and-due-soon*
*Context gathered: 2026-04-11*
