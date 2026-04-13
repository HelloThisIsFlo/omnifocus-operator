# Field Selection Review Codex

## Executive Summary

After reviewing the three worktrees, the best implementation is:

**`agent-1edcddf2`**

It is the strongest implementation because it puts field selection and null exclusion in the right architectural layer, preserves the service contract, and explicitly handles the MCP output schema problem instead of side-stepping it.

The short version:

- `agent-1edcddf2` treats projection as a presentation concern at the server boundary.
- `agent-1edcddf2` keeps `OperatorService` returning full `Task` and `Project` models.
- `agent-1edcddf2` relaxes the generated output schema so projected responses remain valid for MCP clients.
- `agent-1edcddf2` offers the best user-facing ergonomics: `["*"]`, automatic `id`, snake_case normalization, and warnings for bad field names.

The ranking is:

1. `agent-1edcddf2`
2. `agent-904b6be1`
3. `agent-878a38d0`

---

## What Was Being Compared

All three agents implemented the same feature:

- Field selection for `list_tasks` and `list_projects`
- Null exclusion control

In practice, the feature means a caller should be able to do things like:

```json
{
  "query": {
    "fields": ["id", "name", "dueDate"],
    "excludeNull": true
  }
}
```

And receive a smaller, more targeted response instead of the full model payload.

This is a deceptively small feature. It looks like a response formatting change, but it touches several sensitive areas:

- API contract design
- type honesty
- schema generation
- tool documentation
- test coverage
- server/service boundary discipline

That is why the best implementation is not just the one that "works", but the one that fits the system cleanly.

---

## Recommendation At A Glance

| Worktree | Verdict | Why |
|---|---|---|
| `agent-1edcddf2` | Best | Best architecture, best schema handling, best API ergonomics |
| `agent-904b6be1` | Good but weaker | Simpler than the others, but it weakens the response schema too much |
| `agent-878a38d0` | Third | Passes tests, but the service contract becomes dishonest and the API/docs are less coherent |

---

## Why `agent-1edcddf2` Wins

### 1. It puts the feature in the right layer

Field selection is a presentation concern.

That means the ideal place for it is at the boundary where the server turns rich models into tool output.

`agent-1edcddf2` follows that idea closely:

- Repository returns full models
- Service returns full models
- Server applies projection when formatting the final tool response

That keeps the core layers stable and predictable.

### 2. It preserves the service contract

The service continues to return full `ListResult[Task]` and `ListResult[Project]`.

That matters because the service layer is shared internal logic. It should represent domain behavior, not transport formatting.

This is the cleanest mental model:

- service = business logic
- server = transport and presentation

### 3. It explicitly solves the schema problem

Projection changes the response shape. Once fields can be omitted, the normal full-item schema is no longer accurate.

`agent-1edcddf2` is the only implementation that addresses this head-on by generating a relaxed output schema where:

- all documented fields are still visible to clients
- only `id` remains required

That is a strong design decision. It acknowledges the real contract change and models it properly.

### 4. It gives the best caller experience

Its projection behavior is the most practical:

- `fields: ["*"]` returns everything
- `id` is always included
- snake_case field names are normalized to camelCase
- bad fields are warned and ignored instead of hard-failing the whole call

This is a good fit for agent-facing tools, where resilience and recoverability matter.

### 5. It gives the clearest user-facing documentation

The tool descriptions were updated to explain:

- the default projected fields
- how to request all fields
- that nulls are excluded by default

This makes the feature discoverable instead of implicit.

---

## Architectural Overview

### The ideal shape for this feature

```text
Caller
  -> FastMCP Tool
    -> OperatorService
      -> Repository
        -> Full Task / Project models
    -> Projection step at server boundary
      -> final JSON response
```

This keeps the domain layers rich and stable, and only shapes output at the edge.

### How the three implementations compare

