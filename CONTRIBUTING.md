# Contributing

## Setup

```bash
git clone https://github.com/HelloThisIsFlo/omnifocus-operator.git
cd omnifocus-operator
just setup    # installs deps + pre-commit hooks
```

Requires: Python 3.12+, [uv](https://docs.astral.sh/uv/), [just](https://just.systems/).

## Project Structure

```
src/omnifocus_operator/
├── server/          # MCP tool definitions (FastMCP v3)
├── service/         # Business logic — method object pipelines
├── repository/      # Data access — SQLite cache + OmniJS bridge
├── contracts/       # Write-side Pydantic models (Command, Result, etc.)
├── models/          # Core + read-side Pydantic models
├── bridge/          # OmniJS IPC engine + bridge.js
├── simulator/       # In-process OmniJS simulator for integration tests
└── agent_messages/  # Agent-facing warnings and guidance text
```

Three-layer architecture: **MCP Server → Service → Repository**. All layers communicate through typed contracts.

## Running Tests

```bash
just test-python           # Python test suite
just test-js               # JS bridge tests
just test-all              # Both
just test-kw add_task      # Run by keyword (no quotes needed)
just test-one tests/test_server.py  # Single file, no coverage
just test-cov              # With HTML coverage report
```

## Quality Checks

```bash
just check-all    # test + lint + typecheck (full suite)
just ci           # replicate CI pipeline locally
just fix          # auto-fix lint and formatting
just typecheck    # mypy with Pydantic plugin
just lint         # ruff check + format (read-only)
```

Pre-commit hooks run lint, format, and type checks before each commit.

## Key Conventions

- **Service layer**: uses the [Method Object pattern](https://github.com/HelloThisIsFlo/omnifocus-operator/blob/main/docs/architecture.md) — each use case gets a `_VerbNounPipeline` class
- **Models**: see `docs/model-taxonomy.md` — core models have no suffix, output variants use `Read`, write-side contracts use `Command`/`Result`/`Action`/`Spec`
- **Testing**: `InMemoryBridge` for unit tests, `SimulatorBridge` for IPC integration. **Never** touch `RealBridge` in automated tests — the factory raises `RuntimeError` under pytest
- **Extra fields forbidden**: write models use `extra="forbid"` so agents get errors, not silent drops

## PR Process

1. Fork and branch from `main`
2. Write tests for new behavior
3. Run `just ci` before pushing
4. Open a PR — keep the description focused on *what* and *why*

## Useful Commands

| Command | Purpose |
|---------|---------|
| `just serve` | Start the MCP server (stdio) |
| `just inspect` | Open MCP Inspector |
| `just log` | Tail the operator log |
| `just schema` | Dump MCP tool schemas to `.sandbox/` |
| `just safety` | Verify no test references RealBridge |
