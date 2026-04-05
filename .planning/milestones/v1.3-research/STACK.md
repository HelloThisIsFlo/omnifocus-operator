# Technology Stack

**Project:** v1.3 Read Tools
**Researched:** 2026-03-29

## Recommended Stack

No new dependencies. Everything needed is already in the codebase or stdlib.

### Core (unchanged)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.12+ | Runtime | Existing constraint |
| FastMCP | >=3.1.1 | MCP server framework | Existing -- tool registration, serialization |
| Pydantic | v2 | Model validation, serialization | Existing -- query models, result models |
| sqlite3 | stdlib | SQL queries | Existing -- HybridRepository read path |

### New Internal Modules (no deps)

| Module | Purpose | Why New |
|--------|---------|---------|
| `repository/query_builder.py` | SQL string + params generation from query models | Pure functions, testable without database |
| `repository/filter.py` | In-memory filter predicates for BridgeRepository | Bridge fallback path needs Python filtering on snapshot |
| `contracts/use_cases/list_tasks.py` | ListTasksQuery model | Typed filter contract for task listing |
| `contracts/use_cases/list_projects.py` | ListProjectsQuery model | Typed filter contract for project listing |
| `contracts/use_cases/list_common.py` | ListResult generic container | Shared by list/count, both entity types |

## Key Technical Decisions

### Dynamic WHERE Clause Builder (not ORM)

Accumulate `(sql_fragment, params_list)` tuples, join with AND. Pure functions: query model in, `(sql_string, params_tuple)` out.

- Parameterized queries only (`?` placeholders) -- no SQL injection
- Composes with existing `_TASKS_SQL` and `_PROJECTS_SQL` base queries
- Fixed filter surface (10 task, 6 project) -- no need for class-based builder abstraction

### Tag Filter: Subquery, Not JOIN

```sql
t.persistentIdentifier IN (SELECT task FROM TaskToTag WHERE tag IN (?,?))
```

JOIN on TaskToTag creates duplicate rows when a task has multiple matching tags. Subquery returns each task once.

### Substring Search: LIKE with ESCAPE

```sql
(t.name LIKE ? ESCAPE '\' OR t.plainTextNote LIKE ? ESCAPE '\')
```

SQLite's default `LIKE` is case-insensitive for ASCII. Sufficient for task names/notes at current scale. No FTS5 needed (requires writable DB).

### Review Duration: Python Resolution to CF Epoch Float

`nextReviewDate` stored as CF epoch float (seconds since 2001-01-01). Resolve `"1w"`, `"2m"` etc. to Python datetime, convert to CF epoch, compare via parameterized `<= ?`. Reuses existing `_CF_EPOCH` constant.

### Pagination: LIMIT/OFFSET (not keyset)

Dataset is ~2,400 tasks. OFFSET penalty is negligible. MCP tools are stateless -- cursor pagination implies session state. LIMIT/OFFSET is the spec contract.

### Connection Semantics: Fresh Read-Only Per Call

Same pattern as existing `_read_task`, `_read_project`, `_read_tag`. No pooling needed -- SQLite file open is ~0.1ms. WAL mode handles concurrent reads.

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| SQL builder | Hand-built parameterized queries | SQLAlchemy Core | Zero new deps constraint. Fixed query surface doesn't benefit from ORM |
| Async SQLite | asyncio.to_thread(sync) | aiosqlite | Adds a dep. to_thread is the established pattern |
| In-memory filter | Custom predicate functions | pandas / polars | Overkill for <3K objects. List comprehensions are clearer |
| Full-text search | LIKE with ESCAPE | FTS5 virtual tables | Requires writable DB. Overkill for substring match |
| Pagination | LIMIT/OFFSET | Keyset/cursor | Stateless protocol, tiny dataset, added complexity |
| Count | len() after filtering | SQL COUNT(*) | len() is simpler with one code path. COUNT(*) is future optimization if needed |

## Installation

No changes to `pyproject.toml`.

```bash
uv sync  # existing deps are sufficient
```

## Sources

- Project constraint: `fastmcp>=3.1.1` only runtime dependency (PROJECT.md)
- SQLite via stdlib: established in v1.1 (`.research/deep-dives/direct-database-access/RESULTS.md`)
- Python sqlite3 docs: parameterized queries, Row factory -- HIGH confidence
- SQLite LIKE behavior: case-insensitive for ASCII by default -- HIGH confidence
