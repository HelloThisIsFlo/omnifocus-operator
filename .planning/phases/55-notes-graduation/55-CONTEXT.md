# Phase 55: Notes Graduation - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Notes graduate from top-level setter to `actions.note` block on `edit_tasks` — second field graduation after tags (v1.2.1), following the pattern in `docs/architecture.md` §Field graduation. The `actions.note` action group supports `append` (with `\n\n` paragraph separator) and `replace` operations. Top-level `note` is removed from `edit_tasks` input entirely (pre-release, no compat — see carried-forward decisions). `add_tasks` is untouched — initial note content stays a top-level setter per NOTE-05.

The bridge is **not modified**. All composition (append concatenation, no-op detection, whitespace normalization) lives in the service layer. `EditTaskRepoPayload.note` stays `str | None` — service sends the final composed string as a setter-style payload.

</domain>

<decisions>
## Implementation Decisions

### NoteAction contract shape (Area 1)
- **D-01:** Full `TagAction` parity via `@model_validator(mode="after")`. `append` and `replace` are **mutually exclusive** (cannot coexist in the same action) AND **at least one operation is required** (empty `{}` rejected).
- **D-02:** Types locked by spec (MILESTONE-v1.4.md §Notes Graduation):
  - `append: Patch[str] = UNSET` — null rejected by type, `""` is a no-op (NOTE-02)
  - `replace: PatchOrClear[str] = UNSET` — null and `""` both clear the note (NOTE-03)
- **D-03:** Two new error constants in `agent_messages/errors.py`:
  - `NOTE_APPEND_WITH_REPLACE` — raised when both keys are set. Wording follows `TAG_REPLACE_WITH_ADD_REMOVE` style.
  - `NOTE_NO_OPERATION` — raised when neither key is set. Wording follows `TAG_NO_OPERATION` style.
- **Rationale:** TagAction is the explicit precedent cited in the spec ("following tag action pattern", line 188). Exclusivity prevents a class of agent confusion (`{append: "foo", replace: "bar"}` is ambiguous — replace then append? append then replace?) at the schema boundary. Forcing two separate actions if both are needed is the correct cost.

### No-op warning semantics (Area 2)
Mirror the codebase pattern from `architecture.md` §724 ("Setters — idempotent field replacements. Generic no-op warning when value unchanged") and existing warnings (`MOVE_ALREADY_AT_POSITION`, `LIFECYCLE_ALREADY_IN_STATE`, tag no-op guidance).

All no-op cases **skip the bridge call** and **emit an educational warning**. Status is `"success"` (no-op is not a failure).

- **D-04:** **N1 — Empty append.** `append: ""` → skip bridge, warn. New constant `NOTE_APPEND_EMPTY` (or similar) with guidance like "Empty append is a no-op — omit actions.note.append to skip".
- **D-05:** **N2 — Identical-content replace.** `replace: "<string identical to current note>"` → skip bridge, warn. New constant e.g. `NOTE_REPLACE_ALREADY_CONTENT` with guidance "Note already has this content — omit actions.note.replace to skip".
- **D-06:** **N3 — Clear already-empty.** `replace: null` OR `replace: ""` on a note that is empty or whitespace-only (after strip) → skip bridge, warn. New constant e.g. `NOTE_ALREADY_EMPTY` with guidance "Note is already empty — omit actions.note.replace to skip".
- **D-07:** **N4 — Duplicate append NOT detected.** `append: "foo"` on a note ending in `"foo"` produces `"foo\n\nfoo"` and is a genuine state change. Append's contract is concatenation, not deduplication.

### Whitespace handling (Area 3, mostly closed by spec)
- **D-08:** **Strip-and-check rule applied consistently** to both no-op detection (D-06) and append-on-empty logic (NOTE-04). A note containing only whitespace characters (spaces, tabs, newlines) is semantically equivalent to empty.
- **D-09:** When appending to a whitespace-only note, the resulting note content is **the appended text only** — the original whitespace is discarded (no leading separator, no preserved whitespace). Spec line 193: "set directly (no leading separator)".

### Tool description strategy (Area 4)
- **D-10:** Standard, matter-of-fact documentation style — no "Breaking change" framing, no "was top-level before" note. Pre-release + no-compat means there's no real audience for migration messaging.
- **D-11:** Documentation locations (mirroring TagAction precedent):
  - `NoteAction.__doc__` via new `NOTE_ACTION_DOC` constant — class-level overview (append/replace semantics, separator, strip-and-check behavior)
  - Per-field descriptions on `append` / `replace` via new `NOTE_ACTION_APPEND` / `NOTE_ACTION_REPLACE` constants — narrow semantics per operation
  - `EditTaskActions.__doc__` updated to list note alongside tags/move/lifecycle
  - `edit_tasks` tool description updated: remove top-level `note` mention; actions block list includes note
