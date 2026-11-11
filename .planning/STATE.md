---
gsd_state_version: 1.0
milestone: v1.4.1
milestone_name: Task Property Surface & Subtree Retrieval
status: complete
stopped_at: Milestone v1.4.1 complete; ready for /gsd-new-milestone to start v1.5
last_updated: "2026-06-28T13:20:36.000Z"
last_activity: 2026-06-28 - Completed quick task 260628-jrk: increase batch limit from 50 to 150 and release as v1.4.4
progress:
  total_phases: 2
  completed_phases: 2
  total_plans: 14
  completed_plans: 14
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-19)

**Core value:** Reliable, simple, debuggable access to OmniFocus data for AI agents -- executive function infrastructure that works at 7:30am.
**Current focus:** Between milestones — v1.4.1 complete; next is `/gsd-new-milestone` for v1.5

## Current Position

Phase: none active (last: 57 — Parent Filter & Filter Unification, complete)
Plan: none active
Status: Milestone v1.4.1 complete; ready for /gsd-new-milestone to start v1.5
Last activity: 2026-06-28 - Completed quick task 260628-jrk: increase batch limit from 50 to 150 and release as v1.4.4

Progress: [██████████] 100% (v1.4.1 — 2/2 phases complete)

## Performance Metrics

**Velocity:**

- Cumulative: 185 plans across v1.0-v1.4 (170 through v1.3.3 + 15 in v1.4)

*Updated after each plan completion*

## Accumulated Context

### Decisions

_(cleared — v1.4 decisions archived to milestones/v1.4-ROADMAP.md and PROJECT.md Key Decisions)_

### Pending Todos

- [2026-03-06] [bridge] Add retry logic for OmniFocus bridge timeouts — [todo file](.planning/todos/pending/2026-03-06-add-retry-logic-for-omnifocus-bridge-timeouts.md)
- [2026-03-08] [service] Enforce mutually exclusive tags at service layer — [todo file](.planning/todos/pending/2026-03-08-enforce-mutually-exclusive-tags-at-service-layer.md)
- [2026-03-08] [bridge] Investigate and enforce serial execution guarantee for bridge calls — [todo file](.planning/todos/pending/2026-03-08-investigate-and-enforce-serial-execution-guarantee-for-bridge-calls.md)
- [2026-03-08] [service] Consider returning full task object in edit_tasks response — [todo file](.planning/todos/pending/2026-03-08-return-full-task-object-in-edit-tasks-response.md)
- [2026-03-30] [testing] Reorganize test suite into unit/integration/golden-master folders — [todo file](.planning/todos/pending/2026-03-30-reorganize-test-suite-into-unit-integration-golden-master-folders.md)
- [2026-04-04] [models] Add path field for hierarchical entities — [todo file](.planning/todos/pending/2026-04-04-add-path-field-for-hierarchical-entities.md)
- [2026-04-06] [testing] Extend golden master to capture SQLite path output — [todo file](.planning/todos/pending/2026-04-06-extend-golden-master-to-capture-sqlite-path-output.md)
- [2026-04-17] [tooling] Submit OmniFocus Operator to MCP registries — [todo file](.planning/todos/pending/2026-04-17-submit-omnifocus-operator-to-mcp-registries.md) — Needs ### Prerequisites.
- [2026-05-20] [tooling] Fix recurring macOS permission prompt on Claude Desktop launch — [todo file](.planning/todos/pending/2026-05-20-fix-recurring-macos-permission-prompt-on-claude-desktop-laun.md)
- [2026-11-11] [server] Defer OmniFocus folder access to first tool call — [todo file](.planning/todos/pending/2026-11-11-defer-omnifocus-folder-access-to-first-tool-call.md)
- [2026-11-11] [server] Finish structured-content dedup middleware — [todo file](.planning/todos/pending/2026-11-11-finish-structured-content-dedup-middleware.md)
- [2026-11-11] [server] Migrate to FastMCP 3.4+ and 4 and lift the pin — [todo file](.planning/todos/pending/2026-11-11-migrate-to-fastmcp-3-4-and-4-and-lift-the-pin.md)
- [2026-11-11] [docs] Update website install guide for Claude Desktop Full Disk Access — [todo file](.planning/todos/pending/2026-11-11-update-website-install-guide-for-claude-desktop-full-disk-ac.md)

