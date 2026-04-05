# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 -- Foundation

**Shipped:** 2026-03-07
**Phases:** 11 | **Plans:** 22 executed

### What Was Built
- Complete MCP server with `list_all` tool returning structured OmniFocus data
- Three bridge implementations (InMemory, Simulator, Real) with pluggable DI
- File-based IPC engine with atomic writes, async polling, orphan cleanup
- OmniJS bridge script running inside OmniFocus process
- Full Pydantic model suite aligned to empirically-verified BRIDGE-SPEC
- Error-serving degraded mode for headless MCP reliability

### What Worked
- Bottom-up dependency ordering (models -> bridge -> repo -> service -> MCP -> IPC -> simulator -> real) meant each phase built on solid, tested foundations
- TDD approach with atomic commits made debugging trivial -- every commit is self-contained
- Bridge script research (27 OmniJS audit scripts) paid off -- BRIDGE-SPEC alignment in Phase 08.2 had zero surprises
- ~4 min average plan execution -- GSD's fine-grained planning kept scope tight
- Inserting decimal phases (8.1, 8.2) handled urgent discoveries cleanly without disrupting the roadmap

### What Was Inefficient
- Phase 8 UAT discovered the bridge script didn't exist yet -- should have been caught earlier in planning (led to 8.1 insertion)
- VERIFICATION.md missing for phases 08 and 08.1 -- UAT evidence existed but wasn't formalized
- Plan 08.1-04 (Makefile unified test) was planned but never needed -- over-planning
- `_` prefix convention was adopted then reversed in quick task 2 -- wasted effort on initial convention

### Patterns Established
- OmniFocusBaseModel ConfigDict with camelCase aliases and populate_by_name
- TYPE_CHECKING imports + model_rebuild(_types_namespace) for ruff TC + Pydantic compat
- Factory safety guard: PYTEST_CURRENT_TEST blocks RealBridge in automated tests
- SimulatorBridge inherits RealBridge, overrides only _trigger_omnifocus
- bridge.js loaded once at __init__ via importlib.resources
- Fail-fast on unknown enum values at bridge boundary

### Key Lessons
1. **Research before building pays off massively** -- 27 OmniJS audit scripts meant zero model surprises during implementation
2. **Decimal phase insertion is a clean pattern** for handling discoveries mid-milestone
3. **Don't plan "nice-to-have" plans** (08.1-04) -- only plan what's needed to satisfy requirements
4. **Convention decisions should wait until patterns emerge** -- the `_` prefix decision was reversed after seeing the full codebase

### Cost Observations
- Model mix: ~70% opus (research, planning, complex phases), ~30% sonnet (execution, validation)
- Sessions: ~15-20 across 14 days
- Notable: Average plan execution of ~4 min is remarkably fast -- GSD fine-grained planning with TDD is efficient

---

## Milestone: v1.1 -- HUGE Performance Upgrade

**Shipped:** 2026-03-07
**Phases:** 4 | **Plans:** 11 executed

### What Was Built
- Two-axis status model (Urgency + Availability) replacing single-winner enums across all entities
- Repository protocol with structural typing -- BridgeRepository, InMemoryRepository, HybridRepository
- HybridRepository reading all 5 entity types from OmniFocus SQLite cache (~46ms)
- WAL-based freshness detection (50ms poll, 2s timeout, .db mtime fallback)
- Repository factory with env-var routing and error-serving for missing SQLite
- Bridge adapter mapping old bridge format to new model shape (dict lookup tables, in-place mutation)

### What Worked
- Incremental model migration (not big-bang) kept 177+ tests green at every step -- Phase 10's 4-plan approach proved correct
- Research from v1.0 (RESULTS.md, RESULTS_pydantic-model.md) was exhaustive enough that SQLite implementation had zero schema surprises
- Gap closure plans (10-04, 11-03) caught integration issues that would have been painful later -- Nyquist validation forced them early
- Adapter idempotency decision (tasks/projects skip if no status key) let simulator data pass through unchanged
- Entire milestone completed in a single day (88 commits) -- tight scope + solid research = fast execution

