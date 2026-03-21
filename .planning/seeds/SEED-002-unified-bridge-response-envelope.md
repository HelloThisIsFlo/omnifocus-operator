---
id: SEED-002
status: dormant
planted: 2026-03-21
planted_during: v1.2.1 phase 26 (Replace InMemoryRepository with Stateful InMemoryBridge)
trigger_when: when discussing/planning phase 27 — should be considered as a candidate phase to insert before 27
scope: Medium
---

# SEED-002: Investigate unified bridge response envelope

## Why This Matters

Bridge operations currently return inconsistent shapes:
- `get_all` → `{tasks, projects, tags, folders, perspectives}` (flat entity dict)
- `add_task` → `{id, name}` (minimal confirmation)
- `edit_task` → `{id, name}` (minimal confirmation)

At the service layer, this gets further reshaped — `AddTaskResult` and `EditTaskResult` add a `success: bool` field and optional `warnings`, while reads return domain models directly (`AllEntities`, `Task`, `Project`, `Tag`).

A consistent response envelope (e.g. `{success, payload}` or similar) across all bridge operations could:
- Make the bridge protocol more predictable and self-documenting
- Simplify error handling patterns in the repository layer
- Make it easier to add new operations without inventing ad-hoc return shapes each time
- Reduce cognitive load when implementing test doubles (InMemoryBridge, SimulatorBridge)

**This seed is for investigation, not commitment.** The question is whether unification adds real value or just ceremony.

## When to Surface

**Trigger:** When phase 26 completes and discussion/planning of the next phase begins

This seed should be presented during `/gsd:discuss-phase` for phase 27 (or whatever comes after 26). It's a candidate to insert as a phase before 27 — the investigation should happen before committing to new operations that would add more inconsistent return shapes.

Surface conditions:
- Phase 26 is marked complete and next-phase discussion starts
- Any discussion about what to work on next after phase 26

## Scope Estimate

**Medium** — A full phase. Investigation touches bridge protocol, both bridge implementations (real + test doubles), repository layer, and service layer contracts. If unification is adopted, every operation's return path changes.

## Breadcrumbs

Related code and decisions found in the current codebase:

- `src/omnifocus_operator/contracts/protocols.py` — Bridge protocol definition (`send_command` returns `dict[str, Any]`)
- `src/omnifocus_operator/bridge/real.py` — RealBridge implementation
- `tests/doubles/bridge.py` — InMemoryBridge with `_handle_get_all`, `_handle_add_task`, `_handle_edit_task`
- `tests/doubles/simulator.py` — SimulatorBridge
- `src/omnifocus_operator/contracts/use_cases/add_task.py` — `AddTaskResult(success, id, name)` and `AddTaskRepoResult(id, name)`
- `src/omnifocus_operator/contracts/use_cases/edit_task.py` — `EditTaskResult(success, id, name, warnings)` and `EditTaskRepoResult(id, name)`
- `src/omnifocus_operator/repository/bridge_write_mixin.py` — Repository write operations that transform bridge responses

## Notes

Key investigation questions:
1. Should the envelope live at the bridge level (`send_command` return type) or the repository level?
2. Does a typed return from `send_command` (instead of `dict[str, Any]`) make sense, or does it fight the dynamic nature of the OmniJS bridge?
3. Would reads benefit from the envelope, or is it only valuable for writes?
4. How does this interact with the existing `RepoResult` / service-layer result types — consolidation or redundancy?
