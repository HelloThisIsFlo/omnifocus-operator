---
created: 2026-11-11T20:18:23.267Z
title: Defer OmniFocus folder access to first tool call
area: server
severity: major
files:
  - src/omnifocus_operator/server/lifespan.py
  - src/omnifocus_operator/bridge/real.py (mkdir in __init__, sweep_orphaned_files)
  - src/omnifocus_operator/repository/factory.py (os.path.exists check)
  - src/omnifocus_operator/repository/hybrid/hybrid.py (~10 sqlite3.connect sites)
  - .planning/todos/pending/2026-05-20-fix-recurring-macos-permission-prompt-on-claude-desktop-laun.md
---

## Problem

Three things touch OmniFocus's protected folders **at server startup**: the orphan sweep, the IPC folder `mkdir` when the bridge is created, and the database existence check in the repository factory. (The May research said the sweep was the only one; that was incomplete.)

For users who refuse Full Disk Access and rely on macOS's "access data from other apps" prompt, this means a prompt at **every Claude launch**, even on days they never use OmniFocus, because macOS forgets that Allow when the process exits. Deferring all folder access to the first OmniFocus tool call would move the prompt to first actual use.

Quick task 261111-s5c ("version A") only makes startup failures land in error mode with a teaching message; it deliberately keeps the checks at startup. This todo is "version B", agreed with Flo on 2026-11-11 as the follow-up.

**Open fact that decides how much this is worth:** on macOS 27.2.1 no prompt appeared at all on Flo's machine (silent denial). If that is general macOS 27 behaviour, B only helps macOS 26 and older. Test: Full Disk Access off for `uvx`, `tccutil reset SystemPolicyAppData`, restart Claude Desktop, see whether the prompt returns.

## Solution

Roughly 3-4x the size of version A, and it needs a design decision, so not a blind quick task:

- Defer sweep, IPC `mkdir` and the database check until first use. Hybrid reads never call the bridge, so decide where the sweep runs (first bridge command is the natural place).
- Once startup no longer validates anything, a blocked read surfaces **per call**: as a `sqlite3` error at the ~10 connect sites in the hybrid repository, and as `PermissionError` in the bridge. Something must turn those into the teaching message on every call. Where that lives (repository helper, service, or middleware) is the design question; reuse the access-denied detection and message text from 261111-s5c.
- Side effect to accept or handle: a genuinely missing database is also reported at first use instead of at startup.
- Tests asserting "the sweep always runs in the lifespan" (`tests/test_server.py`, `tests/test_simulator_bridge.py`) must be rewritten around the new contract.
- Real-world check is human-only (real OmniFocus, Claude Desktop).
