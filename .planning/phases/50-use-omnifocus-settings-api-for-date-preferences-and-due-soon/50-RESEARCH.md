# Phase 50: Use OmniFocus Settings API for Date Preferences and Due-Soon Threshold - Research

**Researched:** 2026-04-11
**Domain:** OmniJS settings API, preferences infrastructure, date normalization
**Confidence:** HIGH

## Summary

This phase replaces the fragile SQLite plist-parsing path for DueSoon threshold with the clean OmniJS `settings.objectForKey()` API, and upgrades date-only write inputs from midnight-local to user-configured default times. The codebase already has all the building blocks: the `DueSoonSetting` enum, `_SETTING_MAP`, `normalize_date_input()`, and the bridge dispatch pattern. The work is a well-scoped rewiring exercise.

The primary challenge is threading a new preferences module through the DI graph. The service constructor currently takes only `repository`; it needs a `preferences` collaborator. The secondary challenge is making `normalize_date_input()` field-aware without breaking its clean single-responsibility interface.

**Primary recommendation:** Build a `service/preferences.py` module that wraps bridge + lazy cache + raw-to-domain mapping, inject it as a collaborator into `OperatorService`, and update the two date normalization call sites to use field-aware default times.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Fallback to OmniFocus factory defaults + warning when settings unavailable. Never error-serving mode.
- **D-01b:** Factory defaults: `DefaultDueTime=17:00`, `DefaultStartTime=00:00`, `DefaultPlannedTime=09:00`, `DueSoonInterval=172800` (2 days), `DueSoonGranularity=1`.
- **D-01c:** Same fallback pattern for both date-only default times (write) and DueSoon threshold (read).
- **D-01d:** DueSoon fallback upgrades from TODAY to TWO_DAYS.
- **D-02:** Both repositories use bridge-based settings. SQLite plist path deleted entirely.
- **D-02b:** `OPERATOR_DUE_SOON_THRESHOLD` env var deleted.
- **D-02c:** `get_due_soon_setting()` removed from Repository protocol; service reads from preferences module.
- **D-03:** Settings lazy-loaded on first use, cached for server lifetime. No TTL, no refresh.
- **D-03b:** Restart picks up changes. MCP servers restart per conversation anyway.
- **D-03c:** No reload tool.
- **D-04:** Dedicated preferences module, injected into OperatorService alongside existing collaborators.
- **D-04b:** Injected as a collaborator (like `_repository`, `_resolver`, `_domain`, `_payload`).
- **D-04c:** OmniFocus preferences are config loading (infrastructure), not entity CRUD.
- **D-04d:** Module exposes typed settings: default times per date field, DueSoonSetting enum.
- **D-05:** `normalize_date_input()` must become field-aware for per-field default times.
- **D-05b:** This is a product decision (domain.py).
- **D-06:** Tool descriptions updated: add/edit mention default times, list mentions "soon" threshold source, all note restart requirement.
- **D-06d:** Minimal: one sentence per concern.
- **D-07:** Preferences module exposes domain-typed settings, not raw bridge values.
- **D-07b:** `_SETTING_MAP` moves into preferences module as internal implementation detail.

### Claude's Discretion
- Bridge command name and response shape
- Which OmniFocus settings keys to fetch
- Preferences module naming and package placement
- `normalize_date_input()` signature change approach
- `_SETTING_MAP` migration approach
- InMemoryBridge handler for `get_settings`
- Time format parsing for varying OmniFocus formats
- Warning message wording
- How `list_projects` pipeline adapts

