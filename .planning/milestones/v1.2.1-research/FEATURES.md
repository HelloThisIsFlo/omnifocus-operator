# Feature Landscape

**Domain:** Service layer decomposition and write pipeline unification for OmniFocus MCP server (v1.2.1)
**Researched:** 2026-03-16

## Table Stakes

Internal quality features that are expected of a well-structured service layer. Missing = the codebase becomes harder to extend with each new milestone.

| Feature | Why Expected | Complexity | Dependencies |
|---------|--------------|------------|--------------|
| Symmetric write protocol signatures | Both `add_task` and `edit_task` should follow the same pattern at the service-repository boundary. Currently `add_task` passes typed spec + resolved kwargs; `edit_task` passes raw `dict[str, Any]`. Asymmetry forces every new write operation to invent its own convention | Med | Repository protocol change, InMemoryRepository/HybridRepository updates, existing tests |
| Service orchestrates, doesn't implement | Service class should be a ~10-line orchestration flow per method: validate -> resolve -> convert -> delegate. Currently `edit_task` is ~280 lines mixing all concerns | Med | Extraction of validation, domain logic, conversion modules |
| Validation as a separate concern | Input validation (name required, parent exists, tag resolution, anchor exists) is interleaved with domain logic (no-op detection, lifecycle guards) and format conversion (camelCase payload building). Each should be independently testable | Med | New `validation` module within service package |
| Domain logic extraction | Tag diff computation, lifecycle state machine, no-op detection, cycle detection -- these are domain rules, not orchestration. Should live in their own module | Med | New `domain` or `policies` module within service package |
| Format conversion extraction | snake_case -> camelCase mapping, date serialization, `note=None -> ""` normalization, tag name/ID swapping -- mechanical transforms that bloat service methods | Low | New `conversion` or `payload` module within service package |
| Strict write model validation (`extra="forbid"`) | Write models silently discard unknown fields. Agent sends `{"repetitionRule": "weekly"}` -- no error, field vanishes. Table stakes for any write API that agents call | Low | `WriteModel` base class or per-model `model_config` override |
| Read models stay permissive | OmniFocus SQLite may return columns we don't model yet. Read models must keep `extra="ignore"` (Pydantic default) so new OmniFocus versions don't break reads | None | Already the default -- just don't change it |
| InMemoryBridge out of production exports | Test doubles in production `__init__.py` exports and factory is a code smell. Tests should import from direct module paths | Low | `bridge/__init__.py` cleanup, factory removal of `"inmemory"` branch, test import updates |

## Differentiators

Features that go beyond "clean code" to make the architecture genuinely better for future development.

| Feature | Value Proposition | Complexity | Dependencies |
|---------|-------------------|------------|--------------|
| Typed bridge payload model | Instead of `dict[str, Any]` crossing the service-repository boundary, use a typed `BridgePayload` or `WriteCommand` model. Makes the contract explicit and enables Pydantic validation at the boundary | Med | New payload model, repository protocol update |
| Shared resolution module | Parent resolution, tag resolution, and anchor resolution are used by both `add_task` and `edit_task`. Extracting to a shared resolver makes adding future write operations (project edits, tag writes) trivial | Low | Extract `_resolve_parent`, `_resolve_tags` into resolution module |
| Composable validation pipeline | Instead of per-method validation blocks, use composable validators (functions/classes) that can be chained. E.g., `validate_name(spec) |> validate_parent(spec, repo) |> validate_tags(spec, repo)`. Makes adding new validations for future write ops a one-liner | Med | Validation module design, async pipeline support |
| Service package (not module) | Promote `service.py` to `service/` package with `__init__.py`, `orchestrator.py`, `validation.py`, `domain.py`, `conversion.py`. Physical separation enforces boundaries better than discipline | Low | File restructuring, import updates |
| Edit return type parity | `edit_task` currently returns `dict[str, Any]` from repository and constructs `TaskEditResult` in service. Making repository return a typed result (like `add_task` does) removes dict-wrangling from service | Low | `TaskEditResult` construction in repository |

## Anti-Features

Features to explicitly NOT build in v1.2.1.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Generic command/handler framework | CQRS command handlers, message bus, mediator pattern -- overkill for 2 write operations. The goal is module extraction, not architectural astronautics | Simple function-based modules. Re-evaluate at v1.3+ when write operations multiply |
| Middleware/decorator validation chain | Express-style middleware stacks or decorator-based validation pipelines add indirection. The service methods are few enough that explicit orchestration is clearer | Explicit function calls in service methods: `validate_create(spec)`, `validate_edit(spec, task)` |
| Abstract base classes for modules | ABC for `Validator`, `DomainService`, `Converter` -- unnecessary when there's exactly one implementation of each. Protocols are fine if needed for testing, but not upfront | Plain modules with functions. Add protocols only when a second implementation appears |
| Separate domain model from Pydantic | The Cosmic Python pattern of separating domain entities from ORM/serialization models is correct for large systems but overkill here. The Pydantic models ARE the domain -- ~2,400 tasks, single-user, no ORM | Keep Pydantic models. The serialization overhead is zero in this context |
| Event sourcing for writes | Recording domain events from write operations sounds useful for audit trails but adds massive complexity for zero current need | Write operations are fire-and-forget through the bridge. OmniFocus is the source of truth |
| Moving InMemoryBridge to tests/ physically | Step 2 of the cleanup (physical relocation to `tests/`) adds import path complexity and breaks any external tooling that references it. Step 1 (removing from public exports) is sufficient | Remove from `__init__.py` exports and factory. Leave file in `src/` with a docstring marking it as test-only |
| Automated payload validation at repository boundary | Adding Pydantic validation on the bridge payload dict before sending to bridge -- the bridge itself validates and returns errors. Double-validation adds latency | Trust the service layer to produce valid payloads; bridge validates on its end |

