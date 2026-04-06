# Model Taxonomy

CQRS/DDD-inspired naming taxonomy for all Pydantic models in OmniFocus Operator.

## Foundational split

> [!important] Foundational split
> - **`models/`** = what OmniFocus **IS** (domain entities, `OmniFocusBaseModel`)
> - **`contracts/`** = what you can **DO** (operations, boundaries, `CommandModel` with `extra="forbid"`)
> - **Never** embed a `models/` class directly in a `contracts/` command — the base class difference (`extra="forbid"`) means write-side models always need their own class, even with identical fields

## Base class hierarchy

All models in `contracts/` that validate agent input need `extra="forbid"` to reject unknown fields. This shared behavior lives in `StrictModel`; semantic subclasses distinguish write commands from read queries:

```python
class StrictModel(OmniFocusBaseModel):
    """Base for all agent-facing contract models. Rejects unknown fields."""
    model_config = ConfigDict(extra="forbid")

class CommandModel(StrictModel):
    """Write-side contracts: commands, payloads, results, specs, actions."""
    pass

class QueryModel(StrictModel):
    """Read-side contracts: query filters and pagination."""
    pass
```

| Base class | Side | Purpose | Used by |
|------------|------|---------|---------|
| `StrictModel` | — | Shared `extra="forbid"` validation | Never used directly |
| `CommandModel` | Write (inbound) | Commands, payloads, specs, actions | `AddTaskCommand`, `EditTaskRepoPayload`, `LocationSpec`, ... |
| `QueryModel` | Read (inbound) | Query filters and pagination | `ListTasksQuery`, `ListTasksRepoQuery`, `DateFilter`, ... |

Outbound models (results on both sides) inherit `OmniFocusBaseModel` directly — they're system-constructed and don't need `extra="forbid"` validation. This applies to write-side results (`AddTaskResult`, `EditTaskRepoResult`), read-side result containers (`ListResult[T]`, `ListRepoResult[T]`), and core models.

This follows CQRS convention: **commands** change state, **queries** request information. Strict input validation (`extra="forbid"`) applies to inbound models at every boundary; outbound models are system-constructed projections.

## Overview

Every model's name indicates its layer and role. The taxonomy follows CQRS: **write-side** models (commands, payloads, results, specs) and **read-side** models (queries, result containers, output variants) have distinct conventions and base classes. Both sides share strict input validation via `StrictModel`.

**Core model as gravitational center:** The core model (no suffix, `models/`) is the canonical representation of each concept. Every boundary model relates to it directionally:

- **Inbound (write):** A write spec is **constructable** into a core model instance — spec fields map to core fields, with service-supplied defaults and resolution.
- **Outbound (read):** A read output model is **derivable** from a core model instance — transformation may suppress defaults, add computed fields, or reshape for ergonomics.
- **Query (read filters):** A query model defines selection criteria that produce a filtered collection of core model instances. It doesn't mirror the core model's shape — it specifies constraints.

Neither direction requires lossless round-tripping. The core model is the source of truth; boundary models are projections. See [Structure Over Discipline](structure-over-discipline.md) for why this is pre-documented rather than left to agent judgment.

**Service boundary principle:** Input models split at the service boundary — both write-side and read-side. The agent-facing model and the repo-facing model are always separate types, even when their fields are identical today. This follows [Structure Over Discipline](structure-over-discipline.md): the split exists so divergence is "add a field," not a design decision. Output result containers use shared generics (`ListResult[T]`, `ListRepoResult[T]`). Simple reads (get by ID) pass a plain string through every layer — no query model needed.

## Models

Every model falls into one of three categories: core (the domain truth), write-side (commands and their pipeline), or read-side (queries and their pipeline). Each category has its own conventions, base classes, and boundary models.

### Core models

