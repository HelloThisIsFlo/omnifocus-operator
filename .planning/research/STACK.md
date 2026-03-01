# Stack Research

**Domain:** Python MCP server with macOS application bridge (file-based IPC)
**Researched:** 2026-03-01
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| Python | 3.12 | Runtime | 3.12 is the sweet spot: stable, performant, fully supported by all dependencies. 3.11+ is the project constraint. 3.13 works but 3.12 has wider library compatibility. 3.14 support is still maturing in some deps. | HIGH |
| `mcp` (official SDK) | >=1.26.0 | MCP server framework | The official Model Context Protocol Python SDK. Includes a built-in FastMCP high-level API (`from mcp.server.fastmcp import FastMCP`) that handles tool registration, validation, and transport. Use this, not the standalone `fastmcp` package (see "What NOT to Use"). | HIGH |
| Pydantic | >=2.12.0 (latest: 2.12.5) | Data models and validation | Already a transitive dependency of the MCP SDK. Pydantic v2 is required (v1 is EOL). Provides `model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)` for the camelCase/snake_case bridge. The MCP SDK pins `pydantic>=2.12.0`. | HIGH |
| pydantic-settings | >=2.5.2 (latest: 2.13.1) | Server configuration | Already a transitive dependency of the MCP SDK. Use for `--due-soon-threshold` and `--output-format` config via env vars and CLI flags. | HIGH |
| uv | >=0.10 (latest: 0.10.7) | Package/project manager | The standard Python project manager in 2025/2026. Replaces pip, pip-tools, poetry, pyenv, and virtualenv in a single Rust-based tool. 10-100x faster than pip. Handles lockfiles (`uv.lock`), virtual envs, and Python version management. MCP's own `create-python-server` template uses uv. | HIGH |

### Supporting Libraries

| Library | Version | Purpose | When to Use | Confidence |
|---------|---------|---------|-------------|------------|
| anyio | >=4.5 (transitive via MCP SDK) | Async primitives | Use `anyio` for async file I/O and concurrency instead of raw `asyncio` where possible. The MCP SDK is built on anyio. Using it directly gives structured concurrency (task groups) and consistent APIs. Already installed as a transitive dep. | HIGH |
| aiofiles | >=25.1.0 | Async file read/write | For reading/writing request/response JSON files in the IPC layer without blocking the event loop. Small, focused, well-maintained. Use for the bridge's file operations. | HIGH |
| watchfiles | >=1.1.1 | File system watching | For the mock simulator script that watches the `requests/` directory. Uses Rust's `notify` crate under the hood. Provides async `awatch()`. The MCP server itself uses polling (stat + sleep), not watching -- watchfiles is only for the simulator. | MEDIUM |

### Development Tools

| Tool | Version | Purpose | Notes | Confidence |
|------|---------|---------|-------|------------|
| uv | >=0.10.7 | Package management, virtualenv, Python version | `uv init`, `uv add`, `uv sync`, `uv run`. Replaces the entire pip/poetry/pyenv toolchain. | HIGH |
| ruff | >=0.15.0 | Linter + formatter | Replaces both flake8 and black. Written in Rust, 10-100x faster. Configure in `pyproject.toml` under `[tool.ruff]`. Use the 2026 style guide. | HIGH |
| mypy | >=1.19.1 | Static type checking | Essential for a Pydantic-heavy codebase. Pydantic v2 has excellent mypy plugin support. Configure `plugins = ["pydantic.mypy"]` in `pyproject.toml`. | HIGH |
| pytest | >=9.0.2 | Test framework | Standard Python testing. Requires Python >=3.10. | HIGH |
| pytest-asyncio | >=1.3.0 | Async test support | Required for testing async bridge operations, snapshot loading, and IPC polling. Use `asyncio_mode = "auto"` in `pyproject.toml` to avoid decorating every test. | HIGH |
| pytest-timeout | >=2.4.0 | Test timeout protection | Prevents hanging tests during IPC testing. Set a global timeout (e.g., 10s) in `pyproject.toml`. Critical because file polling tests can hang if something goes wrong. | HIGH |

## Project Structure

Use the `src/` layout (matching the official MCP server template):

