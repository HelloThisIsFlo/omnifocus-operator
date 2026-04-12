# Configuration

All configuration is via environment variables. Set them in your MCP client config (e.g., Claude Desktop's `.mcp.json`).

## Main Configuration

What you'd actually change.

### `OPERATOR_REPOSITORY`

Which data access strategy to use for reads.

| Value | Description |
|-------|-------------|
| `hybrid` | **Default.** SQLite cache reads + bridge writes (~46ms reads). OmniFocus does not need to be running for reads. Full availability model including `blocked` status. |
| `bridge-only` | Fallback. Uses OmniJS bridge for everything via IPC. Slower (~2-5s) and degraded: `availability` is reduced to `available`/`completed`/`dropped` (no `blocked` — OmniJS doesn't expose sequential/dependency information). |

Use `bridge-only` as a temporary workaround when the SQLite cache path changes after an OmniFocus update, or when a new OmniFocus version breaks the cache format. Switch back to `hybrid` once you've set the correct path via `OPERATOR_SQLITE_PATH`.

### `OPERATOR_LOG_LEVEL`

Standard Python log levels. **Default:** `INFO`.

Set to `DEBUG` for verbose output (bridge calls, IPC timing, cache hits).

## Rarely Changed

You'd almost never touch these. They exist for non-standard setups and debugging.

### `OPERATOR_OFOCUS_PATH`

Path to the OmniFocus `.ofocus` database directory. Auto-detected from the default OmniFocus location. Only set this if your OmniFocus data lives somewhere unusual (e.g., synced to a custom location).

**Default:** `~/Library/Containers/com.omnigroup.OmniFocus4/Data/Library/Application Support/OmniFocus/OmniFocus.ofocus`

### `OPERATOR_SQLITE_PATH`

Path to the OmniFocus SQLite cache database file. Auto-detected from the default location. Only set this if auto-detection fails (e.g., after an OmniFocus update changes the cache path).

**Default:** `~/Library/Group Containers/34YW5XSRB7.com.omnigroup.OmniFocus/com.omnigroup.OmniFocus4/com.omnigroup.OmniFocusModel/OmniFocusDatabase.db`

### `OPERATOR_WEEK_START`

Which day starts the week for `{this: "w"}` date filter alignment.

| Value | Description |
|-------|-------------|
| `monday` | **Default.** ISO 8601 standard. |
| `sunday` | US convention. |

### `OPERATOR_IPC_DIR`

Directory for bridge IPC files. Only relevant when using the bridge.

**Default:** System temp directory (`/tmp` on macOS).

### `OPERATOR_BRIDGE_TIMEOUT`

Timeout in seconds for bridge calls.

**Default:** `30`

**Why 30s?** macOS App Nap throttles OmniFocus CPU scheduling when it's backgrounded. Lightweight operations (e.g., adding a task) complete quickly even when napped, but heavy reads (`get_all`) can take 10-20s under throttling. The previous 10s default caused spurious timeouts. 30s accommodates App Nap degradation while still failing fast on genuine hangs (OmniFocus not running, bridge crash). In hybrid mode, reads bypass the bridge entirely (SQLite), so App Nap mainly affects writes and bridge-only configurations.
