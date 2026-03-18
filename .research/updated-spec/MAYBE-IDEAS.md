# Maybe Ideas

Ideas that might be worth exploring but need more thought before committing.

## Add task idempotency
- **What:** Detect duplicate `add_tasks` calls with identical arguments and prevent creating duplicate tasks
- **Why maybe:** Retrying `add_tasks` after a timeout creates duplicates (task may have been created but response was lost). `edit_tasks` is naturally idempotent. Could use a request hash or idempotency key to deduplicate.
- **Complexity:** Non-trivial — needs state tracking (recent request hashes) or bridge-level dedup. v1.6 mentions idempotency but doesn't detail this specific case.

## MCP Resources
- **What:** Expose server configuration (due-soon threshold, repository type, SQLite path, server status) as MCP Resources instead of baking into tool responses
- **Why maybe:** Looked into the MCP Resources spec — it's a bit niche. Unclear if the value justifies the implementation effort. Resources are better suited for larger, more complex servers.
- **Complexity:** Low implementation effort, but unclear demand.