### What Was Inefficient
- Gap closure plans could have been folded into original planning if requirements had been more precise upfront
- Some SUMMARY.md files lack `requirements_completed` frontmatter -- gsd-tools couldn't auto-extract accomplishments
- Progress table in ROADMAP.md had misaligned columns for v1.1 phases (missing milestone column)

### Patterns Established
- Repository protocol with `@runtime_checkable` for isinstance checks in tests
- Dict-based adapter mapping tables for all enum transformations
- HybridRepository: numeric string detection for SQLite TEXT column affinity timestamps
- Factory pattern with env-var routing for repository selection
- TEMPORARY_ method prefix (uppercase) to signal unstable API surfaces
- Bridge-reachable status constants as explicit tuples for regression testing

### Key Lessons
1. **Incremental migration > big-bang** -- the 4-plan Phase 10 approach kept tests green at every commit and made debugging trivial
2. **Research-first approach continues to pay off** -- zero SQLite schema surprises because RESULTS.md was thorough
3. **Gap closure is a feature, not a bug** -- Nyquist validation caught real integration gaps early
4. **Adapter idempotency is essential** -- making the adapter safe to run on already-transformed data prevented a whole class of bugs

### Cost Observations
- Model mix: ~80% opus (research, planning, complex phases), ~20% sonnet (execution, validation)
- Sessions: ~5-8 across 1 day
- Notable: 88 commits in a single day -- fastest milestone yet, driven by excellent research artifacts from v1.0

---

## Milestone: v1.2 -- Writes & Lookups

**Shipped:** 2026-03-16
**Phases:** 6 | **Plans:** 21 executed

### What Was Built
- Unified parent model (ParentRef) and `get_all` rename from `list_all`
- Get-by-ID tools (`get_task`, `get_project`, `get_tag`) with dedicated SQLite queries
- Full write pipeline: MCP → Service → Repository → Bridge → OmniFocus
- Task creation (`add_tasks`) with parent/tag resolution and per-item results
- Task editing (`edit_tasks`) with UNSET sentinel patch semantics and actions block
- Diff-based tag computation replacing 4-branch bridge.js dispatch
- Task lifecycle (complete/drop) with educational warnings

### What Worked
- Actions block refactor (Phase 16.1) was inserted mid-milestone and paid off immediately -- clean separation of field setters vs stateful operations
- Diff-based tag simplification (Phase 16.2) dramatically reduced bridge.js complexity (~45 lines → ~4 lines)
- Write-through guarantee (`@_ensures_write_through`) solved read-after-write consistency cleanly
- UAT regression skill caught real issues (same-container move warning, repeating-task drop text)
- Deferred work captured in milestone specs (v1.2.1, v1.2.2) instead of scope creep

### What Was Inefficient
- Phase 16 grew to 6 plans (originally scoped as 3) -- tag modes and movement were more complex than anticipated
- SUMMARY.md files lack `one_liner` field -- gsd-tools couldn't auto-extract accomplishments at milestone completion
- REQUIREMENTS.md descriptions for EDIT-03 through EDIT-08 became stale after Phase 16.1 restructured the API shape
- LIFE-03 (reactivation) was a requirement but OmniJS API limitations made it unimplementable -- should have been flagged during requirements phase

### Patterns Established
- UNSET sentinel with `__get_pydantic_core_schema__` for Pydantic v2 patch models
- Actions block grouping: idempotent setters (top-level) vs stateful operations (actions)
- `_compute_tag_diff` for diff-based tag handling (replace/add/remove → minimal add/remove sets)
- `_process_lifecycle` helper returning (should_call_bridge, warnings) tuple
- Write-through decorator pattern for read-after-write consistency
- Educational no-op warnings that teach agents patch semantics

### Key Lessons
1. **API restructuring mid-milestone is worth it** -- the actions block (Phase 16.1) was inserted urgently but made lifecycle (Phase 17) trivial to add
2. **Move complexity to Python, keep bridge dumb** -- diff-based tag computation proved this pattern scales
3. **Requirements should include feasibility research** -- LIFE-03 was a requirement that couldn't be met; research spike in Phase 17 discovered this too late
4. **UAT regression suites catch real bugs** -- the uat-regression skill found 3 genuine issues in Phase 17
5. **Scope discipline via milestone specs** -- deferring work to formal specs (v1.2.1, v1.2.2) prevented scope creep

