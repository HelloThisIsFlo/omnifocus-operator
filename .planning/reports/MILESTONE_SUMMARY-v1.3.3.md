# Milestone v1.3.3 — Ordering & Move Fix

**Generated:** 2026-04-12
**Purpose:** Team onboarding and project review

---

## 1. Project Overview

**OmniFocus Operator** is a production-grade MCP server exposing OmniFocus (macOS task manager) as structured task infrastructure for AI agents. It provides 11 MCP tools across read and write operations, with SQLite-cached reads (~46ms) and OmniJS bridge writes.

- **Target users:** AI agents (Claude, etc.) that need to manage OmniFocus tasks programmatically
- **Core value:** Reliable, simple, debuggable access to OmniFocus data — executive function infrastructure that works at 7:30am
- **Tech stack:** Python 3.12, uv, Pydantic v2, FastMCP v3, SQLite3 (stdlib), OmniJS bridge
- **Scale:** ~11,600 LOC Python (src/), 2,041 pytest tests, 94% coverage, 11 MCP tools

**v1.3.3 focus:** Two surgical enhancements — task ordering and a same-container move fix. Smallest milestone in the project (2 phases, 4 plans, 1 day).

---

## 2. Architecture & Technical Decisions

- **Decision:** Recursive CTE with three anchors (project roots, inbox roots, recursive children) for outline ordering
  - **Why:** Reproduces exact OmniFocus UI order from SQLite `rank` column. Verified against real data (3,062 tasks, ~5ms performance). Single CTE reused across all read paths.
  - **Phase:** 51

- **Decision:** Python-side dotted ordinal computation (not SQL-side ROW_NUMBER)
  - **Why:** SQLite's recursive CTE has limitations with window functions in UNION ALL branches. CTE provides `sort_path` for ordering; Python computes sequential dotted notation (`1`, `1.1`, `1.2`, `2`) from sorted rows. Simpler, more reliable.
  - **Phase:** 51

- **Decision:** Full unfiltered CTE for sparse ordinals
  - **Why:** `list_tasks` with filters could remove siblings (e.g., task 2 filtered out). Computing orders from filtered results would produce sequential `1, 2` instead of correct sparse `1, 3`. Running the full CTE preserves original ordinals.
  - **Phase:** 51

- **Decision:** Inbox-first ordering via `0000000000/` sort_path prefix
  - **Why:** Revised during UAT from "inbox after projects" to "inbox before projects". `0000000000/` sorts lexicographically before any project prefix. Matches user expectation that inbox is the primary workspace.
  - **Phase:** 51

- **Decision:** Always-translate move pattern (no same-vs-different branching)
  - **Why:** OmniFocus API silently no-ops on same-container beginning/ending moves. Instead of branching on "is this the same container?", always translate `beginning` → `moveBefore(first_child)` and `ending` → `moveAfter(last_child)` when children exist. One code path, simpler logic.
  - **Phase:** 52

- **Decision:** Move translation in `domain.py` per architecture litmus test
  - **Why:** "Would another OmniFocus tool make this same choice?" — the decision to fix the API quirk is opinionated product behavior, not universal plumbing. Another tool might accept the limitation. Domain layer is correct.
  - **Phase:** 52

- **Decision:** Position-specific no-op via self-reference (`anchor_id == task_id`)
  - **Why:** After translation, if the first child tries to move to "beginning", it translates to `moveBefore(self)` — a self-reference. This is the no-op signal. Clean, catches all edge cases (SC6-SC9) without container-membership logic.
  - **Phase:** 52

---

## 3. Phases Delivered

| Phase | Name | Status | One-Liner |
|-------|------|--------|-----------|
| 51 | Task Ordering | Complete | Read-only `order` field (dotted notation like `"2.3.1"`) on Task responses with correct outline ordering via recursive CTE |
| 52 | Same-Container Move Fix | Complete | Service-layer translation of beginning/ending to moveBefore/moveAfter, with position-specific no-op detection |

---

## 4. Requirements Coverage

All 14 requirements satisfied:

### Ordering (5/5)
- ORDER-01: Task responses include `order` integer field reflecting display order within parent
- ORDER-02: Siblings under same parent have sequential, gap-free order values (1, 2, 3...)
- ORDER-03: `order` field is read-only — not settable via `edit_tasks`
- ORDER-04: Tasks returned in outline order via recursive CTE; approximate ordering for BridgeOnlyRepository fallback
- ORDER-05: Inbox tasks sort **before** projects (revised from "after" during UAT)

### Move Fix (6/6)
- MOVE-01: `moveTo beginning` on same container reorders task to first position
- MOVE-02: `moveTo ending` on same container reorders task to last position
- MOVE-03: Service translates to `moveBefore`/`moveAfter` when target container has children
- MOVE-04: Move to empty container works without translation (direct `moveTo`)
- MOVE-05: Move to different container works as before (no regression)
- MOVE-06: "Same-container move not fully supported" warning removed — it's now fixed

