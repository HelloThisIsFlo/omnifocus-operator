---
phase: 260628-jrk
plan: 01
subsystem: server
tags: [batch, schema, release]
duration_minutes: ~20
completed: 2026-06-28
status: complete
commits:
  - 60e93e50  # docs(260628-jrk): pre-dispatch plan
  - a68e7109  # feat(260628-jrk): increase batch limit to 150 for v1.4.4
diff_stats:
  files_changed: 5
  insertions: 23
  deletions: 17
provides:
  - add_tasks and edit_tasks schema maxItems increased to 150
  - v1.4.4 changelog entry
  - README roadmap row for v1.4.4
  - docs landing badge for v1.4.4
affects:
  - src/omnifocus_operator/config.py
  - tests/test_server.py
  - CHANGELOG.md
  - README.md
  - docs/index.html
decisions:
  - Batch limit source of truth remains MAX_BATCH_SIZE.
  - DEFAULT_LIST_LIMIT stays 50.
  - Package version remains VCS-derived by hatch-vcs.
---

# Quick Task 260628-jrk: Increase Batch Limit to 150 and Release v1.4.4 Summary

## What Shipped

- Batch write cap increased:
  - `MAX_BATCH_SIZE` is now `150`.
  - `add_tasks` / `edit_tasks` keep using the existing `Field(max_length=MAX_BATCH_SIZE)` schema path.

- Test boundaries updated:
  - Add path accepts 150 items and rejects 151.
  - Edit path accepts 150 items and rejects 151.

- Release surfaces updated:
  - `CHANGELOG.md` has `[1.4.4] - Batch Limit Increase`.
  - `README.md` roadmap includes v1.4.4.
  - `docs/index.html` hero badge says `v1.4.4 - Batch Limit Increase`.

## Verification

- `PYTEST_ADDOPTS=--no-cov /Users/flo/.local/bin/uv run pytest tests/test_server.py -k "batch_150_items_accepted or batch_151_items_rejected_at_schema_level" -q`
  - `4 passed, 151 deselected`

- `PYTEST_ADDOPTS=--no-cov /Users/flo/.local/bin/uv run pytest tests/test_output_schema.py -x -q`
  - `35 passed`

- `PYTEST_ADDOPTS=--no-cov /Users/flo/.local/bin/uv run pytest tests/test_server.py -q`
  - `155 passed`

- `PYTEST_ADDOPTS=--no-cov /Users/flo/.local/bin/uv run pytest -q`
  - `2561 passed`

- Pre-commit hooks on implementation commit:
  - ruff check passed
  - ruff format passed
  - mypy passed

## Notes

- First focused pytest run used bare `uv` and exited before meaningful verification because this shell did not have `uv` on `PATH`.
- Re-running with `/Users/flo/.local/bin/uv` passed.
- No version file was edited. `pyproject.toml` uses `hatch-vcs`, so the actual package version comes from the release tag.

## Deviations

- None.

## Self-Check: PASSED

- Files modified:
  - `src/omnifocus_operator/config.py`
  - `tests/test_server.py`
  - `CHANGELOG.md`
  - `README.md`
  - `docs/index.html`

- Files created:
  - `.planning/quick/260628-jrk-increase-batch-limit-from-50-to-150-and-/260628-jrk-SUMMARY.md`
  - `.planning/quick/260628-jrk-increase-batch-limit-from-50-to-150-and-/260628-jrk-VERIFICATION.md`

- Commits verified:
  - `60e93e50`
  - `a68e7109`

- Plan must-haves:
  - Batch limit is 150.
  - Default list pagination remains 50.
  - Release version remains tag-driven.
