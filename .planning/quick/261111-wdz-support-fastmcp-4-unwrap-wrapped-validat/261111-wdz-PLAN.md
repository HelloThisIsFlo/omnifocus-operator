---
phase: 261111-wdz
plan: 01
type: execute
mode: quick
wave: 1
depends_on: []
autonomous: true
tags: [fastmcp, dependency, middleware, validation, mcp-sdk-v2, warnings]
requirements:
  - "todo:2026-11-11-migrate-to-fastmcp-3-4-and-4-and-lift-the-pin (exit condition: suite green on newest 4.x, pin becomes >=4,<5)"
files_modified:
  - pyproject.toml
  - uv.lock
  - src/omnifocus_operator/middleware.py
  - src/omnifocus_operator/server/handlers.py
  - tests/test_middleware.py
  - tests/test_server.py
  - CONTRIBUTING.md

estimate:
  tokens: 60000
  raw_tokens: 60000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "On FastMCP 4, invalid tool input produces the same agent-facing teaching messages as on 3.1-3.3 (for example add_tasks with an extra key bogusField fails with Unknown field 'bogusField'); every existing clean-error test and the canary pass with their assertions unchanged."
    - "A FastMCP ValidationError that wraps a Pydantic ValidationError (as __cause__) is turned into the clean ToolError; a FastMCP ValidationError that wraps nothing, or wraps something other than a Pydantic error, propagates as the very same exception object. Both are pinned by named unit tests."
    - "pyproject.toml requires fastmcp>=4,<5 and uv.lock resolves the newest FastMCP 4.x available at execution time; uv lock --check passes."
    - "No source or test code uses the MCP SDK v1 camelCase names (ToolAnnotations hints, Tool input/output schema); the suite emits zero FastMCP deprecation warnings and also passes with FastMCP's camelCase bridge switched off."
    - "Any FastMCPDeprecationWarning raised during the test run fails the run."
    - "uv run pytest -q and just ci are green on FastMCP 4, including tests/test_output_schema.py."
    - "CONTRIBUTING.md's layout tree names FastMCP 4; historical README roadmap rows, .research/, .planning/ history and the fastmcp-spike-guide skill are untouched."
  artifacts:
    - path: "pyproject.toml"
      provides: "fastmcp>=4,<5 dependency and the FastMCP deprecation error filter"
      contains: "fastmcp>=4,<5"
    - path: "uv.lock"
      provides: "Lock refreshed to the newest FastMCP 4.x (planning-time observation: 4.1.8, MCP SDK 2.3.0)"
    - path: "src/omnifocus_operator/middleware.py"
      provides: "ValidationReformatterMiddleware that unwraps FastMCP's wrapped validation error"
      contains: "class ValidationReformatterMiddleware"
    - path: "src/omnifocus_operator/server/handlers.py"
      provides: "ToolAnnotations built with MCP SDK v2 snake_case field names"
      contains: "read_only_hint"
    - path: "tests/test_middleware.py"
      provides: "TestValidationReformatterMiddleware: wrapped-form regression tests and unchanged-propagation tests"
      contains: "class TestValidationReformatterMiddleware"
  key_links:
    - from: "fastmcp FunctionTool argument validation"
      to: "ValidationReformatterMiddleware.on_call_tool"
      via: "fastmcp.exceptions.ValidationError raised from the Pydantic error (function_tool.py: raise ValidationError(str(e), ...) from e)"
      pattern: "__cause__"
    - from: "ValidationReformatterMiddleware"
      to: "_format_validation_errors"
      via: "the unwrapped Pydantic error is formatted by the existing helper, so messages are byte-identical to the 3.x path"
      pattern: "_format_validation_errors"
    - from: "pyproject.toml [tool.pytest.ini_options] filterwarnings"
      to: "fastmcp.FastMCPDeprecationWarning"
      via: "error:: filter entry (public re-export in fastmcp.__all__)"
      pattern: "error::fastmcp.FastMCPDeprecationWarning"
---

<objective>
Move OmniFocus Operator to FastMCP 4 outright and bring back the agent-facing teaching messages for invalid tool input.

