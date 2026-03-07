---
phase: 05-service-layer-and-mcp-server
verified: 2026-03-02T14:30:00Z
status: passed
score: 5/5 success criteria verified
re_verification:
  previous_status: passed
  previous_score: 12/12
  gaps_closed:
    - "TOOL-01: list_all response now contains non-empty collections with visible camelCase field names (dueDate, inInbox, taskStatus, allowsNextAction)"
    - "TOOL-04: stdout redirect removed (it broke MCP connection); replaced with static grep test that enforces no print() calls in source"
  gaps_remaining: []
  regressions: []
---

# Phase 5: Service Layer and MCP Server — Verification Report

**Phase Goal:** A running MCP server with the `list_all` tool that returns the full structured database, wired with dependency injection so the bridge implementation is swappable at startup
**Verified:** 2026-03-02T14:30:00Z
**Status:** PASSED
**Re-verification:** Yes — after gap closure (UAT issues resolved via Plan 03 and stdout fix)

---

## Goal Achievement

### Observable Truths (Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `list_all` returns full DatabaseSnapshot as structured Pydantic data via MCP protocol | VERIFIED | `_server.py` line 89: `return await service.get_all_data()`. `TestTOOL01ListAllStructuredOutput` confirms `structuredContent` has all 5 keys. `_factory.py` now seeds 1 item per collection so collections are non-empty. |
| 2 | Tool has `readOnlyHint=True` and `idempotentHint=True` annotations | VERIFIED | `_server.py` line 78: `ToolAnnotations(readOnlyHint=True, idempotentHint=True)`. `TestTOOL02Annotations` verifies both hints via live MCP tool listing. |
| 3 | Structured output schema (from Pydantic models) in tool definition, with camelCase field names | VERIFIED | `DatabaseSnapshot` is a runtime import (noqa: TC001) so FastMCP resolves `get_type_hints()`. `test_output_schema_uses_camelcase` confirms `dueDate` and `effectiveFlagged` in `$defs.Task.properties`. |
| 4 | All server output goes to stderr; stdout reserved for MCP protocol traffic | VERIFIED | `__main__.py` line 15: `logging.basicConfig(stream=sys.stderr)`. `test_no_print_calls_in_source` statically scans all source files and asserts zero `print()` calls. FastMCP stdio transport writes protocol JSON to stdout directly — not intercepted. |
| 5 | Switching bridge requires zero code changes (env var only) | VERIFIED | `_server.py` line 45: `os.environ.get("OMNIFOCUS_BRIDGE", "real")`. `create_bridge()` factory isolates bridge selection. `TestARCH02BridgeInjection` verifies env var controls bridge selection. No import or code change needed to switch. |

