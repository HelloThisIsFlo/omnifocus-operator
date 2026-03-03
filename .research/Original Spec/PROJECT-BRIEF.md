# OmniFocus Operator — Project Brief

## What We're Building

A Python MCP server that exposes OmniFocus (macOS task manager) as structured task infrastructure for AI agents. It powers a daily review workflow — an AI-guided process for triaging inbox tasks, setting deadlines, estimating durations, extracting projects, prioritizing, and planning the day.

The user has ADHD and relies on OmniFocus as their external brain. This is executive function infrastructure: it needs to be reliable, simple, and easy to debug at 7:30am.

- **Name:** OmniFocus Operator
- **Slug:** `omnifocus-operator`
- **Language:** Python 3.11+ (async, Pydantic models, MCP SDK)
- **Repo:** https://github.com/HelloThisIsFlo/omnifocus-operator (public)

## Architecture

Three layers, each with a single responsibility:

```
MCP Server → Service Layer → OmniFocus Repository
```

- **MCP Server**: Thin wrapper. Registers tools, calls service methods, returns results. No logic.
- **Service Layer**: Business logic and use cases. Filtering, semantic translation, search. This is where the intelligence lives — it bridges "what OmniFocus reports" and "what makes sense to a human/agent."
- **OmniFocus Repository**: Data access. Owns the database snapshot and the bridge. Hides all OmniFocus communication complexity.

### The Bridge

The bridge is a pluggable interface (`send_command(operation, params) → response`) with three implementations, injected at startup:

| Bridge | I/O | Trigger | Use case |
|--------|-----|---------|----------|
| **InMemoryBridge** | None — returns data from memory | None | Unit tests, early development |
| **SimulatorBridge** | File-based IPC (write request JSON, poll response JSON) | None — simulator watches the directory | IPC testing without real OmniFocus |
| **RealBridge** | File-based IPC (same as Simulator) | Triggers OmniFocus via `omnifocus:///omnijs-run` URL scheme | Production |

No implicit fallback — the server knows which mode it's in at startup.

### The Database Snapshot

A single in-memory copy of the full OmniFocus database (~2,400 tasks, ~363 projects, ~64 tags, ~79 folders, ~1.5MB JSON). On every read, the repository checks the `.ofocus` directory mtime. If unchanged, serve from memory. If changed, dump fresh from OmniFocus and replace the entire snapshot. No partial invalidation. Filtering is sub-millisecond against the in-memory snapshot.

### IPC Protocol

File-based JSON request/response via OmniFocus's sandbox directory (`~/Library/Containers/com.omnigroup.OmniFocus4/Data/Documents/omnifocus-operator/`). Both sides use atomic writes (`.tmp` → rename) to prevent partial reads.

The bridge script receives a dispatch string via the URL scheme's `arg` parameter, using `::::` (quadruple colon) as delimiter:

```
req123::::dump                        → dump full database
req123::::read_view                   → read current perspective tasks
req123::::set_perspective::::Review   → switch to "Review" perspective
req123::::add_task                    → create task (payload in request file)
```

Read operations encode everything in the argument string. Write operations read their payload from the request file.

### Two Data Paths (from Milestone 4 onward)

- **Data operations** go through the repository, which manages the snapshot: MCP → Service → Repository → Bridge.
- **UI operations** (perspective switching, reading current view) call the bridge directly, bypassing the repository: MCP → Service → Bridge.

### The Bridge Script

`operatorBridgeScript.js` is the source of truth for the data shape. It's an OmniFocus JS script that dumps the full database (tasks, projects, tags, folders, perspectives) as JSON. Pydantic models are derived from what this script returns — don't invent fields. The script is included in the project repo.

## Key Technical Decisions

- **JSON field names from OmniFocus are camelCase.** Pydantic models use snake_case with camelCase aliases for serialization.
- **`effective_*` fields are inherited values.** A task's `effective_due_date` includes deadlines inherited from parent tasks/projects. Always use `effective_*` variants for filtering — filtering on `dueDate` alone misses ~45% of overdue tasks.
- **`taskStatus` is read-only and not exposed.** OmniFocus computes it: `Available`, `Next`, `Blocked`, `DueSoon`, `Overdue`, `Completed`, `Dropped`. These are mutually exclusive. The service layer decomposes this into two intuitive axes — `availability` (can I work on this?) and `urgency` (how close is the deadline?) — and only exposes those.
- **Test data:** Tests use programmatic fixtures via InMemoryBridge. No pre-generated database dump in the repo.
- **Standard Python exceptions.** No custom exception hierarchy — refine later when real error patterns emerge.
- **MCP tools are plural** (`add_tasks`, `edit_tasks`), taking and returning arrays. Bridge operations are singular (`add_task`) — one item at a time.
- **Patch semantics for edits:** omit = no change, `null` = clear the field. This distinction is critical for dates — `due_date: null` means "remove the deadline."

## API Surface (Target: 18 Tools)

### Reads
- `list_all()` — full database snapshot
- `list_tasks(...)` — tasks with filters (inbox, flagged, project, tags, dates, availability, urgency, search, current_perspective_only, fields)
- `list_projects(...)` — projects with filters (status, folder, review_due_within, flagged, fields)
- `list_tags(...)` — tags with status filter
- `list_folders(...)` — folders with status filter
- `list_perspectives()` — all perspectives (built-in + custom)
- `get_task(id)`, `get_project(id)`, `get_tag(id)` — single item by ID
- `count_tasks(...)`, `count_projects(...)` — same filters, returns integer

### UI
- `show_perspective(name)` — switches the OmniFocus UI to a named perspective (visible side effect)
- `get_current_perspective()` — returns the name of the active perspective

### Writes
- `add_tasks([...])`, `delete_tasks([...])` — task creation and deletion
- `edit_tasks([{ id, changes }])` — task editing with patch semantics
- `add_projects([...])`, `edit_projects([{ id, changes }])` — project creation and editing

### Not in Scope
- Project deletion, tag writes, folder writes, task reordering, undo/dry run, full-text indexing

## Server Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `--due-soon-threshold` | `today` | Options: `today`, `24h`, `2d`, `3d`, `4d`, `5d`, `1w`. Should match the user's OmniFocus "Due Soon" preference. |
| `--output-format` | `json` | Planned: `json`, `taskpaper`. TaskPaper is a future milestone. |

## Milestones

| # | Name | Tools After | Theme |
|---|------|-------------|-------|
| 1 | Foundation | 1 (`list_all`) | Architecture proof + real IPC pipeline |
| 2 | Filtering & Search | 2 (`list_all`, `list_tasks`) | Make reads useful — field filters, semantic status, fuzzy search |
| 3 | Entity Browsing & Lookups | 11 | Expand reads to projects/tags/folders/perspectives + single-item lookups + counts |
| 4 | Perspectives & Field Selection | 13 | UI-aware tools + token efficiency |
| 5 | Writes [DRAFT] | 18 | Task and project creation, editing, deletion — scope and acceptance criteria to be finalized before implementation |

Each milestone has its own detailed spec file. Future milestones (TaskPaper output format, production hardening) are not yet planned.
