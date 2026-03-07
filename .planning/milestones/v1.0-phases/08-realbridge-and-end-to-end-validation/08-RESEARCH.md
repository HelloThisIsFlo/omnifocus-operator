# Phase 8: RealBridge and End-to-End Validation - Research

**Researched:** 2026-03-02
**Domain:** Production bridge implementation, safety guardrails, test coverage audit
**Confidence:** HIGH

## Summary

Phase 8 completes the Milestone 1 foundation by implementing the final missing piece: the production trigger in `RealBridge._trigger_omnifocus()`, wiring `FileMtimeSource` into `app_lifespan` for the `"real"` bridge type, enforcing SAFE-01/SAFE-02 safety guardrails, auditing and filling test gaps across all layers, and establishing the UAT framework for manual testing against live OmniFocus.

The implementation surface is small and well-constrained. RealBridge already has the full IPC pipeline (atomic writes, async polling, dispatch protocol, timeout, orphan sweep). SimulatorBridge proves the template method pattern works. The only production code change is implementing `_trigger_omnifocus()` with `subprocess.run(["open", "-g", url])` and wiring `FileMtimeSource` in `app_lifespan`. The bulk of the phase is safety enforcement (CI grep + runtime guard in factory) and test coverage completion.

**Primary recommendation:** Implement the URL scheme trigger, wire FileMtimeSource, add safety guardrails at factory + CI level, audit and fill test gaps, create the UAT framework with a read-only validation script.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- CI check + runtime guard -- belt and suspenders approach
- Runtime guard at **factory level**: `create_bridge("real")` refuses when `PYTEST_CURRENT_TEST` is set, raising a clear error directing to `inmemory` or `simulator`
- CI step that greps test files for RealBridge usage and fails the build if found
- Update CLAUDE.md with explicit SAFE-01/02 rules so AI agents get the warning upfront
- Both pytest `testpaths` config and CI pipeline exclude the `uat/` directory
- Dedicated `uat/` folder at project root (alongside `src/` and `tests/`)
- UAT scripts are Python scripts run via `uv run python uat/<script>.py`
- Concept document (`uat/README.md`) explaining the UAT folder philosophy
- For Phase 8: read-only UAT script that connects to real OmniFocus, calls `dump_all`, and pretty-prints/validates the response
- Excluded from pytest discovery AND CI pipeline (double protection)
- Agents must NEVER run UAT scripts -- human-only, enforced by convention and CI exclusion
- Error messages are agent-optimized with structured context
- Specific error types for different failure modes (timeout, protocol, connection)
- Fail fast, no retry: 10s timeout then immediate error
- Gap audit + fill: audit existing tests, identify missing coverage, fill gaps
- TEST-02: Claude determines single E2E smoke test vs additional layer integration tests
- TEST-03: verify each layer has tests, fill any discovered gaps
- SAFE-01 enforcement meta-test: Claude decides whether pytest meta-test or CI-only grep script

### Claude's Discretion
- Exact CI implementation approach for the safety grep check (standalone script vs pytest conftest hook)
- Whether the SAFE-01 enforcement is a meta-test in pytest or a CI-only script
- E2E pipeline test granularity (single smoke test vs smoke + layer integration tests)
- URL scheme trigger implementation details (`subprocess.run(["open", url])` vs alternatives)
- FileMtimeSource path configuration for the "real" bridge type in app_lifespan
- Error message exact wording and structure

