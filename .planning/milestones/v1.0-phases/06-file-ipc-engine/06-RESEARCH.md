# Phase 6: File IPC Engine - Research

**Researched:** 2026-03-02
**Domain:** Async file-based IPC between Python MCP server and OmniFocus JXA bridge script
**Confidence:** HIGH

## Summary

Phase 6 builds the file-based IPC mechanics into `RealBridge` as the base class, with `_trigger_omnifocus()` as a no-op placeholder (Phase 8 fills in the URL scheme trigger). The IPC engine writes request files atomically, polls for response files, and handles timeouts, cleanup, and PID-based orphan sweeping.

The technical surface is well-understood: `os.replace()` provides POSIX-guaranteed atomic renames (verified via CPython docs), `asyncio.to_thread()` offloads all blocking file I/O to the thread pool, and `uuid.UUID(str, version=4)` validates UUID4 strings. No external dependencies are needed -- everything uses Python 3.12 stdlib (`os`, `asyncio`, `uuid`, `json`, `pathlib`). The polling approach with `asyncio.sleep()` is simpler and more reliable than filesystem watchers for single-file response detection.

**Primary recommendation:** Use stdlib-only polling with `asyncio.to_thread()` for all file operations. Keep the IPC protocol simple: dispatch string in the `arg` parameter (not in request file content), JSON response with `success`/`error`/`data` envelope matching the existing bridge script format.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- UUID-based filenames: `<pid>_<uuid>.request.json` and `<pid>_<uuid>.response.json`
- PID prefix enables per-instance isolation (multiple MCP server instances can share the same IPC directory safely)
- Clean up both request and response files after successful round-trip
- On timeout, clean up the request file (late OmniFocus responses become orphans for next sweep)
- Flat directory structure: all request/response files in one directory
- IPC directory configurable via `OMNIFOCUS_IPC_DIR` env var (read by factory/wiring layer)
- Constructor also accepts explicit `ipc_dir` parameter (matches existing `OMNIFOCUS_BRIDGE` env var pattern)
- Default path: OmniFocus 4 group container `~/Library/Group Containers/34YW5A73WQ.com.omnigroup.OmniFocus/com.omnigroup.OmniFocus4/ipc/` (research agent should validate exact subpath)
- Auto-create IPC directory (mkdir -p) on initialization if it doesn't exist
- Startup sweep: PID-based ownership -- check if owning PID is alive via `os.kill(pid, 0)`, only delete files from dead PIDs, skip files from alive PIDs
- No age-based fallback for sweep (PID check is sufficient; worst case is harmless orphaned files)
- Timeout cleanup: delete request file when 10s timeout fires
- Architecture: Template method pattern -- `RealBridge` is the base class with all IPC mechanics
- `SimulatorBridge(RealBridge)` overrides `_trigger_omnifocus()` to no-op
- Phase 6 builds `RealBridge` with `_trigger_omnifocus()` as a no-op placeholder; Phase 8 fills in URL scheme trigger
- Granular API: `_write_request()` and `_wait_response()` as separate internal methods (RealBridge.send_command composes them with the trigger hook in between)
- Code location: `src/omnifocus_operator/bridge/` package (IPC is an implementation detail of the bridge, not a separate top-level package)

