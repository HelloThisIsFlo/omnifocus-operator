# Phase 29: Dependency Swap & Imports - Research

**Researched:** 2026-03-26
**Domain:** FastMCP v3 migration (dependency swap, import migration, progress reporting)
**Confidence:** HIGH

## Summary

Phase 29 is a mechanical migration: swap `mcp>=1.26.0` for `fastmcp>=3.1.1`, rewrite two import lines in `server.py`, shorten six `ctx.request_context.lifespan_context` calls to `ctx.lifespan_context`, simplify six `Context[Any, Any, Any]` annotations to `Context`, add `report_progress()` to two batch handlers, clean up `pyproject.toml`, and update docs. The spike experiments (exp 01, 06) have proven every change works. No architectural decisions remain.

One important finding: `ToolAnnotations` is NOT re-exported by `fastmcp`. It must stay as `from mcp.types import ToolAnnotations`. This is acceptable per D-09 since `mcp` is available as a transitive dependency of `fastmcp`, and there is no `fastmcp` equivalent to migrate to.

**Primary recommendation:** Execute as a single linear wave -- all changes are in `server.py`, `__main__.py`, `pyproject.toml`, `README.md`, and `docs/index.html`. No cross-cutting dependencies.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** `from mcp.server.fastmcp import FastMCP, Context` -> `from fastmcp import FastMCP, Context` (src/ only -- test imports are Phase 30)
- **D-02:** `ToolAnnotations` -- use the idiomatic FastMCP v3 import, not `from mcp.types`. Researcher should verify where `fastmcp` exports it
- **D-03:** `ctx.request_context.lifespan_context` -> `ctx.lifespan_context` shorthand wherever it appears
- **D-04:** `pyproject.toml` replaces `mcp>=1.26.0` with `fastmcp>=3.1.1` -- `mcp` remains available as a transitive dependency
- **D-05:** Add `ctx.report_progress(progress=i, total=total)` to `add_tasks` and `edit_tasks` -- even though batch limit is currently 1
- **D-06:** Report at MCP handler level (in `server.py`), not inside the service pipeline
- **D-07:** Update README.md and landing page to reflect `fastmcp>=3.1.1` as the dependency
- **D-08:** "Single runtime dependency" messaging stays accurate -- just the name changes
- **D-09:** Milestone-wide philosophy: code should look native to FastMCP v3. No `mcp.*` imports in src/ if `fastmcp` provides an equivalent
- **D-10:** `Context` type annotation -- adopt simpler type signature if FastMCP v3 has one
- **D-11:** Server entry point -- adopt idiomatic FastMCP v3 runner if different
- **D-12:** Leave `# TODO(Phase NN):` comments for deferred cleanup
- **D-13:** Delete the `spike` dependency group from `pyproject.toml` (lines 28-31)

### Claude's Discretion
- Exact placement of `report_progress` calls within the handler (before/after validation, etc.)
- Whether to add a `log_tool_call` for progress events or keep it minimal

### Deferred Ideas (OUT OF SCOPE)
- Lifting the batch limit on `add_tasks`/`edit_tasks` -- separate concern, different milestone
- Test client migration from `mcp.client.session` -- Phase 30
- Logging overhaul -- Phase 31

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DEP-01 | Server runs on `fastmcp>=3.1.1` with all 6 tools functional | Spike exp 01 proved imports + lifespan work identically; `server.run(transport="stdio")` signature unchanged |
| DEP-02 | All imports migrated from `mcp.server.fastmcp` to `fastmcp` | Only `server.py:16` needs changing; `ToolAnnotations` stays at `mcp.types` (not available in fastmcp) |
| DEP-03 | `ctx.lifespan_context` shorthand replaces `ctx.request_context.lifespan_context` | 6 occurrences in `server.py`; spike exp 01 confirmed both paths work |
| DEP-04 | `pyproject.toml` declares `fastmcp>=3.1.1` replacing `mcp>=1.26.0` | Replace line 8, delete lines 28-31 (spike group); `mcp` stays as transitive dep |
| PROG-01 | `add_tasks` reports progress via `ctx.report_progress()` | Spike exp 06 reference; `report_progress(progress=float, total=float\|None)` signature verified |
| PROG-02 | `edit_tasks` reports progress via `ctx.report_progress()` | Same pattern as PROG-01; no-ops gracefully when client lacks `progressToken` |
| DOC-01 | README reflects `fastmcp>=3.1.1` as runtime dependency | Lines 54, 121 in README.md reference `mcp>=1.26.0` |
| DOC-02 | Landing page reflects new dependency | `docs/index.html` line 1852 references `mcp>=1.26.0` |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **SAFE-01/02:** No automated tests touch the real Bridge; all testing uses `InMemoryBridge` or `SimulatorBridge`
- **Service Layer Convention:** Method Object pattern (`_Pipeline`); progress reporting stays at MCP handler level per D-06
- **UAT for refactoring phases:** Focus on developer experience (package layout, naming, import patterns)
- **Strict mypy:** `strict = true` with pydantic plugin -- all type changes must pass mypy
- **Ruff:** line-length 100, target py312, `.research` and `.claude` excluded