### Warning Accuracy (3/3)
- WARN-01: No-op warning only fires when task is already in the requested position
- WARN-02: "beginning" position check uses `MIN(rank)` among siblings
- WARN-03: "ending" position check uses `MAX(rank)` among siblings

**Milestone Audit:** PASSED — 14/14 requirements, 2/2 phases, 12/12 integration checks, 4/4 E2E flows.

---

## 5. Key Decisions Log

| ID | Decision | Phase | Rationale |
|----|----------|-------|-----------|
| D-01 (P51) | Dotted notation for order (`str \| None`, not `int`) | 51 | LLMs consume output as text — `"2.3.1"` is immediately comprehensible without parent-chain traversal. Agent-first design. |
| D-02 (P51) | All read operations include `order` | 51 | One model shape everywhere — agents don't need to know which method fetched the task |
| D-03 (P51) | Bridge-only degradation returns `None` | 51 | BridgeOnlyRepository lacks rank data. Honest signal of degraded mode — no misleading values |
| D-05 (P51) | Cross-path tests exclude `order` from comparison | 51 | Intentional divergence (str vs None). Known divergence fields list. |
| D-06 (P52) | Always translate when container has children | 52 | No same-vs-different branching. Single code path, simpler logic, fewer bugs |
| D-09 (P52) | Translation lives in domain.py | 52 | Architecture litmus test: opinionated product decision, not universal plumbing |
| D-12 (P52) | No-op detection via `anchor_id == task_id` | 52 | Self-reference check covers all SC6-SC9 scenarios cleanly |
| D-14 (P52) | Remove `MOVE_SAME_CONTAINER` warning entirely | 52 | The fix it promised is now implemented. Replaced by `MOVE_ALREADY_AT_POSITION` with `{position}` placeholder |

---

## 6. Tech Debt & Deferred Items

### Tech Debt (2 minor items)
- Pre-existing `TODO(v1.5)` in `descriptions.py:401` — "Remove when built-in perspectives are supported" (not introduced in this milestone)
- No direct repository-level unit tests for `get_edge_child_id` — covered indirectly via service integration tests (low severity)

### Deferred Ideas
- Add `order` field to Project/Folder/Tag entities — evaluate after task ordering ships
- Golden master re-capture needed after Phase 42 mapper rewrites (blocked on human-only GOLD-01 rule, from v1.3.1)

### Retrospective Lessons
- **Small milestones execute in a day** — 2 phases with tight requirements can go from plan to shipped in a single session
- **Infrastructure phases enable feature phases** — Phase 51's rank column and CTE directly enabled Phase 52's `get_edge_child_id`
- **UAT revisions are first-class outcomes** — ORDER-05 changed from "inbox after projects" to "inbox before projects" during UAT. System working correctly.
- **TDD caught real bugs** — adapter idempotency violation, sparse ordinal computation, ORDER BY tiebreaker — all found during GREEN phase runs

---

## 7. Getting Started

- **Run the project:** `uv run omnifocus-operator` (starts MCP server on stdio)
- **Run tests:** `uv run pytest` (2,041 tests, ~94% coverage)
- **Type check:** `uv run mypy src/omnifocus_operator/ --strict`
- **Key directories:**
  - `src/omnifocus_operator/` — Main source (models/, service/, repository/, contracts/, agent_messages/)
  - `tests/` — pytest suite (test doubles in `tests/doubles/`)
  - `uat/` — Manual UAT scripts (human-only, never automated per SAFE-01/02)
  - `docs/` — Architecture docs, model taxonomy, bridge spec
- **Where to look first:**
  - `src/omnifocus_operator/server.py` — MCP tool definitions (entry point)
  - `src/omnifocus_operator/service/` — Business logic (domain.py, resolver.py, pipeline orchestrators)
  - `src/omnifocus_operator/repository/hybrid/` — SQLite read path (query_builder.py, hybrid.py)
  - `src/omnifocus_operator/models/` — Core Pydantic models (task.py, project.py, etc.)
- **Dev commands:** Always use `uv run` prefix — never bare `pytest` or `python`

---

## Stats

- **Timeline:** 2026-04-11 → 2026-04-12 (1 day)
- **Phases:** 2/2 complete
- **Plans:** 4 executed (~34 min total compute time)
- **Commits:** 54 (including docs/validation/archival)
- **Files changed:** 54 (+5,279 / -418)
- **Contributors:** Flo Kempenich
- **Test suite:** 2,041 pytest + 26 vitest = 2,067 total
- **Cumulative:** 170 plans across v1.0–v1.3.3

---

*Generated from milestone artifacts by GSD milestone-summary workflow.*
