# Feature Landscape

**Domain:** MCP server API contract evolution -- system location namespace, name-based entity resolution, rich references
**Researched:** 2026-04-05

## Table Stakes

Features agents expect from a well-designed MCP tool API. Missing = agents make more errors, need more round-trips, or hit confusing edge cases.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Rich `{id, name}` references in output | Anthropic's own tool design guide says agents "grapple with natural language names significantly more successfully than cryptic identifiers." Bare IDs force a second lookup to correlate. | Med | All name data already available in SQLite joins. Work is in mappers, not queries. |
| Explicit inbox representation (`$inbox`) | Null overloading is the #1 source of agent confusion in the current API. `null` means 3 things depending on context -- agents can't distinguish them in raw JSON. | Med | Core design decision already validated in spec. Constants in `config.py`. |
| Name-based resolution for write fields | Tags already resolve by name (v1.2), list filters resolve by name (v1.3). Write fields (`parent`, `moveTo`) accepting only IDs is an inconsistency. Agents naturally write names. | Med | Resolver infrastructure exists. Extension to new fields is bounded. |
| Non-null `parent` field | Every task has a parent (project, task, or inbox). Null parent forces agents to check `inInbox` separately. With `$inbox` as a value, null is eliminated. | Low | Simplifies agent-side logic. One fewer null check. |
| `project` field on Task (containing project) | Without this, subtasks of inbox tasks show `parent: TaskRef` with no inbox signal. Agent must walk the parent chain to discover containment. | Med | SQLite `containingProjectInfo` column already exists. No new queries. |
| Educational error messages | When agents misuse `before`/`after` with container IDs, or try `get_project("$inbox")`, errors should teach the correct approach. | Low | ~5 lines per error path. Already the project's pattern. |
| Contradictory filter detection | `project: "$inbox"` + `inInbox: false` is logically contradictory. Silent empty results waste agent round-trips. | Low | Simple check at filter resolution time. |

## Differentiators

Features that go beyond what most MCP servers do. Not expected, but valued -- they reduce agent errors and round-trips.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Three-step resolver precedence (`$` -> ID -> name) | Single, unified resolution model across all entity reference fields. Agents learn one pattern, it works everywhere. Most APIs have inconsistent resolution per endpoint. | Med | The `$` prefix short-circuit is the key innovation -- makes system locations collision-proof against name resolution. |
| Tagged object discriminator for `parent` | `{"project": {...}}` vs `{"task": {...}}` -- the key IS the type. Avoids `exclude_defaults` stripping `Literal` discriminator fields (a known Pydantic v2 gotcha). Already proven by `MoveAction`. | Med | Cleaner than `type` field approaches. Serialization-safe. |
| Warning on `parent: null` in add_tasks | Intuitive compatibility: null means "no parent" which naturally means inbox. Warning educates toward `$inbox` without blocking. Most APIs would silently accept or hard error. | Low | One warning message constant + check in pipeline. |
| `$inbox` in `project` filter | Consistency: `$inbox` works in writes, reads, and now filters. Agent that thinks "inbox is a container" naturally reaches for `project: "$inbox"`. | Low | Resolver already handles `$` prefix; just needs to work in filter context. |
| Inbox warning on `list_projects` search | When a name filter would have matched "Inbox", warn that inbox is a system location with guidance to use `list_tasks`. Prevents agents from searching for a project that doesn't exist. | Low | Substring check against "Inbox" constant, warning if hit. |
| Write vocabulary = read vocabulary symmetry | If the agent writes `folder: "Work"`, output returns `folder: {id: "...", name: "Work"}`. Agent can confirm its own write without a second lookup. Most APIs have asymmetric read/write shapes. | Med | The principle is the differentiator; the implementation is just enriching mappers. |
| `PatchOrNone` elimination | Removing a type concept from the vocabulary. Fewer concepts = simpler mental model for contributors and agents. `$inbox` replaces null-as-inbox, so `PatchOrNone` has no uses left. | Low | Type alias removal + field type changes on `MoveAction`. |

## Anti-Features