### Claude's Discretion
- Response detection mechanism (polling with `asyncio.to_thread` vs filesystem watcher)
- Request file content format (dispatch string only vs JSON envelope)
- Response validation depth (JSON + error key check vs raw pass-through)
- Exact polling interval if polling chosen
- Internal error types (reuse existing `BridgeError` hierarchy vs new IPC-specific errors)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| IPC-01 | File writes use atomic pattern (write `.tmp`, then `os.replace()` to final path) | `os.replace()` is POSIX-atomic (CPython docs confirm). Pattern: write to `<path>.tmp`, then `os.replace(tmp, final)`. All via `asyncio.to_thread()`. See Code Examples. |
| IPC-02 | All file I/O in async context is non-blocking (via `asyncio.to_thread()` or anyio) | `asyncio.to_thread()` offloads sync calls to thread pool. Wrap every `open()`, `os.replace()`, `os.path.exists()`, `os.unlink()`, `json.loads(Path.read_text())` call. See Architecture Patterns. |
| IPC-03 | Dispatch protocol uses `<uuid>::::<operation>` format with UUID4 validation | `uuid.UUID(str, version=4)` validates; `ValueError` on invalid. Validate BEFORE constructing dispatch string to prevent `::::` injection. See Code Examples. |
| IPC-04 | IPC base directory defaults to OmniFocus 4 sandbox path but is configurable for dev/test | Default: `~/Library/Group Containers/34YW5A73WQ.com.omnigroup.OmniFocus/com.omnigroup.OmniFocus4/ipc/`. Override via `OMNIFOCUS_IPC_DIR` env var or `ipc_dir` constructor param. Auto-create with `os.makedirs(exist_ok=True)`. |
| IPC-05 | Response timeout at 10 seconds with actionable error message naming OmniFocus | Use `asyncio.wait_for(poll_coro, timeout=10.0)` catching `TimeoutError`, then raise `BridgeTimeoutError` with message naming OmniFocus. Clean up request file on timeout. |
| IPC-06 | Server sweeps orphaned request/response files from IPC directory on startup | `sweep_orphaned_files()` iterates `.request.json`/`.response.json` files, extracts PID prefix, checks liveness via `os.kill(pid, 0)`. Delete files from dead PIDs. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `os` | stdlib | `os.replace()`, `os.unlink()`, `os.makedirs()`, `os.getpid()`, `os.kill()`, `os.stat()` | Atomic rename, file cleanup, directory creation, PID operations |
| `asyncio` | stdlib | `asyncio.to_thread()`, `asyncio.sleep()`, `asyncio.wait_for()` | Non-blocking file I/O, polling sleep, timeout enforcement |
| `uuid` | stdlib | `uuid.uuid4()`, `uuid.UUID()` for validation | UUID4 generation and validation per IPC-03 |
| `json` | stdlib | `json.dumps()`, `json.loads()` | Request/response serialization |
| `pathlib` | stdlib | `Path` for path construction and manipulation | Clean path API, `Path.home()` for default path |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `errno` | stdlib | `errno.ESRCH`, `errno.EPERM` constants | PID liveness check error handling in sweep |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `asyncio.to_thread()` polling | `watchfiles` (Rust-based fs watcher) | Adds a dependency for single-file detection; polling at 50-100ms is simpler, sufficient for ~10s timeout window, and zero-dependency |
| `json` stdlib | `orjson` | Faster for large payloads, but dump responses are ~1.5MB -- `json` handles this in <50ms. Not needed for M1. |
| Manual polling loop | `asyncio.wait_for()` wrapping a poll coroutine | `wait_for` handles timeout cancellation cleanly; recommended over manual elapsed tracking |

**Installation:**
```bash
# No new dependencies -- all stdlib
```

## Architecture Patterns

### Recommended Project Structure
```
src/omnifocus_operator/bridge/
    _protocol.py       # Bridge protocol (exists)
    _errors.py         # Error hierarchy (exists)
    _in_memory.py      # InMemoryBridge (exists)
    _real.py           # NEW: RealBridge with IPC mechanics
    _factory.py        # Factory (update: wire RealBridge)
    __init__.py        # Package exports (update: export RealBridge)
```

### Pattern 1: Template Method for Bridge Trigger
**What:** `RealBridge` implements the full IPC flow with a `_trigger_omnifocus()` hook. Phase 6 makes this a no-op; Phase 7's `SimulatorBridge` inherits and overrides to no-op explicitly; Phase 8 fills in the URL scheme trigger.

**When to use:** `send_command()` orchestration.

