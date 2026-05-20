# macOS TCC Permission Persistence

Why the **`"uvx" would like to access data from other apps`** prompt recurs on **every** Claude Desktop launch — and what actually fixes it. Tracked as GitHub issue #2.

## Verdict (2026-05-20) — SOLVED

**Root cause:** `kTCCServiceSystemPolicyAppData` ("access data from other apps") **does not persist** for this process class (a CLI spawned behind Claude's `disclaimer`). macOS writes the user's "Allow" but parks it at **`auth_value=5` (not honored)** → re-prompts every launch, **regardless of signing** — self-signed *and* a real Developer ID both fail identically. The prompt only appears because the binary lacks **Full Disk Access**: each run does an `AllFiles` (FDA) preflight first; it's denied, so macOS falls back to the non-persistent AppData prompt.

**Fix (validated, update-durable):** ship a **Developer-ID-signed app** and have the user grant it **Full Disk Access** once. FDA's `AllFiles` preflight then passes → the AppData prompt never fires. The FDA grant is keyed to the **Team ID**, so it **survives app updates** — proven by rebuilding with a new cdhash (same Developer ID, no re-grant) → still silent. An *unsigned* binary's FDA grant would break every release, so the cert is required — for **durability**, not for AppData.

> **Status: solved.** Confirmed working + survives updates. Open items:
> 1. **UX cost** — FDA is a *broad* permission and a *manual* System-Settings grant (one-time, can't be auto-prompted). Heavier ask than a dialog click.
> 2. **Untested nicer path** — whether a **notarized** app in `/Applications` lets the *narrow* AppData grant persist (`auth_value=2`), which would avoid asking for FDA at all.

## What was proven vs ruled out

| Claim | Result | Evidence |
|---|---|---|
| The `disclaimer` helper breaks attribution | ❌ **Ruled out** | tccd sets `responsible = our app` (Gate 1) |
| FDA **on Claude.app** fixes it | ❌ **Ruled out** | attribution is *below* Claude; wrong target |
| `AppData` grant persists (any signing) | ❌ **Ruled out** | `auth_value=5` for self-signed **and** Developer ID (Gate 2 failed) |
| Trusting the self-signed cert helps | ❌ **Ruled out** | `tccd` runs as root, ignores login-keychain trust |
| Dialog name fixable via bundle alone | ✅ **Confirmed** | `.app` + `CFBundleDisplayName` → "OmniFocus Operator" even unsigned |
| **Gate 1:** child's read attributes to launcher | ✅ **Confirmed** | tccd: `responsible = launcher` when child `of-reader` reads |
| **FDA on the launcher binary fixes it** | ✅ **Confirmed** | grant FDA → `AllFiles` preflight passes → AppData prompt never fires |
| **FDA grant survives updates** | ✅ **Confirmed** | rebuilt (new cdhash, same Dev ID), no re-grant → still silent |
| Notarized → *narrow* AppData persists | ❓ **Untested** | would avoid the broad FDA ask |

> ⚠️ Earlier mis-read (corrected): "Bartender persists" was its **ScreenCapture (System Set)** grant — *not* a user-prompted AppData grant. We never had proof any app persists a prompted AppData grant; Gate 2 confirms they don't.

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

**Gate 2 + the fix (needs Developer ID cert):**
```sh
cd rig/identity-test && bash build.sh
codesign --force --options runtime --sign "Developer ID Application: <you> (TEAMID)" "OmniFocus Operator.app"
# register so Settings/tccutil can resolve the bundle id:
/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister -f "OmniFocus Operator.app"

# Gate 2 — does AppData persist? Run via disclaimer, Allow once, run again:
#   → STILL re-prompts; TCC.db auth_value stays 5. AppData never persists. (Gate 2 FAILS.)

# THE FIX — grant Full Disk Access to the .app:
#   System Settings → Privacy & Security → Full Disk Access → + → add "OmniFocus Operator.app"
#   then run via disclaimer → SILENT (the AllFiles preflight now passes).

# Durability — simulate an update: rebuild + re-sign (new cdhash, same Dev ID), do NOT re-grant:
cd rig/identity-test && bash build.sh && codesign --force --options runtime --sign "Developer ID Application: <you> (TEAMID)" "OmniFocus Operator.app"
#   run via disclaimer → STILL SILENT → grant is Team-ID-based, survives updates. ✅
```

(FDA grants live in the SIP-protected *system* TCC.db, not the user one — so they don't show up in a `sqlite3` read of `~/Library/.../TCC.db`. Verify durability behaviorally, as above.)

## Files

- `FINDINGS.md` — full investigation: hypotheses, daemon-log proof, `TCC.db` evidence, distribution research, sources.
- `README.md` — this file.

## Related

- GitHub issue #2 (recurring prompt) + the uvx-not-found issue (separate bug, separate root cause: Claude Desktop's minimal PATH).
- Todo: `.planning/todos/pending/2026-05-20-fix-recurring-macos-permission-prompt-on-claude-desktop-laun.md`
- Step-by-step validation guide: `GUIDE.md` (this folder) — with filled-in observations from the live run.
- Docs to correct: landing page (`docs/index.html` ~L2770) says grant **Claude Desktop** Full Disk Access — wrong *target*. FDA is the right lever, but it must be granted to the **server's own signed app**, not `Claude.app` (attribution lands below Claude).