Since FastMCP 3.4, `FunctionTool` converts Pydantic's call-validation error into `fastmcp.exceptions.ValidationError` with the original Pydantic error as `__cause__`. `ValidationReformatterMiddleware` only catches the bare Pydantic error, so on 3.4+ agents get raw Pydantic text instead of messages such as `Unknown field 'bogusField'`. Users reach 3.4+/4.x through `uvx`, which ignores `uv.lock`; v1.4.5 capped the range at `<3.4` as a stopgap.

After this task:
- the middleware unwraps FastMCP's wrapped form, pinned by named regression tests;
- the dependency is `fastmcp>=4,<5`, locked to the newest 4.x;
- source and tests use the MCP SDK v2 names, with no 3.x shims;
- the test run fails on any FastMCP deprecation warning, so the next rename shows up as a red test instead of a buried warning.

Purpose: the project's headline promise is "errors that educate". This restores it on the FastMCP line users actually run, and stops this class of drift from going unnoticed.

Output: updated `pyproject.toml`, `uv.lock`, `middleware.py`, `server/handlers.py`, `CONTRIBUTING.md`; new middleware regression tests; SDK v2 attribute reads in `tests/test_server.py`.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@.planning/todos/pending/2026-11-11-migrate-to-fastmcp-3-4-and-4-and-lift-the-pin.md

@src/omnifocus_operator/middleware.py
@pyproject.toml

Read on demand (large files: use grep, then read the range):
- `tests/test_middleware.py`: helpers `_make_context` (about line 41), `_TestModel` / `_TestListWrapper` / `_capture_validation_error` (about lines 236-258), the `TestFormatValidationErrors` class (about line 334) for style.
- `tests/test_server.py`: `TestCanaryMiddleware` (about line 1789); the clean-error tests (select them with `-k "clean_error or unknown_field or canary"`, 17 tests); camelCase attribute reads at about lines 314, 334, 362, 392, 395, 716-755, 1087-1089, 1734-1776, 1874-2004.
- `src/omnifocus_operator/server/handlers.py`: the eleven `ToolAnnotations(...)` constructions (lines 81-246).
- `tests/conftest.py`: the `server` fixture (about line 491) registers `ValidationReformatterMiddleware` first (innermost), then `ToolLoggingMiddleware`. No change expected.
- `CONTRIBUTING.md` line 17 (layout tree).

