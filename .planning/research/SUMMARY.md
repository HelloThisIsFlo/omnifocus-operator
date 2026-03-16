# Project Research Summary

**Project:** OmniFocus Operator v1.2.1 — Architectural Cleanup
**Domain:** Internal refactoring — service layer decomposition and write pipeline unification
**Researched:** 2026-03-16
**Confidence:** HIGH

## Executive Summary

v1.2.1 is a pure internal refactoring milestone with zero new runtime dependencies. The goal is to correct two structural problems that accumulated during v1.2: a 637-line monolithic `service.py` that mixes orchestration, validation, domain logic, and format conversion; and an asymmetric write pipeline where `add_task` and `edit_task` use different conventions at the service-repository boundary. Both problems are well-understood — research draws from direct codebase analysis, Pydantic v2 docs, and Cosmic Python architecture patterns.

The recommended approach is staged decomposition: start with two independent quick wins (`extra="forbid"` on write models, `InMemoryBridge` export cleanup), then unify the repository write signatures, then extract the service into a package with validation/domain/conversion sub-modules. This ordering matters — decomposing the service before unifying the repository interface leads to wrong abstractions. The extraction should produce exactly 3 sub-modules plus the orchestrator, not 6+.

The main risks are Pydantic-specific: `extra="forbid"` may interact unexpectedly with the `_Unset` sentinel on `TaskEditSpec`, and `model_rebuild()` ordering in `models/__init__.py` is fragile if model files move. Both are detectable immediately with targeted tests. Circular imports during service extraction are the other likely stumbling block, prevented by enforcing a strict one-way dependency direction.

---

## Key Findings

### Recommended Stack

No new dependencies. The milestone uses Pydantic v2.12.5 (already in stack via `mcp>=1.26.0`) more deliberately: `ConfigDict(extra="forbid")` for write model strictness and ConfigDict inheritance merge to keep the base model's alias settings. Python 3.12 module/package patterns handle the service decomposition.

**Core technologies:**
- **Pydantic v2.12.5** (write model validation) — `ConfigDict(extra="forbid")` on write specs; ConfigDict merges additively on inheritance so a `WriteModel` base adds `extra="forbid"` without clobbering `alias_generator` from `OmniFocusBaseModel`
- **Python packages with `__init__.py` re-exports** (service decomposition) — convert `service.py` to `service/` package; `__init__.py` re-exports `OperatorService` so all existing imports are unchanged
- **Module-level functions** (extracted logic) — stateless validation, domain, and conversion functions need no class ceremony; directly testable without instantiating the service

**Critical constraint:** Read models (`Task`, `Project`, `Tag`) must remain `extra="ignore"`. OmniFocus may return unmodeled SQLite columns; strict read models would cause production outages on OmniFocus updates.

### Expected Features

This milestone is internal — "features" are code quality deliverables, not user-visible capabilities.

**Must have (table stakes):**
- `extra="forbid"` on all write spec models — agents sending unknown fields currently get silent discard; essential for any write API
- Symmetric `add_task`/`edit_task` signatures at repository boundary — both accept `dict[str, Any]`, return `dict[str, Any]`; current asymmetry forces every new write operation to invent its own convention
- Service decomposed into orchestrator + 3 sub-modules (`_validation.py`, `_domain.py`, `_payload.py`) — service method becomes a readable ~20-line orchestration flow
- `InMemoryBridge` removed from production exports — test double in `bridge/__init__.py` is a code smell

**Should have (differentiators):**
- Typed return values from repository write methods — `TaskCreateResult`/`TaskEditResult` constructed in service, not wrangled from raw dicts
- Shared resolution logic — `resolve_parent`/`resolve_tags` as free functions usable by both add and edit paths

**Defer to later milestones:**
- Typed `BridgePayload` model at service-repository boundary — `dict[str, Any]` is appropriate; typed intermediate adds overhead for no current benefit
- Composable validation pipeline — only 2 write operations; explicit function calls are clearer
- Physical relocation of `InMemoryBridge` to `tests/` — removing from exports is sufficient for v1.2.1

### Architecture Approach

Target state: a three-module service package with strict one-way dependency direction. Orchestrator calls into sub-modules, never the reverse. Extracted modules are pure functions with explicit dependency injection (repo passed as argument, not accessed via `self`). The repository protocol becomes a thin bridge delegate — payload construction moves to `conversion.py`, result construction moves back to the service.

