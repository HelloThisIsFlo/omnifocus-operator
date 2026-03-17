# Phase 19: InMemoryBridge Export Cleanup - Research

**Researched:** 2026-03-17
**Domain:** Python package exports, import paths, factory pattern cleanup
**Confidence:** HIGH

## Summary

This is a straightforward refactoring phase: remove test doubles from production package `__init__.py` exports and `__all__` lists, delete the `"inmemory"` factory case, and migrate all test imports to direct module paths. No new libraries, no architectural decisions -- purely mechanical removal and import rewriting.

The codebase is well-structured with explicit `__all__` lists and `match/case` factory patterns, making the changes predictable. The main risk is missing an import site, which the test suite (534+ tests) will catch immediately.

**Primary recommendation:** Do exports-first (remove from `__init__.py` and factory), then fix all broken imports in tests. The test suite is the verification -- if all 534+ tests pass, the migration is complete.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Cleanup scope**: Comprehensive -- remove ALL test doubles from production exports, not just InMemoryBridge
  - Bridge package (`bridge/__init__.py`): Remove `InMemoryBridge`, `BridgeCall`, `ConstantMtimeSource`
  - Repository package (`repository/__init__.py`): Remove `InMemoryRepository`
  - InMemoryBridge was never meant to be user-facing -- it was a misunderstanding that it got exported
- **Factory removal**: Remove `"inmemory"` case entirely from `bridge/factory.py` -- as if it was never there
  - No educational deprecation message -- no backward compatibility needed
  - Update catch-all error to list only remaining valid types: `simulator`, `real`
  - Update `repository/factory.py` line 102: change `bridge_type in ("inmemory", "simulator")` to just `bridge_type == "simulator"`
- **Import migration**: All test files update to direct module imports:
  - `from omnifocus_operator.bridge.in_memory import InMemoryBridge, BridgeCall`
  - `from omnifocus_operator.bridge.mtime import ConstantMtimeSource`
  - `from omnifocus_operator.repository.in_memory import InMemoryRepository`
  - Update docstrings in `repository/__init__.py` and `service.py` that mention InMemoryRepository

### Claude's Discretion
- Order of operations (imports first vs exports first vs single commit)
- Whether to update `__all__` in submodules (`in_memory.py`, `mtime.py`)
- Docstring wording updates

### Deferred Ideas (OUT OF SCOPE)
- **SimulatorBridge export cleanup** -- same pattern, deferred to Phase 23
- **OMNIFOCUS_BRIDGE env var removal** -- bundle with SimulatorBridge cleanup in Phase 23
- **Factory simplification/removal** -- evaluate during Phase 23
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFRA-01 | InMemoryBridge not importable from `omnifocus_operator.bridge` | Remove from `bridge/__init__.py` imports and `__all__` list (lines 10, 29, 34, 36) |
| INFRA-02 | Tests import InMemoryBridge via direct module path only | Migrate 5 test files from package imports to `bridge.in_memory` / `bridge.mtime` / `repository.in_memory` |
| INFRA-03 | `"inmemory"` option removed from bridge/repository factory | Delete `case "inmemory"` (lines 40-136 in factory.py), update error message (line 170), update repo factory condition (line 102) |
</phase_requirements>

## Architecture Patterns

### What Gets Removed

**`bridge/__init__.py`** (3 symbols):
- Line 10: `from omnifocus_operator.bridge.in_memory import BridgeCall, InMemoryBridge` -- delete
- Lines 11-12: `ConstantMtimeSource` import -- remove from this import (keep `FileMtimeSource`, `MtimeSource`)
- `__all__` list: Remove `"BridgeCall"` (line 29), `"ConstantMtimeSource"` (line 34), `"InMemoryBridge"` (line 36)

**`repository/__init__.py`** (1 symbol):
- Line 14: `from omnifocus_operator.repository.in_memory import InMemoryRepository` -- delete
- `__all__` list: Remove `"InMemoryRepository"` (line 20)
- Module docstring: Remove mention of InMemoryRepository

**`bridge/factory.py`** (97 lines deleted):
- Line 13: `from omnifocus_operator.bridge.in_memory import InMemoryBridge` -- delete (no longer needed)
- Lines 40-136: Entire `case "inmemory"` block (94 lines of inline sample data) -- delete
- Line 153: Update PYTEST safety check error message -- remove `"inmemory"` mention
- Line 170: Change `"Use: inmemory, simulator, real"` to `"Use: simulator, real"`
- Docstring line 27: Remove `"inmemory"` from parameter docs

