# Milestone v1.2.1 — Project Summary

**Generated:** 2026-03-23
**Purpose:** Team onboarding and project review

---

## 1. Project Overview

OmniFocus Operator is a Python MCP server that exposes OmniFocus (macOS task manager) as structured task infrastructure for AI agents. It's designed as "executive function infrastructure that works at 7:30am" — reliable, simple, debuggable access to OmniFocus data.

- **6 MCP tools**: `get_all`, `get_task`, `get_project`, `get_tag`, `add_tasks`, `edit_tasks`
- **Read path**: SQLite cache (~46ms full snapshot, 30-60x faster than bridge-only)
- **Write path**: OmniJS bridge with write-through guarantee
- **Architecture**: Three-layer (MCP Server -> Service -> Repository) with pluggable bridge implementations
- **Tech stack**: Python 3.12, Pydantic v2, MCP SDK (FastMCP), OmniJS bridge, SQLite3 (stdlib)
- **Single runtime dependency**: `mcp>=1.26.0`

v1.2.1 "Architectural Cleanup" was a pure internal quality milestone — no new tools, no behavioral changes. All 6 MCP tools remained identical from the agent's perspective. The focus was cleaning up the internal architecture established during v1.2 (Writes & Lookups).

---

## 2. Architecture & Technical Decisions

### Model Layer

- **Three-layer model taxonomy** (Phase 20): Write-side models organized into Command (agent intent), RepoPayload (bridge format), RepoResult (bridge response), and Result (agent response). All models live in a `contracts/` package with 7 modules.
  - **Why:** After v1.2 shipped, write models were named inconsistently and mixed concerns across layers. The CQRS/DDD-inspired naming makes each model's role obvious from its class name.

- **Write model strictness** (Phase 18): Write models reject unknown fields (`extra="forbid"`), read models remain permissive (`extra="ignore"`).
  - **Why:** Agents can send typo'd fields (e.g., `"duedate"` instead of `"dueDate"`). Silent discard was the default; now Pydantic raises a clear ValidationError.

- **Patch[T]/PatchOrClear[T] type aliases** (Phase 25): Self-documenting annotations replace raw `T | _Unset` unions. `changed_fields()` helper on CommandModel returns only explicitly-set fields.
  - **Why:** The three-way patch semantics (unset/null/value) were invisible in type annotations. Aliases make the contract readable without checking docstrings.

### Service Layer

- **Service decomposition** (Phase 22): Monolithic 669-line `service.py` became a `service/` package with 5 modules — Resolver, DomainLogic, PayloadBuilder, Validator, and a thin orchestrator.
  - **Why:** All business logic was tangled in one file. Extraction made each concern independently testable and the orchestrator readable as a 9-step sequence.

- **Write pipeline unification** (Phase 21): `add_task` and `edit_task` follow identical patterns at every layer boundary — kwargs dict -> `model_validate()` -> typed payload. `BridgeWriteMixin` extracts shared `_send_to_bridge()`.
  - **Why:** The two write paths used different patterns for payload construction. Unifying them before service decomposition made extraction unambiguous.

- **Method Object pattern**: Every service use case gets a `_VerbNounPipeline` class — created, executed, and discarded within a single call. Mutable `self` is fine because the pipeline object is ephemeral.

### Test Infrastructure

- **Test double relocation** (Phases 19, 23, 24): All 5 test doubles moved from `src/` to `tests/doubles/`. Production code structurally cannot import test code.
  - **Why:** Convention ("don't import InMemoryBridge in production") is enforceable by humans but not by CI. Physical separation makes the boundary impossible to violate.

- **Stateful InMemoryBridge** (Phase 26): `InMemoryRepository` deleted. `InMemoryBridge` maintains mutable state and handles `add_task`/`edit_task` commands. Write tests exercise the real serialization path (`model_dump(by_alias=True)`, snapshot parsing).
  - **Why:** InMemoryRepository simulated write behavior independently of the bridge layer, so it could drift from real behavior silently.

- **StubBridge** (Phase 26): Extracted as a separate canned-response test double for tests that need predictable bridge output without stateful mutation.

- **Golden master contract testing** (Phases 27-28): 43 scenarios in 7 categories captured from RealBridge via UAT, committed as fixtures. CI contract tests verify InMemoryBridge matches.
  - **Why:** Unit test mocks verify interface, not behavior. Golden master proves behavioral equivalence — what OmniFocus actually does is the source of truth.

- **Fixture injection** (Phase 26): `@pytest.mark.snapshot()` marker + fixture chain (bridge -> repo -> service) eliminates hundreds of lines of test setup boilerplate.

- **Bridge factory eliminated** (Phase 23): `create_bridge()` deleted. Repository factory creates `RealBridge` directly. PYTEST safety guard moved to `RealBridge.__init__`.
  - **Why:** The factory existed for env-var routing to test doubles, which was already removed. The indirection served no purpose.

---

## 3. Phases Delivered

