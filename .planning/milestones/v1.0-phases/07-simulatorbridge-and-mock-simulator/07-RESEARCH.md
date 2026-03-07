# Phase 7: SimulatorBridge and Mock Simulator - Research

**Researched:** 2026-03-02
**Domain:** File-based IPC bridge subclass + standalone simulator process
**Confidence:** HIGH

## Summary

Phase 7 introduces two components: (1) `SimulatorBridge`, a subclass of `RealBridge` that overrides `_trigger_omnifocus()` to be a permanent no-op, and (2) a standalone mock simulator Python process that watches for `.request.json` files and writes `.response.json` files with realistic OmniFocus data. Together they prove the full file-based IPC pipeline works end-to-end without OmniFocus running.

The implementation is straightforward because nearly all IPC mechanics already exist in `RealBridge` (Phase 6). SimulatorBridge only needs to lock down the trigger method and wire into the factory + server lifespan. The simulator is a standalone sync Python script that polls the IPC directory, matches request files by PID pattern, and writes atomic responses following the same `.tmp` + `os.replace()` convention.

**Primary recommendation:** Subclass `RealBridge` with a no-op `_trigger_omnifocus()`, wire it through `create_bridge("simulator")` + `app_lifespan`, and build the simulator as a `__main__.py`-runnable module that polls for request files and responds with static realistic data.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Simulator data fidelity**: Realistic data covering common OmniFocus patterns: inbox tasks, tasks in projects, flagged items, some with due dates, a few completed, tags assigned, nested folders. Representative of a typical OmniFocus power user's database. Data is static between requests (same snapshot every time dump_all is called).
- **Simulator invocation & lifecycle**: Runs forever until Ctrl+C (daemon-style, matching how real OmniFocus behaves). Started as a subprocess in pytest integration tests (pytest fixture manages start/stop). Verbose logging to stderr by default (each request/response cycle logged). Prints config summary to stderr on startup (IPC dir, fail mode, delay, etc.).
- **Error simulation modes**: Supports configurable failure modes via CLI flags: `--fail-mode timeout` (receives request but never writes response), `--fail-mode error` (writes `{"success": false, "error": "simulated error"}` response), `--fail-mode malformed` (writes invalid JSON to response file). `--fail-after N` (first N requests succeed, then failure mode activates). `--delay <seconds>` (delays all responses by N seconds, independent of fail mode).
- **Bridge architecture**: SimulatorBridge subclasses RealBridge with a permanently locked no-op `_trigger_omnifocus()`. Lives in `bridge/_simulator.py`. Uses ConstantMtimeSource (data is static; cache invalidation already tested in Phase 4). Factory wiring: `create_bridge("simulator")` returns SimulatorBridge instance.

### Claude's Discretion
- Data source format (hardcoded dict vs JSON fixture file)
- Exact simulator entry point pattern (module `__main__` vs script)
- Simulator polling interval for watching request files
- Integration test fixture implementation details (subprocess management, readiness detection)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BRDG-03 | SimulatorBridge uses file-based IPC without URL scheme trigger | SimulatorBridge subclasses RealBridge, overrides `_trigger_omnifocus()` as permanent no-op. All IPC mechanics inherited from Phase 6. Factory + lifespan wiring researched. |
| TEST-01 | Mock simulator is a standalone Python script that watches for requests and writes test responses | Simulator as `__main__.py` module, uses `argparse` for CLI flags, polls IPC directory, writes atomic responses. Subprocess fixture pattern researched. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `os` / `pathlib` | stdlib | File I/O, atomic writes, directory polling | Already used throughout RealBridge; simulator mirrors the same patterns |
| `argparse` | stdlib | CLI flag parsing for simulator | Standard for Python CLIs; no external dep needed for `--fail-mode`, `--delay`, `--fail-after` flags |
| `json` | stdlib | Request parsing, response serialization | Already used in RealBridge IPC |
| `logging` | stdlib | Stderr logging for simulator | Already used in server; consistent logging approach |
| `subprocess` | stdlib | Pytest fixture spawns simulator process | Standard for process lifecycle management in test fixtures |
| `time` | stdlib | `time.sleep()` for polling interval and `--delay` flag | Simulator is sync (no asyncio); `time.sleep()` is the correct primitive |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | >=9.0.2 | Test framework | Integration tests for SimulatorBridge + simulator |
| `pytest-asyncio` | >=1.3.0 | Async test support | SimulatorBridge tests (send_command is async) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hardcoded dict for simulator data | JSON fixture file | JSON file is more readable/editable but adds file I/O in simulator. **Recommendation: Hardcoded dict** -- keeps simulator self-contained, no file path resolution needed, and the data only needs to exist in one place. |
| `__main__.py` module for simulator | Standalone script file | `__main__.py` enables `python -m omnifocus_operator.simulator` but adds a package. **Recommendation: `__main__.py` approach** -- place simulator under `src/omnifocus_operator/simulator/__main__.py` so it is runnable via `python -m omnifocus_operator.simulator`. This follows the project's existing `__main__.py` pattern and works cleanly with `sys.executable` in subprocess calls. |
| Polling with `time.sleep()` | `watchdog` / `inotify` | Event-based watching avoids polling overhead but adds a dependency. **Recommendation: Polling** -- simulator is a dev/test tool, not production. 100ms polling is plenty responsive and matches the 50ms poll in `RealBridge._wait_response()`. |