## Verified API Findings

### D-02 Resolution: ToolAnnotations

**Finding:** `ToolAnnotations` is NOT exported by `fastmcp` at any level.
- `from fastmcp import ToolAnnotations` -- ImportError
- `from fastmcp.types import ToolAnnotations` -- ImportError
- `from mcp.types import ToolAnnotations` -- works (transitive dep)

**Decision:** Keep `from mcp.types import ToolAnnotations`. This is the only `mcp.*` import that must remain in `src/`. Per D-09, this is acceptable because `fastmcp` provides no equivalent -- we're not being lazy, the re-export simply doesn't exist. Add a `# TODO(Phase NN):` comment if desired, but there's nothing to migrate to today.

**Confidence:** HIGH -- verified against fastmcp 3.1.0 installed in project venv. Also confirmed by spike experiment 01 which uses the same pattern.

### D-10 Resolution: Context Type Annotation

**Finding:** FastMCP v3 `Context` is a plain class, NOT generic.
- Old `mcp` SDK: `Context` was `Generic[ServerDepsT, LifespanContextT, RequestT]` requiring `Context[Any, Any, Any]`
- FastMCP v3: `Context` is a plain class in `fastmcp.server.context` with no `__class_getitem__`
- `Context[Any, Any, Any]` will raise `TypeError` at runtime with FastMCP v3

**Decision:** All 6 type annotations change from `ctx: Context[Any, Any, Any]` to `ctx: Context`. The `from typing import Any` import can be removed from server.py (unless used elsewhere).

**Confidence:** HIGH -- verified programmatically: `Context.__type_params__` is empty, no `__class_getitem__`.

### D-11 Resolution: Server Entry Point

**Finding:** `server.run(transport="stdio")` signature is identical in FastMCP v3.
- `FastMCP.run` signature: `(self, transport: Transport | None = None, show_banner: bool | None = None, **transport_kwargs) -> None`
- The `transport="stdio"` call in `__main__.py` works unchanged

**Decision:** No change to entry point. `server.run(transport="stdio")` is already idiomatic FastMCP v3.

**Confidence:** HIGH -- verified via `inspect.signature(FastMCP.run)`.

### report_progress Signature

**Verified:** `report_progress(self, progress: float, total: float | None = None, message: str | None = None) -> None`
- `progress` and `total` are floats (not ints), but integer values work fine
- `message` parameter exists but is not rendered by any major client (per spike findings)
- No-ops gracefully when client doesn't send `progressToken`

**Confidence:** HIGH -- verified via `inspect.signature`.

## Architecture Patterns

### Change Map

All changes are in 5 files:

```
src/omnifocus_operator/server.py    # Import migration, Context type, lifespan shorthand, progress
src/omnifocus_operator/__main__.py  # TODO comment for Phase 31 logging redesign
pyproject.toml                      # Dependency swap, spike group deletion
README.md                           # Dependency name change (2 locations)
docs/index.html                     # Dependency name change (1 location)
```

### server.py Changes (detailed)

**Line 16 -- Import migration:**
```python
# Before
from mcp.server.fastmcp import Context, FastMCP
# After
from fastmcp import FastMCP, Context
```

**Line 17 -- ToolAnnotations stays:**
```python
from mcp.types import ToolAnnotations  # no fastmcp equivalent exists
```

**Line 14 -- Remove `Any` import (if no longer needed):**
```python
# Before
from typing import TYPE_CHECKING, Any
# After -- check if Any is still used elsewhere in the file
from typing import TYPE_CHECKING
```
Note: `Any` is used in `items: list[dict[str, Any]]` for `add_tasks` and `edit_tasks` parameters, and in `dict[str, object]` return of `app_lifespan`. Check carefully before removing.

**Lines 115, 137, 150, 163, 180, 237 -- Context type simplification:**
```python
# Before
async def get_all(ctx: Context[Any, Any, Any]) -> AllEntities:
# After
async def get_all(ctx: Context) -> AllEntities:
```

**Lines 123, 142, 155, 168, 209, 277 -- Lifespan shorthand:**
```python
# Before
service: OperatorService = ctx.request_context.lifespan_context["service"]
# After
service: OperatorService = ctx.lifespan_context["service"]
```

**`Any` import analysis:**
- `items: list[dict[str, Any]]` in `add_tasks` (line 179) -- STILL NEEDS `Any`
- `items: list[dict[str, Any]]` in `edit_tasks` (line 236) -- STILL NEEDS `Any`
- `app_lifespan` return type `dict[str, object]` (line 67) -- does NOT use `Any`
- **Conclusion:** `Any` import stays because of `dict[str, Any]` in tool signatures

