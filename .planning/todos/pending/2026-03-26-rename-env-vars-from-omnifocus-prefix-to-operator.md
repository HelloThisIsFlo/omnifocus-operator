---
created: 2026-03-26T23:40:40.720Z
title: Rename env vars from OMNIFOCUS prefix to OPERATOR
area: server
files:
  - src/omnifocus_operator/__main__.py:21
  - src/omnifocus_operator/server.py:77
  - src/omnifocus_operator/repository/factory.py
  - src/omnifocus_operator/repository/hybrid.py:476
  - src/omnifocus_operator/bridge/real.py
---

## Problem

All environment variables use the `OMNIFOCUS_` prefix (e.g. `OMNIFOCUS_LOG_LEVEL`, `OMNIFOCUS_REPOSITORY`, `OMNIFOCUS_SQLITE_PATH`). The project is called "OmniFocus Operator" — the prefix should reflect the product name, not the backend it wraps.

Current env vars found in src/:
- `OMNIFOCUS_LOG_LEVEL` — log level
- `OMNIFOCUS_REPOSITORY` — repo type selection (hybrid/bridge-only)
- `OMNIFOCUS_SQLITE_PATH` — SQLite database path
- `OMNIFOCUS_IPC_DIR` — bridge IPC directory
- `OMNIFOCUS_BRIDGE_TIMEOUT` — bridge timeout seconds
- `OMNIFOCUS_OFOCUS_PATH` — .ofocus directory path

## Solution

Rename all to flat `OPERATOR_` prefix — no `OF_` infix needed since the server is inherently about OmniFocus:

| Current | New |
|---------|-----|
| `OMNIFOCUS_LOG_LEVEL` | `OPERATOR_LOG_LEVEL` |
| `OMNIFOCUS_REPOSITORY` | `OPERATOR_REPOSITORY` |
| `OMNIFOCUS_SQLITE_PATH` | `OPERATOR_SQLITE_PATH` |
| `OMNIFOCUS_IPC_DIR` | `OPERATOR_IPC_DIR` |
| `OMNIFOCUS_BRIDGE_TIMEOUT` | `OPERATOR_BRIDGE_TIMEOUT` |
| `OMNIFOCUS_OFOCUS_PATH` | `OPERATOR_OFOCUS_PATH` |

Also rename the `OMNIFOCUS_CONTAINER` constant if appropriate (though that's an internal constant, not an env var).

Touches: `__main__.py`, `server.py`, `repository/factory.py`, `repository/hybrid.py`, `bridge/real.py`, plus docs and CLAUDE.md.