**No additional dependencies needed.** Everything is stdlib + existing dev dependencies.

## Architecture Patterns

### Recommended Project Structure
```
src/omnifocus_operator/
├── bridge/
│   ├── _simulator.py         # SimulatorBridge class (NEW)
│   ├── _real.py              # RealBridge (existing, parent class)
│   ├── _factory.py           # create_bridge() (modify: add "simulator" case)
│   ├── _protocol.py          # Bridge protocol (unchanged)
│   ├── _in_memory.py         # InMemoryBridge (unchanged)
│   ├── _errors.py            # Error types (unchanged)
│   └── __init__.py           # Exports (modify: add SimulatorBridge)
├── simulator/
│   ├── __init__.py           # Package marker
│   ├── __main__.py           # Entry point: python -m omnifocus_operator.simulator
│   └── _data.py              # Realistic static snapshot data
├── server/
│   └── _server.py            # app_lifespan (modify: add "simulator" case)
└── ...
tests/
├── test_simulator_bridge.py  # SimulatorBridge unit + integration tests (NEW)
└── ...
```

### Pattern 1: SimulatorBridge as Minimal RealBridge Subclass
**What:** SimulatorBridge inherits all of RealBridge's IPC mechanics and only overrides `_trigger_omnifocus()` to be a permanent no-op.
**When to use:** When you want the full IPC pipeline but without the URL scheme trigger.
**Example:**
```python
# bridge/_simulator.py
"""SimulatorBridge -- file-based IPC bridge for testing with mock simulator."""

from __future__ import annotations

from pathlib import Path

from omnifocus_operator.bridge._real import RealBridge


class SimulatorBridge(RealBridge):
    """Bridge that uses file IPC without triggering OmniFocus.

    Subclasses RealBridge with a permanently locked no-op
    _trigger_omnifocus(). Designed to work with the mock simulator
    process that watches for request files independently.
    """

    def _trigger_omnifocus(self, dispatch: str) -> None:
        """No-op -- the mock simulator watches for request files directly."""
```

### Pattern 2: Subprocess Fixture with Readiness Detection
**What:** A pytest fixture that spawns the simulator as a subprocess, waits until it is ready (by checking for a sentinel file or parsing stderr output), and tears it down after the test.
**When to use:** Integration tests that need the simulator running as a separate process.
**Example:**
```python
# tests/test_simulator_bridge.py (fixture pattern)
import subprocess
import sys
import time
from pathlib import Path

import pytest


@pytest.fixture
def simulator_process(tmp_path: Path):
    """Start mock simulator subprocess, yield it, then terminate."""
    proc = subprocess.Popen(
        [sys.executable, "-m", "omnifocus_operator.simulator",
         "--ipc-dir", str(tmp_path)],
        stderr=subprocess.PIPE,
        text=True,
    )
    # Wait for readiness: simulator prints "Ready" or similar to stderr
    _wait_for_ready(proc)
    yield proc
    proc.terminate()
    proc.wait(timeout=5)


def _wait_for_ready(proc, timeout=5.0):
    """Block until simulator prints readiness line to stderr."""
    import select
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"Simulator exited early: {proc.returncode}")
        # Read one line from stderr (non-blocking via select or timeout)
        line = proc.stderr.readline()
        if "ready" in line.lower():
            return
    raise TimeoutError("Simulator did not become ready")
```

