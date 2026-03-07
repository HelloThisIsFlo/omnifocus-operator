# Configuration

All configuration is via environment variables. Set them in your MCP client config (e.g., Claude Desktop's `.mcp.json`).

## Main Configuration

What you'd actually change.

### `OMNIFOCUS_REPOSITORY`

Which data access strategy to use for reads.

| Value | Description |
|-------|-------------|
| `sqlite` | **Default.** Direct SQLite cache read (~46ms). OmniFocus does not need to be running. Full availability model including `blocked` status. |
| `bridge` | Fallback. Uses OmniJS bridge via IPC. Slower (~2-5s) and degraded: `availability` is reduced to `available`/`completed`/`dropped` (no `blocked` — OmniJS doesn't expose sequential/dependency information). |

Use `bridge` as a temporary workaround when the SQLite cache path changes after an OmniFocus update, or when a new OmniFocus version breaks the cache format. Switch back to `sqlite` once you've set the correct path via `OMNIFOCUS_SQLITE_PATH`.

### `OMNIFOCUS_LOG_LEVEL`

Standard Python log levels. **Default:** `INFO`.

Set to `DEBUG` for verbose output (bridge calls, IPC timing, cache hits).

## Rarely Changed

You'd almost never touch these. They exist for non-standard setups and debugging.

### `OMNIFOCUS_OFOCUS_PATH`

Path to the OmniFocus `.ofocus` database directory. Auto-detected from the default OmniFocus location. Only set this if your OmniFocus data lives somewhere unusual (e.g., synced to a custom location).

**Default:** `~/Library/Group Containers/34YW5A73Q8.com.omnigroup.OmniFocus/com.omnigroup.OmniFocus/OmniFocus.ofocus`

### `OMNIFOCUS_SQLITE_PATH`

Path to the OmniFocus SQLite cache database file. Auto-detected from the default location. Only set this if auto-detection fails (e.g., after an OmniFocus update changes the cache path).

**Default:** `~/Library/Group Containers/34YW5A73Q8.com.omnigroup.OmniFocus/com.omnigroup.OmniFocus/OmniFocus.ofocus/OmniFocusDatabase.db`

### `OMNIFOCUS_BRIDGE`

Which bridge implementation to use. Only relevant when `OMNIFOCUS_REPOSITORY=bridge`.

| Value | Description |
|-------|-------------|
| `real` | **Default.** Communicates with OmniFocus via file-based IPC and URL scheme. |
| `inmemory` | Test double. Returns seed data from memory. |
| `simulator` | Test double. Runs a mock OmniFocus simulator subprocess. |

`inmemory` and `simulator` are for development/testing only.

### `OMNIFOCUS_IPC_DIR`

Directory for bridge IPC files. Only relevant when using the bridge.

**Default:** System temp directory (`/tmp` on macOS).

### `OMNIFOCUS_BRIDGE_TIMEOUT`

Timeout in seconds for bridge calls. Increase if OmniFocus is slow to respond (large databases, App Nap).

**Default:** `10`
