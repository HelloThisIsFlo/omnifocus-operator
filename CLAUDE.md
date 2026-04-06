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

- **Philosophy**: UAT answers "can I work with this codebase?" — not just "does it work." This means contract consistency, naming clarity, and architectural coherence are all in scope. Specifically:
  - **Design discussions are first-class UAT outcomes.** When the developer spots an inconsistency (e.g., some filters use names, others use IDs), that's not a tangent — it's the point. Go deep: pros/cons, where it lives architecturally, whether to fix now or capture for later.
  - **Proactively surface decisions.** Don't wait for the developer to ask "why did you do it this way?" — present each design choice with the alternatives considered. If every UAT step is mechanical ("does it import?", "does it serialize?"), the UAT is wrong. Every phase involves decisions — those decisions are what UAT validates.
  - **UAT surfaces downstream decisions.** A contract inconsistency in the repo layer affects every layer above it. Catching it during repo UAT prevents locking in the wrong contract for service/server phases. Actively look for decisions that affect downstream phases.
  - **Every design discussion ends with a concrete outcome**: a todo, a new requirement, a fix now, or a deliberate "this is fine" with reasoning. Never just "noted" and move on.
  - **Don't rush past concerns.** If the developer wants to discuss, that's the most valuable part. Don't log-and-move-on. Don't defer to "future phases" when the developer says it's relevant now.
- **Shared rules** (apply to both refactoring and feature UAT):
  - Every step must include exact file path and line range — the developer jumps straight to the code, no searching.
  - Adaptive granularity — split or merge steps based on scope. Small change = fewer steps. Large change = one step per semantic block.
  - **New conventions** get their own step — one per new pattern introduced (base classes, protocols, extracted helpers), with a concrete example.
- **Structural phases** (refactoring, new foundations, infrastructure — anything without user-facing behavior changes): UAT focuses on **developer experience and design decisions**, not "does it still work" (tests cover that). The overarching question: "does this make sense to the person who'll maintain it?"
  - **Mechanical checks** (imports, values, serialization, test suite) run automatically. Report results in one line; don't present as interactive steps.
  - Rooms to cover, as applicable:
    - **Design decisions** — naming conventions, placement, patterns chosen, trade-offs vs alternatives. Present each for review. These are the core UAT steps.
    - **Directory structure & public API** — show the final layout. If small, one step. If large, split per module with exports/signatures at each boundary.
    - **Semantic code walkthrough** — walk through code by semantic block. Point the developer to the code and ask them to explain what it does. If their understanding is correct, pass. If not, the code isn't clear enough — that's a fail.
    - **Naming audit** — for renamed things, show old → new grouped by domain.
- **Feature phases**: UAT has two parts, in order:
  1. **Test walkthrough** — Walk the developer through the tests room by room before running anything. Split by semantic domain, not by test class — e.g., for a filtering feature, separate steps for status/availability filters, join-based filters (tags, projects), date filters, simple filters, and pagination. The question is "do these tests exercise real scenarios, and do you see any gaps?"
  2. **Run the suite** — Only after the walkthrough. Now `pytest` is meaningful because the developer has seen what's actually being verified.

  End-to-end behavior testing (does the MCP tool work from the agent's perspective?) applies when the feature is wired all the way through. For repository-only or service-only phases, the test walkthrough IS the UAT.

- **Client-side schema validation quirk**: Claude Desktop co-work mode pre-validates tool input against the JSON Schema before sending it to the server. Custom `field_validator` error messages may not appear — the client shows a generic schema error instead. This pre-validation is also depth-limited: shallow fields get caught, deeply nested fields may slip through. Both Claude Desktop (regular) and Claude Code CLI pass input directly to the server, so custom messages always show there. If the developer reports a missing custom error message during UAT, suggest testing via Claude Desktop or Claude Code. See `docs/model-taxonomy.md` for details.

## Model Conventions

- **Before creating any new Pydantic model**: Read `docs/model-taxonomy.md`. Models in `models/` use no suffix (core) or `Read` suffix (output-boundary variant). Models in `contracts/` must use a write-side suffix (`Command`, `Result`, `RepoPayload`, `RepoResult`, `Action`, `Spec`).
- **After modifying any model that appears in tool output**: Run `uv run pytest tests/test_output_schema.py -x -q` to verify serialized output still validates against MCP outputSchema. This catches `@model_serializer` and `@field_serializer` additions that erase JSON Schema structure.
