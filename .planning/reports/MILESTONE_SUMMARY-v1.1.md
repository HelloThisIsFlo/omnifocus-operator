# Milestone v1.1 -- HUGE Performance Upgrade: Project Summary

**Generated:** 2026-03-23
**Purpose:** Team onboarding and project review

---

## 1. Project Overview

OmniFocus Operator is a Python MCP server exposing OmniFocus (macOS task manager) as structured task infrastructure for AI agents. Core value: reliable, simple, debuggable access to OmniFocus data -- executive function infrastructure that works at 7:30am.

**v1.1 goal:** Replace the OmniJS bridge read path with direct SQLite cache access for dramatically faster, more accurate data retrieval. Introduces a two-axis status model (Urgency + Availability) replacing single-winner enums.

**Result:** Full snapshot reads dropped from 1-3s (bridge IPC) to ~46ms (SQLite). OmniFocus no longer needs to be running for reads. The two-axis model surfaces richer status semantics (e.g., a task can be both `overdue` AND `blocked`).

---

## 2. Architecture & Technical Decisions

- **Two-axis status model (Urgency + Availability)**
  - **Why:** Single-winner enums (`TaskStatus`, `ProjectStatus`) lost information -- you couldn't express "overdue AND blocked." SQLite pre-computes independent boolean columns for each axis.
  - **Phase:** 10 (Model Overhaul)

- **Python adapter for bridge-to-model mapping (dict lookup tables)**
  - **Why:** Bridge stays dumb (no new computation in bridge.js). Python adapter maps old bridge status enums to new `urgency`/`availability` values via static dict lookups. In-place mutation for zero-copy.
  - **Phase:** 10

- **Repository protocol with structural typing (`typing.Protocol`)**
  - **Why:** Swappable read-path implementations without inheritance coupling. `HybridRepository` (SQLite), `BridgeRepository` (OmniJS), and `InMemoryRepository` (tests) all satisfy the same protocol.
  - **Phase:** 11 (DataSource Protocol)

- **No caching in the primary path**
  - **Why:** SQLite reads are ~46ms -- caching adds complexity for no gain. Caching only survives inside `BridgeRepository` (where bridge calls are 1-3s).
  - **Phase:** 11

- **`bridge/` and `repository/` as peer packages (flat, not nested)**
  - **Why:** Bridge is a general-purpose OmniFocus communication layer, not just a data source. Future milestones use Bridge directly for non-data operations (perspective switching, UI actions).
  - **Phase:** 11

- **HybridRepository naming (not SQLiteRepository)**
  - **Why:** Named for future intent -- reads from SQLite, writes via Bridge, freshness handled internally. The name anticipates dual-source behavior without requiring rename when writes arrive.
  - **Phase:** 12 (SQLite Reader)

- **Fresh SQLite connection per read (`?mode=ro`)**
  - **Why:** SQLite WAL readers see a snapshot from when their transaction started. Reusing connections leads to stale reads. Read-only mode prevents accidental writes.
  - **Phase:** 12

- **WAL-based freshness detection (50ms poll, 2s timeout)**
  - **Why:** After a bridge write, WAL file mtime changes at nanosecond precision. Polling every 50ms with a 2s deadline ensures read-after-write consistency without blocking indefinitely.
  - **Phase:** 12

- **Manual bridge fallback via env var (no automatic failover)**
  - **Why:** Silent automatic failover hides broken state. User must know which read path is active. `OMNIFOCUS_REPOSITORY=bridge` is an explicit, temporary workaround.
  - **Phase:** 13 (Fallback and Integration)

- **Error-serving mode for missing SQLite**
  - **Why:** MCP servers are headless -- crashes are invisible. When SQLite DB is missing, the server stays alive and returns actionable errors (expected path + fix + workaround) on first tool call.
  - **Phase:** 13

---

## 3. Phases Delivered

| Phase | Name | Status | One-Liner |
|-------|------|--------|-----------|
| 10 | Model Overhaul | Complete | Replace single-winner status enums with two-axis model, remove deprecated fields, update all tests |
| 11 | DataSource Protocol | Complete | Abstract read path behind Repository protocol, create BridgeRepository + InMemoryRepository, relocate MtimeSource |
| 12 | SQLite Reader | Complete | Implement HybridRepository with read-only SQLite access, row-to-model mapping, WAL-based freshness detection |
| 13 | Fallback and Integration | Complete | Repository factory, bridge fallback via env var, error-serving when SQLite unavailable |

---

## 4. Requirements Coverage

All 18 requirements satisfied. Milestone audit: **PASSED** (18/18 requirements, 4/4 phases, 18/18 integrations, 4/4 E2E flows).

### Data Models (Phase 10)
- MODEL-01: Task/Project expose `urgency` field (overdue/due_soon/none)
- MODEL-02: Task/Project expose `availability` field (available/blocked/completed/dropped)
- MODEL-03: `TaskStatus`/`ProjectStatus` enums removed, replaced by shared `Urgency`/`Availability`
- MODEL-04: Deprecated fields removed (`active`, `effective_active`, `completed` bool, `sequential`, etc.)
- MODEL-05: `contains_singleton_actions` removed from Project, `allows_next_action` removed from Tag
- MODEL-06: All tests/fixtures updated to new model shape

### SQLite Read Path (Phase 12)
- SQLITE-01: Server reads from SQLite cache (~46ms full snapshot)
- SQLITE-02: Read-only mode (`?mode=ro`), fresh connection per read
- SQLITE-03: Row-to-model mapping with two-axis status
- SQLITE-04: OmniFocus not needed for reads

