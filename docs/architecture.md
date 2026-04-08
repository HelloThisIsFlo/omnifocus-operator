# Architecture Overview

## Layer Diagram

```mermaid
graph TB
    Agent["🤖 AI Agent"]
    Server["server.py<br/>MCP Tool Handlers"]
    Service["service.py<br/>Validation · Resolution · Delegation"]
    Repo["Repository Protocol"]
    HybridRepo["HybridRepository<br/>SQLite reads + Bridge writes"]
    BridgeOnlyRepo["BridgeOnlyRepository<br/>Bridge for reads + writes"]
    SQLite["SQLite Cache<br/>~46ms reads"]
    Bridge["Bridge<br/>OmniJS IPC"]
    OF["OmniFocus"]

    Agent -->|JSON| Server
    Server -->|"Command / Result"| Service
    Service -->|"RepoPayload / RepoResult"| Repo
    Repo --- HybridRepo
    Repo --- BridgeOnlyRepo
    HybridRepo -->|reads| SQLite
    HybridRepo -->|writes| Bridge
    BridgeOnlyRepo --> Bridge
    Bridge -->|File IPC| OF
    SQLite -.->|"OmniFocus writes → WAL updates"| OF
```

## Package Structure

```
omnifocus_operator/
    contracts/       -- Typed boundaries: protocols, commands, payloads, results
        protocols.py     -- Service, Repository, Bridge — all boundaries in one file
        base.py          -- CommandModel, UNSET sentinel
        shared/          -- Shared value objects across use cases
            actions.py       -- TagAction, MoveAction
            repetition_rule.py -- RepetitionRuleRepoPayload, frequency/end specs
        use_cases/       -- One sub-package per operation
            add/tasks.py     -- AddTaskCommand, AddTaskRepoPayload, AddTaskRepoResult, AddTaskResult
            edit/tasks.py    -- EditTaskCommand, EditTaskRepoPayload, EditTaskRepoResult, EditTaskResult
            list/            -- ListTasksQuery, ListProjectsQuery, repo queries, ListRepoResult
    models/          -- Read-side domain models (entities, enums, value objects)
    bridge/          -- OmniFocus communication (IPC, mtime, errors)
    repository/      -- Data access implementations + factory
        bridge_only/         -- Fallback: bridge for reads + writes
            bridge_only.py       -- BridgeOnlyRepository
            adapter.py           -- Raw bridge → model shape adapter
        hybrid/              -- Production: SQLite reads + bridge writes
            hybrid.py            -- HybridRepository
            query_builder.py     -- SQL query construction
        rrule/               -- RRULE serialization/parsing
        bridge_write_mixin.py -- Shared bridge write logic
        factory.py           -- create_repository() — selects implementation
    simulator/       -- Mock OmniFocus simulator for IPC testing
    server.py        -- FastMCP tool registration + wiring
    service/         -- Validation, resolution, domain logic, delegation
        service.py       -- Thin orchestrator (OperatorService)
        convert.py       -- Spec-to-core model conversion at service boundary
        resolve.py       -- Entity resolution (parent, tags, task)
        validate.py      -- Pure input validation
        domain.py        -- Product decisions: the opinionated logic that defines this tool's behavior
        payload.py       -- Typed repo payload construction
    agent_messages/  -- Agent-facing communication surface (warnings + errors)
        warnings.py      -- Centralized warning constants
        errors.py        -- Centralized error message constants
```

> [!important] Split principle
>
> - `models/` = what OmniFocus **IS** (domain entities, `OmniFocusBaseModel`)
> - `contracts/` = what you can **DO** (operations, boundaries, `CommandModel` with `extra="forbid"`)
> - Everything else = **how it's done** (implementations)
>
> Never embed a `models/` class directly in a `contracts/` command — the base class difference (`extra="forbid"`) means write-side models always need their own class, even with identical fields.

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
- Tests use `InMemoryBridge` + `BridgeOnlyRepository` — no separate in-memory repository needed
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

