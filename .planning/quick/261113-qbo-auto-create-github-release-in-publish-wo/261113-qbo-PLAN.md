---
phase: 261113-qbo
plan: 01
type: execute
mode: quick
wave: 1
depends_on: []
autonomous: true
tags: [ci, github-actions, release, changelog, tooling]
requirements:
  - "quick:261113-qbo (every patch tag push (vX.Y.Z, Z > 0) creates its GitHub Release from CHANGELOG.md with no manual step, behind a pre-PyPI CHANGELOG preflight; milestone tags skip both)"
files_modified:
  - scripts/__init__.py
  - scripts/changelog_release.py
  - tests/test_changelog_release.py
  - .github/workflows/publish.yml
  - justfile
  - .pre-commit-config.yaml
  - CONTRIBUTING.md

estimate:
  tokens: 55000
  raw_tokens: 55000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "A patch tag push (vX.Y.Z with Z > 0) runs test (with a CHANGELOG preflight), then publish (PyPI), then a new github-release job. That job creates the Release '<tag> — <Title>' (em dash; tag as pushed; Title from the CHANGELOG.md heading '## [X.Y.Z] - <Title>'). Its body is that section followed by the Full CHANGELOG footer, created with 'gh release create <tag> --verify-tag --title ... --notes-file ...'."
    - "A milestone tag push (vX.Y.0 or two-part vX.Y) still runs test and publishes to PyPI. The CHANGELOG preflight and the Release creation both skip successfully. The log shows 'Milestone release (X.Y.0): GitHub Release is created by the release-milestone skill after the CHANGELOG is written; skipping.' (per locked decisions 1-2)."
    - "Classification lives in the script, not the YAML: v1.4.7 is patch; v1.5.0, v1.4 and v1.3 are milestone; anything that is not v plus two or three dotted numbers (vfoo, 1.4.7, v1, v1.2.3.4, v1.5.0rc1) fails loudly."
    - "For a patch tag whose CHANGELOG section is missing or empty, the test job fails in the preflight, so nothing reaches PyPI and no release is created."
    - "The github-release job has 'needs: publish' and only 'contents: write'. The publish job is byte-for-byte unchanged (still 'id-token: write' only). The test job keeps its existing steps and permissions. No ${{ }} expression appears inside any run script of either changed job: values reach the shell through env."
    - "Extraction is independent of classification. For every one of the 18 existing tags (v1.0 to v1.4.7, milestones included), the script's title and whitespace-trimmed body equal the hand-made GitHub Release name and body. The CLI stays usable standalone (tag in; title and notes out) for the future release-milestone skill."
    - "The tag/heading quirks resolve: v1.0 matches [1.0.0], v1.3 matches [1.3.0], v1.4 matches [1.4] (as would v1.4.0). v1.4 never matches [1.4.1]. [Unreleased] never matches any tag, even if it carries a ' - Title'."
    - "A missing section, an empty section (after cleanup) or an ambiguous match makes the extractor exit non-zero. Its stderr message names the tag and the expected heading. It writes no notes file."
    - "pytest collects the new tests through 'just ci'. The script passes ruff, and mypy strict through 'just typecheck' and the pre-commit mypy hook. The script imports only the standard library, never the project package."
    - "CONTRIBUTING.md's Versioning section has one line saying GitHub Releases are generated from CHANGELOG.md: patches by CI (the section must exist before tagging), milestones by the release-milestone skill after /gsd-complete-milestone."
  artifacts:
    - path: "scripts/changelog_release.py"
      provides: "Stdlib-only tag classifier (patch vs milestone) and extractor (CHANGELOG.md section for a tag becomes the release title and notes), with a standalone CLI"
      contains: "def classify_tag"
    - path: "scripts/__init__.py"
      provides: "Makes scripts/ a package so pytest and mypy import it as scripts.changelog_release"
    - path: "tests/test_changelog_release.py"
      provides: "Unit tests (synthetic changelogs, CLI via tmp_path) plus guards against the real CHANGELOG.md"
      contains: "from scripts.changelog_release import"
    - path: ".github/workflows/publish.yml"
      provides: "test-job CHANGELOG preflight and github-release job (needs: publish, contents: write), both gated on the patch classification"
      contains: "github-release:"
    - path: "justfile"
      provides: "typecheck recipe covers scripts/"
      contains: "mypy src/ scripts/"
    - path: ".pre-commit-config.yaml"
      provides: "mypy hook covers scripts/ (parity with just typecheck)"
      contains: "mypy src/ scripts/"
    - path: "CONTRIBUTING.md"
      provides: "One Versioning line: Releases come from CHANGELOG.md; patches by CI (section before tagging), milestones by the release-milestone skill"
      contains: "release-milestone"
  key_links:
    - from: ".github/workflows/publish.yml (test and github-release jobs)"
      to: "scripts/changelog_release.py --classify"
      via: "a classify step (with an id) writes kind=patch|milestone to GITHUB_OUTPUT; every notes/release step carries if: steps.<id>.outputs.kind == 'patch'"
      pattern: "--classify"
    - from: ".github/workflows/publish.yml (test job preflight)"
      to: "scripts/changelog_release.py --notes-file"
      via: "for patch tags, extraction runs before just ci; a non-zero exit fails test, so publish never starts"
      pattern: "scripts/changelog_release.py"
    - from: ".github/workflows/publish.yml (github-release job)"
      to: "scripts/changelog_release.py"
      via: "runner python3 runs the CLI with the tag from env (github.ref_name), notes file under RUNNER_TEMP"
      pattern: "scripts/changelog_release.py"
    - from: "scripts/changelog_release.py CLI (title on stdout, notes file)"
      to: "gh release create"
      via: "--title from the captured stdout, --notes-file from the written file, --verify-tag, GH_TOKEN env"
      pattern: "--notes-file"
    - from: "publish.yml test job (just ci)"
      to: "tests/test_changelog_release.py real-CHANGELOG guard"
      via: "an empty versioned section fails the test job before anything reaches PyPI"
      pattern: "CHANGELOG.md"
    - from: "justfile typecheck / .pre-commit-config.yaml mypy hook"
      to: "scripts/"
      via: "mypy strict (pyproject [tool.mypy] strict = true) now runs on scripts/ too"
      pattern: "mypy src/ scripts/"
