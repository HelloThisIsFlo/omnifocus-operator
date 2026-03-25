# Technology Stack

**Project:** OmniFocus Operator v1.2.1 -- Architectural Cleanup
**Researched:** 2026-03-16

## Key Finding: Zero New Dependencies, Leverage Existing Stack Harder

v1.2.1 requires **no new runtime or dev dependencies**. This milestone is pure internal refactoring using Pydantic v2 (2.12.5) features and Python 3.12 module patterns already in the stack. The work is about using what's there more deliberately.

---

## What Changes (v1.2.1 patterns only)

### 1. Strict Write Model Validation (`extra="forbid"`)

**Problem:** `OmniFocusBaseModel` uses default `extra="ignore"`. Write models silently drop unknown fields -- an agent sending `{"name": "Test", "repetitionRule": "weekly"}` gets no error.

**Solution:** Introduce a `WriteModel` intermediate base class.

| Aspect | Detail | Confidence |
|--------|--------|------------|
| Mechanism | `ConfigDict(extra="forbid")` on a `WriteModel` subclass of `OmniFocusBaseModel` | HIGH -- Pydantic 2.12.5 docs confirm ConfigDict merges on inheritance |
| Inheritance behavior | Child ConfigDict **merges** with parent -- `WriteModel` sets `extra="forbid"`, inherits `alias_generator=to_camel` and `validate_by_name=True` from `OmniFocusBaseModel` | HIGH -- verified in Pydantic docs |
| Error type | `ValidationError` with error type `extra_forbidden` | HIGH -- Pydantic docs |
| Error message | Pydantic auto-generates clear message: `"Extra inputs are not permitted"` | HIGH |
| Read models | Stay on `OmniFocusBaseModel` (default `extra="ignore"`) -- OmniFocus may return fields we don't model yet | N/A -- design decision, not stack question |

**Implementation pattern:**

```python
# models/base.py -- add WriteModel
class WriteModel(OmniFocusBaseModel):
    """Base for all write specs. Rejects unknown fields."""
    model_config = ConfigDict(extra="forbid")

# models/write.py -- change parent
class TaskCreateSpec(WriteModel):  # was OmniFocusBaseModel
    name: str
    # ... rest unchanged
```

**Why this works cleanly:**
- ConfigDict merge in Pydantic v2 is additive -- child sets only `extra="forbid"`, inherits everything else from parent (`alias_generator`, `validate_by_name`, `validate_by_alias`)
- All existing tests pass because valid inputs don't have extra fields
- The mypy plugin's `init_forbid_extra = true` in `pyproject.toml` already enforces this at type-check time for `__init__` calls, but `model_validate(dict)` bypasses mypy -- `extra="forbid"` catches it at runtime too
- No MRO issues: single inheritance chain, no diamond

**Pitfall to avoid:**
- Do NOT set `extra="forbid"` on `OmniFocusBaseModel` itself. Read models (Task, Project, Tag, etc.) must stay permissive because OmniFocus SQLite schema or bridge JSON may contain fields we haven't modeled yet. Breaking read models is a production outage.

### 2. Service Layer Decomposition -- Module Patterns

**Problem:** `service.py` is 637 lines mixing orchestration, validation, domain logic (tag diff, lifecycle, no-op detection), and format conversion (snake_case -> camelCase payload building).

**Solution:** Extract cohesive modules within the service layer. Use plain Python modules with functions, not classes.

| Pattern | Use For | Why |
|---------|---------|-----|
| Module with functions | Validation, format conversion, domain logic | Simplest possible extraction. No class ceremony. Functions are stateless -- they take inputs and return outputs. Easy to test, easy to import |
| Service class stays | Orchestration (validate -> resolve -> convert -> delegate) | Needs repository reference for lookups. Class holds the dependency |
| Protocol stays | Repository boundary | Already using structural typing via `Protocol`. No change needed |

**Recommended module structure:**

```
src/omnifocus_operator/
    service/                    # Package replaces single file
        __init__.py             # Re-exports OperatorService, ErrorOperatorService
        _orchestrator.py        # OperatorService class (orchestration only)
        _validation.py          # Input validation functions
        _domain.py              # Domain logic (tag diff, lifecycle, no-op detection)
        _payload.py             # Format conversion (spec -> bridge-ready dict)
```

**Why functions, not classes:**
- Validation, domain logic, and format conversion are stateless transformations
- `validate_task_name(name: str) -> None` is clearer than `TaskValidator().validate_name(name)`
- Functions compose: `payload = build_edit_payload(spec, task, tag_diff)`
- No need for dependency injection -- these don't need the repository
- YAGNI: classes add indirection without benefit when there's no state to manage

**Why underscore-prefixed modules:**
- Convention for internal modules in Python packages
- Signals "import from the package, not the module directly"
- `from omnifocus_operator.service import OperatorService` still works via `__init__.py`

