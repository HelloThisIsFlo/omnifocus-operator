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

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 11 | 22 | First milestone -- established GSD + TDD workflow |

### Cumulative Quality

| Milestone | Tests | Coverage | Tech Debt Items |
|-----------|-------|----------|-----------------|
| v1.0 | 203+ (177 pytest + 26 vitest) | ~98% | 4 (all low severity) |

### Top Lessons (Verified Across Milestones)

1. Research-first approach prevents rework (verified by zero model surprises in v1.0)
2. Fine-grained plans (~4 min avg) keep momentum and reduce context-switching cost