---

<objective>
Every **patch** tag push (`vX.Y.Z`, Z > 0) should produce its GitHub Release automatically, right after PyPI publishes, with no manual step. A read-only CHANGELOG preflight in the `test` job blocks PyPI when the patch's section is missing or empty. **Milestone** tags (`vX.Y.0`, two-part `vX.Y`) skip both steps successfully, with a clear log line: their Release comes from the separate release-milestone skill, which is not part of this task (locked decisions 1-3). Today `.github/workflows/publish.yml` only builds and uploads to PyPI, and Releases v1.0 to v1.4.7 were all backfilled by hand.

Purpose: patch releases on GitHub stay complete and match CHANGELOG.md without anyone remembering to do it, and a patch can never reach PyPI without its CHANGELOG section.

Output:
- `scripts/changelog_release.py` (+ `scripts/__init__.py`): a small, testable, stdlib-only classifier and extractor, with a CLI that stays usable standalone.
- `tests/test_changelog_release.py`.
- A patch-gated preflight in the `test` job and a least-privilege, patch-gated `github-release` job in `publish.yml`.
- mypy coverage for `scripts/`.
- One line in CONTRIBUTING.md's Versioning section.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.github/workflows/publish.yml
@justfile
@CONTRIBUTING.md

Read on demand:
- `CHANGELOG.md`: headings at lines 7 (`## [Unreleased]`), 9 (`## [1.4.7] - FastMCP 4`), 73 (`## [1.4] - ...`), 124 (`## [1.3.0] - Read Tools`), 183 (`## [1.0.0] - Foundation`, the last section). There are no `---` lines and no link-reference definitions in the file today.
- `setup_operator.py` lines 1-20: the only existing standalone script. Borrow its conventions: a module docstring with a Usage block, `from __future__ import annotations`, stdlib only.
- `pyproject.toml`:
  - `[tool.pytest.ini_options]` (line 88): `testpaths = ["tests"]`, coverage is only `omnifocus_operator`, so the script does not affect `fail_under`.
  - `[tool.mypy]` (line 123): `strict = true`.
  - `[tool.ruff]` (line 132): ruff lints the whole repo except `.research`, `.agents`, `.claude`; the rule set includes `PLC0415`, so imports stay at the top level.
- `.pre-commit-config.yaml`: the local mypy hook's `entry` is `uv run mypy src/`.
- `tests/test_bridge_contract.py` line 25 (`from tests.doubles import InMemoryBridge`): proves pytest puts the repo root on `sys.path` (`tests/` is a package), so `from scripts.changelog_release import ...` resolves once `scripts/__init__.py` exists.

