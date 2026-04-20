# Maybe Ideas

Ideas that might be worth exploring but need more thought before committing.

## Add task idempotency
- **What:** Detect duplicate `add_tasks` calls with identical arguments and prevent creating duplicate tasks
- **Why maybe:** Retrying `add_tasks` after a timeout creates duplicates (task may have been created but response was lost). `edit_tasks` is naturally idempotent. Could use a request hash or idempotency key to deduplicate.
- **Complexity:** Non-trivial — needs state tracking (recent request hashes) or bridge-level dedup. v1.7 mentions idempotency but doesn't detail this specific case.

## Fuzzy search
- **What:** Typo-tolerant matching on task names/notes via `search` parameter on `list_tasks`. Index-based, ranking: exact > substring > fuzzy.
- **Why maybe:** Substring search from v1.3 covers the vast majority of real queries. Fuzzy helps with typos but that's a comfort feature, not a workflow blocker.
- **Complexity:** In-memory index built from snapshot, refreshed on change. Edge cases around emoji, unicode normalization, short queries.
- **Former milestone:** v1.4.1 (full spec archived)

## TaskPaper output format
- **What:** Alternative serialization for ~5x token reduction. Hierarchy via indentation, TaskPaper tag syntax for fields.
- **Why maybe:** Field selection + null-stripping (v1.4) solve ~80% of the token problem. TaskPaper's marginal benefit on top is ~1.5-2x, but adds: tree reconstruction from flat data, a whole parallel serialization format to maintain, and format duality where agents read TaskPaper but write JSON. The complexity-to-benefit ratio is poor.
- **Complexity:** Tree reconstruction, TaskPaper tag syntax, interaction with field selection, server-wide vs per-tool config.
- **Former milestone:** v1.4.2 (full spec archived)

## Mutually exclusive tag enforcement
- **What:** Validate or warn when agents assign multiple mutually exclusive sibling tags to a task
- **Why maybe:** OmniFocus only enforces tag exclusivity at the UI level. Agents can create invalid states via API, but OmniFocus self-corrects when user later touches the tag group in UI. Low severity.
- **Complexity:** Need to determine if tag exclusivity metadata is accessible via OmniJS or SQLite. Decide validate-before-write vs warn-after.
- **Former milestone:** v1.4.3 stretch goal

## MCP Resources
- **What:** Expose server configuration (due-soon threshold, repository type, SQLite path, server status) as MCP Resources instead of baking into tool responses
- **Why maybe:** Looked into the MCP Resources spec — it's a bit niche. Unclear if the value justifies the implementation effort. Resources are better suited for larger, more complex servers.
- **Complexity:** Low implementation effort, but unclear demand.
