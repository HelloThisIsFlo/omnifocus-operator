# Phase 21: Write Pipeline Unification - Context

**Gathered:** 2026-03-19
**Status:** Ready for planning

<domain>
## Phase Boundary

add_task and edit_task follow the same structural pattern at every layer boundary. Repository becomes a pure pass-through. Service does ALL processing and builds typed payloads. No new tools, no behavioral changes — pure internal quality.

Note: Phase 20 (typed payloads) already absorbed most of the original asymmetry. The remaining work is smaller than initially planned — it's about converging serialization strategy, eliminating a legacy camelCase roundtrip in the service, and making repos explicitly identical.

</domain>

<decisions>
## Implementation Decisions

### Serialization strategy convergence
- Both repos standardize on `exclude_unset=True` (currently add_task uses `exclude_none=True`)
- Service builds `CreateTaskRepoPayload` via kwargs dict with only populated fields → `model_validate()`, instead of setting all fields (some to None) via direct constructor
- This works because Pydantic tracks which fields were explicitly passed — `exclude_unset` drops the rest
- Same pattern edit_task already uses for `EditTaskRepoPayload`

### Service-side payload construction
- edit_task currently builds a camelCase intermediate dict (legacy from pre-Phase 20 when dicts went straight to the bridge), then maps back to snake_case via `_payload_to_repo` mapping dict before `model_validate()`
- Clean this up: build `repo_kwargs` in snake_case from the start, eliminate the `_payload_to_repo` mapping entirely
- Both paths then follow: snake_case kwargs → `model_validate()` → typed payload to repo

### BridgeWriteMixin
- Shared `_send_to_bridge(command: str, payload) -> dict[str, Any]` helper in a `BridgeWriteMixin` class
- Helper does `payload.model_dump(by_alias=True, exclude_unset=True)` + `self._bridge.send_command(command, raw)` — nothing else
- Cache invalidation (`self._cached = None`) stays OUTSIDE the helper, visible in each calling method — sending to bridge shouldn't silently invalidate caches
- Mixin lives in `repository/` (not in the bridge module — it's bridge-related but not BridgeRepository-specific)
- Future write operations (delete_task, add_project, etc.) just call `_send_to_bridge` and wrap the result

### Explicit protocol conformance
- All three repos explicitly declare they implement the Repository protocol:
  - `class BridgeRepository(BridgeWriteMixin, Repository)`
  - `class HybridRepository(BridgeWriteMixin, Repository)`
  - `class InMemoryRepository(Repository)` (no mixin — no bridge)
- Mixin-first in inheritance chain (Python convention: capabilities first, base contract last)
- This is a gap from Phase 20 — repos currently conform structurally but don't declare it

### InMemory alignment
- Claude's discretion on whether InMemory uses model_dump or direct field access
- Guiding principle: simplicity and readability — pick whichever is easiest to follow

### Claude's Discretion
- Exact file location for BridgeWriteMixin within `repository/`
- InMemory internal pattern (model_dump vs direct field access)
- Whether to unify InMemory's add_task and edit_task internal patterns or leave them different
- Ordering of changes across the codebase

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & contracts
- `docs/architecture.md` — Model Taxonomy section, protocol signatures, write pipeline flow
- `src/omnifocus_operator/contracts/protocols.py` — Repository protocol (add_task/edit_task signatures)
- `src/omnifocus_operator/contracts/use_cases/create_task.py` — CreateTaskRepoPayload, CreateTaskRepoResult
- `src/omnifocus_operator/contracts/use_cases/edit_task.py` — EditTaskRepoPayload, MoveToRepoPayload, EditTaskRepoResult

### Service (payload construction to refactor)
- `src/omnifocus_operator/service.py` lines 100-158 — add_task (direct constructor → change to kwargs dict)
- `src/omnifocus_operator/service.py` lines 160-445 — edit_task (camelCase intermediate dict + `_payload_to_repo` mapping → build snake_case from the start)

### Repository implementations (to unify)
- `src/omnifocus_operator/repository/bridge.py` — BridgeRepository (exclude_none → exclude_unset, add mixin + protocol)
- `src/omnifocus_operator/repository/hybrid.py` — HybridRepository (exclude_none → exclude_unset, add mixin + protocol)
- `src/omnifocus_operator/repository/in_memory.py` — InMemoryRepository (add protocol declaration, align patterns)

### Bridge script (for understanding bridge expectations)
- `src/omnifocus_operator/bridge/bridge.js` lines 223-253 — handleAddTask (field presence checks)
- `src/omnifocus_operator/bridge/bridge.js` lines 255-326 — handleEditTask (hasOwnProperty for patch semantics)

### Requirements
- `.planning/REQUIREMENTS.md` — PIPE-01, PIPE-02 definitions

### Prior phase context
- `.planning/phases/20-model-taxonomy/20-CONTEXT.md` — Naming convention, typed payloads, contracts/ package structure

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `contracts/protocols.py`: Repository protocol with typed add_task/edit_task signatures — repos need to explicitly inherit this
- `contracts/use_cases/`: Per-operation payload and result models — already bridge-ready via `model_dump(by_alias=True)`
- `OmniFocusBaseModel.alias_generator`: camelCase aliases via `to_camel` — handles snake_case → camelCase serialization automatically

### Established Patterns
- edit_task's repo payload construction (kwargs dict → model_validate → exclude_unset) is the target pattern for both paths
- `@_ensures_write_through` decorator on HybridRepository ensures read-after-write consistency — unaffected by this phase
- Mixin-first inheritance convention (capabilities, then contract)

### Integration Points
- BridgeRepository and HybridRepository both delegate to `self._bridge.send_command()` — the shared plumbing the mixin captures
- BridgeRepository has `self._cached` for snapshot caching; HybridRepository does not (uses SQLite)
- InMemoryRepository has no bridge — implements the protocol directly against an in-memory snapshot

</code_context>

<specifics>
## Specific Ideas

- "If we can reach uniformity and it's not a hack, then definitely that would be the way to go"
- The `_send_to_bridge` helper should return the raw dict — result class wrapping is each method's job, since result types may differ
- "When you send to bridge, it's not very obvious that it's going to invalidate the cache" — cache invalidation must be visible at the call site
- Phase 22 is about splitting the large service file, not cleanup — the camelCase roundtrip cleanup belongs in Phase 21

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 21-write-pipeline-unification*
*Context gathered: 2026-03-19*
