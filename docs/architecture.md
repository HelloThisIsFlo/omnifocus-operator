# Architecture Overview

## Layer Diagram

```mermaid
graph TB
    Agent["🤖 AI Agent"]
    Server["server.py<br/>MCP Tool Handlers"]
    Service["service.py<br/>Validation · Resolution · Delegation"]
    Repo["Repository Protocol"]
    Hybrid["HybridRepository<br/>SQLite reads + Bridge writes"]
    BridgeRepo["BridgeRepository<br/>Bridge for reads + writes"]
    InMem["InMemoryRepository<br/>Testing"]
    SQLite["SQLite Cache<br/>~46ms reads"]
    Bridge["Bridge<br/>OmniJS IPC"]
    OF["OmniFocus"]

    Agent -->|JSON| Server
    Server -->|"Command / Result"| Service
    Service -->|"RepoPayload / RepoResult"| Repo
    Repo --- Hybrid
    Repo --- BridgeRepo
    Repo --- InMem
    Hybrid -->|reads| SQLite
    Hybrid -->|writes| Bridge
    BridgeRepo --> Bridge
    Bridge -->|File IPC| OF
    SQLite -.->|"OmniFocus writes → WAL updates"| OF
```

## Package Structure

```
omnifocus_operator/
    contracts/       -- Typed boundaries: protocols, commands, payloads, results
        protocols.py     -- Service, Repository, Bridge — all boundaries in one file
        base.py          -- CommandModel, UNSET sentinel
        common.py        -- Shared value objects (TagAction, MoveAction)
        use_cases/       -- One module per operation
            create_task.py   -- AddTaskCommand, AddTaskRepoPayload, AddTaskRepoResult, AddTaskResult
            edit_task.py     -- EditTaskCommand, EditTaskActions, EditTaskRepoPayload, EditTaskRepoResult, EditTaskResult
    models/          -- Read-side domain models (entities, enums, value objects)
    bridge/          -- OmniFocus communication (IPC, in-memory, simulator)
    repository/      -- Data access implementations + factory
    simulator/       -- Mock OmniFocus simulator for IPC testing
    server.py        -- FastMCP tool registration + wiring
    service/         -- Validation, resolution, domain logic, delegation
        service.py       -- Thin orchestrator (OperatorService)
        resolve.py       -- Entity resolution (parent, tags, task)
        validate.py      -- Pure input validation
        domain.py        -- Business rules (lifecycle, tags, cycle, no-op, move)
        payload.py       -- Typed repo payload construction
    agent_messages/  -- Agent-facing communication surface (warnings + errors)
        warnings.py      -- Centralized warning constants
        errors.py        -- Centralized error message constants
```

**Split principle:** `models/` = what OmniFocus IS (domain entities, `OmniFocusBaseModel`). `contracts/` = what you can DO (operations, boundaries, `CommandModel` with `extra="forbid"`). Everything else = how it's done (implementations). Never embed a `models/` class directly in a `contracts/` command — the base class difference (`extra="forbid"`) means write-side models always need their own class, even with identical fields.

## Dependency Direction

```mermaid
graph LR
    server["server.py"]
    service["service.py"]
    contracts["contracts/"]
    models["models/"]
    repository["repository/"]
    bridge["bridge/"]

    server --> contracts
    server --> repository
    server --> bridge
    service --> contracts
    repository --> contracts
    repository --> bridge
    contracts --> models
```

- `contracts/` → `models/` (protocols reference domain entities)
- `service.py` → `contracts/` (protocols + commands + payloads + results)
- `server.py` → `contracts/` + concrete implementations (wiring only)
- `repository/` → `contracts/` (protocols + repo payloads + repo results) + `bridge/` (for writes)
- `repository/in_memory.py` → `contracts/` + `models/` only (zero bridge dependency)
- `models/` → nothing (leaf package, no outward dependencies except Pydantic)

## Protocols

All protocols live in `contracts/protocols.py` — one file shows every typed boundary in the system.

### Service protocol (agent ↔ service)

```python
class Service(Protocol):
    # Reads — return domain entities
    async def get_all_data(self) -> AllEntities: ...
    async def get_task(self, task_id: str) -> Task | None: ...
    async def get_project(self, project_id: str) -> Project | None: ...
    async def get_tag(self, tag_id: str) -> Tag | None: ...
    # Writes — take commands, return results
    async def add_task(self, command: AddTaskCommand) -> AddTaskResult: ...
    async def edit_task(self, command: EditTaskCommand) -> EditTaskResult: ...
```

