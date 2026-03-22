---
id: SEED-005
status: dormant
planted: 2026-03-22
planted_during: v1.2.1 (Architectural Cleanup)
trigger_when: v1.6 Production Hardening complete and launch preparation begins
scope: Large
---

# SEED-005: CLI adapter + marketing reframe ("last OmniFocus tool you'll ever need")

## Why This Matters

Many people want a CLI instead of (or alongside) MCP. Adding a CLI adapter:
- **Doubles the audience** — OmniFocus power users who script via CLI but don't use AI agents
- **Positions as the definitive tool** — not just "the last MCP server" but "the last OmniFocus CLI" too
- **Trivial to build** — the MCP layer is paper-thin; the CLI is just another adapter over OperatorService
- **Marketing multiplier** — Reddit launch can target both MCP and CLI communities simultaneously

The marketing reframe is equally important: README, landing page, and all copy should position this as "the last OmniFocus MCP server you'll ever need (it's also a CLI)" — making it clear that MCP is primary but CLI is a first-class interface too.

## When to Surface

**Trigger:** When v1.6 Production Hardening is complete and launch preparation begins

This seed should be presented during `/gsd:new-milestone` when the milestone scope matches any of these conditions:
- Launch preparation, public release, or "go to market" milestone
- CLI, command-line, or terminal interface work
- Marketing, README, or landing page overhaul
- Post v1.6 milestone planning

## Scope Estimate

**Large** — Full milestone. Two tracks:

1. **CLI adapter** — entry point, arg parsing, output formatting (table/JSON/plain), error handling, shell completions. Thin technically but needs polish for a good DX.
2. **Marketing reframe** — README, landing page (PAGE.md), tagline, feature comparison, installation docs all need to present both interfaces. Not just find-and-replace; the narrative needs to work for both audiences.

## Breadcrumbs

Related code and decisions found in the current codebase:

**Architecture (why it's easy):**
- `src/omnifocus_operator/server.py` — MCP tool registration; thin wrapper over OperatorService. CLI would mirror this pattern.
- `src/omnifocus_operator/service/service.py` — Service layer the CLI calls into. Protocol-based, no MCP coupling.
- `src/omnifocus_operator/contracts/protocols.py` — `Service` protocol defines the agent-facing interface. CLI is just another consumer.

**Existing CLI precedent:**
- `src/omnifocus_operator/simulator/__main__.py` — Standalone argparse CLI for the simulator. Proves the pattern works.

**Entry points:**
- `pyproject.toml` — Currently has `omnifocus-operator` script entry. CLI would add a second (e.g., `omnifocus` or `ofocus`).

**Marketing assets to update:**
- `README.md` — Current: "The last OmniFocus MCP Server you'll ever need"
- `.research/page/PAGE.md` — Full landing page copy, MCP-focused throughout

**Roadmap context:**
- `.planning/ROADMAP.md` — v1.3-v1.6 planned; CLI fits as v1.7 or v2.0
- README roadmap table lists v1.3-v1.6; CLI would extend this

## Notes

- The vibe for marketing: "The last OmniFocus MCP server you'll ever need (it's also a CLI)" — MCP is primary identity, CLI is the bonus that makes it the definitive tool
- No new business logic needed — CLI is purely an adapter/presentation concern
- Consider: should the CLI command be `omnifocus`, `ofocus`, `of`, or keep `omnifocus-operator`? Shorter = better for CLI users.
- Output formatting is the main work: MCP returns JSON naturally; CLI needs table/tree views for `get_all`, human-readable output for lookups
- Shell completions (bash/zsh/fish) would be a nice touch for a "last CLI" claim
