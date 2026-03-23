# Phase 22: Service Decomposition - Context

**Gathered:** 2026-03-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Convert `service.py` (669 lines) into a `service/` package. Extract validation, domain logic, and format conversion into dedicated, independently testable modules. The orchestrator (OperatorService) becomes pure orchestration — a thin sequence of validate, resolve, domain, build, delegate steps. No new tools, no behavioral changes — pure internal quality.

Both OperatorService and ErrorOperatorService must explicitly implement the Service protocol from `contracts/protocols.py`.

</domain>

<decisions>
## Implementation Decisions

### Package structure

```
service/
├── __init__.py     # from .service import OperatorService, ErrorOperatorService
├── service.py      # OperatorService, ErrorOperatorService (thin orchestration + read delegation)
├── resolve.py      # Resolver class + standalone validate_task_name
├── domain.py       # DomainLogic class (lifecycle, tags, cycle, no-op, move, warnings)
└── payload.py      # PayloadBuilder class (typed repo payload construction)
```

- `service.py` inside the package (not `__init__.py`) — consistent with `repository/` pattern where implementations live in their own files
- `__init__.py` is a thin re-export only

### Module naming — action names, not categories

- `resolve.py` — "take raw user input, verify and normalize it" (not "validation.py")
- `domain.py` — "apply business rules" (lifecycle, tag diff, cycle detection, no-op)
- `payload.py` — "assemble typed RepoPayloads" (not "conversion.py")
- Named after what the module DOES, not abstract categories — resolves the overlap between validation and conversion

### Decomposition map

| Module | Functions |
|---|---|
| **resolve.py** | `Resolver.resolve_parent`, `Resolver.resolve_tags`, `validate_task_name` (standalone) |
| **domain.py** | `DomainLogic.process_lifecycle`, `DomainLogic.compute_tag_diff`, `DomainLogic.check_cycle`, `DomainLogic.detect_noop`, `DomainLogic.check_completed_status`, `DomainLogic.process_move`, `_to_utc_ts` (helper) |
| **payload.py** | `PayloadBuilder.build_add`, `PayloadBuilder.build_edit` |
| **service.py** | `OperatorService.add_task`, `OperatorService.edit_task` (orchestration), read delegation (`get_all_data`, `get_task`, `get_project`, `get_tag`), `ErrorOperatorService` |

### Guiding principles for decomposition

- **All warning generation is domain logic** — lifecycle warnings, tag no-op warnings, completed/dropped status warnings, no-op detection all live in domain.py
- **Cycle detection is domain** — it walks the parent-child graph with domain semantics, not basic input validation
- **`_to_utc_ts` lives in domain** — it's a helper solely for no-op detection (semantic equivalence checking), collocated with its purpose
- **Read delegation stays in service** — one-liner pass-throughs, no logic to extract

### Function signatures — classes with dependency injection

- `Resolver(repo: Repository)` — receives repo for parent/tag resolution
- `DomainLogic(repo: Repository, resolver: Resolver)` — receives both (repo for check_cycle graph walking, resolver for tag diff resolution)
- `PayloadBuilder()` — no dependencies, pure transformation
- `validate_task_name(name)` — standalone function, no dependencies

Dependency graph: `Repository → Resolver → DomainLogic`. No cycles.

### _Unset checks stay in the orchestrator

- `_Unset` is a service-layer concern (flow control: "should I call this domain method?")
- Domain methods receive clean Python values (strings, lists, dicts), never `_Unset`
- This keeps domain methods simple to call and test — pass a string, not a command object

### Protocol conformance

- `OperatorService` and `ErrorOperatorService` must explicitly declare they implement the Service protocol from `contracts/protocols.py`
- Same pattern Phase 21 established for repositories

### Logging

- Each module has its own `logger = logging.getLogger("omnifocus_operator")`
- Logging stays close to the logic — Resolver logs resolution attempts, DomainLogic logs lifecycle decisions, etc.

---

## Reference Examples

The following code examples were discussed and approved during context gathering. They represent the **target shape** of each module. Downstream agents should follow these patterns closely.

### service/service.py — The orchestrator

