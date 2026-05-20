# macOS TCC Permission Persistence

Why the **`"uvx" would like to access data from other apps`** prompt recurs on **every** Claude Desktop launch — and what actually fixes it. Tracked as GitHub issue #2.

## Verdict (2026-05-20)

**Root cause: untrusted code identity.** The `uvx → uv → python` launch chain is ad-hoc / self-signed — no Apple-anchored identity. macOS *records* the user's "Allow" (a `TCC.db` row is written) but stores it in a **non-honored state (`auth_value=5`)**, so on the next launch `tccd` treats it as `Unknown` and re-prompts. Forever.

**Fix direction:** set Claude's config `command` to a **Developer-ID-signed launcher** (trusted identity → grant persists, even across updates, because TCC keys on the Team ID, not the file hash). Launcher bundles `uv` and still fetches the server from PyPI at runtime, so the existing CI→PyPI auto-update flow is preserved.

> **Status:** root cause + attribution proven. The signed-launcher fix is **validated up to Gate 1**; Gate 2 (does a real Developer ID persist?) is pending an Apple Developer cert. **Do not build the signing/notarization/distribution pipeline until Gate 2 passes.**

## What was proven vs ruled out

| Claim | Result | Evidence |
|---|---|---|
| The `disclaimer` helper breaks attribution | ❌ **Ruled out** | tccd sets `responsible = our app`; FDA-on-Claude failed because attribution is *below* Claude |
| Full Disk Access fixes it | ❌ **Ruled out** | Different TCC service (`AllFiles` ≠ `AppData`); confirmed by hand |
| Self-signed identity is enough | ❌ **Ruled out** | Grant written but `auth_value=5`, never honored; re-prompts |
| Trusting the self-signed cert helps | ❌ **Ruled out** | `tccd` runs as root, ignores the user-keychain trust override |
| **Trusted (Developer ID) identity required** | ✅ **Confirmed (indirect)** | Bartender (Developer-ID) persists in the same log; ours doesn't |
| Dialog name fixable via bundle alone | ✅ **Confirmed** | `.app` + `CFBundleDisplayName` → shows "OmniFocus Operator" even unsigned |
| **Gate 1:** child's read attributes to launcher | ✅ **Confirmed** | tccd: `responsible = launcher`, `subject = dev.kempenich.oftest`, when child `of-reader` reads |
| **Gate 2:** Developer ID actually persists | ⏳ **Pending** | needs the cert; re-sign rig + confirm `auth_value=2` |

## The fix, decoupled (why auto-update still works)

| Layer | What | Updates via | Re-prompts on update? |
|---|---|---|---|
| 🪪 Signed launcher (bundles `uv`) | stable trusted identity | Homebrew/Sparkle (rare) | ❌ no (same Team ID) |
| 🐍 Server (Python package) | the actual logic | **PyPI** (every release) | ❌ no (identity unchanged) |

Ruled out: **Mac App Store** (its sandbox forbids reading another app's container — the whole point).

## The rig

- `rig/identity-test/` — single binary reads OmniFocus (Rounds A/B: adhoc vs signed).
- `rig/attribution-test/` — launcher spawns a separate reader child (Gate 1).
- Build artifacts (`*.app`, `of-reader`) are gitignored — rebuild with each `build.sh`.

## How to re-run

**Gate 1 (attribution, free):**
```sh
cd rig/attribution-test && bash build.sh    # prints the exact disclaimer command
tccutil reset All dev.kempenich.oftest
# run the printed: disclaimer "<launcher>" "<of-reader>"  → prompt should name "OmniFocus Operator"
```

**Gate 2 (persistence, needs Developer ID cert):**
```sh
cd rig/identity-test && bash build.sh
codesign --force --options runtime --sign "Developer ID Application: <you> (TEAMID)" "OmniFocus Operator.app"
tccutil reset All dev.kempenich.oftest
# run via disclaimer, Allow once, run again → expect NO re-prompt
sqlite3 "$HOME/Library/Application Support/com.apple.TCC/TCC.db" \
  "SELECT service,client,auth_value FROM access WHERE client='dev.kempenich.oftest';"   # want auth_value=2
```

(Reading `TCC.db` needs Full Disk Access on the terminal running `sqlite3`.)

## Files

- `FINDINGS.md` — full investigation: hypotheses, daemon-log proof, `TCC.db` evidence, distribution research, sources.
- `README.md` — this file.

## Related

- GitHub issue #2 (recurring prompt) + the uvx-not-found issue (separate bug, separate root cause: Claude Desktop's minimal PATH).
- Todo: `.planning/todos/pending/2026-05-20-fix-recurring-macos-permission-prompt-on-claude-desktop-laun.md`
- Step-by-step validation guide (Obsidian): `_AgentSandbox_/tcc-validation/GUIDE.md`
- Docs to correct: landing page (`docs/index.html` ~L2770) wrongly says Full Disk Access stops the prompt.
