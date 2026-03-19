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
- **SAFE-02**: `RealBridge` interaction is manual UAT only, performed by the human user against their live OmniFocus database. UAT scripts live in `uat/` and must NEVER be run by agents or CI. The `uat/` directory is excluded from pytest discovery and CI execution.

## UAT Guidelines

- **Refactoring phases**: UAT should focus on **developer experience**, not "does it still work" (tests cover that). Walk the developer through the result room by room — package layout, naming conventions, import patterns, boundary signatures. The question is "does this make sense to the person who'll maintain it?"
- **Feature phases**: UAT should focus on **user-observable behavior** — does the feature work as expected from the agent's perspective?