```text
agent-904b6be1
Caller
  -> FastMCP Tool
    -> OperatorService
      -> projection happens here
      -> service returns dict-shaped results

agent-1edcddf2
Caller
  -> FastMCP Tool
    -> OperatorService
      -> full Task / Project models
    -> projection happens here
    -> relaxed output schema published here

agent-878a38d0
Caller
  -> FastMCP Tool
    -> OperatorService
      -> sometimes returns full models
      -> sometimes returns projected dicts masquerading as models
```

### Why this matters

The deeper projection logic moves into the stack, the more it pollutes internal contracts.

The closer projection stays to the boundary, the easier the system remains to reason about.

That is the central reason `agent-1edcddf2` comes out ahead.

---

## Side-By-Side Comparison

| Category | `agent-904b6be1` | `agent-1edcddf2` | `agent-878a38d0` |
|---|---|---|---|
| Projection layer | Service | Server | Service |
| Service returns full models | No | Yes | Sometimes no |
| Response schema handling | Downgraded to dict result type | Relaxed schema, still well-described | Keeps old service type, but returns dicts |
| Type honesty | Reasonable, but lower fidelity | Strongest | Weakest |
| API ergonomics | Strict camelCase validation | Most ergonomic | Mixed and less coherent |
| Docs quality | Minimal | Strong | Mixed |
| Overall | Good | Best | Third |

---

## Concrete Example

### Desired request

```json
{
  "query": {
    "fields": ["name", "flagged"],
    "excludeNull": true
  }
}
```

### Desired response

```json
{
  "items": [
    {
      "id": "task-123",
      "name": "Review roadmap",
      "flagged": true
    }
  ],
  "total": 1,
  "hasMore": false
}
```

### Why `agent-1edcddf2` handles this best

With `agent-1edcddf2`, this request flows through the stack cleanly:

1. The repository still returns a real `Task`
2. The service still reasons in terms of `Task`
3. The server projects the output at the very end
4. The output schema still documents the available fields correctly

That means the feature works without distorting the layers underneath it.

---

## Detailed Review By Worktree

## `agent-1edcddf2`

### Strengths

- Best architectural boundary
- Best treatment of schema validity
- Best caller ergonomics
- Best balance of strictness and resilience
- Strong dedicated test coverage around projection behavior

### Key design choices

The implementation introduces a dedicated projection module and keeps the logic focused there:

- field set definitions
- field resolution
- projection application
- relaxed schema generation

This is good modularity. The module has a single, coherent responsibility.

### Strongest code decisions

#### Projection is explicitly documented as a server-layer concern

That is the right framing:

```python
"""Field projection and null exclusion for list tool responses.

Projection is a presentation concern applied in the server layer.
The service and repository always return full models...
"""
```

This is one of the clearest signals in the whole comparison.

#### The server publishes relaxed schemas

This is the critical architectural move:

```python
_list_tasks_schema = build_projected_schema(Task)
_list_projects_schema = build_projected_schema(Project)
```

And then:

```python
@mcp.tool(..., output_schema=_list_tasks_schema)
async def list_tasks(...) -> dict[str, Any]:
```

This is the only implementation that fully respects the fact that projected output is no longer a full `Task` schema.

#### The service contract stays clean

The service continues to return the full rich result:

```python
result = await service.list_tasks(query)
return apply_projection(
    result, query.fields, query.exclude_null, TASK_DEFAULT_FIELDS, TASK_ALL_FIELDS
)
```

That separation is strong.

### Tradeoffs

It is the most ambitious implementation of the three.

That means it introduces more code than `agent-904b6be1`. But the extra code is justified because it is solving a real contract problem, not just adding abstraction for its own sake.

### Bottom line

This is the only implementation that is both:

- technically clean
- product-ready at the MCP boundary

That is why it is the best.

---

## `agent-904b6be1`

### Strengths

- Straightforward
- Easy to follow
- Strong contract-level validation for requested fields
- Minimal moving parts

### What it does well

