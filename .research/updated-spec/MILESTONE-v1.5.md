# Milestone v1.5 -- Project Writes

## Goal

Agents can create and edit projects programmatically. After this milestone, the server supports full project lifecycle management — creation with type/folder/review settings, editing with patch semantics, and review marking.

## What to Build

### `add_projects([...])`

Creates projects. Fields: `name` (required), `folder` (ID), `type` (`parallel`/`sequential`/`single_action`, default parallel), `due_date`, `defer_date`, `planned_date`, `flagged`, `estimated_minutes`, `note`, `tags`, `review_interval` ({steps, unit}).

### `edit_projects([{ id, changes: {...} }])`

Same patch semantics as `edit_tasks`. Additional project-specific fields:
- `status` (`active`/`on_hold`/`done`/`dropped`) -- needs `Project.Status` enum in OmniJS (**unverified**)
- `type` (parallel/sequential/single_action) -- sets `sequential` + `containsSingletonActions`
- `folder` (ID or null -> root) -- folder movement
- `review_interval` (object or null -> reset to default) -- needs `Project.ReviewInterval` constructor (**unverified**)
- `reviewed` (`true` only) -- marks project as reviewed, advancing next_review_date (**unverified**: likely `markReviewed()`)

No `delete_projects` -- project deletion is always manual in OmniFocus (see DISCARDED-IDEAS.md).

**Prerequisite:** OmniJS API verification spike for the three unverified APIs before implementation.

## Key Acceptance Criteria

- Project creation with type, folder, and review interval works
- `reviewed: true` advances the review schedule
- Patch semantics work identically to `edit_tasks`
- All existing task tools remain unaffected

## Tools After This Milestone

Sixteen: all fourteen from v1.6, plus `add_projects`, `edit_projects`.
