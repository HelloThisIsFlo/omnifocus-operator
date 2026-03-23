# Feature Landscape

**Domain:** Write pipeline + get-by-ID tools for OmniFocus MCP server (v1.2)
**Researched:** 2026-03-07

## Table Stakes

Features users expect from a task management write API. Missing = the write pipeline feels incomplete.

| Feature | Why Expected | Complexity | Dependencies |
|---------|--------------|------------|--------------|
| Get-by-ID (`get_task`, `get_project`, `get_tag`) | Agents need to inspect single entities after writes, not parse 2.7MB `list_all` dumps | Low | SQLite: single-row query; Bridge: dict lookup from snapshot |
| Task creation (`add_tasks`) | Core write primitive -- agents must be able to add tasks to inbox, projects, or as subtasks | Med | Bridge `add_task` command, request file IPC, service validation |
| Task field editing (`edit_tasks`) | Agents must change names, dates, flags, notes, estimated minutes on existing tasks | Med | Bridge `edit_task` command, patch semantics (omit/null/value) |
| Task movement (project, parent) | Reassigning tasks between projects/parents is fundamental to task management | Med | `edit_tasks` field: `project` or `parent_task_id` changes |
| Tag management on tasks | Tags are the primary categorization mechanism; add/remove/replace must work | Med | Three mutually exclusive modes: `tags`, `add_tags`, `remove_tags` |
| Task completion (`markComplete`) | Most common lifecycle operation; agents must be able to close tasks | Low | Bridge: `task.markComplete()`, well-documented OmniJS API |
| Task dropping (`drop`) | Second lifecycle operation; agents must be able to abandon tasks | Low | Bridge: `task.drop(true)`, irreversible for non-repeating tasks |
| Snapshot invalidation after writes | Next read must reflect the write; stale data after mutations breaks agent trust | Low | WAL mtime detection (v1.1) handles this; bridge mode needs snapshot.stale flag |
| Validation before bridge execution | Catch errors in Python (fast, testable) before sending to OmniJS (slow, untestable) | Med | Service layer checks: name required, IDs exist, mutual exclusions |
| Clear error messages | Agent must understand what went wrong: "Tag 'foo' not found" not "bridge error" | Low | Service-layer validation produces structured errors |
| Batch input/output (array API) | Even if limited to single-item initially, the API shape must be arrays for forward compat | Low | `add_tasks([...])` / `edit_tasks([...])` -- plural naming, array in/out |
| Patch semantics (omit/null/value) | Industry-standard for partial updates; agents shouldn't need to send unchanged fields | Med | Bridge: `hasOwnProperty` checks. Python: Pydantic model with Optional + sentinel |

## Differentiators

Features that elevate this beyond "it works" into "agents love using it."

| Feature | Value Proposition | Complexity | Dependencies |
|---------|-------------------|------------|--------------|
| Task reactivation (`markIncomplete`) | Undo completion -- rare but valuable when agent or user completes wrong task | Low | Bridge: `task.markIncomplete()`. Caveat: no-ops on dropped tasks |
| Three tag edit modes | `add_tags`/`remove_tags` avoids agents needing to read-then-write full tag lists | Low | Mutual exclusion validation in service layer |
| Move to inbox (`project: null`) | Explicitly un-assigning a task is a distinct operation from "leave project unchanged" | Low | Patch semantics: `null` = clear, omit = no change |
| Rich tool descriptions | LLM-optimized descriptions with field tables, examples, edge case notes | Low | No code dep; just thorough docstrings |
| Per-item result reporting | `[{ success: true, id: "xxx", name: "..." }]` -- agent knows exactly what happened | Low | Response model design |
| Request file payloads for writes | Larger/complex JSON payloads via file IPC instead of argument strings | Med | New bridge command pattern; existing IPC infra |

## Anti-Features

Features to explicitly NOT build in v1.2.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| SQLite write path | OmniFocus owns its database; direct writes corrupt state or get overwritten on sync | All writes go through OmniJS bridge exclusively |
| True batch (multi-item) execution | OmniJS has no transactions; partial failures are unrecoverable. Prove single-item first | Accept arrays but enforce length=1 initially; extend to batch in future milestone |
| Rollback / undo support | `document.undo()` exists but is fragile; not a real transaction mechanism | Best-effort execution with clear error reporting |
| Dry run / preview mode | Adds complexity for unclear benefit; agents can validate by reading before writing | Skip; validation catches most errors pre-execution |
| `delete_tasks` | Deletion is destructive and rarely needed; `drop` covers most "remove" intent | Defer to v1.4; `edit_tasks` with move/re-parent handles reorganization |
| Project writes (`add_projects`, `edit_projects`) | Unverified OmniJS APIs (`Project.Status`, `Project.ReviewInterval`); low priority for user's workflow | Defer to v1.4 |
| Tag/folder writes | Low priority; tags are created manually, folders are structural | Defer to future milestone |
| Repeating task special handling | Completing/dropping repeating tasks has complex semantics (this instance vs series); needs research spike | Research during lifecycle phase; use `drop(true)` (all occurrences) as safe default |
| Idempotency / retry logic | Production hardening concern; v1.2 is about proving the pipeline works | Defer to v1.5 |
| Optimistic concurrency (ETags, versions) | Overkill for single-user local MCP server | Not planned |

