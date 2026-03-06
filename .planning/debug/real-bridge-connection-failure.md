---
status: resolved
trigger: "The real bridge (RealBridge) to OmniFocus hangs at 'IPC sweep complete, prewarming repository cache' — never reaches OmniFocus."
created: 2026-03-06T00:00:00Z
updated: 2026-03-06T11:35:00Z
---

## Current Focus

hypothesis: CONFIRMED — the .ofocus path was wrong. Server used Group Containers path which doesn't contain the database file. FileNotFoundError during mtime check caused an ExceptionGroup swallowed by MCP SDK, appearing as a hang.
test: Fix applied — correct path, early validation, exception logging.
expecting: MCP server starts, finds .ofocus, pre-warms cache, connects to OmniFocus.
next_action: User to re-run OMNIFOCUS_BRIDGE=real to verify fix.

## Symptoms

expected: OmniFocus should prompt to accept the automation script (first time), then return the database snapshot JSON. On subsequent runs, no prompt — just returns the snapshot.
actual: Process starts, prints "IPC sweep complete, prewarming repository cache", then hangs indefinitely. Nothing happens on the OmniFocus side — no prompt to accept the script.
errors: Stack trace reveals FileNotFoundError for wrong .ofocus path, swallowed by anyio ExceptionGroup.
reproduction: Run the real bridge via MCP server (OMNIFOCUS_BRIDGE=real).
started: Pre-existing bug since Phase 08 — MCP server with real bridge was never tested until Phase 8.2 UAT.

## Eliminated

- hypothesis: Phase 8.2 broke bridge.js or real bridge Python code
  evidence: UAT test passes. bridge.js and _real.py were NOT changed in Phase 8.2 (git diff confirms).
  timestamp: 2026-03-06T00:01:30Z

- hypothesis: subprocess.run blocks with large URL
  evidence: Tested open -g with full 18839-byte bridge.js URL from command line -- returns in 73ms with exit code 0.
  timestamp: 2026-03-06T00:01:40Z

- hypothesis: OmniFocus doesn't respond from MCP client context
  evidence: Stack trace shows server never reaches the bridge — crashes during mtime check before any OmniFocus interaction.
  timestamp: 2026-03-06T11:30:00Z

## Evidence

- timestamp: 2026-03-06T11:20:00Z
  checked: User ran OMNIFOCUS_BRIDGE=real uv run python -m omnifocus_operator from terminal
  found: Hangs at "Pre-warming repository cache...", triple Ctrl+C reveals FileNotFoundError for /Users/flo/Library/Group Containers/34YW5A73WQ.com.omnigroup.OmniFocus/com.omnigroup.OmniFocus4/OmniFocus.ofocus
  implication: The .ofocus path in _server.py is wrong — points to Group Containers instead of Containers.

- timestamp: 2026-03-06T11:25:00Z
  checked: Filesystem search for actual OmniFocus.ofocus location
  found: ~/Library/Containers/com.omnigroup.OmniFocus4/Data/Library/Application Support/OmniFocus/OmniFocus.ofocus
  implication: Same container root as IPC dir, different subdirectory.

- timestamp: 2026-03-06T11:28:00Z
  checked: Previous debug session ipc-json-parse-error.md
  found: IPC path was already corrected from Group Containers to Containers. But .ofocus path was never updated — it still used the old Group Containers path from Phase 06 research.
  implication: Research assumed Group Containers held both IPC and .ofocus. Only IPC path was fixed when sandbox issues were discovered.

## Resolution

root_cause: The .ofocus database path in _server.py was wrong. It pointed to ~/Library/Group Containers/34YW5A73WQ.com.omnigroup.OmniFocus/com.omnigroup.OmniFocus4/OmniFocus.ofocus (from Phase 06 research) instead of the correct ~/Library/Containers/com.omnigroup.OmniFocus4/Data/Library/Application Support/OmniFocus/OmniFocus.ofocus. The FileNotFoundError during mtime check was swallowed by anyio's ExceptionGroup in the MCP stdio transport, making it appear as a hang. The error only became visible after triple Ctrl+C forced the process to dump the exception stack.
fix: (1) Extracted OMNIFOCUS_CONTAINER as shared root in _real.py, derived both DEFAULT_IPC_DIR and DEFAULT_OFOCUS_PATH from it. (2) Fixed _server.py to import DEFAULT_OFOCUS_PATH instead of hardcoding wrong path. (3) Added early validation — clear error message if .ofocus file not found. (4) Wrapped repository.initialize() in try/except for clean error logging before MCP SDK's exception handling obscures it.
verification: 177 Python tests pass, 26 JS bridge tests pass. Awaiting user re-test with OMNIFOCUS_BRIDGE=real.
files_changed:
  - src/omnifocus_operator/bridge/_real.py
  - src/omnifocus_operator/bridge/__init__.py
  - src/omnifocus_operator/server/_server.py
