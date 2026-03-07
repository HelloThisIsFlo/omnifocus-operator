# Phase 1: Project Scaffolding - Research

**Researched:** 2026-03-01
**Domain:** Python project scaffolding with uv, hatchling, ruff, mypy, pytest, GitHub Actions CI, pre-commit
**Confidence:** HIGH

## Summary

Phase 1 is pure infrastructure: create a runnable Python project with `uv`, `hatchling`, `src/` layout, and all dev tooling (ruff, mypy, pytest, pytest-asyncio) configured so that subsequent phases can immediately write code, run tests, and lint. The only runtime dependency is `mcp>=1.26.0`. No application code is written beyond a minimal package stub.

The tooling ecosystem is mature and well-documented. All version pins are verified against PyPI as of 2026-03-01. The primary risk area is pre-commit mypy configuration (the `mirrors-mypy` hook has known limitations with third-party deps), but using a `language: system` local hook avoids this cleanly. Everything else is straightforward, well-trodden ground.

**Primary recommendation:** Follow the STACK.md template closely. Use `hatchling` as build backend, configure all tools in `pyproject.toml`, add GitHub Actions CI and pre-commit hooks. Keep the package stub minimal (only `__init__.py` and `__main__.py`).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- mypy in strict mode (`strict = true`) with Pydantic plugin
- Ruff handles both linting AND formatting (replaces black)
- Ruff format: double quotes, consistent style enforced in CI via `ruff format --check`
- Bare minimum files: only `__init__.py` and `__main__.py` in `src/omnifocus_operator/`
- No placeholder modules for future phases — each phase creates its own files
- No empty `models/` or `bridge/` directories yet
- Test directory mirrors src structure: `tests/models/`, `tests/bridge/` subdirectories
- Include a smoke test that imports the package and verifies it loads
- conftest.py present but empty — fixtures added by later phases
- pytest-asyncio configured in auto mode (`asyncio_mode = "auto"`)
- GitHub Actions CI pipeline with: ruff check, ruff format --check, mypy, pytest with coverage
- Coverage threshold: 80% minimum (fail CI below this)
- Pre-commit framework with ruff (lint + format) and mypy hooks
- CI triggers on push to main and on pull requests only
- Single Python version in CI matrix: 3.12
- No task runner — `uv run` commands directly

### Claude's Discretion
- Line length (research suggests 100, curated ruff rule set from research is the baseline)
- Ruff rule set selection (curated set from research: E, F, I, N, UP, B, SIM, TCH, RUF — or broader if justified)
- `__init__.py` contents (version string, docstring, or empty — whatever makes sense)
- `__main__.py` entry point stub (real stub with main() or minimal placeholder)
- `py.typed` marker inclusion (recommended but discretionary)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ARCH-03 | Project uses `uv` with `src/` layout and Python 3.12 | Full coverage: uv project init, hatchling build backend, `src/omnifocus_operator/` layout, `requires-python = ">=3.12"`. See Standard Stack, Architecture Patterns, and Code Examples sections. |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| uv | >=0.10.7 | Package/project manager | Community standard for new Python projects in 2025/2026. Replaces pip, poetry, pyenv, virtualenv. Rust-based, 10-100x faster. MCP SDK's own template uses uv. |
| hatchling | >=1.29.0 | Build backend | Standard PEP 517 build backend. Auto-discovers `src/` layout packages. Well-maintained by PyPA. |
| mcp | >=1.26.0 | MCP server SDK (runtime dep) | Official Model Context Protocol Python SDK. Sole runtime dependency. Brings pydantic, anyio, etc. as transitives. |
| Python | 3.12 | Runtime | Stable, performant, fully supported by all dependencies. Project constraint from REQUIREMENTS.md. |

### Dev Tools

