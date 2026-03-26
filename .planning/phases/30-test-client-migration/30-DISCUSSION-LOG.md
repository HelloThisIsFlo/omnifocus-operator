# Phase 30: Test Client Migration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-26
**Phase:** 30-test-client-migration
**Areas discussed:** Migration scope, Fixture strategy, Error assertion depth

---

## Migration scope

| Option | Description | Selected |
|--------|-------------|----------|
| Include all files | Migrate conftest.py, test_server.py, test_simulator_bridge.py, test_simulator_integration.py | ✓ |
| Defer simulator files | Only migrate conftest.py and test_server.py per TEST-01–TEST-05 literal scope | |

**User's choice:** Include all files
**Notes:** D-09 from Phase 29 ("built from scratch with fastmcp>=3") makes it clear — no manual plumbing should survive anywhere.

---

## Fixture strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Fixture yields Client | 6-line async fixture in conftest.py, tests inject client: Client | ✓ |
| Inline async with per test | No fixture, each test wraps body in async with Client(server) | |

**User's choice:** Fixture yields Client
**Notes:** User asked to see code examples for both options before deciding. The fixture approach keeps tests clean (no extra nesting), especially for error tests where `pytest.raises` + `async with` would stack two context managers. User confirmed after seeing the code side-by-side.

---

## Error assertion depth

| Option | Description | Selected |
|--------|-------------|----------|
| Remove entirely | Delete all isError-is-not-True guards, no exception = success | ✓ |
| Replace with structured_content check | Swap each guard for assert result.structured_content is not None | |

**User's choice:** Remove entirely
**Notes:** User raised a concern about test readability — tests should not look like "what's the point?" after removing guards. Verified that no orphan tests exist: every guard is either followed by content assertions or is a setup step in a clearly-named test. User agreed to pragmatic approach: remove all, but if any test looks ambiguous during implementation, add try/except with pytest.fail for that specific case.

---

## Claude's Discretion

- Import organization within test files
- Whether to rename `client_session` → `client` in one commit or split across files

## Deferred Ideas

None — discussion stayed within phase scope