**Facts observed at planning time (2026-11-13, `main` at `ec46a0ce`):**
- `scripts/` does not exist yet; the brief assumed it did. mypy currently runs only on `src/`, both in `just typecheck` (which `just ci` runs) and in the pre-commit hook.
- The reference behaviour below reproduces all 18 live releases exactly. Name equals title, and the trimmed body equals the trimmed body for v1.0 to v1.4.7. This was checked with a throwaway stub through the exact parity command used in Task 2's verify.
- Live release names use the tag as pushed: `v1.3 — Read Tools`, `v1.0 — Foundation`, `v1.4 — Response Shaping & Batch Processing`.
- ruff RUF001/RUF003 do not flag an em dash in strings (probed). `src/` already contains em dashes.
- The `actionlint` on PATH is a mise shim with no version set, so it is unusable without an install. This plan uses a PyYAML structure gate instead (PyYAML is already a dev dependency).
- `gh` is authenticated on this machine. `gh release view` (read-only) works.
- Task 1's workflow gate fails at HEAD with `test: needs exactly one classify step with an id`, which is the expected baseline. It passes on a throwaway candidate `publish.yml` shaped as Task 1 describes (classify step plus patch-gated steps in both jobs). Its "publish job unchanged" and "test job keeps its steps and permissions" assertions already pass at HEAD on purpose: they are preservation checks against `ec46a0ce`.
- `ci.yml` skips pushes that only touch `**.md`. `publish.yml`'s `test` job runs `just ci` on every tag push, before PyPI.
- Why milestones skip (locked decision 1): during the milestone ceremony, the tag is created before the CHANGELOG section is written. On v1.4.1, the tag commit `b05b0aaf` (17:31) does not contain the CHANGELOG commit `e373675c` (17:36), confirmed with `git merge-base --is-ancestor`. So CI could never find a milestone's section.
</context>

## Design decisions (owner-visible)

**Locked with Flo (2026-11-13):**
- 🏷️ **D1: GitHub Releases are automated for patch tags only.**
  - Patch = `vX.Y.Z` with Z > 0. Milestone = `vX.Y.0` or two-part `vX.Y`.
  - For milestones the `github-release` job skips successfully. The log line: `Milestone release (X.Y.0): GitHub Release is created by the release-milestone skill after the CHANGELOG is written; skipping.`
  - The classification lives in the script, where it is testable; the YAML stays thin.
- 🛫 **D2: A pre-PyPI preflight runs for patch tags only.**
  - A read-only step in the `test` job runs the extractor for the pushed tag and fails the job if the section is missing or empty, so PyPI never publishes.
  - For milestones it skips, for the same reason as D1.
- 🔁 **D3: Keep `scripts/` as a package, with tests, and mypy strict extended to `scripts/`.**
  - The release-milestone skill will call the extractor later, so the CLI stays usable standalone: given a tag, it prints the title and writes the notes.
  - Nothing skill-side is built here.
- 📄 **D4: CONTRIBUTING.md gets ONE line in the existing Versioning section, not a Releasing section.**
- 🎯 **D5: The parity gate applies to extraction regardless of classification.** All 18 existing tags, milestones included, must reproduce their live Release.

**Planner choices (within the locked decisions):**
- 📁 **New `scripts/` package.**
  - It holds `changelog_release.py` plus an empty `__init__.py`, so tests import `scripts.changelog_release` and mypy names the module cleanly.
  - No other module goes there.
- 🧮 **Version matching is numeric and ignores trailing zeros.**
  - Only headings whose bracket holds a dotted-numeric version are candidates, so `[Unreleased]` is excluded structurally.
  - A valid tag is `v` plus two or three dotted numbers. A single tag parser feeds both classification and extraction, so both agree on what counts as junk.
  - `1.4` equals `1.4.0` (either direction) but never equals `1.4.1` or `1.40`.
  - More than one matching heading is an error, never a silent first pick.
- ✂️ **A section ends at the next `## ` heading of any kind, or at the end of the file.**
  - This is a safe superset of the reference split (which only split on versioned headings); parity holds 18/18.
- 🐍 **Both new workflow uses (the preflight and the release job) run the runner's preinstalled `python3`, with no uv, setup-python or dependency install.**
  - The script is stdlib-only, so the release job carries no install step, and the preflight can run before the test job's uv setup.
- 🔀 **Workflow gating shape: the same in both changed jobs.**
  - One classify step, with an `id`, writes `kind=patch` or `kind=milestone` to `$GITHUB_OUTPUT`.
  - Every step that extracts notes or creates the release carries `if: steps.<id>.outputs.kind == 'patch'`.
  - Skipped steps leave the job green. Task 1's gate checks this shape.
- 🗣️ **The milestone log line comes from the script.**
  - In `--classify` mode, stdout carries only `patch` or `milestone`; for milestone tags the D1 line goes to stderr.
  - The wording therefore lives in one tested place, not twice in the YAML.
- 🔐 **Least privilege.**
  - A separate `github-release` job holds `contents: write` and nothing else.
  - The `publish` job is untouched: still `id-token: write` only.
  - `${{ }}` expressions appear only in `env:` blocks, never inside `run:` text.