**Example:**
```python
# Source: CONTEXT.md decisions + existing Bridge protocol
class RealBridge:
    """File-based IPC bridge to OmniFocus."""

    def __init__(self, ipc_dir: Path) -> None:
        self._ipc_dir = ipc_dir
        self._pid = os.getpid()

    async def send_command(
        self,
        operation: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        request_id = uuid.uuid4()
        dispatch = f"{request_id}::::{operation}"

        await self._write_request(request_id, dispatch)

        self._trigger_omnifocus(dispatch)

        try:
            response = await asyncio.wait_for(
                self._wait_response(request_id),
                timeout=10.0,
            )
        except TimeoutError:
            await self._cleanup_request(request_id)
            raise BridgeTimeoutError(
                operation=operation,
                timeout_seconds=10.0,
            )

        await self._cleanup_files(request_id)
        return response

    def _trigger_omnifocus(self, dispatch: str) -> None:
        """Hook for triggering OmniFocus. No-op until Phase 8."""
        pass

    # _write_request, _wait_response, _cleanup_* as private methods
```

### Pattern 2: Atomic File Write via os.replace()
**What:** Write content to a `.tmp` file, then atomically move to final path. Readers never see partial content.

**When to use:** Every file write in the IPC layer.

**Example:**
```python
# Source: CPython docs (os.replace is atomic on POSIX)
async def _write_request(self, request_id: uuid.UUID, dispatch: str) -> None:
    filename = f"{self._pid}_{request_id}.request.json"
    final_path = self._ipc_dir / filename
    tmp_path = self._ipc_dir / f"{filename}.tmp"

    content = json.dumps({"dispatch": dispatch})

    def _write() -> None:
        tmp_path.write_text(content, encoding="utf-8")
        os.replace(tmp_path, final_path)

    await asyncio.to_thread(_write)
```

### Pattern 3: Non-Blocking Polling with asyncio.to_thread()
**What:** Poll for response file appearance using `asyncio.sleep()` between checks, with the actual file existence check and read wrapped in `asyncio.to_thread()`.

**When to use:** `_wait_response()` implementation.

**Example:**
```python
# Source: asyncio docs + project PITFALLS.md
async def _wait_response(self, request_id: uuid.UUID) -> dict[str, Any]:
    filename = f"{self._pid}_{request_id}.response.json"
    response_path = self._ipc_dir / filename

    while True:
        exists = await asyncio.to_thread(response_path.exists)
        if exists:
            content = await asyncio.to_thread(
                response_path.read_text, "utf-8"
            )
            return json.loads(content)
        await asyncio.sleep(0.05)  # 50ms poll interval
```

### Pattern 4: PID-Based Orphan Sweep
**What:** On startup, scan IPC directory for files from dead processes. Extract PID from filename, check liveness via `os.kill(pid, 0)`, delete files from dead PIDs.

**When to use:** `RealBridge.__init__()` or a dedicated `async def sweep()` called at startup.

**Example:**
```python
# Source: POSIX kill(2) semantics + CONTEXT.md decisions
import errno
import re

_IPC_FILE_RE = re.compile(r"^(\d+)_[0-9a-f-]+\.(request|response)\.json$")

def _is_pid_alive(pid: int) -> bool:
    """Check if a process is alive via signal 0."""
    try:
        os.kill(pid, 0)
    except OSError as e:
        if e.errno == errno.ESRCH:
            return False  # No such process
        if e.errno == errno.EPERM:
            return True   # Process exists but not owned by us
        raise  # Unexpected error
    return True  # Signal sent successfully

async def sweep_orphaned_files(ipc_dir: Path) -> None:
    """Remove IPC files left by dead processes."""
    def _sweep() -> None:
        if not ipc_dir.exists():
            return
        for entry in ipc_dir.iterdir():
            match = _IPC_FILE_RE.match(entry.name)
            if match:
                pid = int(match.group(1))
                if not _is_pid_alive(pid):
                    entry.unlink(missing_ok=True)

    await asyncio.to_thread(_sweep)
```

