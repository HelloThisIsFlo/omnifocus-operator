---
created: 2026-04-14T14:10:14.486Z
title: Publish on PyPI and set up automated releases
area: tooling
files: []
---

## Problem

OmniFocus Operator is currently install-from-source only (`git clone` + `uv sync`). For public adoption, it needs to be installable via `uvx omnifocus-operator` — zero-install, isolated env, one command in Claude Desktop config.

This todo covers the full journey: metadata preparation → TestPyPI validation → real publish → CI automation → registry submissions.

## Execution Mode

**This is a guided walkthrough, NOT autonomous execution.**

The executing agent MUST act as a mentor/guide:
- Walk Flo through each step interactively
- Explain what's happening and why at each step
- Let him run commands himself when appropriate (especially account setup, token creation, first publish)
- Pause for verification at each phase boundary
- Surface decisions and trade-offs as they arise

## Decisions (from interview)

### Distribution
- **Target**: PyPI, consumed via `uvx omnifocus-operator`
- **PyPI account**: Flo may have one — verify together
- **Package name**: `omnifocus-operator` — check availability on PyPI

### Versioning
- Match internal milestone versioning (v1.0, v1.1, v1.2, etc.)
- First TestPyPI publish: current state (whatever milestone is complete at execution time)
- First real PyPI publish: when current milestone closes
- Automated after that

### License
- **No license for now** (most restrictive — all rights reserved)
- Set `license = "Proprietary"` in pyproject.toml to avoid "UNKNOWN" on PyPI
- **Follow-up (separate todo)**: Explore BSL (Business Source License), then add license file
- Reasoning: can always relax (no license → BSL → MIT), can't restrict after granting MIT
- Core concern: people should use it freely, but not commercialize it. BSL is the leading candidate.
- Websites to explore: tldrlegal.com, choosealicense.com, mariadb.com/bsl-faq, sentry.io/legal/open-source-faq

### Author & Contact
- **Author**: Flo Kempenich
- **Email**: flo@kempenich.ai
- **Motivation**: portfolio visibility, targeting team lead/staff roles

### Platform
- macOS-only (requires OmniFocus)
- Add `Operating System :: MacOS` classifier + README note

### CI/CD
- Existing GitHub Actions CI in place
- **Publish workflow**: GitHub Actions on tag push (e.g., `v1.4.0`)
- **Publish gate**: full test suite (pytest + mypy) before build/publish
- First publish is manual, then automate

### README
- Full refresh before publish — tool list, test counts, roadmap, badges are outdated
- Make GitHub Pages landing page link more prominent
- Landing page update is a SEPARATE task

### Changelog
- Create CHANGELOG.md from milestone summaries
- Consider automating for future releases (skill at milestone close)

### Contributing
- Full refresh of CONTRIBUTING.md — dev setup, PR process, code style, test expectations

### TestPyPI
- Publish to test.pypi.org first
- Full E2E: install via uvx from TestPyPI → server starts → responds to MCP calls

### Registries (post-publish)
- Smithery — research smithery.yaml, submit
- mcp.so — submit listing
- Anthropic MCP server list on GitHub — submit PR

### Keywords (suggested)
- omnifocus, mcp, model-context-protocol, task-management, productivity, ai-agent, macos, automation, sqlite, omnijs

## Solution

### Phase 1: Prepare Metadata
- Verify/create PyPI account together
- Check `omnifocus-operator` name availability
- Update pyproject.toml: version, license="Proprietary", author, email, classifiers, keywords, URLs (homepage, repository, issues, documentation)
- Add macOS classifier and README note
- Full README refresh (tool list, test counts, roadmap, badges)
- Full CONTRIBUTING.md refresh
- Generate CHANGELOG.md from milestone summaries

### Phase 2: Test Publish (TestPyPI)
- Build: `uv build`
- Publish to TestPyPI: `uv publish --index testpypi`
- Verify TestPyPI page (metadata, README rendering)
- E2E: `uvx --index-url https://test.pypi.org/simple/ omnifocus-operator` → verify server starts and responds
- Fix any issues found

### Phase 3: First Real Publish
- When current milestone closes
- `uv build && uv publish`
- Verify PyPI page
- E2E: `uvx omnifocus-operator` → verify server starts and responds
- Update README install instructions (remove "from source" note, add uvx)

### Phase 4: Automate Publishing
- Create `.github/workflows/publish.yml`
- Trigger: tag push matching `v*`
- Steps: checkout → install uv → run tests (pytest + mypy) → build → publish to PyPI
- Use PyPI trusted publishing (OIDC) or API token as GitHub secret
- Test by pushing a tag

### Phase 5: Registries & Discoverability
- Research Smithery submission process, create smithery.yaml if needed
- Submit to mcp.so
- Submit PR to Anthropic's MCP server list on GitHub
- Verify listings are live

### Follow-up (separate todos)
- Choose and add proper license (explore BSL)
- Update GitHub Pages landing page
- Consider automated CHANGELOG generation skill
