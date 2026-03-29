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

- **Refactoring phases**: UAT should focus on **developer experience**, not "does it still work" (tests cover that). Walk the developer through the result room by room — package layout, naming conventions, import patterns, boundary signatures. The question is "does this make sense to the person who'll maintain it?"
- **Feature phases**: UAT should focus on **user-observable behavior** — does the feature work as expected from the agent's perspective?

## Model Conventions

- **Before creating any new Pydantic model**: Read `docs/architecture.md` naming taxonomy (search "Model taxonomy"). Models in `models/` use no suffix (core) or `Read` suffix (output-boundary variant). Models in `contracts/` must use a write-side suffix (`Command`, `Result`, `RepoPayload`, `RepoResult`, `Action`, `Spec`).
- **After modifying any model that appears in tool output**: Run `uv run pytest tests/test_output_schema.py -x -q` to verify serialized output still validates against MCP outputSchema. This catches `@model_serializer` and `@field_serializer` additions that erase JSON Schema structure.