**Score:** 5/5 success criteria verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/omnifocus_operator/service/__init__.py` | Public re-exports for service package; exports OperatorService | VERIFIED | `__all__ = ["OperatorService"]`; imports from `_service` |
| `src/omnifocus_operator/service/_service.py` | OperatorService thin passthrough to repository | VERIFIED | `class OperatorService`, `__init__(self, repository)`, `async def get_all_data()` returns `await self._repository.get_snapshot()` |
| `src/omnifocus_operator/repository/_mtime.py` | ConstantMtimeSource added alongside MtimeSource and FileMtimeSource | VERIFIED | All three classes present; `@runtime_checkable` on `MtimeSource` protocol |
| `src/omnifocus_operator/bridge/_factory.py` | create_bridge factory with match/case, InMemoryBridge seeded with sample data | VERIFIED | match/case for all four cases; "inmemory" case passes realistic 1-item-per-collection dict with camelCase keys (dueDate, inInbox, taskStatus, allowsNextAction, builtin) |
| `src/omnifocus_operator/server/__init__.py` | Public re-exports for server package; exports create_server | VERIFIED | `__all__ = ["create_server"]`; imports from `_server` |
| `src/omnifocus_operator/server/_server.py` | FastMCP server setup, lifespan, tool registration | VERIFIED | `app_lifespan`, `_register_tools`, `create_server` all present and substantive; 101 lines |
| `src/omnifocus_operator/__main__.py` | Entry point: stderr logging config, server.run() | VERIFIED | `logging.basicConfig(stream=sys.stderr)`, `server = create_server(); server.run(transport="stdio")`. No `sys.stdout = sys.stderr` (removed — it corrupted MCP protocol traffic). |
| `tests/test_service.py` | Unit tests for OperatorService, ConstantMtimeSource, bridge factory | VERIFIED | 10 tests; all pass. |
| `tests/test_server.py` | In-process MCP integration tests | VERIFIED | 10 tests across 5 test classes; all pass. `TestTOOL04StdoutClean` uses static source grep instead of runtime redirect check. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `server/_server.py` | `service/_service.py` | lifespan creates OperatorService; tools access via `ctx.request_context.lifespan_context["service"]` | WIRED | Line 59: `service = OperatorService(repository=repository)`. Line 88: `ctx.request_context.lifespan_context["service"]` |
| `server/_server.py` | `bridge/_factory.py` | lifespan calls `create_bridge(bridge_type)` | WIRED | Line 41: `from omnifocus_operator.bridge import create_bridge`. Line 48: `bridge = create_bridge(bridge_type)` |
| `__main__.py` | `server/_server.py` | imports `create_server` and calls `server.run(transport='stdio')` | WIRED | Line 18: `from omnifocus_operator.server import create_server`. Lines 20-21: `server = create_server(); server.run(transport="stdio")` |
| `service/_service.py` | `repository/_repository.py` | constructor injection of OmniFocusRepository; `self._repository` | WIRED | Line 27: `def __init__(self, repository: OmniFocusRepository)`. Line 37: `return await self._repository.get_snapshot()` |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| ARCH-01 | 05-01, 05-02 | Server uses three-layer architecture (MCP Server -> Service Layer -> Repository) | SATISFIED | `_server.py` wires tool -> `OperatorService` -> `OmniFocusRepository`. `TestARCH01ThreeLayerArchitecture::test_list_all_returns_data_through_all_layers` passes. |
| ARCH-02 | 05-01, 05-02 | Bridge implementation injected at startup — no code changes to switch bridges | SATISFIED | `OMNIFOCUS_BRIDGE` env var selects bridge type in lifespan; `create_bridge()` factory isolates bridge-creation concern. `TestARCH02BridgeInjection` confirms env var selects bridge and default 'real' raises cleanly. |
| TOOL-01 | 05-02, 05-03 | `list_all` tool returns full structured database as typed Pydantic data | SATISFIED | `list_all` returns `DatabaseSnapshot`. `structuredContent` now contains non-empty collections (1 item each) with camelCase keys visible. `TestTOOL01ListAllStructuredOutput::test_list_all_structured_content_is_camelcase` passes (dueDate, effectiveFlagged visible; due_date, effective_flagged absent). |
| TOOL-02 | 05-02 | Tool includes MCP annotations (`readOnlyHint`, `idempotentHint`) | SATISFIED | `ToolAnnotations(readOnlyHint=True, idempotentHint=True)` passed to `@mcp.tool()`. Both annotation tests pass via live MCP protocol. |
| TOOL-03 | 05-02 | Tool exposes structured output schema from Pydantic models | SATISFIED | `DatabaseSnapshot` runtime import (noqa: TC001) enables FastMCP `get_type_hints()`. Schema has camelCase `$defs.Task.properties`. `test_output_schema_uses_camelcase` passes. |
| TOOL-04 | 05-02 | Server logs to stderr only (stdout reserved for MCP protocol) | SATISFIED | `logging.basicConfig(stream=sys.stderr)` ensures all log output goes to stderr. `test_no_print_calls_in_source` statically enforces no `print()` calls exist anywhere in source. No runtime stdout redirect (correctly removed — the redirect corrupted MCP protocol traffic). |

No orphaned requirements: REQUIREMENTS.md maps exactly ARCH-01, ARCH-02, TOOL-01, TOOL-02, TOOL-03, TOOL-04 to Phase 5. All six are satisfied.

---

### Anti-Patterns Found

No blockers or warnings.

- No `TODO`, `FIXME`, `XXX`, `HACK`, or `PLACEHOLDER` comments in any phase-created file
- No `return null`, `return {}`, `return []` stubs in logic paths
- No `print()` calls anywhere in source (verified statically by `test_no_print_calls_in_source`)
- One intentional `# noqa: TC001` on `_server.py` line 24 — required and documented (FastMCP `get_type_hints()` needs `DatabaseSnapshot` in module namespace)
- `__main__.py` no longer has `# type: ignore[assignment]` — correctly removed along with the `sys.stdout` redirect

---

### Human Verification Required

None. All five success criteria are verified programmatically:

- Success criterion 1 (structured data): `TestTOOL01ListAllStructuredOutput` exercises full MCP protocol path with in-process memory streams.
- Success criterion 2 (annotations): `TestTOOL02Annotations` reads annotations from live MCP tool listing.
- Success criterion 3 (output schema): `TestTOOL03OutputSchema` reads schema from live MCP tool listing.
- Success criterion 4 (stderr only): `test_no_print_calls_in_source` is a static analysis scan; `basicConfig(stream=sys.stderr)` is directly inspectable.
- Success criterion 5 (config-only bridge switch): `TestARCH02BridgeInjection` verifies `OMNIFOCUS_BRIDGE` env var controls bridge selection end-to-end.

---

## Verification Summary

Phase 5 goal is fully achieved. All 5 success criteria verified against the actual codebase. 105 tests pass, 97.09% coverage.

**Key changes since initial VERIFICATION.md (2026-03-02T12:50:00Z):**

**Gap 1 closed — TOOL-01 camelCase visibility:** `_factory.py` now seeds InMemoryBridge with one realistic item per collection using camelCase keys (`dueDate`, `inInbox`, `taskStatus`, `allowsNextAction`, `builtin`). The camelCase serialization path is now exercised by both the factory data and the dedicated camelCase test.

**Gap 2 closed — TOOL-04 stdout safety:** The `sys.stdout = sys.stderr` redirect was removed from `__main__.py` because it also redirected FastMCP's protocol output to stderr, breaking the MCP connection. The protection against stray `print()` calls is now enforced statically via `test_no_print_calls_in_source`, which scans all `.py` files under `src/` at test time. This is a strictly better approach: it catches violations at the right layer (CI/test) without interfering with the runtime stdio transport.

**Three-layer architecture** remains correctly wired: `__main__.py` -> `create_server()` -> `app_lifespan` (DI wiring) -> `list_all` tool -> `OperatorService.get_all_data()` -> `OmniFocusRepository.get_snapshot()` -> `InMemoryBridge.send_command()`.

---

_Verified: 2026-03-02T14:30:00Z_
_Verifier: Claude (gsd-verifier)_