**Facts observed at planning time (2026-11-11), in a throwaway clone of `main` at `ca06ac18` relocked to FastMCP 4:**
- `uv lock --upgrade-package fastmcp` resolves **fastmcp 4.1.8** (also the newest on PyPI), fastmcp-slim 4.1.8, **mcp 2.3.0**, new **mcp-types 2.3.0**, starlette 0.52.1 → 1.10.0. It also swaps httpx/httpcore for **httpx2/httpcore2** (pulled by mcp 2.3.0), adds httpx2-jsfetch and truststore, and drops keyring and its jaraco/secretstorage helpers. No new *direct* dependency. PyPI provenance of the new transitive packages: httpx2/httpcore2 from github.com/pydantic/httpx2 (Tom Christie), mcp-types from the MCP project (LF Projects), truststore from Seth Larson.
- A fresh venv imports FastMCP 4 cleanly. In an existing venv, run the sync with `--reinstall-package fastmcp --reinstall-package fastmcp-slim`: the two packages share a folder, and after a lock change `cannot import name 'FastMCP'` can appear (seen 2026-11-11).
- On 4.1.8 with no code changes, 11 tests fail (2572 pass). All are clean-error tests plus `TestCanaryMiddleware::test_canary_middleware_catches_validation_error`.
- On 4.1.8, `uv run mypy src/` **fails with 24 errors**, all in `server/handlers.py`. Under MCP SDK v2 and the pydantic mypy plugin, `ToolAnnotations` accepts only `read_only_hint` / `destructive_hint` / `idempotent_hint` as keyword names. At runtime the camelCase spellings still validate silently (they are the wire aliases: `validate_by_alias=True`), so pytest alone would not catch this. The repo's **pre-commit hook runs `uv run mypy src/`** on every commit that touches Python. So the `handlers.py` rename must land in the same commit as the dependency bump.
- In SDK 2.x, `mcp.types` is a documented mirror of `mcp_types` (same objects, no deprecation). `from mcp.types import ToolAnnotations` stays valid. FastMCP 4 still does not re-export `ToolAnnotations`, so the `TODO(Phase 30)` comment in `handlers.py` stays true.
- FastMCP 4's camelCase bridge (`fastmcp/_compat.py`) puts warn-once properties on SDK classes. Each `(class, attribute)` warns **once per process**, so warning counts undercount. Setting `FASTMCP_MCP_CAMELCASE_COMPAT=false` turns the bridge off: every camelCase read then raises `AttributeError` in every test.
- The suite's camelCase reads: 31 lines, all in `tests/test_server.py`, across five names: `ToolAnnotations` readOnlyHint / idempotentHint / destructiveHint and `Tool` inputSchema / outputSchema. Nothing else in the suite trips the bridge.
- `fastmcp.FastMCPDeprecationWarning` is public (`fastmcp.__all__`; also `fastmcp.exceptions.FastMCPDeprecationWarning`) and subclasses `DeprecationWarning`. Adding `"error::fastmcp.FastMCPDeprecationWarning"` to the pytest `filterwarnings` was tried on the unmigrated `tests/test_server.py`: it failed 5 additional tests, one per distinct camelCase name.
- With the changes in this plan applied in that clone, all of these were green: the full suite (2583 passed, zero warnings in the summary), the run with `FASTMCP_MCP_CAMELCASE_COMPAT=false`, `uv run mypy src/`, `uv run ruff check` and `uv run ruff format --check`.
- A Pydantic error raised *inside a tool body* is wrapped by FastMCP 4 in a private `_ToolBodyError` and reaches clients as `ToolError("Error calling tool 'x': …")`. FastMCP files it as a server-side bug, not a bad call. In this project, agent-input-driven body validation happens only in `add_tasks` / `edit_tasks`, and their handlers already catch it per item (`except (ToolError, ValueError)`; a Pydantic `ValidationError` is a `ValueError`). So no agent-facing message changes.
- `fastmcp list --json` (used by `just schema`) still emits camelCase `inputSchema` / `outputSchema` keys on 4.1.8 (`fastmcp/cli/client.py` around line 561). The justfile's `jq` keeps working; no change.
- Baseline on `main` (FastMCP 3.3.1): 2583 tests pass.
- **GSD planner contributions:** all three skipped.
  - API coverage: skipped. The detector, run over this plan's text, returned `detected: true`, but only on the wording "MCP SDK" and on this note's own "API". Re-reading the scope confirms no external API is integrated: this is a version bump of an existing dependency, so there is no capability matrix to produce. No COVERAGE.md is written for this quick task.
  - Assumption-delta: skipped (`phase_unresolved`: a quick task has no roadmap phase).
  - Schema push: skipped (no ORM schema files).
</context>

## Design decisions (owner-visible)

- **DD-1: the middleware handles the FastMCP 4 shape only.**
  - It catches `fastmcp.exceptions.ValidationError`.
    - Pydantic `__cause__` → formatted by the existing `_format_validation_errors`, then raised as `ToolError` with the chain suppressed, exactly like today.
    - Any other cause, or none → re-raised untouched (same object).
  - The old bare-Pydantic `except` branch is **removed**, per the "no 3.x shims" contract.
    - On FastMCP 4 a FunctionTool's argument-validation error always arrives wrapped (`function_tool.py`: `raise ValidationError(str(e), log_level=logging.WARNING) from e`).
    - All tools here are FunctionTools registered with `@mcp.tool`, so that branch would be dead code.
    - If FastMCP ever changes the shape again, the 17 clean-error tests and the canary go red.
- **DD-2: tool-body Pydantic errors are not reformatted.**
  - FastMCP 4 deliberately classifies them as server bugs (private `_ToolBodyError` → `ToolError`).
  - The middleware must not import or special-case that private class.
  - Agent-facing batch messages are unaffected (see the Facts list).
- **DD-3: the drift gate is one pytest `filterwarnings` entry, `error::fastmcp.FastMCPDeprecationWarning`.**
  - Scoped to FastMCP's own warning class.
    - A blanket `error::DeprecationWarning` would sweep in stdlib and pydantic deprecations, for example Python 3.12's sqlite3 default datetime adapters.
  - Caveat: the camelCase bridge warns once per process, so a regression fails the *first* offending test only. That is enough for a tripwire.
  - Turning the bridge off for the whole test session (`FASTMCP_MCP_CAMELCASE_COMPAT=false`) is stricter per test, but covers only camelCase reads, not other FastMCP deprecations.
    - It is used here once, as a completeness check, not as the permanent gate.