| Phase | Name | Status | One-Liner |
|-------|------|--------|-----------|
| 18 | Write Model Strictness | Complete | Write models reject unknown fields; `_Unset` sentinel validated under `extra="forbid"` |
| 19 | InMemoryBridge Export Cleanup | Complete | Test doubles removed from production package exports |
| 20 | Model Taxonomy | Complete | Three-layer naming convention with typed bridge payloads in `contracts/` package |
| 21 | Write Pipeline Unification | Complete | Symmetric add/edit signatures, `BridgeWriteMixin`, `exclude_unset` standardization |
| 22 | Service Decomposition | Complete | 669-line `service.py` -> `service/` package with Resolver, DomainLogic, PayloadBuilder, Validator |
| 23 | SimulatorBridge & Factory Cleanup | Complete | SimulatorBridge removed from exports; bridge factory deleted; PYTEST guard in RealBridge |
| 24 | Test Double Relocation | Complete | 5 test doubles moved from `src/` to `tests/doubles/` with structural import barrier |
| 25 | Patch/PatchOrClear Type Aliases | Complete | `Patch[T]`/`PatchOrClear[T]` aliases + `changed_fields()` helper on CommandModel |
| 26 | Replace InMemoryRepository | Complete | Stateful InMemoryBridge; InMemoryRepository deleted; StubBridge extracted; fixture injection |
| 27 | Bridge Contract Tests | Complete | Golden master from RealBridge UAT; CI contract tests verify InMemoryBridge matches |
| 28 | Expand Golden Master | Complete | 43 scenarios in 7 categories; 9 fields graduated from VOLATILE/UNCOMPUTED to verified |

Plus **7 quick tasks**: lifecycle error fix, status warning suppression, tag warning resolution, deferred items cleanup, move warning wording, `is_set()` TypeGuard, agent message centralization, SAFE-01 CI fix.

---

## 4. Requirements Coverage

All 39 requirements satisfied. Grouped by area:

### Write Pipeline (2/2)
- ✅ **PIPE-01**: Symmetric add/edit signatures at service-repository boundary
- ✅ **PIPE-02**: Same payload construction pattern for both write paths

### Model Taxonomy (4/4)
- ✅ **MODL-01**: Three-layer taxonomy established (Command / RepoPayload / RepoResult / Result)
- ✅ **MODL-02**: Write-side request models renamed with consistent layer convention
- ✅ **MODL-03**: Typed bridge payload models replace `dict[str, Any]`
- ✅ **MODL-04**: All sub-models renamed to indicate their layer

### Service Decomposition (5/5)
- ✅ **SVCR-01–05**: Validation, domain logic, format conversion extracted; package structure; each module independently testable

### Model Strictness (3/3)
- ✅ **STRCT-01**: Write models reject unknown fields with `extra="forbid"`
- ✅ **STRCT-02**: Read models remain permissive
- ✅ **STRCT-03**: `_Unset` sentinel works correctly with forbid

### Test Infrastructure (14/14)
- ✅ **INFRA-01–03**: InMemoryBridge removed from exports, direct imports only, factory option removed
- ✅ **INFRA-04–07**: SimulatorBridge removed from exports, factory deleted, PYTEST guard in RealBridge
- ✅ **INFRA-08–09**: All test doubles in `tests/`, no `src/` imports of test code
- ✅ **INFRA-10–12**: Stateful InMemoryBridge, InMemoryRepository deleted, real serialization in tests
- ✅ **INFRA-13–14**: Golden master captured, CI contract tests verify equivalence

### Type Expressiveness (4/4)
- ✅ **TYPE-01–04**: Patch[T]/PatchOrClear[T] aliases, identical JSON schema, `changed_fields()` helper

### Golden Master Coverage (3/3)
- ✅ **GOLD-01–03**: 43 scenarios in numbered subfolders, capture script rewritten, subfolder discovery in tests

### Field Normalization (4/4)
- ✅ **NORM-01–04**: Lifecycle dates via presence-check, effective fields via exact match with ancestor-chain inheritance

**Audit verdict:** PASSED (39/39 requirements, 11/11 phases, 3/3 E2E flows)

---

## 5. Key Decisions Log