**`repository/factory.py`** (1 line changed):
- Line 102: `bridge_type in ("inmemory", "simulator")` -> `bridge_type == "simulator"`

### What Gets Updated (Docstrings)

**`service.py`** line 68:
- Change `(e.g. ``BridgeRepository``, ``InMemoryRepository``)` to `(e.g. ``BridgeRepository``, ``HybridRepository``)`

**`repository/__init__.py`** docstring:
- Remove `InMemoryRepository (testing implementation returning pre-built snapshots)` mention

### Import Migration Map

Complete inventory of test files needing changes:

| File | Current Import | New Import |
|------|---------------|------------|
| `tests/test_service.py:19` | `from omnifocus_operator.bridge import BridgeError, InMemoryBridge, create_bridge` | Split: keep `BridgeError, create_bridge` from bridge, add `from omnifocus_operator.bridge.in_memory import InMemoryBridge` |
| `tests/test_service.py:21` | `from omnifocus_operator.repository import InMemoryRepository` | `from omnifocus_operator.repository.in_memory import InMemoryRepository` |
| `tests/test_bridge.py:7-15` | `from omnifocus_operator.bridge import (Bridge, BridgeCall, ..., InMemoryBridge)` | Split: keep production symbols from bridge, add `from omnifocus_operator.bridge.in_memory import BridgeCall, InMemoryBridge` |
| `tests/test_repository.py:20` | `from omnifocus_operator.repository import BridgeRepository, InMemoryRepository, Repository` | Split: keep `BridgeRepository, Repository` from repository, add `from omnifocus_operator.repository.in_memory import InMemoryRepository` |
| `tests/test_server.py:531` | `from omnifocus_operator.repository import InMemoryRepository` (local) | `from omnifocus_operator.repository.in_memory import InMemoryRepository` |
| `tests/test_server.py:666` | `from omnifocus_operator.repository import InMemoryRepository` (local) | `from omnifocus_operator.repository.in_memory import InMemoryRepository` |
| `tests/test_server.py:921` | `from omnifocus_operator.repository import InMemoryRepository` (local) | `from omnifocus_operator.repository.in_memory import InMemoryRepository` |
| `tests/test_server.py:1293` | `from omnifocus_operator.repository import InMemoryRepository` (local) | `from omnifocus_operator.repository.in_memory import InMemoryRepository` |

**Already correct** (no changes needed):
- `tests/test_hybrid_repository.py:23` -- already uses `from omnifocus_operator.bridge.in_memory import InMemoryBridge`
- `tests/test_repository.py:18` -- already uses `from omnifocus_operator.bridge.in_memory import InMemoryBridge`
- `tests/test_server.py:187` -- already uses `from omnifocus_operator.bridge.in_memory import InMemoryBridge` (local)

### Factory Test Changes

**`tests/test_service.py:1896-1899`** -- `TestCreateBridge.test_inmemory_returns_inmemory_bridge`:
- This test calls `create_bridge("inmemory")` and asserts it returns `InMemoryBridge`
- Must be **deleted entirely** -- the factory no longer supports `"inmemory"`

### Server Tests Using `OMNIFOCUS_BRIDGE=inmemory`

9 test methods in `test_server.py` set `monkeypatch.setenv("OMNIFOCUS_BRIDGE", "inmemory")`:
- Lines 92, 119, 166, 185, 252, 270, 297, 314, 388

These all go through `create_server()` -> `create_repository()` -> `create_bridge("inmemory")`.

**Solution:** Change `"inmemory"` to `"simulator"` in all 9 monkeypatch calls. SimulatorBridge is the remaining test-suitable factory option. The tests need a bridge that works without real OmniFocus -- SimulatorBridge serves this purpose.

**Important:** The SimulatorBridge constructor needs an IPC directory. The factory already handles this via `OMNIFOCUS_IPC_DIR` env var or defaults. Tests using `monkeypatch` may need to also set `OMNIFOCUS_IPC_DIR` to a `tmp_path` or similar. Check whether existing tests already handle this.

**Alternative:** These tests could be refactored to bypass the factory entirely (instantiate InMemoryBridge directly + inject into repository), but that changes test structure more than needed for this phase. The `"simulator"` swap is simpler and preserves the existing end-to-end-through-factory pattern.

### ConstantMtimeSource: Keep in bridge exports?

