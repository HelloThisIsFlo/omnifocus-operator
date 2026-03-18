# Phase 20: Model Taxonomy - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Write-side models follow a consistent CQRS/DDD-inspired naming convention with typed models at every boundary. Three changes: (1) rename all write-side models to indicate their layer, (2) introduce typed Pydantic models for bridge payloads replacing `dict[str, Any]`, (3) reorganize into a `contracts/` package with protocols and use-case modules. No new tools, no behavioral changes — pure internal quality.

</domain>

<decisions>
## Implementation Decisions

### Naming convention (CQRS/DDD-inspired)

- **Verb-first** for all write-side models: `CreateTask___`, `EditTask___` (not `TaskCreate___`)
- **Noun-only** for read-side entities: `Task`, `Project`, `Tag` (no suffix)
- Seven suffixes, each tied to a specific boundary and role:

| Suffix | Role | Boundary | Examples |
|---|---|---|---|
| `___Command` | Agent instruction | Agent → Service | `CreateTaskCommand`, `EditTaskCommand` |
| `___Result` | Agent outcome (enriched) | Service → Agent | `CreateTaskResult`, `EditTaskResult` |
| `___RepoPayload` | Bridge-ready data | Service → Repository | `CreateTaskRepoPayload`, `EditTaskRepoPayload` |
| `___RepoResult` | Minimal confirmation | Repository → Service | `CreateTaskRepoResult`, `EditTaskRepoResult` |
| `___Action` | Stateful mutation | Nested in commands (actions block) | `TagAction`, `MoveAction` |
| `___Spec` | Write-side value object | Nested, read/write shape diverges | `RepetitionRuleSpec` (future, not Phase 20) |
| No suffix | Read entity / shared VO | Domain | `Task`, `TagRef`, `RepetitionRule` |

- `___Spec` is reserved for future use — no models get this suffix in Phase 20. First user will be `RepetitionRuleSpec` when repetition rule writes are implemented.

### Complete rename map

| Current name (models/write.py) | New name | New location |
|---|---|---|
| `WriteModel` | `CommandModel` | contracts/base.py |
| `_Unset`, `UNSET` | `_Unset`, `UNSET` | contracts/base.py |
| `_clean_unset_from_schema` | `_clean_unset_from_schema` | contracts/base.py |
| `TaskCreateSpec` | `CreateTaskCommand` | contracts/use_cases/create_task.py |
| `TaskCreateResult` | `CreateTaskResult` | contracts/use_cases/create_task.py |
| `TaskEditSpec` | `EditTaskCommand` | contracts/use_cases/edit_task.py |
| `TaskEditResult` | `EditTaskResult` | contracts/use_cases/edit_task.py |
| `ActionsSpec` | `EditTaskActions` | contracts/use_cases/edit_task.py |
| `TagActionSpec` | `TagAction` | contracts/common.py |
| `MoveToSpec` | `MoveAction` | contracts/common.py |
| *(new)* | `CreateTaskRepoPayload` | contracts/use_cases/create_task.py |
| *(new)* | `CreateTaskRepoResult` | contracts/use_cases/create_task.py |
| *(new)* | `EditTaskRepoPayload` | contracts/use_cases/edit_task.py |
| *(new)* | `EditTaskRepoResult` | contracts/use_cases/edit_task.py |
| *(new)* | `MoveToRepoPayload` | contracts/use_cases/edit_task.py |

### Typed payloads at the repository boundary

- Per-operation models at every boundary (not a shared `WriteResult` — each operation has its own RepoPayload and RepoResult)
- Nested `___RepoPayload` models where the bridge expects nested JSON (e.g., `MoveToRepoPayload` inside `EditTaskRepoPayload`)
- Flat fields for primitives and lists (tag IDs, dates, lifecycle)
- `model_dump(by_alias=True)` on RepoPayload produces exactly what the bridge expects — repository is a pure pass-through with zero logic
- RepoResult models are minimal confirmations: `id: str, name: str`
- Service maps RepoResult → agent-facing Result (adds `success`, `warnings`, etc.)

