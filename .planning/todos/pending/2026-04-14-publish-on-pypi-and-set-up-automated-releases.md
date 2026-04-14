---
created: 2026-04-14T14:10:14.486Z
title: Publish on PyPI and set up automated releases
area: tooling
files:
  - pyproject.toml
  - src/omnifocus_operator/__init__.py
  - src/omnifocus_operator/__main__.py
  - .github/workflows/publish.yml
  - README.md
  - CONTRIBUTING.md
  - CHANGELOG.md
---

## Problem

OmniFocus Operator is currently install-from-source only (`git clone` + `uv sync`). For public adoption, it needs to be installable via `uvx omnifocus-operator` — zero-install, isolated env, one command in Claude Desktop config.

This todo covers the full journey: account setup → metadata → build validation → CI automation → first publish → registry submissions.

## Execution Mode

**This is a guided walkthrough, NOT autonomous execution.**

The executing agent MUST act as a mentor/guide:
- Walk Flo through each step interactively
- Explain what's happening and why at each step
- Let him run commands himself when appropriate (especially account setup, first publish)
- Pause for verification at each phase boundary
- Surface decisions and trade-offs as they arise

### Multi-Session Checkpoint System

This todo is designed for **multiple sessions**. Each phase ends with a checkpoint. The agent should:
- Summarize what was completed
- State the next phase clearly
- When prose-heavy work is needed (README, CONTRIBUTING, CHANGELOG), **encourage Flo to do it in a separate session** and come back
- On resume, re-read this todo and pick up from the last incomplete phase

## Decisions (from interview)

### Distribution
- **Target**: PyPI, consumed via `uvx omnifocus-operator`
- **Package name**: `omnifocus-operator` — **confirmed available** on PyPI (checked 2026-04-14)
- **PyPI account**: Create new account with `flo@kempenich.ai` (old account has email verification issues — abandoned)

### Versioning
- **Source of truth**: Git tags via `hatch-vcs` plugin (dynamic versioning)
- Remove hardcoded version from both `pyproject.toml` and `__init__.py`
- **First published version**: `v1.3.0` (matches milestone numbering — v1.0–1.2 were internal)
- **Tag format**: `v1.3.0` (with `v` prefix — hatch-vcs default, Python ecosystem standard)
- Between tags, dev versions look like `1.3.1.dev4+g1234567` — only visible in editable installs, never published
- Runtime `__version__` via `importlib.metadata.version("omnifocus-operator")`

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

### Platform & Non-macOS UX
- macOS-only (requires OmniFocus)
- Add `Operating System :: MacOS` classifier
- **Runtime platform check** in `__main__.py:main()` — if not macOS, print clear error and exit
  - Reason: pure Python packages can't prevent installation on other platforms at the packaging level. Classifiers are informational only. A startup check is the only option.

### Build & Packaging
- **Build system**: Hatchling (already configured)
- **Dynamic versioning**: Add `hatch-vcs` as build dependency
- **bridge.js**: Critical non-Python asset in `src/omnifocus_operator/bridge/bridge.js` — must verify inclusion in wheel
- **Explicit exclude list** in pyproject.toml — defensive, nothing unexpected gets in
  - Exclude: tests/, uat/, docs/, .planning/, .github/, .claude/, bridge/ (npm project at root, not the Python bridge module)
- **Pre-publish safety**: Build wheel → inspect contents → verify no personal data, no unexpected files

### CI/CD & Auth
- **Auth method**: Trusted publishing (OIDC) from day one — no API tokens
  - Configure trusted publisher on PyPI website before first publish
  - GitHub Actions workflow is the publish mechanism (push tag → CI builds → CI publishes)
- **Publish workflow**: `.github/workflows/publish.yml`
  - Trigger: tag push matching `v*`
  - Steps: checkout → install uv → run tests (pytest + mypy) → build → publish to PyPI
  - Gate: full test suite must pass before build/publish
- **First publish goes through CI** (push v1.3.0 tag → workflow publishes)

### TestPyPI
- **Skipped.** Go straight to real PyPI.
- Reasoning: mixed-index dependency resolution adds complexity. PyPI allows yanking/deleting recent versions. Low-traffic package — mistakes are cheap to fix.
- Mitigated by pre-publish wheel inspection step.

### README & PyPI Rendering
- Same README for GitHub and PyPI — fix compatibility issues without changing visual appearance
  - Already uses Unicode emoji (not shortcodes) — no changes needed there
  - Convert relative links to absolute GitHub URLs
  - Verify no HTML that cmarkgfm strips
- **Full README refresh** (test counts, roadmap, badges, license badge, install instructions)
  - Done in a **separate session** — agent checkpoints and directs Flo to do prose work independently
- **Install instructions**: Show `uvx` command in Claude Desktop config:
  ```json
  {
    "mcpServers": {
      "omnifocus-operator": {
        "command": "uvx",
        "args": ["omnifocus-operator"]
      }
    }
  }
  ```

