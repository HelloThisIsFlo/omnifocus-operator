# Feature Landscape

**Domain:** SQL-filtered list/count tools for MCP server
**Researched:** 2026-03-29

## Table Stakes

Features the v1.3 spec requires. Missing = milestone incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| `list_tasks` with 10 filters | Core deliverable -- agents need filtered reads | Med | Dynamic WHERE builder, tag subquery, LIKE search |
| `list_projects` with 6 filters | Project browsing beyond `get_all` | Med | Status shorthands, folder name resolution, review_due_within |
| `list_tags(status?)` | Tag discovery for agents | Low | Simple WHERE on dateHidden/allowsNextAction |
| `list_folders(status?)` | Folder structure browsing | Low | Simple WHERE on dateHidden |
| `list_perspectives()` | Perspective discovery | Low | No filters, plist parsing already exists |
| `count_tasks(...)` | Quick counts for planning | Low | Same filter path, return total_count |
| `count_projects(...)` | Project count by status | Low | Same filter path, return total_count |
| AND combination of filters | All filters compose with AND | Med | Builder pattern handles naturally |
| Completed/dropped excluded by default | Standard OmniFocus UX | Low | Default WHERE clauses |
| Parameterized queries | No SQL injection | Low | `?` placeholders throughout |
| Bridge fallback parity | BridgeRepository must match SQL results | Med | In-memory filtering on AllEntities snapshot |
| LIMIT/OFFSET pagination | Spec requirement on list_tasks/list_projects | Low | SQL LIMIT/OFFSET, Python slice for bridge |
| Substring search (name + notes) | Case-insensitive search via LIKE | Low | `%term%` on name and plainTextNote |
| `count_tasks() == len(list_tasks())` parity | Spec AC: one code path prevents divergence | Low | Shared filter logic |
| Tool descriptions for LLM discoverability | Spec AC: agent can call tools correctly | Med | Detailed descriptions per spec |

## Differentiators

Features that make the implementation stand out beyond minimum requirements.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| <6ms filtered queries | 7x faster than 46ms full snapshot | Low | Natural consequence of filtered SQL with fewer rows to map |
| Educational error messages | Agent learns from validation failures | Low | Extend existing pattern (write tools already do this) |
| Status shorthand expansion | `remaining`, `available`, `all` for projects | Low | Python-side expansion before SQL generation |
| `review_due_within` duration parsing | Natural language format (`now`, `1w`, `2m`) | Med | Python-side resolution to CF epoch float for SQL comparison |
| ListResult with total_count | Agents get pagination info without separate call | Low | `{items: [...], totalCount: N}` enables page computation |

## Anti-Features

Features to explicitly NOT build in v1.3.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Date-based filtering (due, defer, etc.) | Deferred to v1.3.1 -- complex period resolution semantics | Build WHERE clause infrastructure now; v1.3.1 extends it |
| Fuzzy search | Deferred to v1.4.1 -- different algorithm (not LIKE) | Substring LIKE is sufficient |
| Full-text search (FTS5) | Requires writable DB, overkill at scale | LIKE with ESCAPE |
| Custom indexes | Read-only DB, premature optimization | Full scan <5ms at current scale |
| Nested/hierarchical responses | Spec says flat with ID references | Flat lists with parent IDs |
| ORDER BY configuration | Not in spec | Hardcode ORDER BY t.rank |
| Field selection/projection | Deferred to v1.4 | Return full entity models |

## Feature Dependencies

```
Query models (ListTasksQuery, ListProjectsQuery)
  -> query_builder.py (SQL generation)
  -> filter.py (in-memory filtering)

query_builder.py
  -> HybridRepository.list_tasks
  -> HybridRepository.list_projects

filter.py
  -> BridgeRepository.list_tasks
  -> BridgeRepository.list_projects

Repository protocol extensions
  -> Service layer (orchestration + resolution)
  -> Server layer (tool registration)

Tag name resolution (existing Resolver.resolve_tags)
  -> _ListTasksPipeline
  -> service layer

CF epoch conversion (existing _CF_EPOCH, _parse_timestamp)
  -> review_due_within resolution
  -> (v1.3.1: all date filters)
```

## MVP Build Order

1. **Query models + ListResult** -- typed contracts everything depends on
2. **Query builder** -- pure functions, testable without database
3. **list_tasks (HybridRepository)** -- scalar filters first (inbox, flagged, has_children, availability, estimated_minutes_max), then tag subquery and search
4. **list_tasks (BridgeRepository)** -- in-memory fallback, equivalence tested
5. **list_projects for both repos** -- same pattern, adds status shorthands and review_due_within
6. **count_tasks / count_projects** -- thin wrappers on list infrastructure
7. **list_tags / list_folders / list_perspectives** -- simplest tools
8. **Service pipelines + server registration** -- wire everything up
9. **Cross-path equivalence tests** -- spec requirement

Defer entirely to v1.3.1: All date filtering (due, defer, planned, completed, dropped, added, modified).

## Sources

- Milestone spec: `.research/updated-spec/MILESTONE-v1.3.md`
- Date filter spec: `.research/updated-spec/MILESTONE-v1.3.1.md`
- Existing architecture: `docs/architecture.md`