### Anti-Patterns to Avoid
- **Blocking file I/O in async functions:** Never call `Path.exists()`, `open()`, `os.stat()`, `os.replace()` directly in an async function. Always wrap in `asyncio.to_thread()`.
- **Using `os.rename()` instead of `os.replace()`:** `os.rename()` does not guarantee atomic overwrite on all platforms. `os.replace()` is the correct function (Python 3.3+).
- **Manual timeout tracking with elapsed counters:** Use `asyncio.wait_for()` which handles cancellation cleanly. Manual `elapsed += interval` drifts due to execution time.
- **Nested subdirectories for requests/responses:** User decided on flat directory with `.request.json`/`.response.json` suffixes. Do not create `requests/` and `responses/` subdirectories.
- **Ignoring EPERM in PID liveness check:** `os.kill(pid, 0)` raises `EPERM` if the process exists but we lack permission. This means the process IS alive -- do not delete its files.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| UUID4 generation | Custom random hex string | `uuid.uuid4()` | Cryptographically secure, RFC 9562 compliant, guaranteed format |
| UUID4 validation | Regex matching | `uuid.UUID(str, version=4)` | Handles all valid UUID4 formats (with/without hyphens), raises `ValueError` on invalid |
| Timeout enforcement | Manual `elapsed += interval` loop | `asyncio.wait_for(coro, timeout=N)` | Handles cancellation, avoids drift, raises `TimeoutError` cleanly |
| Atomic file write | `open()` + `close()` + hope | `write_to_tmp` + `os.replace(tmp, final)` | POSIX guarantees atomicity of rename; no partial reads possible |
| Process liveness check | Reading `/proc/<pid>/` (Linux-only) | `os.kill(pid, 0)` | Cross-platform POSIX, no actual signal sent, handles ESRCH/EPERM correctly |

**Key insight:** Every piece of the IPC engine maps to a well-understood stdlib primitive. The complexity is in composing them correctly (async wrapping, error mapping, cleanup ordering), not in the primitives themselves.

## Common Pitfalls

### Pitfall 1: Partial reads from non-atomic writes
**What goes wrong:** Reader sees incomplete JSON because writer hasn't finished.
**Why it happens:** Direct `Path.write_text()` to the final path is not atomic -- the file is visible and readable while content is still being written.
**How to avoid:** Always write to `.tmp` first, then `os.replace()`. Both the Python IPC layer and the bridge script (already uses `FileWrapper.WritingOptions.Atomic`) follow this pattern.
**Warning signs:** Occasional `json.JSONDecodeError` on response parsing; empty or truncated response files.

### Pitfall 2: Event loop stalls from synchronous file I/O
**What goes wrong:** MCP client reports timeouts even though OmniFocus responded. The response file exists but was never read because the event loop was blocked.
**Why it happens:** `Path.exists()`, `Path.read_text()`, `os.replace()` are all synchronous. On SSD they feel fast, but the MCP stdio transport requires the event loop to stay responsive for JSON-RPC framing.
**How to avoid:** Wrap every file operation in `asyncio.to_thread()`. The project already uses this pattern in `_mtime.py` (line 42).
**Warning signs:** `asyncio` debug mode warnings about slow callbacks; intermittent MCP protocol errors.

### Pitfall 3: Request ID injection via `::::` delimiter
**What goes wrong:** A crafted request ID containing `::::` alters the operation when the bridge script splits on `::::`.
**Why it happens:** The dispatch string `<uuid>::::<operation>` is split by the bridge script. If the UUID portion contains `::::`, it shifts all parts.
**How to avoid:** Validate the request ID as UUID4 format BEFORE constructing the dispatch string. `uuid.uuid4()` always produces valid UUIDs, but if the ID ever comes from external input, validate first.
**Warning signs:** Unexpected operations executed by the bridge script; error responses for operations that were not requested.

### Pitfall 4: Race condition in startup sweep
**What goes wrong:** Sweep deletes files from a still-alive process that just started, because PID reuse happens fast on macOS.
**Why it happens:** Between reading the file's PID prefix and calling `os.kill(pid, 0)`, the process could die and its PID could be reused. However, this race is extremely narrow (PID reuse on macOS requires wrapping the PID space).
**How to avoid:** Accept this as a theoretical risk. In practice, PID reuse is rare within a single sweep. The user explicitly decided against age-based fallback. Worst case: one request from a new process gets cleaned up, and it retries.
**Warning signs:** Extremely unlikely in practice. If it occurs, the affected process would see a missing request file and can retry.

