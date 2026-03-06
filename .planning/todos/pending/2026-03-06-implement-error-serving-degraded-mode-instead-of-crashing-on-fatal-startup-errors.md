---
created: 2026-03-06T18:22:21.118Z
title: Implement error-serving degraded mode instead of crashing on fatal startup errors
area: server
files:
  - src/omnifocus_operator/__main__.py
  - src/omnifocus_operator/server/_server.py
---

## Problem

### The general problem with MCP server crashes

Traditional servers fail fast on fatal errors (missing database, bad config, missing dependencies) by
crashing with a clear error. This works because:

- There's a terminal or deployment pipeline watching the output
- Logs are immediately visible
- A crash prevents a bad deployment from rolling out

MCP servers are different. They're spawned by agents/hosts (Claude Desktop, Claude Code, etc.), not by
users. When an MCP server crashes at startup:

- There's no terminal the user is watching
- Logs are buried and require enabling debug mode to find
- The failure is silent and mysterious — the user just sees "tool not available" or gets no response
- The agent can't tell the user what went wrong because it never got a chance to communicate

### The current workaround in this project

The project currently validates early in `__main__.py` (before entering the async MCP context) so that
fatal errors produce a clean crash with a printed error message. This was a workaround for a deeper
SDK issue: errors inside the MCP lifespan get wrapped in anyio's `ExceptionGroup` and cause the process
to hang (stdin reader thread can't be cancelled).

This workaround is fragile:
- Only covers errors we explicitly check for before `server.run()`
- Doesn't catch errors that happen during lifespan setup or first use
- Still results in a crash that's invisible to the user unless they're watching stderr

### What this todo replaces

This todo supersedes FOLLOW-UP-NOTES item "MCP SDK Async Error Handling Limitation" — that item
described the symptom (ExceptionGroup hangs), this todo addresses the root cause (crashes are the
wrong failure mode for MCP servers).

## Solution

### The pattern: Error-Serving Degraded Mode

Instead of crashing on fatal errors, start a **shell server** that has the exact same tool interface
but where every tool call returns the same clear, actionable error message.

**Key distinction:**
- **Transient errors** (bad arguments, temporary network issues, OmniFocus not responding) → normal
  error responses as today, nothing changes
- **Fatal errors** (anything that would crash a traditional server) → enter error-serving mode

### Why it works

- The agent is your real user in MCP — communicate failures *to the agent*
- Agent surfaces the error on its very first tool call — no mystery, no log diving
- User gets a clear, actionable message through the channel they're actually looking at: the agent's
  response
- Server is technically "healthy" from the host's perspective (no restart loops, no reconnection
  attempts)
- It's a conversational approach to error management — the agent tells you what's wrong and what to
  fix

### Implementation sketch

```python
# In __main__.py or server startup
try:
    # Normal server initialization (bridge creation, validation, etc.)
    server = create_server(bridge)
except Exception as e:
    # Fatal error — don't crash, enter degraded mode
    server = create_error_server(
        error=e,
        message=f"OmniFocus Operator failed to start: {e}. "
                f"The server is running in error mode — fix the issue and restart."
    )

server.run()
```

The `create_error_server()` would:
1. Register the same tool names as the real server (e.g., `list_all`)
2. Every tool handler returns the error message instead of real data
3. The server stays alive and responsive — just not functional

### Generic pattern — not project-specific

This should be implemented in a way that's reusable across MCP servers. The pattern is:

1. Wrap server initialization in a try/catch
2. On any fatal error, swap in an error-serving server with the same interface
3. The error-serving server is a thin shell — same tool names, every response is the error message

This is applicable to any MCP failure mode: missing dependencies, auth expired, service unavailable,
database moved, bad config, incompatible versions, etc. Don't crash, communicate.

### What to remove after implementing

- The early validation in `__main__.py` (the pre-async crash workaround) can be simplified or removed
  since fatal errors are now caught generically
- The lifespan error handling workaround becomes unnecessary

### Open questions

- Should the error message include instructions on how to check logs for the full traceback?
- Should the error-serving server also expose a `status` or `health` tool that returns the error?
- Should it attempt to re-initialize on each call (in case the issue was fixed), or stay in error
  mode until restart? (Probably stay in error mode — keep it simple, restart to fix.)