### Repository protocol (service ↔ repository)

Three implementations: HybridRepository (production), BridgeRepository (fallback), InMemoryRepository (tests).

```python
class Repository(Protocol):
    # Reads — return domain entities
    async def get_all(self) -> AllEntities: ...
    async def get_task(self, task_id: str) -> Task | None: ...
    async def get_project(self, project_id: str) -> Project | None: ...
    async def get_tag(self, tag_id: str) -> Tag | None: ...
    # Writes — take repo payloads, return repo results
    async def add_task(self, payload: AddTaskRepoPayload) -> AddTaskRepoResult: ...
    async def edit_task(self, payload: EditTaskRepoPayload) -> EditTaskRepoResult: ...
```

### Bridge protocol (repository ↔ OmniFocus)

```python
class Bridge(Protocol):
    async def send_command(self, operation: str, params: dict[str, Any] | None = None) -> dict[str, Any]: ...
```

## Write Pipeline

```mermaid
sequenceDiagram
    participant A as Agent
    participant S as Server
    participant Svc as Service
    participant R as Repository
    participant B as Bridge
    participant OF as OmniFocus

    A->>S: JSON payload
    S->>Svc: AddTaskCommand
    Note over Svc: validate · resolve · build payload
    Svc->>R: AddTaskRepoPayload
    Note over R: model_dump() → dict
    R->>B: dict
    B->>OF: File IPC
    OF-->>B: result dict
    B-->>R: {id, name}
    R-->>Svc: AddTaskRepoResult
    Note over Svc: enrich (add success, warnings)
    Svc-->>S: AddTaskResult
    S-->>A: JSON response
```

- **Service** does ALL processing: validation, parent/tag resolution, tag diff, move transformation, date serialization, no-op detection
- **Repository** is a pure pass-through: `model_dump()` → `send_command()` → wrap result
- **Bridge** is a dumb relay: receives pre-validated dicts, executes, returns minimal confirmation
- Parent resolution: try `get_project` first, then `get_task` — **project takes precedence** (intentional, deterministic)
- HybridRepository marks stale after write; BridgeRepository clears cache

### Method Object Pattern (complex pipelines)

When a service method has many sequential steps with intermediate state, we use the **Method Object** pattern: extract the method body into a short-lived class where each step is a named method and intermediate values live on `self`.

**Why:** Familiarity vs readability. A 100-line method with 12 local variables and numbered comments is *familiar* but forces you to track all state simultaneously. A Method Object with a 12-line `execute()` method and 3-8 line steps is *readable* — each step is self-contained, named, navigable, and shows up in stack traces.

**How it works:**

```python
# Orchestrator stays thin -- one-liner delegation
async def edit_task(self, command: EditTaskCommand) -> EditTaskResult:
    pipeline = _EditTaskPipeline(self._resolver, self._domain, self._payload, self._repository)
    return await pipeline.execute(command)

# Pipeline reads like a table of contents
class _EditTaskPipeline:
    async def execute(self, command):
        await self._verify_task_exists()
        self._validate_and_normalize()
        self._detect_action_flags()
        self._apply_lifecycle()
        ...
```

**When to use:** All service-layer use cases — not just complex ones. The pattern makes any orchestration method self-documenting. Even `add_task` (5 steps) reads better as a pipeline than inline code with variables flowing between steps. The value is self-documenting orchestration, not complexity management.

**Conventions:**
- All pipelines inherit from `_Pipeline` (shared DI constructor)
- Class name: `_VerbNounPipeline` (private, underscore prefix) — e.g., `_AddTaskPipeline`, `_EditTaskPipeline`
- Constructor receives DI dependencies; `execute()` receives the input
- Mutable state on `self` is acceptable — the object is created, executed, and discarded within a single call. The lifetime is bounded.
- Step methods are private (`_verify_task_exists`, not `verify_task_exists`)
- Read delegation methods (get_task, get_project, etc.) stay inline on OperatorService — they're one-liner pass-throughs, not pipelines

## Read Pipeline