Two implementations: HybridRepository (production), BridgeOnlyRepository (fallback). Tests use BridgeOnlyRepository + InMemoryBridge.

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

- **Service** does ALL processing — validation, parent/tag resolution, tag diff, move transformation, date serialization, no-op detection
- **Repository** is a pure pass-through — `model_dump()` → `send_command()` → wrap result
- **Bridge** is a dumb relay — receives pre-validated dicts, executes, returns minimal confirmation
- Parent resolution: try `get_project` first, then `get_task` — **project takes precedence** (intentional, deterministic)
- HybridRepository marks stale after write; BridgeOnlyRepository clears cache

### Method Object Pattern

All service use cases use the **Method Object** pattern: extract the method body into a short-lived class where each step is a named method and intermediate values live on `self`.

**Why:**
- A 100-line method with 12 local variables is *familiar* but forces you to track all state simultaneously
- A Method Object with a 12-line `execute()` method and 3-8 line steps is *readable* — each step is self-contained, named, navigable, and shows up in stack traces
- The value is self-documenting orchestration, not complexity management — even `add_task` (5 steps) reads better as a pipeline

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

**Conventions:**
- All pipelines inherit from `_Pipeline` (shared DI constructor)
- Class name: `_VerbNounPipeline` (private, underscore prefix) — e.g., `_AddTaskPipeline`, `_EditTaskPipeline`
- Constructor receives DI dependencies; `execute()` receives the input
- Mutable state on `self` is acceptable — the object is created, executed, and discarded within a single call. The lifetime is bounded.
- Step methods are private (`_verify_task_exists`, not `verify_task_exists`)
- Read delegation methods (get_task, get_project, etc.) stay inline on OperatorService — one-liner pass-throughs, not pipelines

### Service Layer: Product Decisions vs Plumbing

The service layer modules are organized around **product opinion vs mechanical plumbing** — not "pure vs impure" or "stateful vs stateless."

> [!important] The litmus test
>
> "Would another OmniFocus tool make this same choice?"
>
> - **Yes** → plumbing (any competent implementation needs it)
> - **No** → product decision (this is *our* choice, and it belongs in `domain.py`)

`domain.py` is where you look to understand what makes OmniFocus Operator *this particular product*. If you want to tweak the behavior that defines the tool, you should only need to look here.

Everything else in the service layer is plumbing — I/O sequencing, entity lookups, payload assembly, input validation. Necessary, but any implementation would do roughly the same thing.

| Concern | Where | Why |
|---------|-------|-----|
| "soon" without config → fall back to TODAY + warn | 🧠 domain | Another tool might error or guess. We chose conservative bounds + transparency |
| Lifecycle auto-include (completed filter → add COMPLETED availability) | 🧠 domain | Another tool might require explicit opt-in |
| `null` note → empty string | 🧠 domain | OmniJS rejects null, but *how* to handle it is a product choice |
| ALL mixed with other filters → warning | 🧠 domain | Behavioral guidance for agents — our opinion on what's helpful |
| No-op detection + educational warnings | 🧠 domain | We chose to warn, not silently succeed |
| Filter resolution warnings (multi-match, did-you-mean) | 🧠 domain | Agent UX choices — fuzzy matching policy |
| Fetching `due_soon_setting` from the repo | 🔧 pipeline | I/O sequencing — mechanical |
| Building `ListTasksRepoQuery` from resolved values | 🔧 pipeline | Assembly — mechanical |
| `{this: "w"}` → Monday-to-Sunday bounds | 📅 resolve_dates | Date arithmetic — any implementation needs this |
| Name → ID resolution with fuzzy matching | 🔍 resolve | Lookup mechanics — mechanical |
| Spec-to-core model conversion | 🔄 convert | Data mapping — structural |
| Repo payload construction | 📦 payload | Assembly — structural |