Features to explicitly NOT build. These were considered and rejected for specific reasons.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Virtual inbox project in `get_project` / `list_projects` | `Project` model has required fields (review dates, review interval, urgency, availability) meaningless for inbox. Fabricating values creates dishonest data agents might try to edit. | Error with guidance: "Use `list_tasks` with `project: '$inbox'` or `inInbox: true`." |
| Deprecation warnings for `ending: null` | No consumers exist yet (pre-release). Deprecation is for production APIs with existing users. Now is the time for clean breaks. | Hard error. Educate toward `$inbox`. |
| `$` prefix on display name (`name: "$inbox"`) | The `$` is a system reference prefix for IDs, not a display label. OmniFocus calls it "Inbox", not "$inbox". Same pattern as every other entity: ID for API calls, name for display. | `name: "Inbox"` (human-readable). |
| Negation in project filter (`project: "NOT $inbox"`) | Adds query language complexity. The `inInbox: false` boolean already handles negation cleanly. No need for two ways to express the same thing. | Keep `inInbox: false` as the negation mechanism. |
| Fuzzy/Levenshtein matching for name resolution | Over-engineering at this stage. Case-insensitive substring match (already proven in v1.3 filters) is sufficient. Fuzzy matching is planned for v1.4.1 as a separate feature. | Case-insensitive substring match. Error with suggestions on zero matches. |
| `$trash`, `$archive`, or other system locations now | Only `$inbox` has a concrete use case. Pre-building the namespace for hypothetical locations adds complexity without value. The `$` prefix design supports extension later. | Define `$inbox` only. Unrecognized `$`-prefixed strings get a helpful error listing valid system locations. |
| Silent acceptance of `parent: null` on add_tasks | Agents won't learn about `$inbox` if null works silently. The warning is the teaching mechanism. | Accept with warning suggesting `$inbox` or field omission. |

## Feature Dependencies

```
$inbox constant in config.py
  -> Resolver $-prefix short-circuit (step 1 of three-step precedence)
  -> $inbox in add_tasks parent field
  -> $inbox in edit_tasks moveTo fields
  -> $inbox in list_tasks project filter
  -> Contradictory filter detection ($inbox + inInbox: false)
  -> get_project("$inbox") error
  -> list_projects inbox warning

ProjectRef / TaskRef models
  -> Tagged object parent field on Task
  -> project field on Task (uses ProjectRef)
  -> ParentRef removal

FolderRef model
  -> Rich Project.folder output
  -> Rich Folder.parent output

Name-based resolution for write fields
  -> Depends on: existing Resolver._match_by_name (v1.2 tags)
  -> Depends on: existing Resolver.resolve_filter (v1.3 list filters)
  -> Extends to: parent on add_tasks, beginning/ending/before/after on edit_tasks

PatchOrNone elimination
  -> Depends on: $inbox in moveTo (replaces null-as-inbox)
  -> MoveAction fields become Patch[str]
```

## MVP Recommendation

All features in this milestone are tightly coupled -- they form a single coherent contract change. However, if phasing is needed:

**Phase 1 (foundation):**
1. `$inbox` constant + resolver `$`-prefix handling
2. `ProjectRef`, `TaskRef`, `FolderRef` model types
3. Task output changes: `project` field, tagged `parent`, `inInbox` removal

**Phase 2 (writes):**
4. `$inbox` in add_tasks and edit_tasks
5. `PatchOrNone` elimination (MoveAction field type changes)
6. Better `before`/`after` error messages

**Phase 3 (filters + references):**
7. `$inbox` in list_tasks project filter + contradictory filter detection
8. Name-based resolution for write fields
9. Rich `{id, name}` references on Project, Tag, Folder output

**Defer:** Nothing. All features are table stakes for this milestone's goal of eliminating null overloading and making the API vocabulary consistent.

## Key Observations from Research

**Anthropic's own tool design guidance (source: anthropic.com/engineering/writing-tools-for-agents):**
- Agents handle natural language names far better than cryptic identifiers
- Return fields that directly inform downstream agent actions
- Tool docs should read like contracts: purpose, examples, unambiguous types
- This directly validates the `{id, name}` rich reference pattern and name-based resolution

**Sentinel value design (source: abseil.io/tips/171):**
- General software engineering advice discourages sentinel values *within a type's valid domain*
- The `$` prefix approach avoids this pitfall: `$inbox` is syntactically disjoint from valid OmniFocus IDs and entity names
- The prefix creates a reserved namespace, not a magic value pretending to be a regular string

**GitHub's GraphQL API pattern:**
- Uses global node IDs for machine references, name-based queries as alternative entry points
- Validates the dual-access pattern: IDs for precision, names for convenience
- OmniFocus Operator's three-step resolver is a superset of this pattern

## Sources

- [Anthropic: Writing Tools for Agents](https://www.anthropic.com/engineering/writing-tools-for-agents) -- directly validates rich references and name-based input
- [Abseil Tip #171: Avoid Sentinel Values](https://abseil.io/tips/171) -- context for why `$` prefix is better than in-band sentinels
- [GitHub GraphQL: Using Global Node IDs](https://docs.github.com/en/graphql/guides/using-global-node-ids) -- dual ID/name access pattern precedent
- [Tool Calling Optimization](https://www.statsig.com/perspectives/tool-calling-optimization) -- agent tool design patterns
- Milestone spec: `.research/updated-spec/MILESTONE-v1.3.1.md`