### Module organization — contracts/ package

- New `contracts/` package at `omnifocus_operator/contracts/`
- `contracts/protocols.py` — Service, Repository, Bridge protocols in ONE file (the "full typed contract" file)
- `contracts/base.py` — `CommandModel`, `UNSET`, `_Unset`, `_clean_unset_from_schema`
- `contracts/common.py` — `TagAction`, `MoveAction` (shared value objects, reusable across future use cases)
- `contracts/use_cases/` — one module per operation:
  - `create_task.py` — `CreateTaskCommand`, `CreateTaskRepoPayload`, `CreateTaskRepoResult`, `CreateTaskResult`
  - `edit_task.py` — `EditTaskCommand`, `EditTaskActions`, `EditTaskRepoPayload`, `MoveToRepoPayload`, `EditTaskRepoResult`, `EditTaskResult`
- `models/` becomes read-side only — domain entities, enums, shared value objects
- Bridge and Repository protocols move from `bridge/protocol.py` and `repository/protocol.py` into `contracts/protocols.py`
- New Service protocol added (currently no service protocol exists)

### Backward compatibility

- **Zero.** Clean break, update all call sites. No aliases, no deprecation, no migration messages.
- Same approach as Phase 19 — project is not published, sole user, prefer perfectly clean code.
- `models/write.py` is deleted entirely after migration (all contents moved to contracts/)
- `models/__init__.py` re-exports read-side models only
- `bridge/protocol.py` and `repository/protocol.py` are deleted (protocols moved to contracts/)

### Handling the Phase 21 asymmetry

- Phase 20 introduces typed payloads, but the add/edit pipeline asymmetry remains (Phase 21 fixes it)
- `CreateTaskRepoPayload` may still require minor key manipulation in the repository (tag_ids → tagIds swap)
- `EditTaskRepoPayload` is fully bridge-ready (service does all processing)
- Per-operation models absorb this asymmetry cleanly — each payload honestly reflects how its operation works today
- See `.sandbox/phase-21-payload-convergence.md` for the Phase 21 convergence target

### Decision tree for naming new write-side models

This is for the planner/implementer when encountering edge cases:

1. Is it a top-level instruction from the agent? → `___Command`
2. Is it processed data sent to the repository? → `___RepoPayload`
3. Is it a stateful operation inside the actions block? → `___Action`
4. Is it a complex nested value object (setter, not a mutation)?
   - Same shape as read side → no suffix (shared model)
   - Different shape from read side → `___Spec`
5. Is it the confirmation from the repository? → `___RepoResult`
6. Is it the enriched outcome returned to the agent? → `___Result`

### Claude's Discretion

- Import convenience: whether `contracts/__init__.py` re-exports all models or consumers import from submodules directly
- Whether `contracts/use_cases/__init__.py` re-exports or not
- Exact ordering of model definitions within each use_cases module
- Whether `_clean_unset_from_schema` stays in base.py or gets its own utility module
- How to handle `models/__init__.py` forward reference rebuilding (`model_rebuild`) after write models move out
- Test file import migration ordering and approach

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & naming convention
- `docs/architecture.md` — Model Taxonomy section defines the full naming convention, decision tree, data flow diagram, and package structure. **This is the authoritative reference for naming.**
- `docs/architecture.md` §Protocols — Shows all three protocol signatures with typed models
- `docs/architecture.md` §Write Pipeline — Shows the full typed flow through all boundaries
- `docs/architecture.md` §Package Structure — Shows the target `contracts/` layout

### Full before/after spec
- `.sandbox/phase-20-model-taxonomy-spec.md` — Complete spec with every model, every field, before (current), after Phase 20, and after Phase 21 target state. **Read this for exact field definitions.**
- `.sandbox/phase-21-payload-convergence.md` — Phase 21 convergence target (how the asymmetry gets fixed)