- 🧪 **mypy covers `scripts/`.**
  - The brief asked to check the type config. Since mypy only runs on `src/`, the script would otherwise never be type-checked.
  - Both `just typecheck` and the pre-commit hook get the same change, to stay in parity.
- 🧷 **A real-CHANGELOG guard test checks that every versioned heading yields a non-empty body.**
  - It complements the D2 preflight:
    - the preflight covers the pushed patch tag's own section (missing or empty);
    - the guard catches any empty section already in the file, on every `just ci`.

**Out of scope (not planned):**
- The release-milestone skill, and any creation of milestone Releases (D3).
- Excluding `scripts/` from the sdist. The sdist already ships the justfile, `setup_operator.py` and `.gsd/`, so no convention requires it.
- Pre-release tags (`v1.5.0rc1`). They fail loudly at classification in the `test` job, before PyPI.
- Renaming the workflow.

<tasks>

<task type="tracer">
  <name>Task 1: End-to-end "patch tag v1.4.7 → preflight → GitHub Release; milestone tags skip" through script, tests and workflow</name>
  <files>scripts/__init__.py, scripts/changelog_release.py, tests/test_changelog_release.py, .github/workflows/publish.yml</files>
  <precondition>`gh auth status` succeeds (the verify step reads the live v1.4.7 release, read-only)</precondition>
  <action>
**Script.** Create `scripts/__init__.py` (empty) and `scripts/changelog_release.py`:
- Module docstring with a Usage block, `from __future__ import annotations`, standard library only. To keep SAFE-01 trivially true, it never imports the project package or any bridge module.
- Public contract. Tests and the workflow both depend on these names; internals are up to you:
  - frozen dataclass `ReleaseNotes` with `title: str` and `body: str`
  - exception `ChangelogError`; its message is the user-facing explanation
  - pure function `classify_tag(tag: str) -> Literal["patch", "milestone"]`, raising `ChangelogError` (per D1)
  - pure function `release_for_tag(changelog: str, tag: str) -> ReleaseNotes`, raising `ChangelogError`
  - `main(argv: Sequence[str] | None = None) -> int`, ending in `if __name__ == "__main__": raise SystemExit(main())`
- Tag parsing is shared by both pure functions, so they agree on junk:
  - A valid tag is `v` followed by two or three dot-separated runs of digits (`v1.4`, `v1.4.7`).
  - Anything else raises `ChangelogError` naming the tag, e.g. `vfoo`, `1.4.7` (no `v`), `v1`, `v1.2.3.4`, `v1.5.0rc1`.
- Classification (D1):
  - **patch** = three parts with the third > 0;
  - **milestone** = two parts, or three parts with the third == 0.
  - Examples: `v1.4.7` is patch; `v1.5.0`, `v1.4` and `v1.3` are milestone.
- Headings: match level-2 lines of the form `## [<version>] - <title>` (multiline regex). The section body is the text after that heading line, up to the next line starting with `## ` (any level-2 heading) or the end of the file, whitespace-stripped.
- In this slice, match the tag by exact version: the parsed tag text after `v` equals the bracket text.
- Extraction never consults the classification (D5). It works for milestone tags too, because the future release-milestone skill will call it for them.
- Title: the tag exactly as given, a space, an em dash (U+2014), a space, then the heading title with trailing whitespace stripped. Example: `v1.4.7 — FastMCP 4`.
- Body: the stripped section, then this footer exactly. It is a module constant:
  - footer = two newlines, three hyphens, two newlines, `Full CHANGELOG: https://github.com/HelloThisIsFlo/omnifocus-operator/blob/main/CHANGELOG.md`, one newline
  - The body therefore ends with exactly one newline.
- No matching heading: raise `ChangelogError`. The message names the tag and the expected heading form (`## [X.Y.Z] - <Title>`).

**CLI** (`main`), via argparse. It stays usable standalone (D3):
- Arguments: positional `tag`, plus exactly one of two modes (a required mutually exclusive group):
  - `--notes-file PATH` (extract mode), with optional `--changelog PATH`, default `CHANGELOG.md` relative to the working directory;
  - `--classify` (classify mode); it never reads the CHANGELOG.
- Extract mode, success: write the body to the notes file (UTF-8), print only the title to stdout, return 0.
- Classify mode, success:
  - print exactly `patch` or `milestone` on stdout (one line, nothing else), return 0;
  - for a milestone tag, also print one line to stderr: `Milestone release (X.Y.0): GitHub Release is created by the release-milestone skill after the CHANGELOG is written; skipping.`, where X.Y.0 is the three-part version (`v1.4` gives `1.4.0`) (D1).
- Any `ChangelogError`, or a CHANGELOG that is missing or unreadable:
  - print `error: <message>` to stderr, including the changelog path in extract mode
  - return 1
  - create no notes file (compute everything before writing)

