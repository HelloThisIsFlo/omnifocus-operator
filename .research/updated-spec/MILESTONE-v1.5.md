# Milestone v1.5 -- UI & Perspectives

## Goal

The agent can see what the user sees in OmniFocus, switch perspectives, and navigate users to specific tasks. This milestone introduces a second data path — UI operations bypass the repository and talk directly to the bridge for live state. After this milestone, the server can drive the OmniFocus UI.

## What to Build

### Perspective Interaction

**`get_current_perspective()`** -- returns the name of the currently active perspective in OmniFocus. Read-only, no side effects. Bridge call: `document.windows[0].perspective.name`.

**`show_perspective(name)`** -- switches the user's active perspective in OmniFocus. Takes a perspective name (string, case-sensitive). Works for built-in and custom perspectives. This is the first tool with a visible UI side effect -- the tool description must make this clear. If the perspective isn't found: return an error directing the agent to `list_perspectives()`.

**`list_tasks(current_perspective_only: true)`** -- reads live from the OmniFocus UI instead of the snapshot. The service layer calls the bridge directly (bypasses the repository -- UI operations capture live state). Tasks are returned in the same Task model shape, including availability/urgency. All existing filters work on top of the perspective results.

When computing availability/urgency for perspective tasks, the service layer uses the snapshot for cross-entity lookups (parent tasks, sequential siblings, project metadata). The perspective provides the task list; the snapshot provides the context.

### Architecture: BridgePerspectiveMixin + UI Operations

This milestone introduces perspective operations that need the bridge. These split into two categories:

#### Data operations — `BridgePerspectiveMixin` on the repository

A mixin on the hybrid repository that handles bridge-backed perspective data access:

- **`list_perspectives`** — merges bridge-sourced built-in perspectives (Inbox, Projects, Tags, Forecast, Flagged, Review) with SQLite custom perspectives. Resolves the known gap where only custom perspectives were returned. `get_all` also uses this to include built-ins in the full dump.
- **`get_perspective_content`** (name TBD) — reads the current perspective view via the bridge and returns entity IDs. The service layer then queries the repo with those IDs for enrichment through the normal pipeline. This ensures perspective tasks get the same Task model shape, availability/urgency computation, and filter support as regular queries — consistency by construction.

The mixin keeps all perspective bridge logic cohesive in the repository layer. The hybrid repo already has bridge access via its existing write mixin.

#### UI operations — service layer (not yet designed)

Pure UI operations that don't involve data enrichment:

- **`show_perspective`** / **`switch_to_perspective`** — switches the active perspective in OmniFocus
- **`get_current_perspective`** — returns the active perspective name

These bypass the repository. The service layer needs bridge access for these — the exact mechanism is **undecided**. Options discussed: a separate narrow protocol (preferred direction — clarity of intent over permissions), direct bridge access, or something else. To be designed when this milestone is planned.

#### Open design questions

- **Mixin vs service boundary for perspective content reads**: the mixin reads from the bridge (like a UI op) but feeds into the repo query pipeline (like a data op). The mixin owns "ask bridge → return IDs" but the exact contract is not yet designed.
- **Mixin sharing across repo implementations**: the bridge-only repo already gets built-ins for free via `Perspective.all`. Whether both repos share the mixin or only hybrid uses it is undecided.

**Bridge script changes:**
- **`read_view`** -- reads `document.windows[0].content.rootNode.children`, traverses content tree to extract task/entity references. Returns IDs (or objects — TBD) in a format the mixin can consume.
- **`set_perspective`** -- looks up perspective by name across `Perspective.all`, sets it on `document.windows[0]`. Returns success or error.
- **`get_perspective`** -- returns `document.windows[0].perspective.name`.

### Deep Link: Open Task in OmniFocus UI

**`open_task(id)`** -- opens OmniFocus and navigates to a specific task, making it visible in the UI. Uses the task's `omnifocus:///task/{id}` URL scheme.

This allows agents to say "here, look at this task" and navigate the user directly to it. Natural complement to `show_perspective`.

## Key Acceptance Criteria

- `show_perspective` visibly switches the OmniFocus perspective (built-in and custom)
- `get_current_perspective` returns the active perspective name
- `list_tasks(current_perspective_only: true)` returns live perspective tasks with the same Task model shape
- `current_perspective_only` combines with all existing filters
- Default `list_tasks()` (without `current_perspective_only`) works exactly as before
- Unknown perspective returns a clear error directing to `list_perspectives()`
- `open_task` opens the task in OmniFocus UI
- All existing tools work unchanged

## Tools After This Milestone

Fourteen: all eleven from v1.4, plus `show_perspective`, `get_current_perspective`, `open_task`.