The canonical representation of each concept — no suffix, lives in `models/`, inherits `OmniFocusBaseModel`. Used internally by service, parser, builder. Also serves as the read output model by default (see [Output models](#output-models) for when this changes).

| Suffix | Role | Examples |
|--------|------|---------|
| No suffix | Canonical domain entity or value object | `Task`, `Project`, `Tag`, `Frequency`, `RepetitionRule` |

### Write-side models

All write-side models live in `contracts/`. Inbound models (commands, payloads, specs, actions) inherit `CommandModel`; outbound models (results) inherit `OmniFocusBaseModel`.

#### Agent boundary (agent ↔ service)

| Suffix | Role | Direction | Examples |
|--------|------|-----------|---------|
| `<verb><noun>Command` | Top-level write instruction | Inbound | `AddTaskCommand`, `EditTaskCommand` |
| `<verb><noun>Result` | Outcome returned to agent | Outbound | `AddTaskResult`, `EditTaskResult` |

`<verb><noun>Result` inherits `OmniFocusBaseModel`, not `CommandModel` — it's outbound and system-constructed, not validated against agent input.

#### Repository boundary (service ↔ repository)

| Suffix | Role | Direction | Examples |
|--------|------|-----------|---------|
| `<verb><noun>RepoPayload` | Processed, bridge-ready data | Inbound | `AddTaskRepoPayload`, `EditTaskRepoPayload` |
| `<verb><noun>RepoResult` | Minimal confirmation from bridge | Outbound | `AddTaskRepoResult`, `EditTaskRepoResult` |

`<verb><noun>RepoResult` inherits `OmniFocusBaseModel` — outbound, same as `<verb><noun>Result`.

#### Value objects (nested within commands)

| Suffix | Role | When to use | Examples |
|--------|------|-------------|---------|
| `<noun>Action` | Stateful mutation in the actions block | Nested operation that mutates relative to current state | `TagAction`, `MoveAction` |
| `<noun>Spec` | Write-side value object (desired state) | Nested setter with different shape from its read counterpart | `RepetitionRuleAddSpec`, `RepetitionRuleEditSpec` |

> [!important] Why nested specs can't reuse core models
> A nested write input always needs its own `<noun>Spec` — even when its fields are identical to the core model. `CommandModel` enforces `extra="forbid"` at every nesting level; embedding a core model (`OmniFocusBaseModel`) in a command would leave a gap where unknown fields are silently accepted on the nested object.

Value objects are agent-boundary concepts. A `<noun>Spec` travels on the `Command`, not on the `RepoPayload` — the pipeline resolves the Spec into the core model (or flat fields) before the repo boundary. Similarly, a `<noun>Filter` travels on the `Query`, not on the `RepoQuery`. Nested value objects never need their own repo-boundary models.

### Read-side models

**Boundary adaptation principle:** The read side mirrors the write side at every boundary. `Spec` is to `Command` what `Read` is to `Query` — both adapt shapes for their respective direction. `RepoQuery` is to `Query` what `RepoPayload` is to `Command` — both carry resolved, unambiguous data for the repository. The core model is the canonical representation; boundary variants provide the shapes that make each direction natural.

The full parallel:

| Concern | Write-side | Read-side |
|---------|-----------|-----------|
| Top-level agent contract | `<verb><noun>Command` | `List<Noun>Query` |
| Top-level repo contract | `<verb><noun>RepoPayload` | `List<Noun>RepoQuery` |
| Agent-facing result | `<verb><noun>Result` | `ListResult[T]` |
| Repo-facing result | `<verb><noun>RepoResult` | `ListRepoResult[T]` |
| Nested input value object | `<noun>Spec` — desired state for complex fields | `<noun>Filter` — complex selection criteria |
| Nested output variant | — | `<noun>Read` — adapts output for complex fields |
| Base class (input) | `CommandModel` | `QueryModel` |
| Base class (output) | `OmniFocusBaseModel` | `OmniFocusBaseModel` |
| Lives in | `contracts/` | `contracts/` (query), `models/` (output) |

#### Agent boundary (agent ↔ service)

| Suffix | Role | Direction | Examples |
|--------|------|-----------|---------|
| `List<Noun>Query` | Validated filter + pagination from agent | Inbound | `ListTasksQuery`, `ListProjectsQuery` |
| `ListResult[T]` | Result container returned to agent (items + total_count + warnings) | Outbound | `ListResult[Task]`, `ListResult[Project]` |

`ListResult[T]` inherits `OmniFocusBaseModel`, not `QueryModel` — it's outbound and system-constructed, not validated against agent input. The `T` is a core model or `<noun>Read` variant.

#### Value objects (nested within queries)

| Suffix | Role | When to use | Examples |
|--------|------|-------------|---------|
| `<noun>Filter` | Complex selection criteria nested in a query | Agent-friendly filter with multiple input shapes that the service resolves before the repo | `DateFilter` |

`<noun>Filter` is the read-side counterpart of `<noun>Spec`. A Spec describes desired state for a complex write field; a Filter describes selection criteria for a complex query dimension. The service resolves the filter into concrete repo query fields — the filter object itself doesn't appear on the repo query.

#### Repository boundary (service ↔ repository)

| Suffix | Role | Direction | Examples |
|--------|------|-----------|---------|
| `List<Noun>RepoQuery` | Resolved, repo-ready filter parameters | Inbound | `ListTasksRepoQuery`, `ListProjectsRepoQuery` |
| `ListRepoResult[T]` | Minimal result from repository (items + total_count, no warnings) | Outbound | `ListRepoResult[Task]`, `ListRepoResult[Project]` |

`ListRepoResult[T]` inherits `OmniFocusBaseModel`. The service enriches it into a `ListResult[T]` (adding warnings, "did you mean?" suggestions, etc.) before returning to the agent — mirroring how `RepoResult` is enriched into `Result` on the write side.

#### Output models

The core model serves directly as read output by default. When the output boundary needs a different shape (suppressed defaults, computed fields, reshaped for ergonomics), introduce a `<noun>Read` variant — separate class, not a subclass, derivable from the core model.

| Suffix | Role | Examples |
|--------|------|---------|
| Core model (no suffix) | Default read output — used when shape matches | `Task`, `Project`, `Tag` |
| `<noun>Read` | Output-boundary variant, derivable from core | `FrequencyRead` (hypothetical — not yet needed) |

> [!note] Why "suppressed defaults" can't stay on the core model
> FastMCP serializes tool output via `pydantic_core.to_jsonable_python`, which has no `exclude_defaults` parameter. You don't control the serialization call. A `@field_serializer` on the parent can work as a workaround (see `RepetitionRule.frequency`), but when the concept is used in multiple places or the suppression is intrinsic to the read representation, a `<noun>Read` with the behavior built in is the principled path.

## Naming rules

- **Verb-first** for top-level write-side models: `<verb><noun>Command` — e.g., `AddTaskCommand`, `EditTaskCommand` (not `TaskAddCommand`)
- **Write-side verb matches tool verb**: tool is `add_tasks` → models are `AddTask*`; tool is `edit_tasks` → models are `EditTask*`
- **Noun-only** for core models: `Task`, `Project`, `Tag` (no verb, no suffix)
- **Value objects** within commands are suffix-free when unambiguous (`TagAction`, `MoveAction`), or use `<noun>Spec` when a read-side model of the same name exists. All value objects live in `contracts/` and inherit `CommandModel` — never reuse a read model from `models/` directly in a command
- **Base classes**: `CommandModel` for write-side inbound (commands, payloads, specs, actions), `QueryModel` for read-side inbound (queries, filters) — both inherit `StrictModel` (`extra="forbid"`). All outbound models (results, result containers) inherit `OmniFocusBaseModel` — system-constructed, no strict validation needed
- **Repo qualifier**: Both inbound and outbound models at the repository boundary use `Repo` prefix — write-side (`<verb><noun>RepoPayload`) and read-side (`List<Noun>RepoQuery`) alike
- **Noun-first for nested specs**: When a nested value object needs a verb qualifier (different shapes per use case), the domain noun leads: `RepetitionRuleAddSpec`, `RepetitionRuleEditSpec` (not `AddRepetitionRuleSpec`). Top-level models are verb-first (`AddTaskCommand`); nested specs are noun-first because they represent the THING in different contexts, not different actions.
- **Verb qualifier only when needed**: If a spec has the same shape for both add and edit, use plain `<noun>Spec` (no verb). Only add `Add`/`Edit` qualifier when shapes diverge (e.g., all-required vs patchable fields).
- **Filter for complex query dimensions**: `<noun>Filter` for nested selection criteria in queries — the read-side counterpart of `<noun>Spec`. Lives in `contracts/`, inherits `QueryModel`. The service resolves it into concrete repo query fields.
- **Read suffix only when needed**: Use the core model directly for read output (the common case). Only introduce `<noun>Read` when the output boundary requires a different shape. A `<noun>Read` is a separate class (not a subclass of the core model), inherits `OmniFocusBaseModel`, lives in `models/`, and must be derivable from the core model.
- **Shared generics for result containers**: `ListResult[T]` (agent-facing, includes warnings) and `ListRepoResult[T]` (repo-facing, no warnings) — not per-entity concrete types

## Agent-facing descriptions

Pydantic uses class docstrings and `Field(description=...)` as the `description` field in JSON Schema. When these models are nested inside MCP tool schemas, **every docstring and field description becomes agent-visible documentation**.

All agent-facing description text lives in `agent_messages/descriptions.py` — centralized alongside `errors.py` and `warnings.py`. This means:

- **Class docstrings** on agent-facing models use `__doc__ = CONSTANT` (not inline triple-quoted strings)
- **Field descriptions** use `Field(description=CONSTANT)` (not inline string literals)
- **Internal-only models** (base classes, RepoPayload/RepoResult/RepoQuery, sentinels) keep normal inline docstrings — they don't appear in JSON Schema

The `__doc__ = CONSTANT` pattern is a convention signal: it tells you "this docstring is agent-facing and will appear in the MCP tool schema." Regular inline docstrings mean "developer docs only."

**When adding a new tool to `server.py`**: pass `@mcp.tool(description=CONSTANT)` where the constant is defined in `descriptions.py`. Do not use inline docstrings on tool functions — the enforcement test will reject them.

**When adding a new model to `models/` or `contracts/`**: check if it will appear in an MCP tool's input or output schema. If yes, define its docstring and field descriptions as constants in `descriptions.py` and use the `__doc__ = CONSTANT` / `Field(description=CONSTANT)` patterns. An enforcement test scans these directories and will fail if inline descriptions are found on agent-facing classes.

**What's agent-facing?** Models referenced as field types in tool schemas get `$defs` entries — those are agent-visible. Base classes in an inheritance chain (e.g., `OmniFocusEntity`, `ActionableEntity`) do NOT get `$defs` entries; Pydantic flattens their fields into the leaf class.

## Type constraint boundary

`Literal` and `Annotated` constraint types live on **contract model fields** (`contracts/`), not on core model fields (`models/`). Core models use plain Python types (`str`, `int`, `list[str]`) with runtime validators enforcing correctness.

**Why:**
- **Contract models** define the agent's input schema, where self-documenting constraints (`enum`, `minimum`) guide agents toward valid input.
- **Core models** are used internally by parsers and builders that construct instances from dynamic data — `str.split(",")` returns `list[str]`, not `list[Literal["MO", ...]]`. Putting constraint types on these fields forces `cast()` or `type: ignore` at every construction site.

**Convention:**

| Layer | Field type | Schema effect | Validation |
|-------|-----------|---------------|------------|
| `contracts/` | `Literal["a", "b"]` | `enum: ["a", "b"]` | Type system + runtime |
| `contracts/` | `Annotated[int, Field(ge=1)]` | `minimum: 1` | Type system + runtime |
| `models/` | `str` | `type: string` | Runtime validator only |
| `models/` | `int` | `type: integer` | Runtime validator only |

**Type alias definitions** (e.g., `FrequencyType`, `DayCode`, `DayName`, `OnDate`) live in `contracts/` where they're consumed. Core models import shared validation functions, not type aliases.

> [!note] What about output schema?
> - _**Yes**_, Core models _**do**_ appear in agent output (unless a dedicated `Read` model exists), so their fields _**do**_ land in `outputSchema`.
> - _**However**_, current MCP clients (Claude Code, Claude Desktop) don't expose output schema to agents
> - _**Therefore**_, maintaining constraint annotations on core models for output schema documentation isn't worth the type-system complexity.


An AST enforcement test scans `models/` for `Literal` and `Annotated` field annotations and fails on any violation.

> [!note] Some MCP clients shadow custom validators with schema-level errors
> Some MCP clients (e.g., Claude Desktop co-work mode) pre-validate tool input against the JSON Schema **before** sending it to the server. When this happens, `field_validator` error messages never reach the agent — the client rejects the value first with a generic schema error (e.g., "Expected string, received null"). Both Claude Desktop (regular) and Claude Code CLI pass input directly to the server, where Pydantic validators fire and custom error messages are shown.
>
> Co-work's schema pre-validation is also **depth-limited** — it catches constraint violations on shallow fields (e.g., top-level `enum`, direct `$ref` hops) but may miss the same constraints on deeply nested fields (e.g., `repetitionRule.frequency.type`). So the same `enum` validator might be shadowed at one nesting level but reachable at another.
>
> During UAT, if a custom error message doesn't appear, try the same call via Claude Desktop or Claude Code — the validator likely works, it's just co-work intercepting first. Custom validators are kept as they work on most clients and protect programmatic callers.

## Decision tree for naming a new model

### Read-side

*Query input* (lives in `contracts/use_cases/`, inherits `QueryModel`):

1. Is it an agent-facing filter + pagination model? → `List<Noun>Query`
2. Is it a repo-facing resolved query? → `List<Noun>RepoQuery`
3. Is it a complex nested selection criteria within a query? → `<noun>Filter` (e.g., `DateFilter`)

*Result containers* (live in `contracts/use_cases/`, inherit `OmniFocusBaseModel` — outbound, no validation needed):

4. Is it the result container returned to the agent? → `ListResult[T]` (includes warnings)
5. Is it the result container from the repository? → `ListRepoResult[T]` (no warnings)

*Query output* (lives in `models/`, inherits `OmniFocusBaseModel`):

6. Is the read output shape identical to the core model? → Use the core model directly (no suffix)
7. Does the read output need a different shape (suppressed defaults, computed fields, reshaped for ergonomics)? → `<noun>Read` (separate class, derivable from core)

### Write-side

Lives in `contracts/`. Inbound models inherit `CommandModel`; outbound models (results) inherit `OmniFocusBaseModel`.

*Agent boundary:*

1. Is it a top-level instruction from the agent? → `<verb><noun>Command` (inherits `CommandModel`)
2. Is it the enriched outcome returned to the agent? → `<verb><noun>Result` (inherits `OmniFocusBaseModel`)

*Repository boundary:*

3. Is it processed data sent to the repository? → `<verb><noun>RepoPayload` (inherits `CommandModel`)
4. Is it the confirmation from the repository? → `<verb><noun>RepoResult` (inherits `OmniFocusBaseModel`)

*Value objects (nested within commands):*

5. Is it a stateful operation inside the actions block? → `<noun>Action`
6. Is it a complex nested value object (setter, not a mutation)? → `<noun>Spec`
   Write models inherit `CommandModel`, read output models inherit
   `OmniFocusBaseModel` (no `extra="forbid"`). This base class difference alone justifies
   a dedicated write model, even when the field shapes are identical.
     - Same shape across add/edit → `<noun>Spec` (e.g., `RepetitionRuleSpec`)
     - Different shapes per use case → `<noun><verb>Spec` (e.g., `RepetitionRuleAddSpec` for all-required, `RepetitionRuleEditSpec` for patchable fields)

## Ubiquitous language

> "The agent sends a **command** (write) or a **query** (read). For writes: the service validates, resolves, and builds a **repo payload**. The repository forwards to the bridge and returns a **repo result**. The service enriches this into a **result** for the agent. Within a command, **actions** mutate state; **specs** describe desired state for complex nested objects. When a spec needs different shapes per use case, the domain noun leads with a verb qualifier: RepetitionRuleAddSpec (creation shape) vs RepetitionRuleEditSpec (partial update shape). For filtered reads: the agent sends a **query**. Within a query, **filters** describe complex selection criteria for dimensions that need multiple input shapes (e.g., date ranges with shortcuts, periods, or absolute bounds). The service validates, resolves filters into concrete parameters, and transforms the query into a **repo query** — mirroring the write-side pattern. The repository returns a **list repo result** (items + total count). The service enriches this into a **list result** for the agent (adding warnings and suggestions). Simple reads (get by ID) pass a plain string through every layer — no query model needed. For read output, the **core model** is used directly unless the output boundary needs a different shape — then a **read model** (`<noun>Read`) provides the variant, derivable from the core."

## Taxonomy examples

Six scenarios exercising different parts of the taxonomy — three write-side, three read-side. Use these to verify your understanding before naming a new model.

### Write-side examples

#### Scenario A: Location (nested, read differs from core, same add/edit shape)

> Locations are nested inside tasks — not a standalone tool. A location has: `name` (string), `latitude` (float), `longitude` (float), `radius` (int, defaults to 100 meters).
>
> Read output (radius is default → suppressed):
> ```json
> {"name": "Office", "latitude": 37.7749, "longitude": -122.4194}
> ```
> Read output (radius is non-default → included):
> ```json
> {"name": "Office", "latitude": 37.7749, "longitude": -122.4194, "radius": 200}
> ```
> Write input (same shape for add and edit):
> ```json
> {"name": "Office", "latitude": 37.7749, "longitude": -122.4194, "radius": 200}
> ```

**Answer:** 3 models.

| Model | Category | Location | Base class | Why |
|-------|----------|----------|------------|-----|
| `Location` | Core | `models/` | `OmniFocusBaseModel` | Canonical representation, `radius` defaults to 100 |
| `LocationRead` | Read | `models/` | `OmniFocusBaseModel` | Read output suppresses default radius — different shape than core |
| `LocationSpec` | Write-side value object | `contracts/` | `CommandModel` | Nested setter; same shape for add/edit → no verb qualifier |

#### Scenario B: Priority (nested, read matches core, add/edit shapes differ)

> Priorities are nested inside tasks — not a standalone tool. A priority has: `level` (string), `score` (int).
>
> Read output:
> ```json
> {"level": "high", "score": 85}
> ```
> Write input for add (all fields required):
> ```json
> {"level": "high", "score": 85}
> ```
> Write input for edit (patch — only provide what changes):
> ```json
> {"level": "critical"}
> ```

**Answer:** 3 models. No `PriorityRead` — read shape matches core.

| Model | Category | Location | Base class | Why |
|-------|----------|----------|------------|-----|
| `Priority` | Core (also serves as read) | `models/` | `OmniFocusBaseModel` | Canonical representation, read shape is identical |
| `PriorityAddSpec` | Write-side value object | `contracts/` | `CommandModel` | All-required shape for add |
| `PriorityEditSpec` | Write-side value object | `contracts/` | `CommandModel` | Patchable shape for edit — shapes diverge → verb qualifier |

#### Scenario C: Reminder (top-level tool, full pipeline)

> `Reminder` is a new entity with its own tools: `add_reminders` and `edit_reminders`. Goes through the full three-layer architecture (server → service → repository). A reminder has: `id` (string), `message` (string), `triggerAt` (datetime).
>
> Read output:
> ```json
> {"id": "rem_abc123", "message": "Call dentist", "triggerAt": "2026-04-01T09:00:00Z"}
> ```
> Write input for `add_reminders`:
> ```json
> {"message": "Call dentist", "triggerAt": "2026-04-01T09:00:00Z"}
> ```
> Write input for `edit_reminders` (patch semantics):
> ```json
> {"id": "rem_abc123", "triggerAt": "2026-04-15T09:00:00Z"}
> ```

**Answer:** 9 models. No `ReminderRead` — read shape matches core. No nested specs — fields sit directly on the commands.

| Model | Category | Location | Base class |
|-------|----------|----------|------------|
| `Reminder` | Core (also serves as read) | `models/` | `OmniFocusBaseModel` |
| `AddReminderCommand` | Agent boundary, inbound | `contracts/` | `CommandModel` |
| `EditReminderCommand` | Agent boundary, inbound | `contracts/` | `CommandModel` |
| `AddReminderResult` | Agent boundary, outbound | `contracts/` | `OmniFocusBaseModel` |
| `EditReminderResult` | Agent boundary, outbound | `contracts/` | `OmniFocusBaseModel` |
| `AddReminderRepoPayload` | Repo boundary, inbound | `contracts/` | `CommandModel` |
| `EditReminderRepoPayload` | Repo boundary, inbound | `contracts/` | `CommandModel` |
| `AddReminderRepoResult` | Repo boundary, outbound | `contracts/` | `OmniFocusBaseModel` |
| `EditReminderRepoResult` | Repo boundary, outbound | `contracts/` | `OmniFocusBaseModel` |

### Read-side examples

#### Scenario D: Filtered task listing (full read pipeline)

> `list_tasks` is a read operation with filters. Goes through the full three-layer architecture (server → service → repository). The agent can filter by flagged, tags, project, search term, and limit. Tag filters accept names or IDs. Unrecognized names produce "did you mean?" warnings in the response.
>
> Query input:
> ```json
> {"flagged": true, "tags": ["Work"], "limit": 10}
> ```
> Result:
> ```json
> {"items": [...], "total_count": 47, "warnings": ["Tag 'Wrk' not found — did you mean 'Work'?"]}
> ```

**Answer:** 4 models. Input models split at the service boundary; result containers use shared generics.

| Model | Category | Location | Base class | Why |
|-------|----------|----------|------------|-----|
| `ListTasksQuery` | Agent-facing query | `contracts/use_cases/` | `QueryModel` | Validated filter + pagination from the agent |
| `ListTasksRepoQuery` | Repo-facing query | `contracts/use_cases/` | `QueryModel` | Resolved, repo-ready parameters — separate type even if fields are identical today |
| `ListResult[Task]` | Agent-facing result | `contracts/use_cases/` | `OmniFocusBaseModel` | Generic container with items + total_count + warnings |
| `ListRepoResult[Task]` | Repo-facing result | `contracts/use_cases/` | `OmniFocusBaseModel` | Generic container with items + total_count, no warnings |

#### Scenario E: Simple get by ID (no query model)

> `get_task` looks up a single task by its ID. Takes a single string ID, returns the task.
>
> Input:
> ```
> get_task("oRx3bL_UYq7")
> ```
> Output:
> ```json
> {"id": "oRx3bL_UYq7", "name": "Review Q3 roadmap", "flagged": true, "tags": [...]}
> ```

**Answer:** 0 query/result models. The ID passes as a plain string through every layer. The output is the core model directly.

| Model | Category | Location | Base class | Why |
|-------|----------|----------|------------|-----|
| `Task` | Core (also serves as read output) | `models/` | `OmniFocusBaseModel` | No query model needed — simple reads don't split |

#### Scenario F: Filtered task listing with nested filter (read pipeline + Filter)

> `list_tasks` supports date filtering across seven date dimensions (due, defer, completed, etc.). Each date field accepts three styles: semantic shortcuts (`"overdue"`, `"today"`), shorthand periods (`{"this": "w"}`, `{"last": "3d"}`), or absolute bounds (`{"after": "2026-03-01", "before": "2026-03-31"}`). The agent picks whichever style is most natural.
>
> Query input:
> ```json
> {"due": {"this": "w"}, "flagged": true, "limit": 20}
> ```
> Result:
> ```json
> {"items": [...], "total_count": 5, "warnings": []}
> ```

**Answer:** 5 models. The 4 query/result models from Scenario D, plus a `DateFilter` value object nested in the query.

| Model | Category | Location | Base class | Why |
|-------|----------|----------|------------|-----|
| `ListTasksQuery` | Agent-facing query | `contracts/use_cases/` | `QueryModel` | Validated filter + pagination — `due`, `defer`, etc. each accept a `DateFilter` |
| `DateFilter` | Read-side value object | `contracts/use_cases/` | `QueryModel` | Nested filter with three input shapes (shortcut, period, bounds) — reused across 7 date dimensions |
| `ListTasksRepoQuery` | Repo-facing query | `contracts/use_cases/` | `QueryModel` | Resolved, repo-ready — date filters flattened to concrete `after`/`before` timestamps |
| `ListResult[Task]` | Agent-facing result | `contracts/use_cases/` | `OmniFocusBaseModel` | Generic container with items + total_count + warnings |
| `ListRepoResult[Task]` | Repo-facing result | `contracts/use_cases/` | `OmniFocusBaseModel` | Generic container with items + total_count, no warnings |