```python
class OperatorService(Service):  # explicitly implements Service protocol
    def __init__(self, repository: Repository) -> None:
        self._repository = repository
        self._resolver = Resolver(repository)
        self._domain = DomainLogic(repository, self._resolver)
        self._payload = PayloadBuilder()

    # ── Read delegation (one-liner pass-throughs) ──────────

    async def get_all_data(self) -> AllEntities:
        return await self._repository.get_all()

    async def get_task(self, task_id: str) -> Task | None:
        return await self._repository.get_task(task_id)

    async def get_project(self, project_id: str) -> Project | None:
        return await self._repository.get_project(project_id)

    async def get_tag(self, tag_id: str) -> Tag | None:
        return await self._repository.get_tag(tag_id)

    # ── add_task: validate → resolve → build → delegate ───

    async def add_task(self, command: CreateTaskCommand) -> CreateTaskResult:
        from omnifocus_operator.contracts.use_cases.create_task import CreateTaskResult

        validate_task_name(command.name)

        if command.parent is not None:
            await self._resolver.resolve_parent(command.parent)

        resolved_tag_ids = None
        if command.tags is not None:
            resolved_tag_ids = await self._resolver.resolve_tags(command.tags)

        repo_payload = self._payload.build_add(command, resolved_tag_ids)
        repo_result = await self._repository.add_task(repo_payload)

        return CreateTaskResult(
            success=True, id=repo_result.id, name=repo_result.name
        )

    # ── edit_task: fetch → domain → build → no-op check → delegate ──

    async def edit_task(self, command: EditTaskCommand) -> EditTaskResult:
        from omnifocus_operator.contracts.base import _Unset
        from omnifocus_operator.contracts.use_cases.edit_task import EditTaskResult

        # 1. Verify task exists
        task = await self._repository.get_task(command.id)
        if task is None:
            raise ValueError(f"Task not found: {command.id}")

        validate_task_name_if_set(command.name)  # raises if empty string

        # 2. _Unset checks — orchestrator decides what to call
        has_actions = not isinstance(command.actions, _Unset)
        has_lifecycle = (
            has_actions
            and not isinstance(command.actions.lifecycle, _Unset)
        )
        has_tag_actions = (
            has_actions
            and not isinstance(command.actions.tags, _Unset)
        )
        has_move = (
            has_actions
            and not isinstance(command.actions.move, _Unset)
        )

        # 3. Domain: lifecycle, status warnings
        lifecycle = None
        lifecycle_warns: list[str] = []
        if has_lifecycle:
            lifecycle_action = command.actions.lifecycle
            should_call, lifecycle_warns = self._domain.process_lifecycle(
                lifecycle_action, task  # clean str, not _Unset
            )
            if should_call:
                lifecycle = lifecycle_action

        status_warns = self._domain.check_completed_status(
            task, has_lifecycle
        )

        # 4. Domain: tag diff
        tag_adds: list[str] | None = None
        tag_removes: list[str] | None = None
        tag_warns: list[str] = []
        if has_tag_actions:
            tag_adds, tag_removes, tag_warns = (
                await self._domain.compute_tag_diff(
                    command.actions.tags, task.tags
                )
            )

        # 5. Domain: move processing
        move_to: dict[str, object] | None = None
        if has_move:
            move_to = await self._domain.process_move(
                command.actions.move, command.id
            )

        # 6. Build payload
        repo_payload = self._payload.build_edit(
            command, lifecycle, tag_adds, tag_removes, move_to
        )

        # 7. Domain: no-op + empty-edit detection
        all_warnings = lifecycle_warns + status_warns + tag_warns
        early = self._domain.detect_early_return(
            repo_payload, task, all_warnings
        )
        if early is not None:
            return early

        # 8. Delegate
        repo_result = await self._repository.edit_task(repo_payload)
        return EditTaskResult(
            success=True, id=repo_result.id, name=repo_result.name,
            warnings=all_warnings or None,
        )
```

### service/resolve.py — Input resolution

