---
phase: 260628-jrk
plan: 01
type: execute
mode: quick-full
wave: 1
depends_on: []
autonomous: true
tags: [batch, schema, release]
files_modified:
  - src/omnifocus_operator/config.py
  - tests/test_server.py
  - CHANGELOG.md
  - README.md
  - docs/index.html
  - .planning/STATE.md
must_haves:
  truths:
    - "MAX_BATCH_SIZE is the single source for add_tasks/edit_tasks schema max_length."
    - "DEFAULT_LIST_LIMIT remains 50 and is unrelated to the batch write limit."
    - "Project version is VCS-derived by hatch-vcs; v1.4.4 release identity comes from a git tag."
  artifacts:
    - ".planning/quick/260628-jrk-increase-batch-limit-from-50-to-150-and-/260628-jrk-SUMMARY.md"
    - ".planning/quick/260628-jrk-increase-batch-limit-from-50-to-150-and-/260628-jrk-VERIFICATION.md"
  key_links:
    - "src/omnifocus_operator/config.py"
    - "src/omnifocus_operator/server/handlers.py"
    - "tests/test_server.py"
    - "CHANGELOG.md"
    - "README.md"
    - "docs/index.html"
---

# Quick Task 260628-jrk: Increase Batch Limit to 150 and Release v1.4.4

## Objective

Raise the `add_tasks` / `edit_tasks` batch write limit from 50 to 150 and prepare the v1.4.4 release trail.

<tasks>

<task type="auto">
  <name>Task 1: Raise batch schema limit</name>
  <files>
    src/omnifocus_operator/config.py,
    tests/test_server.py
  </files>
  <action>
  Change `MAX_BATCH_SIZE` from 50 to 150. Update add/edit batch size tests so
  150 is accepted and 151 is rejected. Leave `DEFAULT_LIST_LIMIT` and
  pagination tests unchanged.
  </action>
  <verify>
  `uv run pytest tests/test_server.py -k "batch_150_items_accepted or batch_151_items_rejected_at_schema_level" -q`

  `uv run pytest tests/test_output_schema.py -x -q`
  </verify>
  <done>
  Both write tools enforce `maxItems: 150` through the existing
  FastMCP/Pydantic schema path.
  </done>
</task>

<task type="auto">
  <name>Task 2: Update release surfaces</name>
  <files>
    CHANGELOG.md,
    README.md,
    docs/index.html
  </files>
  <action>
  Move the release note from `[Unreleased]` into
  `[1.4.4] - Batch Limit Increase`. Update roadmap / landing-page version text
  from v1.4.3 to v1.4.4 where it announces the latest shipped release. Keep
  release docs concise. No version-file edit because hatch-vcs owns package
  versioning.
  </action>
  <verify>
  `rg -n "v1\\.4\\.3|1\\.4\\.3|up to 50|50 items|51 items" CHANGELOG.md README.md docs/index.html tests/test_server.py src/omnifocus_operator/config.py`

  Expected remaining hits only for historical v1.4.3 changelog/roadmap entries,
  unrelated default pagination docs, or dependency noise outside this scope.
  </verify>
  <done>
  Reader-facing surfaces identify v1.4.4 as the current batch-limit release.
  </done>
</task>

<task type="auto">
  <name>Task 3: Verify and release tag</name>
  <files>
    .planning/quick/260628-jrk-increase-batch-limit-from-50-to-150-and-/260628-jrk-SUMMARY.md,
    .planning/quick/260628-jrk-increase-batch-limit-from-50-to-150-and-/260628-jrk-VERIFICATION.md,
    .planning/STATE.md
  </files>
  <action>
  Run focused tests plus output schema regression. Commit source/docs changes
  atomically. Write SUMMARY.md and VERIFICATION.md. Update `.planning/STATE.md`
  quick task table with validated status. Commit planning artifacts. Create
  annotated git tag `v1.4.4` on the final release commit.
  </action>
  <verify>
  `uv run pytest tests/test_server.py -k "batch_150_items_accepted or batch_151_items_rejected_at_schema_level" -q`

  `uv run pytest tests/test_output_schema.py -x -q`

  `git tag --list v1.4.4`
  </verify>
  <done>
  Code, release docs, GSD artifacts, and local release tag are present.
  </done>
</task>

</tasks>
