---
status: complete
phase: 55-notes-graduation
source: [55-01-SUMMARY.md, 55-02-SUMMARY.md, 55-03-SUMMARY.md]
started: 2026-04-17T09:06:35Z
updated: 2026-04-17T11:45:00Z
---

## Mechanical checks (auto-verified)

- `uv run pytest -x -q --no-cov` → **2168 passed**
- `uv run mypy src/` → **Success: no issues found in 79 source files**
- `grep "is_set(command.note)" src/` → **0 matches** (dead normalize_clear_intents branch removed)
- `EDIT_TASKS_TOOL_DOC` size → **2034 bytes** (under 2048-byte DESC-08 limit)

## Current Test

[testing complete]

## Tests

### 1. Design review — NoteAction contract shape
expected: |
  `src/omnifocus_operator/contracts/shared/actions.py:71-87` defines `NoteAction`.
  Validator rejects (append AND replace) and (neither set). Mirrors TagAction.
result: pass
notes: |
  Contract + validator approved — matches TagAction, asymmetry (Patch vs PatchOrClear)
  makes semantic sense.

### 2. Design review — process_note_action decision tree
expected: |
  `src/omnifocus_operator/service/domain.py:531-591`. Key decisions: N3-before-N2
  precedence; asymmetric strip-and-check; D-07 literal-"" is only N1 trigger.
result: pass
notes: |
  Both decisions approved. N3-before-N2: "the more specific one, 100%".
  Asymmetric strip: "defensive".

  **Note**: D-07 was revised post-UAT. See Test 8 and commits `c9ad1329` + `0cb60e58`.
  Whitespace-only append is now N1 (matches OmniFocus normalization).

### 3. Design review — EDIT_TASKS_TOOL_DOC bullet wording
expected: |
  Joint iteration: shrink actions.note to tags-style concision; restore the two
  trimmed repetitionRule lines.
result: pass
notes: |
  Final wording: `actions.note: append or replace content (mutually exclusive).`
  `Remove days` example + `frequency.type omittable` bullet restored.
  Rendered: 2034 bytes (14-byte headroom).

  Commits (split cleanly):
  - `c6568a42` docs(descriptions): restore trimmed repetitionRule lines + trailing period
  - `cad3c615` docs(descriptions): correct _INHERITED_TASKS_EXPLANATION (FIXME fix)

### 4. Test walkthrough — TestNoteAction contract validators
expected: |
  `tests/test_service_domain.py:659` — 4 tests covering D-01 (exclusivity +
  at-least-one) and D-02 (Patch[str] null rejection).
result: pass
notes: |
  Coverage deliberately tight. Micro-gap sentinel declined by agreement
  (transitively protected by TestProcessNoteAction N1 setup).

### 5. Test walkthrough — TestProcessNoteAction decision-tree coverage
expected: |
  `tests/test_service_domain.py:2446` — tests pinned to numbered branches.
result: pass
notes: |
  Walked all branches. Fixed one real issue + 2 micro-gaps during walkthrough
  (commit `20b0d2ac`):
  - Deleted Branch 4 duplicate (Plan 02 auto-fix artifact)
  - Added Branch 15: `replace=""` on whitespace-only existing → N3 (symmetric with Branch 14)
  - Added Branch 16: whitespace append on whitespace-only existing → direct set

  Later revised during Test 8 (commits `c9ad1329` + `0cb60e58`):
  - Branch 7 flipped from "whitespace append is real" to "N1 no-op"
  - Branch 16 flipped from "direct set" to "N1 no-op"
  - Branch 2 assertion updated from `"existing content\n\nadded"` to `"existing content\nadded"`

  Final count: 16 tests in TestProcessNoteAction. Full suite 2168 passed.

### 6. Test walkthrough — end-to-end integration tests
expected: |
  `tests/test_service.py` — 3 new integration tests in `TestEditTask`.
result: pass
notes: |
  Correctly scoped for integration layer. Apparent gaps (bridge-payload not
  inspected, no append+tags composition test, N3 doesn't exercise D-08 at
  integration level) are all correctly delegated to unit layer.

### 7. Test walkthrough — NOTE-01 schema regression
expected: |
  `tests/test_output_schema.py:685` — `test_edit_task_command_has_no_top_level_note`.