```python
def validate_task_name(name: str | None) -> None:
    """Raise ValueError if name is empty or whitespace."""
    if not name or not name.strip():
        raise ValueError("Task name is required")


class Resolver:
    """Resolves user-facing identifiers against the repository."""

    def __init__(self, repo: Repository) -> None:
        self._repo = repo

    async def resolve_parent(self, parent_id: str) -> str:
        """Verify parent exists as project or task.
        Returns the ID. Raises ValueError if not found.
        """
        # Project-first resolution (PROJECT.md key decision)
        project = await self._repo.get_project(parent_id)
        if project is not None:
            return parent_id
        task = await self._repo.get_task(parent_id)
        if task is not None:
            return parent_id
        raise ValueError(f"Parent not found: {parent_id}")

    async def resolve_tags(self, tag_names: list[str]) -> list[str]:
        """Resolve tag names to IDs (case-insensitive).
        Falls back to ID lookup if name doesn't match.
        """
        all_data = await self._repo.get_all()
        resolved: list[str] = []
        for name in tag_names:
            tag_id = self._match_tag(name, all_data.tags)
            resolved.append(tag_id)
        return resolved

    def _match_tag(self, name: str, tags: list[Tag]) -> str:
        """Find a single tag by name (case-insensitive) or ID."""
        matches = [t for t in tags if t.name.lower() == name.lower()]
        if len(matches) == 1:
            return matches[0].id
        if len(matches) > 1:
            ids = ", ".join(m.id for m in matches)
            raise ValueError(f"Ambiguous tag '{name}': multiple matches ({ids})")
        # No name match — try as ID fallback
        id_match = next((t for t in tags if t.id == name), None)
        if id_match is not None:
            return id_match.id
        raise ValueError(f"Tag not found: {name}")
```

### service/domain.py — Business rules