**Tests**, in `tests/test_changelog_release.py`. Use top-level imports (ruff PLC0415), `pytest.raises` for errors, and group by domain in classes. Cover at least:
- classification (D1):
  - `v1.4.7` → patch; `v1.5.0` → milestone; `v1.4` → milestone; `v1.3` → milestone;
  - junk (`vfoo`, `1.4.7`, `v1`, `v1.2.3.4`, `v1.5.0rc1`) raises `ChangelogError`, and so does `release_for_tag` with the same junk;
- `main --classify`:
  - for `v1.4.7`: stdout is `patch`, stderr is empty, returns 0;
  - for `v1.4`: stdout is `milestone`, stderr contains `Milestone release (1.4.0)` and `release-milestone skill`, returns 0;
  - for `vfoo`: returns 1 with an `error:` line;
- the extraction happy path on a small synthetic changelog (title, body, exact footer, one trailing newline);
- no matching section raises `ChangelogError`, and the message contains the tag;
- `main` extract mode with `tmp_path`: writes the notes file, prints the title (capsys), returns 0;
- `main` extract mode on a missing tag: returns 1, prints an `error:` line to stderr, creates no file.

**Workflow** (`.github/workflows/publish.yml`). The `publish` job stays byte-identical. Every new step runs the runner's preinstalled `python3` (no uv, setup-python or dependency install) and gets the tag as `"$TAG"` from `env: TAG: ${{ github.ref_name }}`. Both changed jobs use the same gating shape:
- **Classify step:**
  - one step with an `id` (e.g. `kind`) runs the CLI in `--classify` mode and writes `kind=<stdout>` to `$GITHUB_OUTPUT`;
  - capture the stdout in a variable with a plain assignment first, then append to `$GITHUB_OUTPUT`;
  - never embed the command substitution inside the `echo` arguments: that masks a non-zero exit, and a junk tag must fail the step.
- **Gated steps:** every step that runs extract mode or `gh release create` carries `if: steps.<id>.outputs.kind == 'patch'`. For milestone tags they show as skipped and the job stays green. The classify step's stderr line is the log explanation.
- **`test` job, D2 preflight:**
  - insert the classify step and one gated preflight step right after the existing `actions/checkout@v5`, before `Install uv` (fail fast);
  - the preflight runs extract mode with the notes file under `$RUNNER_TEMP`, purely as a check: missing or empty section means a non-zero exit, so `test` fails and `publish` never starts;
  - existing steps stay unchanged in content and order; no `permissions` block is added.
- **New `github-release` job** (D1):
  - `needs: publish`, `runs-on: ubuntu-latest`, `permissions` exactly `contents: write`;
  - steps: `actions/checkout@v5`; the classify step; then, gated on patch, extract mode (notes file under `$RUNNER_TEMP`, title captured from stdout) and `gh release create "$TAG" --verify-tag --title "<captured title>" --notes-file "<that file>"`, with `GH_TOKEN: ${{ github.token }}` in that step's `env`;
  - extract and create can be one step or two, but every one of them carries the patch `if:`. A non-zero exit from extract must stop the job before `gh release create` runs.
- **Hard rule for both jobs:** no `${{ }}` expression may appear inside any `run:` text. Values reach the shell only through `env:`, which blocks script injection. `if:` conditions are evaluated by Actions, so they need no `${{ }}`.
  </action>
  <verify>
    <automated>uv run pytest --no-cov tests/test_changelog_release.py -q</automated>
    <automated>uv run mypy scripts/</automated>
    <automated>uv run ruff check scripts tests/test_changelog_release.py</automated>
    <automated>uv run ruff format --check scripts tests/test_changelog_release.py</automated>
    <automated>uv run python -c 'import json,subprocess as sp; from scripts.changelog_release import release_for_tag as r; n=r(open("CHANGELOG.md").read(),"v1.4.7"); g=json.loads(sp.run(["gh","release","view","v1.4.7","--json","name,body"],capture_output=True,text=True,check=True).stdout); assert (n.title,n.body.strip())==(g["name"],g["body"].strip()), (n.title,g["name"]); print("v1.4.7 parity ok")'</automated>
    <automated>uv run python scripts/changelog_release.py v1.4.7 --notes-file dist/release-notes-check.md</automated>
    <automated>! uv run python scripts/changelog_release.py v9.9.9 --notes-file dist/release-notes-missing.md</automated>
    <automated>test ! -e dist/release-notes-missing.md</automated>
    <automated>test "$(uv run python scripts/changelog_release.py v1.4.7 --classify)" = patch</automated>
    <automated>test "$(uv run python scripts/changelog_release.py v1.5.0 --classify 2>/dev/null)" = milestone</automated>
    <automated>uv run python scripts/changelog_release.py v1.4 --classify 2>&1 >/dev/null | grep -F "Milestone release (1.4.0)"</automated>
    <automated>! uv run python scripts/changelog_release.py vfoo --classify</automated>
    <automated>uv run python -c 'import subprocess as sp, sys, yaml
