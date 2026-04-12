# Discarded Ideas

Ideas considered and intentionally rejected. Documented so they don't get re-proposed.

## Tag writes (create/edit/delete)
- **What:** Allow agents to create, rename, and delete tags
- **Why discarded:** Use case is too small. Tag creation is a meta/setup activity done rarely in the OmniFocus UI. Not worth the API surface or risk of tag pollution.
- **Date:** 2026-03-17

## Delete projects
- **What:** `delete_projects` tool to permanently remove projects
- **Why discarded:** Blast radius too large, no recovery possible. Same reasoning as `delete_tasks` — all deletion stays manual in OmniFocus UI.
- **Date:** 2026-03-17

## Delete tasks
- **What:** `delete_tasks` tool to permanently remove tasks by ID
- **Why discarded:** Blast radius too high for an agent-driven operation — permanent, no undo, cascades to children. The safer pattern is already well-supported: agent moves tasks under a single root via `moveTo`, then asks the user to delete manually. User keeps full control over destruction. Same reasoning as "Delete projects" above.
- **Date:** 2026-04-12

## "Why is this blocked?" blocking reason
- **What:** Expose the reason a task has `availability: blocked` (sequential parent, project on hold, blocking tag)
- **Why discarded:** Niche use case. If something is blocked, it's blocked. Agent can send user a deep link to the task if they need to investigate.
- **Date:** 2026-03-17

## Multi-device sync awareness
- **What:** Detect OmniFocus sync state, handle conflicts when user edits on iOS while agent edits on macOS
- **Why discarded:** OmniFocus sync is slow but reliable at avoiding conflicts. Too niche to engineer around. Users should work on one thing at a time.
- **Date:** 2026-03-17

## Attachments
- **What:** Read/write task attachments (files, links, images)
- **Why discarded:** Not needed for agent workflows. Bridge already extracts attachment data (BRIDGE-SPEC Section 7) but model intentionally excludes it.
- **Date:** 2026-03-17

## Performance benchmark documentation
- **What:** Formal latency targets, SLAs, scale testing docs
- **Why discarded:** Benchmarks done manually. Not worth maintaining as formal documentation.
- **Date:** 2026-03-17
