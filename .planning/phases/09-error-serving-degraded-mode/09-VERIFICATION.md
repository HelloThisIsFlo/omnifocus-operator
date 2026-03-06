---
phase: 09-error-serving-degraded-mode
verified: 2026-03-06T20:10:00Z
status: passed
score: 6/6 must-haves verified
---

# Phase 9: Error-Serving Degraded Mode Verification Report

**Phase Goal:** Fatal startup errors are caught and served as actionable tool responses instead of crashing the headless MCP server -- the agent discovers the error on first tool call with a clear message and restart instruction
**Verified:** 2026-03-06T20:10:00Z
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Fatal startup error does NOT crash the MCP server process | VERIFIED | `app_lifespan` has `except Exception as exc` at line 86 of `_server.py`, yields `ErrorOperatorService` instead of propagating. Integration test `test_tool_call_returns_error_when_lifespan_fails` confirms server stays alive. |
| 2 | Agent calling any tool after a startup failure gets an actionable error message | VERIFIED | `ErrorOperatorService.__getattr__` raises `RuntimeError` with formatted message. Integration test asserts `result.isError is True` and `"failed to start"` in text. |
| 3 | Error message includes the original exception text and restart instruction | VERIFIED | Format string: `f"OmniFocus Operator failed to start:\n\n{error!s}\n\nRestart the server after fixing."`. Unit tests `test_getattr_raises_for_arbitrary_attribute` (matches "bad config") and `test_error_message_includes_restart_instruction` (matches "Restart the server after fixing"). |
| 4 | WARNING is logged for each tool call made in degraded mode | VERIFIED | `__getattr__` calls `logger.warning("Tool call in error mode (attribute: %s)", name)`. Integration test `test_degraded_mode_logs_warning_on_tool_call` asserts "error mode" in WARNING records. |
| 5 | Full traceback is logged to stderr at ERROR level when startup fails | VERIFIED | `logger.exception("Fatal error during startup")` in except block (line 87). Integration test `test_degraded_mode_logs_traceback_at_error_level` asserts "Fatal error during startup" in ERROR records. |
| 6 | `__main__.py` has no pre-async validation -- just create_server + run | VERIFIED | `grep -c "bridge_type.*real" __main__.py` returns 0. File is 25 lines: logging setup, `create_server()`, `server.run(transport="stdio")`. No `sys.exit`, no `os.path.exists` checks. |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/omnifocus_operator/service/_service.py` | ErrorOperatorService class | VERIFIED | Class at line 43, subclasses OperatorService, `__init__` uses `object.__setattr__`, `__getattr__` returns `NoReturn`. 100% coverage. |
| `src/omnifocus_operator/service/__init__.py` | ErrorOperatorService in exports | VERIFIED | Import and `__all__` both include `ErrorOperatorService`. |
| `src/omnifocus_operator/server/_server.py` | try/except in app_lifespan yielding ErrorOperatorService on failure | VERIFIED | try block wraps entire lifespan body (lines 41-85), except at line 86 yields error service (line 91). 95% coverage. |
| `src/omnifocus_operator/__main__.py` | Simplified entry point without pre-async validation | VERIFIED | 25 lines total. No bridge_type check, no sys.exit, no os.path.exists. |
| `tests/test_service.py` | TestErrorOperatorService unit tests | VERIFIED | 5 tests in `TestErrorOperatorService` class (lines 145-189). All pass. |
| `tests/test_server.py` | Degraded mode integration tests | VERIFIED | `TestDegradedMode` class with 3 tests (lines 456-537). Updated `test_default_real_bridge_fails_at_startup` verifies degraded mode (line 128-144). All pass. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `server/_server.py` | `service/_service.py` | ErrorOperatorService import and instantiation in except branch | WIRED | Line 88: `from omnifocus_operator.service import ErrorOperatorService`, line 90: `error_service = ErrorOperatorService(exc)` |
| `server/_server.py` | tool handlers | yield with same dict key as normal path | WIRED | Line 91: `yield {"service": error_service}` -- same `"service"` key as normal path (line 83) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| ERR-01 | 09-01 | ErrorOperatorService raises RuntimeError with message on get_all_data | SATISFIED | Unit test `test_getattr_raises_runtime_error` accesses `_repository` (what `get_all_data` uses internally), asserts RuntimeError |
| ERR-02 | 09-01 | ErrorOperatorService.__getattr__ raises for any attribute | SATISFIED | Unit test `test_getattr_raises_for_arbitrary_attribute` accesses `some_future_method` |
| ERR-03 | 09-01 | app_lifespan catches exceptions and yields ErrorOperatorService | SATISFIED | try/except in `_server.py` lines 41-92; integration test `test_tool_call_returns_error_when_lifespan_fails` |
| ERR-04 | 09-01 | Tool call through error service returns isError=True with message | SATISFIED | Integration test asserts `result.isError is True` and `"failed to start"` in text |
| ERR-05 | 09-01 | __main__.py no longer has pre-async validation | SATISFIED | `grep -c "bridge_type.*real" __main__.py` returns 0; updated `test_default_real_bridge_fails_at_startup` now tests degraded mode |
| ERR-06 | 09-01 | Traceback logged to stderr at ERROR level on startup failure | SATISFIED | `logger.exception("Fatal error during startup")` at line 87; integration test verifies |
| ERR-07 | 09-01 | WARNING logged for each tool call in error mode | SATISFIED | `logger.warning(...)` in `__getattr__`; integration test verifies |

**Note:** ERR-01 through ERR-07 are referenced in ROADMAP.md and PLAN frontmatter but are NOT formally defined in REQUIREMENTS.md. They appear only in RESEARCH.md and VALIDATION.md. This is an administrative gap -- the requirements are satisfied in code but should be added to REQUIREMENTS.md for traceability completeness.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| -- | -- | -- | -- | -- |

No anti-patterns found. No TODOs, FIXMEs, placeholders, empty implementations, or console-log-only handlers in any modified files.

### Human Verification Required

None. All behaviors are fully testable programmatically and covered by the test suite (29 tests pass, 80.04% coverage).

### Gaps Summary

No gaps found. All 6 observable truths are verified. All 6 artifacts pass existence, substantive, and wiring checks. Both key links are confirmed wired. All 7 requirement IDs are satisfied by tested implementation. Tests pass (29/29). No anti-patterns detected.

**Administrative note:** ERR-01 through ERR-07 should be added to REQUIREMENTS.md traceability table for completeness, but this does not block phase goal achievement.

---

_Verified: 2026-03-06T20:10:00Z_
_Verifier: Claude (gsd-verifier)_
