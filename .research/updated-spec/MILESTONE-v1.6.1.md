# Milestone v1.6.1 -- Smart Perspective Content

## Status: Rough Intention

This milestone is not yet designed. It captures a direction discussed during the v1.6 architecture brainstorm. The scope and feasibility need validation before planning.

## Goal

The agent presents perspective content the way the user sees it in OmniFocus — same grouping, same organization, same structure. v1.6 returns a flat list of task IDs; this milestone makes the response shape match the perspective's actual layout. If the user's perspective groups by project, the agent shows projects with nested tasks, not a flat task list.

## What to Build (rough)

### Perspective-aware content presentation

v1.6 returns task IDs from perspective views (projects silently skipped). This milestone makes the response richer:

- Perspectives organized by **projects** → return projects with their task hierarchy
- Perspectives organized by **individual actions** → return tasks (same as v1.6)
- Perspectives organized by **tags** → return tags with grouped tasks
- The response type depends on the perspective's configuration

### Perspective rule parsing

OmniFocus perspectives have rules (stored as plist data in the SQLite `Perspective` table's `valueData` column) that define filtering and grouping. Parsing these rules enables:

- **Fidelity** (primary): understanding the perspective's grouping mode (by project, by tag, by individual action) so the response structure matches what the user sees
- **Performance** (secondary): translating perspective filters into SQL queries against the snapshot — no bridge call needed for custom perspectives

### Caveats

- Perspective rules are a **private format** — not documented by Omni Group, could change across versions
- Built-in perspectives have no rules in SQLite (they're app-level constructs) — bridge is still needed for those
- Bridge reads remain ground truth. Rule parsing adds structure awareness on top.
- This might turn out to be not worth the complexity. The bridge approach from v1.6 may be sufficient for all practical use cases. "Maybe never" is a valid outcome.

## Key Questions (to be explored)

- What does the perspective rule plist format actually look like? Spike needed.
- Is the grouping/organization mode readable from the rules, or only from the live UI?
- How stable is the format across OmniFocus versions?
- Does the agent actually benefit from projects-in-perspectives, or are task IDs sufficient for all practical workflows?
