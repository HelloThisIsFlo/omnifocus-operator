# Quick Task 260317-j2x: Fix F-6 — Echo invalid lifecycle value in error message

**Status:** Complete
**Commit:** 89ba983

## Changes

- **warnings.py**: Added `LIFECYCLE_INVALID_VALUE` and `UNKNOWN_FIELD` constants
- **server.py**: Intercept `literal_error` for lifecycle field, echo invalid value with allowed values; replaced inline `"Unknown field"` f-strings with `UNKNOWN_FIELD` constant
- **test_server.py**: Strengthened lifecycle error test to assert invalid value is echoed back
- **test_warnings.py**: Broadened consolidation test to scan both `service.py` and `server.py` as warning consumers; added `"messages"` list name to inline string detection

## Verification

- `edit_tasks` with `lifecycle: "invalid"` returns: `Invalid lifecycle action 'invalid' -- must be 'complete' or 'drop'`
- No Pydantic internals (`type=`, `input_value`, `pydantic`) leak into error messages
- All 517 tests pass, mypy clean