It validates field names against actual model fields, which is a strong and disciplined choice:

```python
TASK_VALID_FIELDS: frozenset[str] = frozenset(to_camel(name) for name in Task.model_fields)
```

And:

```python
unknown = [f for f in v if f not in TASK_VALID_FIELDS]
...
raise ValueError(UNKNOWN_OUTPUT_FIELD.format(...))
```

This is more explicit and stricter than the `agent-1edcddf2` approach.

### Main weakness

It changes the tool return annotation to:

```python
ListResult[dict[str, Any]]
```

That weakens the published schema significantly.

The project already documents that FastMCP uses the return annotation to generate the output schema. In this repo, that is an important part of the tool contract. Replacing rich item types with plain dicts solves the projection issue in a blunt way, but at a real cost.

### Why it loses to `agent-1edcddf2`

It solves the feature.
It does not solve the feature elegantly.

The difference is:

- `agent-904b6be1` makes the schema less informative
- `agent-1edcddf2` keeps the schema useful and adapts it correctly

### Bottom line

A solid implementation, and clearly better than `agent-878a38d0`, but not the best.

---

## `agent-878a38d0`

### Strengths

- Dedicated projection module
- Good test coverage
- Preserves default full-model behavior when projection is not requested

### Main weaknesses

#### 1. The service contract is no longer honest

The service still declares:

```python
async def _delegate(self) -> ListResult[Task]:
```

But in projection mode it returns projected dicts:

```python
return ListResult(
    items=projected,  # type: ignore[arg-type]  # dict masquerading as Task
    ...
)
```

This is the weakest design point across all three implementations.

The type ignore is not incidental. It is covering a real mismatch between the declared contract and the actual runtime value.

#### 2. It mixes two response models inside the same layer

When projection is off, the service returns full models.
When projection is on, the service returns dict-like projected items.

That means callers of the service cannot rely on one stable shape.

This is exactly the kind of ambiguity that makes internal APIs harder to maintain.

#### 3. The field naming story is less coherent

The projection module defines fields in snake_case internals like:

- `due_date`
- `effective_flagged`
- `has_children`

But output is serialized in camelCase.

That is workable internally, but it creates unnecessary translation complexity and is less clean than building the field-selection API around the final public field names.

#### 4. The docs lag behind the behavior

The descriptions add projection-specific field docs, but the main list tool docs still describe the old full field shape instead of the new projected defaults.

That makes the feature less easy to discover and less easy to trust.

### Why it ranks third

It passes tests and it is not a bad implementation in an absolute sense.

But the type dishonesty is a deeper architectural flaw than the tradeoff made by `agent-904b6be1`.

If I had to maintain one of these branches over time, this is the one I would be least comfortable merging as-is.

---

## The Key Architectural Difference In One Sentence

`agent-1edcddf2` is best because it keeps projection at the transport boundary instead of letting it leak into the service contract.

That is the core of the decision.

---

## Test Evidence

I validated the relevant suites in each worktree using source-pinned runs so each worktree imported its own `src/` tree:

```bash
env PYTHONPATH=src .venv/bin/python -m pytest --no-cov ...
```

Relevant outcomes:

- `agent-904b6be1`: targeted list/server suites passed
- `agent-1edcddf2`: targeted list/projection/server suites passed
- `agent-878a38d0`: targeted list/projection/server suites passed

This matters because the final recommendation is not based on one branch being broken. The branches were close enough functionally that the decision had to be made on architecture quality, contract integrity, and long-term maintainability.

---

## Final Recommendation

Merge or build from **`agent-1edcddf2`**.

If you want the cleanest summary of why:

- it respects the architecture
- it preserves the service contract
- it handles output schema evolution correctly
- it gives the best caller experience
- it is the easiest implementation to defend in a code review

If you want the shortest possible version:

**`agent-1edcddf2` is the only implementation that solves both the feature and the contract implications of the feature.**