- **D-12:** Exact wording is Claude's discretion during planning/execution, following existing `descriptions.py` idioms.

### Implementation architecture (E–H)

- **D-13:** **Composition lives in a new `DomainLogic` method** — `process_note_action(command: EditTaskCommand, task: Task) → (new_note_or_UNSET, should_skip_bridge, warnings)`. Parallels `DomainLogic.process_lifecycle` (see `service/domain.py:499`). Called by `_EditTaskPipeline` before `PayloadBuilder`.
  - Inputs: the command (with `actions.note`) and the resolved task (needed for current note content + no-op detection).
  - Outputs: the final note string to send to the bridge (or `UNSET` to skip note in payload), a boolean indicating whether the whole note operation is a no-op, and any warnings to surface.
  - Integration point: `_EditTaskPipeline` invokes `process_note_action`, passes the resulting note value into the `EditTaskRepoPayload` construction. If `should_skip_bridge` is true AND no other fields/actions changed, the pipeline skips the bridge call entirely (following existing "all-no-op edit" pattern).
- **D-14:** **Dead-code removal in this phase.** The branch `if is_set(command.note) and command.note is None:` in `DomainLogic.normalize_clear_intents` (`service/domain.py:484-485`) becomes unreachable after NOTE-01. Remove it in Phase 55 rather than deferring. Keeps the domain layer honest.
- **D-15:** **Description constants: delete + new family.** Remove `NOTE_EDIT_COMMAND` from `agent_messages/descriptions.py`. Add `NOTE_ACTION_DOC`, `NOTE_ACTION_APPEND`, `NOTE_ACTION_REPLACE` (parallels `TAG_ACTION_DOC`, `TAG_ACTION_ADD`, `TAG_ACTION_REMOVE`, `TAG_ACTION_REPLACE`). AST enforcement tests for description centralization will catch any stragglers.
- **D-16:** **Test migration: two-pass mechanical + coverage review.**
  - **Pass 1 (mechanical):** Find all tests using `EditTaskCommand(note=...)` or equivalent fixture patterns. Rewrite to `EditTaskCommand(id=..., actions=EditTaskActions(note=NoteAction(replace=...)))`. Preserves all existing assertion coverage.
  - **Pass 2 (new coverage):** Add tests for append semantics (including empty-note and whitespace-only edge cases), exclusivity validation errors, all three no-op warning paths, and the `process_note_action` domain method in isolation.

### Non-decisions (verified, no change needed)
- **EditTaskRepoPayload.note** stays `str | None = None`. Service sends the composed string as a setter.
- **Bridge** is not modified. `handleEditTask` already accepts `note: string | null`. No JS work, no golden master recapture required (GM captures bridge contract; bridge contract unchanged).
- **EditTaskActions** keeps its current posture (no "at least one action across the block" validator). Spec line 195 confirms: "Note action alone is valid — no tags/move required in the actions block."
- **add_tasks** is untouched per NOTE-05. `AddTaskCommand.note` remains a top-level `PatchOrClear[str]` setter.
- **Output schema:** `EditTaskResult` is unchanged (Phase 54 already locked the `status/id/name/error/warnings` shape). Input schema (`EditTaskCommand`) changes — MCP clients regenerate input schemas from Pydantic automatically via FastMCP.
- **Batch integration:** Phase 54's fail-fast semantics apply unchanged. Note-related `ValidationError` at input = whole-batch rejection (via `ValidationReformatterMiddleware`). Note-related no-ops are per-item `success` with warnings, not errors.

### Claude's Discretion
- Exact names of new warning/error constants (e.g., `NOTE_APPEND_EMPTY` vs `NOTE_APPEND_NO_OP`) and their wording
- Whether `process_note_action` returns `(new_note_or_UNSET, should_skip_bridge, warnings)` as a 3-tuple, a NamedTuple, or a small dataclass
- Internal helper structure within `process_note_action` (one method or split into `_detect_note_no_op` + `_compose_note`)
- Exact test file organization — one `test_note_action.py` for contract + domain, or split across `tests/contracts/` and `tests/service/`
- Whether the `EditTaskActions` docstring keeps a single consolidated sentence or splits into per-action bullets

### Folded Todos
- None — matched todos were all false positives (keyword matches on generic "task"/"edit" terms, none specifically about notes).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone spec
- `.research/updated-spec/MILESTONE-v1.4.md` §Notes Graduation (lines 169-196) — primary spec: top-level removal, append/replace operations, type conventions, edge cases (empty-note, whitespace-only, note-alone validity)
- `.research/updated-spec/MILESTONE-v1.4.md` §Key Acceptance Criteria > Notes graduation (lines 224-229) — locked acceptance gates