**What NOT to do:**
- Do NOT create abstract base classes for each concern. No `Validator` ABC, no `PayloadBuilder` ABC. These are internal implementation details, not extension points
- Do NOT create a `domain/` sub-package. One level of extraction is enough. If `_domain.py` grows past ~200 lines, revisit then
- Do NOT over-separate. Tag diff computation and lifecycle processing are both "domain logic" -- they belong in the same module even though they operate on different data

### 3. Write Pipeline Unification -- Repository Protocol

**Problem:** `add_task` and `edit_task` have asymmetric signatures at the service-repository boundary:

| Aspect | `add_task` (current) | `edit_task` (current) |
|--------|---------------------|----------------------|
| Service passes | `TaskCreateSpec` + `resolved_tag_ids` kwarg | `dict[str, Any]` (fully bridge-ready) |
| Who serializes | Repository (`model_dump`) | Service (builds dict field-by-field) |
| Return type | `TaskCreateResult` (typed) | `dict[str, Any]` (raw) |

**Solution:** Both paths should pass a bridge-ready `dict[str, Any]` payload to the repository. Service owns all serialization. Repository is a thin pass-through to bridge.

| Aspect | After unification |
|--------|------------------|
| Service builds | Bridge-ready `dict[str, Any]` for both add and edit |
| Repository receives | `dict[str, Any]` payload for both |
| Repository role | Pass payload to `bridge.send_command()`, return typed result |
| Return type | Typed Pydantic model for both (`TaskCreateResult`, `TaskEditResult`) |

**Protocol change:**

```python
class Repository(Protocol):
    # ... reads unchanged ...

    async def add_task(self, payload: dict[str, Any]) -> TaskCreateResult:
        """Create a task from bridge-ready payload."""
        ...

    async def edit_task(self, payload: dict[str, Any]) -> TaskEditResult:
        """Edit a task from bridge-ready payload."""
        ...
```

**Why dict payload (not spec models) at the boundary:**
- The repository doesn't validate or transform -- it sends to bridge. Receiving a dict is honest about that role
- Service already builds the dict for edit_task today -- just extend the pattern to add_task
- Typed return values give the server layer something safe to work with
- The format conversion module (`_payload.py`) owns the spec-to-dict transformation for both paths

**What about InMemoryRepository in tests?**
- InMemoryRepository for tests also receives `dict[str, Any]` -- it can store it or extract fields as needed
- This is simpler than having test doubles parse spec models

### 4. Moving InMemoryBridge Out of Production Exports

**Problem:** `InMemoryBridge` is a test double (call tracking, error simulation) but lives in `src/` and is exported from `bridge/__init__.py`.

**What's needed (no new tech):**
- Remove from `bridge/__init__.py` exports
- Remove `"inmemory"` branch from bridge factory
- Update test imports: `from omnifocus_operator.bridge.in_memory import InMemoryBridge`
- File stays in `src/` (moving to `tests/` is optional and can come later)

**Why keep the file in `src/` for now:**
- The file is small (68 lines), well-bounded, and doesn't pollute the public API once removed from `__init__.py`
- Moving to `tests/` requires updating `[tool.coverage.run]` source paths, potentially changing import mechanics
- Direct module import (`from omnifocus_operator.bridge.in_memory import ...`) still works and is the correct pattern for test utilities that live alongside production code

---

## Existing Stack (Unchanged)

### Runtime

| Technology | Version | Purpose | Status |
|------------|---------|---------|--------|
| Python | 3.12+ | Runtime | Unchanged |
| `mcp` | >=1.26.0 | MCP SDK (FastMCP) | Unchanged, sole runtime dep |
| Pydantic | v2.12.5 (via mcp) | Models, validation | Unchanged -- using more features (ConfigDict merge, extra="forbid") |
| sqlite3 | stdlib | Read path | Unchanged |
| asyncio | stdlib | Async runtime | Unchanged |

### Dev Dependencies (Unchanged)

| Library | Version | Purpose |
|---------|---------|---------|
| ruff | >=0.15.0 | Linting/formatting |
| mypy | >=1.19.1 (strict) | Type checking + pydantic.mypy plugin |
| pytest | >=9.0.2 | Testing |
| pytest-asyncio | >=1.3.0 | Async test support |
| pytest-cov | >=7.0.0 | Coverage |
| pytest-timeout | >=2.4.0 | Test timeouts |
| pre-commit | >=4.0.0 | Pre-commit hooks |

### Mypy Configuration (Relevant)

```toml
[tool.mypy]
strict = true
plugins = ["pydantic.mypy"]

[tool.pydantic-mypy]
init_forbid_extra = true    # Already catches __init__ extra args at type-check
init_typed = true
warn_required_dynamic_aliases = true
```

The `init_forbid_extra = true` setting means mypy already flags `Model(unknown_field=x)` calls. But `Model.model_validate({"unknown_field": "x"})` bypasses mypy -- only runtime `extra="forbid"` catches that. Both layers are needed.