- **DD-4: SDK v2 names everywhere, in source and tests.**
  - `ToolAnnotations` is built with snake_case field names. Mandatory: mypy fails otherwise.
  - Tests read `.read_only_hint`, `.idempotent_hint`, `.destructive_hint`, `.input_schema` and `.output_schema`.
  - Docstrings and comments that name the *wire* fields (outputSchema / inputSchema as protocol concepts) may keep the protocol spelling. Only attribute access changes.

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: FastMCP 4 end-to-end, wrapped validation errors become teaching messages again</name>
  <files>pyproject.toml, uv.lock, src/omnifocus_operator/middleware.py, src/omnifocus_operator/server/handlers.py, tests/test_middleware.py</files>
  <behavior>
    - Test (wrapped form, the regression pin): `call_next` raises a `fastmcp.exceptions.ValidationError` raised `from` a real Pydantic error. Use the existing `_capture_validation_error(_TestListWrapper, {"items": [{"name": "x", "bogus": 1}]})`. The middleware raises `ToolError` whose message equals `"; ".join(_format_validation_errors(pydantic_error))` (that is, `Task 1: Unknown field 'bogus'`). The message contains no "validation error" text.
    - Test (no cause): `call_next` raises a FastMCP `ValidationError("plain")` with no cause. The exception that escapes the middleware **is** the original object (identity check).
    - Test (non-Pydantic cause): `call_next` raises a FastMCP `ValidationError` chained from a `ValueError`. The exception that escapes **is** the original object.
    - Test names state the wrapped form explicitly, so a regression reads clearly in the failure list. Example: `test_fastmcp_wrapped_pydantic_error_becomes_clean_tool_error`.
    - All of these live in a new class `TestValidationReformatterMiddleware` in `tests/test_middleware.py`.
  </behavior>
  <action>
RED first. Add `TestValidationReformatterMiddleware` to `tests/test_middleware.py`, following the file's existing style:
- the `_make_context` helper;
- an `AsyncMock(side_effect=...)` for `call_next`;
- `pytest.raises(ToolError, match=...)` for the reformatting case, `exc_info.value is original` for the propagation cases.

Import FastMCP's error under an alias that cannot be confused with Pydantic's (for example `from fastmcp.exceptions import ValidationError as FastMCPValidationError`). The module already imports Pydantic's `ValidationError`. Run the new tests: the wrapped-form test must fail on current code. Commit the red tests if following the TDD commit cadence. Pre-commit runs mypy, and mypy is still green at this point on FastMCP 3.3.1.

Then move to FastMCP 4, all in ONE commit with the source changes below. Pre-commit's mypy fails on 4.x until `handlers.py` is migrated.
- In `pyproject.toml`, change the dependency to `fastmcp>=4,<5`.
- Run `uv lock --upgrade-package fastmcp`. It must resolve the newest 4.x; 4.1.8 at planning time. Confirm against `https://pypi.org/pypi/fastmcp/json` (`info.version`) and record the resolved fastmcp and mcp versions in the summary.
- Run `uv sync --reinstall-package fastmcp --reinstall-package fastmcp-slim` (the shared-folder cure).

Middleware, per DD-1 and DD-2, in `src/omnifocus_operator/middleware.py`:
- `ValidationReformatterMiddleware.on_call_tool` catches FastMCP's `ValidationError`.
- When `__cause__` is a Pydantic `ValidationError`, build the `ToolError` from it through the existing `_format_validation_errors` and `INVALID_INPUT` fallback, chain suppressed. Messages must be byte-identical to the old path.
- Otherwise re-raise with a bare `raise`.
- Delete the bare-Pydantic `except` branch.
- Leave every helper function unchanged.
- Update the class docstring: it catches FastMCP 4's wrapped validation error and unwraps the Pydantic cause; non-Pydantic causes pass through.