### Pitfall 5: Timeout cleanup leaves orphaned response files
**What goes wrong:** On timeout, the request file is cleaned up, but OmniFocus may still write a response file later. This response becomes an orphan.
**Why it happens:** The URL scheme trigger is fire-and-forget. OmniFocus may be slow but eventually processes the request and writes a response.
**How to avoid:** This is the designed behavior (from CONTEXT.md): "late OmniFocus responses become orphans for next sweep." The startup sweep handles these orphans. No action needed during timeout -- just clean up the request file.
**Warning signs:** Accumulation of `.response.json` files from dead PIDs. Startup sweep resolves this.

### Pitfall 6: `.tmp` file left behind on crash
**What goes wrong:** If the process crashes between writing `.tmp` and calling `os.replace()`, a `.tmp` file is left in the IPC directory.
**Why it happens:** The write-then-replace is a two-step operation.
**How to avoid:** The startup sweep regex can optionally match `.tmp` files and clean them up. Or, since `.tmp` files are never read by the bridge script (it only looks for `.json`), they are harmless.
**Warning signs:** Accumulation of `.tmp` files in the IPC directory over time.

## Code Examples

Verified patterns from official sources and existing codebase:

### Atomic File Write (IPC-01)
```python
# Source: CPython docs (os.replace) + project pattern from _mtime.py
import asyncio
import json
import os
from pathlib import Path

async def write_file_atomic(path: Path, content: str) -> None:
    """Write content to path atomically via tmp + os.replace()."""
    tmp_path = path.with_suffix(path.suffix + ".tmp")

    def _write() -> None:
        tmp_path.write_text(content, encoding="utf-8")
        os.replace(tmp_path, path)

    await asyncio.to_thread(_write)
```

### UUID4 Generation and Validation (IPC-03)
```python
# Source: CPython docs (uuid module)
import uuid

def build_dispatch_string(operation: str) -> tuple[uuid.UUID, str]:
    """Generate a UUID4 request ID and build the dispatch string."""
    request_id = uuid.uuid4()
    dispatch = f"{request_id}::::{operation}"
    return request_id, dispatch

def validate_uuid4(value: str) -> uuid.UUID:
    """Validate a string as UUID4. Raises ValueError if invalid."""
    parsed = uuid.UUID(value, version=4)
    # uuid.UUID(str, version=4) coerces version bits.
    # To strictly validate, compare the string representation:
    if str(parsed) != value.lower():
        raise ValueError(f"Not a valid UUID4: {value!r}")
    return parsed
```

### Response Polling with Timeout (IPC-02, IPC-05)
```python
# Source: CPython docs (asyncio.wait_for, asyncio.to_thread, asyncio.sleep)
import asyncio
from pathlib import Path

async def poll_for_response(
    response_path: Path,
    poll_interval: float = 0.05,
) -> dict:
    """Poll for response file and return parsed JSON."""
    while True:
        exists = await asyncio.to_thread(response_path.exists)
        if exists:
            content = await asyncio.to_thread(
                response_path.read_text, "utf-8"
            )
            return json.loads(content)
        await asyncio.sleep(poll_interval)

# Usage with timeout:
try:
    result = await asyncio.wait_for(
        poll_for_response(response_path),
        timeout=10.0,
    )
except TimeoutError:
    raise BridgeTimeoutError(
        operation=operation,
        timeout_seconds=10.0,
    )
```

### PID Liveness Check (IPC-06)
```python
# Source: POSIX kill(2) semantics, verified via multiple sources
import errno
import os

def is_pid_alive(pid: int) -> bool:
    """Check if process with given PID is alive.

    Uses signal 0 (no actual signal sent) to probe process existence.
    """
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError as e:
        if e.errno == errno.ESRCH:
            return False  # ESRCH = No such process
        if e.errno == errno.EPERM:
            return True   # EPERM = exists but not owned by us
        raise
    return True
```