### __main__.py Changes

**Line 15 -- Add TODO for Phase 31:**
```python
# Before
# Log to file -- stdio_server() hijacks stderr, so file is the reliable path.
# After
# TODO(Phase 31): Redesign logging -- stderr is NOT hijacked (spike exp 03 proved
# the misdiagnosis). Phase 31 should add dual-handler (StreamHandler + FileHandler),
# proper namespace, the works. See CONTEXT.md deferred ideas.
```

### pyproject.toml Changes

**Line 8 -- Dependency swap:**
```python
# Before
dependencies = [
    "mcp>=1.26.0",
]
# After
dependencies = [
    "fastmcp>=3.1.1",
]
```

**Lines 28-31 -- Delete spike group:**
```python
# DELETE these 4 lines:
# Spike: FastMCP v3 migration exploration (see .research/deep-dives/fastmcp-spike/)
spike = [
    "fastmcp>=3",
]
```

### Progress Reporting Pattern

For `add_tasks` -- add after validation, report before processing each item:

```python
async def add_tasks(items: list[dict[str, Any]], ctx: Context) -> list[AddTaskResult]:
    log_tool_call("add_tasks", items=len(items))
    if len(items) != 1:
        msg = ADD_TASKS_BATCH_LIMIT.format(count=len(items))
        raise ValueError(msg)

    # ... validation ...

    total = len(items)
    results = []
    for i, spec in enumerate(validated_items):
        await ctx.report_progress(progress=i, total=total)
        result = await service.add_task(spec)
        results.append(result)
    await ctx.report_progress(progress=total, total=total)
    return results
```

Note: With current batch limit of 1, this reports 0/1 then 1/1. Still worth adding as scaffolding per D-05.

