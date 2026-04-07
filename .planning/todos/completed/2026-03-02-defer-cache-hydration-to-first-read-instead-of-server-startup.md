---
created: 2026-03-02T14:58:08.899Z
title: Defer cache hydration to first read instead of server startup
area: api
files:
  - src/omnifocus_operator/repository/_repository.py
---

## Problem

The MCP server currently preloads the OmniFocus cache on startup. This made sense when assuming a long-lived server serving many requests, but in practice, a **new server instance is spawned per Claude Code session**. This means:

- Every time a user starts a Claude Code session, OmniFocus freezes for ~1-3 seconds while the full database is loaded via JXA
- This happens even if the user never interacts with OmniFocus tasks in that session
- The freeze is acceptable during an explicit read (user is interacting), but unacceptable as a startup side-effect

## Solution

Change cache hydration strategy from **eager (on server start)** to **lazy (on first read)**:

- Remove any preload/hydration logic from server initialization
- Hydrate the snapshot cache on the first read operation instead
- Subsequent reads can use the cached snapshot (with existing TTL/freshness logic)
- This way, the OmniFocus freeze only occurs when the user actually needs task data
