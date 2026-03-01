# Pitfalls Research

**Domain:** MCP server with file-based IPC to macOS sandboxed application (OmniFocus)
**Researched:** 2026-03-01
**Confidence:** HIGH (most pitfalls verified from multiple sources or directly observable in the bridge script and protocol design)

## Critical Pitfalls

### Pitfall 1: Using `os.rename()` instead of `os.replace()` for atomic writes

**What goes wrong:**
The IPC protocol depends on atomic `.tmp` to `.json` renames to prevent partial reads. `os.rename()` on macOS does not guarantee atomic overwrite of an existing destination file. If a response file already exists (e.g., from a stale previous run), `os.rename()` may silently corrupt it or raise an error depending on timing.

**Why it happens:**
`os.rename()` appears to work in testing because collisions are rare. On macOS specifically, `rename(2)` has been reported as non-atomic in edge cases (the OS may delete-then-rename rather than atomically swap). Developers coming from Linux assume POSIX guarantees hold uniformly.

**How to avoid:**
Use `os.replace()` everywhere. It is the correct cross-platform atomic overwrite since Python 3.3. Both the Python IPC layer and any cleanup logic must use `os.replace()`, never `os.rename()`.

**Warning signs:**
- Occasional `FileNotFoundError` or empty response files during high-frequency IPC
- Tests pass in isolation but fail under parallel execution

**Phase to address:**
Milestone 1 (Foundation) -- this is part of the core IPC implementation.

---

### Pitfall 2: Blocking the asyncio event loop with synchronous file I/O

**What goes wrong:**
The MCP server runs on asyncio (stdio transport). File operations -- `open()`, `os.stat()`, `os.replace()`, polling for response files -- are synchronous and block the event loop. During a full dump (~1.5MB JSON), the server becomes unresponsive to other MCP requests. Worse, the polling loop for IPC responses (checking if a file exists every N ms) blocks the event loop on every stat/read call.

**Why it happens:**
Python's `open()`, `os.stat()`, and `pathlib.Path.exists()` are all synchronous. They feel instantaneous for small files on SSDs, so developers skip offloading them. But the MCP SDK's stdio transport requires the event loop to stay responsive for JSON-RPC framing. Even 50ms of blocking can cause protocol timeouts on the client side.

**How to avoid:**
- Use `asyncio.to_thread()` for all file reads, writes, and stat calls in the IPC layer. This is simpler and more predictable than `aiofiles` (which is just a thread pool wrapper with extra API surface).
- The polling loop should use `await asyncio.sleep(interval)` between checks, with the actual file existence check and file read wrapped in `asyncio.to_thread()`.
- Never call `Path.exists()`, `Path.stat()`, `open()`, or `json.load()` directly in an async function.

**Warning signs:**
- MCP client reports timeouts even though OmniFocus responded (the response file exists but was never read because the event loop was blocked)
- `asyncio` debug mode warnings about slow callbacks

**Phase to address:**
Milestone 1 (Foundation) -- bake this into the IPC layer from day one. Retrofitting is painful because every file operation call site must change.

---

### Pitfall 3: mtime-based cache invalidation missing changes within the same second

**What goes wrong:**
The snapshot freshness check uses `.ofocus` directory mtime. If OmniFocus syncs and the Python server checks mtime within the same second, the mtime appears unchanged and the server serves stale data. This is the classic "mtime comparison considered harmful" problem documented extensively in build systems (Make, Git index race condition).

**Why it happens:**
Although APFS supports nanosecond timestamps, there is no guarantee that OmniFocus updates the `.ofocus` package mtime with nanosecond precision. The OmniFocus sync process may touch the directory in a way that rounds to the same second. Additionally, `os.stat()` returns `st_mtime` as a float, which has precision issues -- use `st_mtime_ns` instead.

**How to avoid:**
- Use `st_mtime_ns` (integer nanoseconds) instead of `st_mtime` (float seconds) to get maximum available precision.
- Accept that mtime alone can miss rapid changes. For a task manager used by a human, this is acceptable -- changes happen on human timescales (seconds apart), not within the same nanosecond. Document this known limitation rather than over-engineering around it.
- If false staleness becomes a real problem in production, add a force-refresh mechanism (e.g., an MCP tool or parameter) as a simple escape hatch.

**Warning signs:**
- After quickly adding a task in OmniFocus and immediately querying the MCP server, the new task does not appear
- Inconsistent behavior that "usually works" but occasionally misses changes

