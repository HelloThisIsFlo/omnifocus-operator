---
status: resolved
trigger: "OmniFocus shows SyntaxError: JSON Parse error: Unable to parse JSON string undefined:0:0 on first IPC bridge invocation, then silently fails on subsequent runs."
created: 2026-03-03T00:00:00Z
updated: 2026-03-03T00:15:00Z
---

## Current Focus

hypothesis: CONFIRMED - THREE root causes all now addressed. Root cause 3 fix: IPC dir moved under URL.documentsDirectory.
test: All automated tests pass (166 Python + 16 JS). Need user UAT to confirm OmniFocus round-trip works.
expecting: OmniFocus writes response file successfully under documentsDirectory.
next_action: User runs UAT (uv run python uat/test_read_only.py) to confirm end-to-end IPC works.

## Symptoms

expected: When running `uv run python uat/test_read_only.py`, the Python side should write a JSON request to the IPC folder, trigger OmniFocus via URL scheme, OmniFocus's bridge.js should read the request, execute it, and write a response file back.
actual: First run: OmniFocus shows a pop-up dialog (not in automation console) with `SyntaxError: JSON Parse error: Unable to parse JSON string undefined:0:0`. Subsequent runs: Python side times out waiting for a response, OmniFocus side is completely silent.
errors: `SyntaxError: JSON Parse error: Unable to parse JSON string undefined:0:0`
reproduction: Run `uv run python uat/test_read_only.py`. First time shows error pop-up. Subsequent runs time out silently.
started: During phase 8.1 execution (IPC protocol overhaul). Uncommitted changes exist from previous debug attempt.

## Eliminated

- hypothesis: FileWrapper.fromURL() can't read the request file
  evidence: User confirmed IPC folder IS correctly populated with proper JSON request files. The issue is that bridge.js tries to read `undefined.request.json` because `argument` (the file prefix) is undefined.
  timestamp: 2026-03-03T00:03:00Z

- hypothesis: IPC directory path or _bridge.js file has sandboxing issues
  evidence: The error is specifically a JSON parse error from readRequest(), not a file-not-found. The _bridge.js is in the OmniFocus Group Container which OmniFocus can access.
  timestamp: 2026-03-03T00:03:00Z

## Evidence