> [!note] Where does `resolve_dates.py` sit?
>
> - Contains opinions (show-more boundary choices, day-snapping behavior), but at the **per-field arithmetic** level
> - Domain calls into it for individual field resolution and owns the **cross-field orchestration** — lifecycle mapping, edge-case fallbacks, what to do when configuration is missing

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
    else BridgeOnlyRepository (fallback)
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
- **BridgeOnlyRepository** (fallback via `OPERATOR_REPOSITORY=bridge`): OmniJS bridge dump
  - mtime-based cache invalidation; checks file mtime before each read, serves cached snapshot if unchanged
  - Concurrent reads coalesce into a single bridge dump
- **Tests**: BridgeOnlyRepository + InMemoryBridge (no separate in-memory repository)

## Naming Conventions

### MCP tool verbs

Write tools use domain-native verbs, not CRUD:

| Verb | Operation | Examples |
|------|-----------|---------|
| `add_*` | Introduce a new entity into OmniFocus | `add_tasks`, future `add_projects` |
| `edit_*` | Modify an existing entity | `edit_tasks`, future `edit_projects` |
| `delete_*` | Remove an entity | future `delete_tasks` |
| `get_*` | Look up a single entity by ID | `get_task`, `get_project`, `get_tag` |
| `list_*` | Filtered collection of one entity type | `list_tasks`, `list_projects` |
| `count_*` | Count entities matching a filter | future `count_tasks` |

**Why "add" not "create":**
- "Add" is the natural verb for task management ("add a task to my inbox")
- Matches OmniJS domain language
- Forms a coherent verb system (add/edit/delete)
- "Create" is standard CRUD but sounds formal for the most common operation
- Tool descriptions use natural language freely — e.g., `add_tasks` description can say "Create tasks in OmniFocus." The tool name is the technical identifier, the description is the UX.

### Method names

- `get_all()` → `AllEntities`: structured container with all entity types
- `get_*` by ID → single entity lookup
- `list_*(filters)` → flat list of one entity type (e.g., `list_tasks(status=...)`)
- `add_*` / `edit_*` → write operations
- `get_*` = heterogeneous structured return; `list_*` = homogeneous filtered collection
- `AllEntities` (not `DatabaseSnapshot`) — no caching/snapshot semantics at the protocol level

### Model taxonomy

> [!tip] Full taxonomy with decision tree and examples
>
> See [Model Taxonomy](model-taxonomy.md) for the complete classification:
>
> - Core models vs boundary models
> - Suffix conventions (`Read`, `Command`, `Result`, `RepoPayload`, `RepoResult`)
> - Decision tree for where a new model goes

## Dumb Bridge, Smart Python

> [!important] The key invariant
>
> **The bridge is a relay, not a brain.** All validation, resolution, diff computation, and business logic lives in Python. The bridge receives pre-validated payloads and executes them without interpretation.

### Why

- **OmniJS freezes the UI** — every line of bridge logic is user-visible latency. Scanning 2,825 tasks takes ~1,264ms during which OmniFocus is unresponsive
- **OmniJS is quirky** — opaque enums, unreliable batch operations, null rejection. Sharp edges that are painful to debug
- **Python is testable** — 534 pytest tests cover service logic, adapter transformations, and repository behavior. Bridge.js has 26 Vitest tests for basic relay correctness — that's the right ratio
- **Python is typed** — Pydantic models, mypy strict mode, and structured error handling catch issues at development time, not at 7:30am in production

### Known OmniJS Quirks

Concrete examples of why logic stays out of the bridge:

- **`removeTags(array)` is unreliable** — bridge removes tags one at a time in a loop instead of batch (`bridge.js`, `handleEditTask`)
- **`note = null` is rejected** — OmniFocus API requires empty string to clear notes. Service maps `null → ""` before building the repo payload
- **Enums are opaque objects** — `.name` returns `undefined`. Only `===` comparison against known constants works. Bridge does minimal enum-to-string resolution and throws on unknowns
- **Same-container moves are no-ops** — `beginning`/`ending` moves within the same container don't reorder. Service detects this and warns with a workaround
- **Blocking state is invisible** — bridge cannot determine sequential dependencies or parent-child blocking. Only SQLite has full availability data (`BRIDGE-SPEC.md:FALL-02`)