| Tool | Version | Purpose | Notes |
|------|---------|---------|-------|
| ruff | >=0.15.0 (latest: 0.15.4) | Linter + formatter | Replaces flake8, black, isort. Written in Rust. Configure in `pyproject.toml` under `[tool.ruff]`. |
| mypy | >=1.19.1 | Static type checker | Strict mode with Pydantic plugin. Configure in `pyproject.toml` under `[tool.mypy]`. |
| pytest | >=9.0.2 | Test framework | Standard Python testing. Requires Python >=3.10. |
| pytest-asyncio | >=1.3.0 | Async test support | Auto mode eliminates per-test decorators. Version 1.0+ removed deprecated `event_loop` fixture. |
| pytest-cov | >=7.0.0 | Coverage reporting | Integrates coverage.py with pytest. Needed for `--cov-fail-under=80` in CI. |
| pytest-timeout | >=2.4.0 | Test timeout protection | Prevents hanging tests. Global timeout via `pyproject.toml`. |
| pre-commit | >=4.0.0 | Git hook framework | Runs ruff and mypy before commits. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| hatchling | uv_build | uv_build is newer (2025) and tightly integrated with uv, but hatchling is the established choice from STACK.md research. Both auto-discover `src/` layout. Stick with hatchling per prior research decision. |
| hatchling | setuptools | Legacy. More configuration needed for `src/` layout. No advantage over hatchling. |
| pytest-cov | coverage.py directly | pytest-cov integrates seamlessly with pytest CLI and `pyproject.toml`. Using coverage.py directly requires more manual wiring. |

**Installation:**
```bash
# Runtime dependency
uv add "mcp>=1.26.0"

# Dev dependencies
uv add --dev "ruff>=0.15.0"
uv add --dev "mypy>=1.19.1"
uv add --dev "pytest>=9.0.2"
uv add --dev "pytest-asyncio>=1.3.0"
uv add --dev "pytest-cov>=7.0.0"
uv add --dev "pytest-timeout>=2.4.0"
uv add --dev "pre-commit>=4.0.0"
```

## Architecture Patterns

### Recommended Project Structure

This phase creates only the scaffolding files. No application code beyond stubs.

```
omnifocus-operator/
  pyproject.toml              # All config: build, deps, tools
  uv.lock                     # Generated lockfile
  .python-version             # "3.12" — used by uv and CI
  .pre-commit-config.yaml     # ruff + mypy hooks
  .github/
    workflows/
      ci.yml                  # Lint, format check, type check, test
  src/
    omnifocus_operator/
      __init__.py             # Package docstring + version
      __main__.py             # Entry point stub with main()
      py.typed                # PEP 561 marker
  tests/
    __init__.py               # Makes tests a package (for mypy)
    conftest.py               # Empty — fixtures added by later phases
    test_smoke.py             # Import smoke test
```

### Pattern 1: pyproject.toml as Single Config Source