**Phase to address:**
Milestone 1 (Foundation) -- use `st_mtime_ns` from the start. The force-refresh escape hatch can wait for a later milestone if needed.

---

### Pitfall 4: URL scheme trigger is fire-and-forget with no delivery guarantee

**What goes wrong:**
`open "omnifocus:///omnijs-run?script=..."` returns immediately with exit code 0 regardless of whether OmniFocus actually received, executed, or succeeded with the script. If OmniFocus is not running, the URL scheme may launch it (adding multi-second delay) or silently fail. If OmniFocus is busy (syncing, UI-blocked), the script may queue or drop. The Python side has no way to distinguish "OmniFocus is still processing" from "the trigger was lost."

**Why it happens:**
macOS URL schemes are an IPC mechanism designed for user-facing app launches, not reliable inter-process communication. There is no acknowledgment, no error channel, and no timeout signal from the OS. The `open` command's job is to tell Launch Services to dispatch the URL -- nothing more.

**How to avoid:**
- The 10-second timeout on the response file is the only viable detection mechanism. Make the error message actionable: "OmniFocus did not respond within 10s. Ensure OmniFocus is running and has completed its initial sync."
- Write the request file **before** triggering the URL scheme. The bridge script reads its request ID from the `arg` parameter and can immediately find the request file. If you trigger first and write second, there is a race.
- Consider adding a `ping` operation as a health check: trigger, wait for response file, confirm OmniFocus is responsive. Run this at server startup.
- Log the exact URL being opened at DEBUG level so failed triggers can be manually reproduced.

**Warning signs:**
- Intermittent timeouts that resolve when the user clicks on OmniFocus (bringing it to the foreground helps it process queued scripts)
- Timeouts specifically after OmniFocus has been idle for a long time (macOS may have throttled it)

**Phase to address:**
Milestone 1 (Foundation) -- the timeout and error message are core. The `ping` health check is a good Milestone 1 acceptance test.

---

### Pitfall 5: Bridge script `flattenedTasks` serialization blocking OmniFocus UI

**What goes wrong:**
The bridge script iterates `flattenedTasks`, `flattenedProjects`, `flattenedTags`, and `flattenedFolders` -- the entire OmniFocus database. For ~2,400 tasks, this takes measurable time inside OmniFocus's JavaScript engine. During this time, OmniFocus UI may freeze or stutter because OmniJS scripts run on the main thread. With larger databases (5,000+ tasks, long notes), this becomes noticeable to the user.

**Why it happens:**
OmniJS scripts execute synchronously within OmniFocus's process. Each property access on a task object may trigger a database read. The `.map()` over `flattenedTasks` is O(n) with per-element database access overhead. Community reports confirm that iterating tasks with property reads can take 40+ seconds for ~900 tasks when done inefficiently (though the bridge script's approach of accessing properties directly, not via `.whose()`, is more efficient).

**How to avoid:**
- The current bridge script design (one `flattenedTasks.map()` call with direct property access) is already the most efficient pattern for OmniJS. Do not introduce `.whose()` filtering or per-task conditional logic -- these are slower.
- Minimize the bridge script's work. No filtering, no transformation, no date math in JS. Dump raw data and let Python do the thinking. The existing script already follows this principle.
- For very large databases, consider trimming the dump to exclude completed tasks older than N days. But do this only if profiling shows the dump takes more than 3-5 seconds.
- Accept that the dump will briefly freeze OmniFocus. Since it only happens on cache miss (mtime changed), this is infrequent.

**Warning signs:**
- Users report OmniFocus "beachballing" when the MCP server starts up or refreshes
- Dump times exceeding 5 seconds (measure and log this)

**Phase to address:**
Milestone 1 (Foundation) -- measure dump time and log it. Optimization only if it exceeds acceptable thresholds.

---

### Pitfall 6: Tmp file and response file left behind after crashes (orphaned IPC artifacts)

**What goes wrong:**
If the Python server crashes mid-request, or OmniFocus crashes mid-response, `.tmp` files or completed `.json` response files accumulate in the IPC directory. On next startup, old response files matching a UUID that gets reused (astronomically unlikely with UUID4, but old responses from previous runs remain) could be misread. More practically, the directory fills with garbage over time, and a glob-based response file check could theoretically pick up the wrong file if the matching logic is loose.

**Why it happens:**
Neither side cleans up on crash. The IPC protocol assumes both sides run to completion: Python writes request, OmniFocus writes response, Python reads and deletes response. Any interruption breaks this chain.