```python
class DomainLogic:
    def __init__(self, repo: Repository, resolver: Resolver) -> None:
        self._repo = repo
        self._resolver = resolver

    # ── Lifecycle ─────────────────────────────────────────

    def process_lifecycle(
        self, action: str, task: Task
    ) -> tuple[bool, list[str]]:
        """Returns (should_call_bridge, warnings)."""
        warnings: list[str] = []
        target = Availability.COMPLETED if action == "complete" else Availability.DROPPED

        # No-op: already in target state
        if task.availability == target:
            state_word = "complete" if action == "complete" else "dropped"
            warnings.append(LIFECYCLE_ALREADY_IN_STATE.format(state_word=state_word))
            return False, warnings

        # Cross-state: completed <-> dropped
        if task.availability in (Availability.COMPLETED, Availability.DROPPED):
            prior_state = task.availability.value
            new_state = "complete" if action == "complete" else "dropped"
            warnings.append(
                LIFECYCLE_CROSS_STATE.format(prior_state=prior_state, new_state=new_state)
            )

        # Repeating task
        if task.repetition_rule is not None:
            if action == "complete":
                warnings.append(LIFECYCLE_REPEATING_COMPLETE)
            else:
                warnings.append(LIFECYCLE_REPEATING_DROP)

        return True, warnings

    # ── Status warnings ──────────────────────────────────

    def check_completed_status(
        self, task: Task, has_lifecycle: bool
    ) -> list[str]:
        """Warn if editing a completed/dropped task without lifecycle action."""
        if not has_lifecycle and task.availability in (
            Availability.COMPLETED, Availability.DROPPED
        ):
            return [EDIT_COMPLETED_TASK.format(status=task.availability.value)]
        return []

    # ── Tags ─────────────────────────────────────────────

    async def compute_tag_diff(
        self, tag_actions: TagAction, current_tags: list[TagRef]
    ) -> tuple[list[str], list[str], list[str]]:
        """Returns (add_ids, remove_ids, warnings)."""
        current_ids = {t.id for t in current_tags}
        tag_names = await self._build_tag_name_map()

        if has_replace:
            final, warns = await self._apply_replace(tag_actions, current_ids, tag_names)
        elif has_add and has_remove:
            final, warns = await self._apply_add_remove(tag_actions, current_ids, tag_names)
        elif has_add:
            final, warns = await self._apply_add(tag_actions, current_ids, tag_names)
        elif has_remove:
            final, warns = await self._apply_remove(tag_actions, current_ids, tag_names)
        else:
            final = current_ids
            warns = []

        return list(final - current_ids), list(current_ids - final), warns

    async def _apply_add(
        self, tag_actions: TagAction, current_ids: set[str], tag_names: dict[str, str]
    ) -> tuple[set[str], list[str]]:
        """Resolve add tags, warn if already present. Returns (final_set, warnings)."""
        resolved = await self._resolver.resolve_tags(tag_actions.add)
        warns = [
            TAG_ALREADY_ON_TASK.format(display=tag_names.get(rid, name), tag_id=rid)
            for name, rid in zip(tag_actions.add, resolved)
            if rid in current_ids
        ]
        return current_ids | set(resolved), warns

    # _apply_remove, _apply_replace, _apply_add_remove follow the same pattern:
    # resolve → per-tag warnings → compute final set

    async def _build_tag_name_map(self) -> dict[str, str]:
        """Build tag ID -> name map for warning display names."""
        all_data = await self._repo.get_all()
        return {t.id: t.name for t in all_data.tags}

    # ── Cycle detection ──────────────────────────────────

    async def check_cycle(self, task_id: str, container_id: str) -> None:
        """Raises ValueError if move would create circular ref."""
        all_data = await self._repo.get_all()
        task_map = {t.id: t for t in all_data.tasks}
        current = container_id
        while current is not None:
            if current == task_id:
                raise ValueError("Cannot move task: would create circular reference")
            t = task_map.get(current)
            if t is None or t.parent is None or t.parent.type != "task":
                break
            current = t.parent.id

    # ── No-op detection ──────────────────────────────────

    def detect_early_return(
        self, payload: EditTaskRepoPayload, task: Task, warnings: list[str]
    ) -> EditTaskResult | None:
        """Returns early result if edit is empty or a no-op, else None."""
        if self._is_empty_edit(payload, warnings):
            if warnings:
                return EditTaskResult(success=True, id=payload.id, name=task.name, warnings=warnings)
            return EditTaskResult(
                success=True, id=payload.id, name=task.name,
                warnings=[EDIT_NO_CHANGES_SPECIFIED],
            )
        if self._all_fields_match(payload, task):
            # No-op takes priority over status warnings
            filtered = [w for w in warnings if "your changes were applied" not in w]
            if not filtered:
                filtered = [EDIT_NO_CHANGES_DETECTED]
            return EditTaskResult(success=True, id=payload.id, name=task.name, warnings=filtered)
        return None

    def _is_empty_edit(self, payload: EditTaskRepoPayload, warnings: list[str]) -> bool:
        """Only 'id' in payload, nothing to change."""
        # Check if the payload has any fields set beyond 'id'
        ...

    def _all_fields_match(self, payload: EditTaskRepoPayload, task: Task) -> bool:
        """Compare each payload field against current task state."""
        # Uses _to_utc_ts for date comparison
        ...

    # ── Move processing ──────────────────────────────────

    async def process_move(
        self, move_action: MoveAction, task_id: str
    ) -> dict[str, object]:
        """Resolve, validate, cycle-check a move. Returns move_to dict."""
        position, target_id = self._extract_move_target(move_action)

        if position in ("beginning", "ending"):
            return await self._process_container_move(position, target_id, task_id)
        # position in ("before", "after")
        return await self._process_anchor_move(position, target_id)

    async def _process_container_move(
        self, position: str, container_id: str | None, task_id: str
    ) -> dict[str, object]:
        """Move to beginning/ending of a container (or inbox if None)."""
        if container_id is None:
            return {"position": position, "container_id": None}

        # Verify container exists (project or task)
        await self._resolver.resolve_parent(container_id)

        # If container is a task, check for circular reference
        container_task = await self._repo.get_task(container_id)
        if container_task is not None:
            await self.check_cycle(task_id, container_id)

        return {"position": position, "container_id": container_id}

    async def _process_anchor_move(
        self, position: str, anchor_id: str
    ) -> dict[str, object]:
        """Move before/after a sibling task."""
        anchor = await self._repo.get_task(anchor_id)
        if anchor is None:
            raise ValueError(f"Anchor task not found: {anchor_id}")
        return {"position": position, "anchor_id": anchor_id}

    def _extract_move_target(
        self, move_action: MoveAction
    ) -> tuple[str, str | None]:
        """Find which position key is set. Returns (position, target_id)."""
        from omnifocus_operator.contracts.base import _Unset
        for key in ("beginning", "ending", "before", "after"):
            value = getattr(move_action, key)
            if not isinstance(value, _Unset):
                return key, value
        raise ValueError("No position key set on move action")
```

### service/payload.py — Typed payload construction

