---
id: SEED-006
status: dormant
planted: 2026-03-22
planted_during: v1.2.1 (Architectural Cleanup)
trigger_when: v1.3.1 complete, before starting v1.4
scope: Large
---

# SEED-006: Marketing & landing page milestone — make it official

## Why This Matters

The landing page and marketing copy exist but are in a rough state — built as a quick side project, now outdated as features have evolved significantly through v1.0-v1.2.1. Before pushing on Reddit or going public, the marketing needs to be production-quality and reflect the actual state of the project.

- **Credibility** — rough marketing undermines a polished product. The code is 534+ tests / 94% coverage; the marketing should match that quality bar.
- **Timing** — after v1.3/v1.3.1 (read tools, filtering, search), the feature set is substantial enough to market convincingly
- **Foundation for CLI reframe** — SEED-005 plans to reframe marketing for CLI support later. That reframe is much easier if the marketing is already solid.
- **Living document** — should be refreshed after each major milestone (v1.4, v1.5, etc.) to stay current

## When to Surface

**Trigger:** When v1.3.1 is complete and v1.4 planning begins

This seed should be presented during `/gsd:new-milestone` when the milestone scope matches any of these conditions:
- Post v1.3.1 milestone planning (primary trigger)
- Marketing, landing page, or public launch preparation
- README overhaul or documentation polish
- "Going public" or Reddit launch discussion

**Recurring:** After the initial marketing milestone, consider a lighter refresh pass after each major milestone (v1.4→v1.5, v1.5→v1.6) to keep the page current.

## Scope Estimate

**Large** — Full milestone. Multiple tracks:

1. **Landing page overhaul** — update PAGE.md to reflect current features (v1.0-v1.3.1), architecture, benchmarks. Make it production-quality, not a rough draft.
2. **README polish** — align README with landing page, ensure install instructions are current, update roadmap table
3. **GitHub Pages deploy** — ensure docs/index.html and landing page are properly built and deployed
4. **Supporting assets** — comparison tables (vs other OmniFocus tools), maybe demo GIFs or screenshots
5. **SEO & discoverability** — GitHub topics, description, social preview image

## Breadcrumbs

Related code and decisions found in the current codebase:

**Marketing assets (current state):**
- `.research/page/PAGE.md` — Landing page copy (rough, outdated)
- `README.md` — Current README with "The last OmniFocus MCP Server you'll ever need" tagline
- `docs/index.html` — GitHub Pages entry point

**Documentation:**
- `docs/architecture.md` — Architecture reference (may need updates)
- `docs/configuration.md` — Configuration reference
- `docs/omnifocus-concepts.md` — OmniFocus domain concepts

**Feature specs (what the marketing should reflect):**
- `.research/updated-spec/MILESTONE-v1.3.md` — Read tools spec
- `.research/updated-spec/MILESTONE-v1.3.1.md` — Additional read tools

**Project context:**
- `.planning/PROJECT.md` — Core value proposition and decisions
- `.planning/ROADMAP.md` — Full milestone history and roadmap

## Notes

- The tagline "The last OmniFocus MCP Server you'll ever need" is strong — keep it for the MCP-only phase
- CLI reframe comes later (SEED-005) — this milestone focuses on MCP marketing only
- Consider: comparison with other OmniFocus MCP servers / automation tools to back up the "last you'll ever need" claim
- The landing page should tell a story: problem (OmniFocus is hard to automate) → solution (structured MCP server) → proof (tests, benchmarks, architecture)
- Badge updates: test count, coverage %, dependency count should be dynamic or at least current