### Deferred Ideas (OUT OF SCOPE)
- UAT framework for write operations (sandboxed test data setup/teardown with confirmation prompts) -- future milestones
- Retry/resilience logic for bridge communication -- tracked as "Production hardening"
- Agent-facing structured error responses (JSON error objects vs string messages)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BRDG-04 | RealBridge uses file-based IPC with `omnifocus:///omnijs-run` URL scheme trigger | URL scheme trigger implementation via `subprocess.run(["open", "-g", url])`. See Architecture Patterns for the exact code pattern. The `-g` flag opens in background without stealing focus. |
| SAFE-01 | No automated test, CI pipeline, or agent execution touches the RealBridge -- all automated testing uses InMemoryBridge or SimulatorBridge exclusively | Factory-level runtime guard checking `PYTEST_CURRENT_TEST` env var + CI grep step. See Safety Guardrail Patterns section. |
| SAFE-02 | RealBridge interaction is manual UAT only, performed by the user against their live OmniFocus database | UAT folder structure with read-only validation script. `uat/` excluded from pytest discovery and CI. See UAT Framework section. |
| TEST-02 | Full pipeline is testable via InMemoryBridge with no OmniFocus dependency | Existing `test_server.py::TestARCH01ThreeLayerArchitecture` already tests MCP -> Service -> Repository -> Bridge -> structured data pipeline via InMemoryBridge. May need minor augmentation. See Test Coverage Audit. |
| TEST-03 | pytest + pytest-asyncio test suite with tests for each layer | All 5 layers have existing tests. Gap audit identifies coverage gaps. See Test Coverage Audit. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| subprocess (stdlib) | 3.12 | `open -g` URL scheme trigger | macOS `open` command is the canonical way to open URL schemes; `-g` flag prevents focus stealing |
| os (stdlib) | 3.12 | `PYTEST_CURRENT_TEST` env var detection for safety guard | Standard pytest-set env var, documented in pytest docs |
| pytest | >=9.0.2 | Test framework, already configured | Project standard, already in dev dependencies |
| pytest-asyncio | >=1.3.0 | Async test support | Project standard, already configured with `asyncio_mode = "auto"` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| urllib.parse (stdlib) | 3.12 | URL encoding of script content for omnijs-run URL | Needed to percent-encode JavaScript snippet in URL scheme parameter |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `subprocess.run(["open", "-g", url])` | `webbrowser.open(url)` | `webbrowser` works but can't pass `-g` flag. `subprocess` with `open -g` is the established pattern in this project's research and avoids focus stealing. |
| `subprocess.run` (blocking) | `subprocess.Popen` (fire-and-forget) | `subprocess.run` blocks until `open` exits, but `open` returns immediately after dispatching to Launch Services. Blocking behavior is desirable -- confirms `open` succeeded (exit code 0). |

**No new dependencies.** Everything needed is stdlib + existing dev deps.

## Architecture Patterns

### Recommended Changes to Existing Structure
```
src/omnifocus_operator/
├── bridge/
│   ├── _real.py          # Implement _trigger_omnifocus() (BRDG-04)
│   ├── _factory.py       # Add PYTEST_CURRENT_TEST guard (SAFE-01)
│   └── _errors.py        # Enhance error messages (agent-optimized)
├── server/
│   └── _server.py        # Wire FileMtimeSource for bridge_type=="real" (app_lifespan)
uat/
├── README.md             # UAT philosophy document (SAFE-02)
├── test_read_only.py     # Manual read-only validation script
tests/
├── (existing tests)      # Gap audit + fill (TEST-02, TEST-03)
.github/workflows/
└── ci.yml                # Add safety grep step + uat exclusion
pyproject.toml            # Add testpaths exclusion for uat/
CLAUDE.md                 # Add SAFE-01/02 rules
```

### Pattern 1: URL Scheme Trigger Implementation
**What:** Implement `_trigger_omnifocus()` in `RealBridge` to trigger OmniFocus via the macOS `open` command with the `omnifocus:///omnijs-run` URL scheme.
**When to use:** Production bridge communicating with live OmniFocus.
**Example:**
```python
# Source: .research/MILESTONE-1.md, .planning/research/ARCHITECTURE.md
import subprocess
import urllib.parse

def _trigger_omnifocus(self, dispatch: str) -> None:
    """Trigger OmniFocus via URL scheme to process the IPC request."""
    # The bridge script in OmniFocus reads the dispatch string from the
    # URL arg parameter, finds the corresponding request file, and writes
    # the response file.
    script = "/* bridge script invocation */"
    encoded_script = urllib.parse.quote(script, safe="")
    encoded_arg = urllib.parse.quote(dispatch, safe="")
    url = f"omnifocus:///omnijs-run?script={encoded_script}&arg={encoded_arg}"
    subprocess.run(
        ["open", "-g", url],
        check=True,
        capture_output=True,
    )
```

**Key details:**
- `-g` flag: Opens in background without stealing focus (documented in Architecture research)
- `check=True`: Raises `subprocess.CalledProcessError` if `open` fails (e.g., OmniFocus not installed)
- `capture_output=True`: Suppresses stdout/stderr from `open` command
- `subprocess.run` is synchronous but `open` returns immediately after dispatching to Launch Services -- the actual execution is async inside OmniFocus
- The `_trigger_omnifocus` method is synchronous (not async) in the existing RealBridge class -- keep it synchronous since `open` returns immediately

**Error handling for BridgeConnectionError:**
The trigger should catch `subprocess.CalledProcessError` and `FileNotFoundError` and raise `BridgeConnectionError` with agent-friendly messages:
```python
try:
    subprocess.run(["open", "-g", url], check=True, capture_output=True)
except FileNotFoundError:
    raise BridgeConnectionError(
        operation=dispatch.split("::::")[1] if "::::" in dispatch else "unknown",
        reason="'open' command not found. This server requires macOS.",
    ) from None
except subprocess.CalledProcessError as exc:
    raise BridgeConnectionError(
        operation=dispatch.split("::::")[1] if "::::" in dispatch else "unknown",
        reason=f"Failed to trigger OmniFocus (exit code {exc.returncode}). "
               "Is OmniFocus installed?",
    ) from None
```