result: pass
notes: |
  Two observations surfaced, both actioned (commit `d3e13dec`):
  - Renamed `TestWriteSchemaNoDateTimeFormat` → `TestWriteSchemaShape`
  - Dropped the drive-by `assert "note" not in props` from
    `test_edit_command_schema_nullable_fields` in `test_models.py`.

### 8. Live MCP end-to-end — actions.note against real OmniFocus
expected: |
  Exercise each actions.note branch against the real OmniFocus database via the
  MCP server.
result: pass
notes: |
  All 9 proposed scenarios verified live. Surfaced two production issues that
  required design revision:

  **Scenario H — whitespace-only append behavior (investigated + fixed)**
  - Initial finding: `append="   "` was classified as real change by domain
    (no N1), edit succeeded, but end-to-end note was unchanged.
  - Root cause identified via OmniJS automation console: OmniFocus normalizes
    whitespace-only notes to empty and trims trailing whitespace on write.
    Case 1: `task.note = "   "` stored as `""`.
    Case 2: Replace non-empty with `"   "` → stored as `""`.
    Case 3: `"Existing\n\n   "` stored as `"Existing"` (length 8).
  - **Fix shipped (commit `c9ad1329`)**: `.strip() == ""` check in
    `process_note_action` now fires N1 for whitespace-only append.
  - Agent-facing warning updated: `"Empty or whitespace-only append is a no-op
    (OmniFocus normalizes whitespace to empty) -- omit actions.note.append to
    skip, or pass non-whitespace text to append."`

  **Separator switch — agent controllability (discussed + fixed)**
  - During Scenario H discussion, the append separator came up. Previous
    default `\n\n` couldn't be unpacked to `\n` by agents; `\n` default
    allows agents to prepend their own `\n` for paragraph-break composition.
  - **Fix shipped (commit `0cb60e58`)**: switched to `\n`. Tool description
    updated to explain the agent-prepend pattern.

  **Post-fix live re-verification (after server restart)**
  - `append="Hello"` on empty → `"Hello"` ✓
  - `append="World"` on existing → `"Hello\nWorld"` (single `\n`) ✓
  - `append="   "` → N1 warning with new message text ✓

  **Scenario results:**
  | # | Scenario | Verdict |
  |---|----------|---------|
  | A | append on empty → direct set | ✓ |
  | B | append on existing → `\n` separator (post-fix) | ✓ |
  | C | `append=""` → N1 | ✓ |
  | D | `replace="Totally new"` → set | ✓ |
  | E | `replace` identical → N2 | ✓ |
  | F | `replace=null` on non-empty → clear | ✓ |
  | G | `replace=null` on empty → N3 | ✓ |
  | H | whitespace-only append → **N1 (post-fix)** | ✓ |
  | I | NOTE-01 schema regression | ✓ |

## Summary

total: 8
passed: 8
issues: 0
pending: 0
skipped: 0
blocked: 0

## Commits

Chronological list of commits landed during this UAT session:

- `c6568a42` docs(descriptions): restore trimmed repetitionRule lines + trailing period on actions.note
- `cad3c615` docs(descriptions): correct _INHERITED_TASKS_EXPLANATION with per-field resolution rules
- `20b0d2ac` test(service-domain): tighten TestProcessNoteAction — dedupe + symmetry coverage
- `d3e13dec` test(schema): rename TestWriteSchemaShape + drop redundant NOTE-01 assertion
- `c9ad1329` fix(notes): whitespace-only append fires N1 warning to match OmniFocus behavior
- `0cb60e58` fix(notes): switch append separator from \n\n to \n for agent controllability

## Requirement revisions

- **NOTE-02** revised twice in `.planning/REQUIREMENTS.md` with strikethrough:
  - Empty → Empty or whitespace-only is no-op
  - `\n\n` paragraph separator → `\n` newline separator

## Open follow-up

- **Cleanup pending (human action)** — Flo to manually sweep UAT test tasks under
  the 🗑 DELETE THIS trash task (`huxkCzMOnbq`). Claude-created tasks to clean up:
  - `kOENGKdQVng` (UAT-55 note-graduation, pre-restart)
  - `dk31zttv6rA` (UAT-55 note-graduation, very first session)
  - `c2dzMyARlaD` (UAT-55 whitespace-probe, diagnostic)
  - `kZ7HRVWuiJ6` (UAT-55 re-verify (post-fix))
  - Plus any `UAT-55 OmniJS ws-probe 1/2/3` from the Automation Console
  - Plus any additional probe tasks Flo created during his tangent