In `src/omnifocus_operator/server/handlers.py`, per DD-4:
- Rewrite all eleven `ToolAnnotations(...)` calls to the snake_case field names `read_only_hint`, `destructive_hint`, `idempotent_hint`. Keep the same values.
- Keep the `from mcp.types import ToolAnnotations` import and its TODO comment.

Do not edit `tests/test_server.py` in this task: Task 2 owns it.

SAFE-01: the new tests use mocks only. In any comment, write "the real Bridge", never the class name.
  </action>
  <verify>
    <automated>uv run python -c "import fastmcp, sys; v = fastmcp.__version__; print(v); sys.exit(0 if v.startswith('4.') else 1)" && uv lock --check && uv run pytest --no-cov -q -p no:cacheprovider tests/test_middleware.py -k TestValidationReformatterMiddleware && uv run pytest --no-cov -q -p no:cacheprovider tests/test_server.py -k "clean_error or unknown_field or canary" && uv run mypy src/</automated>
  </verify>
  <done>
- FastMCP 4.x (newest) is installed and locked; `pyproject.toml` reads `fastmcp>=4,<5`.
- The three new middleware tests pass.
- The 17 clean-error/canary tests pass through the real FastMCP Client on 4.x with unchanged assertions.
- mypy is clean.
- `grep -c 'fastmcp>=4,<5' pyproject.toml` returns 1 (baseline at HEAD: 0).
- `grep -cE '(readOnlyHint|idempotentHint|destructiveHint|openWorldHint)=' src/omnifocus_operator/server/handlers.py` returns 0 (baseline at HEAD: 11).
  </done>
</task>

<task type="auto">
  <name>Task 2: SDK v2 attribute reads in tests, and FastMCP deprecations fail the run</name>
  <files>tests/test_server.py, pyproject.toml</files>
  <action>
In `tests/test_server.py`, per DD-4, switch every attribute read of the five renamed fields to the SDK v2 names: read_only_hint, idempotent_hint, destructive_hint, input_schema, output_schema. That is 31 lines at planning time.
- Change only the attribute access.
- Asserted values, `pytest.raises` blocks and `match=` patterns stay exactly as they are.
- Docstrings and comments that name the protocol fields may keep the protocol spelling.
- Also refresh the docstring of `TestCanaryMiddleware::test_canary_middleware_catches_validation_error` so its explanation names FastMCP's wrapped `ValidationError` (unwrapped by the middleware) rather than `type_adapter.validate_python()`. Docstring only; its assertions stay byte-identical.

In `pyproject.toml` `[tool.pytest.ini_options].filterwarnings`, per DD-3:
- Add the entry `"error::fastmcp.FastMCPDeprecationWarning"`, with a one-line TOML comment above it.
- The comment explains why: users run whatever FastMCP `uvx` resolves, so FastMCP deprecations must fail the suite rather than scroll by.
- Keep the existing PydanticJsonSchemaWarning ignore entry.

Prove once that the gate bites, without committing anything:
- Create a throwaway probe test in a fresh temp directory outside the repo, for example from `mktemp -d`.
- The probe imports fastmcp, then reads the camelCase hint attribute of a `ToolAnnotations` built with `read_only_hint=True`.
- Run it from the repo root with the repo's config: `uv run pytest --no-cov -q -p no:cacheprovider -c pyproject.toml --rootdir . <probe path>`.
- It must fail with `FastMCPDeprecationWarning` in the output. Planning observed exactly this.
- Delete the probe and note the result in the summary.

Completeness check: the camelCase bridge warns only once per process, so also run the whole suite with the bridge switched off, `FASTMCP_MCP_CAMELCASE_COMPAT=false uv run pytest --no-cov -q`. It must be green. A leftover old-name read would raise `AttributeError` there.

If any old-name use cannot be migrated cleanly, do not suppress the warning: stop and explain why in the summary.
  </action>
  <verify>
    <automated>test "$(grep -rnE '\.(inputSchema|outputSchema|readOnlyHint|idempotentHint|destructiveHint|openWorldHint)\b' src tests --include='*.py' | wc -l | tr -d ' ')" -eq 0 && test "$(grep -c 'error::fastmcp.FastMCPDeprecationWarning' pyproject.toml)" -eq 1 && DIFF="$(git diff ca06ac18 -U0 -- tests/test_server.py)" && test -n "$DIFF" && test "$(printf '%s\n' "$DIFF" | grep -E '^[-+][^-+]' | grep -cE 'pytest\.raises|match=')" -eq 0 && FASTMCP_MCP_CAMELCASE_COMPAT=false uv run pytest --no-cov -q -p no:cacheprovider</automated>
  </verify>
  <done>