`ConstantMtimeSource` is being removed from `bridge/__init__.py` exports per the locked decision. However, it is NOT exclusively a test double -- it's a legitimate `MtimeSource` implementation used with SimulatorBridge in the repository factory (line 103). The locked decision says to remove it, so remove it. The `bridge/mtime.py` submodule still exports it via its own `__all__`, and `repository/factory.py` already imports from `omnifocus_operator.bridge.mtime` directly (line 95).

**No functional breakage** from removing it from the parent package `__all__`.

### Submodule `__all__` Lists (Discretion Area)

Both `bridge/in_memory.py` and `bridge/mtime.py` have their own `__all__` lists. These are fine as-is:
- `bridge/in_memory.py` has no explicit `__all__` (doesn't need one -- it's a leaf module)
- `bridge/mtime.py` has `__all__ = ["ConstantMtimeSource", "FileMtimeSource", "MtimeSource"]` -- correct, keep as-is
- `repository/in_memory.py` has `__all__ = ["InMemoryRepository"]` -- correct, keep as-is

**Recommendation:** No changes to submodule `__all__` lists. They correctly define what each module exports for star-imports, independent of the parent package re-exports.

## Common Pitfalls

### Pitfall 1: Missing an import site
**What goes wrong:** A test file still imports from the package path and fails at import time
**Why it happens:** grep misses a dynamic or conditional import
**How to avoid:** Run full test suite after changes. The 534+ tests cover all code paths.
**Warning signs:** `ImportError` on test collection

### Pitfall 2: Factory error message still mentions "inmemory"
**What goes wrong:** The catch-all error or PYTEST guard still references `"inmemory"` as a valid option
**How to avoid:** Search for string literal `"inmemory"` in `factory.py` after deletion
**Warning signs:** Error message suggests using a removed option

### Pitfall 3: `OMNIFOCUS_BRIDGE=inmemory` env var in test_server.py
**What goes wrong:** 9 test methods set this env var and fail because the factory no longer handles `"inmemory"`
**How to avoid:** Change all 9 to `"simulator"` and ensure SimulatorBridge setup works
**Warning signs:** `ValueError: Unknown bridge type: 'inmemory'` during test collection

### Pitfall 4: Circular import after removing re-exports
**What goes wrong:** Some module was relying on the `__init__.py` re-export to break a circular dependency
**Why it happens:** Python resolves circular imports via partially-initialized module objects; removing a re-export changes resolution order
**How to avoid:** Verify no production code imports test doubles from package path (confirmed: none do, all references are in tests)
**Warning signs:** `ImportError` or `AttributeError` during import

### Pitfall 5: ConstantMtimeSource in repository/factory.py
**What goes wrong:** The `_create_bridge_repository()` function (line 95) imports `ConstantMtimeSource` from `omnifocus_operator.bridge.mtime` directly -- this is already correct. But line 102 checks `bridge_type in ("inmemory", "simulator")` to decide whether to use it.
**How to avoid:** Change the condition to `bridge_type == "simulator"` as specified in the locked decision
**Warning signs:** ConstantMtimeSource used when it shouldn't be, or not used when it should be

## Don't Hand-Roll

Not applicable -- this phase is pure removal/migration with no new code to write.

## Code Examples

### bridge/__init__.py After Cleanup

```python
"""OmniFocus bridge protocol, implementations, and factory."""

from omnifocus_operator.bridge.errors import (
    BridgeConnectionError,
    BridgeError,
    BridgeProtocolError,
    BridgeTimeoutError,
)
from omnifocus_operator.bridge.factory import create_bridge
from omnifocus_operator.bridge.mtime import (
    FileMtimeSource,
    MtimeSource,
)
from omnifocus_operator.bridge.protocol import Bridge
from omnifocus_operator.bridge.real import (
    DEFAULT_OFOCUS_PATH,
    OMNIFOCUS_CONTAINER,
    RealBridge,
    sweep_orphaned_files,
)
from omnifocus_operator.bridge.simulator import SimulatorBridge

__all__ = [
    "DEFAULT_OFOCUS_PATH",
    "OMNIFOCUS_CONTAINER",
    "Bridge",
    "BridgeConnectionError",
    "BridgeError",
    "BridgeProtocolError",
    "BridgeTimeoutError",
    "FileMtimeSource",
    "MtimeSource",
    "RealBridge",
    "SimulatorBridge",
    "create_bridge",
    "sweep_orphaned_files",
]
```

### repository/__init__.py After Cleanup

