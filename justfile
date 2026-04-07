# Default: show available recipes
default:
    @just --list --unsorted

# ─── Setup ────────────────────────────────────────────────────────────────────

# Install all dependencies and pre-commit hooks
setup:
    uv sync
    cd bridge && npm install
    uv run pre-commit install

# ─── Testing ──────────────────────────────────────────────────────────────────

# Run all tests (Python + JS)
test: test-python test-js
    @echo "All tests passed."

# Run Python tests (extra args forwarded: just test-python -k "foo" -v)
test-python *args='tests/ -x':
    uv run pytest {{ args }}

# Run JS bridge tests
test-js:
    cd bridge && npm test

# Run only golden master contract tests
test-gm:
    uv run pytest tests/test_bridge_contract.py -x -v

# Run tests with HTML coverage report
test-cov:
    uv run pytest tests/ --cov-report=term-missing --cov-report=html
    @echo "HTML report: htmlcov/index.html"

# ─── Code Quality ────────────────────────────────────────────────────────────

# Check linting and formatting (no changes)
lint:
    uv run ruff check src/ tests/
    uv run ruff format --check src/ tests/

# Auto-fix lint issues and reformat
fix:
    uv run ruff check --fix src/ tests/
    uv run ruff format src/ tests/

# Run mypy type checking
typecheck:
    uv run mypy src/

# Run full quality suite: test + lint + typecheck
check-all: test lint typecheck

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

# ─── CI ──────────────────────────────────────────────────────────────────────

# Replicate CI pipeline locally (lint/typecheck first = fail fast)
ci: lint typecheck test-python test-js
    @echo "CI pipeline passed."
