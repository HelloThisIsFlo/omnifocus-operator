# Milestones

## v1.2 Writes & Lookups (Shipped: 2026-03-16)

**Phases:** 6 (14-17 including 16.1, 16.2) | **Plans:** 21 executed
**Requirements:** 28/29 satisfied (LIFE-03 reactivation intentionally deferred)
**Tests:** 501 pytest (up from 313)
**Timeline:** 9 days (2026-03-07 → 2026-03-15) | 295 commits
**LOC:** ~20,189 Python (+7,222 / -323 vs v1.1)
**Git range:** `v1.1..v1.2`

**Key accomplishments:**
1. Unified parent model (`parent: {type, id} | null`) replacing separate project/parent fields; `get_all` renamed from `list_all`
2. Get-by-ID tools (`get_task`, `get_project`, `get_tag`) with dedicated SQLite queries and clear not-found errors
3. Full write pipeline (MCP → Service → Repository → Bridge → OmniFocus) with snapshot invalidation and write-through guarantee
4. Task creation (`add_tasks`) — name-only minimum, parent/tag resolution, per-item results, validation before write
5. Task editing (`edit_tasks`) — UNSET sentinel for patch semantics, actions block grouping (tags/move/lifecycle), diff-based tag computation
6. Task lifecycle — complete/drop via `edit_tasks` with no-op detection, educational warnings, and repeating-task awareness

**Delivered:** Complete read+write MCP interface for OmniFocus tasks — agents can look up entities by ID, create tasks with full field control, edit tasks with patch semantics and structured actions, and manage task lifecycle (complete/drop).

**Known Gaps:**
- LIFE-03: Task reactivation deferred — OmniJS `markIncomplete()` API unreliable
- REQUIREMENTS.md descriptions stale for EDIT-03 through EDIT-08 (reference pre-actions-block field names)
- Mutually exclusive tags not enforced at server level (OmniJS allows it; UI-only enforcement)

---

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

