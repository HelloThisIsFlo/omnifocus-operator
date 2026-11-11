---
created: 2026-11-11T19:39:51.104Z
title: Finish structured-content dedup middleware
area: server
severity: minor
files:
  - branch structured-content-dedup (commit 33fd5d2a)
  - src/omnifocus_operator/middleware.py
  - src/omnifocus_operator/server/__init__.py
  - tests/test_middleware.py
---

## Problem

FastMCP serializes every structured tool result twice: once in `structuredContent`, once as the same JSON in a text block. For large `list_tasks` responses that roughly doubles the payload the agent pays for.

`StructuredContentDeduplicationMiddleware` (written 2026-07-14, never released) strips the text copy when the client negotiates MCP protocol `2025-06-18` or newer; legacy clients, errors and human-written text are kept. It sat uncommitted on `main` until 2026-11-11, when it was parked on branch **`structured-content-dedup`** (local, not pushed) so the FastMCP pin could ship from a clean tree.

**Why it is not ready:**
- **Never verified against a real client.** It infers "client passes structured data to the model" from the protocol version. A client that negotiates the new version but only shows the model the text block would see **empty results, silently**. The MCP spec recommends keeping the text copy for compatibility.
- **Breaks on FastMCP 4 / MCP SDK 2:** reads `client_params.protocolVersion`, renamed to `protocol_version` → `AttributeError` on every tool call (97 test failures when tried on 4.1.8).
- Behaviour change → feature release, not a patch.

## Solution

- Hands-on check in Claude Desktop, Claude Code CLI and at least one other client: does the model still see results with the text block removed? (Human-run; real OmniFocus.)
- Consider an opt-in setting or an allow-list of verified clients instead of inferring from protocol version.
- Fix the `protocol_version` attribute as part of / after the FastMCP migration todo.
- Rebase the branch onto `main` once the migration lands; tests are on the branch (5 unit + 4 assertions in `test_server.py`).