**How to avoid:**
- On startup, sweep the IPC directory: delete all files in `requests/` and `responses/`. The server owns this directory. Any files present at startup are orphans from a previous session.
- After successfully reading a response, delete both the response file and the request file.
- Use UUID4 for request IDs (already planned). The collision probability is negligible, but cleanup on startup eliminates the concern entirely.
- Set a maximum age for files: if a response file is older than 60 seconds, ignore it. This is a defense-in-depth measure.

**Warning signs:**
- The IPC directory accumulates hundreds of small JSON files over days of use
- A request mysteriously gets an instant "response" that is actually from a previous session

**Phase to address:**
Milestone 1 (Foundation) -- startup cleanup is simple and essential.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoded 10s timeout | Simple, no config needed | Too short for cold-start OmniFocus launches, too long for quick health checks | Milestone 1 only. Make configurable by M3 when usage patterns are clear. |
| Polling with `asyncio.sleep()` instead of FSEvents | No native dependency, simple to understand | Higher latency (up to 1 poll interval) and slight CPU waste compared to event-driven | Acceptable for the entire project lifespan. The IPC happens infrequently (cache hit = no IPC), and polling intervals of 100-200ms are fine. |
| No retry on URL scheme trigger failure | Simpler error handling, fail-fast | If OmniFocus is slow to wake, the first trigger might be lost | Milestone 1 only. Consider a single retry with backoff in production hardening. |
| Logging to stderr without structured format | Fast to implement, MCP SDK compatible | Hard to parse programmatically, no log levels per component | Acceptable until production hardening milestone. |
| Tags stored as names (strings) not IDs | Matches bridge script output, simpler models | Tag renames could break cached references; name collisions between nested tags | Acceptable. Tag IDs are not exposed by the bridge script's current output. Revisit if tag writes are added (M5). |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| OmniFocus URL scheme (`omnijs-run`) | Passing the full bridge script in the `script` URL parameter every time, hitting URL length limits (~2048 chars) | The bridge script should be installed as a persistent file in the OmniFocus sandbox. The URL scheme's `script` parameter loads and executes it. Alternatively, use a minimal bootstrap script that reads the installed file. |
| OmniFocus sandbox directory | Hardcoding the path `~/Library/Containers/com.omnigroup.OmniFocus4/...` and assuming it exists | The container directory only exists if OmniFocus 4 is installed. OmniFocus 3 uses a different bundle ID (`com.omnigroup.OmniFocus3`). Check existence at startup and fail with a clear message. Make the path configurable. |
| Pydantic camelCase aliases | Defining aliases for deserialization (JSON from bridge) but forgetting `by_alias=True` when serializing back to JSON for MCP responses | Set `model_config = ConfigDict(populate_by_name=True)` and always use `model_dump(by_alias=True)` for MCP output. Better: define a `serialize()` method on the base model that enforces this. Test serialization round-trip explicitly. |
| MCP tool return values | Returning raw Pydantic model dumps (large nested JSON) that blow up the LLM's context window | The `list_all` tool returns ~1.5MB of JSON. This is inherently large. Ensure the MCP tool description warns about output size. Field selection (M4) is the real fix. |
| asyncio.Lock for deduplication | Using a `threading.Lock` instead of `asyncio.Lock`, or holding the lock during the entire bridge call (including file I/O wait) | Use `asyncio.Lock`. Acquire it, check if a fresh dump already exists (another coroutine may have just completed one), and only trigger the bridge if needed. Release after updating the snapshot, not after every file operation. |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Parsing 1.5MB JSON on every mtime change | Noticeable delay (200-500ms) after OmniFocus sync | Use `orjson` for JSON parsing (~10x faster than `json` stdlib for large payloads). Offload parsing to a thread via `asyncio.to_thread()`. | Databases > 5MB (unlikely for personal use, but possible with long notes) |
| Re-dumping on every OmniFocus sync event | OmniFocus syncs frequently (every 15 min or on app activate). Each sync updates `.ofocus` mtime, triggering a full dump even if no data changed. | Accept the re-dump cost -- it is the design. The dump is infrequent relative to reads (most reads hit the cache). If this becomes painful, add content hashing of the dump to skip snapshot replacement when data is identical. | Not a real problem unless dump time exceeds 3s |
| Bridge script JSON.stringify on large data | OmniFocus JS engine may struggle with very large JSON serialization | The existing bridge already does a single `JSON.stringify()` on the entire response object. This is the right approach -- multiple smaller stringifications would be slower. No action needed unless profiling shows this as a bottleneck. | Databases > 10,000 tasks with long notes |
| Polling interval too aggressive | CPU usage spikes, especially on battery | Use 200ms poll interval (not 50ms). For a 10s timeout, that is 50 stat calls -- negligible on SSD. | Never a real issue at 200ms intervals |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Exposing task content via MCP without transport encryption | Sensitive task data (personal, work, health-related) transmitted over stdio in plaintext | For stdio transport (local use), this is acceptable -- data stays on the machine. If HTTP transport is added later, require TLS. Document that this server exposes all OmniFocus data to the connected agent. |
| Not sanitizing bridge script arguments | A crafted request ID containing `::::` could inject extra arguments into the dispatch string | Validate request IDs as UUID4 format before constructing the argument string. The bridge script splits on `::::`, so a malicious request ID could alter the operation. |
| Request file content injection | For write operations, the bridge reads payloads from request files. A malicious agent could craft payloads that exploit OmniJS APIs | For M1 (read-only), this is not a concern. For M5 (writes), validate all write payloads against a strict schema before writing the request file. The bridge script should validate too. |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Silent failure when OmniFocus is not running | User waits 10 seconds for a timeout, gets a generic error | Check if OmniFocus is running at startup (`pgrep -x OmniFocus` or AppleScript). Warn immediately. Consider auto-launching via URL scheme if not running. |
| First request after startup is slow (cold cache) | The daily review use case means the first request every morning triggers a full dump (2-5 seconds). User perceives the tool as slow. | Pre-warm the cache at server startup: trigger a dump immediately, before any MCP request arrives. The first `list_all` call then hits the warm cache. |
| Error messages reference internal concepts | "Bridge timeout" or "IPC directory not found" means nothing to the user | Use human-readable errors: "OmniFocus did not respond. Is it running?" / "Cannot find OmniFocus data directory. Is OmniFocus 4 installed?" |
| Large `list_all` output overwhelms the LLM | Claude's context fills with 1.5MB of raw JSON, leaving no room for reasoning | Document in the tool description that `list_all` returns the full database. In M2, provide `list_tasks` with filters as the recommended alternative. |

