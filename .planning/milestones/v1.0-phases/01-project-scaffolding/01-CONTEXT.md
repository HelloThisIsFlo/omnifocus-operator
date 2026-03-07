# Phase 1: Project Scaffolding - Context

**Gathered:** 2026-03-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Runnable Python project with all tooling configured so that subsequent phases can immediately write code, run tests, and lint. Delivers: pyproject.toml, src layout, dev dependencies, linter/formatter/type checker configuration, test scaffolding, CI pipeline, and pre-commit hooks. No application code beyond a minimal package stub.

</domain>

<decisions>
## Implementation Decisions

### Code style & strictness
- mypy in strict mode (`strict = true`) with Pydantic plugin
- Ruff handles both linting AND formatting (replaces black)
- Ruff format: double quotes, consistent style enforced in CI via `ruff format --check`

### Claude's Discretion
- Line length (research suggests 100, curated ruff rule set from research is the baseline)
- Ruff rule set selection (curated set from research: E, F, I, N, UP, B, SIM, TCH, RUF — or broader if justified)
- `__init__.py` contents (version string, docstring, or empty — whatever makes sense)
- `__main__.py` entry point stub (real stub with main() or minimal placeholder)
- `py.typed` marker inclusion (recommended but discretionary)

### Module structure
- Bare minimum files: only `__init__.py` and `__main__.py` in `src/omnifocus_operator/`
- No placeholder modules for future phases — each phase creates its own files
- No empty `models/` or `bridge/` directories yet

### Test scaffolding
- Test directory mirrors src structure: `tests/models/`, `tests/bridge/` subdirectories
- Include a smoke test that imports the package and verifies it loads
- conftest.py present but empty — fixtures added by later phases
- pytest-asyncio configured in auto mode (`asyncio_mode = "auto"`)

### CI & pre-commit
- GitHub Actions CI pipeline with: ruff check, ruff format --check, mypy, pytest with coverage
- Coverage threshold: 80% minimum (fail CI below this)
- Pre-commit framework with ruff (lint + format) and mypy hooks
- CI triggers on push to main and on pull requests only
- Single Python version in CI matrix: 3.12
- No task runner — `uv run` commands directly

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. The research (STACK.md) has a detailed pyproject.toml template and dependency list that serves as the starting point.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project. No existing code.

### Established Patterns
- Research prescribes: `mcp>=1.26.0` as sole runtime dep, dev deps (ruff, mypy, pytest, pytest-asyncio, pytest-timeout)
- `src/omnifocus_operator/` layout per official MCP server template
- Build system: hatchling
- Console script entry point: `omnifocus-operator = "omnifocus_operator.__main__:main"`

### Integration Points
- pyproject.toml must declare dependencies that all subsequent phases will use
- Test infrastructure must support async tests from Phase 3 onward
- CI pipeline validates every subsequent phase's code automatically

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-project-scaffolding*
*Context gathered: 2026-03-01*
