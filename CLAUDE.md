# OmniFocus Operator

An MCP server exposing OmniFocus as structured task infrastructure for AI agents.

See @README.md for project overview.

## Naming

- Prose: "OmniFocus Operator"
- Slug: `omnifocus-operator`

## Repository

- GitHub: https://github.com/HelloThisIsFlo/omnifocus-operator
- Public repo

## Safety Rules

- **SAFE-01**: No automated test, CI pipeline, or agent execution may touch `RealBridge`. All automated testing MUST use `InMemoryBridge` or `SimulatorBridge` exclusively. The bridge factory (`create_bridge("real")`) raises `RuntimeError` when `PYTEST_CURRENT_TEST` is set. CI enforces this via grep.
  - In comments and docstrings, write `the real Bridge` (two words) instead of `RealBridge` — CI greps for the literal class name and will flag it.
- **SAFE-02**: `RealBridge` interaction is manual UAT only, performed by the human user against their live OmniFocus database. UAT scripts live in `uat/` and must NEVER be run by agents or CI. The `uat/` directory is excluded from pytest discovery and CI execution.

## Service Layer Convention

- All service use cases use the **Method Object pattern** — see `docs/architecture.md` "Method Object Pattern" for full details
- Every use case gets a `_VerbNounPipeline` class inheriting from `_Pipeline`
- Read delegations (get_task, get_project, etc.) stay inline — one-liner pass-throughs, not pipelines
- Mutable state on `self` is fine — the pipeline is created, executed, and discarded within a single call

## UAT Guidelines

- **Shared rules** (apply to both refactoring and feature UAT):
  - Every step must include exact file path and line range — the developer jumps straight to the code, no searching.
  - Adaptive granularity — split or merge steps based on scope. Small change = fewer steps. Large change = one step per semantic block.
  - **New conventions** get their own step — one per new pattern introduced (base classes, protocols, extracted helpers), with a concrete example.
- **Refactoring phases**: UAT should focus on **developer experience**, not "does it still work" (tests cover that). The overarching question: "does this make sense to the person who'll maintain it?" Rooms to cover:
  - **Directory structure & public API** — show the final layout. If small, one step. If large, split per module with exports/signatures at each boundary.
  - **Semantic code walkthrough** — walk through refactored code by semantic block. Point the developer to the code and ask them to explain what it does. If their understanding is correct, pass. If not, the code isn't clear enough — that's a fail. Tests comprehensibility, not just correctness.
  - **Naming audit** — for renamed things, show old → new grouped by domain.
- **Feature phases**: UAT has two parts, in order:
  1. **Test walkthrough** — Walk the developer through the tests room by room before running anything. Split by semantic domain, not by test class — e.g., for a filtering feature, separate steps for status/availability filters, join-based filters (tags, projects), date filters, simple filters, and pagination. The question is "do these tests exercise real scenarios, and do you see any gaps?"
  2. **Run the suite** — Only after the walkthrough. Now `pytest` is meaningful because the developer has seen what's actually being verified.

  End-to-end behavior testing (does the MCP tool work from the agent's perspective?) applies when the feature is wired all the way through. For repository-only or service-only phases, the test walkthrough IS the UAT.

## Model Conventions

- **Before creating any new Pydantic model**: Read `docs/architecture.md` naming taxonomy (search "Model taxonomy"). Models in `models/` use no suffix (core) or `Read` suffix (output-boundary variant). Models in `contracts/` must use a write-side suffix (`Command`, `Result`, `RepoPayload`, `RepoResult`, `Action`, `Spec`).
- **After modifying any model that appears in tool output**: Run `uv run pytest tests/test_output_schema.py -x -q` to verify serialized output still validates against MCP outputSchema. This catches `@model_serializer` and `@field_serializer` additions that erase JSON Schema structure.
