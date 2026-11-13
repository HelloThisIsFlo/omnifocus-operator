---
phase: 261113-qbo
plan: 01
subsystem: ci-release
status: complete
tags: [ci, github-actions, release, changelog, tooling]
requires: []
provides:
  - "scripts/changelog_release.py: stdlib-only tag classifier + CHANGELOG -> Release notes extractor (standalone CLI)"
  - "publish.yml: patch-gated CHANGELOG preflight in test job; github-release job (needs publish, contents: write)"
  - "mypy strict over scripts/ in just typecheck and pre-commit"
affects:
  - ".github/workflows/publish.yml"
  - "future release-milestone skill (calls the CLI for milestone tags)"
tech-stack:
  added: []
  patterns:
    - "Classify step with id writes kind=patch|milestone to GITHUB_OUTPUT; gated steps use if: steps.kind.outputs.kind == 'patch'"
    - "${{ }} only in env:, never in run: text"
key-files:
  created:
    - scripts/__init__.py
    - scripts/changelog_release.py
    - tests/test_changelog_release.py
  modified:
    - .github/workflows/publish.yml
    - justfile
    - .pre-commit-config.yaml
    - CONTRIBUTING.md
decisions:
  - "Patch tags only get automatic GitHub Releases; milestones skip with a log line from the script (D1)"
  - "Patch tags fail the test job before PyPI if their CHANGELOG section is missing or empty (D2)"
  - "Version matching ignores trailing zeros; only dotted-numeric headings are candidates; ambiguity is an error"
  - "Extract mode creates the notes file's parent directory (only after all checks pass)"
metrics:
  duration: "~6 min"
  completed: 2026-11-13
estimate:
  tokens: 55000
  tasks: 3
actuals:
  tokens: 6000
  tasks: 3
  commits: 4
plan_head_before: c72ba0297e4fa5a65c140a5d40c9ba57d3a285b8
plan_head_after: 9747c96e4aa8619d0cf06bc744750cc784e5a4a9
---

# Phase 261113-qbo Plan 01: Auto-create GitHub Release in publish workflow Summary

Patch tag pushes now create their GitHub Release `vX.Y.Z — <Title>` from CHANGELOG.md right after PyPI, behind a pre-PyPI CHANGELOG preflight; milestone tags skip both green, via a stdlib-only, tested `scripts/changelog_release.py`.

## 🎯 Results

- **Tests:** 57 new in `tests/test_changelog_release.py`; full `just ci` green, **2643 passed**, coverage 97.57%.
- **All-tags parity:** `18 tags, mismatches: []` (v1.0 to v1.4.7, milestones included, D5).
- **mypy strict** now covers `scripts/` (`just typecheck`: 82 source files clean).
- **Workflow gate:** `workflow ok`; `publish` job byte-identical to `ec46a0ce`; `git diff ec46a0ce -- publish.yml` is +45 / -0.

## 🛠️ Workflow steps as committed

**`test` job**, inserted right after `actions/checkout@v5`, before `Install uv`:

- `Classify release tag` (`id: kind`, `env: TAG: ${{ github.ref_name }}`)
  - `kind=$(python3 scripts/changelog_release.py "$TAG" --classify)` then `echo "kind=$kind" >> "$GITHUB_OUTPUT"`
  - Plain assignment, so a junk tag fails the step (bash `-e`).
  - Milestones: the D1 line is printed on stderr here.
- `Preflight CHANGELOG section (patch tags)`
  - `if: steps.kind.outputs.kind == 'patch'`
  - `python3 scripts/changelog_release.py "$TAG" --notes-file "$RUNNER_TEMP/release-notes.md"`
  - Missing or empty section → non-zero → `test` fails → `publish` never starts.
- Existing steps unchanged; no `permissions` block added.

**New `github-release` job** (`needs: publish`, `runs-on: ubuntu-latest`, `permissions: contents: write`):

- `actions/checkout@v5`
- `Classify release tag` (`id: kind`, same as above)
- `Create GitHub Release from CHANGELOG (patch tags)`
  - `if: steps.kind.outputs.kind == 'patch'`
  - `env: TAG: ${{ github.ref_name }}`, `GH_TOKEN: ${{ github.token }}`
  - How the title travels:
    - `title=$(python3 scripts/changelog_release.py "$TAG" --notes-file "$notes")` (stdout = title, notes file = body)
    - a failing extract aborts the step before `gh release create` runs
    - `gh release create "$TAG" --verify-tag --title "$title" --notes-file "$notes"`

## 👀 First real observation

- Patch Release creation: first observed on the **next patch tag push** (e.g. v1.5.1).
- Milestone skip: first observed on the **next milestone tag** (e.g. v1.5.0). Look for `Milestone release (1.5.0): GitHub Release is created by the release-milestone skill after the CHANGELOG is written; skipping.` in both jobs' classify step.
- Nothing in this plan pushed a tag or created a Release.

## 📦 Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 (tracer) | 3fcfb25d | feat: auto-create patch GitHub Releases from CHANGELOG.md |
| 2 RED | 7c3ab33b | test: failing tests for version quirks, body cleanup and refusals |
| 2 GREEN | 1d9cd831 | feat: match tags ignoring trailing zeros; refuse empty or ambiguous sections |
| 3 | 9747c96e | chore: type-check scripts/ and document where Releases come from |

## TDD Gate Compliance

- RED: `7c3ab33b`; 16 of the new tests failed against Task 1's exact-match slice (trailing-zero matching, Unreleased with v1.2 → [1.2.0], cleanup, empty, ambiguity, real-CHANGELOG milestone titles).
- GREEN: `1d9cd831`; 57/57 pass.
- REFACTOR: none needed.

## Deviations from Plan

Design decisions D1-D5 and the planner choices were followed as written.

Minor implementation details within the contract:

- **Extract mode creates the notes file's parent directory** (`mkdir(parents=True, exist_ok=True)`), only after every check passed. Task 1's verify writes to `dist/`, which may not exist. A failure still writes nothing.
- **Extract-mode `ChangelogError` messages append `(in <changelog path>)`**, as the plan's "include the changelog path in extract mode" asks.
- **Test `match=` patterns use `re.escape`** (ruff RUF043). Lint fix only, no behaviour change.

## Threat model check

- T-261113-01: `github-release` has `contents: write` only; `publish` unchanged (gate asserts both).
- T-261113-02: no `${{` in any `run:` text; values arrive via `env:` and quoted `"$VAR"`.
- T-261113-03: `--verify-tag` present.
- T-261113-04: preflight before PyPI; extract failure stops before `gh release create`.
- T-261113-05: stdlib-only imports (negative grep passes).
- No new security surface beyond the threat register.

## Self-Check: PASSED

- FOUND: scripts/__init__.py, scripts/changelog_release.py, tests/test_changelog_release.py
- FOUND commits: 3fcfb25d, 7c3ab33b, 1d9cd831, 9747c96e (all ancestors of HEAD)