**Discretion recommendation:** Place `report_progress` AFTER validation (don't report progress on invalid input). Report 0/total before processing, total/total after. Keep it minimal -- no `log_tool_call` for progress events (the middleware in Phase 31 will handle logging).

### Anti-Patterns to Avoid

- **Don't remove `from mcp.types import ToolAnnotations`** -- fastmcp doesn't re-export it. Removing it breaks the code.
- **Don't use `Context[Any, Any, Any]`** -- FastMCP v3 Context is not generic; this raises TypeError.
- **Don't push progress into service layer** -- D-06 explicitly keeps `report_progress` at the MCP handler level.
- **Don't change test imports** -- Phase 30 handles test migration. Tests still use `from mcp.server.fastmcp import FastMCP` etc.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Progress reporting | Custom protocol messages | `ctx.report_progress()` | Built into FastMCP, no-ops when unsupported |
| Dependency version management | Manual pip installs | `uv sync` after pyproject.toml edit | uv handles resolution and lockfile |

## Common Pitfalls

### Pitfall 1: Forgetting ToolAnnotations stays at mcp.types
**What goes wrong:** Changing `from mcp.types import ToolAnnotations` to something that doesn't exist
**Why it happens:** D-09 says "no mcp.* imports if fastmcp provides an equivalent" -- but fastmcp DOESN'T provide one
**How to avoid:** Keep `from mcp.types import ToolAnnotations` unchanged. It's the one exception.
**Warning signs:** ImportError on `fastmcp.types.ToolAnnotations` or `fastmcp.ToolAnnotations`

### Pitfall 2: Context[Any, Any, Any] TypeError
**What goes wrong:** Keeping the old generic syntax causes TypeError at tool registration time
**Why it happens:** FastMCP v3 Context is a plain class, not Generic
**How to avoid:** Replace all `Context[Any, Any, Any]` with `Context`
**Warning signs:** `TypeError: 'type' object is not subscriptable` during import/registration

### Pitfall 3: Tests break because test imports aren't updated
**What goes wrong:** Tests still import from `mcp.server.fastmcp` but conftest/fixtures might be affected by the dependency change
**Why it happens:** Phase 29 changes the runtime dep; `mcp` becomes transitive instead of direct
**How to avoid:** `mcp` remains available as a transitive dependency of `fastmcp`. Tests should still pass with their existing `mcp.*` imports. Verify by running `uv run pytest` after the dependency swap.
**Warning signs:** ImportError in tests (unlikely since `mcp` is a transitive dep of `fastmcp`)

### Pitfall 4: Removing `Any` import prematurely
**What goes wrong:** `Any` is still needed for `dict[str, Any]` in tool parameter types
**Why it happens:** Removing `Context[Any, Any, Any]` makes it seem like `Any` is unused
**How to avoid:** Check all uses of `Any` in server.py before removing the import
**Warning signs:** mypy error `Name "Any" is not defined`

### Pitfall 5: uv sync / lockfile issues after dependency swap
**What goes wrong:** Lockfile gets out of sync or old `mcp` direct dep lingers
**Why it happens:** `uv sync` needs to resolve new dependency tree
**How to avoid:** Run `uv sync` after editing pyproject.toml, then run full test suite
**Warning signs:** Resolution errors or unexpected package versions

## Code Examples

### Import Block (after migration)

```python
# server.py imports (after Phase 29)
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from fastmcp import FastMCP, Context
from mcp.types import ToolAnnotations  # no fastmcp equivalent
from pydantic import ValidationError
```

### Tool Handler (after migration)

```python
@mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def get_all(ctx: Context) -> AllEntities:
    """Return the full OmniFocus database as structured data."""
    from omnifocus_operator.service import OperatorService

    service: OperatorService = ctx.lifespan_context["service"]
    log_tool_call("get_all")
    result = await service.get_all_data()
    logger.debug(
        "server.get_all: returning tasks=%d, projects=%d, tags=%d",
        len(result.tasks),
        len(result.projects),
        len(result.tags),
    )
    return result
```

### Progress Reporting (add_tasks pattern)

```python
# Source: spike experiment 06 adapted for add_tasks
total = len(items)  # currently always 1, but scaffolding for future
for i, item_dict in enumerate(items_to_process):
    await ctx.report_progress(progress=i, total=total)
    # ... process item ...
await ctx.report_progress(progress=total, total=total)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `from mcp.server.fastmcp import FastMCP` | `from fastmcp import FastMCP` | FastMCP v3 (2025) | Separate package, richer API |
| `Context[Any, Any, Any]` (generic) | `Context` (plain class) | FastMCP v3 | Simpler type annotations |
| `ctx.request_context.lifespan_context` | `ctx.lifespan_context` | FastMCP v3 | Convenience shortcut |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x + pytest-asyncio |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_server.py -x --no-cov` |
| Full suite command | `uv run pytest` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEP-01 | Server runs with fastmcp>=3.1.1 | integration | `uv run pytest tests/test_server.py -x --no-cov` | Yes |
| DEP-02 | No `mcp.server.fastmcp` imports in src/ | smoke | grep check (not a pytest test) | N/A |
| DEP-03 | `ctx.lifespan_context` shorthand used | code review | grep check (not a pytest test) | N/A |
| DEP-04 | pyproject.toml declares fastmcp>=3.1.1 | smoke | `grep 'fastmcp>=3.1.1' pyproject.toml` | N/A |
| PROG-01 | add_tasks reports progress | manual | No test -- ctx.report_progress no-ops in test client | N/A |
| PROG-02 | edit_tasks reports progress | manual | No test -- ctx.report_progress no-ops in test client | N/A |
| DOC-01 | README references fastmcp>=3.1.1 | smoke | `grep 'fastmcp>=3.1.1' README.md` | N/A |
| DOC-02 | Landing page references fastmcp>=3.1.1 | smoke | `grep 'fastmcp' docs/index.html` | N/A |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_server.py -x --no-cov`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green + grep verification for import/doc changes

### Wave 0 Gaps
None -- existing test infrastructure covers all phase requirements. The 697 existing tests validate that all 6 tools remain functional after the import migration. No new test files needed for Phase 29 (Phase 30 handles test client migration).

## Open Questions

1. **`Any` in lifespan return type**
   - What we know: `app_lifespan` returns `AsyncIterator[dict[str, object]]` -- uses `object`, not `Any`
   - What's unclear: Whether the return type annotation should change to be more specific (e.g., typed dict)
   - Recommendation: Leave as-is -- orthogonal to this phase

2. **filterwarnings for Pydantic UNSET**
   - What we know: `pyproject.toml` line 43-44 filters a pydantic warning about UNSET
   - What's unclear: Whether FastMCP v3's pydantic dependency changes affect this warning
   - Recommendation: Run tests after migration; if warning reappears, update the filter

## Sources

### Primary (HIGH confidence)
- FastMCP v3.1.0 installed in project venv -- programmatic verification of all APIs
- Spike experiment 01 (`01_server_and_context.py`) -- import migration reference
- Spike experiment 06 (`06_progress.py`) -- progress reporting reference
- Spike FINDINGS.md -- comprehensive migration assessment

### Secondary (MEDIUM confidence)
- PyPI package index -- fastmcp 3.1.1 is latest, mcp 1.26.0 is transitive dep

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- single dependency swap, version verified on PyPI
- Architecture: HIGH -- all changes verified via spike experiments + programmatic API checks
- Pitfalls: HIGH -- exhaustive testing of import paths, type annotations, and edge cases

**Research date:** 2026-03-26
**Valid until:** 2026-04-26 (stable -- fastmcp v3 API is settled)
