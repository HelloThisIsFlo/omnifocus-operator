# Phase 14: Model Refactor & Lookups - Context

**Gathered:** 2026-03-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Unified parent field on Task read model, rename `list_all` MCP tool to `get_all`, and three get-by-ID tools (`get_task`, `get_project`, `get_tag`). No new entity types, no filtering, no write pipeline.

</domain>

<decisions>
## Implementation Decisions

### ParentRef shape
- Unified `parent` field: `{ type, id, name } | null`
- `type` values: `"project"` or `"task"` (string literal, not enum)
- Includes `name` for agent convenience — consistent with existing TagRef pattern (id + name)
- Inbox tasks: `parent: null` (not a fake parent object); `in_inbox` field already handles inbox detection
- Immediate parent only — no `containing_project` shortcut. Agent already knows context in practice (got the ID from somewhere). Deeply nested subtask needing project discovery is a niche case that doesn't justify a second field

### Not-found behavior
- Raise MCP error (`isError: true`) for non-existent IDs
- Simple error message: "Task not found: {id}" (no hints about other entity types)
- No ID format validation — just query the database and let "not found" cover invalid/missing IDs

### Tool return shape
- get-by-ID tools return the bare entity object directly (no envelope/wrapper)
- Same fields as in `get_all` — identical Pydantic model, no enrichment

### Tool naming
- Hard rename: `list_all` removed, `get_all` added (breaking change, acceptable pre-v2)
- Simple singular names: `get_task`, `get_project`, `get_tag`, `get_all`
- No namespace prefix — MCP server itself is the namespace
- Single `id` parameter (not batch/list)

### Claude's Discretion
- ParentRef as Pydantic model vs TypedDict vs inline dict
- SQLite query strategy for get-by-ID (single query vs reuse existing _read_all)
- How to handle the `containingProjectInfo` → parent type mapping in the SQLite adapter
- Test structure for new tools

</decisions>

<specifics>
## Specific Ideas

- ParentRef should mirror TagRef's pattern — both are `{ id, name }` with ParentRef adding `type`
- get_all payload is ~2.5MB in practice, mostly useful for debugging — but that's a separate concern (see Deferred Ideas)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `TagRef` model (`models/common.py`): existing `{ id, name }` ref pattern — ParentRef extends this with `type`
- `OmniFocusBaseModel` with camelCase alias config: ParentRef inherits this for consistent serialization
- `_map_task_row` (`repository/hybrid.py:216-257`): already maps `containingProjectInfo` and `parent` — needs update to build ParentRef
- `AllEntities` model (`models/snapshot.py`): container for get_all, individual models reused for get-by-ID

### Established Patterns
- TYPE_CHECKING imports + model_rebuild for Pydantic forward refs
- Dict-based adapter mapping tables for enum transformations
- Repository protocol with structural typing (add get_task/get_project/get_tag methods)
- FastMCP tool registration with ToolAnnotations (readOnlyHint, idempotentHint)

### Integration Points
- `server.py:_register_tools`: add 3 new tool registrations + rename list_all → get_all
- `service.py:OperatorService`: add get_task/get_project/get_tag delegation methods
- `repository/protocol.py:Repository`: extend protocol with get-by-ID methods
- `repository/hybrid.py:HybridRepository`: add SQLite queries by persistentIdentifier
- `repository/in_memory.py:InMemoryRepository`: add in-memory lookup by ID
- `bridge/adapter.py`: update task adapter for new parent field structure

</code_context>

<deferred>
## Deferred Ideas

- **Summary/lightweight mode for get_all** — boolean flag that returns only `{ id, name }` per entity instead of full objects. Would make get_all actually usable by agents (currently ~2.5MB). Related to v1.4 field selection (OUTP-02) but could be a simpler standalone feature.

</deferred>

---

*Phase: 14-model-refactor-lookups*
*Context gathered: 2026-03-07*
