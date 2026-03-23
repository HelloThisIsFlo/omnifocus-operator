# Milestone v1.2 — Project Summary

**Generated:** 2026-03-23
**Purpose:** Team onboarding and project review

---

## 1. Project Overview

OmniFocus Operator is a Python MCP server that exposes OmniFocus (macOS task manager) as structured task infrastructure for AI agents. It provides reliable, simple, debuggable access to OmniFocus data — executive function infrastructure that works at 7:30am.

**v1.2 "Writes & Lookups"** was the milestone that made the server bidirectional. Prior milestones established read-only access (v1.0 Foundation) and performance (v1.1 SQLite caching at ~46ms). v1.2 added:
- **Lookups:** Agents can inspect individual entities by ID instead of fetching the entire database
- **Task creation:** Full write pipeline from MCP tool call through to OmniFocus
- **Task editing:** Patch semantics with tag management, task movement, and lifecycle actions
- **Shipped:** 2026-03-16 (9 days, 226 commits)

After v1.2, the server exposes 6 MCP tools: `get_all`, `get_task`, `get_project`, `get_tag`, `add_tasks`, `edit_tasks`.

## 2. Architecture & Technical Decisions

- **Decision:** Unified parent model (`ParentRef: { type, id, name } | null`)
  - **Why:** Replaces separate `project` + `parent` string fields. Inbox = null, project parent = type "project", subtask parent = type "task". Mirrors existing TagRef pattern. Name included for agent convenience.
  - **Phase:** 14

- **Decision:** Project-first parent resolution
  - **Why:** When resolving a parent ID, try `get_project` before `get_task`. In practice IDs don't collide, but the order is intentional and deterministic.
  - **Phase:** 15

- **Decision:** UNSET sentinel for patch semantics
  - **Why:** Pydantic can't natively distinguish "field omitted" from "field set to null". Custom sentinel with `__get_pydantic_core_schema__` enables three-way semantics: omit = no change, null = clear, value = set.
  - **Phase:** 16

- **Decision:** "Key IS the position" moveTo design
  - **Why:** `{"ending": "parentId"}` — the key (beginning/ending/before/after) IS the position, the value IS the reference. Exactly one key allowed. Makes illegal states unrepresentable; maps directly to OmniJS position API.
  - **Phase:** 16

- **Decision:** Actions block grouping (field setters vs stateful operations)
  - **Why:** edit_tasks separates idempotent field setters (top-level: name, flagged, dates) from stateful operations (actions: tags, move, lifecycle). Clean semantic boundary, extensible design. Inserted mid-milestone (Phase 16.1) and paid off immediately — lifecycle (Phase 17) dropped into the reserved slot.
  - **Phase:** 16.1

- **Decision:** Diff-based tag computation in Python, not bridge
  - **Why:** Replaced 4-branch ~45-line JavaScript dispatch with ~4 lines. `_compute_tag_diff` computes `(add_ids, remove_ids, warnings)` from set operations. Bridge receives only `addTagIds`/`removeTagIds`. Trust migration: logic moves from low-trust zone (bridge.js, manual UAT only) to high-trust zone (Python, fully tested).
  - **Phase:** 16.2

- **Decision:** Lifecycle via `Literal["complete", "drop"]` — no reactivation
  - **Why:** `markIncomplete()` OmniJS API is unreliable. `drop(false)` universally for all task types (non-repeating: permanent drop; repeating: skip occurrence). Pydantic validates, no dedicated enum needed. Reactivation deferred — user can Cmd+Z in OmniFocus.
  - **Phase:** 17

- **Decision:** Educational warnings in write responses
  - **Why:** Write results include optional `warnings` array for no-ops, cross-state transitions, and repeating task behavior. Teaches agents correct usage through response feedback. LLMs learn in-context from tool responses.
  - **Phase:** 16, 17

- **Decision:** Write-through guarantee via `@_ensures_write_through` decorator
  - **Why:** After a write, the decorator ensures the SQLite WAL mtime has advanced before returning. Reads never wait; writes guarantee freshness. Consistent read-after-write for agents.
  - **Phase:** 16.2

## 3. Phases Delivered

| Phase | Name | Status | One-Liner |
|-------|------|--------|-----------|
| 14 | Model Refactor & Lookups | Complete | Unified parent field, renamed `list_all` to `get_all`, added `get_task`/`get_project`/`get_tag` with dedicated SQLite queries |
| 15 | Write Pipeline & Task Creation | Complete | Full write pipeline (MCP -> Service -> Repository -> Bridge -> OmniFocus) with `add_tasks` tool, parent/tag resolution, and per-item results |
| 16 | Task Editing | Complete | `edit_tasks` with UNSET sentinel patch semantics, tag modes (replace/add/remove), task movement with cycle detection, and educational warnings |
| 16.1 | Actions Grouping | Complete | Restructured edit_tasks API: idempotent field setters (top-level) separated from stateful operations (actions block). Lifecycle slot reserved. |
| 16.2 | Bridge Tag Simplification | Complete | Moved tag set computation to Python `_compute_tag_diff`. Bridge receives only addTagIds/removeTagIds. Fixed stale-cache reads and suppressed-warning bugs. |
| 17 | Task Lifecycle | Complete | Complete and drop tasks via `actions.lifecycle`. No-op detection, cross-state warnings, repeating task occurrence handling. |