### Pattern 3: Simulator Request-Response Loop
**What:** The simulator polls the IPC directory for `.request.json` files, parses the dispatch string, generates a response, and writes it atomically.
**When to use:** This is the core simulator loop.
**Example:**
```python
# simulator/__main__.py (core loop, simplified)
def _handle_request(request_path: Path, data: dict, args) -> None:
    """Parse request, generate response, write atomically."""
    content = json.loads(request_path.read_text(encoding="utf-8"))
    dispatch = content["dispatch"]
    uuid_str, operation = dispatch.split("::::")

    # Extract PID from filename: <pid>_<uuid>.request.json
    pid = request_path.name.split("_")[0]
    response_path = request_path.parent / f"{pid}_{uuid_str}.response.json"

    if args.delay:
        time.sleep(args.delay)

    if _should_fail(args):
        _write_failure(response_path, args.fail_mode)
    else:
        _write_success(response_path, data)


def _write_success(response_path: Path, data: dict) -> None:
    """Write success response atomically."""
    tmp_path = response_path.with_suffix(".json.tmp")
    content = json.dumps({"success": True, "data": data})
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, response_path)
```

### Pattern 4: Factory + Lifespan Wiring
**What:** Wire `create_bridge("simulator")` and update `app_lifespan` to handle the simulator bridge type with `ConstantMtimeSource`.
**When to use:** Server startup with `OMNIFOCUS_BRIDGE=simulator`.
**Example:**
```python
# bridge/_factory.py -- "simulator" case
case "simulator":
    import os
    from omnifocus_operator.bridge._simulator import SimulatorBridge
    from omnifocus_operator.bridge._real import DEFAULT_IPC_DIR

    ipc_dir_str = os.environ.get("OMNIFOCUS_IPC_DIR")
    ipc_dir = Path(ipc_dir_str) if ipc_dir_str else DEFAULT_IPC_DIR
    return SimulatorBridge(ipc_dir=ipc_dir)

# server/_server.py -- lifespan update
if bridge_type in ("inmemory", "simulator"):
    mtime_source = ConstantMtimeSource()
else:
    msg = f"FileMtimeSource path not configured for bridge type: {bridge_type}"
    raise NotImplementedError(msg)
```

### Anti-Patterns to Avoid
- **Inheriting and overriding `send_command()`:** Don't reimplement the IPC flow. SimulatorBridge should ONLY override `_trigger_omnifocus()`. The entire request/response cycle is inherited.
- **Making the simulator async:** The simulator is a standalone sync process. Using asyncio adds complexity with zero benefit since it just polls a directory and writes files.
- **Hardcoding PID matching in the simulator:** The simulator should respond to ANY `.request.json` file it finds, not filter by PID. Multiple bridge instances could be testing simultaneously, and the simulator should serve them all.
- **Using `os.rename()` instead of `os.replace()`:** `os.replace()` is atomic on macOS; `os.rename()` is not cross-platform safe (project decision from research highlights).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic file writes | Custom fsync+rename logic | `.tmp` + `os.replace()` pattern from RealBridge | Already proven in Phase 6; consistency matters for IPC |
| CLI argument parsing | Manual `sys.argv` parsing | `argparse` | Handles `--fail-mode`, `--delay`, `--fail-after` cleanly with type validation |
| Process lifecycle in tests | Manual `Popen` + `time.sleep()` | Readiness-based fixture (readline from stderr) | Sleep-based detection is flaky; readiness detection is deterministic |
| Response file naming | Custom naming scheme | Same `<pid>_<uuid>.response.json` convention | Must match what `RealBridge._wait_response()` expects |

**Key insight:** The simulator must be protocol-compatible with `RealBridge` -- it reads the same file format, uses the same naming convention, and writes the same response envelope. Any deviation breaks the IPC contract.

## Common Pitfalls

### Pitfall 1: Race Between Simulator Startup and Test Execution
**What goes wrong:** Test sends a request before the simulator is ready to process it, causing a timeout.
**Why it happens:** `subprocess.Popen()` returns immediately; the simulator needs time to initialize and start polling.
**How to avoid:** Simulator prints a "Ready: watching <ipc_dir>" line to stderr on startup. The pytest fixture reads stderr line-by-line until it sees the readiness marker before yielding the fixture.
**Warning signs:** Flaky timeout errors that pass on retry.

