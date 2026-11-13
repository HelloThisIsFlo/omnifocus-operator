---
name: release-milestone
description: Manual-only repo workflow. Use only when explicitly invoked as release-milestone or by SKILL.md path; do not auto-select from related requests.
---

# Release Milestone

The ceremony that takes a closed milestone out the door: CHANGELOG entry, README and landing page brought up to date, then the GitHub Release.

Run it after `/gsd-complete-milestone`, which archives the milestone and creates its milestone tag (`vX.Y`).

- Why it exists: CI creates GitHub Releases for patch tags only. For a milestone tag it publishes to PyPI and skips the Release, because the CHANGELOG section doesn't exist yet when the tag is created. This skill writes that section and creates the Release.
- Known lag: PyPI renders `README.md` from the tagged commit, so the PyPI page keeps the pre-housekeeping README until the next release. That's accepted.

## 🧭 What the run looks like

1. Check the milestone is ready.
2. Draft the CHANGELOG entry and the housekeeping edits.
3. Flo reviews both together → commit after his yes.
4. Make sure the tag is on GitHub and its publish run is green.
5. Create the GitHub Release after a second yes.
6. Close on what's live and what's still open.

Tell Flo these pauses up front: two yeses, and possibly one push of his own.

## 1. 🔍 Check the milestone is ready

- The target is the milestone `/gsd-complete-milestone` just closed: `milestone:` in `.planning/STATE.md`, and its tag.
  - `{VERSION}` below is that version as tagged, without the `v` (e.g. `1.5`). Only the CHANGELOG heading uses `X.Y.0`.
  - `CHANGELOG.md` already has its section → say so and stop.
- It needs `.planning/milestones/v{VERSION}-MILESTONE-AUDIT.md`.
  - Its `status:` frontmatter is `passed` or `tech_debt` → go ahead; mention the tech debt to Flo.
  - Anything else (e.g. `gaps_found`), or no audit → tell Flo to run `/gsd-audit-milestone` first, and stop.
  - Why: the entry must describe what was verified, not what was planned.

## 2. ✍️ Draft the CHANGELOG entry

- Sources, most trusted first:
  - `.planning/milestones/v{VERSION}-REQUIREMENTS.md` (what was delivered)
  - `.planning/milestones/v{VERSION}-MILESTONE-AUDIT.md` (what was verified)
  - phase summaries in `.planning/milestones/v{VERSION}-phases/`
  - `.research/updated-spec/MILESTONE-v{VERSION}.md` only as background: it's the initial spec and drifts during the milestone.
- Insert it after `## [Unreleased]`, titled `## [X.Y.0] - <milestone subtitle>`, e.g. `## [1.5.0] - Project Writes`.
  - Why: `X.Y.0` is the project's version convention (CONTRIBUTING.md § Versioning). `scripts/changelog_release.py` matches it to the `vX.Y` tag by ignoring trailing zeros.
- Move any `[Unreleased]` items that shipped in this version into the new entry.
- Content:
  - Keep a Changelog categories (Added, Changed, Fixed), only the ones that apply.
  - User-facing changes only: tools, filters, fields, behaviour. Internal refactors only when they change the public API.
  - Breaking changes under Changed, saying clearly what changed.
  - One bullet per feature. Match the tone and density of the entries already there.
- Never invent a change: every bullet traces to the requirements, the audit or a phase summary.

## 3. 🧹 Draft the housekeeping

The README and the landing page (`docs/index.html`) should tell the same story as the Release.

- 🔢 **Test count and coverage**
  - Run `uv run pytest`: the README counts Python tests only (`just test-all` also runs the JS and web suites, which aren't counted).
  - Take the passed count and the `TOTAL` coverage %, rounded down.
  - `grep` for the old numbers in every format: with and without the comma (`2,561`, `2561`), and coverage as both `97%` and `97%25` (the badge URL). Replace every occurrence in both files.
- 🛠️ **Tools**
  - Update the descriptions of tools whose capabilities changed: the README's tool tables and the matching text on the landing page.
  - New tools get new rows, and the tool count changes with them (README's `11 MCP tools`, the landing page's "Eleven tools").
- 🗺️ **Roadmap**
  - Mark the milestone done in both roadmaps: ✅ in the README, the "done" state on the landing page.
  - Reword the row if the shipped scope drifted from the plan: the rows were written from the initial spec.
- 🏷️ **Version label**
  - The landing page's hero badge → `v{VERSION} — <milestone subtitle>`.

## 4. 👀 Review, then commit

- Show Flo, in one message:
  - the CHANGELOG entry in full, in a blockquote;
  - the housekeeping as a short summary of changes per file.
- Commit after his yes: `docs: release notes and housekeeping for v{VERSION}`.

## 5. 🏷️ Create the GitHub Release

- Check both are on GitHub:
  - the tag: `git ls-remote --tags origin v{VERSION}`
  - the release commit: `git status -sb` shows `main` not ahead of `origin/main`. It matters because the notes footer, the README and the landing page are all read from `main`.
  - Anything missing → ask Flo to push, with the exact command in a code block: `git push origin main v{VERSION}`, or `git push origin main` when the tag is already there. Never push yourself: what reaches `main` and when is his call.
- Check the tag's publish run is green: `gh run list --workflow publish.yml --branch v{VERSION}`.
  - Still running → wait for it (`gh run watch <id>`). Failed → stop and show Flo the failed job.
  - Why: a Release for a version that never reached PyPI announces something users can't install. Patch Releases get this guarantee from CI; here it's this check.
- Build the title and notes with the same script CI uses, so milestone and patch Releases share one format:

  ```bash
  python3 scripts/changelog_release.py v{VERSION} --notes-file "$TMPDIR/release-notes.md"
  ```

  It prints the title (`v1.5 — Project Writes`) and writes the notes file.
- Show Flo the title and notes. Create the Release only after his yes:
  - Why a second yes: the Release is public and notifies everyone watching the repository.

  ```bash
  gh release create v{VERSION} --verify-tag --title "<title>" --notes-file "$TMPDIR/release-notes.md"
  ```

## 6. ➡️ Close on what's live and what's open

- What's live: the Release link and the PyPI version.
- What's still open: offer the other post-milestone skills, without running them.
  - `doc-suite-updater`
  - `uat-suite-updater`
- Don't call the release done while those offers are unanswered.
