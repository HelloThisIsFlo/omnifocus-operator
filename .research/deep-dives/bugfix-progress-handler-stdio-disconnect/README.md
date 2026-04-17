# MCP progress-notification reproducer

Minimal FastMCP server that isolates the "unknown progressToken" / stdio disconnect bug in Claude Code CLI 2.1.105+.

## Verdict (2026-04-17)

**Root cause: Claude Code CLI treats any `notifications/progress` with an unknown `progressToken` as a fatal stdio transport error.** One strike kills the pipe. The rejected tokens are the client's own — it sends them in `_meta.progressToken` and refuses to recognise them coming back.

- `emit_only_final()` — **one** notification → transport torn down.
- Log trail matched upstream issue [#47765](https://github.com/anthropics/claude-code/issues/47765) bit-for-bit:
  ```
  STDIO connection dropped after 379s uptime
  Connection error: Received a progress notification for an unknown token: {"method":"notifications/progress","params":{"progress":1,"total":1,"progressToken":6}}
  Closing transport (stdio transport error: Error)
  Tool 'emit_only_final' completed successfully in 10ms
  ```
- Claude Code CLI reports the tool as `"completed successfully"` **even after tearing down the transport** — which is why the v1.4 UAT observation of "6 notifications accumulated before disconnect" was misread. The first progress emission almost certainly killed the transport; the failure only surfaced when a later call needed the dead pipe.

Upstream:
- [#47378](https://github.com/anthropics/claude-code/issues/47378) — open (broader "stdio kills stdin after successful tool response" framing)
- [#47765](https://github.com/anthropics/claude-code/issues/47765) — closed as dup of #47378 (specifically diagnoses the unknown-progressToken dispatch path, proposes client-side fix)

Response in the codebase: see `src/omnifocus_operator/config.py` — `PROGRESS_NOTIFICATIONS_ENABLED: bool = False` disables progress emission entirely until the upstream fix ships.

## Wire-path ground truth (verified from source)

- `Context.report_progress` echoes the client's token verbatim from `request_context.meta.progressToken` (`fastmcp/server/context.py:395`).
- `session.send_progress_notification` → `session.send_notification` → `self._write_stream.send(session_message)` (`mcp/shared/session.py:335`).
- Tool responses take the same path via `_send_response` → `self._write_stream.send(session_message)` (`mcp/shared/session.py:341/349`).
- `write_stream` is a single `anyio.create_memory_object_stream(0)` — zero-buffer, FIFO, one reader (`mcp/server/stdio.py:58`).
- Drained by one `stdout_writer` coroutine that writes `json + "\n"` then flushes (`mcp/server/stdio.py:75-81`).

So: notifications emitted before the response hit stdout before the response. No reordering possible at the server. Commit `307136e7`'s "final races response" theory is dead at the transport layer — the bug is purely on the client's dispatcher.

## Hypotheses this reproducer was built to distinguish

| Hypothesis | Predicted result | Actual |
|---|---|---|
| Client never registers progressTokens it sends (theory 1) | `emit_only_final` disconnects immediately | **Confirmed** |
| Bug only affects the final notification (race) | `emit_intermediates` fine at any n; `emit_with_final` triggers it | Not tested — theory 1 already won |
| Bug is timing-sensitive | `delay_ms=500` between emissions fixes it | Not tested — theory 1 already won |
| Batch-size threshold (307136e7's mitigation framing) | Scales with n in a non-linear way | Not tested — theory 1 already won |

Theory 1 wins absolutely. Every progress emission is a strike, regardless of count, timing, or batch size.

## How to re-run (for verifying an upstream fix)

The server is wired into Claude Code CLI via this project's `.mcp.json` — no manual config needed. After pulling a newer Claude Code CLI:

1. Restart the Claude Code session.
2. Call `echo()` — confirms baseline works.
3. Call `emit_only_final()`. If the transport survives **and** no `unknown progressToken` line appears in the MCP log, the client-side fix is in.

MCP log location:

```
~/Library/Caches/claude-cli-nodejs/<url-encoded-project-path>/mcp-logs-progress-repro/*.jsonl
```

If you need to run the server standalone (without Claude Code CLI wiring):

```sh
uv run python .research/deep-dives/bugfix-progress-handler-stdio-disconnect/server.py
```

## Full experiment sequence (only needed if re-investigating)

The definitive result was reached at step 2. If upstream behavior changes in a way that doesn't match theory 1, the remaining steps discriminate subtler models. Restart the client between runs for a clean session:

1. `echo()` — baseline.
2. `emit_only_final()` — one notification. If it disconnects, theory 1 is live.
3. `emit_intermediates(n=1)` — equivalent shape, different call path.
4. `emit_intermediates(n=3)` — matches the v1.4 UAT 3-item scenario.
5. `emit_intermediates(n=10)` — higher N for scaling checks.
6. `emit_with_final(n=3)` — tests 307136e7's specific theory.
7. `emit_intermediates(n=3, delay_ms=500)` — if timing matters, this should be fine.

Record: (a) did any notification get rejected in the log, (b) did the transport disconnect, (c) on which call in the session.