## "Looks Done But Isn't" Checklist

- [ ] **Atomic writes:** Both sides (Python and JS) use atomic writes -- verify the JS side uses `FileWrapper.WritingOptions.Atomic` (it does in the draft script) AND the Python side uses `os.replace()` (not `os.rename()`)
- [ ] **Request file written before URL trigger:** The request file must exist before `open` fires the URL scheme, or the bridge script may look for a request file that does not exist yet
- [ ] **IPC directory created at startup:** Neither OmniFocus nor the bridge script creates `requests/` and `responses/` subdirectories. The Python server must ensure they exist at startup (`mkdir -p` equivalent).
- [ ] **Bridge script encoding:** The URL scheme passes the script as a URL-encoded parameter. Special characters in the JS source (quotes, braces, newlines) must survive URL encoding. Test with the actual OmniFocus URL handler, not just in a browser.
- [ ] **Pydantic alias round-trip:** Fields deserialize from camelCase (bridge JSON) and serialize back to camelCase (MCP output). If `by_alias=True` is missing from `model_dump()`, the MCP output uses snake_case, which is inconsistent with the bridge schema.
- [ ] **Deduplication lock actually prevents parallel dumps:** Write a test where two coroutines call the repository simultaneously. Only one bridge call should fire. The second coroutine should receive the result from the first.
- [ ] **Timeout error is actionable:** The timeout error message mentions OmniFocus by name and suggests checking if it is running. Not a generic "timeout" string.
- [ ] **Snapshot replacement is atomic:** The in-memory snapshot must be replaced in a single assignment (`self._snapshot = new_snapshot`), not by mutating the existing snapshot in place. Concurrent reads during replacement must see either the old or the new snapshot, never a half-updated one.
- [ ] **`.ofocus` path is configurable:** Tests cannot depend on the real `.ofocus` directory. The path must be injectable.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Stale cache (mtime miss) | LOW | Restart the MCP server. It re-checks mtime on next request. Or add a `refresh` tool/parameter. |
| Orphaned IPC files | LOW | Delete all files in `requests/` and `responses/`. Server startup does this automatically. |
| OmniFocus unresponsive to URL scheme | LOW | Quit and relaunch OmniFocus. The bridge script is stateless -- no recovery needed on the OF side. |
| Corrupted response JSON (partial write) | LOW | The request will timeout. Retry the MCP operation. The corrupted file is cleaned up on next startup. |
| Bridge script error (JS exception) | LOW | The bridge script wraps everything in try/catch and writes `{ success: false, error: "..." }`. Python receives the error and surfaces it. No recovery action needed beyond fixing the bug. |
| Pydantic validation failure on dump data | MEDIUM | A field shape changed in OmniFocus or the bridge script. Update the Pydantic model to match. Use `model_validate(..., strict=False)` during development to get detailed error messages. |
| asyncio.Lock deadlock | HIGH | Only possible if the lock is acquired but never released (exception in critical section without try/finally). Use `async with lock:` context manager exclusively -- never bare `acquire()`/`release()`. |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| `os.replace()` over `os.rename()` | M1 (Foundation) | Grep codebase for `os.rename` -- should return zero results |
| Blocking event loop with file I/O | M1 (Foundation) | All file operations wrapped in `asyncio.to_thread()`. Enable asyncio debug mode in tests to catch slow callbacks. |
| mtime nanosecond precision | M1 (Foundation) | Code uses `st_mtime_ns`, not `st_mtime`. Unit test with mocked timestamps. |
| URL scheme fire-and-forget | M1 (Foundation) | Integration test: trigger with OmniFocus not running, verify actionable error message within timeout. |
| Bridge script performance | M1 (Foundation) | Log dump time. Acceptance: < 3 seconds for ~2,400 tasks. |
| Orphaned IPC cleanup | M1 (Foundation) | Test: create orphan files, start server, verify they are deleted. |
| Pydantic alias serialization | M1 (Foundation) | Round-trip test: deserialize bridge JSON, serialize for MCP, verify camelCase field names. |
| Deduplication lock correctness | M1 (Foundation) | Concurrent coroutine test with mock bridge that counts invocations. |
| Request ID injection | M1 (Foundation) | Validate request IDs as UUID4 before constructing dispatch string. |
| Token overflow from `list_all` | M2 (Filtering) | `list_tasks` with field selection reduces output. Document `list_all` size warning. |
| Tag name vs ID fragility | M5 (Writes) | If tag writes are added, evaluate whether tag IDs should be introduced. |
| Cache pre-warming | M1 (Foundation) | First MCP request returns in < 500ms (cache already warm from startup). |

