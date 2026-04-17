---
created: 2026-04-17T20:18:45.652Z
title: Submit OmniFocus Operator to MCP registries
area: tooling
files:
  - README.md
  - docs/index.html
---

## Problem

OmniFocus Operator is now live on PyPI (v1.4.0, published 2026-04-17) and installable via `uvx omnifocus-operator`. End-to-end validation passed — `list_perspectives` via uvx works against the real OmniFocus database.

What's left from the original PyPI publish todo (Phase 5 — deferred): getting discovered. The MCP ecosystem has a few central directories agents and users search for servers, and OmniFocus Operator isn't listed in any of them yet. Without submissions, the package is findable only by searching PyPI directly or stumbling onto the GitHub repo.

**Gating condition from original todo**: landing page (`docs/index.html`) refresh should happen *before* registry submissions. Rationale: each registry will link back to the landing page as the canonical description, and we want reviewers to see the polished version, not a stale one.

## Solution

### Prerequisites
- [ ] Landing page refresh (`docs/index.html`) — separate todo may be warranted; see follow-ups below
- [ ] Verify PyPI listing still looks correct after any README badge updates (currently says 2086 tests, actual is 2167)

### Registry submissions
- [ ] **Smithery** (https://smithery.ai)
  - Research submission process — likely `smithery.yaml` in repo root
  - Create config file if needed (server command, env vars, transport type)
  - Submit via their flow
- [ ] **mcp.so** (https://mcp.so)
  - Find submission entrypoint (GitHub PR? form? API?)
  - Submit with description, install command, link to landing page
- [ ] **Anthropic's MCP server list** (https://github.com/modelcontextprotocol/servers)
  - Fork the repo
  - Add entry to README.md in the community/third-party section
  - Open PR

### Post-submission
- [ ] Verify each listing appears and links/metadata render correctly
- [ ] Track any moderation feedback or revision requests

### Follow-up (separate todos, not in scope here)
- Choose and add proper license — originally flagged to explore BSL (Business Source License). Current state: `license = "LicenseRef-Proprietary"` in pyproject.toml, "all rights reserved" in README. Goal: free to use, not to commercialize.
- GitHub Pages landing page refresh — update roadmap (v1.4 done), test count (2086 → 2167), install instructions (verify uvx block), tools section (confirm 11 tools still accurate)
- README badge update — test count badge drift (2086 → 2167)
- Automated CHANGELOG generation skill — currently `/update-changelog` runs manually after archive; consider wiring into the archive-milestone workflow

## Context
- Original todo (now completed): `.planning/todos/completed/2026-04-14-publish-on-pypi-and-set-up-automated-releases.md` — captures all decisions made during the PyPI publish journey
- PyPI page: https://pypi.org/project/omnifocus-operator/
- GitHub repo: https://github.com/HelloThisIsFlo/omnifocus-operator
- Landing page: https://hellothisisflo.github.io/omnifocus-operator
