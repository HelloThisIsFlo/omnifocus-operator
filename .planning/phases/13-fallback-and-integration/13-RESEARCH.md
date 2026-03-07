# Phase 13: Fallback and Integration - Research

**Researched:** 2026-03-07
**Domain:** Repository factory, error-serving mode, env-var-driven read path selection
**Confidence:** HIGH

## Summary

Phase 13 is a wiring/integration phase -- no new data logic, no new protocols. The work is:
1. A `create_repository()` factory that reads `OMNIFOCUS_REPOSITORY` env var and returns either `HybridRepository` (default) or `BridgeRepository`
2. Restructuring `server.py` lifespan to call the factory instead of inline bridge setup
3. Error-serving mode when SQLite DB not found (reusing existing `ErrorOperatorService`)
4. Documentation updates to `configuration.md`

All building blocks exist. The factory pattern is proven (`create_bridge` in `bridge/factory.py`). `ErrorOperatorService` already handles degraded mode. Both `HybridRepository` and `BridgeRepository` satisfy the `Repository` protocol. This is assembly, not invention.

**Primary recommendation:** Follow the `create_bridge()` factory pattern exactly. Keep the factory in `repository/__init__.py` or a new `repository/factory.py`. The lifespan becomes: factory call -> OperatorService -> yield, with try/except for ErrorOperatorService.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Error message distinguishes **fix** (find correct SQLite path, set `OMNIFOCUS_SQLITE_PATH`) vs **workaround** (set `OMNIFOCUS_REPOSITORY=bridge`)
- Show the expected path that was checked; no reason detection
- `ErrorOperatorService` reused for SQLite-not-found (consistent with Phase 9 design)
- No automatic bridge failover (explicitly out of scope)
- Bridge mode maps ambiguous tasks to `available` -- no `blocked`
- No model pollution (no metadata fields or caveats in response data)
- Startup log warning when running in bridge mode
- Documentation handles the bridge caveat (not runtime data)
- Bridge fallback is temporary workaround (1-2 days), not permanent mode
- Repository factory function in `repository/__init__.py`: `create_repository(repo_type)` reads `OMNIFOCUS_REPOSITORY`
- Factory returns `HybridRepository` (default/sqlite) or `BridgeRepository` (bridge fallback)
- Factory encapsulates bridge-repository-specific setup: MtimeSource, ofocus path validation
- Factory raises on SQLite not found -- caught by lifespan's try/except
- IPC orphan sweep stays in server lifespan (bridge-level, not bridge-repository-level)
- IPC sweep always runs regardless of `OMNIFOCUS_REPOSITORY` setting

### Claude's Discretion
- Repository factory implementation details (error message exact wording)
- How to restructure existing bridge setup code when extracting to factory
- Test strategy for the new factory and error-serving paths
- Configuration.md updates for degraded mode documentation

### Deferred Ideas (OUT OF SCOPE)
- Writes through HybridRepository (future milestone)
- HybridRepository rename (current name intentional)

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FALL-01 | `OMNIFOCUS_REPOSITORY=bridge` switches read path from SQLite to OmniJS bridge | Repository factory pattern; env var routing; BridgeRepository already satisfies Repository protocol |
| FALL-02 | Bridge fallback: urgency fully populated, availability reduced to available/completed/dropped (no blocked) | Already handled by bridge adapter (`adapt_snapshot`); no new code needed -- just verify via test |
| FALL-03 | SQLite not found -> error-serving mode with actionable message | `ErrorOperatorService` already exists; factory raises `FileNotFoundError` with path + instructions |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `os` | 3.12 | Env var reading, path existence checks | Already used everywhere |
| `ErrorOperatorService` | existing | Degraded mode on startup failure | Proven in Phase 9; tested in `test_server.py` |
| `Repository` protocol | existing | Structural typing for both repos | ARCH-01 complete |

### Supporting
No new dependencies. Everything is stdlib + existing code.

## Architecture Patterns

### Current Lifespan (to be restructured)
```
server.py::app_lifespan
├── create_bridge(bridge_type)          # from OMNIFOCUS_BRIDGE
├── sweep_orphaned_files(bridge.ipc_dir)
├── MtimeSource selection (Constant vs File)
├── ofocus_path validation              # FileNotFoundError
├── BridgeRepository(bridge, mtime_source)
├── OperatorService(repository)
└── yield {"service": service}
    └── except -> ErrorOperatorService
```