```
omnifocus-operator/
  pyproject.toml
  uv.lock
  src/
    omnifocus_operator/
      __init__.py
      __main__.py          # Entry point: uv run omnifocus-operator
      server.py             # FastMCP server, tool registration
      service.py            # Service layer (thin passthrough in M1)
      repository.py         # OmniFocus repository, snapshot management
      bridge/
        __init__.py
        interface.py        # Abstract bridge interface
        in_memory.py        # InMemoryBridge for unit tests
        file_ipc.py         # Shared file-based IPC logic
        simulator.py        # SimulatorBridge (file IPC, no URL trigger)
        real.py             # RealBridge (file IPC + URL scheme trigger)
      models/
        __init__.py
        task.py
        project.py
        tag.py
        folder.py
        perspective.py
        database.py         # DatabaseSnapshot container
  scripts/
    mock_simulator.py       # Standalone simulator script
  tests/
    conftest.py
    test_server.py
    test_service.py
    test_repository.py
    test_bridge/
      test_in_memory.py
      test_file_ipc.py
    test_models/
      test_task.py
      ...
```

## Installation

```bash
# Initialize project (if starting fresh)
uv init omnifocus-operator
cd omnifocus-operator

# Core dependencies
uv add "mcp>=1.26.0"
# Note: mcp already brings in pydantic>=2.12.0, pydantic-settings>=2.5.2,
#       anyio>=4.5, httpx, starlette, uvicorn as transitive deps.

# Additional runtime dependencies
uv add "aiofiles>=25.1.0"

# Dev dependencies
uv add --dev "pytest>=9.0.2"
uv add --dev "pytest-asyncio>=1.3.0"
uv add --dev "pytest-timeout>=2.4.0"
uv add --dev "mypy>=1.19.1"
uv add --dev "ruff>=0.15.0"
uv add --dev "watchfiles>=1.1.1"  # Only needed for mock simulator

# Sync everything
uv sync
```

## pyproject.toml Configuration

```toml
[project]
name = "omnifocus-operator"
version = "0.1.0"
description = "MCP server exposing OmniFocus as structured task infrastructure for AI agents"
requires-python = ">=3.12"
dependencies = [
    "mcp>=1.26.0",
    "aiofiles>=25.1.0",
]

[project.scripts]
omnifocus-operator = "omnifocus_operator.__main__:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
timeout = 10

[tool.mypy]
strict = true
plugins = ["pydantic.mypy"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM", "TCH", "RUF"]

[tool.ruff.format]
quote-style = "double"
```

## Key Technical Decisions

### Use the official `mcp` SDK's built-in FastMCP, not standalone `fastmcp`

The official `mcp` package (v1.26.0) includes `mcp.server.fastmcp.FastMCP` -- the original FastMCP 1.0 that was merged into the SDK in 2024. This is sufficient for OmniFocus Operator's needs:

- Tool registration via `@mcp.tool()` decorator
- Automatic Pydantic schema generation from type hints
- stdio transport (the default, which is what Claude Desktop uses)
- Lifespan context manager for startup/cleanup

The standalone `fastmcp` package (now at v3.0) adds features like server proxying, REST API generation, authentication, and client management. These are overkill for a single-purpose MCP server. Using the official SDK means one fewer dependency, tighter alignment with the MCP spec, and no risk of divergence between FastMCP's protocol implementation and the official one.

**Import:** `from mcp.server.fastmcp import FastMCP`

### Use `anyio` for async primitives, not raw `asyncio`

The MCP SDK is built on anyio. Using anyio directly (for task groups, sleep, file operations) keeps the async style consistent. `asyncio.Lock` is fine for the deduplication lock since we know we are running on asyncio, but prefer anyio for new async code.

### Use `aiofiles` for non-blocking file I/O in the bridge

The bridge reads and writes JSON files (request/response). Using `aiofiles.open()` prevents blocking the event loop during file operations. This matters because the MCP server handles concurrent tool calls and cannot afford to block on synchronous I/O.

### Pydantic v2 model configuration for camelCase aliasing

```python
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

class OmniFocusModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Accept both snake_case and camelCase
    )
```

This lets models use Pythonic snake_case internally while serializing to camelCase for JSON output matching the bridge script's format.

### `uv` as the sole project management tool