### Requirements
- `.planning/REQUIREMENTS.md` §Notes Graduation (NOTE-01 through NOTE-05) — traceable requirement IDs this phase must close

### Architecture & conventions
- `docs/architecture.md` §Field graduation (lines 707-742) — the pattern this phase executes. `note` is explicitly named as the canonical next graduation. TagAction shown as the precedent.
- `docs/architecture.md` §Agent-facing messages (lines 743-753) — warning/error wording conventions (centralized in `agent_messages/`, AST-enforced)
- `docs/model-taxonomy.md` — model naming conventions. `NoteAction` lives in `contracts/shared/actions.py` alongside `TagAction`, `MoveAction`.

### Prior phase context
- `.planning/phases/53-response-shaping/53-CONTEXT.md` — D-03 establishes "no stripping on write results" (EditTaskResult unchanged here). References this phase as "Phase 55 graduation."
- `.planning/phases/54-batch-processing/54-CONTEXT.md` — D-02 locks the result model shape (`status/id/name/error/warnings`). Phase 55 inherits without modification.

### Current implementation (key files)
- `src/omnifocus_operator/contracts/use_cases/edit/tasks.py` — `EditTaskCommand` (remove top-level `note`), `EditTaskActions` (add `note: Patch[NoteAction] = UNSET`), `EditTaskRepoPayload` (unchanged)
- `src/omnifocus_operator/contracts/shared/actions.py` — **primary edit target.** Add `NoteAction` class here mirroring `TagAction` (lines 36-63). Follow the same `@model_validator(mode="after")` pattern for exclusivity + required.
- `src/omnifocus_operator/contracts/base.py` — `Patch`, `PatchOrClear`, `UNSET`, `is_set` — reused for `NoteAction` field types
- `src/omnifocus_operator/service/domain.py` — **primary edit target.** Add `DomainLogic.process_note_action` (new method, mirror `process_lifecycle` at line 499). Remove the unreachable `command.note is None` branch from `normalize_clear_intents` (lines 484-485).
- `src/omnifocus_operator/service/service.py` — `_EditTaskPipeline` method object. Wire in `process_note_action` call before payload construction.
- `src/omnifocus_operator/service/payload.py` — `PayloadBuilder.build_edit_payload` (lines 76-77 use `_add_if_set` for `note`). After Phase 55, note enters the payload from the `process_note_action` return value, not from `command.note`.
- `src/omnifocus_operator/agent_messages/descriptions.py` — delete `NOTE_EDIT_COMMAND`, add `NOTE_ACTION_DOC`, `NOTE_ACTION_APPEND`, `NOTE_ACTION_REPLACE`. Update `EDIT_TASK_ACTIONS_DOC` to mention note. Update `edit_tasks` tool description.
- `src/omnifocus_operator/agent_messages/errors.py` — add `NOTE_APPEND_WITH_REPLACE`, `NOTE_NO_OPERATION`. Precedent: `TAG_REPLACE_WITH_ADD_REMOVE`, `TAG_NO_OPERATION`.
- `src/omnifocus_operator/agent_messages/` — new warning constants for N1/N2/N3. Confirm which file/module (likely the same errors module or a parallel warnings module — check existing organization during planning).

### Bridge (reference only, not modified)
- `bridge/tests/handleEditTask.test.js` (lines 178-185) — bridge already accepts `note: string | null` from `handleEditTask`. No JS changes in Phase 55.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`TagAction`** at `contracts/shared/actions.py:36-63` — exact pattern template for `NoteAction`. Same location, same model_validator posture, same constant-family style.
- **`DomainLogic.process_lifecycle`** at `service/domain.py:499` — shape template for `process_note_action`. Returns `(should_call_bridge, warnings)` tuple; Phase 55 extends to `(new_note_or_UNSET, should_skip_bridge, warnings)`.
- **`DomainLogic.normalize_clear_intents`** at `service/domain.py:474-495` — about to lose its note branch. Remaining `tags.replace=None → []` logic stays.
- **`_EditTaskPipeline`** in `service/service.py` — Method Object pattern. Already loads the task (needed for `process_note_action` to access current note content for no-op detection).
- **`ValidationReformatterMiddleware`** — automatically formats `NoteAction` validation errors into agent-friendly messages without any per-handler wiring.
- **AST enforcement tests** for description centralization — will flag any `Field(description="literal string")` regressions when descriptions move to constants.

