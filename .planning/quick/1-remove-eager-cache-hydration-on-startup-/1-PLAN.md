---
phase: quick-1
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/omnifocus_operator/repository/_repository.py
  - src/omnifocus_operator/server/_server.py
  - tests/test_repository.py
  - tests/test_server.py
autonomous: true
requirements: [LAZY-CACHE]

must_haves:
  truths:
    - "Server starts without calling OmniFocus bridge"
    - "First tool call lazily populates the cache via get_snapshot()"
    - "initialize() method no longer exists on OmniFocusRepository"
  artifacts:
    - path: "src/omnifocus_operator/repository/_repository.py"
      provides: "Repository without initialize() method"
      contains: "async def get_snapshot"
    - path: "src/omnifocus_operator/server/_server.py"
      provides: "Lifespan without pre-warm block"
  key_links:
    - from: "src/omnifocus_operator/server/_server.py"
      to: "OmniFocusRepository"
      via: "lifespan creates repo but does NOT call initialize()"
      pattern: "repository = OmniFocusRepository"
---

<objective>
Remove eager cache hydration on MCP server startup so the first tool call lazily populates the cache instead.

Purpose: Avoids blocking OmniFocus for ~3 seconds every time a new Claude session starts. The `get_snapshot()` method already handles a cold cache (`self._snapshot is None`), so no new lazy-loading logic is needed.
Output: Leaner server startup, removed dead code, updated tests.
</objective>

<execution_context>
@/Users/flo/.claude/get-shit-done/workflows/execute-plan.md
@/Users/flo/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/omnifocus_operator/repository/_repository.py
@src/omnifocus_operator/server/_server.py
@tests/test_repository.py
@tests/test_server.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Remove initialize() from repository and lifespan</name>
  <files>src/omnifocus_operator/repository/_repository.py, src/omnifocus_operator/server/_server.py</files>
  <action>
In `_repository.py`: Delete the `initialize()` method (lines 70-76). No other changes needed -- `get_snapshot()` already handles `self._snapshot is None`.

In `_server.py`: Delete the pre-warm block (lines 78-84):
```
    logger.info("Pre-warming repository cache...")
    try:
        await repository.initialize()
    except Exception:
        logger.exception("Failed to pre-warm repository cache")
        raise
    logger.info("Cache pre-warmed successfully")
```
No replacement log message needed. Update the docstring of `app_lifespan` to remove the "pre-warm" mention -- change to something like "Create the service stack and yield it for tool handlers."
  </action>
  <verify>
    <automated>cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && python -c "import ast; tree = ast.parse(open('src/omnifocus_operator/repository/_repository.py').read()); methods = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]; assert 'initialize' not in methods, f'initialize still present: {methods}'"</automated>
  </verify>
  <done>initialize() method deleted from OmniFocusRepository. Pre-warm block deleted from app_lifespan. Docstring updated.</done>
</task>

<task type="auto">
  <name>Task 2: Update tests -- remove SNAP-06, fix server test helpers</name>
  <files>tests/test_repository.py, tests/test_server.py</files>
  <action>
In `test_repository.py`:
- Delete the entire `TestSNAP06Initialize` class (lines ~207-228) -- the 2 tests (`test_initialize_populates_cache`, `test_get_snapshot_after_initialize_uses_cache`) are dead.
- Delete `test_initialize_failure_allows_retry` from `TestErrorPropagation` (lines ~307-319) -- replace with `test_failed_first_load_allows_retry` that calls `get_snapshot()` directly instead of `initialize()`. The behavior being tested (retry after failure) is still valid, just call `get_snapshot()` instead.

In `test_server.py`:
- In `_build_patched_server` (line 39): Replace `await repo.initialize()` with a bare `yield {"service": service}` -- no pre-warm call. The patched lifespan should just yield the service without calling initialize.
- Delete `test_sweep_called_before_cache_prewarm` entirely (lines ~449-511) -- this test specifically validates sweep-before-initialize ordering which no longer applies. The sweep itself is still tested by `test_sweep_called_for_ipc_bridge` (which remains).

IMPORTANT: `session.initialize()` calls in `test_simulator_integration.py` and `test_simulator_bridge.py` are MCP ClientSession initialization -- do NOT touch those.
  </action>
  <verify>
    <automated>cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && uv run pytest tests/test_repository.py tests/test_server.py -x -q 2>&1 | tail -5</automated>
  </verify>
  <done>All tests pass. No references to `repository.initialize()` remain in tests. SNAP-06 test class removed. Server helper no longer calls initialize. Sweep ordering test removed.</done>
</task>

</tasks>

<verification>
```bash
# Full test suite passes
uv run pytest -x -q

# No remaining references to repository initialize() (excluding MCP session.initialize())
grep -rn "repository.*initialize\|repo\.initialize\|await.*initialize()" src/ tests/ | grep -v "session.initialize" | grep -v "__pycache__"

# Ruff + mypy pass
uv run ruff check src/ tests/
uv run mypy src/
```
</verification>

<success_criteria>
- `initialize()` method does not exist on `OmniFocusRepository`
- Server lifespan creates repo without calling any pre-warm method
- All tests pass (no references to deleted method)
- First tool call triggers lazy cache population via existing `get_snapshot()` cold-cache path
</success_criteria>

<output>
After completion, create `.planning/quick/1-remove-eager-cache-hydration-on-startup-/1-SUMMARY.md`
</output>