## 4. Requirements Coverage

### Naming (1/1)
- ✅ **NAME-01**: MCP tool renamed from `list_all` to `get_all`

### Models (2/2)
- ✅ **MODL-01**: Unified `parent: { type, id, name } | null` replacing separate project/parent fields
- ✅ **MODL-02**: All Pydantic models, adapters, and serialization updated for new parent structure

### Lookups (4/4)
- ✅ **LOOK-01**: Agent can look up a single task by ID (full Task object with urgency/availability)
- ✅ **LOOK-02**: Agent can look up a single project by ID
- ✅ **LOOK-03**: Agent can look up a single tag by ID
- ✅ **LOOK-04**: Not-found returns clear error (not crash/empty response)

### Task Creation (8/8)
- ✅ **CREA-01**: Create task with name (minimum required field)
- ✅ **CREA-02**: Assign to parent (project or task ID, server resolves type)
- ✅ **CREA-03**: Set tags, dates, flag, estimated_minutes, note on creation
- ✅ **CREA-04**: No parent = inbox
- ✅ **CREA-05**: Service validates inputs before bridge execution
- ✅ **CREA-06**: Per-item result (success, id, name)
- ✅ **CREA-07**: Array API with single-item constraint
- ✅ **CREA-08**: Snapshot invalidated after write; next read returns fresh data

### Task Editing (9/9)
- ✅ **EDIT-01**: Patch semantics (omit = no change, null = clear, value = set)
- ✅ **EDIT-02**: Editable fields: name, note, due_date, defer_date, planned_date, flagged, estimated_minutes
- ✅ **EDIT-03**: Replace all tags via `actions.tags.replace`
- ✅ **EDIT-04**: Add tags via `actions.tags.add`
- ✅ **EDIT-05**: Remove tags via `actions.tags.remove`
- ✅ **EDIT-06**: Mutually exclusive tag modes validated (replace is standalone; add/remove combinable)
- ✅ **EDIT-07**: Move to different parent via `actions.move`
- ✅ **EDIT-08**: Move to inbox via `actions.move` with null value
- ✅ **EDIT-09**: Array API with single-item constraint

### Task Lifecycle (4/5)
- ✅ **LIFE-01**: Agent can mark a task as complete via `actions.lifecycle="complete"`
- ✅ **LIFE-02**: Agent can drop a task via `actions.lifecycle="drop"`
- ⚠️ **LIFE-03**: Reactivation — **intentionally deferred**. OmniJS `markIncomplete()` API unreliable. User can Cmd+Z in OmniFocus.
- ✅ **LIFE-04**: Lifecycle interface design resolved via research spike
- ✅ **LIFE-05**: Edge cases documented (repeating tasks, cross-state transitions)

**Milestone Audit Verdict:** TECH DEBT — 28/29 requirements met, 1 intentional deferral. All 6 phases passed verification. 6/6 Nyquist compliant.

## 5. Key Decisions Log

