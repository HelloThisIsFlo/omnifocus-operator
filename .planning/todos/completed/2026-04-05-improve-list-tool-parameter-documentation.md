---
created: 2026-04-05T00:03:53.815Z
title: Improve list tool parameter documentation
area: api
files:
  - src/omnifocus_operator/contracts/use_cases/list/tasks.py
  - src/omnifocus_operator/contracts/use_cases/list/projects.py
  - src/omnifocus_operator/contracts/use_cases/list/perspectives.py
  - src/omnifocus_operator/agent_messages/descriptions.py
---

## Problem

External review of list tool documentation identified gaps where agents receive no guidance in the JSON schema. Four distinct areas need attention, each for different reasons.

### 1. Seven parameters have no `Field(description=...)` at all

These parameters appear in the schema as just a name and type — no description string reaches the agent:

**list_tasks (4 params):**
- `flagged` (bool | None) — Agent can't tell whether `true` means "flagged only", `false` means "unflagged only", or if `null` means "both". The tristate semantics aren't obvious from the type alone.
- `inInbox` (bool | None) — "Inbox" is a core OmniFocus concept with specific meaning (unprocessed tasks not assigned to a project). Without description, agent may confuse it with "all tasks" or misunderstand scope. There's also a known subtlety: only returns root-level inbox tasks, not their subtasks.
- `estimatedMinutesMax` (int | None) — Name suggests a ceiling filter, but: is it inclusive or exclusive? What happens to tasks with no estimate — are they included or excluded? Agent has to guess.
- `offset` (int | None) — The tool-level description mentions "offset requires limit", but the parameter itself says nothing. An agent reading just the schema gets no pagination guidance.

**list_projects (3 params):**
- `flagged` (bool | None) — Same tristate ambiguity as list_tasks.
- `offset` (int | None) — Same gap as list_tasks.
- `reviewDueWithin` — The tool-level description documents duration string syntax ("now", "1w", "2m", "1y"), but the parameter's own Field has no description. An agent reading the schema sees the parameter name and nothing else. The useful syntax docs are stranded in the tool description where they're easy to miss.

### 2. Availability defaults silently hide completed/dropped items

All list tools default their `availability` filter to a subset (e.g., `[available, blocked]` for tasks). This means completed and dropped items are excluded by default with no indication to the agent. An agent asking "show me all tasks in Project X" will silently miss completed ones and have no way to know they're being filtered out.

This should be documented on the availability parameter's own `Field(description=...)`, not in the tool-level description — that way the hint appears right where the agent would look to understand the filter.

### 3. Folder hierarchy behavior is undocumented (and unexplored)

Folders can be nested (folders within folders). The current documentation says nothing about:
- Whether `list_folders` returns a flat list or a tree
- Whether nested folders have a `parent` field
- How an agent would reconstruct the hierarchy

**Note:** We haven't actually verified the behavior ourselves yet. This item requires exploration first, then documentation. The `path` field todo (2026-04-04) may relate.

### 4. `list_perspectives` claims to return built-in perspectives but doesn't

The description says "List all perspectives (built-in and custom)" but only custom perspectives are returned. This is a known software limitation tracked in the backlog for v1.5 — the code behavior won't change now.

We should add a brief note to the description making the current behavior clear (e.g., a one-liner about built-in perspectives coming in a future version). This note should be easy to find and remove when v1.5 ships — ideally a single clearly-marked line or a named constant that's obvious to grep for.

## Suggestions (not prescriptive — discuss before implementing)

- Items 1 & 2: Could be a single pass through `descriptions.py` + the query model files. Consider whether all list tools' `availability`, `limit`, and `offset` params should get descriptions too (not just tasks/projects) for consistency.
- Item 3: Start with a quick exploration (call `list_folders` on a database with nested folders, inspect the output) before deciding what to document.
- Item 4: Consider whether this lives in the tool-level `LIST_PERSPECTIVES_TOOL_DOC` constant or as a note on the model. Either way, grep-ability matters — a `# TODO(v1.5): remove` comment or a named constant like `PERSPECTIVES_BUILTIN_NOTE` would make cleanup obvious.
