# Milestone v1.1 -- HUGE Performance Upgrade

**Status:** Shipped 2026-03-07
**Tools after:** 1 (`list_all`)
**Git tag:** `v1.1`

## What Was Delivered

- Two-axis status model (Urgency + Availability) replacing single-winner TaskStatus/ProjectStatus enums
- Repository protocol abstracting read path (HybridRepository, BridgeRepository, InMemoryRepository)
- HybridRepository reading all 5 entity types from OmniFocus SQLite cache (~46ms full snapshot)
- WAL-based read-after-write freshness detection (50ms poll, 2s timeout)
- Repository factory with `OMNIFOCUS_REPOSITORY` env var routing (hybrid default, bridge fallback)
- Error-serving degraded mode when SQLite unavailable
- Deprecated model fields removed, shared enums across all entities
- 313 pytest tests, 26 Vitest tests, ~98% coverage

## Details

For full phase-by-phase details, see:
- `.planning/MILESTONES.md` (summary)
- `.planning/milestones/v1.1-phases/` (phase directories)
- `.planning/milestones/v1.1-REQUIREMENTS.md` (requirements archive)
- `.planning/milestones/v1.1-ROADMAP.md` (roadmap archive)