### Deferred Ideas (OUT OF SCOPE)
None.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PREF-01 | Bridge `get_settings` command reads date-related preferences via OmniJS | Bridge dispatch pattern verified in `bridge.js:375-404`; OmniJS `settings.objectForKey()` API verified in research findings |
| PREF-02 | Preferences module: lazy load, domain-typed, cached for lifetime | Lazy singleton pattern already exists in `config.py:84-98`; `_SETTING_MAP` for DueSoon mapping at `hybrid.py:67-75` |
| PREF-03 | Fallback to OmniFocus factory defaults + warning when unavailable | Warning pattern established in `warnings.py`; factory default values verified empirically |
| PREF-04 | Date-only `dueDate` enriched with user's `DefaultDueTime` | `normalize_date_input()` at `domain.py:123-148` is the interception point, already flags interim behavior |
| PREF-05 | Date-only `deferDate` enriched with user's `DefaultStartTime` | Same interception point |
| PREF-06 | Date-only `plannedDate` enriched with user's `DefaultPlannedTime` | Same interception point |
| PREF-07 | Date-only normalization is field-aware | `_AddTaskPipeline._normalize_dates()` and `_EditTaskPipeline._normalize_dates()` both call `normalize_date_input()` per-field |
| PREF-08 | DueSoon as `DueSoonSetting` enum from preferences, replacing SQLite/env var | `DueSoonSetting` enum at `enums.py:27-68`; `_SETTING_MAP` at `hybrid.py:67-75` already does this mapping |
| PREF-09 | DueSoon fallback: TWO_DAYS + warning (upgrading from TODAY fallback) | Fallback logic at `domain.py:237-243`; warning constant at `warnings.py:128-131` |
| PREF-10 | `get_due_soon_setting()` removed from Repository protocol | Protocol at `protocols.py:106`; call sites at `service.py:320`, `hybrid.py:1042`, `bridge_only.py:352` |
| PREF-11 | SQLite plist-parsing code deleted | `hybrid.py:1002-1044` + `_SETTING_MAP` at lines 67-75 + `plistlib` import |
| PREF-12 | `OPERATOR_DUE_SOON_THRESHOLD` env var and config field deleted | `config.py:64-81` (field + validator) |
| PREF-13 | Tool descriptions updated | `descriptions.py:448-637` (ADD, EDIT, LIST_TASKS, LIST_PROJECTS tool docs) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **SAFE-01/02**: No automated test touches the real bridge. Tests use `InMemoryBridge` or `SimulatorBridge`.
- **Service Layer Convention**: Method Object pattern for use cases. `_VerbNounPipeline` inheriting `_Pipeline`.
- **Model Conventions**: Read `docs/model-taxonomy.md` before creating models. After modifying tool output models, run `test_output_schema.py`.
- **Dumb Bridge, Smart Python**: Bridge is a relay. All logic in Python.

## Architecture Patterns

### Recommended Preferences Module Structure

```
service/
  preferences.py    # New: lazy-loaded OmniFocus preferences
  domain.py         # Modified: field-aware normalize_date_input()
  service.py        # Modified: OperatorService constructor + pipeline rewiring
```

### Pattern 1: Lazy Singleton with Bridge
**What:** A preferences class that lazy-loads settings from the bridge on first access, caches them, and exposes domain-typed values.
**When to use:** Exactly this phase -- loading OmniFocus config that doesn't change during a session.

```python
# Source: modeled after config.py:84-98 lazy singleton pattern
class OmniFocusPreferences:
    """Lazy-loaded OmniFocus date/time preferences.

    Loads settings via bridge on first access, caches for server lifetime.
    Falls back to OmniFocus factory defaults if bridge is unavailable.
    """

    _FACTORY_DEFAULTS = {
        "DefaultDueTime": "17:00",
        "DefaultStartTime": "00:00",
        "DefaultPlannedTime": "09:00",
        "DueSoonInterval": 172800,
        "DueSoonGranularity": 1,
    }

    _SETTING_MAP: dict[tuple[int, int], DueSoonSetting] = {
        (86400, 1): DueSoonSetting.TODAY,
        (86400, 0): DueSoonSetting.TWENTY_FOUR_HOURS,
        (172800, 1): DueSoonSetting.TWO_DAYS,
        (259200, 1): DueSoonSetting.THREE_DAYS,
        (345600, 1): DueSoonSetting.FOUR_DAYS,
        (432000, 1): DueSoonSetting.FIVE_DAYS,
        (604800, 1): DueSoonSetting.ONE_WEEK,
    }

    def __init__(self, bridge: Bridge) -> None:
        self._bridge = bridge
        self._loaded = False
        self._due_soon: DueSoonSetting = DueSoonSetting.TWO_DAYS  # factory default
        self._default_due_time: str = "17:00"
        self._default_start_time: str = "00:00"
        self._default_planned_time: str = "09:00"
        self._warnings: list[str] = []

    async def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        try:
            result = await self._bridge.send_command("get_settings")
            self._apply(result)
        except Exception:
            self._warnings.append(SETTINGS_FALLBACK_WARNING)

    async def get_due_soon_setting(self) -> DueSoonSetting:
        await self._ensure_loaded()
        return self._due_soon

    async def get_default_time(self, field: str) -> str:
        """Return default time for a date field: 'due_date', 'defer_date', 'planned_date'."""
        await self._ensure_loaded()
        # ... field -> time mapping
```

