---
created: 2026-05-20T18:04:28.908Z
title: Fix recurring macOS permission prompt on Claude Desktop launch
area: tooling
files:
  - scratch/tcc-validation/ (test scaffolding, gitignored)
  - GitHub issue #2
---

## Problem

On macOS, the prompt **`"uvx" would like to access data from other apps`** reappears on **every** Claude Desktop launch. Clicking Allow never persists. Tracked publicly as issue #2.

**Root cause (PROVEN — via tccd log + TCC.db inspection, macOS 26):**
- The `uvx → uv → python` launch chain is ad-hoc / self-signed — no trusted (Apple-anchored) code identity.
- macOS *does* record the Allow (a TCC.db row is written) but parks it in a **non-honored state (`auth_value=5`)**. Next run, `tccd` treats it as `Unknown` → re-prompts. Forever.

**Disproven (ruled out):**
- Claude Desktop's `disclaimer` helper does NOT break attribution — our app is correctly its own responsible process.
- Full Disk Access does NOT fix it (different TCC service: `AllFiles` ≠ `AppData`).
- A self-signed identity is NOT enough — stable but untrusted, so the grant isn't honored.

**Decided separately:** the dialog NAME is fixable on its own — a `.app` bundle with `CFBundleDisplayName` made the prompt read "OmniFocus Operator" even while unsigned (no Apple account needed).

## Solution

**Leading candidate (NOT yet committed):** a Developer-ID-signed + notarized launcher as the MCP config `command`, bundling `uv` and still fetching the server from PyPI at runtime (preserves the CI→PyPI auto-update flow). Distribution method undecided (Homebrew Cask / Sparkle DMG / Claude Desktop `.mcpb` extension).

**DECIDED next action — two cheap validation gates BEFORE building any signing/notarization/distribution pipeline** (explicit goal: do not spend a day on a pipeline that might not work):

1. **Free, now:** modify the test so the launcher *spawns a child* that reads OmniFocus's container (mimics launcher → uv → python) and confirm the prompt still attributes to the launcher's identity, not the child. *(Validates the attribution architecture — currently only inferred.)*
2. **After buying an Apple Developer ID cert (~£99/yr):** re-sign the existing throwaway test app with it, confirm the grant now persists (`auth_value=2`, no re-prompt across runs). *(Validates the core bet — currently only inferred from the Bartender control.)*

**Open risks (note, don't block):** app may need to live in `/Applications`; hardened-runtime entitlements when spawning uv/python (likely fine); `uvx` caching means the launcher must use `@latest`/`--refresh` to guarantee freshness; the OmniFocus "Run Script" first-run prompt is a separate mechanism not addressed here.

**Artifacts:** validation guide at Obsidian `_AgentSandbox_/tcc-validation/GUIDE.md`; test scaffolding (`trigger.c`, `build.sh`, `Info.plist`, built `.app`) in repo `scratch/tcc-validation/` (gitignored).