- Old-name attribute reads in src/tests: 0 (baseline at HEAD: 31).
- Filter entry present: 1 (baseline: 0).
- No `pytest.raises` or `match=` line changed in `tests/test_server.py` (a non-regression guard; 0 at HEAD too).
- The suite passes with the camelCase bridge off. That single run also covers the deprecation gate: the new pyproject entry turns any other FastMCP deprecation into an error.
- The probe result is recorded in the summary.
- The diff guard compares against `ca06ac18`, the planning-time HEAD and an ancestor of every executor branch. It works the same before or after commit, on `main` or in a worktree.
  </done>
</task>

<task type="auto">
  <name>Task 3: Contributor docs name FastMCP 4, full CI gate</name>
  <files>CONTRIBUTING.md</files>
  <action>
In `CONTRIBUTING.md`, change the stale major-version label on the `server/` line of the project-structure tree (line 17) to name FastMCP 4, for example "MCP tool definitions (FastMCP 4)".

Leave untouched:
- the README roadmap rows;
- `.research/` and `.planning/` history;
- `.agents/skills/fastmcp-spike-guide`, a historical spike guide;
- the README test-count badge, CHANGELOG and version labels (the orchestrator owns the release).

Then run the project's required gates on FastMCP 4:
- `uv run pytest tests/test_output_schema.py -x -q`, which the project requires after anything touching tool output or schemas;
- `just ci`, which runs `uv sync --locked --dev`, npm ci for bridge and web, ruff, mypy, the SAFE-01 grep, the JS tests and pytest with the coverage floor.

Record in the summary:
- the final test count and resolved versions;
- the fact that stdio transport and the real lifespan are not covered by the suite and cannot be smoke-tested by an agent (the lifespan builds the real Bridge; SAFE-01/02). The owner's post-release check covers them.
  </action>
  <verify>
    <automated>test "$(grep -c 'FastMCP v3' CONTRIBUTING.md)" -eq 0 && test "$(grep -cE 'FastMCP v?4' CONTRIBUTING.md)" -ge 1 && uv run pytest tests/test_output_schema.py -x -q --no-cov && just ci</automated>
  </verify>
  <done>
- `CONTRIBUTING.md` names FastMCP 4: stale-label count 0 (baseline at HEAD: 1); FastMCP 4 count at least 1 (baseline: 0).
- `tests/test_output_schema.py` and `just ci` are green on FastMCP 4.
  </done>
</task>

</tasks>

<verification>
- `uv run pytest -q` is green on the newest FastMCP 4.x, with no FastMCPDeprecationWarning in the warnings summary. Expected count: the 2583 baseline plus the new middleware tests.
- `FASTMCP_MCP_CAMELCASE_COMPAT=false uv run pytest --no-cov -q` is green.
- `just ci` is green; `uv lock --check` passes.
- `git diff ca06ac18 -- tests/test_server.py` shows only attribute renames, plus at most a docstring refresh in `TestCanaryMiddleware`. No `pytest.raises` or `match=` line differs.
- The tool behaviour change is limited to restoring the teaching messages. `tests/test_output_schema.py` passes.
</verification>

<success_criteria>
- Agents on FastMCP 4 get `Unknown field '…'`-style teaching errors again, and a named regression test guards the wrapped form.
- The dependency is `fastmcp>=4,<5`, locked at the newest 4.x, with no 3.x compatibility code left.
- The next FastMCP deprecation fails the test run instead of hiding in the warnings summary.
- Every check in `just ci` passes.
</success_criteria>

<output>
Create `.planning/quick/261111-wdz-support-fastmcp-4-unwrap-wrapped-validat/261111-wdz-SUMMARY.md` when done. Include:
- the resolved fastmcp and mcp versions;
- the final test count;
- the gate-probe result;
- the camelCase-bridge-off run result;
- the stdio/lifespan note for the owner's manual check.
</output>