### Cost Observations
- Model mix: ~70% opus (research, planning, complex phases), ~30% sonnet (execution, validation)
- Sessions: ~10-15 across 9 days
- Notable: 3.6 min average plan execution -- consistent with v1.0/v1.1 velocity

---

## Milestone: v1.2.1 -- Architectural Cleanup

**Shipped:** 2026-03-23
**Phases:** 11 | **Plans:** 27 executed

### What Was Built
- Write model strictness (`extra="forbid"`) on all 5 write specs with improved error handling
- Three-layer model taxonomy in contracts/ package (Command/RepoPayload/RepoResult/Result)
- Service decomposition: monolithic 669-line service.py → 4-module service/ package with DI
- Test double isolation: 5 doubles relocated from src/ to tests/doubles/ with structural import barrier
- Stateful InMemoryBridge replacing InMemoryRepository — write tests exercise real serialization
- StubBridge as purpose-built canned-response double; InMemoryBridge purely stateful
- Patch[T]/PatchOrClear[T] type aliases making patch semantics self-documenting
- Golden master contract testing: 43 scenarios in 7 categories proving InMemoryBridge ≡ RealBridge
- 9 fields graduated from VOLATILE/UNCOMPUTED with ancestor-chain inheritance
- @pytest.mark.snapshot fixture composition eliminating hundreds of lines of test boilerplate

### What Worked
- Dependency ordering (STRCT→MODL→PIPE→SVCR) validated each concern in isolation before building on it
- Gap closure plans (Phases 22, 26, 27) caught real integration issues — StubBridge extraction, fixture refactoring, raw format conversion all emerged from UAT
- Golden master approach proved powerful — captured real OmniFocus behavior once, verified forever in CI
- Quick task mechanism handled 7 urgent fixes without disrupting the main roadmap
- Phases 25-28 grew organically from earlier phase discussions — roadmap evolution was disciplined (formal additions, not scope creep)

### What Was Inefficient
- Phase 27 VERIFICATION.md never re-run after gap closure plans fixed the issues — stale documentation artifact
- Phase 26 grew from 2 to 5 plans due to UAT discoveries (StubBridge split, fixture refactoring) — could have been anticipated with deeper upfront analysis of test coupling
- ROADMAP.md header said "Phases 18-24" but milestone actually spanned 18-28 — headers became stale as phases were added
- Progress table column alignment inconsistency for v1.2.1 phases (missing milestone column in some rows)

### Patterns Established
- Method Object pattern (`_VerbNounPipeline`) for service use cases — created, executed, discarded
- contracts/ package as the canonical location for cross-layer types and protocols
- `@pytest.mark.snapshot` + fixture chain (bridge→repo→service) for declarative test setup
- Golden master capture script with numbered subfolder categories (01-add through 07-inheritance)
- Presence-check sentinel normalization (`"<set>"`) for verifying nullable date fields without value comparison
- `changed_fields()` on CommandModel complementing `is_set()` TypeGuard for field inspection

### Key Lessons
1. **Dependency ordering for refactoring milestones is critical** — validating strictness before renaming, typed payloads before pipeline unification, made each phase build on verified foundations
2. **Golden master > unit test mocks for behavioral equivalence** — 43 scenarios caught drift that targeted unit tests would miss
3. **Quick tasks are essential for milestone hygiene** — 7 urgent fixes handled without derailing the 11-phase roadmap
4. **Gap closure plans are a feature** — Phases 26 and 27 both grew through UAT-driven gap closure, and the result was dramatically better test infrastructure
5. **Structural isolation > convention** — moving test doubles to tests/doubles/ made production-test boundary impossible to violate, not just discouraged

### Cost Observations
- Model mix: ~65% opus (research, planning, complex phases), ~35% sonnet (execution, validation)
- Sessions: ~15-20 across 8 days
- Notable: Phase 22 (service decomposition) was the most complex — 4 plans + gap closure. Phase 28 (golden master expansion) required UAT capture sessions with the live database.

---

## Milestone: v1.2.2 -- FastMCP v3 Migration

**Shipped:** 2026-03-26
**Phases:** 3 | **Plans:** 6 executed

