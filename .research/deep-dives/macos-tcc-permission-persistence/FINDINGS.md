# Findings — macOS TCC Permission Persistence

Investigation date: **2026-05-20** · macOS **26 (Tahoe)** · Claude Desktop (Electron).

---

## The setup

Claude Desktop does not spawn the MCP server directly. It goes through a signed helper:

```
Claude.app/Contents/Helpers/disclaimer  →  uvx  →  uv  →  python3.13 (reads OmniFocus)
```

- `disclaimer` is Anthropic-signed (Team `Q6L2SF6YDW`). Its job: call `responsibility_spawnattrs_setdisclaim()` so its **direct child becomes its own responsible process** (instead of responsibility rolling up to Claude.app).
- The server reads OmniFocus's group container (`~/Library/Group Containers/34YW5XSRB7.com.omnigroup.OmniFocus`) → triggers TCC class **`kTCCServiceSystemPolicyAppData`** ("…access data from other apps").

### Signing facts (all ad-hoc, no identity)

| Binary | Signature | Team ID |
|---|---|---|
| `uvx` (`~/.local/share/mise/installs/uv/0.11.3/…`) | adhoc, linker-signed | not set |
| `uv` | adhoc | not set |
| uv-managed `python3.13` (`~/.local/share/uv/python/…`) | adhoc, `Identifier=-` | not set |

The dialog displays **`"uvx"`** — the disclaimer's *direct child* (= the config `command`), even though `python` does the actual read. TCC attributes the descendant's access up to the direct child.

---

## Distribution-route research (pre-experiment)

Four candidate fixes; only one survives:

| Route | Persists once? | Why |
|---|---|---|
| **Signed launcher** (Developer ID) | ✅ likely | stable trusted identity; TCC keys grant on Team ID, survives updates |
| Claude Desktop `.mcpb` extension | ❌ | same `disclaimer` spawn; Claude bundles **Node, not Python**; Pydantic deps can't portably bundle → falls back to uvx |
| Full Disk Access (manual) | ❌ | FDA = `SystemPolicyAllFiles`, a *different service* than `AppData`; doesn't satisfy the prompt |
| `uv tool install` + abs path | ❌ | stable path, but still adhoc / no identity |

