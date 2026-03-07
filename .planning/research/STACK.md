# Stack Research

**Domain:** SQLite cache reading + two-axis status model for existing Python MCP server
**Researched:** 2026-03-07
**Confidence:** HIGH

## Recommendation Summary

**Zero new runtime dependencies.** Python 3.12 stdlib covers SQLite reading, WAL polling, and path resolution. The two-axis status model is a Pydantic enum refactor. Keep the single-dep (`mcp>=1.26.0`) architecture.

---

## What Changes (v1.1 additions only)

### New Stdlib Usage

| Module | Purpose | Why Sufficient |
|--------|---------|----------------|
| `sqlite3` | Read OmniFocus SQLite cache | Built-in, WAL-aware, supports `mode=ro` URI connections. 46ms reads don't justify async overhead. SQLite 3.51.0 on current macOS. |
| `os.stat()` | WAL mtime polling for freshness detection | `st_mtime_ns` gives nanosecond precision. WAL write = data queryable (SQLite design guarantee). |
| `pathlib.Path` | Database path resolution | Already used in project. `expanduser()` handles `~/Library/Group Containers/...` including spaces. |

### Pydantic Model Changes (no new deps)

| Change | Details |
|--------|---------|
| **Delete enums** | `TaskStatus`, `ProjectStatus` |
| **Add enums** | `Urgency` (overdue/due_soon/none), `Availability` (available/blocked/completed/dropped) -- same `StrEnum` base |
| **Modify `OmniFocusEntity`** | Remove `active`, `effective_active` |
| **Modify `ActionableEntity`** | Remove `completed` (bool), `sequential`, `completed_by_children`, `should_use_floating_time_zone`. Add `urgency: Urgency`, `availability: Availability` |

---

## SQLite Connection Pattern

```python
import sqlite3

# Read-only via URI -- prevents accidental writes to OmniFocus DB
conn = sqlite3.connect(
    f"file:{db_path}?mode=ro",
    uri=True,
    check_same_thread=False,
)
conn.row_factory = sqlite3.Row  # dict-like column access
```

- **`mode=ro`**: Engine-level read-only. Not just Python-side; SQLite itself refuses writes.
- **`check_same_thread=False`**: Safe for read-only. Allows connection reuse across calls.
- **`row_factory=sqlite3.Row`**: Access columns by name, clean mapping to Pydantic constructors.
- **No connection pooling needed**: Single connection, reused. 46ms query time, sequential access via stdio.

## WAL Freshness Pattern

```python
import os

WAL_PATH = db_path.parent / (db_path.name + "-wal")

def wal_mtime_ns() -> int:
    return os.stat(WAL_PATH).st_mtime_ns
```

- Poll every 50ms, timeout at 2s after a write operation
- WAL mtime change = data queryable (documented SQLite guarantee)
- No file-watching library needed

## Database Path

```
~/Library/Group Containers/34YW5XSRB7.com.omnigroup.OmniFocus/
  com.omnigroup.OmniFocus4/com.omnigroup.OmniFocusModel/OmniFocusDatabase.db
```

- Hardcoded default, overridable via `OMNIFOCUS_DB_PATH` env var
- `Path.expanduser()` resolves `~`
- `pathlib` handles spaces in "Group Containers" natively

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `aiosqlite` | 46ms reads are fast enough to run synchronously. stdio MCP server processes one request at a time. Async adds complexity (context managers, error handling) with zero benefit. | `sqlite3` (stdlib) |
| `sqlalchemy` / `peewee` | ORM is massive overkill for read-only queries against a known, stable schema (unchanged since OF1 2008). Adds deps, abstraction, and mapping complexity. | Raw SQL strings with `sqlite3` |
| `watchdog` / `watchfiles` | File watching is overkill for mtime polling on a known path. Adds dependency, background threads, event loops. | `os.stat().st_mtime_ns` |
| `apsw` | Alternative SQLite binding with VFS support. Unnecessary for simple reads. Non-stdlib. | `sqlite3` (stdlib) |
| `pydantic-settings` | DB path config via env var. One `os.environ.get()` with a default is simpler than adding a dependency for a single setting. | `os.environ.get()` + `pathlib.Path` |
| `dataclasses` for enums | Already using `StrEnum` + Pydantic throughout. No reason to introduce a parallel pattern. | `enum.StrEnum` (existing pattern) |

---

## Alternatives Considered

| Recommended | Alternative | When to Switch |
|-------------|-------------|----------------|
| `sqlite3` (stdlib) | `aiosqlite` | If server moves to SSE/StreamableHTTP transport with concurrent requests. Not applicable for stdio. |
| Raw SQL strings | SQLAlchemy Core | If query composition grows complex (dynamic multi-predicate filtering). Revisit in filtering milestone. |
| `os.stat()` polling | `watchdog` | If real-time push notifications of DB changes are ever needed. Not applicable for request-driven reads. |
| Single `sqlite3` connection | Connection per query | If thread safety becomes a concern (e.g., background refresh). Not applicable for sequential stdio access. |

---

## Integration Points

### Where SQLite Reader Fits

```
MCP Server -> Service Layer -> Repository -> [SQLite Reader | OmniJS Bridge]
                                              ^^^^^^^^^^^^
                                              NEW: primary read path
```

- **Repository** already abstracts the data source. SQLite reader implements the same read interface.
- **Bridge** remains for writes and as manual fallback (`OMNIFOCUS_BRIDGE=omnijs`).
- **Factory** gains logic: default to SQLite reader, fall back to error-serving if DB not found.

### What Stays Unchanged

- `pyproject.toml` dependencies section (no additions)
- Dev dependencies (no additions)
- All existing test infrastructure (pytest, mypy, ruff)
- MCP server layer, service layer interfaces
- Bridge protocol for writes

---

## Version Compatibility

| Component | Version | Notes |
|-----------|---------|-------|
| Python `sqlite3` | Ships with 3.12 | SQLite 3.51.0 engine on macOS Sequoia. WAL support since SQLite 3.7.0 (2010). URI filenames since 3.8.0 (2013). |
| Pydantic v2 | Transitive via `mcp>=1.26.0` | `StrEnum` validated natively. `AwareDatetime` handles timezone-aware dates. |
| macOS SQLite | 3.51.0 | System SQLite matches Python's bundled version. OmniFocus uses system SQLite for its cache. |

---

## Installation

```bash
# Nothing to install. Zero new dependencies.
# Existing `uv sync` is sufficient.
```

---

## Sources

- Python 3.12 `sqlite3` stdlib docs -- URI mode, `mode=ro`, `row_factory`, WAL support (HIGH confidence)
- `.research/deep-dives/direct-database-access/RESULTS.md` -- benchmarks (46ms), WAL timing (~500ms), schema stability (HIGH confidence, empirical)
- `.research/deep-dives/direct-database-access/RESULTS_pydantic-model.md` -- field mapping, enum design (HIGH confidence, validated against live DB)
- Local `python3 -c "import sqlite3; print(sqlite3.sqlite_version)"` = 3.51.0 (verified)

---
*Stack research for: OmniFocus Operator v1.1 SQLite cache reading*
*Researched: 2026-03-07*