### What Was Built
- Dependency swap from `mcp>=1.26.0` to `fastmcp>=3.1.1` with native v3 import patterns
- Test client migration: 65-line `_ClientSessionProxy` → 10-line `Client(server)` fixture, 40+ tests migrated
- `ToolLoggingMiddleware` replacing 6 manual `log_tool_call()` call sites
- Dual-handler logging: stderr (Claude Desktop) + 5MB rotating file with `__name__` convention across 10 modules
- `ctx.report_progress()` scaffolding in batch write handlers

### What Worked
- Spike-first approach: 8 experiments in `.research/deep-dives/fastmcp-spike/` eliminated all unknowns before planning — zero surprises during execution
- Phase consolidation (6 → 3 phases) based on spike findings kept scope tight and execution fast (~3 days)
- All 3 phases completed in a single day of execution (research and planning happened across prior days)
- Nyquist validation caught nothing — clean execution with zero gaps, zero rework
- 708 tests passing at 98% coverage throughout — no regressions from the migration

### What Was Inefficient
- REQUIREMENTS.md checkboxes for DEP/PROG/DOC groups left unchecked despite being satisfied — documentation drift between phases and requirements tracking
- SUMMARY.md `requirements_completed` frontmatter missing for some plans — inconsistent artifact quality

### Patterns Established
- `Client(server)` fixture pattern for FastMCP v3 test infrastructure
- `pytest.raises(ToolError, match=...)` as idiomatic error assertion pattern
- Middleware with injected logger for cross-cutting MCP concerns
- `__name__` logger convention with root logger as dual-handler configuration point

### Key Lessons
1. **Spike experiments before migration planning** — the FastMCP v3 spike saved significant rework by proving patterns before committing to roadmap structure
2. **Infrastructure migrations can be fast** — 3 phases, 6 plans, single day of execution when research is thorough
3. **Phase consolidation from spike findings** — original 6-phase plan was over-planned; spike evidence compressed to 3 phases with better boundaries

### Cost Observations
- Model mix: ~60% opus (research, spike analysis, planning), ~40% sonnet (execution)
- Sessions: ~5 across 3 days (research + planning + execution)
- Notable: Average plan execution of ~4 min — consistent with historical velocity. Total execution ~24 min for all 6 plans.

---

## Milestone: v1.2.3 -- Repetition Rule Write Support

**Shipped:** 2026-03-29
**Phases:** 4 | **Plans:** 15 executed