### Response Validation (Bridge Script Format)
```python
# Source: .research/operatorBridgeScript.js (lines 49-170)
# The bridge script writes: { success: true, data: {...} }
#                        or: { success: false, error: "..." }

def validate_response(raw: dict[str, Any], operation: str) -> dict[str, Any]:
    """Validate bridge response envelope and extract data."""
    if not isinstance(raw, dict):
        raise BridgeProtocolError(
            operation=operation,
            detail=f"Response is not a JSON object: {type(raw).__name__}",
        )
    if raw.get("success") is True:
        return raw.get("data", {})
    error_msg = raw.get("error", "Unknown error from OmniFocus")
    raise BridgeProtocolError(
        operation=operation,
        detail=f"OmniFocus reported error: {error_msg}",
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `os.rename()` for atomic writes | `os.replace()` | Python 3.3 (2012) | `os.replace()` guaranteed atomic overwrite on POSIX; `os.rename()` has platform-dependent behavior for existing dst |
| `aiofiles` for async file I/O | `asyncio.to_thread()` | Python 3.9 (2020) | stdlib solution, no dependency; `aiofiles` is just a thread pool wrapper with extra API surface |
| `loop.run_in_executor()` | `asyncio.to_thread()` | Python 3.9 (2020) | Simpler API, same underlying mechanism (default ThreadPoolExecutor) |
| `watchgod` for file watching | `watchfiles` (Rust backend) | 2022 | `watchgod` deprecated; `watchfiles` is faster but still a dependency. For single-file polling, neither is needed. |

**Deprecated/outdated:**
- `aiofiles`: Not deprecated but unnecessary when `asyncio.to_thread()` is available (Python 3.9+). Adds a dependency for no benefit.
- `loop.run_in_executor()`: Still works but `asyncio.to_thread()` is the modern replacement with simpler API.

## Discretion Recommendations

### Response Detection: Polling (recommended over filesystem watcher)

**Recommendation: Polling with `asyncio.to_thread()` + `asyncio.sleep()`**

Rationale:
1. **Zero dependencies:** Polling uses only stdlib. `watchfiles` would add a Rust-compiled dependency (build complexity, platform wheels).
2. **Single-file detection:** We are watching for exactly one file to appear. Filesystem watchers are designed for monitoring directories with many changes -- overkill here.
3. **Simplicity:** A `while True: exists? read : sleep` loop is 5 lines. A filesystem watcher requires setup, teardown, and async iteration.
4. **Latency is acceptable:** At 50ms poll interval, average response detection latency is 25ms. Within a 10s timeout window, this is negligible.
5. **Proven pattern:** The project already uses `asyncio.to_thread(os.stat, path)` in `_mtime.py`.

**Poll interval: 50ms** (0.05s). This balances responsiveness (25ms average latency) against CPU (20 stat calls/second). The existing architecture research recommended 200ms, but for a 10s timeout window, 50ms is more responsive without meaningful CPU cost on modern SSDs.

### Request File Content: Dispatch string in a JSON envelope (recommended)

**Recommendation: JSON envelope with dispatch string**

```json
{"dispatch": "<uuid>::::<operation>"}
```

Rationale:
1. **Extensibility:** Future write operations (M5) need to include payloads in the request file. A JSON envelope accommodates this naturally: `{"dispatch": "...", "payload": {...}}`.
2. **Debuggability:** JSON files are human-readable and can be inspected with standard tools.
3. **Consistency:** Response files are JSON. Request files being JSON too creates a symmetric protocol.
4. **Note:** For Phase 6 read operations, the bridge script does NOT read request files -- it receives the dispatch string via the URL `arg` parameter. The request file serves as a "ticket" (proof that a request is in-flight) and for future write payloads.

### Response Validation: JSON parse + success/error check (recommended)

**Recommendation: Parse JSON, check `success` boolean, extract `data` or raise on `error`**

Rationale:
1. **The bridge script already returns a structured envelope:** `{ success: true, data: {...} }` or `{ success: false, error: "..." }` (verified in `operatorBridgeScript.js`, lines 49-170).
2. **Error detection:** Without checking `success`, a failed operation (e.g., unknown operation) would silently return `{ success: false, error: "Unknown operation: foo" }` as if it were valid data.
3. **Maps to existing errors:** `success: false` maps naturally to `BridgeProtocolError(detail=error_msg)`.
4. **Pass-through risk:** Raw pass-through would leak the envelope structure to the repository/service layer, creating a leaky abstraction.

### Error Types: Reuse existing BridgeError hierarchy (recommended)

**Recommendation: Reuse `BridgeTimeoutError`, `BridgeProtocolError`, `BridgeConnectionError` from `_errors.py`**

Rationale:
1. **Already designed for this:** `BridgeTimeoutError` has `timeout_seconds`, `BridgeProtocolError` has `detail`, `BridgeConnectionError` has `reason`. All chain via `__cause__`.
2. **Upstream code already handles these:** The repository and service layers catch `BridgeError` subtypes.
3. **No new concepts needed:** IPC timeout = `BridgeTimeoutError`, malformed response = `BridgeProtocolError`, missing IPC dir / OmniFocus not installed = `BridgeConnectionError`.

## Default IPC Path Analysis

The CONTEXT.md specifies: `~/Library/Group Containers/34YW5A73WQ.com.omnigroup.OmniFocus/com.omnigroup.OmniFocus4/ipc/`

**Key facts:**
- `34YW5A73WQ` is the Omni Group's Apple Developer Team ID, standard across all macOS installs (confirmed in CONTEXT.md specifics).
- The Group Containers directory is used by sandboxed apps that share data across app extensions. OmniFocus uses this for sharing between the main app and extensions.
- The bridge script uses `URL.documentsDirectory` which resolves to the app's sandbox Documents directory. For OmniFocus 4, this is within the Group Container.
- The `/ipc/` subdirectory is new (not in the bridge script) -- it separates IPC files from other OmniFocus data.

**Note:** The bridge script currently hardcodes `omnifocus-operator/responses/` as the response directory relative to `URL.documentsDirectory`. The CONTEXT.md decision uses a flat directory with `.request.json` and `.response.json` suffixes. This means **the bridge script will need to be updated to match the new IPC directory and flat naming convention** -- but that is a Phase 8 concern (bridge script integration), not Phase 6.

**For Phase 6:** Use the configurable `ipc_dir` path. Tests will use `tmp_path` (pytest fixture). The default path constant should be defined but will only be exercised in Phase 8 UAT.

**Path construction:**
```python
from pathlib import Path

