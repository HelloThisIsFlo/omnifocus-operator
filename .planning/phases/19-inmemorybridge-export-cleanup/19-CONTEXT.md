# Phase 19: InMemoryBridge Export Cleanup - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove all test doubles from production package exports so they're not importable as if they're production code. Clean break — no backward compatibility, no migration messages. After this phase, test doubles are only available via direct module imports.

Scope: InMemoryBridge (+ BridgeCall, ConstantMtimeSource) from bridge package, InMemoryRepository from repository package, and "inmemory" factory option. SimulatorBridge and OMNIFOCUS_BRIDGE env var cleanup are explicitly deferred to Phase 22.

</domain>

<decisions>
## Implementation Decisions

### Cleanup scope
- **Comprehensive**: Remove ALL test doubles from production exports, not just InMemoryBridge
- Bridge package (`bridge/__init__.py`): Remove `InMemoryBridge`, `BridgeCall`, `ConstantMtimeSource`
- Repository package (`repository/__init__.py`): Remove `InMemoryRepository`
- InMemoryBridge was never meant to be user-facing — it was a misunderstanding that it got exported

### Factory removal
- Remove `"inmemory"` case entirely from `bridge/factory.py` — as if it was never there
- No educational deprecation message — no backward compatibility needed
- Update catch-all error to list only remaining valid types: `simulator`, `real`
- Update `repository/factory.py` line 102: change `bridge_type in ("inmemory", "simulator")` to just `bridge_type == "simulator"`

### Import migration
- All test files update to direct module imports:
  - `from omnifocus_operator.bridge.in_memory import InMemoryBridge, BridgeCall`
  - `from omnifocus_operator.bridge.mtime import ConstantMtimeSource`
  - `from omnifocus_operator.repository.in_memory import InMemoryRepository`
- Update docstrings in `repository/__init__.py` and `service.py` that mention InMemoryRepository

### Claude's Discretion
- Order of operations (imports first vs exports first vs single commit)
- Whether to update `__all__` in submodules (`in_memory.py`, `mtime.py`)
- Docstring wording updates

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Bridge package exports
- `src/omnifocus_operator/bridge/__init__.py` — Current exports including InMemoryBridge, BridgeCall, ConstantMtimeSource (lines 10, 12, 34-36)
- `src/omnifocus_operator/bridge/in_memory.py` — InMemoryBridge and BridgeCall definitions
- `src/omnifocus_operator/bridge/mtime.py` — ConstantMtimeSource definition (lines 55+, designed for InMemoryBridge)

### Bridge factory
- `src/omnifocus_operator/bridge/factory.py` — "inmemory" case (lines 40-136) and catch-all error (line 170)

### Repository package exports
- `src/omnifocus_operator/repository/__init__.py` — InMemoryRepository export (lines 6, 14, 20)
- `src/omnifocus_operator/repository/in_memory.py` — InMemoryRepository definition
- `src/omnifocus_operator/repository/factory.py` — bridge_type check at line 102 (`"inmemory"` in condition)

### Test files to migrate
- `tests/test_service.py:19` — `from omnifocus_operator.bridge import BridgeError, InMemoryBridge, create_bridge`
- `tests/test_service.py:21` — `from omnifocus_operator.repository import InMemoryRepository`
- `tests/test_bridge.py:7` — `from omnifocus_operator.bridge import (... InMemoryBridge ...)`
- `tests/test_repository.py:20` — `from omnifocus_operator.repository import BridgeRepository, InMemoryRepository, Repository`
- `tests/test_server.py:531,666,921,1293` — `from omnifocus_operator.repository import InMemoryRepository`
- `tests/test_hybrid_repository.py` — uses InMemoryBridge (check exact import)

### Docstrings to update
- `src/omnifocus_operator/service.py:68` — mentions InMemoryRepository

### Requirements
- `.planning/REQUIREMENTS.md` — INFRA-01, INFRA-02, INFRA-03 definitions (InMemoryRepository cleanup extends beyond explicit requirements)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None specific — this is a removal/migration phase

### Established Patterns
- Package `__init__.py` files use explicit `__all__` lists — remove entries from both import and `__all__`
- Test files use package-level imports (`from omnifocus_operator.bridge import ...`) — migrate to module-level
- Factory uses `match/case` — remove the `"inmemory"` case branch

### Integration Points
- `bridge/factory.py` "inmemory" case (lines 40-136) — 94 lines of inline sample data that get deleted
- `repository/factory.py` line 102 — `bridge_type in ("inmemory", "simulator")` condition for ConstantMtimeSource
- `bridge/factory.py` line 153 — PYTEST safety check error message mentions "inmemory" (update text)
- `bridge/factory.py` line 170 — catch-all error lists "inmemory" as valid type (update text)

</code_context>

<specifics>
## Specific Ideas

- "InMemoryBridge was never meant to be user-facing — it was a misunderstanding"
- "It should be as if it was never exposed to a user. There is no backward compatibility needed."
- InMemoryRepository has the same pattern but is cleaner to remove — no factory route, just exports

</specifics>

<deferred>
## Deferred Ideas

- **SimulatorBridge export cleanup** — same pattern, but cascades into factory simplification. Deferred to Phase 22 (Service Decomposition) to avoid half-and-half cleanup.
- **OMNIFOCUS_BRIDGE env var removal** — once SimulatorBridge is also removed from factory, the env var becomes pointless. Bundle with SimulatorBridge cleanup in Phase 22.
- **Factory simplification/removal** — with only "real" remaining, the factory becomes trivial. Evaluate during Phase 22.

</deferred>

---

*Phase: 19-inmemorybridge-export-cleanup*
*Context gathered: 2026-03-17*