### Pitfall 2: Simulator Reads Partially-Written Request Files
**What goes wrong:** Simulator reads a `.request.json` file while the bridge is still writing it, getting truncated JSON.
**Why it happens:** Bridge writes via `.tmp` + `os.replace()`, but if the simulator checks between `write_text()` and `os.replace()`, it would see the `.tmp` file.
**How to avoid:** Simulator ONLY watches for files matching `*.request.json` (not `.tmp` files). Since `os.replace()` is atomic, the `.request.json` file appears fully-formed.
**Warning signs:** `json.JSONDecodeError` in the simulator.

### Pitfall 3: Response File PID Mismatch
**What goes wrong:** Simulator writes response with wrong PID prefix; bridge never finds it.
**Why it happens:** The response file must be `<pid>_<uuid>.response.json` where PID matches the requesting process. The simulator must extract the PID from the request filename, NOT use its own PID.
**How to avoid:** Parse PID from request filename: `request_path.name.split("_")[0]`. Use the SAME PID in the response filename.
**Warning signs:** `BridgeTimeoutError` despite simulator logging that it wrote a response.

### Pitfall 4: Leftover Request Files Between Tests
**What goes wrong:** A request file from a previous test is still present when a new test starts; the simulator processes the stale request.
**Why it happens:** Test teardown did not clean up, or bridge timeout left orphaned files.
**How to avoid:** Use `tmp_path` for each test (pytest creates unique temp dirs). The simulator only watches the specific IPC dir it was started with. Also: `sweep_orphaned_files()` runs on startup via lifespan.
**Warning signs:** Tests interfere with each other; simulator processes unexpected requests.

### Pitfall 5: Simulator stderr Buffering Blocks Readiness Detection
**What goes wrong:** The fixture's `readline()` blocks forever because Python buffers stderr output in the subprocess.
**Why it happens:** Python uses block buffering for pipes by default (not line buffering).
**How to avoid:** Either (a) use `PYTHONUNBUFFERED=1` env var when spawning the simulator, or (b) call `sys.stderr.reconfigure(line_buffering=True)` in the simulator at startup, or (c) use `sys.stderr.flush()` after each log line.
**Warning signs:** Fixture hangs waiting for "ready" line that was already printed but buffered.

### Pitfall 6: Simulator Process Leaks on Test Failure
**What goes wrong:** If a test fails or times out, the simulator process is not terminated, leaving orphan processes.
**Why it happens:** pytest fixture teardown may not run if the test process crashes hard.
**How to avoid:** Use `proc.terminate()` in fixture teardown (which runs even on test failure). Also set `proc.wait(timeout=5)` to avoid blocking. Consider `atexit` as last resort.
**Warning signs:** `ps aux | grep simulator` shows leftover processes after test runs.

## Code Examples

### SimulatorBridge Implementation
```python
# bridge/_simulator.py
"""SimulatorBridge -- file-based IPC bridge for testing with mock simulator."""

from __future__ import annotations

from pathlib import Path

from omnifocus_operator.bridge._real import RealBridge


class SimulatorBridge(RealBridge):
    """Bridge that uses file IPC without triggering OmniFocus.

    Identical to RealBridge except _trigger_omnifocus() is a permanent
    no-op.  Designed to pair with the mock simulator process
    (``python -m omnifocus_operator.simulator``).
    """

    def _trigger_omnifocus(self, dispatch: str) -> None:
        """No-op -- simulator watches for request files independently."""
```

### Factory Wiring
```python
# In bridge/_factory.py, replace the "simulator" case:
case "simulator":
    import os
    from omnifocus_operator.bridge._real import DEFAULT_IPC_DIR
    from omnifocus_operator.bridge._simulator import SimulatorBridge

    ipc_dir_str = os.environ.get("OMNIFOCUS_IPC_DIR")
    ipc_dir = Path(ipc_dir_str) if ipc_dir_str else DEFAULT_IPC_DIR
    return SimulatorBridge(ipc_dir=ipc_dir)
```

### Lifespan Update
```python
# In server/_server.py, update the mtime_source selection:
if bridge_type in ("inmemory", "simulator"):
    mtime_source = ConstantMtimeSource()
else:
    msg = f"FileMtimeSource path not configured for bridge type: {bridge_type}"
    raise NotImplementedError(msg)
```