## Feature Dependencies

```
Strict write model validation (extra="forbid")
  -- Independent. Can be done first as a quick win.
  -- No dependency on decomposition work.
  -- Requires: WriteModel base class or per-model config override.

InMemoryBridge export cleanup
  -- Independent. Can be done first or in parallel.
  -- No dependency on decomposition work.
  -- Requires: test import updates (find all `from omnifocus_operator.bridge import InMemoryBridge`).

Service decomposition: extraction of modules
  --> Requires understanding the full service.py to draw boundaries
  --> Must happen BEFORE symmetric write unification (unification is easier
      when concerns are already separated)
  --> Order within decomposition:
      1. Format conversion (most mechanical, least judgment)
      2. Validation (clear boundary: "is this request valid?")
      3. Domain logic (most interleaved with orchestration, extract last)

Symmetric write protocol signatures
  --> Depends on: service decomposition (separating concerns makes it obvious
      what the repository's role should be)
  --> Depends on: understanding where bridge payload construction should live
  --> Changes: Repository protocol, HybridRepository, InMemoryRepository
  --> Risk: largest blast radius -- touches both write paths + all tests
```

**Critical path:** `extra="forbid"` + InMemoryBridge cleanup (parallel, independent) --> Service decomposition (format -> validation -> domain) --> Symmetric write signatures

## MVP Recommendation

**Phase 1 -- Quick wins (independent, low risk):**
1. `WriteModel` base with `extra="forbid"` on `TaskCreateSpec`, `TaskEditSpec`, sub-specs
2. Remove `InMemoryBridge` from `bridge/__init__.py` exports and factory
3. Update test imports to use `from omnifocus_operator.bridge.in_memory import InMemoryBridge`

**Phase 2 -- Service decomposition (incremental extraction):**
4. Promote `service.py` to `service/` package
5. Extract format conversion: `service/conversion.py` -- payload building, camelCase mapping, date serialization, `note=None -> ""` normalization
6. Extract validation: `service/validation.py` -- name validation, parent resolution, tag resolution, anchor validation, empty-edit detection
7. Extract domain logic: `service/domain.py` -- tag diff computation, lifecycle state machine, no-op detection, cycle detection, status warnings

**Phase 3 -- Symmetric write signatures:**
8. Define the unified service-repository write contract (both operations follow same pattern)
9. Update `Repository` protocol with symmetric signatures
10. Update `HybridRepository` and `InMemoryRepository`
11. Update service orchestration to use the new contract

**Defer:** Typed `BridgePayload` model, composable validation pipeline -- nice-to-haves that can happen in future milestones when more write operations justify the abstraction.

**Ordering rationale:**
- Quick wins first: zero risk, immediate quality improvement, familiar refactoring scope
- Decomposition before unification: extracting concerns into modules reveals the natural boundary for the repository contract. Trying to unify the protocol while everything is tangled in one method leads to wrong abstractions
- Format conversion first within decomposition: most mechanical, least design judgment, gives confidence in the extraction pattern before tackling the harder modules
- Each phase has a clear "done" state and all tests pass throughout

## Three Validation Categories (from Cosmic Python)

This framework maps directly to the decomposition:

| Category | Definition | Where It Lives | Current Location | Target Location |
|----------|-----------|---------------|-----------------|----------------|
| **Syntax** | Structural: required fields, types, value ranges | Pydantic models at the edge | `TaskCreateSpec`, `TaskEditSpec` + `model_validate` in server.py | Same (already correct) + `extra="forbid"` |
| **Semantic** | Meaningful: referenced entities exist, operations make sense | Service-layer precondition checks | Mixed into `add_task` and `edit_task` methods | `service/validation.py` |
| **Pragmatic** | Domain rules: business constraints, state machine guards | Domain model or domain service module | Mixed into `edit_task` method | `service/domain.py` |

## Sources

- [Cosmic Python: Appendix E -- Validation](https://www.cosmicpython.com/book/appendix_validation.html) -- syntax/semantic/pragmatic validation categories, "ensure" pattern
- [Cosmic Python: Chapter 4 -- Service Layer](https://www.cosmicpython.com/book/chapter_04_service_layer.html) -- service layer orchestrates, delegates to domain and infrastructure
- [Pydantic v2 Models Documentation](https://docs.pydantic.dev/latest/concepts/models/) -- `extra="forbid"` config inheritance, `model_validate` override
- [Pydantic v2 Configuration](https://docs.pydantic.dev/latest/api/config/) -- `ConfigDict` options including `extra`, `strict`
- `.research/updated-spec/MILESTONE-v1.2.1.md` -- full milestone spec with asymmetry map and acceptance criteria
- `.planning/PROJECT.md` -- project context, key decisions, constraints
- [DDD Validation Across Layers](https://medium.com/@serhatalftkn/domain-driven-design-a-comprehensive-guide-to-validation-across-layers-8955d6854e7d) -- validation placement by layer in DDD
- [Enterprise Service Layer Pattern in Python](https://dev.to/ronal_daniellupacamaman/enterprise-design-pattern-implementing-the-service-layer-pattern-in-python-57mh) -- service layer as orchestration boundary