### Target Lifespan (after Phase 13)
```
server.py::app_lifespan
├── sweep_orphaned_files()              # IPC sweep, always runs
├── create_repository(repo_type)        # NEW: from OMNIFOCUS_REPOSITORY
│   ├── "sqlite" (default) -> HybridRepository
│   │   └── raises FileNotFoundError if DB missing
│   └── "bridge" -> BridgeRepository
│       ├── create_bridge(bridge_type)
│       ├── MtimeSource selection
│       └── ofocus_path validation
├── OperatorService(repository)
└── yield {"service": service}
    └── except -> ErrorOperatorService
```

### Pattern: Repository Factory
**What:** `create_repository()` mirrors `create_bridge()` -- match statement on string type, encapsulates all setup
**Key detail:** Factory owns bridge-repository-specific setup (MtimeSource, ofocus path). The lifespan just calls factory + wraps in OperatorService.

```python
# repository/factory.py (or in __init__.py per user decision)
def create_repository(repo_type: str) -> Repository:
    match repo_type:
        case "sqlite" | "hybrid":
            db_path = os.environ.get("OMNIFOCUS_SQLITE_PATH", _DEFAULT_DB_PATH)
            if not os.path.exists(db_path):
                raise FileNotFoundError(
                    f"OmniFocus SQLite database not found at:\n"
                    f"  {db_path}\n\n"
                    f"To fix: ...\n"
                    f"As a workaround: ..."
                )
            return HybridRepository(db_path=Path(db_path))
        case "bridge":
            # Move all bridge setup from current lifespan here
            bridge = create_bridge(bridge_type)
            mtime_source = _create_mtime_source(bridge_type)
            return BridgeRepository(bridge=bridge, mtime_source=mtime_source)
        case _:
            raise ValueError(f"Unknown repository type: {repo_type!r}")
```

### Pattern: Error Message Structure
**What:** Actionable error with fix vs workaround distinction
```
OmniFocus SQLite database not found at:
  /path/that/was/checked

To fix this:
  Set OMNIFOCUS_SQLITE_PATH to the correct database location.

As a temporary workaround:
  Set OMNIFOCUS_REPOSITORY=bridge to use the OmniJS bridge (slower, no 'blocked' availability).
```

### Anti-Patterns to Avoid
- **Automatic failover:** User decided against this. If SQLite missing, error -- don't silently fall back to bridge
- **Model pollution:** Don't add `is_degraded` or `mode` fields to response data
- **Bridge setup duplication:** Extract bridge setup to factory, don't duplicate the MtimeSource/ofocus logic

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Degraded mode | New error-serving mechanism | `ErrorOperatorService` | Already tested, intercepts all attribute access |
| Repository switching | If/elif in lifespan | Factory function | Proven pattern from `create_bridge()` |
| Bridge availability mapping | New adapter logic | Existing `adapt_snapshot` | Already maps to available/completed/dropped |

## Common Pitfalls