## Feature Dependencies

```
Get-by-ID tools (get_task, get_project, get_tag)
  -- No deps on write pipeline; can ship independently
  -- Enables write validation (create task, then get_task to verify)

Write pipeline infrastructure
  --> Bridge script: new commands (add_task, edit_task)
  --> Bridge script: request file payload reading
  --> Repository protocol: write methods added
  --> Service layer: validation logic
  --> Snapshot invalidation after writes

add_tasks
  --> Write pipeline infrastructure
  --> Service validation: name required, project/parent_task_id exist, tags exist
  --> Bridge: new Task(name, project), property assignments

edit_tasks (simple fields)
  --> Write pipeline infrastructure
  --> add_tasks proven (same pipeline)
  --> Patch semantics in bridge (hasOwnProperty checks)
  --> Tag mode mutual exclusion validation

edit_tasks (lifecycle: complete/drop/reactivate)
  --> edit_tasks simple fields proven
  --> Research spike: OmniJS lifecycle API surface
  --> Interface decision: field-in-payload vs action-style
```

**Critical path:** Get-by-ID (warm-up) --> Write pipeline infra --> add_tasks --> edit_tasks (simple) --> edit_tasks (lifecycle)

## MVP Recommendation

**Phase 1 -- Get-by-ID (warm-up, low risk):**
1. `get_task(id)`, `get_project(id)`, `get_tag(id)`
2. SQLite single-row queries + bridge dict lookups + InMemory dict lookups
3. Not-found error handling

**Phase 2 -- Task creation:**
4. Bridge `add_task` command with request file payload
5. Write pipeline: MCP -> Service -> Repository -> Bridge -> invalidate
6. `add_tasks` MCP tool (single-item initially)
7. Service validation (name required, project/parent exist, tags exist, mutual exclusions)

**Phase 3 -- Task editing (simple fields):**
8. Bridge `edit_task` command with patch semantics
9. `edit_tasks` MCP tool for: name, note, dates, flagged, estimated_minutes
10. Tag editing (three modes with mutual exclusion)
11. Task movement (project, parent_task_id, move to inbox)

**Phase 4 -- Lifecycle changes:**
12. Research spike: OmniJS `markComplete()`, `markIncomplete()`, `drop()` behavior
13. Interface decision for lifecycle in edit payload
14. Complete, drop, reactivate via `edit_tasks`

**Defer:** Nothing within v1.2 scope. Batch execution (multi-item) deferred but API shape is future-proof.

**Ordering rationale:**
- Get-by-ID first: zero write risk, validates new repository methods, enables write verification
- add_tasks before edit_tasks: creation is simpler (no patch semantics), proves the full write pipeline
- Simple edits before lifecycle: field assignments are well-understood; lifecycle has open questions needing a research spike
- Each phase builds on the previous: same pipeline, increasing complexity

## Open Questions (Resolve During Implementation)

| Question | Phase | Impact |
|----------|-------|--------|
| Partial failure strategy (best-effort vs stop-on-first) | Phase 2-3 | Response format; initially moot with single-item constraint |
| Batch response format (`{ success, data }` vs `{ added, errors }`) | Phase 2 | API contract; single-item makes this trivial initially |
| Lifecycle interface (field edit vs action-style) | Phase 4 | Determines `edit_tasks` payload shape for complete/drop |
| `markIncomplete()` on dropped task (confirmed no-op?) | Phase 4 | Reactivation strategy; may need `document.undo()` |
| Repeating task completion semantics | Phase 4 | `drop(false)` vs `drop(true)` behavior |
| Task movement API (`assignedContainer` vs property writes) | Phase 3 | Bridge implementation for project/parent changes |

## Sources

- `.research/updated-spec/MILESTONE-v1.2.md` -- detailed v1.2 spec with field tables and open questions
- `.research/deep-dives/omnifocus-api-ground-truth/BRIDGE-SPEC.md` -- write operations, property writes, creation, caveats
- `.planning/PROJECT.md` -- scope, constraints, key decisions
- [54 Patterns for Building Better MCP Tools](https://www.arcade.dev/blog/mcp-tool-patterns) -- MCP tool design patterns
- [MCP Tools Specification](https://modelcontextprotocol.io/specification/2025-06-18/server/tools) -- official MCP tools spec
- [OmniFocus Tasks - Omni Automation](https://www.omni-automation.com/omnifocus/task.html) -- OmniJS task API reference
