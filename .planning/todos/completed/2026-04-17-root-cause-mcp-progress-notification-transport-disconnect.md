---
created: 2026-04-17T19:00:00Z
updated: 2026-04-17T21:00:00Z
title: Track upstream Claude Code CLI fix for MCP progress-notification stdio teardown
area: server
files:
  - src/omnifocus_operator/config.py
  - src/omnifocus_operator/server/handlers.py
  - tests/test_server.py
---

## Status: DONE (2026-04-17) — server-side disposition shipped; upstream tracked elsewhere

Root-caused. 307136e7 mitigation removed. Progress notifications disabled via feature flag pending upstream Claude Code CLI fix. Tracking the upstream issue is handled via `.planning/STATE.md` (blockers section) and the re-enable procedure in `src/omnifocus_operator/config.py` — no further action needed on this todo.

## Resolution in the code

- Removed the 307136e7 mitigation (threshold + drop-final).
- Added a single feature flag `PROGRESS_NOTIFICATIONS_ENABLED: bool = False` in `config.py` (one comment block there explains the whole story, including upstream issue links).
- `add_tasks` / `edit_tasks` in `server/handlers.py` now wrap `ctx.report_progress` in a single `if PROGRESS_NOTIFICATIONS_ENABLED` — no other comments, no threshold, no "drop final" special case.
- Test class renamed to `TestProgressNotificationsDisabled` with an assertion that the flag is `False` and that `add_tasks` / `edit_tasks` emit zero progress events at any batch size.

## Root cause (verified, not hypothesized)

Claude Code CLI 2.1.105+ treats any `notifications/progress` with a `progressToken` it considers unknown as a fatal stdio transport error. One strike kills the pipe; every subsequent tool call in the session returns `-32000 Connection closed`.

The rejected tokens are **the client's own** — it sends them in `_meta.progressToken` and then refuses to recognise them when the server echoes them back. Whether the client never registers a callback for tokens it sends, or reaps them on response receipt before the notification dispatcher runs, the observable behavior is the same: any progress emission is a strike.

## Evidence

Empirical verification via `.research/deep-dives/bugfix-progress-handler-stdio-disconnect/`:
- Minimal FastMCP server with four tools (`echo`, `emit_only_final`, `emit_intermediates`, `emit_with_final`).
- `echo()` — clean, 40ms.
- `emit_only_final()` — **one** notification, zero intermediates → transport torn down. Log trail matched upstream issue #47765 bit-for-bit: `STDIO connection dropped` → `Connection error: Received a progress notification for an unknown token: {...progressToken:6}` → `Closing transport (stdio transport error: Error)` → `Tool 'emit_only_final' completed successfully in 10ms`.
- Experiment halted at call 2 — verdict was already definitive.

The "6 notifications accumulated before disconnect" framing from the original v1.4 UAT was misread. The transport almost certainly died on the first progress emission of the first `add_tasks` batch; the failure only surfaced on a later call because Claude Code CLI logs the tool as `"completed successfully"` even after tearing down the transport.

## Upstream

- https://github.com/anthropics/claude-code/issues/47378 — **open**. Broader framing ("stdio kills stdin after successful tool response"). Matches our symptom.
- https://github.com/anthropics/claude-code/issues/47765 — **closed as duplicate of #47378**. Diagnoses the specific mechanism (unknown-progressToken treated as transport error) and proposes the client-side fix.

The dup classification is plausibly wrong (47378 reporters see it without emitting progress at all, so there are likely two independent stdio-teardown bugs lumped together), but for our purposes both lead back to the same upstream repo.

## Re-enable procedure (for when upstream fix ships)

Kept here as a breadcrumb, even though this todo is done. Canonical copy lives in `src/omnifocus_operator/config.py`.

1. Pull the latest Claude Code CLI.
2. Set `PROGRESS_NOTIFICATIONS_ENABLED = True` in `config.py`.
3. Run the reproducer (`.research/deep-dives/bugfix-progress-handler-stdio-disconnect/`) against the updated client — `emit_only_final()` should succeed, transport should stay alive, no `unknown progressToken` log line.
4. If clean, run UAT against the real `add_tasks` / `edit_tasks` tools with 3+ item batches to confirm end-to-end.
5. Delete the flag, the `if PROGRESS_NOTIFICATIONS_ENABLED` conditionals in `handlers.py`, the `TestProgressNotificationsDisabled` class in `tests/test_server.py`, and the reproducer directory.

## Related

- Commit `307136e7` (2026-04-17) — introduced the now-removed mitigation.
- `.planning/milestones/v1.4-MILESTONE-AUDIT.md` §"Server — MCP transport" — contains the post-audit resolution note.
- `.research/deep-dives/bugfix-progress-handler-stdio-disconnect/` — reproducer + wire-path analysis + findings.
- Feedback memory `feedback_dont-hand-wave-bug-fixes.md` — codifies "never propose threshold tweaks as a fix for an unverified bug." The 307136e7 mitigation was the exact shape this rule exists to catch; we've now replaced it with an evidence-backed disablement.

## Housekeeping (from original UAT)

- UAT leftovers in OmniFocus Inbox: `fnewwdAo9I9` ("UAT test 1 (renamed during UAT)"), `nCjv9QuG4mR` ("UAT test 2 (stripping audit 2026-04-17)"). Safe to drop/delete manually.