### Pattern 2: Factory-Level Safety Guard (SAFE-01)
**What:** `create_bridge("real")` checks for `PYTEST_CURRENT_TEST` env var and refuses with a clear error.
**When to use:** Prevent any automated test from accidentally instantiating RealBridge.
**Example:**
```python
# In _factory.py, inside the "real" case before creating the bridge:
case "real":
    import os

    if os.environ.get("PYTEST_CURRENT_TEST"):
        msg = (
            "RealBridge is not available during automated testing "
            "(PYTEST_CURRENT_TEST is set). "
            "Use OMNIFOCUS_BRIDGE=inmemory or OMNIFOCUS_BRIDGE=simulator instead."
        )
        raise RuntimeError(msg)

    from omnifocus_operator.bridge._real import DEFAULT_IPC_DIR, RealBridge
    # ... rest of factory code
```

**Why `PYTEST_CURRENT_TEST`:** pytest sets this env var automatically during test execution. It includes the test node ID (e.g., `tests/test_foo.py::test_bar (setup)`). Checking for its presence is the standard way to detect "am I running inside pytest?" without importing pytest.

### Pattern 3: FileMtimeSource Wiring in app_lifespan
**What:** Replace the `NotImplementedError` for `bridge_type == "real"` with actual `FileMtimeSource` wiring.
**When to use:** Production startup with real OmniFocus.
**Example:**
```python
# In _server.py app_lifespan, replacing the else branch:
if bridge_type in ("inmemory", "simulator"):
    mtime_source = ConstantMtimeSource()
else:
    from omnifocus_operator.repository import FileMtimeSource

    # Default: OmniFocus 4 database bundle path
    # The .ofocus bundle's mtime changes on every sync/edit
    default_ofocus_path = str(
        Path.home()
        / "Library"
        / "Group Containers"
        / "34YW5A73WQ.com.omnigroup.OmniFocus"
        / "com.omnigroup.OmniFocus4"
        / "OmniFocus.ofocus"
    )
    ofocus_path = os.environ.get("OMNIFOCUS_OFOCUS_PATH", default_ofocus_path)
    mtime_source = FileMtimeSource(path=ofocus_path)
```

**Key details:**
- The `.ofocus` bundle path follows the same `~/Library/Group Containers/34YW5A73WQ.com.omnigroup.OmniFocus/com.omnigroup.OmniFocus4/` base as the IPC directory (they share the Group Container)
- Configurable via `OMNIFOCUS_OFOCUS_PATH` env var (consistent with `OMNIFOCUS_IPC_DIR` pattern)
- The exact subpath to `OmniFocus.ofocus` within the Group Container needs UAT verification -- this is flagged in Phase 4 research as a known uncertainty

### Pattern 4: CI Safety Grep Step
**What:** CI step that fails the build if any test file references RealBridge.
**Example:**
```yaml
# In .github/workflows/ci.yml, before the Test step:
- name: Safety check (SAFE-01)
  run: |
    if grep -r "RealBridge" tests/ --include="*.py" -l; then
      echo "ERROR: Test files must not reference RealBridge (SAFE-01)"
      echo "Use InMemoryBridge or SimulatorBridge for automated testing."
      exit 1
    fi
```