### What Was Built
- Structured RepetitionRule read model with RRULE parser/builder, replacing raw ruleString on both read paths
- Output schema regression guards (jsonschema validates all 6 tools' output against MCP outputSchema)
- Full repetition rule write pipeline: add/edit with partial updates, same-type merge, type-change detection
- Flat Frequency model (6 types) replacing 9-subtype discriminated union, enabling type-optional edits
- Educational validation errors and anchor date warnings

### What Worked
- Two-phase structure (read model Phase 32 before write model Phase 33) — clean dependency ordering, write path built on validated read types
- Custom RRULE parser research spike (79 tests) meant zero implementation surprises — purpose-built for OmniFocus subset
- Phase 33.1 insertion (flat Frequency refactor) was the right call — 9-subtype union was fundamentally incompatible with type-optional edits; early refactor prevented escalating complexity
- Output schema validation (Phase 32.1) caught a real regression during development — @model_serializer was erasing JSON Schema structure
- UAT found 2 genuine bugs (multi-value BYMONTHDAY, no-op warning suppression) that unit tests missed

### What Was Inefficient
- Phase 33 grew to 5 plans (originally scoped as 3) due to gap closure — validation error quality and BYMONTHDAY edge cases discovered during execution
- 9-subtype discriminated union (Phase 33) was replaced entirely by flat model (Phase 33.1) — ~2 plans of union-specific work thrown away
- ROADMAP.md Phase 33 status and 33-05 checkbox not updated after completion — documentation drift
- SUMMARY frontmatter `requirements_completed` underutilized — only 12/39 REQ-IDs populated across all SUMMARYs

### Patterns Established
- Flat Frequency model with type discriminator and optional specialization fields (on_days, on, on_dates)
- FrequencyEditSpec as pure patch container — no validators, validation deferred to Frequency construction from merged result
- `is_set()` merge pattern: existing dict + submitted explicitly-set fields
- `auto_clear_monthly_mutual_exclusion` — operates on merged dict before model validation
- @field_validator over Field(ge=1) for agent-facing error quality
- @field_serializer on parent model (RepetitionRule.frequency) to avoid schema erasure

### Key Lessons
1. **Discriminated unions are poor write models** — Pydantic requires the discriminator for construction, making partial updates impossible. Flat models with optional fields are better for write paths
2. **Output schema testing catches real bugs** — the jsonschema-vs-data approach found @model_serializer erasure that Pydantic validation alone would miss
3. **Research spikes prevent rework** — custom RRULE parser had zero surprises because spike tested 79 cases first
4. **UAT finds what unit tests miss** — both BYMONTHDAY multi-value and no-op suppression were real user-observable bugs invisible to unit tests
5. **Insert phases early when architecture doesn't fit** — Phase 33.1 was inserted urgently after Phase 33 exposed the union's limitations; the refactor was cheaper than workarounds

### Cost Observations
- Model mix: ~70% opus (research, planning, complex phases), ~30% sonnet (execution)
- Sessions: ~8-10 across 3 days
- Notable: Average plan execution of ~7.7 min — slightly higher than historical ~4 min due to Phase 33.1 P02 (24 min service layer rewrite). Total execution ~116 min for 15 plans.

---

## Milestone: v1.3 -- Read Tools

**Shipped:** 2026-04-05
**Phases:** 12 | **Plans:** 26 executed

### What Was Built
- Parameterized SQL filtering engine for tasks (10 filters) and projects (6 filters)
- 5 new MCP list tools with typed query models, rich inputSchema, and DEFAULT_LIST_LIMIT=50
- Name-to-ID resolution cascade at service boundary with fuzzy "did you mean?" warnings
- Write tool schema migration via ValidationReformatterMiddleware
- Description centralization — 60 constants in descriptions.py with AST enforcement
- Cross-path equivalence tests (32 parametrized) proving SQL ≡ bridge
- Type constraint boundary (Literal/Annotated reserved for contracts) with AST enforcement
- Fixed effectiveCompletionDate ghost tasks in availability mappers and SQL clauses

### What Worked
- Decimal phase insertion continued to prove its value — 7 insertions (35.1, 35.2, 36.1-36.4, 37.1) handled urgent discoveries cleanly
- Cross-path equivalence as a hard requirement caught real SQL/bridge divergence during development — worth the test investment
- Description centralization (Phase 36.3) with AST enforcement prevents a whole category of documentation drift
- Quick tasks handled 8 fixes without disrupting the main roadmap — maintained milestone momentum
- Phase 38 as collaborative session (no formal pipeline) was efficient for phrasing/documentation work

### What Was Inefficient
- 7 decimal phases out of 12 total — over half the phases were insertions, suggesting the original 4-phase roadmap was too coarse-grained for a milestone this scope
- DESC-07/DESC-08 checkboxes not updated despite passing enforcement tests — manual traceability tables drift from automated enforcement
- Phase 38 had no PLAN/VERIFICATION artifacts — while efficient, it created audit gaps (Nyquist non-compliant)
- Some VALIDATION.md files marked non-compliant despite phases being complete — Nyquist gap-filling happened retroactively rather than inline

### Patterns Established
- `_ReadPipeline` as separate base from `_Pipeline` for read-side Method Objects
- Per-use-case package structure: `contracts/use_cases/{verb}/` with `__init__.py` re-exports
- Resolution cascade pattern: ID match → substring → fuzzy "did you mean?" — reusable for any entity reference
- `SqlQuery` NamedTuple as standard return type for parameterized SQL
- QueryModel base (distinct from CommandModel) for read-side contracts
- `ReviewDueFilter` as first `<noun>Filter` value object pattern

### Key Lessons
1. **Original phase scoping was too optimistic** — "4 phases for read tools" became 12 phases with 7 insertions. The architectural cleanup work (contract splits, description centralization, type boundaries) was as large as the feature itself
2. **Automated enforcement > manual checklists** — AST enforcement tests for descriptions and type boundaries are self-maintaining; traceability table checkboxes drift
3. **Cross-path equivalence is non-negotiable** — caught real divergence between SQL and bridge paths that would have been invisible to unit tests
4. **Collaborative sessions work for documentation** — Phase 38 was efficient because the "code" was English prose; formal pipelines add overhead without value for phrasing work
5. **Name resolution is a cross-cutting concern** — building it once at the service boundary (Phase 35.2) meant all 5 list tools got it for free

### Cost Observations
- Model mix: ~60% opus (research, planning, complex phases), ~40% sonnet (execution, validation)
- Sessions: ~12-15 across 7 days
- Notable: Quick tasks (8 total) were ~30% of the work by count but kept the main pipeline unblocked

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 11 | 22 | First milestone -- established GSD + TDD workflow |
| v1.1 | 4 | 11 | Fastest milestone -- research artifacts enabled single-day execution |
| v1.2 | 6 | 21 | First write milestone -- decimal phases (16.1, 16.2) for mid-milestone restructuring |
| v1.2.1 | 11 | 27 | First refactoring milestone -- dependency-ordered phases, golden master contract testing |
| v1.2.2 | 3 | 6 | First migration milestone -- spike-first approach, phase consolidation from research |
| v1.2.3 | 4 | 15 | First domain-feature milestone -- research spike → read model → write model → refactor arc |
| v1.3 | 12 | 26 | Largest feature milestone -- 7 decimal insertions, cross-path equivalence as hard requirement |

### Cumulative Quality

| Milestone | Tests | Coverage | Tech Debt Items |
|-----------|-------|----------|-----------------|
| v1.0 | 203+ (177 pytest + 26 vitest) | ~98% | 4 (all low severity) |
| v1.1 | 339 (313 pytest + 26 vitest) | ~98% | 0 |
| v1.2 | 527 (501 pytest + 26 vitest) | ~94% | 3 (LIFE-03 deferred, stale docs, tag exclusivity) |
| v1.2.1 | 723 (697 pytest + 26 vitest) | ~94% | 1 (stale Phase 27 VERIFICATION.md) |
| v1.2.2 | 734 (708 pytest + 26 vitest) | ~98% | 1 (ToolAnnotations mcp.types residual) |
| v1.2.3 | 1,139 (1,113 pytest + 26 vitest) | ~94% | 6 (all cosmetic/documentation) |
| v1.3 | 1,554 (1,528 pytest + 26 vitest) | ~94% | 4 (Nyquist gaps on 4 phases, all process artifacts) |

### Top Lessons (Verified Across Milestones)

1. Research-first approach prevents rework (verified in v1.0, v1.1, v1.2 -- LIFE-03 was the exception that proves the rule)
2. Fine-grained plans (~4 min avg) keep momentum and reduce context-switching cost (consistent across all milestones)
3. Incremental migration beats big-bang (verified in v1.1 Phase 10, v1.2 Phase 16.1 actions refactor, v1.2.1 dependency ordering)
4. Gap closure plans catch integration issues early when forced by validation (verified in v1.1, v1.2, v1.2.1 Phases 22/26/27)
5. Move complexity to Python, keep bridge dumb (established v1.2 -- diff-based tags proved the pattern)
6. Structural isolation > convention for test boundaries (established v1.2.1 -- physical relocation beats import discipline)
7. Golden master > targeted mocks for behavioral equivalence (established v1.2.1 -- 43 scenarios catch drift that unit tests miss)
8. Spike experiments eliminate unknowns before planning (established v1.2.2 -- 8 experiments compressed 6 phases to 3)
9. Output schema testing catches bugs Pydantic alone misses (established v1.2.3 -- jsonschema-vs-data caught @model_serializer schema erasure)
10. Discriminated unions are poor write models; flat models enable partial updates (established v1.2.3 -- Phase 33.1 refactor was cheaper than workarounds)
11. Automated enforcement > manual checklists for documentation (established v1.3 -- AST tests self-maintain, traceability checkboxes drift)
12. Cross-path equivalence as hard requirement catches real divergence (established v1.3 -- 32 parametrized tests, mandatory for new filters)