- timestamp: 2026-03-03T00:01:00Z
  checked: Uncommitted changes in bridge.js, _real.py
  found: Previous debug attempt changed from inline script to bootstrap eval() pattern. Bootstrap loads _bridge.js from disk via eval(). The `argument` variable (OmniFocus's special variable for &arg= parameter) is referenced inside bridge.js IIFE but NOT in the bootstrap itself.
  implication: The bootstrap eval() approach broke `argument` accessibility.

- timestamp: 2026-03-03T00:02:00Z
  checked: Omni Automation documentation on script URLs and argument handling
  found: Omni Automation docs say: "argument will automatically be replaced with the passed decoded value of the arg parameter" and "avoid using the term argument elsewhere in your script." The argument is a special placeholder/variable available in the script= parameter context.
  implication: `argument` is injected/available only in the top-level script evaluation context. Code loaded via eval() from a separate file does NOT have access to `argument`.

- timestamp: 2026-03-03T00:03:00Z
  checked: Error message analysis
  found: `SyntaxError: JSON Parse error: Unable to parse JSON string` - this comes from readRequest() calling JSON.parse() on invalid input. If argument is undefined, filePrefix is undefined, requestPath becomes "...undefined.request.json", FileWrapper reads nonexistent/wrong file, and JSON.parse fails on whatever is returned.
  implication: Confirms argument is undefined in eval'd context.

- timestamp: 2026-03-03T00:04:00Z
  checked: Why subsequent runs are silent
  found: OmniFocus requires "security approval" for non-static script URLs. First run shows approval dialog + error. After error/rejection, OmniFocus may cache the script hash as rejected or the automation context enters a broken state, causing subsequent URL scheme triggers to be silently ignored.
  implication: This is expected OmniFocus behavior after a script error on first run. Restarting OmniFocus would likely allow the script to run again.

- timestamp: 2026-03-03T00:06:00Z
  checked: Fix implementation and automated test suites
  found: Applied fix to two files. All 166 Python tests pass, all 16 JavaScript bridge tests pass. Bootstrap now correctly references `argument` in the script= context.
  implication: Fix is safe -- no regressions in automated tests. Requires human UAT verification.

- timestamp: 2026-03-03T00:09:00Z
  checked: User UAT of first fix attempt (bootstrap eval + argument in bootstrap)
  found: First fix did NOT work. TWO additional root causes discovered by user: (1) OmniFocus JSON-parses &arg= value before making it available -- raw file_prefix is not valid JSON. (2) OmniFocus sandbox blocks reading _bridge.js from IPC dir -- FileWrapper.fromURL fails with permission error.
  implication: Bootstrap eval() approach is fundamentally broken. Must revert to inline script + JSON-encode arg value.

- timestamp: 2026-03-03T00:10:00Z
  checked: Applied 3-part fix
  found: Reverted _real.py to inline script (self._script passed as script= param), added json.dumps(file_prefix) for arg encoding, restored IIFE in bridge.js, cleaned up test filter. Diff vs HEAD is minimal and targeted.
  implication: Awaiting test run and UAT verification.

- timestamp: 2026-03-03T00:12:00Z
  checked: Filesystem discovery of URL.documentsDirectory
  found: Searched filesystem for benchmark artifacts. Found omnifocus-benchmark/ and omnifocus-operator/ dirs at ~/Library/Containers/com.omnigroup.OmniFocus4/Data/Documents/. This is where URL.documentsDirectory resolves to on macOS. NOT the Group Container (~/Library/Group Containers/34YW5A73WQ...) which was the old IPC path.
  implication: DEFAULT_IPC_DIR must change from Group Containers path to Containers path. bridge.js must derive IPC dir from URL.documentsDirectory at runtime.

- timestamp: 2026-03-03T00:13:00Z
  checked: Applied root cause 3 fix and ran all tests
  found: Changed DEFAULT_IPC_DIR to ~/Library/Containers/com.omnigroup.OmniFocus4/Data/Documents/omnifocus-operator/ipc. bridge.js now derives IPC dir from URL.documentsDirectory + "omnifocus-operator/ipc" at runtime (no more %%IPC_DIR%% placeholder). Removed placeholder replacement from _real.py __init__. Updated test_ipc_engine.py DEFAULT_IPC_DIR assertion. All 166 Python tests pass, all 16 JS tests pass.
  implication: Fix is safe -- no regressions. Requires UAT to confirm OmniFocus round-trip works.

## Key Findings (from investigation)

### OmniFocus Sandbox Rules for URL Scheme Scripts
- `omnijs-run` URL scheme scripts CANNOT write files via `FileWrapper.write()` outside `URL.documentsDirectory`. This is a blanket sandbox restriction, not directory- or URL-method-specific.
- Reading via `FileWrapper.fromURL()` works from broader paths (e.g. Group Containers).
- Writing only works under `URL.documentsDirectory`, which maps to `~/Library/Containers/com.omnigroup.OmniFocus4/Data/Documents/` (NOT the Group Container at `~/Library/Group Containers/34YW5A73WQ.com.omnigroup.OmniFocus/`).
- Installed PlugIns (like FocusRelay) have different, broader sandbox entitlements.

### `argument` Variable Scoping
- OmniFocus's `argument` variable (from `&arg=`) is only available in the top-level `script=` evaluation context. Code loaded via `eval()` from a separate file does NOT have access to it.
- OmniFocus JSON-parses the `&arg=` value before exposing it, so the value must be valid JSON.

### Working IPC Pattern
The proven pattern (from user's earlier benchmark) that guided the fix:
```javascript
var docsDir = URL.documentsDirectory.string.replace("file://", "");
var basePath = docsDir + "omnifocus-operator/ipc";
// Write: FileWrapper.write() works when path is under documentsDirectory
var data = Data.fromString(JSON.stringify(result));
var url = URL.fromPath(basePath + "/response.json", false);
var wrapper = FileWrapper.withContents("response.json", data);
wrapper.write(url, [FileWrapper.WritingOptions.Atomic], null);
```

### Considered but Not Needed
Options explored before discovering the documentsDirectory fix: OmniFocus PlugIn (FocusRelay-style), Pasteboard IPC, AppleScript bridge, Hybrid PlugIn, Omni Preferences storage. All unnecessary since moving IPC under documentsDirectory resolved the write permission issue.

## Resolution

root_cause: THREE root causes: (1) OmniFocus JSON-parses the &arg= URL parameter before making it available as `argument` -- raw file_prefix is not valid JSON. (2) OmniFocus sandbox blocks reading _bridge.js from the Group Container IPC dir, making the bootstrap eval() approach unworkable. (3) OmniFocus sandbox blocks FileWrapper.write() outside URL.documentsDirectory -- the old IPC dir (Group Containers path) is not writable by URL scheme scripts.

fix: 4-part fix addressing all 3 root causes: (1) Inline script approach -- full bridge.js content passed as script= parameter (no _bridge.js, no eval()). (2) JSON-encode the arg= value with json.dumps() so OmniFocus can parse it. (3) bridge.js IIFE derives IPC dir from URL.documentsDirectory + "omnifocus-operator/ipc" at runtime, ensuring FileWrapper.write() has sandbox permission. (4) Python DEFAULT_IPC_DIR changed to ~/Library/Containers/com.omnigroup.OmniFocus4/Data/Documents/omnifocus-operator/ipc (matches URL.documentsDirectory on filesystem).

verification: All 166 Python tests + 16 JS tests pass. UAT confirmed by user — IPC round-trip works end-to-end.
files_changed: [src/omnifocus_operator/bridge/_real.py, src/omnifocus_operator/bridge/bridge.js, tests/test_ipc_engine.py, bridge/tests/bridge.test.js]