---

## Pydantic v2 Features Used

| Feature | Version | Purpose | Confidence |
|---------|---------|---------|------------|
| `ConfigDict(extra="forbid")` | 2.0+ | Reject unknown fields on write models | HIGH -- official docs, verified in 2.12.5 |
| ConfigDict inheritance merge | 2.0+ | `WriteModel` inherits `alias_generator` from parent, adds `extra="forbid"` | HIGH -- official docs confirm additive merge |
| `_Unset` sentinel with `__get_pydantic_core_schema__` | 2.0+ | Patch semantics (already implemented) | HIGH -- in production since v1.2 |
| `model_validator(mode="after")` | 2.0+ | Mutual exclusivity checks (already implemented) | HIGH -- in production since v1.2 |
| `ValidationError` with `extra_forbidden` type | 2.0+ | Clear error when agent sends unknown fields | HIGH -- official docs |

---

## Python 3.12 Features Used

| Feature | Purpose | Notes |
|---------|---------|-------|
| `type` statement (PEP 695) | Not needed | Existing generic syntax (`[F: Callable[..., Any]]`) works fine |
| `Protocol` (structural typing) | Repository boundary | Already in use, no changes needed |
| Modules as namespaces | Service decomposition | Package with `__init__.py` re-exports |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Write model strictness | `WriteModel` intermediate class with `extra="forbid"` | Set `extra="forbid"` directly on each write spec | Intermediate class is DRY -- one place to change, clear inheritance chain |
| Write model strictness | `WriteModel` intermediate class | `model_validate(..., strict=True)` at call site | Caller-side enforcement is fragile -- easy to forget. Model-level is declarative |
| Service decomposition | Module with functions (`_validation.py`, etc.) | New classes (`TaskValidator`, `PayloadBuilder`) | Stateless transforms don't need classes. Functions are simpler, compose better |
| Service decomposition | Single-level package (`service/`) | Nested packages (`service/validation/`, etc.) | Over-engineering for ~600 lines of logic. One level is enough |
| Repository write interface | `dict[str, Any]` payload for both paths | Typed spec models at boundary | Repository is a pass-through to bridge -- dict is honest. Service owns the types |
| InMemoryBridge location | Keep in `src/`, remove from exports | Move to `tests/` directory | Smaller change surface. Coverage config stays simple. Can move later if needed |

---

## What NOT to Do

- **No new dependencies.** Zero. Not even dev deps.
- **No abstract base classes** for internal concerns. `Validator` ABC with a single implementation is textbook over-engineering.
- **No dependency injection framework.** Repository is injected via constructor. Extracted modules are imported as functions. That's enough.
- **No event system / pub-sub** for service decomposition. Direct function calls. The codebase has 6 tools and 2 write paths -- no need for indirection.
- **No generic payload builder pattern.** The two write paths (add/edit) have different logic (edit has patch semantics, lifecycle, move, tag diff). A generic builder would obscure the differences. Two explicit paths with shared utility functions.
- **No `dataclass` for intermediate DTOs.** The bridge payload is `dict[str, Any]` -- that's the format the bridge accepts. No need to wrap it in a typed intermediate just to unwrap it one function call later.

---

## Installation

```bash
# Nothing to install. Zero new dependencies.
# Existing `uv sync` is sufficient.
```

---

## Sources

- [Pydantic v2 Configuration docs (2.12.5)](https://docs.pydantic.dev/latest/concepts/config/) -- ConfigDict inheritance merge behavior, `extra` parameter -- HIGH confidence
- [Pydantic v2 Models docs (2.12.5)](https://docs.pydantic.dev/latest/concepts/models/) -- `extra="forbid"` behavior -- HIGH confidence
- [Pydantic v2 Validation Errors (2.12.5)](https://docs.pydantic.dev/latest/errors/validation_errors/) -- `extra_forbidden` error type and message format -- HIGH confidence
- [Pydantic mypy integration docs](https://docs.pydantic.dev/latest/integrations/mypy/) -- `init_forbid_extra` interaction with ConfigDict -- HIGH confidence
- [Pydantic ConfigDict inheritance discussion #7778](https://github.com/pydantic/pydantic/discussions/7778) -- confirms merge behavior in practice -- MEDIUM confidence
- [PEP 544 -- Protocols: Structural subtyping](https://peps.python.org/pep-0544/) -- Protocol usage for Repository boundary -- HIGH confidence
- [Mypy Protocols documentation](https://mypy.readthedocs.io/en/stable/protocols.html) -- structural typing with strict mypy -- HIGH confidence
- Existing codebase direct inspection: `service.py`, `models/write.py`, `models/base.py`, `repository/protocol.py`, `bridge/__init__.py`, `hybrid.py`
- MILESTONE-v1.2.1.md -- milestone spec

---
*Stack research for: OmniFocus Operator v1.2.1 Architectural Cleanup*
*Researched: 2026-03-16*
