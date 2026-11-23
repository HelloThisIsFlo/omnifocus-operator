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

## Update 2026-11-23 — what Apple documents for macOS 27, and the `.mcpb` bug

Both quotes are verbatim from Apple's [macOS 27 release notes](https://developer.apple.com/documentation/macos-release-notes/macos-27-release-notes), read on 2026-11-23.

**1. The prompt is gone by design** (section "System Integrity Protection", New Features):

> Accessing files in other developer teams’ app data containers and app group containers no longer prompts the user for authorization; such accesses are denied by default and can be managed by the user in Privacy & Security settings. (161835690)

- Explains the silent denial seen on 27.2.1. No `tccutil reset` brings the prompt back.
- Applies to every app, signed or not: the spike no longer needs to ask "does a real app get a prompt?".

**2. A grant narrower than Full Disk Access exists, but not for a bare binary** (section "Privacy & Security Settings", Known Issues):

> In the Files & Folders pane, a process without a bundle ID cannot be granted access to specific app data containers or app group containers owned by other developer teams. (184660124)
>
> Workaround: Consider if the access is necessary. If required, grant Full Disk Access to the process for the duration of the requirement.

- `uvx` has no bundle ID, so Full Disk Access on `uvx` is Apple's documented workaround, not a quirk of this machine.
- A signed `.app` has a bundle ID. It may only need a Files & Folders grant for OmniFocus's containers. **Untested**: the pane has not been looked at, and nothing has been tried through Claude Desktop's `disclaimer` chain.
- New spike question: with no Full Disk Access, does that grant alone make the read work? How does the app get listed, and does one grant cover both the database folder (group container) and the IPC folder (app container)?

**3. A binary packed inside a `.mcpb` cannot start on macOS** ([modelcontextprotocol/mcpb#294](https://github.com/modelcontextprotocol/mcpb/issues/294), open since 2026-07-16):

- Claude Desktop extracts every file of an extension at mode `0600`, so a `type: "binary"` server fails with `Permission denied` on every launch. Reported with a signed, notarized app (Fantastical).
- Consequence for delivery: the signed `.app` lives in `/Applications`. A `.mcpb` can at most be a thin wrapper that starts it; it cannot contain it.

**4. The Full Disk Access grant on `uvx` does not survive a uv update** (settles the "Unverified" line in the 2026-11-10 update):

- mise moved uv from `0.13.7` to `0.13.9` on 2026-11-19, each version in its own folder (`~/.local/share/mise/installs/uv/<version>/…/uvx`); the `0.13.7` folder is gone. Flo had to add the new binary to Full Disk Access again.
- The signature was not the problem: `uvx` 0.13.9 is Developer-ID signed (`Identifier=sh.astral.uvx`, Team `2DC432GLL2`, designated requirement on identifier + Team ID).
- `codesign` reports `Info.plist=not bound`: no bundle ID, so the grant is filed under the binary's path, and the path changes with every version.

**5. macOS 27.3 changes the Full Disk Access flow** ([27.3 beta 2 release notes](https://developer.apple.com/documentation/macos-release-notes/macos-27_3-release-notes), section "Privacy & Security", read on 2026-11-23; beta, may still change):

> Guidance to encourage users to grant access to just the specific apps (for System & App Protection Override) or folders (for Full Disk Access) that are required for their workflows

> All app permissions previously granted by users will remain in effect.

- Also listed: granting by "selecting the requesting app from a list", and an option to make an app "ask every time".
- Apple tells developers to "be prepared to adjust how you onboard users". Any install guide or setup screen written before 27.3 ships will need a second pass.
- Unknown: whether the folder choice accepts another vendor's container folders.