**What:** All tool configuration lives in `pyproject.toml` — no separate `ruff.toml`, `mypy.ini`, `pytest.ini`, `.coveragerc`, or `setup.cfg`.
**When to use:** Always for new projects. Reduces file count and ensures a single source of truth.
**Source:** [uv docs](https://docs.astral.sh/uv/concepts/projects/init), [ruff docs](https://docs.astral.sh/ruff/configuration)

### Pattern 2: src/ Layout with Hatchling Auto-Discovery

**What:** Code lives under `src/omnifocus_operator/`, and hatchling automatically discovers it without explicit `packages` config.
**When to use:** Always for installable packages. Prevents accidental imports of uninstalled code during testing.
**Source:** [Python Packaging Guide](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/), [Scientific Python Dev Guide](https://learn.scientific-python.org/development/guides/packaging-simple/)

### Pattern 3: Console Script Entry Point

**What:** `[project.scripts]` declares `omnifocus-operator = "omnifocus_operator.__main__:main"`, making the package runnable via both `uv run omnifocus-operator` and `python -m omnifocus_operator`.
**When to use:** For any CLI/server entry point.
**Source:** [Python Packaging Guide](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)

### Anti-Patterns to Avoid
- **Flat layout without `src/`:** Causes import confusion between installed package and local source during testing.
- **Multiple config files:** Don't create separate `.ruff.toml`, `mypy.ini`, etc. Everything goes in `pyproject.toml`.
- **`uv_build` instead of `hatchling`:** The prior STACK.md research selected hatchling. Don't switch mid-project without justification.
- **Adding `aiofiles` as a dependency now:** Per STACK.md, use `anyio.open_file()` instead. Runtime deps beyond `mcp` are added in later phases only if needed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Import sorting | Manual import ordering | `ruff` with `I` rule set | Ruff handles isort-compatible import sorting automatically |
| Code formatting | Manual style enforcement | `ruff format` | Replaces black, enforces consistent style automatically |
| Coverage threshold enforcement | Custom CI script checking coverage | `pytest-cov --cov-fail-under=80` | Built-in, declarative, works with pyproject.toml |
| Git hook management | Manual `.git/hooks/` scripts | `pre-commit` framework | Manages hook versions, isolation, and cross-platform compat |
| Python version management in CI | Manual Python install steps | `astral-sh/setup-uv@v7` with `python-version` | Handles uv install, Python version, and caching in one action |

**Key insight:** Every tool in this phase has a `pyproject.toml`-native configuration path. Hand-rolling shell scripts or separate config files creates drift and maintenance burden.

## Common Pitfalls

### Pitfall 1: Pre-commit mypy with mirrors-mypy
**What goes wrong:** The `pre-commit/mirrors-mypy` hook runs mypy in an isolated virtualenv without your project dependencies. It silently adds `--ignore-missing-imports`, which means type errors from third-party deps (like pydantic) become `Any` — you think you have strict type checking but you don't.
**Why it happens:** pre-commit's design isolates each hook. mypy needs to see installed dependencies to check types properly.
**How to avoid:** Use a `local` hook with `language: system` that runs mypy from your project's virtualenv via `uv run mypy`. This ensures mypy sees all installed packages.
**Warning signs:** mypy reports zero errors on code that should have pydantic-related type issues.

### Pitfall 2: pytest-asyncio version mismatch
**What goes wrong:** pytest-asyncio 1.0+ (May 2025) removed the deprecated `event_loop` fixture and changed event loop lifecycle. Old code using `@pytest.fixture` for `event_loop` will break.
**Why it happens:** Major version bump with breaking changes.
**How to avoid:** Use `asyncio_mode = "auto"` in `pyproject.toml` and `pytest-asyncio>=1.3.0`. Never define custom `event_loop` fixtures. Use `loop_scope` parameter on `@pytest.mark.asyncio` if you need non-function-scoped loops.
**Warning signs:** `DeprecationWarning` about event_loop fixture, `RuntimeError: There is no current event loop`.

### Pitfall 3: Coverage fail-under with zero tests
**What goes wrong:** `--cov-fail-under=80` fails immediately when there's only one smoke test and a minimal package stub, because coverage of an almost-empty codebase is unpredictable.
**Why it happens:** Coverage is meaningless with near-zero lines of code.
**How to avoid:** In Phase 1, configure the coverage tooling but set a low threshold or skip enforcement until Phase 2+ when there's real code. Alternatively, ensure the smoke test exercises the `__init__.py` and `__main__.py` imports to hit 100% of the stub code.
**Warning signs:** CI fails on coverage threshold with a package that has 5 lines of code.

### Pitfall 4: pytest-cov config discovery
**What goes wrong:** pytest-cov cannot find `[tool.coverage.*]` settings in `pyproject.toml` unless explicitly told where to look.
**Why it happens:** coverage.py's config discovery differs from pytest's.
**How to avoid:** Pass `--cov-config=pyproject.toml` explicitly in pytest addopts, or set it in `[tool.pytest.ini_options]`.
**Warning signs:** Coverage settings (like `source`, `omit`) are silently ignored.

### Pitfall 5: Ruff format vs ruff check ordering
**What goes wrong:** Running `ruff check --fix` can produce code that needs reformatting. If format runs before check, fixes can undo formatting.
**How to avoid:** In pre-commit, `ruff-check` hook must come BEFORE `ruff-format`. In CI, run `ruff check` first, then `ruff format --check` (check-only mode, no writes).
**Warning signs:** Pre-commit passes but CI fails on format check, or vice versa.

## Code Examples

Verified patterns from official sources:

### pyproject.toml — Complete Configuration

```toml
# Source: STACK.md research + uv/ruff/mypy/pytest official docs
[project]
name = "omnifocus-operator"
version = "0.1.0"
description = "MCP server exposing OmniFocus as structured task infrastructure for AI agents"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "mcp>=1.26.0",
]

[project.scripts]
omnifocus-operator = "omnifocus_operator.__main__:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[dependency-groups]
dev = [
    "ruff>=0.15.0",
    "mypy>=1.19.1",
    "pytest>=9.0.2",
    "pytest-asyncio>=1.3.0",
    "pytest-cov>=7.0.0",
    "pytest-timeout>=2.4.0",
    "pre-commit>=4.0.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
timeout = 10
addopts = [
    "--strict-markers",
    "--cov=omnifocus_operator",
    "--cov-config=pyproject.toml",
    "--cov-report=term-missing",
]

[tool.coverage.run]
source = ["omnifocus_operator"]

[tool.coverage.report]
fail_under = 80
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
]

[tool.mypy]
strict = true
plugins = ["pydantic.mypy"]

[tool.pydantic-mypy]
init_forbid_extra = true
init_typed = true
warn_required_dynamic_aliases = true

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM", "TCH", "RUF"]

[tool.ruff.format]
quote-style = "double"
```

### .pre-commit-config.yaml

```yaml
# Source: astral-sh/ruff-pre-commit (v0.15.4), local mypy hook
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.4
    hooks:
      - id: ruff-check
        args: [--fix]
      - id: ruff-format
  - repo: local
    hooks:
      - id: mypy
        name: mypy
        entry: uv run mypy
        language: system
        types: [python]
        require_serial: true
```

### GitHub Actions CI Workflow

```yaml
# Source: https://docs.astral.sh/uv/guides/integration/github/
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v7
        with:
          enable-cache: true

      - name: Set up Python
        run: uv python install 3.12

      - name: Install dependencies
        run: uv sync --locked --dev

      - name: Lint
        run: uv run ruff check

      - name: Format check
        run: uv run ruff format --check

      - name: Type check
        run: uv run mypy src/

      - name: Test
        run: uv run pytest --cov-fail-under=80
```

### src/omnifocus_operator/__init__.py

```python
"""OmniFocus Operator — MCP server exposing OmniFocus as structured task infrastructure for AI agents."""

__version__ = "0.1.0"
```

### src/omnifocus_operator/__main__.py

```python
"""Entry point for omnifocus-operator."""

from omnifocus_operator.server import main


def main() -> None:
    """Run the OmniFocus Operator MCP server."""
    # Server implementation added in Phase 5
    raise NotImplementedError("Server not yet implemented — see Phase 5")


if __name__ == "__main__":
    main()
```

Note: The `__main__.py` stub should define `main()` directly rather than importing from `server.py` (which doesn't exist yet). The console script entry point (`omnifocus_operator.__main__:main`) points here. The actual server import is wired in Phase 5.

### tests/test_smoke.py

```python
"""Smoke test: verify the package can be imported."""


def test_package_imports() -> None:
    """Verify omnifocus_operator package is importable."""
    import omnifocus_operator

    assert omnifocus_operator.__version__ == "0.1.0"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pip + virtualenv + pip-tools | uv (single tool) | 2024-2025 | 10-100x faster, single lockfile, Python version management included |
| flake8 + black + isort | ruff (single tool) | 2023-2024 | 100-200x faster, single config, drop-in replacement |
| setuptools + setup.py | hatchling + pyproject.toml | 2022-2023 (PEP 621/660) | Declarative config, auto-discovery, no setup.py |
| pytest-asyncio `strict` mode default | `auto` mode recommended | 2025 (v1.0) | No more per-test `@pytest.mark.asyncio` needed |
| pre-commit/mirrors-mypy | Local system hook via uv | 2024-2025 (community shift) | Accurate type checking with project deps visible |
| Poetry for dep management | uv | 2024-2025 | Faster, simpler, growing community standard |

**Deprecated/outdated:**
- `setup.py` / `setup.cfg`: Replaced by `pyproject.toml` (PEP 621). Do not create these files.
- `requirements.txt`: Replaced by `uv.lock`. Do not create this file.
- `MANIFEST.in`: Not needed with hatchling. Build includes are controlled via `pyproject.toml`.
- `tox.ini`: Not needed. `uv run` replaces tox for single-version testing. CI handles the matrix.
- pytest-asyncio `event_loop` fixture: Removed in v1.0. Use `asyncio_mode = "auto"` instead.

## Discretionary Recommendations

These are areas marked as "Claude's Discretion" in CONTEXT.md. Research-backed recommendations:

### Line Length: 100
STACK.md research already suggests 100. This is a good middle ground — wider than black's 88 default (which is cramped for modern wide monitors) but narrower than 120 (which causes horizontal scrolling in side-by-side diffs). Ruff's default is 88, so this must be explicitly set.

### Ruff Rule Set: E, F, I, N, UP, B, SIM, TCH, RUF
The curated set from STACK.md is solid. Each rule set earns its place:
- **E, F**: Core pycodestyle + pyflakes (catches real bugs)
- **I**: isort-compatible import sorting
- **N**: PEP 8 naming conventions
- **UP**: pyupgrade — modernizes syntax to Python 3.12
- **B**: flake8-bugbear — catches common bugs and design problems
- **SIM**: flake8-simplify — suggests simpler code patterns
- **TCH**: flake8-type-checking — moves imports into `TYPE_CHECKING` blocks
- **RUF**: Ruff-specific rules (catches additional patterns)

No need to go broader. This set catches real problems without noisy false positives.

### `__init__.py` Contents: Docstring + Version
Include a module docstring and `__version__ = "0.1.0"`. The version string enables the smoke test to verify the import works with an assertion (`assert omnifocus_operator.__version__`). The docstring describes the package purpose. Keep it minimal — no re-exports.

### `__main__.py`: Real Stub with `main()`
Define a `main()` function that raises `NotImplementedError` with a helpful message. This satisfies the console script entry point (`omnifocus_operator.__main__:main`) and is wired in Phase 5. The `if __name__ == "__main__"` block calls `main()` for `python -m omnifocus_operator` support.

### `py.typed` Marker: Include
Include the `py.typed` marker file (PEP 561). This is a zero-cost signal that the package supports type checking. It enables downstream consumers (and mypy strict mode) to check types when importing `omnifocus_operator`. Recommended by the Python typing community for all typed packages.

## Open Questions

1. **pytest-cov `--cov-fail-under` with stub code**
   - What we know: With only `__init__.py` and `__main__.py` (both ~5 lines), a smoke test that imports the package should hit ~100% coverage of the stub. The 80% threshold should pass.
   - What's unclear: If `__main__.py` has unreachable code paths (like the `NotImplementedError` branch in `main()`), coverage could dip below 80% depending on how it's measured.
   - Recommendation: Set `fail_under = 80` in `pyproject.toml` but verify with `uv run pytest --cov-report=term-missing` after implementation. If coverage is an issue with stubs, add a test that calls `main()` and asserts the `NotImplementedError`. Alternatively, exclude `__main__.py` from coverage for Phase 1 only.

2. **Pre-commit mypy: pass entire `src/` or changed files only?**
   - What we know: mypy benefits from checking the entire project (a change in module A can break types in module B). Running on changed files only misses cross-module issues.
   - What's unclear: Whether `uv run mypy src/` as the entry point (checking all of `src/`) is fast enough for pre-commit, especially as the codebase grows.
   - Recommendation: Start with `uv run mypy src/` (check everything). For a small project like this, it will be fast. Revisit if pre-commit becomes slow in later phases.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest >=9.0.2 + pytest-asyncio >=1.3.0 |
| Config file | `pyproject.toml` under `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest -x` |
| Full suite command | `uv run pytest --cov-fail-under=80` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ARCH-03 | Project uses uv with src/ layout and Python 3.12 | smoke | `uv run pytest tests/test_smoke.py -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest -x`
- **Per wave merge:** `uv run pytest --cov-fail-under=80`
- **Phase gate:** Full suite green + `uv run ruff check` + `uv run ruff format --check` + `uv run mypy src/` before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_smoke.py` — covers ARCH-03 (package import + version check)
- [ ] `tests/conftest.py` — empty, present for structure
- [ ] `tests/__init__.py` — makes tests discoverable by mypy
- [ ] Framework install: `uv sync --dev` — installs pytest, pytest-asyncio, pytest-cov, pytest-timeout

## Sources

### Primary (HIGH confidence)
- [uv docs — project init](https://docs.astral.sh/uv/concepts/projects/init) — src layout, pyproject.toml, dependency groups
- [uv docs — GitHub Actions](https://docs.astral.sh/uv/guides/integration/github/) — CI workflow patterns
- [ruff docs — configuration](https://docs.astral.sh/ruff/configuration) — pyproject.toml config, rule sets, format settings
- [astral-sh/ruff-pre-commit](https://github.com/astral-sh/ruff-pre-commit) — v0.15.4, hook IDs: ruff-check, ruff-format
- [astral-sh/setup-uv](https://github.com/astral-sh/setup-uv) — v7, GitHub Actions integration
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) — FastMCP server setup, pyproject.toml patterns
- [mypy docs — config file](https://mypy.readthedocs.io/en/stable/config_file.html) — strict mode, pyproject.toml config
- [Pydantic docs — mypy integration](https://docs.pydantic.dev/latest/integrations/mypy/) — plugin config, pydantic-mypy settings
- [pytest-asyncio docs — configuration](https://pytest-asyncio.readthedocs.io/en/latest/reference/configuration.html) — asyncio_mode auto
- [pytest-cov docs — configuration](https://pytest-cov.readthedocs.io/en/latest/config.html) — fail_under, cov-config
- [Python Packaging Guide](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) — pyproject.toml, console scripts, src layout

### Secondary (MEDIUM confidence)
- [Jared Khan — mypy pre-commit](https://jaredkhan.com/blog/mypy-pre-commit) — why mirrors-mypy is problematic, local hook pattern
- [Scientific Python Dev Guide](https://learn.scientific-python.org/development/guides/packaging-simple/) — hatchling + src layout best practices
- [pytest-asyncio 1.0 migration](https://thinhdanggroup.github.io/pytest-asyncio-v1-migrate/) — breaking changes in v1.0

### Tertiary (LOW confidence)
- None. All findings verified against primary sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified on PyPI as of 2026-03-01, prior STACK.md research confirmed
- Architecture: HIGH — src/ layout + hatchling + pyproject.toml is the well-established Python standard
- Pitfalls: HIGH — pre-commit mypy gotcha is well-documented; pytest-asyncio 1.0 changes verified via release notes
- CI/pre-commit: HIGH — astral-sh/setup-uv and ruff-pre-commit are official, actively maintained actions

**Research date:** 2026-03-01
**Valid until:** 2026-04-01 (stable domain, 30-day validity)