uv replaces pip, poetry, pyenv, and virtualenv. It is the community standard for new Python projects in 2025/2026. The MCP SDK's own `create-python-server` template uses uv. Key commands:
- `uv run omnifocus-operator` -- run the server
- `uv sync --dev` -- install all deps including dev
- `uv add <package>` -- add a dependency
- `uv lock` -- regenerate lockfile

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `mcp` (official SDK) | `fastmcp` (standalone v3) | Only if you need advanced features: server proxying, REST-to-MCP generation, built-in auth, or multi-server composition. OmniFocus Operator does not. |
| uv | Poetry | Only if the team is deeply invested in Poetry and unwilling to migrate. Poetry is slower, more complex, and losing mindshare to uv. |
| Pydantic v2 | attrs + cattrs | Only for performance-critical data pipelines where Pydantic's validation overhead matters. Not relevant here -- 1.5MB JSON parse is negligible. |
| ruff | flake8 + black + isort | Never for new projects. ruff replaces all three, is faster, and has a single config. |
| mypy | pyright / ty | pyright is viable (faster, better inference). mypy is recommended because Pydantic's mypy plugin is mature and well-tested. pyright support for Pydantic exists but mypy's is battle-hardened. |
| pytest-asyncio | anyio pytest plugin (`anyio.pytest_plugin`) | anyio's plugin works but pytest-asyncio has wider adoption and better docs. Since we are on asyncio (not trio), pytest-asyncio is the natural fit. |
| aiofiles | `anyio.open_file()` | anyio includes async file support (`anyio.open_file`). This is a valid alternative that avoids an extra dependency. Consider using `anyio.open_file()` directly since anyio is already a transitive dep. The tradeoff: aiofiles has a more familiar API; anyio.open_file is simpler and zero-extra-deps. **Recommendation: Start with `anyio.open_file()` and only add aiofiles if the API proves limiting.** |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `fastmcp` (standalone package) | Adds a large, fast-moving dependency (v3.0, 17MB source) with features this project does not need. Creates risk of protocol divergence with the official SDK. | `mcp` (official SDK) with `from mcp.server.fastmcp import FastMCP` |
| Poetry | Slower, more complex lockfile resolution, declining community momentum vs uv. | uv |
| Pydantic v1 | EOL. The MCP SDK requires v2. | Pydantic v2 (>=2.12.0) |
| flake8 / black / isort (separately) | Three tools doing what one (ruff) does better and faster. | ruff |
| `watchdog` | Heavy, complex API, C extension. For file watching, watchfiles (Rust-based) is faster and simpler. | watchfiles (for simulator) or `os.stat()` + `asyncio.sleep()` (for snapshot freshness) |
| `asyncio.to_thread(open(...))` | Manual thread delegation for file I/O. Error-prone, no async context manager support. | aiofiles or `anyio.open_file()` |
| `subprocess` for OmniFocus triggering | The bridge uses the `omnifocus:///omnijs-run` URL scheme, which on macOS is triggered via `open -g "omnifocus:///..."`. Do not try to script OmniFocus via `subprocess` or AppleScript -- the URL scheme is the documented, sandboxed approach. | `subprocess.run(["open", "-g", url])` to open the URL scheme (this is the correct, minimal approach) |

## Stack Patterns

**For the MCP server entry point:**
```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("OmniFocus Operator")

@mcp.tool()
async def list_all() -> dict:
    """Return the full OmniFocus database snapshot."""
    # service.list_all() -> repository.get_snapshot() -> bridge if stale
    ...

if __name__ == "__main__":
    mcp.run()  # stdio transport by default
```

**For Pydantic models matching bridge output:**
```python
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

class Task(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: str
    name: str
    note: str
    flagged: bool
    effective_flagged: bool
    due_date: str | None = None
    effective_due_date: str | None = None
    tags: list[str] = Field(default_factory=list)
    project: str | None = None  # ID reference
    parent: str | None = None   # ID reference
    # ... remaining fields from bridge script
```