Key external corroboration (same OS): claude-code issues [#36675](https://github.com/anthropics/claude-code/issues/36675) (bare binary, no Info.plist → TCC won't persist), [#36832](https://github.com/anthropics/claude-code/issues/36832) (the `disclaimer` wrapper), [#48311](https://github.com/anthropics/claude-code/issues/48311) (designated requirement must stay stable across updates), [#27557](https://github.com/anthropics/claude-code/issues/27557) (disclaimer's bare-name signing). uv signing request: [astral-sh/uv#14870](https://github.com/astral-sh/uv/issues/14870).

---

## Experiment: the free validation (self-signed)

Rig: a `.app` (`CFBundleDisplayName = "OmniFocus Operator"`, id `dev.kempenich.oftest`) wrapping a tiny reader. Run via `disclaimer` straight from the terminal (faithful — disclaimer makes the child its own responsible process regardless of parent).

| Round | Build | Result |
|---|---|---|
| **A** (control) | adhoc | prompt **every** run; dialog already says "OmniFocus Operator" ✅ (name fix is free) |
| **B** (test) | self-signed (`OFOperator Test Cert`) | **still re-prompts** ❌ |
| **Probe 1** | self-signed + cert "Always Trust" in login keychain | still re-prompts ❌ (tccd is root; ignores login-keychain trust) |

### Daemon log — run #1 (first run, no record yet)

```
IDENTITY_ATTRIBUTION: identifier = dev.kempenich.oftest, type 0
Handling access request to kTCCServiceSystemPolicyAppData … ReqResult(Auth Right: Unknown …) → prompt
DR: identifier "dev.kempenich.oftest" and certificate leaf = H"8abb…"
TCCDEvent: type=Create, service=kTCCServiceSystemPolicyAppData, identifier=dev.kempenich.oftest   ← record WRITTEN on Allow
```

### Daemon log — run #2 (record exists, no reset)

```
matchesCodeRequirement … dev.kempenich.oftest :
  identifier "dev.kempenich.oftest" and certificate leaf = H"8abb…" ; status: 0   ← identity VALID
Handling access request to kTCCServiceSystemPolicyAppData … ReqResult(Auth Right: Unknown …) → prompt AGAIN
```

Identity check passes, yet the grant is `Unknown` → not honored.

### Ground truth — `TCC.db`

```
service=kTCCServiceSystemPolicyAppData  client=dev.kempenich.oftest  client_type=0
auth_value=5   auth_reason=2 (User Consent)   last_modified=<recent>
```

- The row **exists** → grant is persisted, not lost at write time.
- `auth_value=5` is **outside the classic set** (`0 denied / 1 unknown / 2 allowed / 3 limited`) — a newer macOS value the public docs don't cover. Its *operational* meaning is unambiguous from the log: **not honored → re-prompt.**
- `auth_reason=2` = the user really did consent.

### Positive control — Bartender (in the same log)

A Developer-ID-signed app (Team `24J875RH8J`) on the same machine, same instant:
```
Handling access request … from {com.surteesstudios.Bartender} … Auth Right: Allowed   authValue=2  ✅
```
→ Trusted identity = `auth_value=2`, honored, persists. Untrusted (ours) = `5`, re-prompts. **The only differentiating variable is trust lineage.**

---

## Gate 1 — attribution of a spawned child (free, PASSED)

Question: in the real chain the *launcher* won't read — `python` (a child) will. Does TCC attribute the child's read to the launcher's identity?

Rig: launcher `posix_spawn`s a separate bare binary `of-reader`; launcher never touches OmniFocus.

```
AttributionChain:
  responsible = OmniFocusOperatorTest   (…/OmniFocus Operator.app)   ← the launcher
  accessing   = of-reader               (the child that actually read)
  requesting  = com.apple.sandboxd
Handling access … kTCCServiceSystemPolicyAppData,
  from Sub:{dev.kempenich.oftest} Resp:{OmniFocusOperatorTest …/OmniFocus Operator.app}
```

Dialog named **"OmniFocus Operator"**. ✅ **The child's read attributes to the launcher's identity.** The signed-launcher architecture is sound.

(Detail: DR here showed a `cdhash` because this launcher is still adhoc — with Developer ID it becomes Team-ID-based.)

---

## Gate 2 — does Developer ID make AppData persist? **FAILED**

Re-signed the rig with a real Developer ID (Florian Kempenich, Team `7T6UW39FB3`). DR became Team-ID-based and chains to Apple Root CA:
```
Authority = Developer ID Application: Florian Kempenich (7T6UW39FB3) → Developer ID CA → Apple Root CA
designated => identifier "dev.kempenich.oftest" and anchor apple generic and …leaf[subject.OU] = "7T6UW39FB3"
```
Registered (`lsregister`), reset, ran via `disclaimer`, Allow, re-ran.

**Result: still re-prompts. `TCC.db` `auth_value=5`, unchanged.** Trusted signing alone does **not** make the AppData grant persist — identical to self-signed.

→ **`SystemPolicyAppData` does not persist for this process class, regardless of signing.**

## Breakthrough — Full Disk Access is the real lever

Closest public match: [claude-code #24162](https://github.com/anthropics/claude-code/issues/24162) (same `auth_value=5` + `SystemPolicyAppData`, Claude's own embedded CLI). The reframe: every run does an `AllFiles` (FDA) preflight **before** the AppData path — see the original run's log (`Handling access request to kTCCServiceSystemPolicyAllFiles … Denied`). Grant FDA → that preflight passes → the AppData prompt never fires.

Test: System Settings → Privacy & Security → Full Disk Access → add the signed `.app` → run via `disclaimer` → **SILENT.** ✅ The only variable changed was the FDA grant (no reset needed — it nagged every run before).

## Gate 3 — does the FDA grant survive updates? **PASSED**

Rebuilt the app (new cdhash) + re-signed with the same Developer ID, **without re-granting FDA** → ran → **still silent.** The grant is keyed to the **Team ID** (designated requirement), not the cdhash → survives every release. An *unsigned* binary's FDA grant would be path/cdhash-pinned and break on update — so the cert is required, for **durability**.

> FDA grants live in the **SIP-protected system TCC.db**, so a user-db `sqlite3` read shows no `AllFiles` row (only the dead `AppData|5`). Durability was verified **behaviorally** (rebuild → still silent), not by reading the DB.

## Corrections to earlier reasoning

- **"Bartender persists"** was its **ScreenCapture (System Set)** grant — *not* a prompted AppData grant. We never actually had evidence any app persists a *prompted* AppData grant; Gate 2 confirms they don't.
- **"Full Disk Access doesn't fix it"** (early conclusion) was about FDA on **`Claude.app`** (wrong target — attribution lands below Claude). FDA on the **server's own signed binary** *is* the fix.

## Definitive root cause (4-agent deep research, 2026-05-21)

After signed + notarized + /Applications + user-launched (`open`) ALL still gave `auth_value=5`, four independent research agents converged on the same answer:

**`kTCCServiceSystemPolicyAppData` is a *transient, process-lifetime* permission — non-persistent by design.** Apple DTS (Quinn), Forums thread 742147:
> TCC privileges fall into groups: Persistent system-wide; Persistent per-user; **Transient, process lifetime**. The privilege to access other apps' containers falls into that third group. **If granted, that consent applies only for the duration of that app instance.** Every time the pid changes will trigger a new prompt. This is as expected.

- The transience is a property of the **service**, not the **client** — which is exactly why no identity/notarization/location/launch-context change moved it.
- **Why us specifically:** the file is in OmniGroup's **Group Container** (`34YW5XSRB7.com.omnigroup.OmniFocus`). Since macOS 15, accessing another team's group container without the transient prompt requires legitimate **membership** — group ID prefixed with *your* Team ID, or provisioning/App-Store. Our team `7T6UW39FB3` ≠ `34YW5XSRB7` → membership structurally impossible → always the transient path. (Per-app Container protection: CVE-2023-42929, Sonoma; Group Container protection: Sequoia 15.)
- **`auth_value=5`:** a live `tccd` disassembly (Tahoe) revealed a *session-scoped authorization* subsystem (`Session scoped auth is valid/invalid for client`, keyed to `session_pid`/`pid_version`/`boot_uuid`) and proved the enum extends past the classic `0–3` (e.g. `auth_value=4` for Calendar add-only). So `5` ≈ a **session-scoped allow** valid only for the granted pid. (Exact integer undocumented publicly; the *behavior* is Apple-documented.)
- **Not just us:** identical "re-prompts every launch" reported for claude-code #36832, openai/codex #11027, ghostty #4496, Adobe Illustrator/InDesign 2026, ACDSee — all resolve to **grant Full Disk Access**.

**How other apps "do it" (none of which is persisting a prompted foreign-container grant — that isn't a thing):** read their *own* data; same-vendor App Group; have Full Disk Access; or use the other app's **API** (AppleScript/automation → `AppleEvents` TCC, which *does* persist).

**Verdict matrix:**
| Option | Verdict |
|---|---|
| Persistent prompted `AppData=2` (foreign Group Container) | ❌ Impossible by design |
| **Full Disk Access** (user-granted) | ✅ Works, persists, industry standard |
| OmniFocus automation API instead of raw reads | ✅ Persists (AppleEvents), Omni-supported, but an architecture change |
| App Group | ❌ same-vendor only |
| PPPC pre-grant of `SystemPolicyAppData` | ❌ not a valid PPPC key (FDA-via-PPPC works, MDM-only) |

> Side note from research: third-party OmniFocus integrations (rubyfocus, of-store) use the **automation API / `.ofocus` transaction store**, not raw SQLite. Worth weighing for the project long-term — but the current SQLite read demonstrably works with FDA, so this is a strategic note, not a blocker.

### Sources (deep research)
- Apple DTS (Quinn) — transient/process-lifetime classification: https://developer.apple.com/forums/thread/742147
- Apple DTS (Quinn) — Group Container membership criteria + "consent applies only for the duration of that app instance": https://developer.apple.com/forums/thread/721701 · https://developer.apple.com/forums/thread/801461
- CVE-2023-42929 (container protection origin): https://jhftss.github.io/CVE-2023-42929-Why-Do-We-Need-The-App-Container-Protection/
- Mark Rowe — TCC & the platform sandbox policy (AppData is a per-access up-call): https://bdash.net.nz/posts/tcc-and-the-platform-sandbox-policy/
- Same-symptom reports: claude-code [#36832](https://github.com/anthropics/claude-code/issues/36832) · codex [#11027](https://github.com/openai/codex/issues/11027) · ghostty [#4496](https://github.com/ghostty-org/ghostty/discussions/4496)
- App Groups (same-team only): https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.security.application-groups
- FDA = standard answer (Carbon Copy Cloner, Retrospect): https://bombich.com/en/kb/ccc/6/granting-full-disk-access-ccc-and-its-helper-tool
- PPPC has no `SystemPolicyAppData` key: https://support.apple.com/guide/deployment/privacy-preferences-policy-control-payload-dep38df53c2a/web
- OmniFocus automation: https://omni-automation.com/ · https://github.com/jyruzicka/rubyfocus

## The fix (validated) + open items

✅ **Developer-ID-signed app + user grants Full Disk Access once → silent forever, survives updates.**

### Productization decisions (2026-05-21)

- **Notarized + /Applications → AppData persist?** TESTED → **No** (still `auth_value=5`). Notarization does nothing for the prompt; it's only for Gatekeeper on downloaded apps.
- **Architecture:** dropping the SQLite fast-read path is OFF the table (it's the product's whole value). So the real choice is **prompt-every-time** vs **Full Disk Access**.
- **Q1 — does durable FDA require notarization?** **No. Signing (Developer ID) is the only irreducible requirement.** Durability (FDA grant survives updates) was proven on a signed-but-NOT-notarized app (the grant keys to Team ID). The current `uvx`/python chain is unsigned + version-pinned paths → an FDA grant on it would be path-based → breaks on updates + invisible in Settings. So: durable FDA ⇒ a Developer-ID-signed launcher. Notarization deferred to distribution.
- **Q2 — cheap UX win (lazy defer):** the SQLite reads are **already lazy** (fresh read-only connection per query, nothing in repo `__init__`). The ONLY eager startup touch is `sweep_orphaned_files(DEFAULT_IPC_DIR)` at `server/lifespan.py:36` — it hits OmniFocus's container at boot, which is what fires the prompt on *every Claude Desktop launch*. Defer that sweep to first tool call (or first write) → prompt moves to **first OmniFocus tool use**, never on Claude boot. Small, localized change; do regardless of the FDA decision. (NOT yet implemented — captured as direction.)

### Open: minimal-setup + durable FDA (research in progress, 2026-05-21)

Goal: simplest setup for a non-technical user that yields a *durable* FDA grant. Ideal = edit one config file; even better = double-click Claude Desktop Extension. **4 background agents dispatched:**
1. Can FDA persist **unsigned** via stable paths alone? (what breaks a path-based grant)
2. Lightest **Python → Developer-ID-signable binary** route (PyInstaller/Nuitka/py2app/briefcase vs a signed stub that re-signs a copy of `uv`).
3. **`.mcpb` Claude Desktop Extension** bundling a signed binary — does the signature/path survive extraction so FDA persists? (the dream double-click path)
4. Full **distribution decision matrix** (setup steps × FDA-persist × signing/notarization × auto-update × friction).

→ Synthesis + recommendation to land here when agents return.

---

## Distribution + auto-update design (decided shape, not yet committed)

- **Two layers:** signed launcher (bundles `uv`, rarely changes) + server on PyPI (every release). TCC remembers the launcher; server logic updates underneath via PyPI. Developer ID means version updates **never re-prompt** (grant keyed to Team ID).
- **Caching gotcha:** plain `uvx pkg` caches and won't auto-pull newer releases — launcher must use `uvx pkg@latest` / `--refresh` so "next run = latest" holds.
- **Distribution options (undecided):** Homebrew Cask (one-liner, `brew upgrade`) → Sparkle DMG (download once, in-app auto-update) → `.mcpb` double-click (best UX, needs validation).
- **Out:** Mac App Store (sandbox forbids cross-container reads).
- **Separate, not addressed here:** the OmniFocus "Run Script" first-run prompt is a different mechanism.

---

## Open risks (note, don't block)

- App may need to live in `/Applications` (Bartender did; rig ran from a repo dir — untested variable).
- Hardened-runtime entitlements when spawning uv/python — likely fine (separate processes, not loaded as libraries), unverified.
- Gate 2 itself — the core bet, still inferred until tested with a real cert.

---

## Sources

- Apple Forums [730043](https://developer.apple.com/forums/thread/730043) (TCC + designated requirement), [811970](https://developer.apple.com/forums/thread/811970) (Team ID in DR)
- [Rainforest QA — TCC.db deep dive](https://www.rainforestqa.com/blog/macos-tcc-db-deep-dive)
- [Howard Oakley / eclecticlight — permissions & TCC attribution](https://eclecticlight.co/2025/11/08/explainer-permissions-privacy-and-tcc/)
- [Qt — The Curious Case of the Responsible Process](https://www.qt.io/blog/the-curious-case-of-the-responsible-process) (`responsibility_spawnattrs_setdisclaim`)
- [HackTricks — macOS TCC](https://book.hacktricks.wiki/en/macos-hardening/macos-security-and-privilege-escalation/macos-security-protections/macos-tcc/index.html)
- claude-code issues #36675, #36832, #48311, #27557 · [astral-sh/uv#14870](https://github.com/astral-sh/uv/issues/14870)
- [Apple — PPPC payload (MDM-only)](https://support.apple.com/guide/deployment/privacy-preferences-policy-control-payload-dep38df53c2a/web)
- [Anthropic — Desktop Extensions](https://www.anthropic.com/engineering/desktop-extensions) · [modelcontextprotocol/mcpb](https://github.com/modelcontextprotocol/mcpb)