w = yaml.safe_load(open(sys.argv[1]))["jobs"]
o = yaml.safe_load(sp.run(["git", "show", "ec46a0ce:.github/workflows/publish.yml"], capture_output=True, text=True, check=True).stdout)["jobs"]
run = lambda s: s.get("run", "")
assert w["publish"] == o["publish"], "publish job changed"
assert w["test"].get("permissions") == o["test"].get("permissions"), "test job permissions changed"
assert all(s in w["test"]["steps"] for s in o["test"]["steps"]), "test job lost or altered an existing step"
def gated(job):
    st = w[job]["steps"]
    assert all("${{" not in run(s) for s in st), job + ": ${{ inside run text"
    c = [s for s in st if "--classify" in run(s)]
    assert len(c) == 1 and c[0].get("id"), job + ": needs exactly one classify step with an id"
    g = [s for s in st if "--notes-file" in run(s) or "gh release create" in run(s)]
    assert g and all(("steps." + c[0]["id"] + ".outputs.") in str(s.get("if", "")) and "patch" in str(s.get("if", "")) for s in g), job + ": notes/release steps not gated on patch"
gated("test")
gated("github-release")
r = w["github-release"]
runs = " ".join(run(s) for s in r["steps"])
assert r["needs"] in ("publish", ["publish"]) and r["permissions"] == {"contents": "write"}, "github-release needs/permissions"
assert all(x in runs for x in ("gh release create", "--verify-tag", "--title", "--notes-file", "scripts/changelog_release.py")), "github-release command"
assert any(s.get("env", {}).get("GH_TOKEN") == "${{ github.token }}" for s in r["steps"]), "GH_TOKEN env"
assert "gh release create" not in " ".join(run(s) for s in w["test"]["steps"]), "test job must not create releases"
print("workflow ok")' .github/workflows/publish.yml</automated>
  </verify>
  <done>
- The v1.4.7 title and body produced by the script match the live GitHub Release.
- Extract mode prints `v1.4.7 — FastMCP 4` and writes the notes file. On `v9.9.9` it exits non-zero with an `error:` message and writes no file.
- Classify mode prints `patch` for `v1.4.7` and `milestone` for `v1.5.0` and `v1.4` (with the D1 line on stderr), and fails on `vfoo`.
- `publish.yml`:
  - the `test` job has a classify step plus a patch-gated preflight before `Install uv` (D2), with its original steps and permissions intact;
  - the new `github-release` job has `needs: publish`, `contents: write` only, a classify step, and patch-gated extract and `gh release create ... --verify-tag` with GH_TOKEN from env (D1);
  - no `${{` appears inside `run:` in either job, and the `publish` job is identical to `ec46a0ce`.
- The new tests pass, and mypy strict and ruff are clean on `scripts/`.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Every historical tag resolves, and broken CHANGELOG sections refuse to publish</name>
  <files>scripts/changelog_release.py, tests/test_changelog_release.py</files>
  <precondition>`gh auth status` succeeds (the all-tags parity verify reads the 18 live releases, read-only)</precondition>
  <behavior>