**For async file-based IPC:**
```python
import anyio
import json
import uuid

async def send_ipc_request(base_dir: str, operation: str) -> dict:
    request_id = str(uuid.uuid4())
    request_path = f"{base_dir}/requests/{request_id}.json"
    response_path = f"{base_dir}/responses/{request_id}.json"

    # Atomic write: tmp then rename
    tmp_path = request_path.replace(".json", ".tmp")
    async with await anyio.open_file(tmp_path, "w") as f:
        await f.write(json.dumps({"id": request_id, "operation": operation}))
    await anyio.Path(tmp_path).rename(request_path)

    # Poll for response
    deadline = anyio.current_time() + 10.0  # 10s timeout
    while anyio.current_time() < deadline:
        if await anyio.Path(response_path).exists():
            async with await anyio.open_file(response_path, "r") as f:
                return json.loads(await f.read())
        await anyio.sleep(0.05)  # 50ms poll interval

    raise TimeoutError("OmniFocus did not respond within 10s -- is it running?")
```

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| mcp >=1.26.0 | pydantic >=2.12.0 | MCP SDK pins this range; do not override. |
| mcp >=1.26.0 | anyio >=4.5 | Transitive dep; available for direct use. |
| mcp >=1.26.0 | Python >=3.10 | We target 3.12 for performance and syntax benefits. |
| pytest >=9.0 | Python >=3.10 | Dropped Python 3.9 support. |
| pytest-asyncio >=1.3.0 | Python >=3.10 | Aligned with pytest 9.x requirements. |
| ruff >=0.15.0 | Python 3.7+ (linting target) | Lints any Python version; runs on 3.10+. |
| mypy >=1.19.1 | Python >=3.9 | 1.19 is last to support 3.9; we are on 3.12. |

## Revised Dependency Decision: aiofiles vs anyio.open_file()

After analysis, **drop `aiofiles` and use `anyio` directly** for async file operations. Rationale:

1. `anyio` is already a transitive dependency of the MCP SDK -- zero extra deps.
2. `anyio.open_file()` provides the same async file I/O capabilities.
3. `anyio.Path` provides async versions of `pathlib.Path` methods (exists, stat, rename, mkdir, etc.).
4. Keeps the async style consistent with the MCP SDK's own internals.

This means the **only runtime dependency beyond the MCP SDK is: none.** The `mcp` package brings everything needed.

## Final Dependency Summary

**Runtime:**
- `mcp>=1.26.0` (brings pydantic, pydantic-settings, anyio, httpx, starlette, uvicorn)

**Dev:**
- `pytest>=9.0.2`
- `pytest-asyncio>=1.3.0`
- `pytest-timeout>=2.4.0`
- `mypy>=1.19.1`
- `ruff>=0.15.0`
- `watchfiles>=1.1.1` (for mock simulator only)

## Sources

- [MCP Python SDK (GitHub)](https://github.com/modelcontextprotocol/python-sdk) -- architecture, dependencies, FastMCP API
- [MCP Python SDK (PyPI)](https://pypi.org/project/mcp/) -- version 1.26.0, Python >=3.10
- [MCP SDK pyproject.toml](https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/pyproject.toml) -- exact dependency pins (pydantic>=2.12.0, anyio>=4.5, etc.)
- [Pydantic (PyPI)](https://pypi.org/project/pydantic/) -- version 2.12.5, Python >=3.9
- [uv (GitHub)](https://github.com/astral-sh/uv) -- version 0.10.7, Rust-based package manager
- [ruff (GitHub)](https://github.com/astral-sh/ruff) -- version 0.15.0, 2026 style guide
- [mypy (PyPI)](https://pypi.org/project/mypy/) -- version 1.19.1
- [pytest (PyPI)](https://pypi.org/project/pytest/) -- version 9.0.2, Python >=3.10
- [pytest-asyncio (PyPI)](https://pypi.org/project/pytest-asyncio/) -- version 1.3.0, Python >=3.10
- [watchfiles (PyPI)](https://pypi.org/project/watchfiles/) -- version 1.1.1, Rust-based
- [aiofiles (PyPI)](https://pypi.org/project/aiofiles/) -- version 25.1.0 (evaluated but not recommended; use anyio instead)
- [create-python-server (GitHub)](https://github.com/modelcontextprotocol/create-python-server) -- official MCP server template structure
- [FastMCP vs mcp.server.fastmcp (GitHub issue)](https://github.com/modelcontextprotocol/python-sdk/issues/1068) -- relationship between standalone FastMCP and official SDK
- [anyio docs](https://anyio.readthedocs.io/en/stable/why.html) -- rationale for anyio over raw asyncio

---
*Stack research for: Python MCP server with macOS application bridge*
*Researched: 2026-03-01*