### Freshness (Phase 12)
- FRESH-01: WAL mtime detection, 50ms poll, 2s timeout
- FRESH-02: Fallback to `.db` mtime when WAL absent

### Architecture (Phase 11)
- ARCH-01: Repository protocol abstracts read path
- ARCH-02: Service layer consumes Repository protocol
- ARCH-03: InMemoryRepository exists for testing

### Fallback (Phase 13)
- FALL-01: `OMNIFOCUS_REPOSITORY=bridge` switches read path
- FALL-02: Bridge mode: full urgency, limited availability (no `blocked`)
- FALL-03: SQLite not found -> error-serving with actionable message

---

## 5. Key Decisions Log

| ID | Decision | Phase | Rationale |
|----|----------|-------|-----------|
| D1 | All enums switch to snake_case values | 10 | Consistency. JSON field names stay camelCase via Pydantic alias generator |
| D2 | Clean break, zero backward compatibility | 10 | No real users yet; reserve v2.0 for workflow logic |
| D3 | Bridge stays dumb; adapter in Python | 10 | OmniFocus is extremely slow -- minimize time in JS. Bridge is a relay, not a brain |
| D4 | Incremental migration (not big-bang) | 10 | Tests green at every commit. 4-plan approach kept 177+ tests passing throughout |
| D5 | Repository protocol (not DataSource) | 11 | "DataSource" doesn't imply filtering/querying. Repository feels right for `repo.get_tasks(status=done)` |
| D6 | MtimeSource moves to bridge package | 11 | It's a bridge-internal concern (only BridgeRepository uses it) |
| D7 | HybridRepository, not SQLiteRepository | 12 | Anticipates dual-source (SQLite reads + Bridge writes). No rename when writes arrive |
| D8 | `TEMPORARY_simulate_write()` method | 12 | Deliberately ugly naming to ensure cleanup when real writes are implemented |
| D9 | No automatic SQLite-to-bridge failover | 13 | Silent fallback hides broken state. Explicit is better than implicit |
| D10 | Error message: fix vs workaround distinction | 13 | Fix = find correct SQLite path. Workaround = bridge fallback. Different severity |

---

## 6. Tech Debt & Deferred Items

### Tech Debt
None accumulated during v1.1. Milestone audit found zero anti-patterns, zero TODOs/FIXMEs, zero placeholder implementations.

### Deferred Items
- **Writes through Repository:** HybridRepository will route writes through Bridge internally in a future milestone (v1.2)
- **Repository rename:** HybridRepository may be renamed when writes are added (decided to keep current name)
- **Bridge nesting under Repository:** Reconsidered only if all Bridge usage eventually goes through Repository (kept flat)

### Lessons from Retrospective
- **Incremental migration > big-bang** -- the 4-plan Phase 10 approach kept tests green at every commit
- **Research-first approach continues to pay off** -- zero SQLite schema surprises because research artifacts were thorough
- **Gap closure is a feature, not a bug** -- Nyquist validation caught real integration gaps early
- **Adapter idempotency is essential** -- making the adapter safe to run on already-transformed data prevented a whole class of bugs

---

## 7. Getting Started

### Run the project
```bash
git clone https://github.com/HelloThisIsFlo/omnifocus-operator.git
cd omnifocus-operator
uv sync
```

### Run tests
```bash
uv run pytest              # 313 pytest tests (at v1.1 tag)
cd bridge && npx vitest run # 26 JS tests
```

### Key directories
```
src/omnifocus_operator/
  bridge/          # OmniJS communication layer (adapter, IPC, bridge protocol)
  repository/      # Read path abstraction (HybridRepository, BridgeRepository, InMemoryRepository)
  models/          # Pydantic models with two-axis status (Urgency + Availability)
  server.py        # MCP server with lifespan, repository factory wiring
  service.py       # Service layer (thin pass-through in v1.1)
```

### Where to look first
- `repository/hybrid.py` -- the star of v1.1: SQLite reader with freshness detection (463 lines)
- `repository/protocol.py` -- Repository protocol definition (24 lines)
- `repository/factory.py` -- env-var-driven repository selection
- `bridge/adapter.py` -- old bridge format -> new two-axis model mapping
- `models/enums.py` -- `Urgency`, `Availability`, `TagAvailability`, `FolderAvailability`

### Configuration
| Env Var | Default | Purpose |
|---------|---------|---------|
| `OMNIFOCUS_REPOSITORY` | `sqlite` | Read path: `sqlite` (fast, default) or `bridge` (fallback) |
| `OMNIFOCUS_SQLITE_PATH` | Auto-detected | Override SQLite database location |
| `OMNIFOCUS_BRIDGE` | `real` | Bridge implementation: `real`, `simulator`, `inmemory` |

---

## Stats

- **Timeline:** 2026-03-07 -> 2026-03-07 (single day)
- **Phases:** 4/4 complete
- **Plans:** 11 executed (including 2 gap closure plans)
- **Commits:** 89
- **Files changed:** 102 (+13,419 / -2,264)
- **Tests at completion:** 313 pytest + 26 Vitest (98% coverage)
- **Contributors:** Flo Kempenich
- **Audit:** PASSED -- 18/18 requirements, Nyquist COMPLIANT across all 4 phases

---

*Summary generated from milestone artifacts: ROADMAP, REQUIREMENTS, MILESTONE-AUDIT, CONTEXT/VERIFICATION/RESEARCH files for Phases 10-13, and RETROSPECTIVE.*
