# Model Taxonomy

CQRS/DDD-inspired naming taxonomy for all Pydantic models in OmniFocus Operator.

## Foundational split

`models/` = what OmniFocus IS (domain entities, `OmniFocusBaseModel`). `contracts/` = what you can DO (operations, boundaries, `CommandModel` with `extra="forbid"`). Never embed a `models/` class directly in a `contracts/` command — the base class difference (`extra="forbid"`) means write-side models always need their own class, even with identical fields.

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
| `CommandModel` | Write | Commands, payloads, results, specs, actions | `AddTaskCommand`, `EditTaskRepoPayload`, ... |
| `QueryModel` | Read | Query filters and pagination | `ListTasksQuery`, `ListProjectsQuery`, ... |

This follows CQRS convention: **commands** change state, **queries** request information. Both need strict input validation at the agent boundary, but they serve different architectural roles and have different pipeline characteristics (see [Why query models are shared across layers](#why-query-models-are-shared-across-layers)).

## Overview

Every model's name indicates its layer and role. The taxonomy follows CQRS: **write-side** models (commands, payloads, results, specs) and **read-side** models (queries, result containers, output variants) have distinct conventions and base classes. Both sides share strict input validation via `StrictModel`.

**Core model as gravitational center:** The core model (no suffix, `models/`) is the canonical representation of each concept. Every boundary model relates to it directionally:

- **Inbound (write):** A write spec is **constructable** into a core model instance — spec fields map to core fields, with service-supplied defaults and resolution.
- **Outbound (read):** A read output model is **derivable** from a core model instance — transformation may suppress defaults, add computed fields, or reshape for ergonomics.
- **Query (read filters):** A query model defines selection criteria that produce a filtered collection of core model instances. It doesn't mirror the core model's shape — it specifies constraints.

Neither direction requires lossless round-tripping. The core model is the source of truth; boundary models are projections. See [Structure Over Discipline](structure-over-discipline.md) for why this is pre-documented rather than left to agent judgment.

## Core models

The canonical representation of each concept — no suffix, lives in `models/`, inherits `OmniFocusBaseModel`. Used internally by service, parser, builder. Also serves as the read output model by default (see [Output models](#output-models) for when this changes).

| Suffix | Role | Examples |
|--------|------|---------|
| No suffix | Canonical domain entity or value object | `Task`, `Project`, `Tag`, `Frequency`, `RepetitionRule` |

## Write-side models

All write-side models live in `contracts/`, inherit `CommandModel`.

### Agent boundary (agent ↔ service)

| Suffix | Role | Direction | Examples |
|--------|------|-----------|---------|
| `<verb><noun>Command` | Top-level write instruction | Inbound | `AddTaskCommand`, `EditTaskCommand` |
| `<verb><noun>Result` | Outcome returned to agent | Outbound | `AddTaskResult`, `EditTaskResult` |

### Repository boundary (service ↔ repository)

| Suffix | Role | Direction | Examples |
|--------|------|-----------|---------|
| `<verb><noun>RepoPayload` | Processed, bridge-ready data | Inbound | `AddTaskRepoPayload`, `EditTaskRepoPayload` |
| `<verb><noun>RepoResult` | Minimal confirmation from bridge | Outbound | `AddTaskRepoResult`, `EditTaskRepoResult` |

### Value objects (nested within commands)

| Suffix | Role | When to use | Examples |
|--------|------|-------------|---------|
| `<noun>Action` | Stateful mutation in the actions block | Nested operation that mutates relative to current state | `TagAction`, `MoveAction` |
| `<noun>Spec` | Write-side value object (desired state) | Nested setter with different shape from its read counterpart | `RepetitionRuleAddSpec`, `RepetitionRuleEditSpec` |

## Read-side models

**Boundary adaptation principle:** `Spec` is to `Command` what `Read` is to `Query`. Both exist to enable fluent interaction with the core model at different boundaries — `Spec` adapts nested shapes for input ergonomics (what the agent sends), `Read` adapts nested shapes for output ergonomics (what the agent receives). The core model is the canonical representation; boundary variants provide the shapes that make each direction natural.

The full parallel:

| Concern | Write-side | Read-side |
|---------|-----------|-----------|
| Top-level contract | `<verb><noun>Command` | `List<Noun>Query` |
| Nested shape variant | `<noun>Spec` — adapts input for complex fields | `<noun>Read` — adapts output for complex fields |
| Base class | `CommandModel` | `QueryModel` (query), `OmniFocusBaseModel` (output) |
| Lives in | `contracts/` | `contracts/` (query), `models/` (output) |

### Query models (input)

Query models live in `contracts/use_cases/`, inherit `QueryModel`. They carry filter parameters and pagination through the full pipeline (server → service → repository).

| Suffix | Role | Examples |
|--------|------|---------|
| `List<Noun>Query` | Validated filter + pagination parameters | `ListTasksQuery`, `ListProjectsQuery`, `ListTagsQuery`, `ListFoldersQuery` |

### Output models

The core model serves directly as read output by default. When the output boundary needs a different shape (suppressed defaults, computed fields, reshaped for ergonomics), introduce a `<noun>Read` variant — separate class, not a subclass, derivable from the core model.

| Suffix | Role | Examples |
|--------|------|---------|
| Core model (no suffix) | Default read output — used when shape matches | `Task`, `Project`, `Tag` |
| `<noun>Read` | Output-boundary variant, derivable from core | `FrequencyRead` (hypothetical — not yet needed) |

**Why "suppressed defaults" can't stay on the core model:** FastMCP serializes tool output via `pydantic_core.to_jsonable_python`, which has no `exclude_defaults` parameter. You don't control the serialization call. A `@field_serializer` on the parent can work as a workaround (see `RepetitionRule.frequency`), but when the concept is used in multiple places or the suppression is intrinsic to the read representation, a `<noun>Read` with the behavior built in is the principled path.

### Result container

| Model | Role | Base class | Examples |
|-------|------|------------|---------|
| `ListResult[T]` | Generic result container (items + total_count) | `OmniFocusBaseModel` | `ListResult[Task]`, `ListResult[Project]` |

`ListResult[T]` inherits `OmniFocusBaseModel`, not `QueryModel` — it's outbound and system-constructed, not validated against agent input. The `T` is a core model or `<noun>Read` variant.

### Why query models are shared across layers

Write-side models need separate types at each boundary because the **shape genuinely changes** between layers:

```
AddTaskCommand          →  Service transforms  →  AddTaskRepoPayload
  parent: str (name)         resolves, builds        parent_id: str (ID)
  tags: ["Work"]             restructures            tag_ids: ["id1"]
  (agent-friendly shape)                             (bridge-ready shape)
```

Read-side query models don't need this split because the **shape stays the same**. Service resolves values (tag names → IDs, status shorthand expansion, default exclusions) but the model structure is identical before and after:

```
ListTasksQuery          →  Service refines    →  ListTasksQuery (same model)
  tags: ["Work"]             resolves values       tags: ["id1"]
  flagged: true              applies defaults      flagged: true
  (same fields, same types throughout)
```

The fundamental difference: writes are **transformative** (command → payload requires restructuring for the bridge), reads are **refinements** (filter values get resolved but the contract shape is stable). A separate `ListTasksRepoQuery` would duplicate 95% of the fields for the sake of one resolved value — the wrong tradeoff.

This mirrors how existing simple reads already work: `get_task(task_id: str)` passes the same string through every layer without a `GetTaskRepoQuery`.

## Naming rules

- **Verb-first** for top-level write-side models: `<verb><noun>Command` — e.g., `AddTaskCommand`, `EditTaskCommand` (not `TaskAddCommand`)
- **Write-side verb matches tool verb**: tool is `add_tasks` → models are `AddTask*`; tool is `edit_tasks` → models are `EditTask*`
- **Noun-only** for core models: `Task`, `Project`, `Tag` (no verb, no suffix)
- **Value objects** within commands are suffix-free when unambiguous (`TagAction`, `MoveAction`), or use `<noun>Spec` when a read-side model of the same name exists. All value objects live in `contracts/` and inherit `CommandModel` — never reuse a read model from `models/` directly in a command
- **Base classes**: `CommandModel` for write-side, `QueryModel` for read-side queries — both inherit `StrictModel` (`extra="forbid"`, strict validation). `ListResult` inherits `OmniFocusBaseModel` (outbound, no strict validation)
- **Repo qualifier**: Both inbound and outbound models at the repository boundary use `Repo` prefix for symmetry and clarity
- **Noun-first for nested specs**: When a nested value object needs a verb qualifier (different shapes per use case), the domain noun leads: `RepetitionRuleAddSpec`, `RepetitionRuleEditSpec` (not `AddRepetitionRuleSpec`). Top-level models are verb-first (`AddTaskCommand`); nested specs are noun-first because they represent the THING in different contexts, not different actions.
- **Verb qualifier only when needed**: If a spec has the same shape for both add and edit, use plain `<noun>Spec` (no verb). Only add `Add`/`Edit` qualifier when shapes diverge (e.g., all-required vs patchable fields).
- **Read suffix only when needed**: Use the core model directly for read output (the common case). Only introduce `<noun>Read` when the output boundary requires a different shape. A `<noun>Read` is a separate class (not a subclass of the core model), inherits `OmniFocusBaseModel`, lives in `models/`, and must be derivable from the core model.

## Decision tree for naming a new model

**Read-side:**

*Query input* (lives in `contracts/use_cases/`, inherits `QueryModel`):

1. Is it a validated filter + pagination model for a list operation? → `List<Noun>Query` (e.g., `ListTasksQuery`)
2. Is it a result container for list operations? → `ListResult[T]` (inherits `OmniFocusBaseModel`, not `QueryModel` — outbound, no validation needed)

*Query output* (lives in `models/`, inherits `OmniFocusBaseModel`):

3. Is the read output shape identical to the core model? → Use the core model directly (no suffix)
4. Does the read output need a different shape (suppressed defaults, computed fields, reshaped for ergonomics)? → `<noun>Read` (separate class, derivable from core)

**Write-side** (lives in `contracts/`, inherits `CommandModel`):

1. Is it a top-level instruction from the agent? → `<verb><noun>Command`
2. Is it processed data sent to the repository? → `<verb><noun>RepoPayload`
3. Is it a stateful operation inside the actions block? → `<noun>Action`
4. Is it a complex nested value object (setter, not a mutation)? → `<noun>Spec`
   Write models inherit `CommandModel`, read output models inherit
   `OmniFocusBaseModel` (no `extra="forbid"`). This base class difference alone justifies
   a dedicated write model, even when the field shapes are identical.
     - Same shape across add/edit → `<noun>Spec` (e.g., `RepetitionRuleSpec`)
     - Different shapes per use case → `<noun><verb>Spec` (e.g., `RepetitionRuleAddSpec` for all-required, `RepetitionRuleEditSpec` for patchable fields)
5. Is it the confirmation from the repository? → `<verb><noun>RepoResult`
6. Is it the enriched outcome returned to the agent? → `<verb><noun>Result`

## Ubiquitous language

> "The agent sends a **command** (write) or a **query** (read). For writes: the service validates, resolves, and builds a **repo payload**. The repository forwards to the bridge and returns a **repo result**. The service enriches this into a **result** for the agent. Within a command, **actions** mutate state; **specs** describe desired state for complex nested objects. When a spec needs different shapes per use case, the domain noun leads with a verb qualifier: RepetitionRuleAddSpec (creation shape) vs RepetitionRuleEditSpec (partial update shape). For filtered reads: the agent sends a **query** that travels unchanged through all layers — the service refines values but doesn't reshape. The repository returns a **list result** with items and total count. For read output, the **core model** is used directly unless the output boundary needs a different shape — then a **read model** (`<noun>Read`) provides the variant, derivable from the core."

## Taxonomy examples

Four scenarios exercising different parts of the taxonomy. Use these to verify your understanding before naming a new model.

### Scenario A: Location (nested, read differs from core, same add/edit shape)

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

### Scenario B: Priority (nested, read matches core, add/edit shapes differ)

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

### Scenario C: Reminder (top-level tool, full pipeline)

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
| `AddReminderResult` | Agent boundary, outbound | `contracts/` | `CommandModel` |
| `EditReminderResult` | Agent boundary, outbound | `contracts/` | `CommandModel` |
| `AddReminderRepoPayload` | Repo boundary, inbound | `contracts/` | `CommandModel` |
| `EditReminderRepoPayload` | Repo boundary, inbound | `contracts/` | `CommandModel` |
| `AddReminderRepoResult` | Repo boundary, outbound | `contracts/` | `CommandModel` |
| `EditReminderRepoResult` | Repo boundary, outbound | `contracts/` | `CommandModel` |

### Scenario D: Filtered task listing (query, shared across layers)

> `list_tasks` is a read operation with filters. The agent sends filter parameters (flagged, tags, search, limit). The same query model travels through server → service → repository — the service resolves tag names to IDs and applies default exclusions, but the model shape doesn't change. Repository returns `ListResult[Task]`.
>
> Query input:
> ```json
> {"flagged": true, "tags": ["Work"], "limit": 10}
> ```
> Result:
> ```json
> {"items": [...], "total_count": 47}
> ```

**Answer:** 2 models. No separate repo-boundary query model — shape doesn't change between layers (see [Why query models are shared across layers](#why-query-models-are-shared-across-layers)).

| Model | Category | Location | Base class | Why |
|-------|----------|----------|------------|-----|
| `ListTasksQuery` | Query contract | `contracts/use_cases/` | `QueryModel` | Validated filter + pagination, shared across all layers |
| `ListResult[Task]` | Result container | `contracts/use_cases/` | `OmniFocusBaseModel` | Generic outbound container — not agent input, no `extra="forbid"` |