### Pitfall 1: IPC Sweep Scope
**What goes wrong:** Moving IPC sweep into the repository factory (it's bridge-level, not bridge-repository-level)
**Why it happens:** IPC sweep looks related to bridge setup
**How to avoid:** IPC sweep stays in server lifespan. It runs always (future-proofing for HybridRepository writes). Factory only handles read-path concerns.
**Warning signs:** IPC sweep only runs when `OMNIFOCUS_REPOSITORY=bridge`

### Pitfall 2: Bridge Type vs Repository Type
**What goes wrong:** Confusing `OMNIFOCUS_BRIDGE` (which bridge impl) with `OMNIFOCUS_REPOSITORY` (which read path)
**How to avoid:** Repository factory reads `OMNIFOCUS_REPOSITORY`. Only when repo_type="bridge" does it also read `OMNIFOCUS_BRIDGE` to select bridge implementation.

### Pitfall 3: HybridRepository Already Handles Missing DB
**What goes wrong:** Adding path-existence check inside HybridRepository when it should be in the factory
**Why it happens:** Seems natural to validate in the repository
**How to avoid:** Factory validates path existence and raises with actionable error. HybridRepository just takes a path and uses it (sqlite3 will fail if path is wrong, but the factory error is friendlier).

### Pitfall 4: Forgetting Bridge Mode Startup Warning
**What goes wrong:** No indication in logs that bridge mode is active
**How to avoid:** Factory or lifespan logs `logger.warning("Running in bridge fallback mode -- availability data is degraded (no 'blocked' status)")` when `OMNIFOCUS_REPOSITORY=bridge`

### Pitfall 5: Test Isolation
**What goes wrong:** Tests set `OMNIFOCUS_REPOSITORY` env var and it leaks
**How to avoid:** Use `monkeypatch.setenv` in tests (automatically cleaned up by pytest)

## Code Examples

### Existing ErrorOperatorService Pattern
```python
# From service.py -- reuse as-is
class ErrorOperatorService(OperatorService):
    def __init__(self, error: Exception) -> None:
        object.__setattr__(self, "_error_message",
            f"OmniFocus Operator failed to start:\n\n{error!s}\n\nRestart the server after fixing.")
    def __getattr__(self, name: str) -> NoReturn:
        raise RuntimeError(self._error_message)
```

### Existing Factory Pattern to Follow
```python
# From bridge/factory.py -- same structure for repository factory
def create_bridge(bridge_type: str) -> Bridge:
    match bridge_type:
        case "inmemory": ...
        case "simulator": ...
        case "real": ...
        case _: raise ValueError(...)
```

### Current Lifespan (what gets restructured)
```python
# From server.py -- lines 34-91
# The bridge setup block (lines 49-79) moves into create_repository("bridge")
# The try/except + ErrorOperatorService stays in lifespan
```

### FALL-02 Already Handled
```python
# Bridge adapter already maps availability correctly:
# - Tasks without explicit completion/drop -> "available" (not "blocked")
# - OmniJS doesn't expose sequential/dependency info
# - No new code needed, just verify via test
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| All reads through bridge (~2-5s) | SQLite primary read (~46ms) | Phase 12 | 50x faster reads |
| Inline bridge setup in lifespan | Repository factory (this phase) | Phase 13 | Clean separation |
| Single read path | Switchable via env var | Phase 13 | Graceful degradation |

## Open Questions

1. **Factory location: `repository/__init__.py` vs `repository/factory.py`**
   - CONTEXT.md says `repository/__init__.py`
   - But `create_bridge` lives in `bridge/factory.py` (separate file)
   - Recommendation: Follow `create_bridge` pattern -- use `repository/factory.py` for consistency. Re-export from `__init__.py`.

2. **IPC sweep when no bridge is active**
   - CONTEXT.md says "always runs" and "no-op if no IPC dir exists"
   - Current code checks `hasattr(bridge, "ipc_dir")` -- without a bridge object, sweep needs a default IPC dir
   - Recommendation: Import `DEFAULT_IPC_DIR` and sweep it directly. `sweep_orphaned_files` already handles missing dirs gracefully.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (via uv) |
| Config file | `pyproject.toml` |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FALL-01 | `OMNIFOCUS_REPOSITORY=bridge` routes to BridgeRepository | unit | `uv run pytest tests/test_repository_factory.py -x -q` | No -- Wave 0 |
| FALL-01 | `OMNIFOCUS_REPOSITORY=sqlite` (default) routes to HybridRepository | unit | `uv run pytest tests/test_repository_factory.py -x -q` | No -- Wave 0 |
| FALL-02 | Bridge mode: urgency populated, availability reduced (no blocked) | unit | `uv run pytest tests/test_adapter.py -x -q` | Partial -- adapter tests exist, need bridge-mode-specific assertion |
| FALL-03 | SQLite not found -> error-serving mode with actionable message | unit | `uv run pytest tests/test_repository_factory.py -x -q` | No -- Wave 0 |
| FALL-03 | Error message contains expected path + fix + workaround | unit | `uv run pytest tests/test_repository_factory.py -x -q` | No -- Wave 0 |
| FALL-03 | Server integration: factory error -> ErrorOperatorService | integration | `uv run pytest tests/test_server.py -x -q` | Partial -- degraded mode tests exist, need SQLite-specific variant |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_repository_factory.py` -- covers FALL-01, FALL-03 (factory routing + error messages)
- [ ] Adapter test for FALL-02 bridge availability assertion (may fit in existing `test_adapter.py`)
- [ ] Server integration test for SQLite-not-found -> ErrorOperatorService path

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `server.py`, `service.py`, `repository/`, `bridge/factory.py` -- all integration points read directly
- `13-CONTEXT.md` -- user decisions locked
- `REQUIREMENTS.md` -- FALL-01, FALL-02, FALL-03 requirements

### Secondary (MEDIUM confidence)
- None needed -- this is purely internal wiring with no external dependencies

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new deps, all existing code
- Architecture: HIGH -- factory pattern proven, all pieces exist
- Pitfalls: HIGH -- codebase fully inspected, integration points clear

**Research date:** 2026-03-07
**Valid until:** 2026-04-07 (stable -- no external dependency changes possible)
