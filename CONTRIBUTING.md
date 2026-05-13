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

## Versioning

OmniFocus Operator uses [semantic versioning](https://semver.org/) going forward from **v1.5**:

- **`X.Y.0`** — minor bump for any feature work (new tools, new behavior, new response fields, scope additions)
- **`X.Y.Z`** — patch bump reserved for **true bug fixes only** (no new behavior, no API changes)
- **`X.0.0`** — major bump for breaking changes (renamed/removed tools, response shape breaks, dropped platform support)

**Historical note:** Releases through **v1.4.1** use a looser convention where `.Z` slots sometimes carried themed feature increments (e.g. v1.4.1 added presence flags and a new filter — feature work, not a bug fix). These are **not retroactively renumbered** — the git tags and release history are preserved as shipped. The strict convention above applies to v1.5 onward.

**Strikethrough convention in planning docs:** When milestone numbers shift in `.planning/` or `.research/`, historical references use markdown strikethrough to preserve audit trail: `~~v1.7~~ v1.8`. New material uses the new number plainly. Future agents reading archive material can see both the old and new identity at a glance.

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
