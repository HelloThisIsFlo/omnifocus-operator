# Phase 50: Use OmniFocus settings API for date preferences and due-soon threshold - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-11
**Phase:** 50-use-omnifocus-settings-api-for-date-preferences-and-due-soon
**Areas discussed:** Fallback behavior, DueSoon data source, Settings cache lifetime

---

## Fallback Behavior

### When settings are unavailable for date-only writes

| Option | Description | Selected |
|--------|-------------|----------|
| OmniFocus defaults (Recommended) | Use OmniFocus's documented factory defaults as hardcoded fallback: DefaultDueTime=17:00, DefaultStartTime=00:00, DefaultPlannedTime=09:00 | |
| Midnight (current behavior) | Keep T00:00:00 as fallback. Simple, predictable, already tested | |
| Educational error | Reject date-only input with a message requiring time component | |

**User's choice:** OmniFocus defaults + a warning in the response
**Notes:** User wanted the fallback to succeed (not error) but also wanted transparency — agent should know when configured times weren't available.

### Consistent DueSoon fallback

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, consistent fallback (Recommended) | Replace educational error with OF defaults (TWO_DAYS) + warning | ✓ |
| No, keep error for DueSoon | DueSoon failure on read side could silently return wrong results | |

**User's choice:** Yes, consistent fallback
**Notes:** Same pattern everywhere — succeed with defaults + warn.

### Error-serving mode check

**User's concern:** Wanted to verify no existing code triggers error-serving/degraded mode for missing DueSoon settings.
**Finding:** Confirmed — current code uses fallback + warning pattern (domain.py:237-243). No error-serving mode triggered. Phase 50 keeps this pattern.

---

## DueSoon Data Source

### SQLite plist-parsing vs bridge

| Option | Description | Selected |
|--------|-------------|----------|
| Replace entirely with bridge (Recommended) | Both repos use bridge settings. Delete plist code, _SETTING_MAP, env var. One source of truth. | ✓ |
| Keep SQLite as fast path | HybridRepo keeps SQLite, bridge only for DefaultDueTime | |
| Bridge primary, SQLite fallback | Try bridge first, fall back to SQLite. Belt and suspenders. | |

**User's choice:** Replace entirely with bridge
**Notes:** Simplifies codebase. One path for all settings.

---

## Settings Cache Lifetime + Architecture

### Settings lifecycle

| Option | Description | Selected |
|--------|-------------|----------|
| Lazy singleton, restart to refresh (Recommended) | Load on first use, cache for server lifetime. Next conversation picks up changes. | ✓ |
| Startup eager load | Read once at startup. Adds ~1.2s to startup. | |
| TTL cache with refresh | Cache with time-to-live. More complex. | |
| Per-request fresh read | Always fresh. ~1.2s per settings-needing request. Not viable. | |

**User's initial thought:** Considered background refresh (asyncio.create_task after response) or a reload endpoint.
**Discussion outcome:** Background refresh would freeze OmniFocus UI (~1.2s) after every settings-consuming request. Reload tool adds permanent API surface for a yearly event. Lazy singleton with restart is the simplest and fits MCP lifecycle (servers restart per conversation).

### Architecture: where does the cache live?

**User's design:** Separate preferences module, injected with Bridge, injected into service as a collaborator. NOT on the service itself, NOT in the repository.
**Rationale:** Settings aren't entity CRUD (not a repo concern) — they're config loading that the service consumes. Follows existing DI pattern.

---

## Tool Description Updates (added post-discussion)

**User's request:** Tool descriptions must inform agents about the user-configured defaults:
- **add_tasks / edit_tasks:** Date-only inputs use the user's OmniFocus default times (e.g., due dates default to configured time, not midnight)
- **list_tasks / list_projects:** The "soon" shortcut uses the user's OmniFocus due-soon threshold preference
- **All affected tools:** Brief note that date/time preferences are read from OmniFocus on first use; restart server if changed

---

## Claude's Discretion

- Bridge command design (name, response shape, which keys)
- Preferences module naming and placement
- `normalize_date_input()` signature change approach
- `_SETTING_MAP` migration details
- Time format parsing
- Test strategy (InMemoryBridge handler)
- Warning message wording
- `list_projects` pipeline adaptation

## Deferred Ideas

None — discussion stayed within phase scope.
