# Milestones

## v1.1 HUGE Performance Upgrade (Shipped: 2026-03-07)

**Phases:** 4 (10-13) | **Plans:** 11 executed
**Requirements:** 18/18 satisfied
**Tests:** 313 pytest, 26 Vitest, UAT passed (all phases)
**Timeline:** 1 day (2026-03-07) | 88 commits
**LOC:** ~14,144 Python (+13,192 / -2,252 vs v1.0)
**Git range:** `v1.0..v1.1`

**Key accomplishments:**
1. Two-axis status model (Urgency + Availability) replacing single-winner TaskStatus/ProjectStatus enums across all entities
2. Repository protocol abstracting read path -- BridgeRepository, InMemoryRepository, and HybridRepository are swappable
3. HybridRepository reading all 5 entity types directly from OmniFocus SQLite cache (~46ms full snapshot)
4. WAL-based read-after-write freshness detection (50ms poll, 2s timeout, fallback to .db mtime)
5. Repository factory with OMNIFOCUS_REPOSITORY env var routing (sqlite default, bridge fallback)
6. Error-serving degraded mode when SQLite unavailable with actionable fix instructions

**Delivered:** Direct SQLite cache access as primary read path, eliminating OmniFocus process dependency for reads and providing dramatically faster, more accurate data retrieval with a richer status model.

---

## v1.0 Foundation (Shipped: 2026-03-07)

**Phases:** 11 (1-9 including 8.1, 8.2) | **Plans:** 22 executed (1 skipped)
**Requirements:** 42/42 satisfied (35 original + 7 ERR-*)
**Tests:** 177+ pytest, 26 Vitest, UAT passed (all phases)
**Timeline:** 14 days (2026-02-21 to 2026-03-07) | 234 commits
**LOC:** ~5,943 Python | ~215k JS (bridge + deps) | ~28k TS (tests)
**Git range:** initial commit to `81700ba`

**Key accomplishments:**
1. Full MCP server with `list_all` tool -- three-layer architecture (MCP -> Service -> Repository) returning structured Pydantic data
2. Pluggable bridge abstraction -- InMemoryBridge, SimulatorBridge, and RealBridge swappable via config with zero code changes
3. File-based IPC engine -- atomic writes, async polling, 10s timeout, orphan sweep, OmniFocus sandbox-aware
4. JavaScript bridge script (OmniJS) running inside OmniFocus, completing the end-to-end IPC pipeline
5. BRIDGE-SPEC alignment -- per-entity status resolvers, RepetitionRule redesign, fail-fast enums validated against live OmniFocus
6. Error-serving degraded mode -- fatal startup errors served as actionable MCP tool responses instead of silent crashes

**Known Tech Debt:**
- Missing VERIFICATION.md for phases 08 and 08.1 (UAT evidence exists)
- Plan 08.1-04 (Makefile unified test) skipped
- SUMMARY.md files lack requirements_completed frontmatter

---