### Roadmap Evolution

_(cleared — v1.4 insertions archived to milestones/v1.4-ROADMAP.md)_

### Blockers/Concerns

- **MCP progress-notification transport disconnect** — Claude Code CLI 2.1.105+ regression (upstream #47378 open). Progress notifications disabled via `PROGRESS_NOTIFICATIONS_ENABLED=False`. Re-enable procedure in `src/omnifocus_operator/config.py`.

### Quick Tasks Completed

| # | Description | Date | Commit | Status | Directory |
|---|-------------|------|--------|--------|-----------|
| 260424-j63 | Unify empty-result warning surface (superseded by 260424-kd0) | 2026-04-24 | d44e4742 |  | [260424-j63-unify-empty-result-warning-surface](./quick/260424-j63-unify-empty-result-warning-surface/) |
| 260424-kd0 | Simplify empty-result warning to single static message | 2026-04-24 | 74fbf6ad |  | [260424-kd0-simplify-empty-result-warning-to-single-](./quick/260424-kd0-simplify-empty-result-warning-to-single-/) |
| 260628-jrk | increase batch limit from 50 to 150 and release as v1.4.4 | 2026-06-28 | a68e7109 | Verified | [260628-jrk-increase-batch-limit-from-50-to-150-and-](./quick/260628-jrk-increase-batch-limit-from-50-to-150-and-/) |

## Session Continuity

Last activity: 2026-06-28 - Completed quick task 260628-jrk: increase batch limit from 50 to 150 and release as v1.4.4.
Stopped at: Milestone v1.4.1 complete; ready for /gsd-new-milestone to start v1.5.

## Deferred Items

Items acknowledged and deferred at milestone v1.4.1 close on 2026-04-24:

| Category | Item | Status |
|----------|------|--------|
| uat_gap | 57-UAT.md (0 open scenarios — false positive) | resolved |
| quick_task | 260328-sh9-fix-bysetpos-repetition-rule-parsing-bug | missing |
| quick_task | 260411-fv2-make-date-filter-before-after-bounds-inc | missing |
| quick_task | 260411-h2p-add-date-filters-to-list-projects | missing |
| quick_task | 260411-uf3-surface-preferences-warnings-to-agent-re | missing |
| quick_task | 260417-oiw-strip-batch-result-items-in-add-tasks-an | missing |
| quick_task | 260424-j63-unify-empty-result-warning-surface | missing |
| quick_task | 260424-kd0-simplify-empty-result-warning-to-single- | missing |
| todo | 2026-03-06-add-retry-logic-for-omnifocus-bridge-timeouts.md | pending (low / bridge) |
| todo | 2026-03-08-enforce-mutually-exclusive-tags-at-service-layer.md | pending (low / service) |
| todo | 2026-03-08-investigate-and-enforce-serial-execution-guarantee-for-bridge-calls.md | pending (medium / bridge) |
| todo | 2026-03-08-return-full-task-object-in-edit-tasks-response.md | pending (low / service) |
| todo | 2026-03-30-reorganize-test-suite-into-unit-integration-golden-master-folders.md | pending (testing) |
| seed | SEED-001-dropped-repeating-warning-accuracy | dormant |
| seed | SEED-003-bridge-protocol-review-for-direct-calls | dormant |
| seed | SEED-004-adapter-silent-noop-violates-fail-fast | dormant |
| seed | SEED-005-cli-adapter-and-marketing-reframe | dormant |
| seed | SEED-006-marketing-landing-page-milestone | dormant |

Notes:
- Quick-task "missing" status = completion marker absent in GSD tracking schema; all 7 directories exist with real commit SHAs. Carry-over from earlier milestones that didn't archive their quick-task folders.
- Todos + seeds are deliberately carried forward (todos → v1.8; seeds → v1.5/v1.6/v1.8 + landing-page milestone).