- Matching ignores trailing zeros (the brief's tag/heading quirks; extraction only, per D5):
  - `v1.3` matches `[1.3.0]`; `v1.4` matches `[1.4]`; `v1.4.0` matches `[1.4]`; `v1.0` matches `[1.0.0]`.
  - `v1.4` does NOT match `[1.4.1]`; `v1.4` does NOT match `[1.40]`.
- `[Unreleased]` never matches:
  - with `## [Unreleased]` (no title) plus a `## [1.2.0] - X` section, tag `v1.2` still gets the 1.2.0 section;
  - a changelog whose only section is `## [Unreleased] - Something` raises "no matching section" for any valid tag (e.g. `v1.0`): Unreleased is never a candidate, even with a title. Junk tags are already covered by Task 1's shared parser.
- Body cleanup (cases a-c are the reference behaviour):
  - (a) a trailing `---` separator line is removed;
  - (b) the first link-reference definition line (`[label]: ` at line start) and everything after it are dropped;
  - (c) when `---` comes right before a link-reference block (the Keep a Changelog footer shape on the last section), both are gone and the body ends at the last real content line;
  - (d) a `---` in the middle of a section is kept.
- Empty section: if a section is empty after cleanup (nothing; only `---`; only link refs), `ChangelogError` is raised and the message says the section is empty.
- Ambiguity: two headings that normalize to the same version (`[1.4]` and `[1.4.0]`) raise `ChangelogError` naming both.
- Real `CHANGELOG.md`, located with `Path(__file__).resolve().parents[1] / "CHANGELOG.md"`:
  - these titles are pinned: `v1.0 — Foundation`, `v1.3 — Read Tools`, `v1.4 — Response Shaping & Batch Processing`, `v1.4.7 — FastMCP 4`;
  - every versioned heading in the file yields a non-empty body. This is the guard that makes `publish.yml`'s `test` job fail on an empty section before PyPI.
  </behavior>
  <action>
- RED: add the tests above to `tests/test_changelog_release.py`. Use synthetic changelogs for every case except the real-CHANGELOG class. Run them and confirm the matching, cleanup, ambiguity and empty-section tests fail against Task 1's exact-match slice.
- GREEN: extend `release_for_tag`:
  - Reuse Task 1's tag parser. Turn the parsed tag and each heading's bracket text into integer tuples, dropping trailing zero components before comparing.
  - Extraction stays independent of `classify_tag` (D5): milestone tags such as `v1.0`, `v1.3` and `v1.4` must extract just like patches.
  - Headings whose bracket text is not dotted digits are never candidates.
  - Apply the body cleanup in an order that satisfies case (c): cut at the first link-reference definition, strip, remove a trailing `---` line, strip again.
  - Raise `ChangelogError` for empty sections and for more than one match.
- Keep these unchanged: every message names the tag and the expected heading form; the CLI contract; the module's stdlib-only imports.
- REFACTOR only if it reads better. Behaviour must stay pinned by the tests.
  </action>
  <verify>
    <automated>uv run pytest --no-cov tests/test_changelog_release.py -q</automated>
    <automated>uv run python -c 'import json,subprocess as sp; from scripts.changelog_release import release_for_tag as r; t=open("CHANGELOG.md").read(); tags=sp.run(["git","tag","--list","v*"],capture_output=True,text=True,check=True).stdout.split(); gh=lambda g: json.loads(sp.run(["gh","release","view",g,"--json","name,body"],capture_output=True,text=True,check=True).stdout); bad=[g for g in tags if (lambda n,x:(n.title,n.body.strip())!=(x["name"],x["body"].strip()))(r(t,g),gh(g))]; print(len(tags),"tags, mismatches:",bad); assert len(tags)>=18 and not bad'</automated>
    <automated>uv run mypy scripts/</automated>
    <automated>uv run ruff check scripts tests/test_changelog_release.py</automated>
    <automated>uv run ruff format --check scripts tests/test_changelog_release.py</automated>
    <automated>! grep -nE '^\s*(from|import) omnifocus_operator' scripts/changelog_release.py</automated>
  </verify>
  <done>
- All 18 existing tags reproduce their live GitHub Release title and body (mismatches: []). Milestones are included, regardless of classification (D5).
- The quirk, Unreleased, cleanup, empty-section and ambiguity tests pass, and the real-CHANGELOG guard passes on today's file.
- The script still imports only the standard library, and mypy strict plus ruff are clean.
  </done>
</task>

<task type="auto">
  <name>Task 3: Type-check scripts/ in CI and pre-commit; one CONTRIBUTING line on where Releases come from</name>
  <files>justfile, .pre-commit-config.yaml, CONTRIBUTING.md</files>
  <action>
- `justfile`: the `typecheck` recipe becomes `uv run mypy src/ scripts/`, so `just ci` (which runs `typecheck`) type-checks the script under the existing strict config (D3). Keep the recipe's comment accurate.
- `.pre-commit-config.yaml`: the local mypy hook's `entry` becomes `uv run mypy src/ scripts/`, in parity with the justfile (D3). Touch nothing else in that file.
- `CONTRIBUTING.md` (D4):
  - add ONE line, or one short bullet, inside the existing `## Versioning` section; no new heading or subsection, and no other edits;
  - it says GitHub Releases are generated from `CHANGELOG.md`: patches automatically by CI (the version's section must exist before tagging), milestones via the release-milestone skill after `/gsd-complete-milestone`;
  - match the file's tone.
  </action>
  <verify>
    <automated>just typecheck</automated>
    <automated>grep -n 'mypy src/ scripts/' justfile</automated>
    <automated>grep -n 'mypy src/ scripts/' .pre-commit-config.yaml</automated>
    <automated>grep -n "release-milestone" CONTRIBUTING.md</automated>
    <automated>grep -n "CHANGELOG.md" CONTRIBUTING.md</automated>
    <automated>uv run python -c 'import subprocess as sp; a, d, _ = sp.run(["git", "diff", "--numstat", "ec46a0ce", "--", "CONTRIBUTING.md"], capture_output=True, text=True, check=True).stdout.split("\t"); assert 1 <= int(a) <= 2 and d == "0", (a, d); print("contributing diff ok")'</automated>
  </verify>
  <done>
- `just typecheck` runs mypy strict over `src/` and `scripts/` and passes.
- The pre-commit mypy hook runs the same command.
- CONTRIBUTING.md's Versioning section gains exactly one line (diff against `ec46a0ce`: 1-2 added, 0 removed). It names CHANGELOG.md, CI for patches (section before tagging) and the release-milestone skill for milestones.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| tag push → GitHub Actions | Tag names and CHANGELOG.md text flow into shell steps that hold a token able to write repo contents |
| github-release job → GitHub API | `contents: write` token creates the public Release |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-261113-01 | Elevation of Privilege | publish.yml job permissions | high | mitigate | Separate `github-release` job with only `contents: write`. The `publish` job stays exactly `id-token: write`. The Task 1 PyYAML gate asserts both |
| T-261113-02 | Tampering | `run:` steps in the test and github-release jobs | medium | mitigate | No `${{ }}` inside `run:` text. Tag, title and token reach the shell only through `env:` and quoted `"$VAR"` use. The classify output is captured by plain assignment, so a failure is never masked. The Task 1 gate asserts no `${{` in run text in either job |
| T-261113-03 | Spoofing | Release bound to a tag | medium | mitigate | `gh release create "$TAG" --verify-tag` refuses to create a tag implicitly. The job runs only on `push: tags: v*` after `publish` succeeds, and only for patch tags (D1) |
| T-261113-04 | Repudiation / integrity | Release content and PyPI/Release consistency | medium | mitigate | For patch tags, the D2 preflight in `test` fails on a missing or empty section before PyPI. Junk tags fail classification in `test`. Missing, empty or ambiguous cases exit non-zero before `gh release create`. Milestones skip by design (D1). Parity with all 18 hand-made releases is checked in Task 2 (D5) |
| T-261113-05 | Tampering | scripts/changelog_release.py importing project code | low | mitigate | Stdlib-only; never imports the project package or bridge modules (SAFE-01). Task 2 verify negative-greps import lines |
| T-261113-SC | Tampering | package installs | low | accept | No new packages, no install step in the new job. The script is stdlib-only and runs on the runner's preinstalled `python3` |
</threat_model>

<verification>
- `just ci` passes:
  - setup-ci, lint (ruff covers `scripts/` and the new test), typecheck (now `src/` and `scripts/`), safety, JS/web tests;
  - pytest with `--cov-fail-under=80`, which collects `tests/test_changelog_release.py` through `testpaths = ["tests"]`.
- `uv run pytest --no-cov tests/test_changelog_release.py -q` is green.
- The all-tags parity command from Task 2 reports `18 tags, mismatches: []`.
- `git diff ec46a0ce -- .github/workflows/publish.yml` shows only additions: the classify and preflight steps in `test`, and the new `github-release` job. The `publish` job is unchanged.
- The real behaviour can only be observed on the next tag push: Release creation on the next patch tag, and the skip on the next milestone tag. Nothing in this plan pushes a tag or creates a release.
</verification>

<success_criteria>
- Patch tag push → test (CHANGELOG preflight) → PyPI publish → GitHub Release `vX.Y.Z — <Title>`, with the CHANGELOG section plus the Full CHANGELOG footer, and no manual step (D1, D2).
- A milestone tag push publishes to PyPI. The preflight and the Release creation skip green, with the D1 log line.
- A patch tag whose section is missing or empty never reaches PyPI (D2).
- The script reproduces all 18 existing releases exactly, milestones included (D5), and tolerates the `v1.3`/`[1.3.0]` and `v1.4`/`[1.4]` quirks. Its CLI works standalone for the future release-milestone skill (D3).
- Least privilege holds: the `publish` job is unchanged, and the release job has `contents: write` only.
- `just ci` collects the new tests, and ruff plus mypy strict cover `scripts/` (D3).
- CONTRIBUTING.md's Versioning section has one line on where Releases come from (D4).
</success_criteria>

<output>
Create `.planning/quick/261113-qbo-auto-create-github-release-in-publish-wo/261113-qbo-SUMMARY.md` when done. Include:
- the final test count and the all-tags parity output line;
- the exact new workflow steps as committed: the `test`-job classify and preflight steps, and the `github-release` job (step names, `if:` conditions, and how the title travels);
- a note that patch Release creation will first be observed on the next patch tag push, and the milestone skip on the next milestone tag (e.g. v1.5.0);
- any deviation from the Design decisions above.
</output>