**Major components after refactoring:**
1. `service/_orchestrator.py` — 80-100 lines; pure orchestration: validate → domain → convert → delegate; holds repo reference
2. `service/validation.py` — name checks, parent resolution, tag name-to-ID resolution; async functions receiving `repo` as argument
3. `service/domain.py` — lifecycle state machine, tag diff, no-op detection, cycle detection; mostly pure sync functions
4. `service/conversion.py` — `build_add_payload()` and `build_edit_payload()`; pure sync functions; no async, no repo access
5. **Repository protocol** — unified: both `add_task(payload: dict)` and `edit_task(payload: dict)` return `dict`; no typed spec at boundary

**Unchanged:** `server.py` → `OperatorService` import; bridge IPC protocol; `@_ensures_write_through` decorator placement; SQLite read path.

### Critical Pitfalls

1. **`extra="forbid"` + `_Unset` sentinel interaction** — `TaskEditSpec` uses `_Unset` as default for optional fields; `extra="forbid"` on a parent class may cause `ValidationError` on valid inputs due to Pydantic v2 config MRO issues (#9768, #9992). Prevention: apply `extra="forbid"` per-model, not via a `WriteModel` base; test both `model_validate(dict)` and `model_validate_json(str)` paths before any other refactoring.

2. **`model_rebuild()` ordering** — `models/__init__.py` rebuilds 15 models in dependency order with a shared `_types_namespace`; reorganizing model files disrupts this ordering and causes `PydanticUndefinedAnnotation` at import time, crashing all 534 tests. Prevention: keep all `model_rebuild()` calls centralized in `models/__init__.py` regardless of where model classes live.

3. **Circular imports during service extraction** — extracted modules importing back into the service creates circular deps. Prevention: strict one-way direction: orchestrator imports from sub-modules, never the reverse; sub-modules receive dependencies as arguments.

4. **`InMemoryBridge` mass import breakage** — removing from `bridge/__init__.py` in one step causes 100+ `ImportError`s across the test suite. Prevention: two-commit approach — first update all test imports to use `bridge.in_memory` direct path, run suite, then remove the export.

5. **`_Unset` sentinel leaking into bridge payloads** — using `model_dump()` on `TaskEditSpec` includes UNSET sentinel values; `bridge.js` can't deserialize them. Prevention: retain explicit field-by-field construction for edit payloads; use `model_dump()` only for create specs (no sentinels).

---

## Implications for Roadmap

### Phase 1: Write Model Strictness
**Rationale:** Independent of all other changes; smallest scope; validates the Pydantic `extra="forbid"` + sentinel interaction before it affects anything else. Catching sentinel issues here costs minutes; catching them mid-decomposition costs hours.
**Delivers:** Write specs reject unknown fields at runtime (`ValidationError`), closing the silent-discard gap for agent calls.
**Addresses:** `extra="forbid"` table stakes feature.
**Avoids:** Pitfall 1 (sentinel interaction) — tested in isolation before inheritance patterns are introduced.

### Phase 2: InMemoryBridge Export Cleanup
**Rationale:** Independent of all other changes; best done before decomposition to reduce diff noise during larger refactors.
**Delivers:** `InMemoryBridge` removed from public production exports; tests use `bridge.in_memory` direct module path.
**Addresses:** InMemoryBridge code smell.
**Avoids:** Pitfall 4 (mass import breakage) — two-commit approach with full suite run between steps.

### Phase 3: Repository Write Interface Unification
**Rationale:** Must happen before service decomposition. Decomposing the service around the old asymmetric protocol leads to wrong abstractions. Once the repository accepts `dict[str, Any]` for both operations, the service's role (build the payload) becomes unambiguous.
**Delivers:** Symmetric `add_task(payload: dict)`/`edit_task(payload: dict)` on all three repo implementations; payload construction removed from repositories.
**Addresses:** Symmetric write protocol table stakes feature.
**Avoids:** Pitfall 5 (payload shape change) — bridge payload contract tests assert exact dict passed to `send_command`; Pitfall 8 (UNSET leak) — explicit field construction retained for edit path; Pitfall 9 (`@_ensures_write_through` break) — decorator stays on repo methods unchanged.

### Phase 4: Service Decomposition
**Rationale:** Depends on unified interface from Phase 3. Extraction order within this phase: conversion first (most mechanical, least design judgment), then validation, then domain logic (most interleaved with orchestration). Each sub-step keeps all 534 tests green.
**Delivers:** `service/` package; `_orchestrator.py` slimmed to ~80-100 lines; clean separation of concerns.
**Addresses:** All service decomposition table stakes features.
**Avoids:** Pitfall 3 (circular imports) — one-way dependency direction enforced; Pitfall 6 (over-decomposition) — max 3 sub-modules; Pitfall 2 (model_rebuild) — service modules import from the `models` package, not individual files.

### Phase Ordering Rationale

- Phases 1 and 2 are independent and can run in parallel or either order; they touch different files.
- Phase 3 before Phase 4 is non-negotiable: the service decomposition's payload-building logic only makes sense once the repository is a thin passthrough.
- The entire milestone has no public API changes — `server.py` and all external consumers are untouched throughout.
- Risk increases from phase to phase: Phase 1 is a 5-line change, Phase 4 is the most complex. Doing easy phases first validates the approach and builds confidence.

### Research Flags

All phases have standard, well-documented patterns. No additional research spikes are needed.

- **Phase 1:** Pydantic `ConfigDict` behavior is documented; the sentinel interaction test is prescriptive and self-contained.
- **Phase 2:** Mechanical find-and-replace of import paths; scope discoverable via `grep`.
- **Phase 3:** Signature change on known files; `mypy --strict` catches protocol mismatches.
- **Phase 4:** Cosmic Python service layer extraction pattern is well-documented; order within phase is specified.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Zero new dependencies; Pydantic v2.12.5 ConfigDict inheritance confirmed in official docs and GitHub discussions |
| Features | HIGH | Derived from direct codebase analysis; asymmetry and smells are observable facts |
| Architecture | HIGH | Based on reading actual source files (`service.py` 637 lines, `repository/protocol.py`, etc.); target state is a straightforward extraction |
| Pitfalls | HIGH | Pydantic sentinel/config pitfalls backed by known GitHub issues; circular import and decorator risks derived from codebase structure |

**Overall confidence:** HIGH

### Gaps to Address

- **`extra="forbid"` + sentinel interaction (Phase 1):** High confidence on the risk, but exact behavior depends on Pydantic 2.12.5 runtime. Write the targeted test before committing to a `WriteModel` base vs. per-model approach. The per-model approach is safer and should be the default.
- **`model_dump(exclude_unset=True)` semantics (Phase 3/4):** Pydantic's "unset" means "not provided during validation," which differs from "has UNSET sentinel default." Validate this explicitly before using `model_dump` anywhere in the edit path.
- **`InMemoryRepository` dict handling (Phase 3):** After unification, `InMemoryRepository.add_task` receives `dict[str, Any]` with camelCase keys and must reconstruct in-memory `Task` objects. Exact field mapping needs verification against the `Task` model fields.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis — `service.py` (637 lines), `models/write.py` (318 lines), `models/__init__.py` (115 lines, 15 model_rebuild calls), `repository/protocol.py`, `bridge/__init__.py`, `tests/test_service.py` (2000+ lines)
- [Pydantic v2 Configuration docs (2.12.5)](https://docs.pydantic.dev/latest/concepts/config/) — ConfigDict inheritance merge, `extra` parameter
- [Pydantic v2 Validation Errors](https://docs.pydantic.dev/latest/errors/validation_errors/) — `extra_forbidden` error type
- [PEP 544 — Protocols](https://peps.python.org/pep-0544/) — structural typing for Repository boundary
- [Cosmic Python: Service Layer](https://www.cosmicpython.com/book/chapter_04_service_layer.html) — orchestration responsibilities
- [Cosmic Python: Validation](https://www.cosmicpython.com/book/appendix_validation.html) — syntax/semantic/pragmatic validation categories

### Secondary (MEDIUM confidence)
- [Pydantic config inheritance discussion #7778](https://github.com/pydantic/pydantic/discussions/7778) — ConfigDict merge behavior in practice
- `.research/updated-spec/MILESTONE-v1.2.1.md` — milestone spec with asymmetry map and acceptance criteria

### Tertiary — Known issues requiring test validation
- [Pydantic config MRO issue #9768](https://github.com/pydantic/pydantic/issues/9768) — config merging in multiple inheritance
- [Pydantic model_config MRO issue #9992](https://github.com/pydantic/pydantic/issues/9992) — config doesn't respect MRO
- [Pydantic sentinel serialization #9943](https://github.com/pydantic/pydantic/discussions/9943) — custom sentinel failures
- [Pydantic model_rebuild issue #7618](https://github.com/pydantic/pydantic/issues/7618) — forward reference failures

---
*Research completed: 2026-03-16*
*Ready for roadmap: yes*