### Established Patterns
- **Action-model constants family** (TagAction): `TAG_ACTION_DOC` (class docstring), `TAG_ACTION_ADD`/`TAG_ACTION_REMOVE`/`TAG_ACTION_REPLACE` (per-field descriptions), plus errors `TAG_REPLACE_WITH_ADD_REMOVE` / `TAG_NO_OPERATION`. Phase 55 mirrors this exactly for note.
- **No-op-with-warning pattern** (`architecture.md` §724): detect state-unchanged condition, skip bridge call, populate `warnings` array, return `status: "success"`. Universal across setters, tags, lifecycle, move.
- **Patch-null-rejection via `@field_validator`** — `MoveAction._reject_null_anchor` (`contracts/shared/actions.py:82-88`) shows how `Patch[str]` fields reject explicit nulls with educational errors. `NoteAction.append` uses the type alone (`Patch[str]` rejects null via its type machinery); no explicit validator needed unless a custom message is preferred.
- **Strip-and-check equivalence** — new for Phase 55 but straightforward: `(existing_note or "").strip() == ""` collapses empty and whitespace-only cases into one branch.

### Integration Points
- **`EditTaskCommand.note`** (`contracts/use_cases/edit/tasks.py:75`) — removed in this phase. The `@field_validator` call site on line 92 (`_check_date_format`) is unaffected — it only touches date fields.
- **`EditTaskActions`** (`contracts/use_cases/edit/tasks.py:41-53`) — gains `note: Patch[NoteAction] = UNSET`. Class docstring (`EDIT_TASK_ACTIONS_DOC`) needs a one-line update to list note.
- **`PayloadBuilder.build_edit_payload`** (`service/payload.py:77`) — `_add_if_set(kwargs, command, "name", "note", "flagged", ...)` call: drop `"note"` from the list. Note enters the payload via the `process_note_action` return value integrated in the pipeline.
- **`_EditTaskPipeline`** in `service/service.py` — add one `process_note_action` call before payload construction; thread the returned note value and warnings into the payload and result.
- **All tests using `EditTaskCommand(note=...)`** — mechanical rewrite per D-16 Pass 1.
- **`edit_tasks` tool description** in `agent_messages/descriptions.py` — remove top-level `note` from the semantics list; add `note` to the actions-block description.

</code_context>

<specifics>
## Specific Ideas

- **Minimize branching in `process_note_action`.** The logic naturally decomposes:
  1. If `command.actions.note` is UNSET → return `(UNSET, True, [])` (skip note entirely, no-op at this layer)
  2. If `note_action.append` is set: compute `existing_stripped = (task.note or "").strip()`. If `append == ""` → N1 warn. Else if `existing_stripped == ""` → return `(append_text, False, [])`. Else → return `(task.note + "\n\n" + append_text, False, [])`.
  3. If `note_action.replace` is set: compute `clearing = replace in (None, "")` and `target = replace or ""`. If `clearing` AND `existing_stripped == ""` → N3 warn. Else if target == task.note → N2 warn. Else → return `(target, False, [])`.
- **Where does `process_note_action` return the cleared value for a bridge call?** When `replace: null` clears a non-empty note, the new value is `""`. The bridge-facing payload sends `note: ""` (matches the current "clear note" convention documented in `normalize_clear_intents`).
- **Test the `@model_validator` boundary.** Two explicit ValidationError tests per the D-03 constants: `{append: "foo", replace: "bar"}` raises `NOTE_APPEND_WITH_REPLACE`; `{}` raises `NOTE_NO_OPERATION`. Mirror the shape of `test_tag_action.py` (or wherever TagAction validators are tested).
- **Warning copy calibration.** Existing no-op warnings use imperative guidance ("omit X to skip"). Preserve that voice for note warnings — don't switch to declarative ("Note was not updated"). Agents parse the imperative form faster.
- **Consider a small fixture helper** `make_edit_command_with_note(note_action)` for tests if the migration churn in D-16 is large. Avoid if tests stay readable without it.

</specifics>

<deferred>
## Deferred Ideas

- **Note metadata (created-at, modified-at)** — not in scope, spec doesn't mention it, future milestone if ever needed.
- **Rich text / formatted notes** — OmniFocus supports some formatting, this phase preserves string-only semantics like the current implementation.
- **Note templates / expansion macros** — out of scope; agents compose before calling.
- **Clipboard-style append with deduplication** — N4 explicitly excluded. If real-world usage shows agents re-appending identical blocks, revisit as a future feature, not a v1.4 concern.
- **Cross-item note references in a batch** — Phase 54 already documented cross-item references as unsupported; no special case for notes.

</deferred>

---

*Phase: 55-notes-graduation*
*Context gathered: 2026-04-16*