### Simulator Entry Point
```python
# simulator/__main__.py
"""Mock OmniFocus simulator -- standalone process for integration testing."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

logger = logging.getLogger("omnifocus_simulator")

_REQUEST_RE = re.compile(r"^\d+_[0-9a-f-]+\.request\.json$")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Mock OmniFocus simulator for integration testing",
    )
    parser.add_argument(
        "--ipc-dir", type=Path, required=True,
        help="Directory to watch for IPC request files",
    )
    parser.add_argument(
        "--fail-mode", choices=["timeout", "error", "malformed"],
        default=None,
        help="Failure simulation mode",
    )
    parser.add_argument(
        "--fail-after", type=int, default=None,
        help="Number of successful requests before failure mode activates",
    )
    parser.add_argument(
        "--delay", type=float, default=0.0,
        help="Delay in seconds before writing response",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )
    # Ensure line-buffered stderr for readiness detection
    sys.stderr.reconfigure(line_buffering=True)

    args.ipc_dir.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Config: ipc_dir=%s fail_mode=%s fail_after=%s delay=%s",
        args.ipc_dir, args.fail_mode, args.fail_after, args.delay,
    )
    logger.info("Ready: watching %s", args.ipc_dir)

    _run_loop(args)


def _run_loop(args) -> None:
    from omnifocus_operator.simulator._data import SIMULATOR_SNAPSHOT
    request_count = 0
    seen: set[str] = set()

    while True:
        for entry in args.ipc_dir.iterdir():
            if entry.name in seen:
                continue
            if not _REQUEST_RE.match(entry.name):
                continue
            seen.add(entry.name)
            request_count += 1
            logger.info("Request #%d: %s", request_count, entry.name)
            _handle_request(entry, SIMULATOR_SNAPSHOT, args, request_count)

        time.sleep(0.1)  # 100ms polling interval


if __name__ == "__main__":
    main()
```

### Realistic Simulator Data (Recommendation: hardcoded dict)
```python
# simulator/_data.py
"""Static realistic OmniFocus snapshot for the mock simulator."""

SIMULATOR_SNAPSHOT: dict = {
    "tasks": [
        {
            "id": "task-inbox-001",
            "name": "Buy groceries for the week",
            "note": "Milk, eggs, bread, avocados",
            "inInbox": True,
            "completed": False,
            "flagged": False,
            "effectiveFlagged": False,
            # ... all 32 fields
        },
        # ... ~8-12 tasks covering: inbox, project tasks, flagged, due dates,
        # completed, with tags, nested
    ],
    "projects": [
        # 2-3 projects: one active, one with sequential tasks
    ],
    "tags": [
        # 3-4 tags: work, personal, errands, waiting
    ],
    "folders": [
        # 2 folders: Work, Personal (nested structure)
    ],
    "perspectives": [
        # 3 perspectives: Inbox (builtin), Forecast (builtin), one custom
    ],
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `os.rename()` for atomic writes | `os.replace()` | Python 3.3+ | `os.replace()` atomically replaces on macOS; `os.rename()` raises `FileExistsError` on Windows |
| Sleep-based subprocess readiness | Readiness line detection on stderr | Standard pattern | Deterministic startup detection; eliminates flaky timing in CI |
| `print()` to stderr for logging | `logging` module | Python convention | Structured logging, configurable levels, consistent with server logging |

**Deprecated/outdated:**
- None relevant. All patterns use stdlib features stable since Python 3.6+.

## Open Questions

1. **Exact simulator data richness**
   - What we know: Needs to cover inbox tasks, project tasks, flagged items, due dates, completed tasks, tags, nested folders. User wants "representative of a typical power user."
   - What's unclear: Exact number of entities and field coverage. Does every optional field need a non-None example?
   - Recommendation: Include 8-12 tasks, 2-3 projects, 3-4 tags, 2 folders, 3 perspectives. Cover all nullable field types with at least one non-None example. This is a Claude's Discretion area -- planner can scope it.

2. **Simulator `--fail-after` interaction with `seen` set**
   - What we know: `--fail-after N` means first N requests succeed, then failure mode activates.
   - What's unclear: Does a re-polled stale request count toward N? (It should not, since `seen` prevents re-processing.)
   - Recommendation: Count is based on requests actually processed (post-dedup). Document this behavior.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_simulator_bridge.py -x` |