DEFAULT_IPC_DIR = (
    Path.home()
    / "Library"
    / "Group Containers"
    / "34YW5A73WQ.com.omnigroup.OmniFocus"
    / "com.omnigroup.OmniFocus4"
    / "ipc"
)
```

## Open Questions

1. **Bridge script response directory alignment**
   - What we know: The bridge script writes to `URL.documentsDirectory/omnifocus-operator/responses/<id>.json`. The CONTEXT.md decisions specify a flat directory with `<pid>_<uuid>.response.json` naming.
   - What's unclear: Whether `URL.documentsDirectory` in OmniJS resolves to a path under the Group Container or the app's own sandbox container. Also, the bridge script does not include a PID prefix.
   - Recommendation: This is a Phase 8 concern. Phase 6 builds the Python-side IPC mechanics with the configurable `ipc_dir`. The bridge script will be updated in Phase 8 to match.

2. **Exact subpath within the Group Container**
   - What we know: CONTEXT.md specifies `com.omnigroup.OmniFocus4/ipc/` as the subpath. The `34YW5A73WQ` team ID is confirmed.
   - What's unclear: Whether `com.omnigroup.OmniFocus4` is the actual subdirectory name within the Group Container, or whether OmniFocus uses a different structure. Cannot verify without inspecting an actual macOS system with OmniFocus 4 installed.
   - Recommendation: Define the default path as a constant. Verify in Phase 8 UAT. The `OMNIFOCUS_IPC_DIR` env var override exists precisely for when the default doesn't match reality.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x + pytest-asyncio 1.3+ |
| Config file | `pyproject.toml` ([tool.pytest.ini_options]) |
| Quick run command | `uv run pytest tests/test_real_bridge.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| IPC-01 | Atomic write: .tmp then os.replace() | unit | `uv run pytest tests/test_real_bridge.py::TestAtomicWrite -x` | Wave 0 |
| IPC-02 | All file I/O non-blocking (asyncio.to_thread) | unit | `uv run pytest tests/test_real_bridge.py::TestNonBlockingIO -x` | Wave 0 |
| IPC-03 | Dispatch string format + UUID4 validation | unit | `uv run pytest tests/test_real_bridge.py::TestDispatchProtocol -x` | Wave 0 |
| IPC-04 | IPC dir configurable, defaults to OmniFocus path | unit | `uv run pytest tests/test_real_bridge.py::TestIPCDirectory -x` | Wave 0 |
| IPC-05 | 10s timeout with actionable OmniFocus error | unit | `uv run pytest tests/test_real_bridge.py::TestTimeout -x` | Wave 0 |
| IPC-06 | Startup sweep of orphaned files from dead PIDs | unit | `uv run pytest tests/test_real_bridge.py::TestOrphanSweep -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_real_bridge.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_real_bridge.py` -- covers IPC-01 through IPC-06 (all phase requirements)
- [ ] Test fixtures for tmp IPC directory (`tmp_path` from pytest)
- [ ] Test helper for creating fake IPC files with specific PID prefixes (for sweep tests)