```mermaid
sequenceDiagram
    participant A as Agent
    participant S as Server
    participant Svc as Service
    participant R as Repository
    participant SQLite as SQLite Cache
    participant B as Bridge
    participant OF as OmniFocus

    A->>S: get_all / get_task / get_project / get_tag
    S->>Svc: delegate
    Svc->>R: delegate

    alt HybridRepository (default)
        R->>SQLite: SQL query (~46ms full snapshot)
        SQLite-->>R: rows
        Note over R: map rows → domain entities
    else BridgeRepository (fallback)
        R->>B: send_command("get_all")
        B->>OF: File IPC
        OF-->>B: JSON dump
        B-->>R: raw dict
        Note over R: adapt → domain entities
    end

    R-->>Svc: AllEntities / Task / Project / Tag
    Svc-->>S: pass through
    S-->>A: JSON response
```

### Caching

- **HybridRepository** (default): SQLite cache, ~46ms full snapshot, OmniFocus not required
  - WAL-based freshness detection: 50ms poll, 2s timeout after writes
  - No caching layer on top — 46ms is fast enough
  - Marks stale after writes; next read waits for fresh WAL mtime
- **BridgeRepository** (fallback via `OMNIFOCUS_REPOSITORY=bridge`): OmniJS bridge dump
  - mtime-based cache invalidation; checks file mtime before each read, serves cached snapshot if unchanged
  - Concurrent reads coalesce into a single bridge dump
- **InMemoryRepository** (tests): no caching (returns constructor snapshot as-is)

## Naming Conventions

### MCP tool verbs

Write tools use domain-native verbs, not CRUD:

| Verb | Operation | Examples |
|------|-----------|---------|
| `add_*` | Introduce a new entity into OmniFocus | `add_tasks`, future `add_projects` |
| `edit_*` | Modify an existing entity | `edit_tasks`, future `edit_projects` |
| `delete_*` | Remove an entity | future `delete_tasks` |
| `get_*` | Look up a single entity by ID | `get_task`, `get_project`, `get_tag` |
| `list_*` | Filtered collection of one entity type | future `list_tasks`, `list_projects` |
| `count_*` | Count entities matching a filter | future `count_tasks` |

**Why "add" not "create":** Deliberate decision after extensive analysis. "Add" is the natural verb for task management ("add a task to my inbox"), matches OmniJS domain language, and forms a coherent verb system (add/edit/delete). "Create" is standard CRUD but sounds formal for the most common operation (tasks). Tool descriptions use natural language freely — e.g., `add_tasks` description can say "Create tasks in OmniFocus" — the tool name is the technical identifier, the description is the UX.

### Method names

- `get_all()` → `AllEntities`: structured container with all entity types
- `get_*` by ID → single entity lookup
- `list_*(filters)` → flat list of one entity type (e.g., `list_tasks(status=...)`) — planned for v1.3
- `add_*` / `edit_*` → write operations
- `get_*` = heterogeneous structured return; `list_*` = homogeneous filtered collection
- `AllEntities` (not `DatabaseSnapshot`) — no caching/snapshot semantics at the protocol level

### Model taxonomy (CQRS/DDD-inspired)

Write-side models follow a CQRS/DDD-inspired naming convention. Every model's name indicates its layer and role. Read-side models (entities, value objects) use bare names with no suffix.

#### Agent boundary (agent ↔ service)

| Suffix | Role | Direction | Examples |
|--------|------|-----------|---------|
| `___Command` | Top-level write instruction | Inbound | `AddTaskCommand`, `EditTaskCommand` |
| `___Result` | Outcome returned to agent | Outbound | `AddTaskResult`, `EditTaskResult` |

#### Repository boundary (service ↔ repository)

| Suffix | Role | Direction | Examples |
|--------|------|-----------|---------|
| `___RepoPayload` | Processed, bridge-ready data | Inbound | `AddTaskRepoPayload`, `EditTaskRepoPayload` |
| `___RepoResult` | Minimal confirmation from bridge | Outbound | `AddTaskRepoResult`, `EditTaskRepoResult` |

#### Value objects (nested within commands)

| Suffix | Role | When to use | Examples |
|--------|------|-------------|---------|
| `___Action` | Stateful mutation in the actions block | Nested operation that mutates relative to current state | `TagAction`, `MoveAction` |
| `___Spec` | Write-side value object (desired state) | Nested setter with different shape from its read counterpart | `RepetitionRuleAddSpec`, `RepetitionRuleEditSpec` |