| Full suite command | `uv run pytest --tb=short -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BRDG-03 | SimulatorBridge sends command via file IPC, no URL trigger | unit | `uv run pytest tests/test_simulator_bridge.py::TestSimulatorBridgeUnit -x` | Wave 0 |
| BRDG-03 | `create_bridge("simulator")` returns SimulatorBridge | unit | `uv run pytest tests/test_simulator_bridge.py::TestFactory -x` | Wave 0 |
| BRDG-03 | SimulatorBridge `_trigger_omnifocus()` is no-op | unit | `uv run pytest tests/test_simulator_bridge.py::TestTriggerNoOp -x` | Wave 0 |
| BRDG-03 | Server lifespan handles "simulator" bridge type | unit | `uv run pytest tests/test_simulator_bridge.py::TestLifespan -x` | Wave 0 |
| BRDG-03 | SimulatorBridge inherits `ipc_dir` property (sweep compat) | unit | `uv run pytest tests/test_simulator_bridge.py::TestIpcDirInheritance -x` | Wave 0 |
| TEST-01 | Simulator starts and becomes ready | integration | `uv run pytest tests/test_simulator_bridge.py::TestSimulatorProcess -x` | Wave 0 |
| TEST-01 | Full round-trip: bridge -> file -> simulator -> response -> bridge | integration | `uv run pytest tests/test_simulator_bridge.py::TestEndToEnd -x` | Wave 0 |
| TEST-01 | Simulator `--fail-mode error` returns error response | integration | `uv run pytest tests/test_simulator_bridge.py::TestErrorSimulation -x` | Wave 0 |
| TEST-01 | Simulator `--fail-mode malformed` writes invalid JSON | integration | `uv run pytest tests/test_simulator_bridge.py::TestErrorSimulation -x` | Wave 0 |
| TEST-01 | Simulator `--fail-mode timeout` never responds | integration | `uv run pytest tests/test_simulator_bridge.py::TestErrorSimulation -x` | Wave 0 |
| TEST-01 | Simulator `--fail-after N` transitions from success to failure | integration | `uv run pytest tests/test_simulator_bridge.py::TestFailAfter -x` | Wave 0 |
| TEST-01 | Simulator `--delay` delays response | integration | `uv run pytest tests/test_simulator_bridge.py::TestDelay -x` | Wave 0 |
| TEST-01 | MCP server with SimulatorBridge returns simulator data via `list_all` | integration | `uv run pytest tests/test_simulator_bridge.py::TestMcpIntegration -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_simulator_bridge.py -x`
- **Per wave merge:** `uv run pytest --tb=short -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_simulator_bridge.py` -- covers BRDG-03 and TEST-01 (unit + integration tests)
- [ ] `src/omnifocus_operator/bridge/_simulator.py` -- SimulatorBridge class
- [ ] `src/omnifocus_operator/simulator/__init__.py` -- simulator package marker
- [ ] `src/omnifocus_operator/simulator/__main__.py` -- simulator entry point
- [ ] `src/omnifocus_operator/simulator/_data.py` -- static snapshot data

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `bridge/_real.py` (RealBridge implementation, IPC mechanics, file naming)
- Codebase analysis: `bridge/_factory.py` (factory pattern, lazy imports, env var handling)
- Codebase analysis: `server/_server.py` (app_lifespan, bridge type handling, mtime source selection)
- Codebase analysis: `tests/test_real_bridge.py` (test patterns for IPC, subprocess helpers, response simulation)
- Codebase analysis: `tests/test_server.py` (in-process MCP integration test patterns)
- Python docs: `os.replace()` atomicity, `argparse`, `subprocess.Popen`, `logging`

### Secondary (MEDIUM confidence)
- [Simon Willison's TIL: Subprocess server in pytest](https://til.simonwillison.net/pytest/subprocess-server) -- subprocess fixture patterns with readiness detection

### Tertiary (LOW confidence)
- None -- all findings verified against codebase or stdlib docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all stdlib, no new dependencies
- Architecture: HIGH -- SimulatorBridge is a minimal subclass of existing proven code; patterns directly follow RealBridge
- Pitfalls: HIGH -- all pitfalls identified from concrete codebase analysis (IPC naming, atomic writes, stderr buffering)

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (stable -- stdlib only, no version churn)
