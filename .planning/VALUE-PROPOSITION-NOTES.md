# Value Proposition Notes

> WIP notes for README writing — not the final copy.
> These are rough reminders of key selling points to draw from when writing the actual README.

## 1. Better Modeling Than OmniFocus's Raw API

- OmniFocus's `taskStatus` conflates two independent concerns into a single field:
  - **Availability**: Can I work on this right now? (available, next, blocked, completed, dropped)
  - **Urgency**: How time-sensitive is it? (overdue, due_soon, none)
- `taskStatus` uses a priority hierarchy: Overdue > Blocked > DueSoon > Next > Available. If a task is both blocked AND overdue, OmniFocus picks one — the information about the other axis is destroyed.
- OmniFocus Operator decomposes this into two independent axes: `availability` and `urgency`.
- This means an agent can ask "show me blocked tasks that are overdue" — something impossible with the raw API's single-field representation.
- Key point: we're not adding opinions, we're recovering information that OmniFocus's API loses.

## 2. Snapshot-Based Caching

- Instead of hitting OmniFocus via AppleScript/JXA on every query, the bridge captures a point-in-time snapshot of the entire database.
- All queries run in-memory against that snapshot.
- Benefits:
  - **Consistent reads**: No mid-query mutations. You get a coherent view of the database.
  - **Fast filtering**: All filtering happens in Python against in-memory data.
  - **Reduced OmniFocus load**: One snapshot fetch, many queries.

## 3. Pluggable Bridge Architecture

- The bridge layer is abstracted behind an interface.
- Three implementations:
  - `RealBridge` — talks to OmniFocus (manual UAT only).
  - `InMemoryBridge` — fast, deterministic testing with no external dependencies.
  - `SimulatorBridge` — richer test scenarios.
- This abstraction enables safe, fast automated testing without ever touching real OmniFocus data.

## 4. Protocol-First Design

- Built on MCP (Model Context Protocol).
- Any MCP-compatible agent can use it — Claude, or anything else that speaks MCP.
- Not tied to a specific agent, IDE, or workflow tool.

## 5. Workflow-Agnostic

- The server exposes task infrastructure, not workflow opinions.
- Workflow logic (GTD reviews, time-blocking, priority schemes, etc.) lives in the agent, not the server.
- This makes it composable — different agents can implement different workflows on top of the same task data.

## 6. Reliability

- The OmniFocus URL-scheme trigger is fire-and-forget — no delivery guarantee.
- The bridge accounts for this:
  - Atomic writes via `os.replace()` (not `os.rename()`).
  - Nanosecond timestamps (`st_mtime_ns`) for cache freshness.
  - Async I/O (`asyncio.to_thread()`) to avoid blocking the event loop.

## 7. Empirical API Knowledge

- Every field access path and behavior is verified by running audit scripts against live OmniFocus data.
- The bridge is built on empirical findings, not OmniFocus's sparse/misleading documentation.
- Examples of non-obvious behaviors discovered through auditing:
  - Enum values are opaque — only `===` comparison works, no cross-type sharing.
  - `task.active` doesn't mean what you'd think: OnHold and Done projects still have `active=true`.
  - `effective*` fields work identically on project objects and root task objects (no bug, despite what you might expect).
  - Only 4 fields actually need the `project.task.*` access path: `added`, `modified`, `active`, `effectiveActive`.
  - Bridge must use `Project.Status` directly, not reconstruct it from task fields.

---

## Comparison with Alternatives

- 3 competing OmniFocus MCP servers exist (as of early 2026).
- All three share the same limitations:
  - **Synchronous AppleScript/JXA**: Every query hits OmniFocus directly. No caching, no snapshots.
  - **No abstraction layer**: Tightly coupled to the AppleScript bridge. No way to test without a live OmniFocus instance.
  - **No semantic modeling**: They pass through OmniFocus's raw fields as-is, including the conflated `taskStatus`.
- OmniFocus Operator's differentiators: snapshot caching, pluggable bridge, decomposed availability/urgency model, empirical API verification.
