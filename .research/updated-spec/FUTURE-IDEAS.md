# Future Ideas

Ideas worth pursuing eventually but not assigned to any milestone yet.

## Notifications / reminders
- **What:** Read/write task notifications (due-date alerts, custom reminders, timing configuration)
- **Why future:** Bridge already extracts notification data (BRIDGE-SPEC Section 7, deferred). Could enhance agent-created tasks by setting reminders. Low priority but clearly useful.

## MCP Resources
- **What:** Expose server configuration (due-soon threshold, repository type, SQLite path, server status) as MCP Resources instead of baking into tool responses
- **Why future:** Makes the server self-describing. Agents can discover capabilities and adapt. Needs investigation into MCP Resources spec first.
- **Note:** Flo wants to research this independently before committing.