### Current models to rename
- `src/omnifocus_operator/models/write.py` — All current write models (WriteModel, TaskCreateSpec, TaskEditSpec, etc.)
- `src/omnifocus_operator/models/__init__.py` — Current re-exports and model_rebuild() calls
- `src/omnifocus_operator/models/base.py` — OmniFocusBaseModel (stays, not renamed)

### Current protocols to move
- `src/omnifocus_operator/bridge/protocol.py` — Bridge protocol (moves to contracts/protocols.py)
- `src/omnifocus_operator/repository/protocol.py` — Repository protocol (moves to contracts/protocols.py)

### Service (needs import updates + new protocol)
- `src/omnifocus_operator/service.py` — OperatorService (all write method signatures change from Spec→Command, dict→RepoPayload)
- `src/omnifocus_operator/server.py` — MCP tool handlers (import paths change)

### Repository implementations (signatures change)
- `src/omnifocus_operator/repository/hybrid.py` — add_task/edit_task signatures change to typed payloads/results
- `src/omnifocus_operator/repository/bridge.py` — same
- `src/omnifocus_operator/repository/in_memory.py` — same

### Requirements
- `.planning/REQUIREMENTS.md` — MODL-01 through MODL-04 definitions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `OmniFocusBaseModel` (models/base.py): Read-side base with alias_generator, validate_by_name/alias — unchanged, still used for Result models and read entities
- `_Unset` sentinel (models/write.py): Singleton with `__get_pydantic_core_schema__` — moves to contracts/base.py, behavior unchanged
- `_clean_unset_from_schema` (models/write.py): JSON schema cleanup utility — moves with the sentinel
- `warnings.py`: Warning string constants — import paths unaffected by this phase

### Established Patterns
- All write models inherit from `WriteModel` (→ `CommandModel`) with `extra="forbid"` — pattern preserved
- Write models override `model_json_schema()` to clean UNSET from JSON schema — pattern preserved, moves with the models
- Result models inherit from `OmniFocusBaseModel` (permissive) — pattern preserved
- `models/__init__.py` does `model_rebuild(_types_namespace=_ns)` for forward references — needs updating after write models move out

### Integration Points
- `server.py` lines 178-236: MCP tool handlers that parse JSON into write specs — import paths change
- `service.py` lines 99-137: `add_task` method — parameter type changes from `TaskCreateSpec` to `CreateTaskCommand`
- `service.py` lines 139-350+: `edit_task` method — parameter type changes, must build `EditTaskRepoPayload` instead of `dict[str, Any]`
- `repository/protocol.py`: Protocol definition — moves to `contracts/protocols.py`, signatures change
- `repository/hybrid.py` lines 477-523: `add_task`/`edit_task` — signatures change to typed payloads/results
- All test files importing from `omnifocus_operator.models.write` or `omnifocus_operator.models` — import paths change

</code_context>

<specifics>
## Specific Ideas

- "I come from the Java world with DDD and CQRS — those are the two architectural concepts that influenced my career the most"
- "Clarity beats verbosity" — verbose names like `CreateTaskRepoPayload` are preferred if they're immediately clear
- "Treat agents as a junior developer" — the architecture should make the right path the obvious path. Per-operation models prevent agents from hacking around a shared model when things diverge
- "I want to open ONE file and see the full typed flow" — `contracts/protocols.py` exists so a human can see every boundary at a glance
- "`ls contracts/use_cases/` should show every operation" — the use_cases folder is the operation index
- The naming convention was stress-tested against the future RepetitionRule feature to verify it evolves cleanly — it does (see `___Spec` suffix for future read/write shape divergence)

</specifics>

<deferred>
## Deferred Ideas

- **`___Spec` suffix usage** — convention defined but no models use it in Phase 20. First user: `RepetitionRuleSpec` when repetition rule writes are implemented.
- **Write pipeline unification** — Phase 21 converges add/edit to the same pattern. Phase 20's per-operation models absorb the current asymmetry.
- **Service decomposition** — Phase 22 splits service.py into a package. The `contracts/` package established here provides the typed interfaces that decomposed modules will implement against.

</deferred>

---

*Phase: 20-model-taxonomy*
*Context gathered: 2026-03-18*
