---
phase: 50-use-omnifocus-settings-api-for-date-preferences-and-due-soon
reviewed: 2026-04-11T00:00:00Z
depth: standard
files_reviewed: 20
files_reviewed_list:
  - src/omnifocus_operator/agent_messages/descriptions.py
  - src/omnifocus_operator/agent_messages/warnings.py
  - src/omnifocus_operator/bridge/bridge.js
  - src/omnifocus_operator/config.py
  - src/omnifocus_operator/contracts/protocols.py
  - src/omnifocus_operator/repository/bridge_only/bridge_only.py
  - src/omnifocus_operator/repository/hybrid/hybrid.py
  - src/omnifocus_operator/server.py
  - src/omnifocus_operator/service/domain.py
  - src/omnifocus_operator/service/preferences.py
  - src/omnifocus_operator/service/service.py
  - tests/conftest.py
  - tests/doubles/bridge.py
  - tests/test_bridge.py
  - tests/test_list_pipelines.py
  - tests/test_preferences.py
  - tests/test_server.py
  - tests/test_service_domain.py
  - tests/test_service.py
  - tests/test_warnings.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 50: Code Review Report

**Reviewed:** 2026-04-11
**Depth:** standard
**Files Reviewed:** 20
**Status:** issues_found

## Summary

Phase 50 adds `OmniFocusPreferences`, a lazy-loaded, cached abstraction over the new `get_settings` bridge command. The architecture is solid — lazy load with re-entry protection, factory-default fallback, domain-typed outputs. The `_AddTaskPipeline` and `_EditTaskPipeline` both call into it correctly, and the test coverage is thorough.

Three issues warrant attention:

1. **Logic error in `matches_inbox_name`** — the substring check is reversed, causing false positives for many short strings.
2. **Protocol coupling in `server.py`** — the lifespan directly accesses `repository._bridge`, which breaks when using any repository that doesn't expose a public `_bridge` attribute.
3. **`_apply` in preferences can throw uncaught** — `int()` coercions are outside the bridge-call try/except block.

Two info-level items: `handleGetSettings` missing from bridge.js test exports, and a `_normalize_time` edge case for malformed inputs.

---

## Warnings

### WR-01: `matches_inbox_name` substring check is reversed

**File:** `src/omnifocus_operator/service/service.py:100`

**Issue:** The function checks `value.lower() in "Inbox".lower()`, which tests whether the *user's input* is a substring of `"inbox"` — not whether `"inbox"` appears in the user's input. This means any string of length <= 5 that is a substring of `"inbox"` (e.g. `"in"`, `"nb"`, `"ox"`, `"x"`, `"o"`, `""`) triggers the inbox warning, while longer strings containing "inbox" (e.g. `"my inbox tasks"`) do not.

The intent appears to be: warn when the user's project filter value contains the word "inbox" as a substring.

**Fix:**
```python
def matches_inbox_name(value: object) -> bool:
    """Check if the inbox name is a case-insensitive substring of the value."""
    if not isinstance(value, str):
        return False
    return "inbox" in value.lower()
```

---

### WR-02: `server.py` accesses `repository._bridge` — breaks non-bridge repositories

**File:** `src/omnifocus_operator/server.py:108`

**Issue:** The lifespan constructs `OmniFocusPreferences` by reaching directly into the repository's private attribute:

```python
preferences = OmniFocusPreferences(repository._bridge)
```

`_bridge` is not part of the `Repository` protocol. If a repository implementation doesn't have this attribute (e.g. a future pure-SQLite mode, or a mock in tests), this raises `AttributeError` at startup, bypassing the `ErrorOperatorService` fallback and crashing the server cold.

It also tightly couples the server startup to the concrete repository implementation detail.

**Fix:** Expose the bridge through the `create_repository` factory or pass it separately. The cleanest option given the current design is a named return from `create_repository`:

```python
# Option A: return bridge alongside repository
repository, bridge = create_repository(repo_type)
preferences = OmniFocusPreferences(bridge)
```

Or, if the bridge is always present on write-capable repositories, narrow the type at creation time and access it through a protocol method rather than a private attribute.

---

### WR-03: `int()` coercions in `_apply` are outside the fallback try/except

**File:** `src/omnifocus_operator/service/preferences.py:128-129`

**Issue:** `_apply` is called from `_ensure_loaded` *after* the try/except block that wraps the bridge call:

```python
try:
    raw = await self._bridge.send_command("get_settings")
except Exception:
    ...
    return

self._apply(raw)   # <-- outside try/except
```

Inside `_apply`, the coercions `int(interval)` and `int(granularity)` on line 128-129 will raise `ValueError` if OmniFocus returns non-numeric values for those fields (e.g. `None`, a string like `"unknown"`, etc.). That exception propagates uncaught up through `_ensure_loaded`, through the caller (`get_due_soon_setting` / `get_default_time`), and ultimately surfaces as an unhandled error in the pipeline.

Since `_loaded` is set to `True` before the bridge call, a failure in `_apply` leaves the object in a state where `_loaded=True` but the values are still at factory defaults — which is actually the correct fallback behavior, but the exception still propagates rather than silently using the defaults.

**Fix:**

```python
self._loaded = True  # Before bridge call

try:
    raw = await self._bridge.send_command("get_settings")
except Exception:
    logger.warning("Failed to read OmniFocus preferences; using factory defaults")
    self._warnings.append(SETTINGS_FALLBACK_WARNING)
    return

try:
    self._apply(raw)
except Exception:
    logger.warning("Failed to parse OmniFocus preferences; using factory defaults")
    self._warnings.append(SETTINGS_FALLBACK_WARNING)
```

---

## Info

### IN-01: `handleGetSettings` not exported for Vitest tests

**File:** `src/omnifocus_operator/bridge/bridge.js:443-464`

**Issue:** The new `handleGetSettings` function added in this phase is not included in `module.exports`. The test entry point exports all other operation handlers (`handleGetAll`, `handleAddTask`, `handleEditTask`) but omits the new one. This means Vitest tests cannot call `handleGetSettings` directly if unit tests are ever added.

**Fix:**
```js
module.exports = {
    readRequest, writeResponse,
    handleGetAll, handleAddTask, handleEditTask, handleGetSettings,  // add handleGetSettings
    dispatch,
    d, pk, rr, ri, ts, ps, gs, fs, rst, adk, reverseRst, reverseAdk,
};
```

---

### IN-02: `_normalize_time` silent pass-through on malformed input

**File:** `src/omnifocus_operator/service/preferences.py:81-90`

**Issue:** `_normalize_time` handles two-part (`HH:MM`) and three-part (`HH:MM:SS`) splits, but silently returns the raw value unchanged for any other shape (e.g. a single segment `"1700"`, four segments `"19:00:00:00"`, or an empty string). This is a defensive-coding gap — not a current bug since OmniFocus only returns these two formats — but the function gives no indication that the input was unrecognized.

**Fix:** Add a fallback log or assertion for unexpected formats:
```python
@staticmethod
def _normalize_time(raw: str) -> str:
    parts = raw.split(":")
    if len(parts) == 2:
        return f"{parts[0]}:{parts[1]}:00"
    if len(parts) == 3:
        return raw
    logger.warning("Unexpected time format from OmniFocus preferences: %r", raw)
    return raw
```

---

_Reviewed: 2026-04-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
