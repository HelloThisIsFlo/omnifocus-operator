---
created: 2026-04-17T19:00:00Z
title: Root-cause MCP progress-notification transport disconnect
area: server
files:
  - src/omnifocus_operator/config.py
  - src/omnifocus_operator/server/handlers.py
  - tests/test_server.py
---

## Problem

**The bug:** When `add_tasks` / `edit_tasks` emit MCP progress notifications during a batch, Claude Code's MCP client rejects them with "unknown progressToken" — even though the client itself put that token in the request's `_meta.progressToken`. After N rejections, the client closes the stdio transport, breaking every subsequent tool call in the session.

**Reproduced during v1.4 milestone audit UAT (2026-04-17):**
- Called `add_tasks` with 3 items (at threshold → progress emitted)
- Called `edit_tasks` with 3 items (at threshold → progress emitted)
- Called `get_task` (no progress, succeeded)
- Attempted cleanup `edit_tasks` — transport disconnected, tool unavailable

6 intermediate progress notifications accumulated before the disconnect. This matches the commit `307136e7` repro note: "call 5 in TUI mode, call 12 in regular mode."

## Current State: Mitigation, Not Fix

Commit `307136e7` ("fix(server): threshold progress notifications + drop final to prevent stdio race") shipped **an empirical mitigation**:

1. **Removed** the post-loop `ctx.report_progress(progress=total, total=total)` unconditionally (biggest offender — always raced the response over stdio).
2. **Added** `PROGRESS_NOTIFICATION_MIN_BATCH_SIZE = 3` gate: skip progress entirely for small batches.

The config comment admits uncertainty:

> *"Precise client-side mechanism NOT verified. It could be that Claude Code doesn't register a callback for the tokens it sends, or that it cleans them up too eagerly relative to when notifications get dispatched. We can't tell from the outside without reading the client source. What we CAN verify: fewer emitted notifications → sessions stay alive longer."*

**This is mitigation dressed up as fix.** Any batch above the threshold still eats strikes against an unknown-capacity counter. The project's reliability posture (per PROJECT.md and README) does not tolerate knob-tweaked workarounds for unverified bugs.

## Not Acceptable

Raising `PROGRESS_NOTIFICATION_MIN_BATCH_SIZE` (e.g., 3 → 20) is **not a solution**. If you send 21 items, the bug returns. The threshold is a rain-check on fixing it, not a fix.

## What's Known From Server-Side Investigation (2026-04-17)

1. **Server echoes the token correctly.** FastMCP's `Context.report_progress` pulls from `self.request_context.meta.progressToken` verbatim — no transformation, no regeneration. The token on the wire IS the client's own token.
2. **`related_request_id` goes into transport metadata**, not the wire protocol. Likely ignored by stdio transport.
3. **Notifications are sent via `self._write_stream.send(session_message)`** — serialized in write order with the response. Over stdio the client should read progress-N before response.
4. **The client's rejection is observable** (MCP logs would show it, but Claude Code CLI doesn't persist MCP server logs like Claude Desktop does).

## What's Unknown (To Investigate)

1. **Why does Claude Code say "unknown progressToken"** when the server echoes the client's own token? Hypotheses:
   - Client GC: response handler fires first and reaps the token before the queued progress notification is dispatched (race on a single-threaded event loop with unfortunate ordering)
   - Token type mismatch: MCP spec allows progressToken as `string | int`; serialization somewhere converts between them
   - Client has an unrelated bug in its progress-notification path
2. **Does Claude Desktop have the same issue?** If only Claude Code CLI, the bug is client-specific.
3. **Does a newer Claude Code / FastMCP / MCP SDK version fix this?** (Current: FastMCP 3.1.1.)
4. **Is there a documented upstream issue?** Check:
   - github.com/modelcontextprotocol/python-sdk
   - github.com/jlowin/fastmcp
   - github.com/anthropics/claude-code (issues tracker — may or may not be public)

## Investigation Plan

**Do NOT ship code changes until root cause is verified.**

1. **Search upstream issue trackers** for `progressToken` / `unknown progressToken` / `stdio race` / `MCP progress notification` — FastMCP, MCP Python SDK, Claude Code issue trackers.
2. **Read the MCP spec on progressToken lifecycle** — is the client required to keep tokens valid for the duration of the request? Or allowed to GC on response? That alone determines whether server-side timing can ever be safe.
3. **Instrument the server** with timestamped stderr logs on every progress emission and every response return. Next disconnect → have the exact sequence captured.
4. **Try to reproduce under Claude Desktop** to isolate whether this is Claude Code CLI-specific.
5. **Write a minimal reproducer** (no OmniFocus bridge, just a FastMCP server with a loop emitting progress) — if it reproduces, the bug is clearly not OF-specific and can be reported upstream.

Only after the investigation completes, decide:
- **Fix upstream is available / required** → adopt, remove mitigation.
- **Bug is unresolvable server-side** → decide deliberately whether to emit progress at all. If no, remove the emission entirely; don't keep a threshold as "maybe safe."
- **Fix is in MCP spec / architecture** → wait, document the decision to wait, disable progress emission until then.

## Scope

- Investigation task, not a code-fix task.
- Scope is "understand the bug, then decide."
- Expected output of investigation: evidence document (what's happening on the wire, what the client does, upstream status) + recommendation grounded in that evidence.

## Related

- Commit `307136e7` (2026-04-17) — introduced current mitigation.
- `.planning/milestones/v1.4-MILESTONE-AUDIT.md` — v1.4 shipped with this bug unresolved; audit lists it as tech debt pointing at this todo.
- Feedback memory `feedback_dont-hand-wave-bug-fixes.md` — codifies "never propose threshold tweaks as a fix for an unverified bug."

## Context for Resuming

- Flo plans to pick this up in a fresh context window (post v1.4 audit closure).
- UAT task cleanup left two tasks in OmniFocus Inbox: `fnewwdAo9I9` ("UAT test 1 (renamed during UAT)"), `nCjv9QuG4mR` ("UAT test 2 (stripping audit 2026-04-17)"). Safe to drop/delete manually.