[VERIFIED: codebase patterns] The lazy singleton pattern exists in `config.py:84-98`. Bridge protocol at `protocols.py:110-117`.

### Pattern 2: Field-Aware Date Normalization
**What:** Upgrade `normalize_date_input()` to accept a default time for date-only inputs instead of hardcoded midnight.
**When to use:** This phase -- the function already has the `"T" not in value` branch that appends midnight.

Two approaches (Claude's discretion per D-05c):

**Option A: Caller provides default time**
```python
def normalize_date_input(value: str, default_time: str = "00:00:00") -> str:
    if "T" not in value and "t" not in value:
        return f"{value}T{default_time}"
    # ... aware->local conversion unchanged
```
- Pro: `normalize_date_input` stays pure (no async, no preferences dependency)
- Pro: Callers already know which field they're processing
- Con: Callers must obtain default time before calling

**Option B: Field name parameter**
```python
def normalize_date_input(value: str, field: str = "due_date") -> str:
    ...
```
- Con: Requires preferences access inside domain function (breaks purity)

**Recommendation: Option A** -- the caller already iterates per-field in both `_AddTaskPipeline._normalize_dates()` and `_EditTaskPipeline._normalize_dates()`. Passing the default time keeps `normalize_date_input` pure and testable without mocking preferences.

[VERIFIED: codebase] Call sites at `service.py:533-543` and `service.py:674-682` already iterate per-field.

### Pattern 3: Bridge Command Handler
**What:** Add `handleGetSettings()` to `bridge.js` following the existing dispatch pattern.

```javascript
// Source: bridge.js dispatch pattern at lines 375-404
function handleGetSettings() {
    var result = {};
    var keys = [
        "DefaultDueTime",
        "DefaultStartTime",
        "DefaultPlannedTime",
        "DueSoonInterval",
        "DueSoonGranularity"
    ];
    for (var i = 0; i < keys.length; i++) {
        result[keys[i]] = settings.objectForKey(keys[i]);
    }
    return result;
}
```

[VERIFIED: codebase + research findings] `settings.objectForKey(key)` returns native types: strings for time values, integers for interval/granularity. Confirmed in `.research/deep-dives/timezone-behavior/05-settings-api/FINDINGS.md`.

### Anti-Patterns to Avoid
- **Don't make preferences a Repository concern** -- D-04c explicitly states this is config loading, not entity CRUD
- **Don't add a new protocol method** -- D-02c removes `get_due_soon_setting()` from Repository; don't add a replacement
- **Don't add reload/refresh** -- D-03c explicitly rejects this
- **Don't parse plist in the new path** -- the whole point is that `settings.objectForKey()` returns clean primitives

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Time string parsing | Custom regex for `HH:MM:SS` / `HH:MM` | Simple split on `:` with zero-padding | OmniJS returns inconsistent formats (`19:00:00` vs `09:00`), but both are trivially parseable |
| DueSoon interval→enum mapping | New mapping table | Migrate existing `_SETTING_MAP` from `hybrid.py:67-75` | Already tested and correct |
| Lazy singleton | Custom metaclass | Simple `_loaded` flag + `async _ensure_loaded()` | Pattern already in `config.py`; async version needs await-before-access |

## Common Pitfalls

### Pitfall 1: Time Format Inconsistency from OmniJS
**What goes wrong:** OmniJS returns `"19:00:00"` for some time settings and `"09:00"` for others (confirmed in FINDINGS.md: `DefaultDueTime: 19:00:00`, `DefaultPlannedTime: 09:00`).
**Why it happens:** OmniFocus stores these as strings with no consistent formatting.
**How to avoid:** Parse time strings by splitting on `:` and normalizing to `HH:MM:SS`. Both 2-part and 3-part formats map cleanly.
**Warning signs:** Tests passing with `"17:00"` factory defaults but failing with real user values in `HH:MM:SS` format.

### Pitfall 2: Async Lazy Loading in Sync Context
**What goes wrong:** `normalize_date_input()` is currently synchronous. If preferences are injected into it, the function needs to become async, which cascades.
**Why it happens:** Bridge calls are async (IPC with OmniFocus).
**How to avoid:** Use Option A from Pattern 2 -- keep `normalize_date_input()` pure/sync. Callers obtain the default time from preferences (async) before calling.
**Warning signs:** `await` in domain.py, or passing the preferences object into `normalize_date_input()`.

### Pitfall 3: DI Change Cascades to Tests
**What goes wrong:** `OperatorService.__init__` currently takes only `repository`. Adding `preferences` as a constructor parameter breaks every test that creates `OperatorService(repository=...)`.
**Why it happens:** The constructor change propagates to all test fixtures and helper functions.
**How to avoid:** Two options: (1) make `preferences` optional with a default that uses a stub/factory default, or (2) update all test instantiation sites. Option 2 is more honest and avoids hidden defaults.
**Warning signs:** Dozens of test failures after the constructor change.

### Pitfall 4: InMemoryBridge Missing `get_settings` Handler
**What goes wrong:** All tests use `InMemoryBridge`, which currently falls through to `_handle_get_all()` for unknown operations. A `get_settings` call would return the wrong data type.
**Why it happens:** `InMemoryBridge.send_command()` has a catch-all: `return self._handle_get_all()`.
**How to avoid:** Add an explicit `get_settings` handler to `InMemoryBridge` that returns factory defaults or configurable settings.
**Warning signs:** Tests pass accidentally because bridge returns a dict (get_all snapshot) that doesn't raise, but the preferences module gets garbage data.

### Pitfall 5: DueSoon Fallback Warning Message Changes
**What goes wrong:** The existing `DUE_SOON_THRESHOLD_NOT_DETECTED` warning references `OPERATOR_DUE_SOON_THRESHOLD` env var. After deleting the env var, the message is misleading.
**Why it happens:** Warning text was written for the env-var fallback path.
**How to avoid:** Update the warning message when deleting the env var. New message should reference OmniFocus preferences and the factory default (TWO_DAYS).
**Warning signs:** Tests asserting on old warning text break, or worse, pass because nobody checks the message content.

## Code Examples

### Current: `normalize_date_input()` (to be modified)
```python
# Source: domain.py:123-148 [VERIFIED: codebase]
def normalize_date_input(value: str) -> str:
    if "T" not in value and "t" not in value:
        # Date-only: append midnight local
        # Interim behavior -- settings API todo will upgrade to DefaultDueTime.
        return f"{value}T00:00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is not None:
        local_dt = dt.astimezone()
        return local_dt.replace(tzinfo=None).isoformat()
    return value
```

### Current: `_ReadPipeline._resolve_date_filters()` (to be rewired)
```python
# Source: service.py:309-328 [VERIFIED: codebase]
async def _resolve_date_filters(self) -> None:
    self._now = local_now()
    due_soon_setting: DueSoonSetting | None = None
    if (is_set(self._query.due) and isinstance(self._query.due, StrEnum)
            and self._query.due.value == "soon"):
        due_soon_setting = await self._repository.get_due_soon_setting()
    # ...
```

### Current: DueSoon fallback in domain.py (to be updated)
```python
# Source: domain.py:236-243 [VERIFIED: codebase]
if isinstance(value, StrEnum) and value.value == "soon" and due_soon_setting is None:
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    bounds[field_name] = ResolvedDateBounds(
        after=midnight,
        before=midnight + timedelta(days=1),
    )
    warnings.append(DUE_SOON_THRESHOLD_NOT_DETECTED)
```

### Current: Bridge dispatch pattern (to add `get_settings`)
```javascript
// Source: bridge.js:375-397 [VERIFIED: codebase]
if (operation === "get_all") {
    var data = handleGetAll();
    writeResponse(ipcDir, filePrefix, { success: true, data: data });
} else if (operation === "add_task") {
    var result = handleAddTask(request.params);
    writeResponse(ipcDir, filePrefix, { success: true, data: result });
} else if (operation === "edit_task") {
    // ...
} else {
    writeResponse(ipcDir, filePrefix, { success: false, error: "Unknown operation: " + operation });
}
```

### Current: InMemoryBridge dispatch (to add `get_settings`)
```python
# Source: tests/doubles/bridge.py:157-165 [VERIFIED: codebase]
if operation == "get_all":
    return self._handle_get_all()
if operation == "add_task":
    return self._handle_add_task(params or {})
if operation == "edit_task":
    return self._handle_edit_task(params or {})
# Unknown operations return the assembled snapshot
return self._handle_get_all()
```

### Current: OperatorService constructor (to add preferences)
```python
# Source: service.py:136-140 [VERIFIED: codebase]
def __init__(self, repository: Repository) -> None:
    self._repository = repository
    self._resolver = Resolver(repository)
    self._domain = DomainLogic(repository, self._resolver)
    self._payload = PayloadBuilder()
```

### Current: server.py wiring (to create preferences + inject)
```python
# Source: server.py:103-109 [VERIFIED: codebase]
repository = create_repository(repo_type)
service = OperatorService(repository=repository)
yield {"service": service}
```

## Deletion Inventory

Files/code being **deleted** (per D-02, D-02b, D-02c, PREF-11, PREF-12):

| Target | Location | What |
|--------|----------|------|
| SQLite plist parsing | `hybrid.py:1002-1044` | `_read_due_soon_setting_sync()` + `get_due_soon_setting()` |
| `_SETTING_MAP` | `hybrid.py:67-75` | Migrates to preferences module (not pure delete) |
| `plistlib` import | `hybrid.py` (top) | No longer needed after plist parsing removed |
| Bridge-only env var path | `bridge_only.py:352-359` | `get_due_soon_setting()` that reads `config.get_settings().due_soon_threshold` |
| Repository protocol method | `protocols.py:106` | `get_due_soon_setting()` line |
| Config field + validator | `config.py:64-81` | `due_soon_threshold` field, `_validate_due_soon_threshold()`, and DueSoonSetting import |
| Warning text | `warnings.py:128-131` | `DUE_SOON_THRESHOLD_NOT_DETECTED` -- replaced with new settings-fallback warning |
| Existing tests | `test_due_soon_setting.py` | Entire file -- tests SQLite plist parsing and env var paths |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SQLite Setting table plist-parsing | OmniJS `settings.objectForKey()` | Phase 50 (this phase) | Clean primitives, no binary parsing |
| `OPERATOR_DUE_SOON_THRESHOLD` env var | Bridge-based preferences | Phase 50 | Single source of truth (OmniFocus prefs) |
| Midnight local for date-only inputs | User-configured default times | Phase 50 | Matches OmniFocus UI behavior |
| DueSoon on Repository protocol | DueSoon on preferences module | Phase 50 | Settings are infrastructure, not CRUD |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `settings.objectForKey()` returns native JS types (string, number) that JSON-serialize cleanly through the bridge | Architecture Patterns | Would need type coercion in bridge.js |
| A2 | OmniJS time strings are always `HH:MM` or `HH:MM:SS` format | Pitfall 1 | Would need more flexible parsing |
| A3 | OmniJS settings API is available in OmniFocus 4 (the version the project targets) | Architecture Patterns | Would need fallback or version detection |

[A1: VERIFIED via FINDINGS.md] -- The research script confirmed that `settings.objectForKey("DefaultDueTime")` returns `"19:00:00"`, `settings.objectForKey("DueSoonInterval")` returns `86400` (integer). These serialize cleanly as JSON primitives.

[A2: VERIFIED via FINDINGS.md] -- Observed values: `"19:00:00"`, `"08:00:00"`, `"09:00"`, `"17:00"`, `"14:00"`, `"00:00"`. Mix of HH:MM and HH:MM:SS confirmed.

[A3: VERIFIED via FINDINGS.md] -- The research script ran successfully against the user's live OmniFocus 4 installation.

**All assumptions verified. No user confirmation needed.**

## Open Questions (RESOLVED)

1. **How should the preferences module handle unknown DueSoonInterval/Granularity pairs?**
   - What we know: Current `_SETTING_MAP` returns `None` for unknown pairs. The domain fallback uses TODAY bounds.
   - What's unclear: Should the preferences module fall back to TWO_DAYS (factory default) for unknown pairs, or expose `None` to let domain handle it?
   - Recommendation: Fall back to TWO_DAYS inside the preferences module. The module's contract is "always returns a valid DueSoonSetting" -- `None` only when the bridge itself fails. Unknown pairs mean the user has a valid setting we can't map, so TWO_DAYS (factory default) is safer than TODAY.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x + pytest-asyncio |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/ -x -q --no-header --timeout=10` |
| Full suite command | `uv run pytest tests/ --timeout=10` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PREF-01 | Bridge `get_settings` returns date preferences | unit | `uv run pytest tests/test_bridge.py -x -q -k get_settings` | No -- Wave 0 |
| PREF-02 | Preferences module lazy loads, caches, maps to domain types | unit | `uv run pytest tests/test_preferences.py -x -q` | No -- Wave 0 |
| PREF-03 | Fallback to factory defaults + warning on bridge failure | unit | `uv run pytest tests/test_preferences.py -x -q -k fallback` | No -- Wave 0 |
| PREF-04 | Date-only dueDate gets user's DefaultDueTime | unit | `uv run pytest tests/test_service_domain.py -x -q -k normalize_date` | Partially (tests exist for midnight, need update) |
| PREF-05 | Date-only deferDate gets user's DefaultStartTime | unit | Same as above | No -- Wave 0 |
| PREF-06 | Date-only plannedDate gets user's DefaultPlannedTime | unit | Same as above | No -- Wave 0 |
| PREF-07 | Normalization is field-aware | unit | Same as above | No -- Wave 0 |
| PREF-08 | DueSoon exposed as enum from preferences | unit | `uv run pytest tests/test_preferences.py -x -q -k due_soon` | No -- Wave 0 |
| PREF-09 | DueSoon fallback = TWO_DAYS + warning | unit | `uv run pytest tests/test_preferences.py -x -q -k fallback` | No -- Wave 0 |
| PREF-10 | `get_due_soon_setting()` removed from Repository protocol | unit | `uv run pytest tests/test_due_soon_setting.py -x -q` | Yes -- existing file, needs deletion/replacement |
| PREF-11 | SQLite plist-parsing code deleted | integration | `uv run pytest -x -q` (full suite green = no references remain) | N/A -- deletion verified by suite |
| PREF-12 | Env var and config field deleted | integration | `uv run pytest -x -q` | N/A -- deletion verified by suite |
| PREF-13 | Tool descriptions updated | unit | `uv run pytest tests/test_descriptions.py -x -q` | Yes -- existing, needs assertion updates |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q --no-header --timeout=10`
- **Per wave merge:** `uv run pytest tests/ --timeout=10`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_preferences.py` -- covers PREF-02, PREF-03, PREF-08, PREF-09
- [ ] Update `tests/doubles/bridge.py` -- `InMemoryBridge` needs `get_settings` handler
- [ ] Update `tests/test_service_domain.py` -- normalize_date_input tests need field-aware assertions
- [ ] Delete `tests/test_due_soon_setting.py` -- SQLite plist tests become dead code
- [ ] Bridge JS test in `tests/bridge/` -- verify `handleGetSettings()` function (if Vitest tests exist)

## Sources

### Primary (HIGH confidence)
- `.research/deep-dives/timezone-behavior/05-settings-api/FINDINGS.md` -- empirical OmniJS settings API data, all 66 keys, user vs default values
- Codebase grep of all call sites, protocols, implementations for `get_due_soon_setting`, `normalize_date_input`, `_SETTING_MAP`

### Secondary (MEDIUM confidence)
- `.planning/phases/49-implement-naive-local-datetime-contract-for-all-date-inputs/49-CONTEXT.md` -- Phase 49 D-02 and D-06 establishing interim midnight behavior and domain.py placement

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries needed, pure codebase rewiring
- Architecture: HIGH -- all patterns verified in existing codebase, decisions locked
- Pitfalls: HIGH -- all based on verified codebase patterns and empirical settings API data

**Research date:** 2026-04-11
**Valid until:** 2026-05-11 (stable -- OmniJS API is established, codebase patterns well-understood)