### Changelog
- Create `CHANGELOG.md` in [Keep a Changelog](https://keepachangelog.com/) format
- Generate initial content from milestone summaries in `.planning/`
- Consider automating for future releases (skill at milestone close)

### Contributing
- Full refresh of `CONTRIBUTING.md` — target audience: **experienced devs**
- Cover: setup, PR process, key conventions, testing requirements
- Keep it concise — assume they can read the code

### CLI Flags
- **Deferred** — no `--version`, `--check`, or `--help` flags in this todo
- Separate feature if needed later

### Keywords
- omnifocus, mcp, model-context-protocol, task-management, productivity, ai-agent, macos, automation, sqlite, omnijs

### Registries (post-publish, potentially deferred)
- Smithery, mcp.so, Anthropic MCP server list on GitHub
- Submit **after landing page update** — possibly separate todo
- Not necessarily same session as first publish

## Solution

### Phase 1: Account & Build Config
> **Checkpoint**: Flo does these steps himself, agent guides

- [x] Create PyPI account at pypi.org with `flo@kempenich.ai`
- [x] Enable 2FA on PyPI account (required)
- [x] Configure trusted publisher on PyPI for `omnifocus-operator`:
  - Owner: `HelloThisIsFlo`
  - Repository: `omnifocus-operator`
  - Workflow: `publish.yml`
  - Environment: (optional, can use default)
- [x] Add `hatch-vcs` to build dependencies in pyproject.toml
- [x] Switch to dynamic versioning (remove hardcoded version from pyproject.toml and `__init__.py`)
- [x] Update `__init__.py` to use `importlib.metadata.version("omnifocus-operator")`
- [x] Update pyproject.toml metadata:
  - `license = "Proprietary"`
  - Author name + email
  - Classifiers (Python 3.12+, macOS, Framework :: FastMCP, etc.)
  - Keywords
  - URLs (homepage → landing page, repository, issues, documentation)
- [x] Add platform check in `__main__.py` — non-macOS prints clear error and exits
- [x] Configure explicit wheel exclusions in pyproject.toml
- [x] **CHECKPOINT**: Build config complete. Prose work next.

### Phase 2: Docs Refresh (separate session recommended)
> **Agent instruction**: "The README, CONTRIBUTING, and CHANGELOG refresh is best done in a focused session. Go do that separately and come back when you're ready for Phase 3."

- [x] Full README refresh:
  - Update test count and coverage badges
  - Update license badge (MIT → Proprietary or remove)
  - Update roadmap status
  - Update install instructions (show uvx command)
  - Convert relative links to absolute GitHub URLs
  - Verify PyPI markdown compatibility
  - **Note**: Landing page (`docs/index.html`) refreshed alongside README — same numbers, install commands, tools section, roadmap.
- [x] CONTRIBUTING.md refresh (experienced dev audience, concise)
- [x] CHANGELOG.md creation (Keep a Changelog format, from milestone summaries)
- [x] **CHECKPOINT**: All docs ready for publish.

### Phase 3: Build Validation & Pre-Publish Scan
> **Checkpoint**: Verify the package before it goes to PyPI

- [ ] Create a git tag for testing: `v1.3.0` (or current milestone version)
- [ ] `uv build` — build both sdist and wheel
- [ ] Inspect wheel contents — list all files, verify:
  - `bridge.js` is included
  - No test files, docs, .planning, or other non-source files
  - No personal data (OmniFocus task IDs, real names beyond author)
- [ ] Verify README renders correctly (optional: `twine check dist/*`)
- [ ] **CHECKPOINT**: Package is clean and ready.

### Phase 4: CI Workflow & First Publish
> **Checkpoint**: The big moment — first public release

- [ ] Create `.github/workflows/publish.yml`:
  - Trigger: tag push matching `v*`
  - Jobs: test (pytest + mypy) → build → publish
  - Uses trusted publishing (OIDC) — no secrets needed
  - Publish only if tests pass
- [ ] Push the publish workflow to main
- [ ] Push tag `v1.3.0` → CI runs → publishes to PyPI
- [ ] Verify PyPI page: metadata, README rendering, classifiers
- [ ] E2E validation: `uvx omnifocus-operator` → verify server starts and responds to MCP calls
- [ ] **CHECKPOINT**: Published and verified!

### Phase 5: Registries & Discoverability (deferred — after landing page update)
> **Can be a separate todo. Submit when landing page is refreshed.**

- [ ] Research Smithery submission process, create smithery.yaml if needed
- [ ] Submit to mcp.so
- [ ] Submit PR to Anthropic's MCP server list on GitHub
- [ ] Verify listings are live

### Follow-up (separate todos)
- Choose and add proper license (explore BSL)
- Update GitHub Pages landing page
- Consider automated CHANGELOG generation skill
