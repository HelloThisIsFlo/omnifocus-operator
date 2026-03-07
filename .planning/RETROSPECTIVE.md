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

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 11 | 22 | First milestone -- established GSD + TDD workflow |
| v1.1 | 4 | 11 | Fastest milestone -- research artifacts enabled single-day execution |

### Cumulative Quality

| Milestone | Tests | Coverage | Tech Debt Items |
|-----------|-------|----------|-----------------|
| v1.0 | 203+ (177 pytest + 26 vitest) | ~98% | 4 (all low severity) |
| v1.1 | 339 (313 pytest + 26 vitest) | ~98% | 0 |

### Top Lessons (Verified Across Milestones)

1. Research-first approach prevents rework (verified in v1.0 and v1.1 -- zero surprises both times)
2. Fine-grained plans (~4 min avg) keep momentum and reduce context-switching cost
3. Incremental migration beats big-bang (verified in v1.1 Phase 10 -- tests green at every commit)
4. Gap closure plans catch integration issues early when forced by validation (verified in v1.1)
