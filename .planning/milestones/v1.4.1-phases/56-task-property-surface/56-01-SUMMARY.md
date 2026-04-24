---
phase: 56-task-property-surface
plan: 01
subsystem: preferences
tags: [omnifocus-settings, bridge, preferences, lazy-load, factory-defaults]

requires:
  - phase: 50-use-omnifocus-settings-api-for-date-preferences-and-due-soon
    provides: "OmniFocusPreferences lazy-load-once pattern, bridge handleGetSettings function, InMemoryBridge.configure_settings"

provides:
  - "Bridge relays OFMCompleteWhenLastItemComplete + OFMTaskDefaultSequential alongside existing date keys"
  - "OmniFocusPreferences.get_complete_with_children_default() -> bool (factory default True)"
  - "OmniFocusPreferences.get_task_type_default() -> 'parallel' | 'sequential' (factory default 'parallel')"
  - "Absence-as-factory-default semantic: missing key OR null value resolves to OF factory default"
  - "InMemoryBridge._settings seeded with the two new keys for test ergonomics"

affects:
  - "56-05 (add_tasks create-default resolution PROP-05/06) consumes both getters"
  - "56-06 (edit_tasks write path) may consume getters for invariant checks"
  - "Any future plan that needs OF user-default resolution"

tech-stack:
  added: []
  patterns:
    - "Extend existing preferences module — no new settings-access code path"
    - "Absence-as-factory-default: `if key in raw and raw[key] is not None` guard, otherwise keep factory default"
    - "Bool coercion (bool(raw[key])) to mitigate tampering (T-56-01)"

key-files:
  created: []
  modified:
    - "src/omnifocus_operator/bridge/bridge.js — two keys added to handleGetSettings; handleGetSettings exported"
    - "src/omnifocus_operator/service/preferences.py — _FACTORY_DEFAULTS, __init__, _apply, two new async getters"
    - "tests/doubles/bridge.py — InMemoryBridge._settings seeded with factory defaults for the new keys"
    - "bridge/tests/bridge.test.js — 2 new Vitest tests (all-7-keys, null-tolerance)"
    - "tests/test_preferences.py — TestPreferencesNewTaskPropertyKeys class (9 tests)"
    - "tests/test_bridge.py — FACTORY_DEFAULTS fixture extended with the two new keys"

key-decisions:
  - "Raw-bool storage in _FACTORY_DEFAULTS for OFMTaskDefaultSequential; translation to 'parallel'/'sequential' happens in __init__ and _apply (getter is a pure pass-through)"
  - "Seed InMemoryBridge._settings with factory-default values so unconfigured tests never land on the absence-as-factory-default path (unless they explicitly pop the key)"
  - "Export handleGetSettings from bridge.js module.exports so Vitest can call it directly (closed IN-01 from phase 50 review)"
  - "Rule-1 auto-fix: extend existing TestInMemoryBridgeGetSettings.FACTORY_DEFAULTS fixture to match the new _settings dict shape"

patterns-established:
  - "Task-property preferences surface: extend OmniFocusPreferences, do not add a parallel settings reader"
  - "Presence AND non-null guard for each new preference key in _apply (absence-as-factory-default)"

requirements-completed: [PREFS-01, PREFS-02, PREFS-03, PREFS-04, PREFS-05]

duration: 4min
completed: 2026-04-19
---

# Phase 56 Plan 01: Preferences Extension Summary

**`OmniFocusPreferences` surfaces `completesWithChildren` + task-type defaults via the existing bridge-based lazy-load-once pattern — absence in the OF Setting store resolves to OF factory defaults (True / "parallel") with no plistlib dependency in the service layer.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-19T15:42:55Z
- **Completed:** 2026-04-19T15:46:54Z
- **Tasks:** 2 (both TDD)
- **Files modified:** 6

## Accomplishments

- Bridge relays two additional settings keys (`OFMCompleteWhenLastItemComplete`, `OFMTaskDefaultSequential`) alongside the existing five date-related keys.
- `OmniFocusPreferences` gained two new async getters (`get_complete_with_children_default`, `get_task_type_default`) sharing the existing lazy-load-once cache — a single `get_settings` bridge call per server lifetime regardless of how many getters are invoked.
- Absence-as-factory-default semantic is now encoded end-to-end: missing key OR null value leaves the factory default (True / "parallel") in place.
- Bridge-failure fallback exercises both new getters: factory defaults returned, `SETTINGS_FALLBACK_WARNING` emitted via the existing mechanism.
- `InMemoryBridge._settings` seeded with the two new keys so downstream test authors get factory-default behavior without configuring every key.
- Closed IN-01 (phase 50 review): `handleGetSettings` is now exported from `bridge.js` `module.exports` so Vitest can call it directly.