#### Read-side models

| Suffix | Role | Examples |
|--------|------|---------|
| No suffix | Domain entity or shared value object | `Task`, `Project`, `Tag`, `TagRef`, `RepetitionRule` |

#### Naming rules

- **Verb-first** for top-level write-side models: `AddTask___`, `EditTask___` (not `TaskAdd___`)
- **Write-side verb matches tool verb**: tool is `add_tasks` → models are `AddTask*`; tool is `edit_tasks` → models are `EditTask*`
- **Noun-only** for read entities: `Task`, `Project`, `Tag` (no verb, no suffix)
- **Value objects** within commands are suffix-free when unambiguous (`TagAction`, `MoveAction`), or use `___Spec` when a read-side model of the same name exists. All value objects live in `contracts/` and inherit `CommandModel` — never reuse a read model from `models/` directly in a command
- **Base class**: `CommandModel` — all command-layer models inherit this (`extra="forbid"`, strict validation)
- **Repo qualifier**: Both inbound and outbound models at the repository boundary use `Repo` prefix for symmetry and clarity
- **Noun-first for nested specs**: When a nested value object needs a verb qualifier (different shapes per use case), the domain noun leads: `RepetitionRuleAddSpec`, `RepetitionRuleEditSpec` (not `AddRepetitionRuleSpec`). Top-level models are verb-first (`AddTaskCommand`); nested specs are noun-first because they represent the THING in different contexts, not different actions.
- **Verb qualifier only when needed**: If a spec has the same shape for both add and edit, use plain `___Spec` (no verb). Only add `Add`/`Edit` qualifier when shapes diverge (e.g., all-required vs patchable fields).

#### Decision tree for naming a new write-side model

1. Is it a top-level instruction from the agent? → `___Command`
2. Is it processed data sent to the repository? → `___RepoPayload`
3. Is it a stateful operation inside the actions block? → `___Action`
4. Is it a complex nested value object (setter, not a mutation)? → `___Spec`
   Write models always inherit `CommandModel` (`extra="forbid"`), read models inherit
   `OmniFocusBaseModel` (no `extra="forbid"`). This base class difference alone justifies
   a dedicated write model, even when the field shapes are identical.
     - Same shape across add/edit → `NounSpec` (e.g., `RepetitionRuleSpec`)
     - Different shapes per use case → `NounVerbSpec` (e.g., `RepetitionRuleAddSpec` for all-required, `RepetitionRuleEditSpec` for patchable fields)
5. Is it the confirmation from the repository? → `___RepoResult`
6. Is it the enriched outcome returned to the agent? → `___Result`

#### Ubiquitous language

> "The agent sends a **command**. The service validates, resolves, and builds a **repo payload**. The repository forwards to the bridge and returns a **repo result**. The service enriches this into a **result** for the agent. Within a command, **actions** mutate state; **specs** describe desired state for complex nested objects. When a spec needs different shapes per use case, the domain noun leads with a verb qualifier: RepetitionRuleAddSpec (creation shape) vs RepetitionRuleEditSpec (partial update shape)."

## Dumb Bridge, Smart Python

The most important architectural invariant: **the bridge is a relay, not a brain**. All validation, resolution, diff computation, and business logic lives in Python. The bridge script receives pre-validated payloads and executes them without interpretation.

### Why

- **OmniJS freezes the UI.** Every line of bridge logic is user-visible latency — scanning 2,825 tasks takes ~1,264ms during which OmniFocus is unresponsive
- **OmniJS is quirky.** Opaque enums, unreliable batch operations, null rejection — the runtime has sharp edges that are painful to debug
- **Python is testable.** 534 pytest tests cover service logic, adapter transformations, and repository behavior. Bridge.js has 26 Vitest tests for basic relay correctness — that's the right ratio
- **Python is typed.** Pydantic models, mypy strict mode, and structured error handling catch issues at development time, not at 7:30am in production

### Known OmniJS Quirks

These are concrete examples of why logic stays out of the bridge:

- **`removeTags(array)` is unreliable** — bridge works around this by removing tags one at a time in a loop instead of batch (`bridge.js`, `handleEditTask`)
- **`note = null` is rejected** — OmniFocus API requires empty string to clear notes. Service maps `null → ""` before building the repo payload
- **Enums are opaque objects** — `.name` returns `undefined`. Only `===` comparison against known constants works. Bridge does minimal enum-to-string resolution and throws on unknowns (`bridge.js`, enum resolvers)
- **Same-container moves are no-ops** — `beginning`/`ending` moves within the same container don't reorder. Service detects this and warns with a workaround
- **Blocking state is invisible** — bridge cannot determine sequential dependencies or parent-child blocking. Only SQLite has full availability data (`BRIDGE-SPEC.md:FALL-02`)

### What Lives Where

| Concern | Where | Why |
|---------|-------|-----|
| Enum-to-string resolution | Bridge | Must happen at source (opaque objects) |
| Tag name-to-ID resolution | Service | Case-insensitive matching, ambiguity errors |
| Tag diff computation | Service | Minimal add/remove sets, no-op warnings |
| Cycle detection (moves) | Service | Parent chain walk on cached snapshot — instant |
| No-op detection + warnings | Service | Field comparison before bridge delegation |
| Null-means-clear mapping | Service | Business logic, not transport |
| RRULE string generation | Service | Structured fields → RRULE string (see [RRULE Utility Layer](#rrule-utility-layer)) |
| Lifecycle (complete/drop) | Service + Bridge | Service validates state, bridge executes `markComplete()`/`drop()` |
| Validation (all of it) | Service | Three layers, all before bridge call |

### The Result

The bridge is ~400 lines of trivial relay code. The rest of the project is ~14,000 lines of validated, typed, tested Python. That's the right split.

## Show-More Principle

In a task manager, error costs are asymmetric:

- **Showing one extra task** = the user glances at it, sees it's irrelevant, moves on. Cost: near zero.
- **Missing a task** = the user doesn't know what they can't see. They miss a deadline, forget a commitment, lose trust in the tool. Cost: high.

This is the same tradeoff as tuning a classifier: the optimal bias depends on the domain. A spam filter tolerates some missed spam to avoid burying real emails — but for medical screening, you bias hard toward flagging anything suspicious, because missing a diagnosis is catastrophic while a false alarm just means more tests. Task management is closer to medical screening: the cost of a miss far outweighs the cost of showing too much.

**This asymmetry biases every ambiguous design decision toward inclusion.** When a boundary could be inclusive or exclusive, make it inclusive. When "due soon" could exclude or include overdue tasks, include them. When a time period's count is ambiguous, round toward showing more.

This is NOT "show everything." Filters are strict — `flagged: true` means flagged, `project: "Work"` means the Work project. The principle applies specifically to **boundary cases where reasonable people could argue either way.** In those cases, the tiebreaker is always: show the task.

### Applied examples

| Decision | Clean/precise option | Generous option | Chosen |
|----------|---------------------|-----------------|--------|
| `available` filter | Only strictly-available tasks | Includes `next` (first available in sequential project) | Generous |
| `blocked` filter | Only tasks blocked by other tasks | All four blocking reasons (deferred, sequential, parent, on-hold) | Generous |
| `"soon"` shorthand | Future-only window | Upper-bound threshold — overdue is a natural subset | Generous |
| Day-snapping (`{last: "3d"}`) | Exactly 3 calendar days | 3 full past days + partial today (N+1 touched) | Generous |
| `before` boundary | Exclusive (half-open, composable) | Inclusive (agents echo user's dates, it just works) | Generous |

In every case: the generous option means "you might see one extra task." The clean option means "you might miss one."

### When NOT to apply

- **Strict filters are strict.** `flagged: true`, `availability: "available"` — no fuzziness. These aren't boundary cases, they're different questions.
- **Default exclusions are intentional.** Completed/dropped tasks require an explicit filter. "Show active tasks" is a clear design choice, not an ambiguous boundary.
- **The principle is a tiebreaker**, not a blanket rule. If the answer is obviously "exclude," exclude.

## Write API Patterns

### Patch semantics (edit_tasks)

Three-way field distinction: omit = no change, null = clear, value = set.

```json
{
  "id": "abc123",
  "name": "New name",      // value → set
  "dueDate": null,         // null  → clear
                           // note  → omitted, no change
}
```

- Pydantic sentinel pattern (UNSET) distinguishes "not provided" from "explicitly null"
- Clearable fields: dates, note, estimated_minutes. Value-only: name, flagged
- Bridge payload only includes non-UNSET fields; bridge.js uses `hasOwnProperty()` to detect presence

### Task movement (actions.move)

"Key IS the position" design — the `MoveAction` has exactly one key:

```json
{"move": {"ending": "proj-123"}}       // last child of container
{"move": {"beginning": "proj-123"}}    // first child of container
{"move": {"after": "task-sibling"}}    // after this sibling (parent inferred)
{"move": {"before": "task-sibling"}}   // before this sibling (parent inferred)
{"move": {"beginning": null}}          // move to inbox
```

- Lives under `actions.move` in the `EditTaskCommand` (see [Field graduation](#field-graduation))
- One key = one position + one reference. Invalid combos are structurally impossible.
- Maps directly to OmniJS position API: `container.beginning`, `container.ending`, `task.before`, `task.after`
- Full cycle validation via SQLite parent chain walk before bridge call

### Field graduation

The edit API separates **setters** (top-level fields) from **actions** (operations that modify state):

```json
{
  "id": "xyz",
  "name": "Renamed",        // setter -- simple field replacement
  "flagged": true,           // setter
  "actions": {               // actions -- operations with richer semantics
    "tags": { "add": [...], "remove": [...] },   // or "replace": [...]
    "move": { "after": "sibling-id" },
    "lifecycle": "complete"
  }
}
```

Design principles:
- **Setters** are idempotent field replacements (top-level). Generic no-op warning when value unchanged.
- **Actions** are operations that modify relative to current state (nested under `actions`). Action-specific warnings (e.g., "Tag 'X' is already on this task").
- **Any field can graduate** from setter to action group when it needs more than simple replacement.
  - Migration path:
    1. Remove the field from top-level setters
    2. Add it as an action group under `actions` with `replace` + new operations
  - Example: `note` could graduate to `actions.note: { replace: "...", append: "..." }` when append-note is needed.
- **Tags are the first graduated field:**

  ```json
  // Before graduation (v1.2.0): top-level setter, replace-only
  { "tags": ["Work", "Planning"] }

  // After graduation (v1.2.1): action group with add/remove/replace
  { "actions": { "tags": { "add": ["Urgent"], "remove": ["Planning"] } } }
  ```

- **Each graduation is independent** — migrate one field at a time as use cases emerge.

### Agent-facing messages

All agent-facing text — warnings and errors — is centralized in `agent_messages/` with AST-based test enforcement preventing inline regressions. Agents learn from every response, so message quality is a first-class concern.

- Write results include optional `warnings` array for no-ops and edge cases
- Errors (ValueError) use the same centralized constant + `.format()` pattern as warnings
- Examples:
  - Tag no-op: "Tag 'X' was not on this task — omit remove_tags to skip"
  - Setter no-op: "Field 'flagged' is already true — omit to skip"
  - Same-container move: "Task is already in this container. Use 'before' or 'after' with a sibling task ID to control ordering."
  - Lifecycle on completed: "Task is already completed — no change made"

## Two-Axis Status Model

- Urgency: `overdue`, `due_soon`, `none` — time-based, computed from dates
- Availability: `available`, `blocked`, `completed`, `dropped` — lifecycle state
- Replaces single-winner status enum from v1.0; matches OmniFocus internal representation

## Repetition Rule: Structured Fields, Not RRULE Strings

> **Status:** Read + write models implemented (v1.2.3) — flat `Frequency` model, `parse_rrule()`, `build_rrule()`. Type optional on edits.

Agents never see RRULE strings. The read and write models expose repetition as structured fields with a flat frequency model. The RRULE string is an internal serialization detail between the service layer and the bridge.

Why top-level (not inside `actions`): setting a repetition rule is idempotent — same input always produces the same result, regardless of current state. Follows the same pattern as `due_date`, `note` — set, clear, or leave unchanged.

### Frequency Model Hierarchy

Three models, one concept:

```
Frequency(OmniFocusBaseModel)          -- domain model, canonical representation
                                          validation (cross-type, value ranges, mutual exclusion)
                                          used internally by service, parser, builder
                                          used directly for read output (in RepetitionRule.frequency)

FrequencyAddSpec(CommandModel)         -- agent input boundary for creation
                                          same fields as Frequency, extra="forbid"

FrequencyEditSpec(CommandModel)        -- agent input boundary for editing
                                          Patch/PatchOrClear fields, no validation
                                          service resolves to Frequency after merge
```

`Frequency` is the domain model — it defines what a valid frequency IS. The write specs are input boundary objects that exist only to receive and constrain agent input. The service always works with `Frequency` internally.

**Future: `FrequencyRead`** — If read output ever needs frequency-specific serialization beyond what `RepetitionRule.@field_serializer` provides, introduce `FrequencyRead(Frequency)` as a subclass. The service continues to work with `Frequency`; the read output boundary wraps in `FrequencyRead`. This keeps the domain model clean and the read-specific behavior at the output boundary. Do not add `FrequencyRead` until a concrete need arises — but when it does, this is the path.

### Repetition Rule Structure

```
repetitionRule
├── frequency                    -- flat model, 6 types + optional specialization fields
│   ├── type                     -- required on read/add, optional on edit (inferred from existing)
│   ├── interval                 -- every N of that type (default: 1, omitted in output when 1)
│   └── onDays / on / onDates    -- optional specialization (see below)
├── schedule                     -- "regularly" | "regularly_with_catch_up" | "from_completion"
├── basedOn                      -- "due_date" | "defer_date" | "planned_date"
└── end                          -- optional: {"date": "ISO-8601"} or {"occurrences": N}
```

- `schedule` — three values; collapses scheduleType + catchUpAutomatically into one field
- `basedOn` — renamed from anchorDateKey to match OmniFocus UI language ("based on due date"). See [OmniFocus Concepts](omnifocus-concepts.md#dates) for date semantics
- `end` — "key IS the value" pattern (same as [actions.move](#task-movement-actionsmove)): exactly one key, omit for no end
- `frequency.interval` — nested (tightly coupled with type: "every 2 weeks" is one concept). Omitted from read output when 1 (the default)

### Frequency Types

Six types sharing a single flat model. Optional fields specialize the base type — no sub-types needed:

| Type | Optional fields | Example |
|------|-----------------|---------|
| `minutely` | — | Every 30 minutes |
| `hourly` | — | Every 2 hours |
| `daily` | — | Every 3 days |
| `weekly` | `onDays`: `string[]` — two-letter codes (MO–SU) | Every 2 weeks; optionally on specific days |
| `monthly` | `on`: `object` — `{ordinal: dayName}`, OR `onDates`: `int[]` — day numbers (1–31, -1 = last) | Every month; optionally on nth weekday or specific dates |
| `yearly` | — | Every year |

`on` and `onDates` are mutually exclusive on `monthly` — you specify a weekday pattern OR specific dates, not both. Cross-type fields are rejected with an educational error.

```json
// weekly → onDays: array of two-letter day codes (case-insensitive, normalized to uppercase)
"onDays": ["MO", "WE", "FR"]

// monthly → on: single key-value object (reads like English: "on the second Tuesday")
// Keys: first, second, third, fourth, fifth, last
// Values: monday–sunday, weekday, weekend_day (case-insensitive, normalized to lowercase)
"on": {"second": "tuesday"}

// monthly → onDates: array of integers (1–31, -1 for last day)
"onDates": [1, 15, -1]
```

### Examples

**Daily** — every 3 days, from completion, based on defer date:
```json
{
  "repetitionRule": {
    "frequency": { "type": "daily", "interval": 3 },
    "schedule": "from_completion",
    "basedOn": "defer_date"
  }
}
```

**Weekly** — every 2 weeks on Mon and Fri, regularly with catch-up, based on due date:
```json
{
  "repetitionRule": {
    "frequency": { "type": "weekly", "interval": 2, "onDays": ["MO", "FR"] },
    "schedule": "regularly_with_catch_up",
    "basedOn": "due_date"
  }
}
```

**Monthly (nth weekday)** — the last Friday of every month, stop after 12 occurrences:
```json
{
  "repetitionRule": {
    "frequency": { "type": "monthly", "on": {"last": "friday"} },
    "schedule": "regularly",
    "basedOn": "due_date",
    "end": { "occurrences": 12 }
  }
}
```

**Monthly (specific dates)** — the 1st and 15th of every month, until a date:
```json
{
  "repetitionRule": {
    "frequency": { "type": "monthly", "onDates": [1, 15] },
    "schedule": "regularly_with_catch_up",
    "basedOn": "planned_date",
    "end": { "date": "2026-12-31" }
  }
}
```

**Clear** — standard patch semantics: `"repetitionRule": null`

### Partial Update Semantics

Repetition rules support targeted partial updates on `edit_tasks`, following two rules:

1. **Root-level fields are independently updatable** — change `schedule`, `basedOn`, or `end` without resending other fields
2. **Frequency object uses type as the merge boundary:**
   - `type` optional on same-type updates — inferred from existing task
   - Same type → merge (omitted fields preserved from existing rule)
   - Type changes → `type` required + full replacement (defaults apply like creation)
   - Specialization fields (`onDays`, `on`, `onDates`) can be added or cleared without changing type

```json
// Change only basedOn (everything else preserved):
{ "repetitionRule": { "basedOn": "defer_date" } }

// Change interval on existing task (type inferred from existing):
{ "repetitionRule": { "frequency": { "interval": 5 } } }

// Add specific days to a weekly task (no type change needed):
{ "repetitionRule": { "frequency": { "onDays": ["MO", "WE", "FR"] } } }

// Remove day constraint from weekly (clear the field):
{ "repetitionRule": { "frequency": { "onDays": null } } }

// Switch from date-based to weekday-based monthly (onDates auto-cleared):
{ "repetitionRule": { "frequency": { "on": {"last": "friday"} } } }

// Switch from daily to weekly (type required for type change):
{ "repetitionRule": { "frequency": { "type": "weekly", "onDays": ["MO", "FR"] } } }
```

No existing rule + partial update → error: "Task has no repetition rule. Provide a complete rule."

### RRULE Utility Layer

Standalone functions bridge the structured API and the internal RRULE format:

```mermaid
flowchart LR
    subgraph Agent-Facing
        SF[Structured Fields]
    end

    subgraph Internal
        BUILD["build_rrule()"]
        PARSE["parse_rrule()"]
        RRULE[RRULE String]
    end

    subgraph OmniFocus
        BRIDGE[bridge.js]
        SQLITE[(SQLite cache)]
    end

    SF -- "writes" --> BUILD -- "writes" --> RRULE -- "writes" --> BRIDGE
    SQLITE -- "reads" --> PARSE -- "reads" --> SF
    BRIDGE -- "reads" --> PARSE
```

#### Write Path

- `build_rrule(Frequency) → str` — structured model to RRULE string
- Service layer calls `build_rrule()` then sends the RRULE string + metadata to bridge.js
- Bridge stays dumb — receives `(ruleString, scheduleType, anchorDateKey, catchUp)`, creates `new Task.RepetitionRule()`

#### Read Path

- `parse_rrule(str) → Frequency` — RRULE string to structured model
- Both read paths (SQLite and bridge adapter) call `parse_rrule()` — single parsing implementation, two call sites
- All parsing in Python, not bridge — see [Dumb Bridge, Smart Python](#dumb-bridge-smart-python)

#### Common

- Both functions accept/return Pydantic models, not dicts

### Validation Layers

Three layers, all before bridge execution:

1. **Pydantic structural** — required fields, enum values, `end` has exactly one key
2. **Type-specific constraints** — reject fields that don't belong to given frequency type; value ranges (interval >= 1, valid day codes, valid ordinals, dayOfMonth -1 to 31 excluding 0)
3. **Service semantic** — no existing rule + partial update, type change + incomplete frequency, no-op detection with educational warnings

## Design Rationale

### Why Repository, not DataSource

- Repository implies querying/filtering — `list_tasks(filters)` in v1.3
- DataSource implies raw data access — too thin an abstraction
- Repository is the richer contract for how consumers interact with data

### Why flat packages (bridge/ and repository/ as peers)

- Bridge is a general OmniFocus communication channel, not just data access
- Future milestones: perspective switching, UI actions — all via Bridge directly
- Write operations go through Bridge (repository delegates)
- `repository/` depends on `bridge/` (never reverse)
- Keeping them as siblings avoids false nesting (`repository/bridge/` would imply ownership)

## Deferred Decisions

- Multi-repository coordination in OperatorService (if needed)