| # | Decision | Phase | Rationale |
|---|----------|-------|-----------|
| 1 | `extra="forbid"` on write models, `extra="ignore"` on read | 18 | Catch agent typos at validation; remain forward-compatible on reads |
| 2 | Warning strings consolidated in `warnings.py` | 18 | Single source of truth for all agent-facing messages |
| 3 | No backward-compatible aliases after renames | 19, 20 | Clean break; all call sites updated in same commit |
| 4 | CQRS/DDD naming: Command/RepoPayload/Result | 20 | Layer visible in class name; `contracts/` as canonical cross-layer package |
| 5 | `exclude_unset=True` standardized over `exclude_none` | 21 | Correct semantics for patch models where `None` means "clear" |
| 6 | BridgeWriteMixin for shared bridge communication | 21 | DRY without inheritance hierarchy; cache invalidation visible at call sites |
| 7 | DI for service modules (Resolver, DomainLogic, PayloadBuilder) | 22 | Each module testable in isolation; orchestrator is pure coordination |
| 8 | Bridge factory deleted entirely | 23 | Indirection for env-var routing to test doubles served no purpose after cleanup |
| 9 | PYTEST guard via `type(self) is RealBridge` | 23 | Allows SimulatorBridge subclass to bypass guard while blocking automated tests |
| 10 | Flat `tests/doubles/` package (no mirroring src/ layout) | 24 | Simpler imports; test doubles are a cohesive group, not scattered modules |
| 11 | Three type aliases (Patch, PatchOrClear, PatchOrNone) | 25 | Different semantics deserve different names even when implementation is identical |
| 12 | InMemoryBridge stores entities as camelCase dicts | 26 | Matches real bridge format; tests exercise the full serialization path |
| 13 | StubBridge as separate class from InMemoryBridge | 26 | Canned responses vs stateful mutation are different concerns |
| 14 | `@pytest.mark.snapshot()` marker for fixture injection | 26 | Declarative test setup; fixture chain handles bridge -> repo -> service wiring |
| 15 | Golden master with numbered subfolder categories | 28 | Self-documenting filesystem order; no external manifest needed |
| 16 | Presence-check normalization (`"<set>"` sentinel) for lifecycle dates | 27-28 | Verify field is populated without comparing exact timestamps |
| 17 | Ancestor-chain inheritance in InMemoryBridge | 28 | Compute effective fields (flagged, dates) by walking project -> task hierarchy |

---

## 6. Tech Debt & Deferred Items

### Tech Debt

- **Phase 27 stale VERIFICATION.md**: Shows `gaps_found` status, but gaps were closed by plans 27-03/27-04 and Phase 28. VERIFICATION.md was never re-run after gap closure. Documentation artifact only — 690 tests + 42 contract tests confirm resolution.

### Deferred Items

- Status field graduation (taskStatus, status) — time-dependent, complex; deferred to future milestone
- Repetition rule writes — v1.3+ scope; golden master ready to be regenerated when implemented
- Task reactivation (`markIncomplete`) — OmniJS API unreliable; deferred indefinitely

### Lessons Learned (from RETROSPECTIVE.md)

1. **Dependency ordering for refactoring is critical** — validating strictness before renaming, typed payloads before pipeline unification, made each phase build on verified foundations
2. **Golden master > unit test mocks** — 43 scenarios catch behavioral drift that targeted unit tests miss
3. **Quick tasks are essential** — 7 urgent fixes handled without derailing the 11-phase roadmap
4. **Gap closure plans are a feature** — Phases 26 and 27 grew through UAT-driven discovery; the result was dramatically better infrastructure
5. **Structural isolation > convention** — physical relocation of test doubles beats import discipline

---

## 7. Getting Started

### Run the project
```bash
uv sync              # install dependencies
uv run pytest        # run all 697 tests (~15s)
uv run pytest -x     # stop at first failure
```

### Key directories
```
src/omnifocus_operator/
├── server.py           # MCP server entry point (FastMCP)
├── service/            # Business logic package
│   ├── service.py      # Orchestrator (thin, ~9-step pipelines)
│   ├── resolve.py      # Entity resolution (parents, tags)
│   ├── domain.py       # Business rules (lifecycle, tag diff, no-op)
│   ├── validate.py     # Input validation
│   └── payload.py      # Format conversion to bridge payloads
├── contracts/          # Cross-layer types and protocols
│   ├── commands.py     # Agent-facing write models (CommandModel base)
│   ├── repo_payloads.py # Typed bridge payloads
│   ├── results.py      # Response models
│   └── protocols.py    # Repository/Bridge protocols
├── repository/         # Data access layer
├── bridge/             # OmniJS bridge communication
├── models/             # Read-side Pydantic models
└── agent_messages/     # All agent-facing warning/error strings

tests/
├── doubles/            # All test doubles (InMemoryBridge, StubBridge, SimulatorBridge)
├── golden/             # Golden master fixtures (43 scenarios)
└── ...                 # Test files mirroring src/ structure
```

### Where to look first
- **Entry point**: `src/omnifocus_operator/server.py` — the 6 MCP tool definitions
- **Write flow**: `service/service.py` `_AddTaskPipeline` / `_EditTaskPipeline` — Method Object pattern
- **Models**: `contracts/commands.py` for write models, `models/` for read models
- **Test patterns**: Any test file with `@pytest.mark.snapshot()` for the fixture injection pattern
- **Golden master**: `tests/golden/` for behavioral contract tests

---

## Stats

- **Timeline:** 2026-03-16 -> 2026-03-23 (8 days)
- **Phases:** 11/11 complete (+ 7 quick tasks)
- **Plans:** 27 executed
- **Requirements:** 39/39 satisfied
- **Commits:** 336
- **Files changed:** 418 (+67,053 / -6,274)
- **Tests:** 518 -> 690 (+172 tests, net gain)
- **Coverage:** ~94%
- **Contributors:** Flo Kempenich