**Testing strategy notes:**
- All tests use `tmp_path` (pytest fixture) as the IPC directory -- never the real OmniFocus sandbox path.
- Timeout tests should use a short timeout (e.g., 0.2s) and no response file to avoid 10s waits.
- PID liveness tests can use `os.getpid()` (alive) and a known-dead PID (e.g., parse from a file created by a subprocess that has exited).
- SAFE-01/SAFE-02: No test touches `RealBridge` with the actual OmniFocus trigger. Phase 6's `RealBridge` has `_trigger_omnifocus()` as a no-op, so it is safe for automated testing.

## Sources

### Primary (HIGH confidence)
- CPython docs: `os.replace()` -- "If successful, the renaming is an atomic operation (POSIX requirement)" ([CPython source](https://github.com/python/cpython/blob/main/Doc/library/os.rst))
- CPython docs: `asyncio.to_thread()` -- offloads sync calls to thread pool ([CPython source](https://github.com/python/cpython/blob/main/Doc/library/asyncio-task.rst))
- CPython docs: `asyncio.wait_for()` -- timeout with cancellation ([CPython source](https://github.com/python/cpython/blob/main/Doc/library/asyncio-task.rst))
- CPython docs: `uuid.uuid4()` -- cryptographically-secure random UUID ([CPython source](https://github.com/python/cpython/blob/main/Doc/library/uuid.rst))
- Bridge script: `.research/operatorBridgeScript.js` -- response envelope format, dispatch string splitting

### Secondary (MEDIUM confidence)
- POSIX `kill(2)` semantics for signal 0: ESRCH = no process, EPERM = exists but no permission ([Stack Overflow](https://stackoverflow.com/questions/568271), [GeeksforGeeks](https://www.geeksforgeeks.org/python/python-os-kill-method/))
- OmniFocus Group Container path with `34YW5A73WQ` team ID (confirmed by user in CONTEXT.md, standard Apple Developer Team ID for Omni Group)
- Polling vs filesystem watcher tradeoffs ([watchfiles docs](https://watchfiles.helpmanual.io/), [SuperFastPython](https://superfastpython.com/asyncio-to_thread/))

### Tertiary (LOW confidence)
- Exact subpath `com.omnigroup.OmniFocus4/ipc/` within Group Container -- user-specified but not independently verified. Will be confirmed in Phase 8 UAT.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all stdlib, well-documented primitives
- Architecture: HIGH -- template method pattern decided by user, IPC flow is straightforward composition
- Pitfalls: HIGH -- atomic writes, async I/O, UUID injection are all documented in project research
- IPC path default: MEDIUM -- team ID confirmed, exact subpath needs UAT verification

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (stable domain, stdlib-only, no fast-moving dependencies)