```python
class PayloadBuilder:
    """Assembles typed repo payloads from processed command data."""

    def build_add(
        self,
        command: CreateTaskCommand,
        resolved_tag_ids: list[str] | None,
    ) -> CreateTaskRepoPayload:
        """Build add-task payload. Only includes populated fields."""
        kwargs: dict[str, object] = {"name": command.name}
        if command.parent is not None:
            kwargs["parent"] = command.parent
        if resolved_tag_ids is not None:
            kwargs["tag_ids"] = resolved_tag_ids
        if command.due_date is not None:
            kwargs["due_date"] = command.due_date.isoformat()
        if command.defer_date is not None:
            kwargs["defer_date"] = command.defer_date.isoformat()
        if command.planned_date is not None:
            kwargs["planned_date"] = command.planned_date.isoformat()
        if command.flagged is not None:
            kwargs["flagged"] = command.flagged
        if command.estimated_minutes is not None:
            kwargs["estimated_minutes"] = command.estimated_minutes
        if command.note is not None:
            kwargs["note"] = command.note
        return CreateTaskRepoPayload.model_validate(kwargs)

    def build_edit(
        self,
        command: EditTaskCommand,
        lifecycle: str | None,
        add_tag_ids: list[str] | None,
        remove_tag_ids: list[str] | None,
        move_to: dict[str, object] | None,
    ) -> EditTaskRepoPayload:
        """Build edit-task payload from command + domain results."""

        # --- 1. Extract command fields ---
        kwargs: dict[str, object] = {"id": command.id}

        # Simple fields (name, note, flagged, estimated_minutes)
        self._add_if_set(kwargs, command, "name", "note", "flagged", "estimated_minutes")

        # note=None means 'clear' -> OmniFocus wants empty string
        if "note" in kwargs and kwargs["note"] is None:
            kwargs["note"] = ""

        # Date fields -> ISO strings (None stays None = clear)
        self._add_dates_if_set(kwargs, command, "due_date", "defer_date", "planned_date")

        # --- 2. Merge domain results ---
        if lifecycle is not None:
            kwargs["lifecycle"] = lifecycle
        if add_tag_ids:
            kwargs["add_tag_ids"] = add_tag_ids
        if remove_tag_ids:
            kwargs["remove_tag_ids"] = remove_tag_ids
        if move_to is not None:
            kwargs["move_to"] = MoveToRepoPayload(**move_to)

        # --- 3. Build typed payload ---
        return EditTaskRepoPayload.model_validate(kwargs)

    def _add_if_set(self, kwargs: dict, command: object, *fields: str) -> None:
        """Add non-UNSET command fields to kwargs dict."""
        from omnifocus_operator.contracts.base import _Unset
        for field in fields:
            value = getattr(command, field)
            if not isinstance(value, _Unset):
                kwargs[field] = value

    def _add_dates_if_set(self, kwargs: dict, command: object, *fields: str) -> None:
        """Add non-UNSET date fields, serialized to ISO string."""
        from omnifocus_operator.contracts.base import _Unset
        for field in fields:
            value = getattr(command, field)
            if not isinstance(value, _Unset):
                kwargs[field] = value.isoformat() if value is not None else None
```

### Test strategy

```
tests/
├── test_service.py              # EXISTING — stays as integration (full pipeline through OperatorService)
├── test_service_resolve.py      # NEW — Resolver unit tests (real InMemoryRepo)
├── test_service_domain.py       # NEW — DomainLogic unit tests (stub Resolver, no InMemoryRepo dependency)
└── test_service_payload.py      # NEW — PayloadBuilder unit tests (pure, no dependencies)
```

- Mirror module structure: one test file per extracted module
- Move existing test_service.py tests that specifically test extracted logic into the new files
- test_service.py keeps only integration tests (full add_task/edit_task flows)
- DomainLogic tests use stub Resolver (not InMemoryRepository) — avoids dependency on InMemoryRepo which is being replaced in Phase 26
- Resolver tests use real InMemoryRepository (will naturally migrate in Phase 26)
- PayloadBuilder tests are pure data transformation — no repo, no stubs

**DomainLogic test fixture example:**
```python
class StubResolver:
    """Returns pre-configured IDs. No InMemoryRepository dependency."""
    def __init__(self, tag_map: dict[str, str]):
        self._tag_map = tag_map

    async def resolve_tags(self, names: list[str]) -> list[str]:
        return [self._tag_map[n] for n in names]

    async def resolve_parent(self, pid: str) -> str:
        return pid  # always succeeds

@pytest.fixture
def domain():
    resolver = StubResolver({"Work": "t1", "Home": "t2"})
    repo = ...  # minimal fake for check_cycle / get_all
    return DomainLogic(repo, resolver)
```

