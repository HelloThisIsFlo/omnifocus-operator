# Default: show available recipes
default:
    @just --list --unsorted

# ─── Setup ────────────────────────────────────────────────────────────────────

# Install all dependencies and pre-commit hooks
setup:
    uv sync
    cd bridge && npm install
    uv run pre-commit install

# ─── MCP Install ──────────────────────────────────────────────────────────────

mcp-install:
    uv run python setup_operator.py

mcp-uninstall:
    uv run python setup_operator.py --uninstall

# ─── Testing ──────────────────────────────────────────────────────────────────

# Run tests by keyword (just test-kw add_task or edit): no coverage, no quotes needed
test-kw *expr:
    uv run pytest --no-cov -x -k "{{ expr }}"

# Run all tests (Python + JS)
test-all: test-python test-js
    @echo "All tests passed."

# Run Python tests (extra args forwarded: just test-python -k "foo" -v)
test-python *args='tests/ -x':
    uv run pytest {{ args }}

# Run JS bridge tests
test-js:
    cd bridge && npm test

# Run a single test file without coverage
test-one *args:
    uv run pytest --no-cov {{ args }}

# Run only golden master contract tests
test-gm:
    uv run pytest tests/test_bridge_contract.py -x -v

# Rerun only previously failed tests
test-failed:
    uv run pytest --no-cov --lf -x

# Run tests with HTML coverage report
test-cov:
    uv run pytest tests/ --cov-report=term-missing --cov-report=html
    @echo "HTML report: htmlcov/index.html"

# ─── Code Quality ────────────────────────────────────────────────────────────

# Check linting and formatting (no changes)
lint:
    uv run ruff check
    uv run ruff format --check

# Auto-fix lint issues and reformat
fix:
    uv run ruff check --fix
    uv run ruff format

# Run mypy type checking
typecheck:
    uv run mypy src/

# Run full quality suite: test + lint + typecheck
check-all: test-all lint typecheck

# ─── Running ─────────────────────────────────────────────────────────────────

# Start the MCP server (stdio transport)
serve:
    uv run omnifocus-operator

# Start the simulator
simulator ipc_dir='/tmp/test-ipc':
    uv run python -m omnifocus_operator.simulator --ipc-dir {{ ipc_dir }}

# ─── Logs ────────────────────────────────────────────────────────────────────

# Tail the operator log file
log:
    @touch ~/Library/Logs/omnifocus-operator.log
    tail -f ~/Library/Logs/omnifocus-operator.log

# Clear log and start tailing
log-clear:
    @: > ~/Library/Logs/omnifocus-operator.log
    tail -f ~/Library/Logs/omnifocus-operator.log

# Show last N log lines (default 50)
log-last n='50':
    @tail -n {{ n }} ~/Library/Logs/omnifocus-operator.log

# ─── Golden Master ───────────────────────────────────────────────────────────

# Capture golden master snapshots (runs against LIVE OmniFocus)
[confirm("⚠ This runs against your LIVE OmniFocus database. Continue?")]
capture-gm:
    uv run python uat/capture_golden_master.py

# ─── UAT ─────────────────────────────────────────────────────────────────────

# List available UAT scripts (human-only, never automated)
uat-scripts:
    @echo "⚠ UAT scripts run against LIVE OmniFocus. Human-only per SAFE-02."
    @echo ""
    @ls -1 uat/*.py uat/*.sh

# List UAT regression test suites (Claude skill: /uat-regression)
uat-regression-suites:
    @echo "UAT regression suites (run via /uat-regression in Claude Code):"
    @echo ""
    @ls -1 .claude/skills/uat-regression/tests/

# List doc regression scenarios (Claude skill: /doc-regression)
doc-regression-scenarios:
    @echo "Doc regression scenarios (run via /doc-regression in Claude Code):"
    @echo ""
    @ls -1 .claude/skills/doc-regression/scenarios/

# ─── Dev Tools ───────────────────────────────────────────────────────────────

# Open MCP Inspector connected to the operator
inspect:
    npx @modelcontextprotocol/inspector uv run omnifocus-operator

# ─── Housekeeping ────────────────────────────────────────────────────────────

# Remove caches and build artifacts
clean:
    rm -rf .mypy_cache .pytest_cache .ruff_cache htmlcov .coverage
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# ─── CI ──────────────────────────────────────────────────────────────────────

# SAFE-01: No test may reference RealBridge outside allowed files
safety:
    @violations=$(grep -r "RealBridge" tests/ --include="*.py" --exclude-dir=doubles -l \
        | grep -v "test_smoke\.py" \
        | grep -v "test_ipc_engine\.py" || true); \
    if [ -n "$violations" ]; then \
        echo "$$violations"; \
        echo "ERROR: SAFE-01 violation — test files must not reference RealBridge"; \
        echo "Use InMemoryBridge or SimulatorBridge. Allowed: doubles/, test_smoke.py, test_ipc_engine.py"; \
        exit 1; \
    fi

# Replicate CI pipeline locally (lint/typecheck first = fail fast)
ci: lint typecheck safety test-js
    uv run pytest --cov-fail-under=80
    @echo "CI pipeline passed."