**Recommendation (Claude's Discretion):** Use a CI-only grep step rather than a pytest meta-test. Rationale:
- A CI grep step is simpler, faster, and operates at the text level (catches imports, string references, comments mentioning RealBridge in test code)
- A pytest meta-test would only run when pytest runs, but the safety rule is about what exists in test files, not what runs
- The existing test for `print()` in `test_server.py::TestTOOL04StdoutClean` uses a similar static grep pattern inside a test -- this works but the CI step is more direct for SAFE-01
- Both approaches are valid; CI-only is cleaner separation of concerns

### Pattern 5: UAT Framework Structure
**What:** Dedicated `uat/` directory for manual-only test scripts.
**Example structure:**
```
uat/
├── README.md                 # Philosophy + safety rules + usage instructions
└── test_read_only.py         # Phase 8: read-only dump + validate
```

**UAT script pattern:**
```python
#!/usr/bin/env python3
"""Manual UAT: Read-only OmniFocus dump validation.

Usage: uv run python uat/test_read_only.py

This script connects to real OmniFocus via RealBridge,
calls dump_all, and validates the response structure.

DO NOT run this in CI or automated tests. Human-only.
"""
import asyncio
from pathlib import Path

from omnifocus_operator.bridge._real import DEFAULT_IPC_DIR, RealBridge
from omnifocus_operator.models import DatabaseSnapshot


async def main() -> None:
    bridge = RealBridge(ipc_dir=DEFAULT_IPC_DIR)
    print("Sending dump_all to OmniFocus...")
    raw = await bridge.send_command("dump_all")

    snapshot = DatabaseSnapshot.model_validate(raw)
    print(f"Tasks: {len(snapshot.tasks)}")
    print(f"Projects: {len(snapshot.projects)}")
    print(f"Tags: {len(snapshot.tags)}")
    print(f"Folders: {len(snapshot.folders)}")
    print(f"Perspectives: {len(snapshot.perspectives)}")
    print("Validation: OK")


if __name__ == "__main__":
    asyncio.run(main())
```

### Anti-Patterns to Avoid
- **Importing RealBridge in test files:** Even for type-checking or isinstance assertions. Tests that need to verify RealBridge behavior should use SimulatorBridge (which inherits from RealBridge and shares all IPC mechanics).
- **Running UAT scripts in CI:** The uat/ directory must be excluded from both pytest discovery and CI pipeline execution.
- **Retrying in the bridge:** The user decision is "fail fast, no retry." Retry logic belongs in the agent layer, not the bridge.
- **Using `webbrowser.open()`:** Cannot pass `-g` flag to prevent focus stealing. Use `subprocess.run(["open", "-g", url])`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| URL encoding for script content | Manual string replacement | `urllib.parse.quote()` | Handles all special characters correctly (spaces, newlines, unicode) |
| Test-environment detection | Custom env var or config file | `PYTEST_CURRENT_TEST` env var | pytest sets this automatically; no configuration needed |
| URL scheme triggering | `os.system()` or shell pipes | `subprocess.run(["open", "-g", url])` | Safe argument handling, exit code checking, no shell injection |

**Key insight:** The implementation is almost entirely wiring and configuration. The hard work (IPC engine, error hierarchy, repository caching) is already done. Don't over-engineer the small remaining pieces.

## Common Pitfalls

### Pitfall 1: URL Scheme Fire-and-Forget Nature
**What goes wrong:** `open "omnifocus:///omnijs-run?..."` returns immediately with exit code 0 regardless of whether OmniFocus actually received or executed the script. If OmniFocus is not running, the URL scheme may launch it (adding multi-second delay) or silently fail.
**Why it happens:** macOS URL scheme dispatch is fire-and-forget by design. There is no synchronous acknowledgment channel.
**How to avoid:** This is the accepted design. The bridge already handles this via timeout: if OmniFocus doesn't write a response file within 10s, BridgeTimeoutError is raised with an agent-friendly message. The error message should suggest checking if OmniFocus is running.
**Warning signs:** Consistent timeouts during UAT; OmniFocus launching from a cold start.

### Pitfall 2: RealBridge Reference Leaking into Tests
**What goes wrong:** A test imports `RealBridge` for an isinstance check, type annotation, or fixture -- violating SAFE-01.
**Why it happens:** Developers (or AI agents) naturally reach for the concrete class when writing tests.
**How to avoid:** The CI grep step catches this statically. The runtime guard in the factory prevents accidental instantiation. Note: the existing `test_real_bridge.py` tests RealBridge's IPC mechanics using `tmp_path` -- these tests are testing the IPC engine, not triggering real OmniFocus. The SAFE-01 rule means: "no test creates a RealBridge that could contact real OmniFocus." The existing `test_real_bridge.py` must be audited -- it imports and instantiates `RealBridge` directly.
**Warning signs:** CI grep step flagging `test_real_bridge.py`. This file may need renaming or restructuring.

**IMPORTANT NUANCE on test_real_bridge.py:** The existing file `tests/test_real_bridge.py` imports and uses `RealBridge` extensively. These tests exercise the IPC engine (atomic writes, polling, cleanup, timeout, orphan sweep) using `tmp_path` -- they never contact real OmniFocus because `_trigger_omnifocus()` is a no-op in the base class. However, the SAFE-01 success criterion says "grep for RealBridge in test files returns zero matches." This creates tension with the existing test file. The resolution options are:
1. **Rename/restructure:** Move IPC-engine tests to test the behavior through SimulatorBridge (which inherits from RealBridge), eliminating direct RealBridge references
2. **Exclude the file from grep:** Accept that `test_real_bridge.py` tests the IPC engine, not real OmniFocus -- adjust the grep pattern to check for `create_bridge("real")` or `RealBridge(ipc_dir=DEFAULT_IPC_DIR)` instead
3. **Keep as-is and document:** The intent of SAFE-01 is preventing tests from contacting real OmniFocus, not preventing testing of IPC mechanics

The user locked decision says the CI grep checks "test files for RealBridge usage." Recommendation: refactor `test_real_bridge.py` to use SimulatorBridge (since SimulatorBridge inherits all IPC mechanics) and rename it. This is the cleanest compliance with SAFE-01.

### Pitfall 3: FileMtimeSource Path May Not Exist
**What goes wrong:** Server startup fails with `OSError` because the `.ofocus` path doesn't exist on the machine (OmniFocus not installed, different version, or non-macOS).
**Why it happens:** The default path is hardcoded to OmniFocus 4's Group Container structure.
**How to avoid:** The `FileMtimeSource` already propagates `OSError` (fail-fast design from Phase 4). The error message should be agent-friendly: "Cannot find OmniFocus data at <path>. Is OmniFocus 4 installed?" Consider checking path existence at startup and failing early with a clear message.
**Warning signs:** Server crashes on startup on a machine without OmniFocus.

### Pitfall 4: .ofocus Path Uncertainty
**What goes wrong:** The exact `.ofocus` bundle path within the Group Container may differ from what's documented.
**Why it happens:** The path `~/Library/Group Containers/34YW5A73WQ.com.omnigroup.OmniFocus/com.omnigroup.OmniFocus4/OmniFocus.ofocus` is inferred from patterns but not independently verified with a live OmniFocus 4 installation.
**How to avoid:** This is explicitly a Phase 8 UAT concern. The UAT script will verify the actual path. The `OMNIFOCUS_OFOCUS_PATH` env var provides an escape hatch if the default is wrong.
**Warning signs:** UAT script fails to find the `.ofocus` bundle at the default path.

### Pitfall 5: Coverage Threshold Failure
**What goes wrong:** Adding safety guards and UAT infrastructure without sufficient new tests causes the 80% coverage threshold to fail (currently at 46.62%).
**Why it happens:** The `server/` package and `simulator/__main__.py` have 0% coverage under the unit test suite. The simulator's main module is a standalone CLI process tested via subprocess integration tests that don't contribute to `pytest-cov` line coverage.
**How to avoid:** Focus the test gap audit on modules with low coverage. The `--cov-fail-under=80` threshold in pyproject.toml may need to account for the simulator module (which is tested via subprocess, not importable tests). Consider adding `omit` patterns for `simulator/__main__.py` in coverage config, or writing unit tests for its internal functions.
**Warning signs:** `uv run pytest --cov-fail-under=80` failing after Phase 8 changes.

## Code Examples

### URL Scheme Trigger (BRDG-04)
```python
# Source: .planning/research/ARCHITECTURE.md line 419, 470
# In src/omnifocus_operator/bridge/_real.py

import subprocess
import urllib.parse

from omnifocus_operator.bridge._errors import BridgeConnectionError

def _trigger_omnifocus(self, dispatch: str) -> None:
    """Trigger OmniFocus to process the current IPC request.

    Opens the ``omnifocus:///omnijs-run`` URL scheme via macOS ``open -g``
    (background, no focus steal). The bridge script inside OmniFocus reads
    the request file, executes the operation, and writes the response file.
    """
    # Minimal JS: just invokes the bridge script with the dispatch argument.
    # The actual bridge script is installed as a plug-in in OmniFocus.
    script = "var url = URL.fromString('file:///path/to/bridge.omnijs'); url.call(function(){});"
    encoded_script = urllib.parse.quote(script, safe="")
    encoded_arg = urllib.parse.quote(dispatch, safe="")
    url = f"omnifocus:///omnijs-run?script={encoded_script}&arg={encoded_arg}"

    operation = dispatch.split("::::")[1] if "::::" in dispatch else "unknown"
    try:
        subprocess.run(["open", "-g", url], check=True, capture_output=True)
    except FileNotFoundError:
        raise BridgeConnectionError(
            operation=operation,
            reason="'open' command not found. This server requires macOS.",
        ) from None
    except subprocess.CalledProcessError as exc:
        raise BridgeConnectionError(
            operation=operation,
            reason=(
                f"Failed to trigger OmniFocus (exit code {exc.returncode}). "
                "Is OmniFocus installed?"
            ),
        ) from None
```

**Note on the script content:** The exact JavaScript snippet passed to `omnijs-run` depends on how the bridge script is installed in OmniFocus. The project brief references `operatorBridgeScript.js` as the bridge script. The script content in the URL may be a minimal bootstrap that loads and runs the installed plug-in, or it may be the full bridge script inlined. This is a detail for the planner to resolve based on the bridge script's actual installation mechanism. The `dispatch` string is passed via the `&arg=` parameter.

### Factory Safety Guard (SAFE-01)
```python
# Source: 08-CONTEXT.md locked decisions
# In src/omnifocus_operator/bridge/_factory.py

case "real":
    import os

    if os.environ.get("PYTEST_CURRENT_TEST"):
        msg = (
            "RealBridge is not available during automated testing "
            "(PYTEST_CURRENT_TEST is set). "
            "Use OMNIFOCUS_BRIDGE=inmemory or OMNIFOCUS_BRIDGE=simulator instead."
        )
        raise RuntimeError(msg)

    from omnifocus_operator.bridge._real import DEFAULT_IPC_DIR, RealBridge

    ipc_dir_str = os.environ.get("OMNIFOCUS_IPC_DIR")
    ipc_dir = Path(ipc_dir_str) if ipc_dir_str else DEFAULT_IPC_DIR
    return RealBridge(ipc_dir=ipc_dir)
```

### FileMtimeSource Wiring
```python
# Source: 08-CONTEXT.md integration points
# In src/omnifocus_operator/server/_server.py app_lifespan

from pathlib import Path

if bridge_type in ("inmemory", "simulator"):
    mtime_source = ConstantMtimeSource()
else:
    from omnifocus_operator.repository import FileMtimeSource

    default_ofocus = str(
        Path.home()
        / "Library"
        / "Group Containers"
        / "34YW5A73WQ.com.omnigroup.OmniFocus"
        / "com.omnigroup.OmniFocus4"
        / "OmniFocus.ofocus"
    )
    ofocus_path = os.environ.get("OMNIFOCUS_OFOCUS_PATH", default_ofocus)
    mtime_source = FileMtimeSource(path=ofocus_path)
```

## Test Coverage Audit

### Current State (166 tests, 46.62% coverage)

| Layer | Test File | Tests | Coverage Notes |
|-------|-----------|-------|----------------|
| Models | `test_models.py` | ~40+ | Models at 100% coverage. Well-tested. |
| Bridge (protocol, errors, InMemory) | `test_bridge.py` | 22 | Bridge protocol and InMemoryBridge well-tested |
| Bridge (RealBridge IPC) | `test_real_bridge.py` | 25 | IPC engine well-tested. **SAFE-01 conflict: imports RealBridge** |
| Bridge (SimulatorBridge) | `test_simulator_bridge.py` | 10 | Unit + factory + lifespan wiring tested |
| Bridge (Simulator integration) | `test_simulator_integration.py` | 7 | Subprocess E2E tests |
| Repository | `test_repository.py` | 21+ | SNAP-01 through SNAP-06, errors, concurrency, FileMtimeSource |
| Service | `test_service.py` | 7 | Thin passthrough tested |
| Server (MCP integration) | `test_server.py` | 11 | ARCH-01/02, TOOL-01/02/03/04, IPC-06 wiring |
| Smoke | `test_smoke.py` | 3 | Package import, entry point, default bridge |

### Coverage Gaps to Address

1. **`server/_server.py` at 0% line coverage**: Despite being tested via in-process MCP client in `test_server.py`, the `_server.py` module shows 0% because tests import and run it in a subprocess-like pattern. This is likely a coverage measurement issue with how `pytest-cov` tracks lines in modules loaded inside `asynccontextmanager` and task groups. Verify whether the existing tests actually cover `app_lifespan` paths.

2. **`server/__init__.py` at 0%**: The `create_server` re-export. Trivial but should be covered by any test that calls `from omnifocus_operator.server import create_server`.

3. **`service/_service.py` at 71%**: Missing coverage on lines 28 and 37. Likely the `__init__` and a method not called in tests.

4. **`repository/_repository.py` at 38%**: Low coverage despite 21+ repository tests. Suggests the repository code paths exercised in tests use `InMemoryBridge` + `FakeMtimeSource`, and the production code paths (real mtime checking) aren't covered by unit tests. This is expected -- the real paths are Phase 8 UAT.

5. **`repository/_mtime.py` at 75%**: Lines 38, 42-43, 56 uncovered. Line 38 is `FileMtimeSource.__init__`, lines 42-43 are `get_mtime_ns` body, line 56 is `ConstantMtimeSource.get_mtime_ns`. These ARE tested in `test_repository.py::TestFileMtimeSource` and `TestConstantMtimeSource` -- the coverage gap may be a measurement artifact.

6. **`simulator/__main__.py` at 0%**: The standalone CLI simulator process. Tested via subprocess in `test_simulator_integration.py` but `pytest-cov` can't measure coverage of subprocesses. Consider: add `simulator/__main__.py` to coverage `omit` list, or write unit tests for internal helper functions.

7. **`test_real_bridge.py` SAFE-01 conflict**: This file imports and uses `RealBridge` directly. It tests IPC mechanics, not real OmniFocus. Must be refactored to use `SimulatorBridge` or otherwise made SAFE-01 compliant.

### TEST-02 Assessment (Full E2E Pipeline via InMemoryBridge)

**Existing coverage:** `test_server.py::TestARCH01ThreeLayerArchitecture::test_list_all_returns_data_through_all_layers` already tests the full MCP -> Service -> Repository -> Bridge -> structured Pydantic data pipeline using InMemoryBridge via the real server with `OMNIFOCUS_BRIDGE=inmemory`.

**Recommendation (Claude's Discretion):** The existing test satisfies TEST-02. A single focused test that explicitly asserts the full pipeline (tool call -> structured Pydantic data with correct entity counts) is sufficient. No additional integration tests needed beyond verifying data flows correctly through all layers, which the existing test does.

### TEST-03 Assessment (Tests for Each Layer)

**All 5 layers have tests.** Gap analysis:

| Layer | Has Tests | Gaps |
|-------|-----------|------|
| Models | Yes (`test_models.py`) | None significant |
| Bridge | Yes (`test_bridge.py`, `test_real_bridge.py`, `test_simulator_bridge.py`) | `test_real_bridge.py` needs SAFE-01 refactor |
| Repository | Yes (`test_repository.py`) | None significant |
| Service | Yes (`test_service.py`) | Minor coverage gaps |
| MCP Server | Yes (`test_server.py`) | Coverage measurement issue |

### Recommended Test Actions

1. **Refactor `test_real_bridge.py`** to eliminate direct `RealBridge` imports:
   - All IPC tests can use `SimulatorBridge` since it inherits 100% of IPC mechanics
   - Rename to `test_ipc_engine.py` to reflect what's actually being tested
   - Factory and default-path tests stay (they use `create_bridge("real")` with monkeypatched env)

2. **Add SAFE-01 enforcement test or CI step** (one or both):
   - CI grep: `grep -r "RealBridge" tests/ --include="*.py" -l` must return empty
   - Optional pytest meta-test: similar to existing `test_no_print_calls_in_source` pattern

3. **Add factory safety guard test**: Test that `create_bridge("real")` raises `RuntimeError` when `PYTEST_CURRENT_TEST` is set.

4. **Verify existing TEST-02 coverage**: Confirm `test_server.py::TestARCH01` exercises the full pipeline.

5. **Coverage config**: Add `simulator/__main__.py` to `omit` in `[tool.coverage.run]` since it's tested via subprocess.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2+ with pytest-asyncio 1.3.0+ |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/ -x --timeout=10` |
| Full suite command | `uv run pytest --cov-fail-under=80` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BRDG-04 | RealBridge triggers OmniFocus via URL scheme | manual-only (UAT) | N/A -- manual: `uv run python uat/test_read_only.py` | Wave 0 (create `uat/test_read_only.py`) |
| BRDG-04 | _trigger_omnifocus() calls subprocess with correct URL | unit (mock subprocess) | `uv run pytest tests/test_ipc_engine.py::TestTriggerImplementation -x` | Wave 0 (add to refactored test file) |
| SAFE-01 | create_bridge("real") refuses during pytest | unit | `uv run pytest tests/test_service.py::TestCreateBridge::test_real_refuses_during_pytest -x` | Wave 0 |
| SAFE-01 | No test file references RealBridge | CI grep | CI step in `.github/workflows/ci.yml` | Wave 0 |
| SAFE-02 | UAT folder excluded from pytest | unit (meta) | `uv run pytest --collect-only` and verify no uat/ tests collected | Wave 0 |
| TEST-02 | Full pipeline via InMemoryBridge | integration | `uv run pytest tests/test_server.py::TestARCH01 -x` | Exists (test_server.py) |
| TEST-03 | Each layer has tests | audit | `uv run pytest --co -q` and verify coverage per module | Exists (all layers) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x --timeout=10`
- **Per wave merge:** `uv run pytest --cov-fail-under=80`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `uat/test_read_only.py` -- manual UAT script for BRDG-04
- [ ] `uat/README.md` -- UAT philosophy document for SAFE-02
- [ ] Refactor `tests/test_real_bridge.py` to `tests/test_ipc_engine.py` using SimulatorBridge
- [ ] Add SAFE-01 guard test in `tests/test_service.py` (factory refuses during pytest)
- [ ] Add SAFE-01 CI grep step in `.github/workflows/ci.yml`
- [ ] Add `testpaths` exclusion for `uat/` in `pyproject.toml`
- [ ] Update `CLAUDE.md` with SAFE-01/02 rules
- [ ] Coverage config: add `simulator/__main__.py` to omit

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `_trigger_omnifocus()` is no-op | Implemented with `subprocess.run(["open", "-g", url])` | Phase 8 | Enables production use |
| `app_lifespan` raises NotImplementedError for "real" | Wires FileMtimeSource with configurable .ofocus path | Phase 8 | Enables production use |
| No safety guardrails | Factory guard + CI grep + uat/ exclusion | Phase 8 | SAFE-01/02 enforced |

## Open Questions

1. **Exact .ofocus bundle path within Group Container**
   - What we know: OmniFocus 3 uses `~/Library/Containers/com.omnigroup.OmniFocus3/Data/Library/Application Support/OmniFocus/OmniFocus.ofocus`. OmniFocus 4 uses Group Containers at `~/Library/Group Containers/34YW5A73WQ.com.omnigroup.OmniFocus/com.omnigroup.OmniFocus4/`. The exact subpath to `OmniFocus.ofocus` within OmniFocus 4's Group Container is unverified.
   - What's unclear: Whether it's `OmniFocus.ofocus` directly in the Group Container's versioned directory, or in a deeper `Data/Library/Application Support/OmniFocus/` subpath.
   - Recommendation: Use a configurable default with `OMNIFOCUS_OFOCUS_PATH` env var. UAT verification will determine the correct path. Fail with a clear error if path doesn't exist.

2. **Exact JavaScript snippet for omnijs-run URL**
   - What we know: The URL format is `omnifocus:///omnijs-run?script=<encoded>&arg=<dispatch>`. The bridge script (`operatorBridgeScript.js`) exists in `.research/`.
   - What's unclear: Whether the script parameter should be the full bridge script inlined, or a minimal bootstrap that references an installed plug-in. The bridge script may be too large to inline in a URL.
   - Recommendation: The planner should inspect `.research/operatorBridgeScript.js` and determine the trigger approach. A minimal inline script that reads the dispatch arg and processes the IPC request file is most reliable.

3. **test_real_bridge.py refactoring scope**
   - What we know: The file has 25 tests covering IPC mechanics. All can work with SimulatorBridge since it inherits from RealBridge.
   - What's unclear: Whether the factory tests that explicitly call `create_bridge("real")` should remain (they validate the factory, but import RealBridge for isinstance checks).
   - Recommendation: Refactor IPC tests to use SimulatorBridge. For factory tests that must reference RealBridge, move them to a separate file or accept the grep exclusion. The SAFE-01 intent is "no test contacts real OmniFocus," not "no test mentions the class name."

## Sources

### Primary (HIGH confidence)
- Existing codebase: `src/omnifocus_operator/bridge/_real.py`, `_factory.py`, `_errors.py`, `_simulator.py`, `server/_server.py`
- Existing tests: `tests/test_real_bridge.py`, `test_server.py`, `test_simulator_integration.py`
- Project research: `.research/MILESTONE-1.md`, `.planning/research/ARCHITECTURE.md`, `.planning/research/PITFALLS.md`
- Phase 8 CONTEXT.md: User decisions from `/gsd:discuss-phase`
- [Omni Automation Script URLs](https://omni-automation.com/script-url/) - URL scheme format confirmation

### Secondary (MEDIUM confidence)
- [OmniFocus URL Schemes](https://inside.omnifocus.com/url-schemes) - Official URL scheme documentation (covers /add, /inbox, etc. but not omnijs-run directly)
- [subprocess documentation](https://docs.python.org/3/library/subprocess.html) - Python 3.12 subprocess.run behavior
- pytest documentation - PYTEST_CURRENT_TEST env var behavior

### Tertiary (LOW confidence)
- OmniFocus 4 .ofocus path: Inferred from OmniFocus 3 patterns and Group Container structure. Needs UAT verification.
- Exact JavaScript snippet for URL scheme trigger: Based on `.research/MILESTONE-1.md` pattern but unverified with live OmniFocus.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All stdlib, no new dependencies, patterns well-documented in project research
- Architecture: HIGH - Small implementation surface, patterns proven by SimulatorBridge, clear integration points
- Pitfalls: HIGH - Well-documented in prior research phases, safety patterns are straightforward
- .ofocus path: LOW - Exact path unverified, needs UAT confirmation
- JS trigger snippet: LOW - Exact script content depends on bridge script installation approach

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (stable domain, no external dependency changes expected)