```python
"""Repository package -- protocol and implementations for OmniFocus data access.

Provides the ``Repository`` protocol abstraction, ``BridgeRepository`` (production
implementation wrapping Bridge + MtimeSource + adapter with caching), and
``HybridRepository`` (SQLite-based reader for fast ~46ms reads).

MtimeSource classes live in ``omnifocus_operator.bridge.mtime``.
"""

from omnifocus_operator.repository.bridge import BridgeRepository
from omnifocus_operator.repository.factory import create_repository
from omnifocus_operator.repository.hybrid import HybridRepository
from omnifocus_operator.repository.protocol import Repository

__all__ = [
    "BridgeRepository",
    "HybridRepository",
    "Repository",
    "create_repository",
]
```

### Test Import Migration Pattern

```python
# BEFORE (package-level import -- will break)
from omnifocus_operator.bridge import BridgeError, InMemoryBridge, create_bridge
from omnifocus_operator.repository import InMemoryRepository

# AFTER (direct module imports for test doubles, package for production)
from omnifocus_operator.bridge import BridgeError, create_bridge
from omnifocus_operator.bridge.in_memory import InMemoryBridge
from omnifocus_operator.repository.in_memory import InMemoryRepository
```

### Factory Catch-All Error After Cleanup

```python
case _:
    msg = f"Unknown bridge type: {bridge_type!r}. Use: simulator, real"
    raise ValueError(msg)
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2+ with pytest-asyncio |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/ -x --no-header -q` |
| Full suite command | `uv run pytest tests/ --no-header -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | `from omnifocus_operator.bridge import InMemoryBridge` raises ImportError | unit | `uv run pytest tests/test_bridge.py -x -q --no-header -k "import"` | No -- Wave 0 |
| INFRA-02 | All tests using InMemoryBridge import from direct module path | meta/grep | `grep -rn "from omnifocus_operator.bridge import.*InMemoryBridge" tests/` (must return empty) | N/A -- grep check |
| INFRA-03 | `create_bridge("inmemory")` raises ValueError | unit | `uv run pytest tests/test_service.py -x -q --no-header -k "unknown_raises"` | Partial (existing test covers unknown types, but "inmemory" test must be deleted/repurposed) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x --no-header -q`
- **Per wave merge:** `uv run pytest tests/ --no-header -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] Verification test: `from omnifocus_operator.bridge import InMemoryBridge` raises ImportError -- could be a simple test, or verified by grep
- [ ] Verification test: `create_bridge("inmemory")` raises ValueError (the existing `test_inmemory_returns_inmemory_bridge` must be replaced with this)
- [ ] Verification: grep for remaining `"inmemory"` string literals in `src/` (should find none except comments)

**Note:** The primary verification is the existing 534+ test suite passing. The import-level checks above are secondary confirmations. If all tests pass after the migration, INFRA-01/02/03 are satisfied by definition.

## Open Questions

1. **SimulatorBridge in test_server.py factory tests**
   - What we know: 9 tests use `OMNIFOCUS_BRIDGE=inmemory` via `create_server()` factory path
   - What's unclear: Whether SimulatorBridge requires IPC directory setup in these tests, or if the default path is acceptable (tests may not actually exercise the bridge)
   - Recommendation: Try `"simulator"` swap first. If IPC dir issues arise, add `monkeypatch.setenv("OMNIFOCUS_IPC_DIR", str(tmp_path))`. If that's too invasive, refactor these tests to bypass the factory and inject directly.

## Sources

### Primary (HIGH confidence)
- Direct code inspection of all files in scope:
  - `src/omnifocus_operator/bridge/__init__.py` -- current exports
  - `src/omnifocus_operator/bridge/factory.py` -- factory with "inmemory" case
  - `src/omnifocus_operator/bridge/in_memory.py` -- InMemoryBridge definition
  - `src/omnifocus_operator/bridge/mtime.py` -- ConstantMtimeSource definition
  - `src/omnifocus_operator/repository/__init__.py` -- current exports
  - `src/omnifocus_operator/repository/factory.py` -- bridge_type condition
  - `src/omnifocus_operator/repository/in_memory.py` -- InMemoryRepository definition
  - `src/omnifocus_operator/service.py` -- docstring mentioning InMemoryRepository
  - All test files: `tests/test_bridge.py`, `tests/test_service.py`, `tests/test_repository.py`, `tests/test_server.py`, `tests/test_hybrid_repository.py`

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, pure refactoring
- Architecture: HIGH -- all files inspected, complete inventory of changes
- Pitfalls: HIGH -- well-understood domain (Python imports), all edge cases catalogued

**Research date:** 2026-03-17
**Valid until:** No expiry -- this is codebase-specific structural knowledge, not library-dependent
