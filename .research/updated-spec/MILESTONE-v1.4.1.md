# Milestone v1.4.1 — Task Property Surface & Subtree Retrieval

## Status: Rough Intention

This milestone is not yet designed. It captures directions collected during and after v1.4. Scope, include-group placement, and stripping semantics need a design conversation before planning.

## Goal

Close two categories of friction left after v1.4:

1. **Task property exposure** — OmniFocus properties the MCP server currently hides (auto-complete, parallel/sequential, presence of notes / repetition / attachments). v1.4 reshaped how responses are delivered; v1.4.1 closes remaining gaps on *what* is exposed.
2. **Subtree retrieval** — today the agent can find a task via search but has no clean way to fetch its descendants without walking the full project. A `parent` filter on `list_tasks` mirrors the existing `project` filter and eliminates the workaround.

## Why a Point Release Instead of a Regular Milestone

Small, focused additions that round out v1.4 rather than warrant a full milestone — same pattern as v1.3.1 / v1.3.2 / v1.3.3 after v1.3. Each item is a narrow field addition or filter extension, not a new tool or architectural change.

## What to Build (rough)

### Auto-complete (read + write)

Expose OmniFocus's auto-complete setting on tasks. Lets the agent:
- Read whether a task is a grouping (auto-complete ON) vs a parent task (OFF).
- Toggle it when applying the bracket convention, without the human having to do it manually.

### Parallel / sequential task type (read, create, edit)

Expose whether a task/project is parallel or sequential on `add_tasks`, `edit_tasks`, and in read output:
- Set at creation time — e.g., checklist-style groupings are typically parallel.
- Flip during restructuring.

### Presence flags in default response (`hasNote`, `hasRepetition`, `hasAttachments`)

A family of boolean presence flags, all following the same pattern: `true` when the underlying content exists, stripped when `false` (so they only appear as `true`). They signal the agent "there's content here — ask for it via the appropriate `include` group if you need it."

| Field | Signals |
|-------|---------|
| `hasNote` | A note exists — fetch via `include: ["notes"]` |
| `hasRepetition` | A repetition rule exists — fetch via the appropriate include group |
| `hasAttachments` | Attachments exist — `true`-only, stripping makes it cheap even if attachments aren't fully exposed yet |

**Design criterion:** this pattern earns its keep when the `true` case is *rare*. If most tasks have the field, the flag ends up present most of the time and the signal dilutes. All three above are genuinely uncommon in typical databases — cheap to include, useful when they fire.

### Rename `hasChildren` → `hasSubtasks`

The existing `hasChildren` boolean becomes `hasSubtasks` for vocabulary consistency with the rest of the API (`parent` field, upcoming `parent` filter, "subtasks" phrasing in docs). **Stays in the `hierarchy` include group, not the default response** — unlike the presence flags above, subtasks are *common*, so keeping it behind the explicit include avoids cluttering the default payload.

### `parent` filter on `list_tasks`

A new filter on `list_tasks` that mirrors the existing `project` filter, resolving a task reference instead of a project reference.

**Contract:**
- Accepts name (case-insensitive substring) or ID — same three-step resolver precedence as every other entity reference (`$` prefix → exact ID → name substring).
- Returns **all descendants** of the resolved task, at any depth.
- Returns the **parent task itself** in the result set alongside its descendants — per the "show more" principle in `docs/architecture.md`. The agent asked for a subtree; returning children without the root leaves them disembodied. Including the parent delivers a complete, interpretable subtree.

**Motivation:** today, finding a task via search and then getting its subtree is cumbersome — the agent has to identify the containing project, fetch the project (which returns *everything* in it), and filter the result locally. A `parent` filter makes subtree retrieval a single call with the same ergonomics as `project`.

**Alternatives considered and rejected:**
- *Auto-expand children in search results* — bloats every query with hierarchy, confusing when the user just wanted to find a task.
- *Mitigate the bloat with warnings* — warnings add cognitive overhead without solving the underlying problem.

The filter approach is strictly additive: search behaviour stays lean, subtree retrieval becomes explicit and cheap.

## Key Questions (to be explored)

- **Include-group placement for auto-complete + parallel/sequential.** Both are structural/behavioural task properties. Do they live in an existing include group (`time`? `hierarchy`?), or do they deserve a new group (e.g. `structure` / `behaviour`)? Likely grouped together — same question applies to both.
- **Project scope.** Auto-complete and parallel/sequential also apply to projects. Does v1.4.1 cover only tasks, or projects too? (Project writes are v1.7 — but reads could land earlier.)
- **Default vs. opt-in for the new fields.** Presence flags are planned as default-included (strip-when-false). The two structural/behavioural fields (auto-complete, parallel/sequential) probably sit behind an include group — confirm during design.
- **`parent` filter interaction with other filters.** Does `parent: "X"` compose with `project: "Y"`, `tags: [...]`, date filters, etc.? Presumably yes (AND-composed, same as everything else). Worth confirming the semantics for the "parent itself" inclusion — does the parent task still appear if it fails a sibling filter? (Probably yes — the parent is a structural anchor, not a filter match.)
- **`hasAttachments` without full attachment support.** The flag can ship before attachment retrieval is implemented — it's useful on its own ("there's something here, go look in OmniFocus"). Decide whether to land the include group for attachments in this milestone or defer.