## Sources

- [Atomic writes on macOS: `os.replace` vs `os.rename`](https://github.com/python/cpython/issues/143909) -- HIGH confidence
- [mtime comparison considered harmful](https://apenwarr.ca/log/20181113) -- HIGH confidence, authoritative analysis of mtime pitfalls
- [Git index race condition](https://crypto.stanford.edu/~blynn/gg/race.html) -- HIGH confidence, demonstrates same-second mtime collision
- [OmniFocus batch task reading performance](https://discourse.omnigroup.com/t/reading-a-batch-of-tasks-taking-way-too-long/36691) -- HIGH confidence, direct from Omni forums
- [OmniFocus MCP Server discussion](https://discourse.omnigroup.com/t/omnifocus-mcp-server/71214) -- MEDIUM confidence, community reports
- [MCP implementation tips and pitfalls (Nearform)](https://nearform.com/digital-community/implementing-model-context-protocol-mcp-tips-tricks-and-pitfalls/) -- HIGH confidence
- [asyncio deadlock patterns](https://superfastpython.com/asyncio-deadlock/) -- HIGH confidence
- [asyncio.Lock documentation](https://docs.python.org/3/library/asyncio-sync.html) -- HIGH confidence, official Python docs
- [macOS sandbox file access](https://developer.apple.com/documentation/security/accessing-files-from-the-macos-app-sandbox) -- HIGH confidence, Apple documentation
- [Electron deep link length limits](https://github.com/electron/electron/issues/40776) -- MEDIUM confidence, suggests ~2048 char URL scheme limit
- [Pydantic alias documentation](https://docs.pydantic.dev/latest/concepts/alias/) -- HIGH confidence, official docs
- [`rename(2)` non-atomic on macOS](http://www.weirdnet.nl/apple/rename.html) -- MEDIUM confidence, older source but corroborated by CPython issue tracker

---
*Pitfalls research for: OmniFocus Operator (MCP server + file-based IPC + OmniFocus automation)*
*Researched: 2026-03-01*