## Task Commits

Each task was committed atomically (TDD: RED step was covered by the GREEN-included failing test because the exported surface didn't exist yet):

1. **Task 1: Extend `bridge.js:handleGetSettings` with the two new preference keys** — `50139d65` (feat)
   - Added `OFMCompleteWhenLastItemComplete` and `OFMTaskDefaultSequential` to the `keys` array.
   - Exported `handleGetSettings` so Vitest can call it.
   - 2 Vitest tests: all-7-keys returned, null preserved for the new keys.

2. **Task 2: Extend `OmniFocusPreferences` + update `InMemoryBridge` defaults** — `2ecf5a8a` (feat)
   - `_FACTORY_DEFAULTS` + `__init__` initialisation of `_complete_with_children_default` / `_task_type_default`.
   - `_apply()` extended with two absence-aware blocks.
   - Two new async getters.
   - `InMemoryBridge._settings` seeded.
   - Fixture in `tests/test_bridge.py` updated to match the extended `_settings` shape (Rule-1 auto-fix).
   - 9 new tests in `TestPreferencesNewTaskPropertyKeys`.

_Plan metadata commit is created by the orchestrator after the full wave completes (STATE.md/ROADMAP.md are owned by the orchestrator per this plan's objective)._

## Files Created/Modified

- `src/omnifocus_operator/bridge/bridge.js` — `handleGetSettings` keys array extended (5 → 7 entries); `handleGetSettings` added to `module.exports`.
- `src/omnifocus_operator/service/preferences.py` — `_FACTORY_DEFAULTS` extended; `__init__` initialises two new cached attrs; `_apply()` extended with two absence-aware blocks; two new async getters (`get_complete_with_children_default`, `get_task_type_default`).
- `tests/doubles/bridge.py` — `InMemoryBridge._settings` seeded with factory defaults for the two new keys.
- `bridge/tests/bridge.test.js` — `describe("handleGetSettings", ...)` block with 2 tests (all-7-keys, null preserved).
- `tests/test_preferences.py` — new `TestPreferencesNewTaskPropertyKeys` class with 9 tests covering both bool paths, key-absent path, null-value path, cache-sharing invariant (PREFS-04), and bridge-failure fallback + warning.
- `tests/test_bridge.py` — `TestInMemoryBridgeGetSettings.FACTORY_DEFAULTS` fixture extended with the two new keys (Rule-1 auto-fix).

## Test Counts Added

- `bridge/tests/bridge.test.js`: **+2** Vitest tests (71 → 73 total).
- `tests/test_preferences.py`: **+9** tests in `TestPreferencesNewTaskPropertyKeys` (21 → 30 total).
- `tests/test_bridge.py`: fixture edit only, no new tests.

Overall pytest suite: **2177 passed** (was 2168 before this plan).

## Factory-Default Values Hard-Coded in `_FACTORY_DEFAULTS`

For future lookup, the task-property factory defaults now live alongside the existing date-preference defaults:

| Key | Type | Factory-default value | Domain meaning |
| --- | --- | --- | --- |
| `OFMCompleteWhenLastItemComplete` | `bool` | `True` | `completeWithChildren` on tasks/projects defaults to true (user can disable) |
| `OFMTaskDefaultSequential` | `bool` | `False` | task-type defaults to `"parallel"` (raw `False` → `"parallel"` translation in `__init__` / `_apply`) |

## Decisions Made

- **Raw-bool storage for `OFMTaskDefaultSequential` in `_FACTORY_DEFAULTS`, translated to `"parallel"` / `"sequential"` at read time.** Mirrors OF's Setting store contract (raw bool). Keeps `_FACTORY_DEFAULTS` as a single-source-of-truth for OF's on-disk representation.
- **Seed `InMemoryBridge._settings` with the two new keys at factory-default values.** Alternative was to leave them absent and require every test to configure them. Seeding keeps the test surface ergonomic; tests that want the absence path (`bridge._settings.pop(...)`) can still exercise it.
- **Export `handleGetSettings` from `bridge.js` `module.exports`.** Closes IN-01 from the phase 50 review. Without this, no Vitest coverage is possible.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Extended `TestInMemoryBridgeGetSettings.FACTORY_DEFAULTS` fixture**
- **Found during:** Task 2 verification run (full pytest suite).
- **Issue:** The existing `tests/test_bridge.py:TestInMemoryBridgeGetSettings` class asserted `result == self.FACTORY_DEFAULTS` against a hard-coded 5-key dict. After seeding `InMemoryBridge._settings` with the two new keys (plan-mandated), this assertion failed because the bridge now returned 7 keys.
- **Fix:** Extended the `FACTORY_DEFAULTS` ClassVar in `tests/test_bridge.py` with the two new keys (True / False), broadened the type annotation to include `bool`.
- **Files modified:** `tests/test_bridge.py`
- **Verification:** `uv run pytest tests/test_bridge.py --no-cov -x -q` — 23 tests pass.
- **Committed in:** `2ecf5a8a` (part of Task 2 commit).

**2. [Rule 3 - Blocking] Exported `handleGetSettings` from `bridge.js` `module.exports`**
- **Found during:** Task 1 RED run.
- **Issue:** The new Vitest tests failed with `bridge.handleGetSettings is not a function` because the function was implemented in phase 50 but never added to the test-entry `module.exports` list (flagged as IN-01 in phase 50 review, deferred at the time).
- **Fix:** Added `handleGetSettings: handleGetSettings` to the exports map.
- **Files modified:** `src/omnifocus_operator/bridge/bridge.js`
- **Verification:** Vitest tests green (73/73).
- **Committed in:** `50139d65` (Task 1 commit).

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking).
**Impact on plan:** Both deviations were necessary to complete the planned tasks — the `FACTORY_DEFAULTS` fixture had to reflect the new `_settings` shape the plan mandated, and `handleGetSettings` had to be exported before Vitest could exercise it. No scope creep.

## Issues Encountered

None. Plan executed cleanly under TDD. Both GREEN runs passed on first try.

## User Setup Required

None.

## Next Phase Readiness

- Wave 2 (read surface — default-response flags, hierarchy include group, `NEVER_STRIP` additions) can proceed without further preference-layer plumbing.
- Wave 3 (write surface — `add_tasks` create-default resolution via `PROP-05`/`PROP-06`) can consume `OmniFocusPreferences.get_complete_with_children_default()` and `get_task_type_default()` directly.
- No blockers introduced. No plistlib import, no `RealBridge` reference, no cache-direct access path introduced.

## Threat Flags

No new security-relevant surface introduced. The two new preference keys extend the existing trust boundary (OmniFocus → Python) with the same tampering mitigation as the date preferences: presence-and-non-null guard + explicit `bool()` coercion in `_apply` (T-56-01 already listed in the plan's threat register).

## Self-Check: PASSED

- FOUND: `src/omnifocus_operator/bridge/bridge.js` (modified)
- FOUND: `src/omnifocus_operator/service/preferences.py` (modified)
- FOUND: `tests/doubles/bridge.py` (modified)
- FOUND: `bridge/tests/bridge.test.js` (modified)
- FOUND: `tests/test_preferences.py` (modified)
- FOUND: `tests/test_bridge.py` (modified)
- FOUND: commit `50139d65`
- FOUND: commit `2ecf5a8a`
- VERIFIED: `grep "OFMCompleteWhenLastItemComplete" src/omnifocus_operator/bridge/bridge.js` — 1 occurrence in `handleGetSettings` keys array.
- VERIFIED: `grep "OFMTaskDefaultSequential" src/omnifocus_operator/bridge/bridge.js` — 1 occurrence.
- VERIFIED: `grep "import plistlib\|from plistlib" src/omnifocus_operator/service/preferences.py` — no results (PREFS-05 satisfied).
- VERIFIED: `grep "RealBridge" tests/test_preferences.py` — no results (SAFE-01 satisfied).
- VERIFIED: `uv run mypy src/omnifocus_operator/service/preferences.py` — Success: no issues found.
- VERIFIED: `uv run pytest tests/` — 2177 passed.
- VERIFIED: Vitest bridge suite — 73 passed.

---
*Phase: 56-task-property-surface*
*Completed: 2026-04-19*