| ID | Decision | Phase | Rationale |
|----|----------|-------|-----------|
| D-14.1 | ParentRef shape: `{ type, id, name } | null` with string literal type | 14 | Mirrors TagRef pattern; name for agent convenience; null for inbox |
| D-14.2 | Not-found = MCP error (`isError: true`), no ID format validation | 14 | Simple "query and report" — let "not found" cover all invalid/missing cases |
| D-14.3 | Get-by-ID returns bare entity (no envelope) | 14 | Same fields as `get_all`, identical Pydantic model |
| D-15.1 | Single `parent` ID field, server resolves project-first | 15 | Agent doesn't need to know if ID is a project or task |
| D-15.2 | Tags specified by name (case-insensitive), ID fallback for disambiguation | 15 | Natural agent interface; ambiguity error includes IDs for retry |
| D-15.3 | `add_tasks` plural with single-item constraint | 15 | Future-proofed for batch; validation error if more than 1 |
| D-15.4 | HybridRepository gains bridge reference; reads SQLite, writes bridge | 15 | Clean separation: fast reads, reliable writes |
| D-16.1 | UNSET sentinel with `__get_pydantic_core_schema__` | 16 | Three-way semantics impossible with Pydantic's native None |
| D-16.2 | "Key IS the position" moveTo design | 16 | One key = one operation; maps to OmniJS position API; illegal states unrepresentable |
| D-16.3 | Full cycle detection via SQLite parent chain walk | 16 | Cheap (~46ms cache), prevents circular references before bridge call |
| D-16.4 | Educational no-op warnings on all write responses | 16 | LLMs learn patch semantics from tool response feedback |
| D-16.1.1 | No backward compatibility — clean break on API restructuring | 16.1 | Alpha with single user; new shape designed as if from scratch |
| D-16.1.2 | Actions block: tags + move + lifecycle (reserved) | 16.1 | Field graduation pattern; lifecycle slot ready for Phase 17 |
| D-16.2.1 | `_compute_tag_diff` set operations in Python | 16.2 | Trust migration from low-trust bridge.js to fully-tested Python service |
| D-17.1 | Two lifecycle values: "complete" and "drop" (imperative verbs) | 17 | CQRS distinction: commands vs state adjectives (completed/dropped) |
| D-17.2 | `drop(false)` universally — no separate "skip" value | 17 | Non-repeating: permanent drop. Repeating: skips occurrence. One code path. |
| D-17.3 | Reactivation ("reopen") deferred entirely | 17 | `markIncomplete()` unreliable; no practical agent use case |

## 6. Tech Debt & Deferred Items

### From Milestone Audit
- **LIFE-03 reactivation deferred** — REQUIREMENTS.md checkbox marked Complete but feature not implemented. Documentation discrepancy.
- **Stale REQUIREMENTS.md descriptions** — EDIT-03 through EDIT-08 still reference pre-Phase 16.1 field names (`tags`, `add_tags`, `remove_tags`, `parent`) instead of actions block shape
- **Phase 16.2 Plan 03 SUMMARY stale** — States "stale-check on get-by-ID" but implementation uses `@_ensures_write_through` decorator pattern
- **Mutually exclusive tags not enforced at server level** — OmniJS allows simultaneous tag operations; enforcement is UI-only. Deferred to future milestone.

### From Retrospective
- Phase 16 grew from 3 to 6 plans — tag modes and movement were more complex than anticipated
- LIFE-03 should have been flagged during requirements phase, not discovered during implementation
- SUMMARY.md files lack `one_liner` field, preventing auto-extraction at milestone completion

### Deferred Ideas (captured in CONTEXT.md files)
- Summary/lightweight mode for `get_all` (related to v1.4 field selection)
- Position field for `add_tasks` (reuse moveTo model)
- Bridge.js simplification to match new actions API shape (completed in Phase 16.2 for tags)
- `"reopen"` / `"reactivate"` lifecycle action
- `delete_tasks` tool (v1.4)

## 7. Getting Started

- **Run the project:**
  ```bash
  git clone https://github.com/HelloThisIsFlo/omnifocus-operator.git
  cd omnifocus-operator && uv sync
  ```
- **Run tests:** `uv run pytest` (always use `uv run`, never bare `pytest`)
- **Key directories:**
  - `src/omnifocus_operator/` — main package
  - `src/omnifocus_operator/models/` — Pydantic models (read + write)
  - `src/omnifocus_operator/repository/` — data access (HybridRepository, protocol)
  - `src/omnifocus_operator/service.py` — validation, resolution, business logic
  - `src/omnifocus_operator/server.py` — MCP tool registration
  - `src/omnifocus_operator/bridge/` — OmniJS bridge script + IPC
  - `tests/` — pytest suite
  - `bridge/tests/` — Vitest suite for bridge.js
- **Where to look first:**
  - `server.py` — entry point, all 6 MCP tools registered here
  - `service.py` — core logic (validation, parent/tag resolution, tag diff, lifecycle, movement)
  - `models/write.py` — UNSET sentinel, TaskCreateSpec, TaskEditSpec, ActionsSpec, MoveToSpec
  - `bridge/bridge.js` — OmniJS handlers (handleAddTask, handleEditTask, handleGetAll)
- **Architecture:** Three-layer: MCP Server -> Service -> Repository. Reads via SQLite (~46ms). Writes via OmniJS bridge with write-through guarantee.
- **Safety:** Never touch `RealBridge` in automated tests. All test code uses `InMemoryBridge` or `SimulatorBridge`. See SAFE-01/SAFE-02 in CLAUDE.md.

---

## Stats

- **Timeline:** 2026-03-07 → 2026-03-16 (9 days)
- **Phases:** 6/6 complete
- **Plans:** 21 executed
- **Commits:** 226
- **Files changed:** 183 (+30,560 / -1,155)
- **Tests at completion:** 527 (501 pytest + 26 vitest), 94% coverage
- **Contributors:** Flo Kempenich