### What Lives Where

| Concern | Where | Why |
|---------|-------|-----|
| Enum-to-string resolution | 🌉 Bridge | Must happen at source (opaque objects) |
| Tag name-to-ID resolution | ⚙️ Service | Case-insensitive matching, ambiguity errors |
| Tag diff computation | ⚙️ Service | Minimal add/remove sets, no-op warnings |
| Cycle detection (moves) | ⚙️ Service | Parent chain walk on cached snapshot — instant |
| No-op detection + warnings | ⚙️ Service | Field comparison before bridge delegation |
| Null-means-clear mapping | ⚙️ Service | Business logic, not transport |
| RRULE string generation | 🗄️ Repository | Repository owns RRULE both directions (see [RRULE Utility Layer](#rrule-utility-layer)) |
| Lifecycle (complete/drop) | ⚙️ Service + 🌉 Bridge | Service validates state, bridge executes `markComplete()`/`drop()` |
| Validation (structural) | 📐 Contract models | Pydantic validators on specs — value ranges, enum membership, field constraints |
| Validation (semantic) | ⚙️ Service | State checks, no-op detection, cross-entity resolution |

### The Result

The bridge is ~400 lines of trivial relay code. The rest of the project is ~14,000 lines of validated, typed, tested Python. That's the right split.

## Show-More Principle

In a task manager, error costs are asymmetric:

- **Showing one extra task** — the user glances at it, sees it's irrelevant, moves on. Cost: near zero.
- **Missing a task** — the user doesn't know what they can't see. They miss a deadline, forget a commitment, lose trust in the tool. Cost: high.

Same tradeoff as tuning a classifier — a spam filter tolerates false negatives to avoid burying real emails, but medical screening biases hard toward flagging anything suspicious. Task management is closer to medical screening: the cost of a miss far outweighs the cost of showing too much.

> [!important] The rule
>
> **Every ambiguous boundary decision biases toward inclusion.**
>
> - Boundary could be inclusive or exclusive? → inclusive
> - "Due soon" could exclude or include overdue? → include
> - Time period count is ambiguous? → round toward showing more

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

- **Strict filters are strict** — `flagged: true`, `availability: "available"` — no fuzziness. These aren't boundary cases, they're different questions.
- **Default exclusions are intentional** — completed/dropped tasks require an explicit filter. "Show active tasks" is a clear design choice, not an ambiguous boundary.
- **The principle is a tiebreaker**, not a blanket rule. If the answer is obviously "exclude," exclude.

## Structure Over Discipline

*Designing architecture for agents who always take the shortest path.*

Agents optimize for least resistance uniformly and instantly — they don't leave legible patterns you can learn from. So: **pave first.** Make the structure guide toward the right choice, not discipline or documentation.

- **Prefer duplication over shared abstractions** when paths will diverge — separate types per operation, separate classes even when fields match today. Agents won't recognize when a shared abstraction is the wrong fit.
- **Use the type system to make wrong states unrepresentable** — distinct types at each boundary, sentinel types for ambiguous states. If the wrong choice doesn't compile, agents can't take it.
- **Make module boundaries self-documenting** — when the module name tells you where new code goes, agents don't need to make judgment calls about placement.

> [!tip] Full writeup with examples
>
> See [Structure Over Discipline](structure-over-discipline.md) for concrete examples of each principle applied in this codebase.

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

- **Setters** — idempotent field replacements (top-level). Generic no-op warning when value unchanged.
- **Actions** — operations that modify relative to current state (nested under `actions`). Action-specific warnings (e.g., "Tag 'X' is already on this task").
- **Any field can graduate** from setter to action group when it needs more than simple replacement.
  - Migration path:
    1. Remove the field from top-level setters
    2. Add it as an action group under `actions` with `replace` + new operations
  - **Example:** `note` could graduate to `actions.note: { replace: "...", append: "..." }` when append-note is needed.
- **Tags are the first graduated field:**

  ```json
  // Before graduation (v1.2.0): top-level setter, replace-only
  { "tags": ["Work", "Planning"] }

  // After graduation (v1.2.1): action group with add/remove/replace
  { "actions": { "tags": { "add": ["Urgent"], "remove": ["Planning"] } } }
  ```

- **Each graduation is independent** — migrate one field at a time as use cases emerge.

### Agent-facing messages

All agent-facing text is centralized in `agent_messages/` with AST-based test enforcement preventing inline regressions. Agents learn from every response, so message quality is a first-class concern.

- Write results include optional `warnings` array for no-ops and edge cases
- Errors (`ValueError`) use the same centralized constant + `.format()` pattern as warnings
- Examples:
  - Tag no-op: "Tag 'X' was not on this task — omit remove_tags to skip"
  - Setter no-op: "Field 'flagged' is already true — omit to skip"
  - Same-container move: "Task is already in this container. Use 'before' or 'after' with a sibling task ID to control ordering."
  - Lifecycle on completed: "Task is already completed — no change made"

## Two-Axis Status Model

- **Urgency**: `overdue`, `due_soon`, `none` — time-based, computed from dates
- **Availability**: `available`, `blocked`, `completed`, `dropped` — lifecycle state
- Replaces single-winner status enum from v1.0; matches OmniFocus internal representation

## Repetition Rule: Structured Fields, Not RRULE Strings

> **Status:** Read + write models implemented (v1.2.3) — flat `Frequency` model, `parse_rrule()`, `build_rrule()`. Type optional on edits.

Agents never see RRULE strings. The read and write models expose repetition as structured fields with a flat frequency model. The RRULE string is an internal serialization detail between the service layer and the bridge.

> [!note] Why top-level (not inside `actions`)?
>
> - Setting a repetition rule is **idempotent** — same input always produces the same result, regardless of current state
> - Follows the same pattern as `due_date`, `note` — set, clear, or leave unchanged

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

The `repository/rrule/` package owns RRULE translation in both directions. Service works exclusively with core types (`Frequency`, `Schedule`, `BasedOn`, `EndCondition`) — it never sees RRULE strings.

#### Write Path

- Service builds a `RepetitionRuleRepoPayload` (all core types) and hands it to the repository
- `bridge_write_mixin._dump_payload()` intercepts and delegates to `rrule/serialize.py`
- `serialize.py` calls `builder.py` (Frequency → RRULE string) and `schedule.py` (Schedule/BasedOn → bridge enums)
- Bridge receives flat `{ruleString, scheduleType, anchorDateKey, catchUpAutomatically}`

#### Read Path

- Both read implementations (`hybrid.py`, `adapter.py`) normalize raw fields via mapping tables, then call shared `rrule/` functions
- `parser.py`: `parse_rrule()` → `Frequency`, `parse_end_condition()` → `EndCondition | None`
- `schedule.py`: `derive_schedule()` → `Schedule`, anchorDateKey → `BasedOn`
- Assembled into `RepetitionRule` (core model) — service receives clean types

---

_For detailed flow diagrams — write (add/edit) and read pipelines with full data flow: [repetition-rule-flow.md](repetition-rule-flow.md)_

### Validation Layers

Three layers, all before bridge execution:

1. **Pydantic structural** (contract model validators) — required fields, enum values, `end` has exactly one key
2. **Type-specific constraints** (contract model validators) — reject fields that don't belong to given frequency type; value ranges (interval >= 1, valid day codes, valid ordinals, dayOfMonth -1 to 31 excluding 0)
3. **Service semantic** (service layer) — no existing rule + partial update, type change + incomplete frequency, no-op detection with educational warnings

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
