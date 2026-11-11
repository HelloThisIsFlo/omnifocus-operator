---
created: 2026-05-20T18:04:28.908Z
title: Fix recurring macOS permission prompt on Claude Desktop launch
area: tooling
files:
  - .research/deep-dives/macos-tcc-permission-persistence/ (full deep dive + rig)
  - GitHub issue #2
---

## Problem

On macOS, the prompt **`"uvx" would like to access data from other apps`** reappears on **every** Claude Desktop launch. Clicking Allow never persists. Tracked publicly as issue #2.

**Root cause (PROVEN — via tccd log + TCC.db inspection, macOS 26):**
- The `uvx → uv → python` launch chain is ad-hoc / self-signed — no trusted (Apple-anchored) code identity.
- macOS *does* record the Allow (a TCC.db row is written) but parks it in a **non-honored state (`auth_value=5`)**. Next run, `tccd` treats it as `Unknown` → re-prompts. Forever.

**Disproven (ruled out):**
- Claude Desktop's `disclaimer` helper does NOT break attribution — our app is correctly its own responsible process.
- Full Disk Access on **Claude.app** does NOT fix it (attribution lands below Claude). *(But FDA on the server's own signed binary DOES — see Solution.)*
- A self-signed identity is NOT enough — stable but untrusted, so the grant isn't honored.

**Decided separately:** the dialog NAME is fixable on its own — a `.app` bundle with `CFBundleDisplayName` made the prompt read "OmniFocus Operator" even while unsigned (no Apple account needed).

## Solution

**✅ SOLVED (2026-05-20):** ship a **Developer-ID-signed app** + have the user grant it **Full Disk Access** once → prompt gone, and it **survives updates** (grant keyed to Team ID — proven by rebuild). FDA's `AllFiles` preflight passes *before* the AppData path, so the prompt never fires. Key surprise: `SystemPolicyAppData` itself **never persists** (`auth_value=5`) regardless of signing — **FDA is the lever; the cert just makes the FDA grant durable.**

**Validation gates (all run on the rig):**
1. ✅ **Gate 1 — attribution.** Launcher spawns a child (`of-reader`) that reads OmniFocus; tccd set `responsible = launcher`, prompt named "OmniFocus Operator". Architecture sound.
2. ❌ **Gate 2 — does Developer ID make AppData persist? NO.** Re-signed with a real Developer ID (Team `7T6UW39FB3`) → still `auth_value=5`, still re-prompts.
3. ✅ **Fix + Gate 3 — FDA + durability.** Grant FDA to the signed `.app` → silent. Rebuild (new cdhash, same Dev ID), no re-grant → still silent → survives updates.

**Decisions (2026-05-21):**
- Dropping the SQLite cache is OFF the table → the real choice is **prompt-every-time** vs **Full Disk Access**.
- **Notarized + /Applications tested → does NOT make AppData persist** (still `5`). Notarization is only for Gatekeeper/distribution.
- **Durable FDA requires a Developer-ID-SIGNED launcher; notarization NOT needed for persistence** (proven on signed-not-notarized). Unsigned FDA = path-based, breaks on updates.
- 🥇 **Cheap win to do first (Q2 lazy defer):** move `sweep_orphaned_files(DEFAULT_IPC_DIR)` out of eager startup (`server/lifespan.py:36`) → first tool call. SQLite reads are already lazy. Moves prompt from "every Claude launch" to "first OmniFocus tool use". (Not yet implemented.)

**Distribution research DONE (4 agents, 2026-05-21) → full matrix + sources in deep-dive FINDINGS.** Conclusions:
- Durable FDA requires a Developer-ID-signed launcher; "one config edit + durable FDA" is impossible (needs a signed download). Notarization mandatory for any download (Gatekeeper).
- Ship a signed **`.app`** (proven to survive rebuild), not a bare CLI binary (FDA-fragile). Lightest build = **PyApp** (signed launcher, uv-bootstraps server from PyPI → keeps auto-update).
- **Recommended two-tier:** (1) NOW free — keep `uvx` + Q2 lazy-defer (prompt → first OF use); (2) durable opt-out — signed+notarized `.app` via `.mcpb` double-click using the **split-identity pattern** (signed `.app` in /Applications + thin `.mcpb` wrapper); Homebrew cask = fallback.
- **Next spike before any pipeline:** FDA on signed `.app` that *spawns* the python child → child read silent + survives rebuild (combines proven Gate 1 + Gate 3).

**Open risks (note, don't block):** app may need to live in `/Applications`; hardened-runtime entitlements when spawning uv/python (likely fine); `uvx` caching means the launcher must use `@latest`/`--refresh` to guarantee freshness; the OmniFocus "Run Script" first-run prompt is a separate mechanism not addressed here.

**Full deep dive (canonical record):** `.research/deep-dives/macos-tcc-permission-persistence/` — `README.md` (verdict + tables + how-to-rerun), `FINDINGS.md` (daemon-log proof, TCC.db evidence, route research, sources), and the runnable rig (`rig/identity-test/`, `rig/attribution-test/`).

**Also:** step-by-step validation guide at Obsidian `_AgentSandbox_/tcc-validation/GUIDE.md` (with filled observations).

## Update 2026-11-10 — macOS 27 changes the picture

**Observed on macOS 27.2.1, Claude Desktop, uv 0.13.7, operator v1.4.4:**
- **No prompt appears any more.** The read is denied silently: `(Sandbox) System Policy: python3.14 deny(1) file-read-data …/omnifocus-operator/ipc` in the system log.
- **The server now crashes at boot** — the eager `sweep_orphaned_files(DEFAULT_IPC_DIR)` (`server/lifespan.py:36`) raises `PermissionError: [Errno 1]`, Desktop reports "Couldn't start … Connection closed", tools never register. On macOS 26 the same line only caused the recurring prompt.
- `tccutil reset SystemPolicyAppData` — targeted at `com.anthropic.claudefordesktop`, `sh.astral.uvx`, or the uvx path — did **not** bring the prompt back. (Category-wide reset untested.)
- **Fix that worked:** Full Disk Access granted to the real `uvx` binary (`~/.local/share/mise/installs/uv/0.13.7/uv-aarch64-apple-darwin/uvx`). FDA on Claude.app does nothing (still true — `disclaimer` makes `uvx` the responsible process).
- Claude Code CLI sessions are unaffected (no `disclaimer`; they inherit the terminal's grants).

**New fact vs May:** `uvx` is now **Developer-ID signed by Astral** (`Identifier=sh.astral.uvx`, Team `2DC432GLL2`); it was ad-hoc in uv 0.11.3. An FDA grant on `uvx` may therefore be durable across uv upgrades. **Unverified** — check after the next uv bump (mise installs each version in a new folder; bare CLI binaries were flagged FDA-fragile in FINDINGS).

**Direction confirmed with Flo (2026-11-10):** FDA-for-`uvx` is too broad to ask of users (every `uvx`-launched tool gets the whole disk) → the signed `.app` launcher (Tier 2) stays the goal. Sequence:
1. Lazy-defer the sweep + teaching error on `PermissionError` (name the resolved `uvx` path and the FDA steps). Now a crash fix, not just a UX win. Quick-task sized.
2. Spike: signed `.app` that spawns the python child, FDA granted — **rerun on macOS 27**, all May evidence is macOS 26.
3. Launcher + signing/notarization pipeline + delivery (`.mcpb` / Homebrew) as its own milestone.
4. Install guide rewrite (separate todo: website guide).

**Interim user guidance:** README → "Claude Desktop on recent macOS: Full Disk Access" (temporary section).