**PayloadBuilder test example (pure, no dependencies):**
```python
def test_build_add_minimal():
    builder = PayloadBuilder()
    command = CreateTaskCommand(name="Buy milk")
    payload = builder.build_add(command, resolved_tag_ids=None)
    assert payload.name == "Buy milk"
    # No parent, no tags, no dates — only name in payload
```

### Claude's Discretion

- Exact internal structure of `_all_fields_match` and `_is_empty_edit` in DomainLogic
- Whether `_add_if_set` and `_add_dates_if_set` in PayloadBuilder are methods or standalone helpers
- Stub Resolver implementation details for DomainLogic tests (the example above is a starting point)
- Exact logging message content (preserve existing messages where possible)
- Import organization within each module
- Whether `validate_task_name_if_set` (for edit_task's optional name) is a separate function or handled inline

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & contracts
- `docs/architecture.md` — Model Taxonomy section, protocol signatures, write pipeline flow
- `src/omnifocus_operator/contracts/protocols.py` — Service, Repository, Bridge protocols (Service protocol must be implemented)
- `src/omnifocus_operator/contracts/use_cases/create_task.py` — CreateTaskCommand, CreateTaskRepoPayload, CreateTaskResult
- `src/omnifocus_operator/contracts/use_cases/edit_task.py` — EditTaskCommand, EditTaskRepoPayload, MoveToRepoPayload, EditTaskResult

### Current service (the file being decomposed)
- `src/omnifocus_operator/service.py` — All 669 lines being split into the package

### Requirements
- `.planning/REQUIREMENTS.md` — SVCR-01 through SVCR-05 definitions

### Prior phase context
- `.planning/phases/20-model-taxonomy/20-CONTEXT.md` — Naming convention, contracts/ package, typed payloads
- `.planning/phases/21-write-pipeline-unification/21-CONTEXT.md` — Unified pipeline pattern, BridgeWriteMixin, exclude_unset standardization

### Future dependency (informational)
- `.planning/todos/pending/2026-03-19-replace-inmemoryrepository-with-stateful-inmemorybridge.md` — Phase 26 will replace InMemoryRepository; new DomainLogic tests should not depend on it

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `contracts/protocols.py`: Service protocol exists but OperatorService doesn't declare conformance — this phase fixes that
- `contracts/base.py`: `_Unset`, `UNSET` sentinel — used by orchestrator for flow control, not passed to domain/resolve modules
- `warnings.py`: Warning string constants — used by domain.py for all warning generation
- `BridgeWriteMixin` (repository/): Established pattern for extracting shared functionality into a mixin — similar decomposition approach

### Established Patterns
- `repository/` package: implementations in their own files (hybrid.py, bridge.py), `__init__.py` re-exports — same pattern for service/
- Phase 21 kwargs dict → `model_validate()` pattern — PayloadBuilder follows this for both add and edit
- `@_ensures_write_through` decorator on HybridRepository — unaffected by this phase

### Integration Points
- `server.py`: imports `OperatorService`, `ErrorOperatorService` from `omnifocus_operator.service` — import path preserved via `__init__.py` re-export
- `contracts/protocols.py`: Service protocol — both service classes must declare conformance
- `test_service.py`: existing tests need splitting into module-specific test files

</code_context>

<specifics>
## Specific Ideas

- "I come from the Java world with DDD and CQRS" — classes with dependency injection preferred over bare functions with passed parameters
- "I would love to see how you plan on building the domain logic" — domain.py should have clear visual grouping (section separators) and well-decomposed private helpers
- "This method shouldn't be just one block of unreadable code" — public domain methods delegate to focused private helpers (e.g., `process_move` → `_extract_move_target`, `_process_container_move`, `_process_anchor_move`)
- "As long as we can keep the service small" — the orchestrator must be visibly thin after extraction; that's the whole point
- Service protocol conformance: "it's quite a big deal" — explicitly declaring protocol implementation, not just structural typing

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 22-service-decomposition*
*Context gathered: 2026-03-19*
