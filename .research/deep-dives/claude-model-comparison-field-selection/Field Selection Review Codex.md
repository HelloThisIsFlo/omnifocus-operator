# Field Selection Review — Codex

> [!important] Verdict
>
> - 🥇 **Opus 4.6** — best architecture, schema handling, and caller ergonomics
> - 🥈 **Sonnet 4.6** — solid and simple, but weakens the response schema
> - 🥉 **Opus 4.5** — passes tests, but the service contract becomes dishonest

> [!note] Naming
>
> - Reviews reference models by name, not worktree IDs
> - Opus 4.6 = `agent-1edcddf2`, Sonnet 4.6 = `agent-904b6be1`, Opus 4.5 = `agent-878a38d0`
> - Branches: `claude-model-comparison-field-selection/<model>`

## The Feature

Field selection + null exclusion for `list_tasks` and `list_projects`:

```json
{
  "query": {
    "fields": ["id", "name", "dueDate"],
    "excludeNull": true
  }
}
```

Deceptively small — touches API contracts, type honesty, schema generation, tool docs, and server/service boundary discipline. The best implementation isn't the one that "works" — it's the one that fits the system cleanly.

## Comparison

| Category | 🥇 Opus 4.6 | 🥈 Sonnet 4.6 | 🥉 Opus 4.5 |
|---|---|---|---|
| **Projection layer** | ✅ Server | Service | Service |
| **Service returns full models** | ✅ Yes | No | Sometimes |
| **Schema handling** | Relaxed, well-described | Downgraded to `dict` | Keeps old type, returns dicts |
| **Type honesty** | ✅ Strongest | Reasonable, lower fidelity | ❌ Weakest |
| **API ergonomics** | Most ergonomic | Strict camelCase | Mixed |
| **Docs quality** | Strong | Minimal | Mixed |

## Architecture

### The ideal shape

```text
Caller → FastMCP Tool → OperatorService → Repository
                                              ↓
                                        Full Task/Project models
                    ↓
              Projection at server boundary
                    ↓
              Final JSON response
```

Domain layers stay rich and stable. Output shaping happens at the edge.

### How each model approached it

- 🥇 **Opus 4.6** — projection at the server boundary
  - Service returns full `ListResult[Task]` / `ListResult[Project]`
  - Server applies `apply_projection()` and publishes relaxed output schema
- 🥈 **Sonnet 4.6** — projection in the service layer
  - Service converts models to dicts, filters fields, returns `ListResult[dict[str, Any]]`
  - Schema loses type information
- 🥉 **Opus 4.5** — projection in the service layer (with masquerading)
  - Service sometimes returns full models, sometimes projected dicts
  - `type: ignore[arg-type]` covers the mismatch

> [!important] The core insight
>
> - The deeper projection moves into the stack, the more it pollutes internal contracts
> - The closer it stays to the boundary, the easier the system remains to reason about
> - => Opus 4.6 wins because it keeps projection at the **transport boundary**

## Why Opus 4.6 Wins

- ✅ **Right layer** — projection is a presentation concern, belongs at the server boundary
  - Repository → full models
  - Service → full models
  - Server → applies projection at the very end
- ✅ **Preserves the service contract** — `OperatorService` keeps returning full `ListResult[Task]`
  - Service = business logic, Server = transport + presentation
  - No ambiguity for internal callers
- ✅ **Solves the schema problem** — generates a relaxed output schema where:
  - All documented fields remain visible to clients
  - Only `id` stays required
  - => Projected responses are valid for MCP clients without losing type documentation
- ✅ **Best caller experience**
  - `fields: ["*"]` → returns everything
  - `id` always included automatically
  - `snake_case` → normalized to `camelCase`
  - Bad field names → warned and ignored (not hard error)
- ✅ **Clearest tool documentation** — descriptions updated with:
  - Default projected fields
  - How to request all fields
  - `excludeNull` default behavior

### Concrete example

**Request:**

```json
{ "fields": ["name", "flagged"], "excludeNull": true }
```

**Response:**

```json
{
  "items": [{ "id": "task-123", "name": "Review roadmap", "flagged": true }],
  "total": 1, "hasMore": false
}
```

The request flows cleanly: repository returns a real `Task` → service reasons in `Task` → server projects at the end → output schema still documents available fields.

## Detailed Findings

### 🥇 Opus 4.6

**Strengths:**

- Best architectural boundary, schema handling, caller ergonomics
- Dedicated projection module with single, coherent responsibility
  - Field set definitions, resolution, application, relaxed schema generation
- Strong dedicated test coverage for projection behavior

**Key code decisions:**

- Projection explicitly documented as a server-layer concern:
  ```python
  """Projection is a presentation concern applied in the server layer.
  The service and repository always return full models..."""
  ```
- Server publishes relaxed schemas at registration:
  ```python
  _list_tasks_schema = build_projected_schema(Task)

  @mcp.tool(..., output_schema=_list_tasks_schema)
  async def list_tasks(...) -> dict[str, Any]:
  ```
- Service contract stays clean:
  ```python
  result = await service.list_tasks(query)
  return apply_projection(result, query.fields, query.exclude_null, ...)
  ```

**Tradeoff:** Most ambitious of the three — more code than Sonnet 4.6. Justified because it solves a real contract problem, not just adding abstraction.

### 🥈 Sonnet 4.6

**Strengths:**

- Straightforward, easy to follow, minimal moving parts
- Strong field validation against actual model fields:
  ```python
  TASK_VALID_FIELDS: frozenset[str] = frozenset(to_camel(name) for name in Task.model_fields)
  ```

**Main weakness:** Changes the tool return annotation to `ListResult[dict[str, Any]]`

- Weakens the published schema significantly
- FastMCP uses return annotations to generate output schema — this repo relies on that
- => Solves the feature, doesn't solve it elegantly

### 🥉 Opus 4.5

**Strengths:**

- Dedicated projection module, good test coverage
- Preserves full-model behavior when projection is off

**Main weaknesses:**

- ❌ **Dishonest service contract** — declares `ListResult[Task]`, returns projected dicts
  ```python
  return ListResult(items=projected, ...)  # type: ignore[arg-type]
  ```
  - The `type: ignore` covers a real mismatch, not a false positive
- ❌ **Two response shapes** from the same layer — callers can't rely on one stable shape
- ⚠️ **Field naming incoherence** — projection uses `snake_case` internally (`due_date`, `effective_flagged`) while output is `camelCase`
- ⚠️ **Docs lag behavior** — tool descriptions still describe old full-field shape

## Test Evidence

All three suites passed when run with source-pinned imports:

```bash
env PYTHONPATH=src .venv/bin/python -m pytest --no-cov ...
```

- 🥇 Opus 4.6 — list/projection/server suites ✅
- 🥈 Sonnet 4.6 — list/server suites ✅
- 🥉 Opus 4.5 — list/projection/server suites ✅

=> The decision was made on architecture quality, contract integrity, and maintainability — not on which branch was broken.
