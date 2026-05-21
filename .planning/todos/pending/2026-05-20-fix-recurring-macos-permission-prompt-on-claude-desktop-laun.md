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

**In progress (4 background research agents, 2026-05-21):** minimal-setup path for a durable FDA grant — (1) unsigned/stable-path viability, (2) lightest Python→signable-binary, (3) `.mcpb` extension bundling a signed binary (double-click), (4) distribution decision matrix. Synthesis → deep dive.

**Open risks (note, don't block):** app may need to live in `/Applications`; hardened-runtime entitlements when spawning uv/python (likely fine); `uvx` caching means the launcher must use `@latest`/`--refresh` to guarantee freshness; the OmniFocus "Run Script" first-run prompt is a separate mechanism not addressed here.

**Full deep dive (canonical record):** `.research/deep-dives/macos-tcc-permission-persistence/` — `README.md` (verdict + tables + how-to-rerun), `FINDINGS.md` (daemon-log proof, TCC.db evidence, route research, sources), and the runnable rig (`rig/identity-test/`, `rig/attribution-test/`).

**Also:** step-by-step validation guide at Obsidian `_AgentSandbox_/tcc-validation/GUIDE.md` (with filled observations).
