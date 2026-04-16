# Phase 55: Notes Graduation - Research

**Researched:** 2026-04-16
**Domain:** Contract/service refactoring — graduate `note` from top-level setter to `actions.note` action block on `edit_tasks`.
**Confidence:** HIGH (CONTEXT.md already locked 16 decisions; this research maps them to exact call sites and line numbers.)

## Summary

Phase 55 is a **second-generation graduation** following the tag graduation (v1.2.1) pattern, explicitly cited in `docs/architecture.md` §Field graduation as the canonical migration template. CONTEXT.md has already locked every design decision (D-01 through D-16). Research goal: translate those decisions into grep-verifiable line numbers, reusable snippets, and a migration surface inventory.

**Scope is narrow and mechanical at the contract layer; subtle at the domain/service layer.** New `NoteAction` class mirroring `TagAction` (parity is tight — same file, same validator shape, same constant family). New `DomainLogic.process_note_action` method (shape parallels `process_lifecycle` at `domain.py:499`, signature extended to 3-tuple per D-13). One integration point in `_EditTaskPipeline` between `_resolve_actions` and `_build_payload`. One `PayloadBuilder.build_edit` argument drop (`"note"` from `_add_if_set`). One dead-code branch removal in `normalize_clear_intents`. Bridge is NOT touched (confirmed: `bridge/tests/handleEditTask.test.js:178-186` still exercises `note: null` / `note: string`).

**Migration surface:** `note=` appears in 25 occurrences across 8 test files, of which **12 test-code sites in 5 files** exercise `EditTaskCommand(..., note=...)` and need mechanical rewrite. The remaining 13 sites are in `add_tasks` contexts (`AddTaskCommand.note`), repo doubles, or snapshot fixtures (`make_task_dict(note=...)`) and stay unchanged (NOTE-05).

**Primary recommendation:** Structure the plan as **three sequential surgeries** — (1) contract-layer (NoteAction + EditTaskActions field + errors + descriptions + EditTaskCommand field removal), (2) domain/service-layer (process_note_action + pipeline wiring + normalize_clear_intents dead-code removal + PayloadBuilder call-site edit), (3) test migration (Pass 1 mechanical rewrites + Pass 2 new coverage). Lean on AST enforcement tests (`tests/test_descriptions.py`) as the safety net — they will fail loudly if any inline string sneaks in.

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Contract shape (D-01 through D-03):**
- D-01: `NoteAction` with `append` and `replace` as mutually exclusive AND at-least-one-required via `@model_validator(mode="after")`. Full TagAction parity. `{}` rejected.
- D-02: Types locked: `append: Patch[str] = UNSET` (null rejected by type, `""` is no-op per NOTE-02); `replace: PatchOrClear[str] = UNSET` (null and `""` both clear per NOTE-03).
- D-03: Two new error constants in `agent_messages/errors.py`:
  - `NOTE_APPEND_WITH_REPLACE` — mirrors `TAG_REPLACE_WITH_ADD_REMOVE` wording style.
  - `NOTE_NO_OPERATION` — mirrors `TAG_NO_OPERATION` wording style.

**No-op warning semantics (D-04 through D-07):**
- D-04: **N1** — `append: ""` → skip bridge, warn (educational: "omit actions.note.append to skip"). New warning constant (naming at Claude's discretion, e.g., `NOTE_APPEND_EMPTY`).
- D-05: **N2** — `replace: "<current-note>"` → skip bridge, warn ("Note already has this content — omit actions.note.replace to skip"). New constant (e.g., `NOTE_REPLACE_ALREADY_CONTENT`).
- D-06: **N3** — `replace: null` OR `replace: ""` on empty/whitespace-only note → skip bridge, warn ("Note is already empty — omit actions.note.replace to skip"). New constant (e.g., `NOTE_ALREADY_EMPTY`). Uses strip-and-check.
- D-07: **N4** — append that happens to duplicate existing content (e.g., `append: "foo"` on note ending in `"foo"`) is a **real change**, NOT a no-op. Append's contract is concatenation, not deduplication.

**Whitespace handling (D-08, D-09):**
- D-08: Strip-and-check rule applies consistently to N3 (empty-check) and NOTE-04 (append-on-empty). `(note or "").strip() == ""` collapses empty and whitespace-only cases.
- D-09: Appending to a whitespace-only note → result is the appended text only (original whitespace discarded; no leading separator).

**Tool description strategy (D-10 through D-12):**
- D-10: Matter-of-fact documentation — no "Breaking change" framing. Pre-release, no-compat.
- D-11: Documentation locations: `NoteAction.__doc__` via new `NOTE_ACTION_DOC` constant; per-field descriptions on `append`/`replace` via new `NOTE_ACTION_APPEND`/`NOTE_ACTION_REPLACE` constants; `EditTaskActions.__doc__` updated; `edit_tasks` tool description updated (remove top-level `note` mention, add note to actions block list).
- D-12: Exact wording at Claude's discretion (follow existing `descriptions.py` idioms).

**Implementation architecture (D-13 through D-16):**
- D-13: New `DomainLogic.process_note_action(command, task) → (new_note_or_UNSET, should_skip_bridge, warnings)`. Shape parallels `process_lifecycle` (`domain.py:499`). Called from `_EditTaskPipeline` before payload construction.
- D-14: Dead-code removal: `if is_set(command.note) and command.note is None:` branch in `normalize_clear_intents` (`domain.py:484-485`) becomes unreachable — remove it in this phase, keep domain layer honest.
- D-15: Description constants: delete `NOTE_EDIT_COMMAND` from `descriptions.py`; add `NOTE_ACTION_DOC`, `NOTE_ACTION_APPEND`, `NOTE_ACTION_REPLACE`. AST enforcement tests (`tests/test_descriptions.py`) catch stragglers.
- D-16: Test migration: two-pass. Pass 1 (mechanical) — rewrite every test using `EditTaskCommand(note=...)` to `EditTaskCommand(id=..., actions=EditTaskActions(note=NoteAction(replace=...)))` pattern. Pass 2 (coverage) — new tests for append semantics, empty-note edge cases, exclusivity validation errors, three no-op warning paths, and `process_note_action` in isolation.

### Claude's Discretion

- Exact names of new warning/error constants (e.g., `NOTE_APPEND_EMPTY` vs `NOTE_APPEND_NO_OP`) and their wording
- Whether `process_note_action` returns `(new_note_or_UNSET, should_skip_bridge, warnings)` as a 3-tuple, a NamedTuple, or a small dataclass
- Internal helper structure within `process_note_action` (one method or split into `_detect_note_no_op` + `_compose_note`)
- Exact test file organization — one `test_note_action.py` for contract + domain, or split across `tests/contracts/` and `tests/service/`
- Whether the `EditTaskActions` docstring keeps a single consolidated sentence or splits into per-action bullets

### Deferred Ideas (OUT OF SCOPE)

- Note metadata (created-at, modified-at) — not in spec
- Rich text / formatted notes — stays string-only
- Note templates / expansion macros — agent composes before calling
- Clipboard-style append with deduplication (N4) — explicitly excluded
- Cross-item note references in a batch — Phase 54 already documented as unsupported

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| NOTE-01 | Top-level `note` removed from `edit_tasks` input schema | Drop field at `contracts/use_cases/edit/tasks.py:75`; drop `"note"` arg from `_add_if_set` at `service/payload.py:77`; delete dead branch at `service/domain.py:484-485`; remove `NOTE_EDIT_COMMAND` from `descriptions.py:181` and from import at `contracts/use_cases/edit/tasks.py:19`. |
| NOTE-02 | `actions.note.append` (Patch[str], null rejected, `""` no-op) adds text with `\n\n` separator | New `NoteAction.append` field typed `Patch[str] = UNSET` (null rejection via `Patch` type machinery — no explicit `@field_validator` needed). Composition in new `DomainLogic.process_note_action`. Empty-string no-op → N1 warning (D-04). |
| NOTE-03 | `actions.note.replace` (PatchOrClear[str], null and `""` clear) replaces entire note | New `NoteAction.replace` field typed `PatchOrClear[str] = UNSET`. Composition in `process_note_action`. Identical-content no-op → N2; clear-already-empty no-op → N3. |
| NOTE-04 | Append on empty/whitespace-only note sets directly (no leading separator) | Strip-and-check in `process_note_action`: if `(task.note or "").strip() == ""` then result = `append_text` (no `"\n\n"` prefix). Per D-08, D-09. |
| NOTE-05 | `add_tasks` retains top-level `note` field for initial content | `AddTaskCommand.note` unchanged; `PayloadBuilder.build_add` unchanged (`service/payload.py:56-57`); `NOTE_ADD_COMMAND` constant at `descriptions.py:179` unchanged. No changes in `_AddTaskPipeline`. Preserve `tests/test_models.py` note=... fixtures in add contexts. |

## Standard Stack

No new external libraries. All work uses existing primitives.

### Existing primitives reused

| Primitive | Location | Purpose for Phase 55 |
|-----------|----------|---------------------|
| `Patch[T]`, `PatchOrClear[T]`, `UNSET`, `is_set()` | `contracts/base.py:51-70` | Type aliases for `NoteAction.append`/`replace` fields (null rejection via type machinery) |
| `CommandModel` (base class) | `contracts/base.py:86-91` | Parent class for `NoteAction` — `extra="forbid"` via `StrictModel` |
| `@model_validator(mode="after")` from `pydantic` | TagAction precedent at `contracts/shared/actions.py:52-63` | Validator for exclusivity + at-least-one on `NoteAction` |
| `Field(default=UNSET, description=...)` | Pattern throughout `contracts/` | Per-field descriptions must reference constants (AST-enforced) |
| `ValidationReformatterMiddleware` | Existing middleware | Reformats `NoteAction` `ValidationError`s into agent-friendly messages — no per-handler wiring needed |

[VERIFIED: codebase grep — `tests/test_contracts_type_aliases.py:93` shows `EditTaskCommand(id="t1", name="x", note=None)` passes validation today, demonstrating `PatchOrClear[str]` already works the way we'll reuse]

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `@model_validator(mode="after")` for exclusivity | Separate `@field_validator` per field | TagAction already uses `after`-mode for identical use case — follow precedent. `after` is the right phase because it needs to see all three fields together. |
| 3-tuple return from `process_note_action` | NamedTuple or dataclass | Claude's discretion per CONTEXT. Precedent is 2-tuple from `process_lifecycle`. A NamedTuple would marginally improve readability at call site. |

## Architecture Patterns

### Recommended Task Structure

```
Plan 01 (Contract Layer):
  ├─ Add NoteAction class (contracts/shared/actions.py, after MoveAction)
  ├─ Add NOTE_APPEND_WITH_REPLACE + NOTE_NO_OPERATION to errors.py
  ├─ Add NOTE_ACTION_DOC + NOTE_ACTION_APPEND + NOTE_ACTION_REPLACE to descriptions.py
  ├─ Add note: Patch[NoteAction] = UNSET field to EditTaskActions
  ├─ Update EDIT_TASK_ACTIONS_DOC in descriptions.py
  ├─ Remove note field from EditTaskCommand
  ├─ Remove NOTE_EDIT_COMMAND from descriptions.py AND from imports
  └─ Update EDIT_TASKS_TOOL_DOC (remove top-level note mention, add note to actions list)

Plan 02 (Domain + Service Layer):
  ├─ Add 3 new warning constants (N1/N2/N3) to warnings.py
  ├─ Add DomainLogic.process_note_action (mirror process_lifecycle shape)
  ├─ Remove dead branch in normalize_clear_intents (lines 484-485)
  ├─ Drop "note" from PayloadBuilder._add_if_set call (service/payload.py:77)
  ├─ Wire process_note_action into _EditTaskPipeline (after _resolve_actions, before _build_payload)
  └─ Pass computed note value + note warnings into payload builder + all_warnings

Plan 03 (Test Migration + New Coverage):
  ├─ Pass 1: Mechanical — rewrite 12 EditTaskCommand(note=...) call sites in 5 test files
  ├─ Pass 2a: NoteAction contract tests — exclusivity, at-least-one, type rejection
  ├─ Pass 2b: process_note_action domain unit tests — all decision branches
  ├─ Pass 2c: _EditTaskPipeline integration tests — 3 no-op warning paths, append semantics, empty-note, whitespace-only
  └─ Pass 2d: (optional) Property test for append invariance
```

This split lets Plan 01 land as a green commit (contract exists, is_set(actions.note) always False, nothing broken) before Plan 02 adds behavior.

### Pattern 1: TagAction Template (exact reference for NoteAction)

**Source:** `src/omnifocus_operator/contracts/shared/actions.py:36-63` [VERIFIED: read in session]

```python
class TagAction(CommandModel):
    __doc__ = TAG_ACTION_DOC

    add: Patch[list[str]] = Field(
        default=UNSET,
        description=TAG_ACTION_ADD,
    )
    remove: Patch[list[str]] = Field(
        default=UNSET,
        description=TAG_ACTION_REMOVE,
    )
    replace: PatchOrClear[list[str]] = Field(
        default=UNSET,
        description=TAG_ACTION_REPLACE,
    )

    @model_validator(mode="after")
    def _validate_incompatible_tag_edit_modes(self) -> TagAction:
        has_replace = is_set(self.replace)
        has_add = is_set(self.add)
        has_remove = is_set(self.remove)
        if has_replace and (has_add or has_remove):
            msg = TAG_REPLACE_WITH_ADD_REMOVE
            raise ValueError(msg)
        if not has_replace and not has_add and not has_remove:
            msg = TAG_NO_OPERATION
            raise ValueError(msg)
        return self
```

**Expected NoteAction shape (derived):**

```python
class NoteAction(CommandModel):
    __doc__ = NOTE_ACTION_DOC

    append: Patch[str] = Field(default=UNSET, description=NOTE_ACTION_APPEND)
    replace: PatchOrClear[str] = Field(default=UNSET, description=NOTE_ACTION_REPLACE)

    @model_validator(mode="after")
    def _validate_incompatible_note_edit_modes(self) -> NoteAction:
        has_append = is_set(self.append)
        has_replace = is_set(self.replace)
        if has_append and has_replace:
            msg = NOTE_APPEND_WITH_REPLACE
            raise ValueError(msg)
        if not has_append and not has_replace:
            msg = NOTE_NO_OPERATION
            raise ValueError(msg)
        return self
```

**Update `__all__` at `contracts/shared/actions.py:101`:** add `"NoteAction"`.

### Pattern 2: process_lifecycle Template (shape for process_note_action)

**Source:** `src/omnifocus_operator/service/domain.py:499-529` [VERIFIED: read in session]

Current `process_lifecycle` returns `(should_call_bridge: bool, warnings: list[str])` — 2-tuple.

**Expected `process_note_action` shape (derived per D-13):**

```python
def process_note_action(
    self,
    command: EditTaskCommand,
    task: Task,
) -> tuple[str | _Unset, bool, list[str]]:
    """Returns (new_note_value_or_UNSET, should_skip_bridge, warnings).

    - new_note_value_or_UNSET: str to send to bridge, or UNSET to leave note absent from payload
    - should_skip_bridge: True when the note operation is a pure no-op
    - warnings: educational warnings (N1/N2/N3)
    """
    warnings: list[str] = []

    # No note action → UNSET, no skip, no warnings
    if not is_set(command.actions) or not is_set(command.actions.note):
        return UNSET, True, warnings

    note_action = command.actions.note
    existing_stripped = (task.note or "").strip()

    if is_set(note_action.append):
        append_text = note_action.append
        if append_text == "":
            warnings.append(NOTE_APPEND_EMPTY)
            return UNSET, True, warnings
        if existing_stripped == "":
            # Empty/whitespace-only note → set directly (NOTE-04, D-09)
            return append_text, False, warnings
        # Concatenate with paragraph separator (NOTE-02)
        return (task.note or "") + "\n\n" + append_text, False, warnings

    # Replace path
    assert is_set(note_action.replace)
    replace_val = note_action.replace
    clearing = replace_val is None or replace_val == ""
    target = replace_val or ""
    if clearing and existing_stripped == "":
        warnings.append(NOTE_ALREADY_EMPTY)
        return UNSET, True, warnings
    if target == (task.note or ""):
        warnings.append(NOTE_REPLACE_ALREADY_CONTENT)
        return UNSET, True, warnings
    return target, False, warnings
```

Naming of the 3 warning constants is Claude's discretion (D-04/D-05/D-06).

### Pattern 3: Pipeline Integration Point

**Current `_EditTaskPipeline.execute` sequence** (`service/service.py:667-685`) [VERIFIED: read in session]:

```python
async def execute(self, command: EditTaskCommand) -> EditTaskResult:
    self._command = command
    self._preferences_warnings: list[str] = []

    await self._verify_task_exists()
    self._validate_and_normalize()          # normalize_clear_intents
    await self._normalize_dates()
    self._resolve_actions()                 # extracts self._lifecycle_action, self._tag_actions, self._move_action
    self._apply_lifecycle()
    self._check_completed_status()
    self._apply_repetition_rule()
    await self._apply_tag_diff()
    await self._apply_move()
    self._build_payload()                   # <<< note MUST be resolved before this

    if (early := self._detect_noop()) is not None:
        return early
    return await self._delegate()
```

**Phase 55 integration:**

1. Extend `_resolve_actions` (line 713-722) to extract `self._note_action = actions.note if is_set(actions.note) else None`.
2. Add new `self._apply_note_action()` method (parallels `_apply_lifecycle`), calls `process_note_action`, stores `self._note_value` (str or UNSET) + `self._note_warns: list[str]`.
3. Call it in `execute()` between `_apply_move()` and `_build_payload()` (or after `_validate_and_normalize` — order doesn't matter for note; insertion point at discretion).
4. In `_build_payload` (line 944-964), extend `build_edit` signature OR pre-set `kwargs["note"] = self._note_value` directly. Simplest: pass `self._note_value` as a new keyword argument to `PayloadBuilder.build_edit`, and have the builder add it to kwargs iff `is_set(note_value)`.
5. Append `self._note_warns` to `self._all_warnings` in `_build_payload` (line 958-964).

### Pattern 4: PayloadBuilder.build_edit change

**Current** `service/payload.py:76-77` [VERIFIED: read in session]:

```python
# Simple fields (name, note, flagged, estimated_minutes)
self._add_if_set(kwargs, command, "name", "note", "flagged", "estimated_minutes")
```

**Expected after Phase 55:** drop `"note"` from the positional args — note enters via a new parameter, not via `_add_if_set(command, ...)`.

```python
self._add_if_set(kwargs, command, "name", "flagged", "estimated_minutes")
# ... elsewhere in method:
if is_set(note_value):
    kwargs["note"] = note_value
```

Signature add: `note_value: str | _Unset = UNSET` as a new kwarg to `build_edit`.

### Anti-Patterns to Avoid

- **Inline field descriptions:** AST test `test_no_inline_field_descriptions_in_agent_models` (`tests/test_descriptions.py:127-167`) will fail if `Field(description="...")` uses a string literal or f-string. Every description must be an `ast.Name` reference.
- **Inline class docstrings:** AST test `test_no_inline_class_docstrings_on_agent_classes` (`tests/test_descriptions.py:169-201`) will fail if `NoteAction` uses `"""docstring"""` instead of `__doc__ = NOTE_ACTION_DOC`.
- **Missing consumer reference:** AST test `test_all_description_constants_referenced_in_consumers` (`tests/test_descriptions.py:118-125`) will fail if you add a constant to `descriptions.py` but never import it in a consumer module.
- **Unused removed constant:** removing `NOTE_EDIT_COMMAND` but forgetting to remove the import at `contracts/use_cases/edit/tasks.py:19` causes an `ImportError`. Both must be removed in the same change.
- **Forgetting `__all__`:** `contracts/shared/actions.py:101` lists `MoveAction`, `TagAction` — must add `NoteAction` for clean re-export.
- **Naming convention violation:** `tests/test_output_schema.py:556-561` has `CONTRACTS_EXEMPT = {"CommandModel", "EditTaskActions", ...}`. `NoteAction` ends with `"Action"` (in `CONTRACT_SUFFIXES`) so it's automatically allowed. No exempt-list change needed.
- **Touching bridge or JS tests:** explicitly forbidden — bridge contract is unchanged. `bridge/tests/handleEditTask.test.js:178-186` already covers `note: null` / `note: string` and stays exactly as is.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Null rejection on `append` | Custom `@field_validator` | The `Patch[str]` type alias rejects `None` via Pydantic type machinery | TagAction's `add`/`remove` use `Patch[list[str]]` with no `@field_validator` for null — precedent. MoveAction's `@field_validator("before", "after", mode="before")` at `actions.py:82-88` only exists because it wants a *custom message* for null; if default type-error message is acceptable, no validator is needed. CONTEXT `code_context` §Established Patterns (line 134) confirms. |
| Exclusivity validation | Nested if/else at service layer | `@model_validator(mode="after")` on `NoteAction` | Contract-layer rejection runs before service sees the command — catches errors at the schema boundary and uses `ValidationReformatterMiddleware` automatically. Matches TagAction. |
| Agent-friendly validation error messages | Custom error handler in service layer | Raise `ValueError(CONSTANT)` inside the validator | `ValidationReformatterMiddleware` (noted in CONTEXT `code_context` §Reusable Assets) auto-formats. |
| Reformatting Pydantic errors per-handler | Custom wrapping logic in `_EditTaskPipeline` | Let the middleware handle it | Already wired for TagAction / MoveAction — same path for NoteAction. |
| Tracking whether note was "cleared" via a boolean flag | Extra `note_clear: bool` parameter | Use `str | _Unset` return (value is `""` for clear, `UNSET` for skip) | `EditTaskRepoPayload.note: str | None = None` already distinguishes: payload value `""` → bridge clears; field absent from `model_fields_set` → bridge leaves note alone. The no-op detection in `DomainLogic._all_fields_match` at `domain.py:1026-1047` uses `payload.model_fields_set` so dropping `note` from set is the right signal for "skip". |

**Key insight:** Every problem Phase 55 needs to solve has a TagAction (v1.2.1) or MoveAction (v1.2.1) precedent. The phase is "fill in the Note-shaped hole in an already-built framework."

## Runtime State Inventory

N/A — Phase 55 is a code/contract refactor with zero runtime state implications.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no schema changes to SQLite cache, no ChromaDB, no Mem0 | None |
| Live service config | None — OmniFocus task `note` attribute format unchanged; bridge contract unchanged | None |
| OS-registered state | None | None |
| Secrets/env vars | None | None |
| Build artifacts | None — pure source refactor; existing `uv sync` is sufficient after changes | None |

**Canonical question:** After every file in the repo is updated, what runtime systems still have the old string cached, stored, or registered? **Answer: nothing.** MCP clients regenerate input schemas from Pydantic on server startup (FastMCP does this automatically — noted in CONTEXT §Non-decisions). No migration script needed.

## Migration Surface Inventory

Exact file-by-file inventory of `note=` usages that need Plan 03 Pass 1 mechanical rewrite.

### Production code (SINGLE touchpoint)

| File | Line | Context | Action |
|------|------|---------|--------|
| `src/omnifocus_operator/service/domain.py` | 484 (string `"note"` in a comment/docstring at line 1) | `normalize_clear_intents` dead branch | Remove lines 484-485 per D-14 |

Only **one** production site uses `note=` in `EditTaskCommand` construction — and that's the line being deleted.

### Test files — EDIT contexts (mechanical rewrite)

All of these sites are `EditTaskCommand(..., note=...)` and need rewriting per D-16 Pass 1.

| File | Line | Current | Target Replacement |
|------|------|---------|---------------------|
| `tests/test_service_domain.py` | 651 | `EditTaskCommand(id="t1", note=None)` | Replace semantics: rewrite the *test itself*, since `normalize_clear_intents` no longer handles note. These tests (lines 649-665) verify the dead branch — **delete them** (keeps domain layer honest, per D-14). |
| `tests/test_service_domain.py` | 657 | `EditTaskCommand(id="t1", note="Hello")` | Same — delete; covered by new `process_note_action` tests. |
| `tests/test_service.py` | 650 | `EditTaskCommand(id="task-001", note="New note")` | `EditTaskCommand(id="task-001", actions=EditTaskActions(note=NoteAction(replace="New note")))` |
| `tests/test_service.py` | 968 | `EditTaskCommand(id="task-001", note=None)` | `EditTaskCommand(id="task-001", actions=EditTaskActions(note=NoteAction(replace=None)))` |
| `tests/test_service.py` | 1209-1215 (multi-field) | `EditTaskCommand(id=..., name=..., note="New note", flagged=True, estimated_minutes=60.0)` | `EditTaskCommand(id=..., name=..., actions=EditTaskActions(note=NoteAction(replace="New note")), flagged=True, estimated_minutes=60.0)` |
| `tests/test_service.py` | 1241 | `EditTaskCommand(id="task-001", note="")` | `EditTaskCommand(id="task-001", actions=EditTaskActions(note=NoteAction(replace="")))` |
| `tests/test_service_payload.py` | 116 | `EditTaskCommand(id="t1", note="")` | **Entire test changes semantics.** `PayloadBuilder` no longer receives note from command. Test becomes: call `build_edit(command, note_value="", ...)` with the new kwarg. |
| `tests/test_service_payload.py` | 127 | `EditTaskCommand(id="t1", note=None)` | Same — test becomes `build_edit(command, note_value=UNSET, ...)`; `None` is no longer a valid command-level value. Delete or rewrite. |
| `tests/test_service_payload.py` | 234 | `EditTaskCommand(id="t1", note="Hello")` | `build_edit(command, note_value="Hello", ...)` |
| `tests/test_contracts_type_aliases.py` | 93 | `EditTaskCommand(id="t1", name="x", note=None)` | **Test needs semantic rewrite.** It currently validates `PatchOrClear[str]` on the removed field. Replace with an equivalent test on any remaining `PatchOrClear[str]` field (e.g., `due_date`) OR on `NoteAction.replace`. |

### Test files — ADD contexts (UNCHANGED, verify only)

These stay exactly as they are — NOTE-05 preserves top-level `note` on `AddTaskCommand`.

| File | Line | Context |
|------|------|---------|
| `tests/test_models.py` | 378, 426, 978 | `make_task_dict(..., note=...)` — entity fixtures, not commands |
| `tests/test_service.py` | 246 | `AddTaskCommand(..., note="Some note", ...)` |
| `tests/test_service_payload.py` | 56 | `AddTaskCommand(..., note="Some note", ...)` |
| `tests/test_cross_path_equivalence.py` | 523 | Bridge parameter serialization — entity-level `note` |
| `tests/test_server.py` | 1892 | Comment describing stripped fields |
| `tests/doubles/bridge.py` | 379 | `InMemoryBridge` task constructor — entity-level `note` |

### Test file count summary

- **Files with EDIT `note=` usages needing mechanical rewrite:** 5 (`test_service_domain.py`, `test_service.py`, `test_service_payload.py`, `test_contracts_type_aliases.py`)
- **Total EDIT `note=` call sites to rewrite or delete:** 11 (2 in `test_service_domain.py` for deletion, 5 in `test_service.py` rewrite, 3 in `test_service_payload.py` rewrite/delete, 1 in `test_contracts_type_aliases.py` rewrite)
- **ADD contexts staying unchanged:** 13 sites across 6 files (verify with `grep -n` after migration that no EDIT `note=` remains)
- **Production code touchpoints beyond the deletion:** zero `note=` construction sites in `src/` [VERIFIED: grep]

## Common Pitfalls

### Pitfall 1: Duplicate work in normalize_clear_intents
**What goes wrong:** Developer adds `process_note_action` but forgets D-14 — leaves the unreachable `if is_set(command.note) and command.note is None:` branch in place.
**Why it happens:** The branch looks like it's still valid — but after NOTE-01, `EditTaskCommand` has no `note` field, so `command.note` raises `AttributeError`.
**How to avoid:** `service/domain.py:484-485` removal is a Plan 02 checklist item; verify `EditTaskCommand` no longer has a `note` attribute.
**Warning signs:** `AttributeError` in `normalize_clear_intents` during test run; mypy fails on `command.note` reference.

### Pitfall 2: Forgetting the description import removal
**What goes wrong:** `NOTE_EDIT_COMMAND` is deleted from `descriptions.py` but the import at `contracts/use_cases/edit/tasks.py:19` remains → `ImportError` at module load.
**Why it happens:** The import is 56 lines away from the field that uses it; easy to miss after removing the field.
**How to avoid:** Plan the 4-step edit atomically: delete field, delete import, delete constant from descriptions, verify no other consumer references `NOTE_EDIT_COMMAND`.
**Warning signs:** `ImportError: cannot import name 'NOTE_EDIT_COMMAND'` on first test run.

### Pitfall 3: N3 vs N2 ambiguity
**What goes wrong:** When existing note is empty and `replace: ""` is passed, both N2 (identical-content) and N3 (clear-already-empty) technically match. Emitting both is redundant.
**Why it happens:** `task.note = ""`, `replace_val = ""` → `target == task.note` is True AND `clearing AND existing_stripped == ""` is True.
**How to avoid:** Structure `process_note_action` to check N3 (clearing intent on empty) *before* N2 (identical content) — prefer the more specific warning. Alternatively: check `clearing` path first; if not clearing, then check identical content. See the Pattern 2 pseudocode above.
**Warning signs:** Tests emit two warnings where one is expected.

### Pitfall 4: Whitespace-only append semantics surprise
**What goes wrong:** Agent sends `append: "   "` (whitespace-only, not empty-string). Is it a no-op?
**Why it happens:** D-08 says strip-and-check applies to the *existing* note for empty-detection. But the *incoming* `append` value: D-04 only excludes the literal empty string `""`. A whitespace-only append IS a real change (produces `"existing\n\n   "`).
**How to avoid:** In `process_note_action`, only check `append_text == ""` for N1 — never `append_text.strip() == ""`. Document this in the test comment.
**Warning signs:** Flo asks "wait, is `append: '   '` also a no-op?" during UAT.

### Pitfall 5: Missing NoteAction from __all__
**What goes wrong:** `NoteAction` is defined but not exported from `contracts/shared/actions.py`.
**Why it happens:** `__all__` at line 101 is easy to miss after scrolling through the class definition.
**How to avoid:** Checklist item: update `__all__ = ["MoveAction", "NoteAction", "TagAction"]` (alphabetical).
**Warning signs:** `from omnifocus_operator.contracts.shared.actions import NoteAction` fails in tests.

### Pitfall 6: Naming-convention test false sense of security
**What goes wrong:** `tests/test_output_schema.py:584-598` enforces "contracts classes must end with a recognized suffix." `NoteAction` ends with `"Action"` so it's automatically included. Good. But `EditTaskActions` is in `CONTRACTS_EXEMPT` because it's plural-Actions. Adding `note: Patch[NoteAction] = UNSET` to it does NOT require exempt-list changes.
**Why it matters:** Planner might think they need to update the exempt list — they don't.
**How to avoid:** Note the exemption in plan comment; avoid unnecessary edits.

## Code Examples

### Example 1: NoteAction contract (expected Phase 55 output)

```python
# src/omnifocus_operator/contracts/shared/actions.py (NEW class, added after MoveAction)
# Source: derived from TagAction at contracts/shared/actions.py:36-63 [VERIFIED]

class NoteAction(CommandModel):
    __doc__ = NOTE_ACTION_DOC

    append: Patch[str] = Field(default=UNSET, description=NOTE_ACTION_APPEND)
    replace: PatchOrClear[str] = Field(default=UNSET, description=NOTE_ACTION_REPLACE)

    @model_validator(mode="after")
    def _validate_incompatible_note_edit_modes(self) -> NoteAction:
        has_append = is_set(self.append)
        has_replace = is_set(self.replace)
        if has_append and has_replace:
            msg = NOTE_APPEND_WITH_REPLACE
            raise ValueError(msg)
        if not has_append and not has_replace:
            msg = NOTE_NO_OPERATION
            raise ValueError(msg)
        return self


__all__ = ["MoveAction", "NoteAction", "TagAction"]  # alphabetical
```

### Example 2: EditTaskActions update

```python
# src/omnifocus_operator/contracts/use_cases/edit/tasks.py
# Before: actions = {tags, move, lifecycle}
# After: actions = {tags, move, lifecycle, note}

class EditTaskActions(CommandModel):
    __doc__ = EDIT_TASK_ACTIONS_DOC

    tags: Patch[TagAction] = UNSET
    move: Patch[MoveAction] = UNSET
    lifecycle: Patch[Literal["complete", "drop"]] = UNSET
    note: Patch[NoteAction] = UNSET  # NEW

    @field_validator("lifecycle", mode="before")
    @classmethod
    def _validate_lifecycle(cls, v: object) -> object:
        if isinstance(v, str) and v not in ("complete", "drop"):
            raise ValueError(LIFECYCLE_INVALID_VALUE.format(value=v))
        return v
```

Also add `NoteAction` to the import from `contracts.shared.actions` at line 32.

### Example 3: EditTaskCommand (field removed)

```python
# Before: had `note: PatchOrClear[str] = Field(default=UNSET, description=NOTE_EDIT_COMMAND)` at line 75
# After: field entirely removed, import of NOTE_EDIT_COMMAND removed from line 19
```

### Example 4: New test pattern (replaces old `note=` tests)

```python
# tests/test_service.py — rewrite of test_patch_note_only

@pytest.mark.snapshot(tasks=[make_task_dict(id="task-001", name="Task")])
async def test_patch_note_only(
    self, service: OperatorService, repo: BridgeOnlyRepository
) -> None:
    """Editing only note (via actions.note.replace) leaves other fields unchanged."""
    result = await service.edit_task(
        EditTaskCommand(
            id="task-001",
            actions=EditTaskActions(note=NoteAction(replace="New note")),
        )
    )
    assert result.status == "success"
    task = await repo.get_task("task-001")
    assert task is not None
    assert task.note == "New note"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `note` as top-level `PatchOrClear[str]` setter on `EditTaskCommand` | `actions.note` as `NoteAction` with `append` + `replace` | Phase 55 (v1.4) | Second field graduation; follows tag precedent from v1.2.1 |
| `DomainLogic.normalize_clear_intents` handles `note=None → note=""` | `DomainLogic.process_note_action` handles full note composition, `normalize_clear_intents` loses the note branch | Phase 55 (D-14) | Domain layer honesty — no unreachable code |
| `PayloadBuilder.build_edit(command, ...)` reads note from `command.note` via `_add_if_set` | `build_edit(command, ..., note_value=UNSET)` takes note as explicit parameter | Phase 55 | Decouples payload construction from command shape; cleaner separation of "what to send" from "what was requested" |
| `NOTE_EDIT_COMMAND` description constant | `NOTE_ACTION_DOC`, `NOTE_ACTION_APPEND`, `NOTE_ACTION_REPLACE` family | Phase 55 (D-15) | Parallels `TAG_ACTION_*` family; AST-enforced |

**Deprecated/outdated:**
- `NOTE_EDIT_COMMAND` in `descriptions.py:181` — delete in Phase 55. Also delete its import at `contracts/use_cases/edit/tasks.py:19`.
- `normalize_clear_intents` note branch at `domain.py:484-485` — delete in Phase 55 (D-14).

## Assumptions Log

> All factual claims in this research were verified against the codebase via Read and Grep in this session, or cited directly from CONTEXT.md (which was itself derived from a discuss-phase session). **No items are tagged [ASSUMED].**

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| — | (none) | — | — |

The only Claude's-discretion items (warning constant names, 3-tuple vs NamedTuple) are called out explicitly as such in CONTEXT §Claude's Discretion — they are not assumed facts but deferred decisions.

## Open Questions (RESOLVED)

1. **Should Plan 01 or Plan 02 add the three new warning constants?**
   - What we know: D-15 puts `NOTE_ACTION_*` description constants in Plan 01 (contract layer). But the three no-op warning constants (N1/N2/N3) are *only* used by `process_note_action` in Plan 02.
   - What's unclear: Whether adding unused warning constants in Plan 01 triggers a test failure. The `test_all_description_constants_referenced_in_consumers` test only covers `descriptions.py`, not `warnings.py`. Grep shows no equivalent AST-enforced check for `warnings.py`.
   - Recommendation: Add warning constants in Plan 02 (where they're first consumed). Add error constants (`NOTE_APPEND_WITH_REPLACE`, `NOTE_NO_OPERATION`) in Plan 01 because they ARE consumed by the contract validator in Plan 01.
   - **RESOLVED:** Plan 02 Task 1 adds `NOTE_APPEND_EMPTY`, `NOTE_REPLACE_ALREADY_CONTENT`, `NOTE_ALREADY_EMPTY` in `src/omnifocus_operator/agent_messages/warnings.py` (where `process_note_action` first consumes them). Plan 01 Task 1 adds `NOTE_APPEND_WITH_REPLACE` and `NOTE_NO_OPERATION` in `agent_messages/errors.py` (consumed by the `NoteAction` validator in the same plan). Matches the recommendation above.

2. **Should Plan 03 split into 3a (mechanical) / 3b (new coverage) or stay monolithic?**
   - What we know: D-16 says "two-pass". Could be one plan with two sequential tasks or two plans.
   - What's unclear: GSD plan granularity policy — the phase's `config.json` has `"granularity": "coarse"`, suggesting fewer, larger plans.
   - Recommendation: Keep as one Plan 03 with Pass 1 and Pass 2 as distinct task groups inside it. Matches the coarse granularity signal.
   - **RESOLVED:** Single Plan 03 with two tasks — Task 1 (tool description update, D-10/D-11) + Task 2 (integration tests + NOTE-01 schema regression + NOTE-05 regression verification). Pass 1 mechanical rewrites moved earlier (Plan 01 Task 2). Pass 2 contract-validator tests moved earlier as well (Plan 01 Task 1 in revision round 2). Plan 03 owns the remaining integration + tool-description surface. Matches coarse granularity.

3. **Does `EditTaskCommand.actions.note = NoteAction(replace=None)` skip the bridge, or does it send `note: ""`?**
   - What we know: CONTEXT D-06 says N3 (clear on already-empty note) skips the bridge. D-14 says clearing a non-empty note sends `""` to the bridge.
   - What's unclear: Nothing — this IS answered by CONTEXT. Pseudocode in Pattern 2 implements correctly. Calling out here only as a sanity-check for the planner.
   - Recommendation: No ambiguity; pattern is correct as documented.
   - **RESOLVED:** `DomainLogic.process_note_action` (Plan 02 Task 2) returns `""` (not UNSET) when clearing a non-empty note — the bridge receives `note: ""` via `PayloadBuilder.build_edit`'s new `note_value=""` kwarg path (Plan 02 Task 3). When the note is already empty (or whitespace-only, strip-and-check per D-08), the method returns UNSET so `PayloadBuilder` skips the `note` kwarg entirely and the bridge is not called for note; the N3 warning (`NOTE_ALREADY_EMPTY`) is surfaced in `EditTaskResult.warnings`. Pipeline wiring + precedence (N3 before N2 per Pitfall 3) is locked in Plan 02.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio (detected from `tests/__pycache__/*.cpython-312-pytest-9.0.2.pyc`) |
| Config file | `pyproject.toml` (pytest settings) |
| Quick run command | `uv run pytest tests/test_service_domain.py tests/test_contracts_type_aliases.py -x -q` |
| Full suite command | `uv run pytest -x -q` |
| Output schema regression | `uv run pytest tests/test_output_schema.py -x -q` (MANDATORY after any model change per project CLAUDE.md) |
| AST enforcement | `uv run pytest tests/test_descriptions.py -x -q` (catches inline strings / missing constants) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| NOTE-01 | Top-level `note` removed from `EditTaskCommand` | unit (schema) | `uv run pytest tests/test_output_schema.py::TestWriteSchemaNoDateTimeFormat -x -q` (and a new `test_edit_task_command_no_top_level_note`) | ❌ new test needed (Wave 0) |
| NOTE-01 | AST check: `NOTE_EDIT_COMMAND` no longer referenced | unit (AST) | `uv run pytest tests/test_descriptions.py::TestDescriptionConsolidation::test_all_description_constants_referenced_in_consumers -x -q` | ✅ existing |
| NOTE-01 | Agent error is educational when old API used | unit (ValidationError) | `uv run pytest tests/test_contracts_type_aliases.py -x -q` (after rewrite) | ✅ existing (needs Pass 1 rewrite) |
| NOTE-02 | `append` adds text with `\n\n` separator on non-empty note | unit (domain) | `uv run pytest tests/test_service_domain.py::TestProcessNoteAction::test_append_on_non_empty_note -x -q` | ❌ new test needed |
| NOTE-02 | `append: ""` is a no-op with warning (N1) | unit (domain) | `uv run pytest tests/test_service_domain.py::TestProcessNoteAction::test_append_empty_string_is_noop -x -q` | ❌ new test needed |
| NOTE-02 | `append: None` rejected by type | unit (contract) | `uv run pytest tests/test_contracts_actions.py::TestNoteAction::test_append_null_rejected -x -q` | ❌ new file needed (Wave 0) — OR add to existing `tests/test_service_domain.py` (Claude's discretion) |
| NOTE-03 | `replace` with new string sets note | unit (domain) + integration | `uv run pytest tests/test_service.py::TestEditTask::test_patch_note_only -x -q` (after rewrite) | ✅ existing (needs Pass 1 rewrite) |
| NOTE-03 | `replace: None` clears note on non-empty | integration | `uv run pytest tests/test_service.py::TestEditTask::test_note_null_clears_note -x -q` (after rewrite) | ✅ existing (needs Pass 1 rewrite) |
| NOTE-03 | `replace: ""` clears note on non-empty | integration | `uv run pytest tests/test_service.py::TestEditTask::test_clear_note_with_empty_string -x -q` (after rewrite) | ✅ existing (needs Pass 1 rewrite) |
| NOTE-03 | Identical-content replace is no-op with warning (N2) | unit (domain) | `uv run pytest tests/test_service_domain.py::TestProcessNoteAction::test_replace_identical_content_is_noop -x -q` | ❌ new test needed |
| NOTE-03 | Clear-already-empty is no-op with warning (N3) | unit (domain) | `uv run pytest tests/test_service_domain.py::TestProcessNoteAction::test_clear_already_empty_is_noop -x -q` | ❌ new test needed |
| NOTE-04 | Append on empty note sets directly (no separator) | unit (domain) | `uv run pytest tests/test_service_domain.py::TestProcessNoteAction::test_append_on_empty_note_sets_directly -x -q` | ❌ new test needed |
| NOTE-04 | Append on whitespace-only note discards whitespace | unit (domain) | `uv run pytest tests/test_service_domain.py::TestProcessNoteAction::test_append_on_whitespace_only_note -x -q` | ❌ new test needed |
| NOTE-05 | `AddTaskCommand.note` unchanged | integration (regression) | `uv run pytest tests/test_service.py::TestAddTask -x -q` | ✅ existing (no changes) |
| NOTE-01..05 | Output schema unchanged (EditTaskResult) | unit (schema) | `uv run pytest tests/test_output_schema.py -x -q` | ✅ existing |
| Exclusivity | `{append, replace}` both set → `NOTE_APPEND_WITH_REPLACE` error | unit (contract validator) | `uv run pytest tests/test_contracts_actions.py::TestNoteAction::test_append_and_replace_rejected -x -q` | ❌ new file OR new class |
| At-least-one | `{}` → `NOTE_NO_OPERATION` error | unit (contract validator) | `uv run pytest tests/test_contracts_actions.py::TestNoteAction::test_empty_rejected -x -q` | ❌ new file OR new class |
| Pipeline | Note action only (no other actions) is valid | integration | `uv run pytest tests/test_service.py::TestEditTask::test_note_action_alone -x -q` | ❌ new test needed (spec line 195) |
| Pipeline | Note + tags + move in one call | integration | `uv run pytest tests/test_service.py::TestEditTask::test_note_with_other_actions -x -q` | ❌ new test needed |

### Test Dimensions (Nyquist — minimum sufficient coverage)

| Dimension | Purpose | Count (estimate) |
|-----------|---------|------------------|
| **Contract-layer unit (Pydantic validators)** | `NoteAction` exclusivity, at-least-one, type rejection | 4–5 tests |
| **Domain-layer unit (`process_note_action`)** | Each branch of the decision tree: UNSET, append-empty, append-on-empty, append-on-non-empty, replace-identical, clear-on-empty, clear-on-non-empty, replace-with-new-content | 8 tests |
| **Service-layer integration (`_EditTaskPipeline`)** | Pipeline threads note through to payload; no-op detection composes with `detect_early_return`; warnings surface in `EditTaskResult.warnings` | 5–7 tests |
| **Regression** | `AddTaskCommand` unchanged; `EditTaskResult` output schema unchanged; `add_tasks` flow unchanged | 2–3 tests (mostly existing) |
| **AST enforcement** | `test_descriptions.py` catches any inline-string regression | 0 new (existing suite runs as-is) |

### Property-based candidates

- **Append invariance:** `append(note, "") == note` (no-op). Hypothesis/property test over `note: str`.
- **Whitespace idempotence:** `append("   \n  ", x) == x` (whitespace-only note becomes `x`, not `"   \n  \n\nx"`).
- **Paragraph-separator always double-newline:** Property test: for any non-empty `note` and non-empty `append_text`, the result contains exactly `"\n\n"` between them (not `"\n"`, not `"\n\n\n"`).

These are optional polish — mark as "should-have" not "must-have" in the plan. Deterministic table-driven tests cover the same surface.

### Golden master touchpoints

**None.** [VERIFIED: bridge unchanged per CONTEXT §Non-decisions.] Golden master snapshots capture bridge I/O, and Phase 55 sends the same `note: string | null` payload the bridge has always accepted (`bridge/tests/handleEditTask.test.js:178-186`). No GM recapture required. Confirmed: `project_golden-master-human-only` memory rule applies — if GM somehow needs refresh, that's human-only anyway.

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_service_domain.py tests/test_service.py tests/test_service_payload.py tests/test_contracts_type_aliases.py tests/test_descriptions.py tests/test_output_schema.py -x -q` (fast feedback on all affected files)
- **Per wave/plan merge:** `uv run pytest -x -q` (full suite — 2086 tests, ~project standard)
- **Phase gate:** Full suite green + mypy clean + `uv run pytest tests/test_output_schema.py` green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] **New test class** `TestProcessNoteAction` in `tests/test_service_domain.py` — unit tests for `DomainLogic.process_note_action` (8 tests)
- [ ] **New test file OR new class** for `NoteAction` contract validator — exclusivity, at-least-one, type rejection (4–5 tests). Options:
  - Add to existing `tests/test_service_domain.py` near the normalize_clear_intents tests (simplest, stays with related behavior)
  - Create `tests/test_contracts_actions.py` (cleaner split; no existing file)
  - Planner/executor discretion per CONTEXT §Claude's Discretion
- [ ] **New integration tests** in `tests/test_service.py::TestEditTask` — note-alone, note-with-other-actions, no-op warning propagation end-to-end (3–4 tests)
- [ ] **Schema regression test** — add a test that asserts `EditTaskCommand` JSON schema has no top-level `note` property (in `tests/test_output_schema.py`).
- [ ] **Framework install:** None needed — pytest already present per pyproject.toml.

### Edge-case coverage for strip-and-check

| Input (existing note) | Input (append/replace) | Expected | Test |
|----------------------|------------------------|----------|------|
| `None` | `append: "hello"` | result = `"hello"` (no separator) | unit |
| `""` | `append: "hello"` | result = `"hello"` (no separator) | unit |
| `"   "` (three spaces) | `append: "hello"` | result = `"hello"` (whitespace discarded per D-09) | unit |
| `"\n\t \n"` | `append: "hello"` | result = `"hello"` (Unicode-safe whitespace check via `str.strip()`) | unit |
| `"already there"` | `append: "hello"` | result = `"already there\n\nhello"` | unit |
| `"already there\n\n"` | `append: "hello"` | result = `"already there\n\n\n\nhello"` (literal concat, no collapse) | unit — document this behavior |
| `None` | `replace: None` | N3 warning, no bridge call | unit |
| `""` | `replace: ""` | N3 warning, no bridge call | unit |
| `"   "` | `replace: None` | N3 warning (whitespace-only treated as empty per D-08) | unit |
| `"content"` | `replace: "content"` | N2 warning, no bridge call | unit |
| `"content"` | `replace: "other"` | result = `"other"`, no warning | unit |
| `"content"` | `replace: None` | result = `""`, bridge called with `note=""` | unit + integration |
| `"content"` | `replace: ""` | result = `""`, bridge called with `note=""` | unit + integration |
| (no note action) | — | `process_note_action` returns `(UNSET, True, [])`, payload has no `note` field | unit |
| N/A | `append: ""` on any existing | N1 warning, no bridge call | unit |
| N/A | `append: "   "` on non-empty | result = `"existing\n\n   "` (whitespace-only append is NOT N1) | unit — document this nuance per Pitfall 4 |

Unicode whitespace: Python's `str.strip()` handles Unicode whitespace (U+00A0, U+2028, etc.) correctly — no special handling needed. One test confirming `"\u00a0"` strips to `""` is sufficient.

## Project Constraints (from CLAUDE.md)

Active constraints from `./CLAUDE.md` and `~/.claude/CLAUDE.md` relevant to Phase 55:

- **SAFE-01:** No `RealBridge` in automated tests or CI — all tests use `InMemoryBridge` or `SimulatorBridge`. Phase 55 tests fall squarely under this — bridge factory raises if `PYTEST_CURRENT_TEST` is set. CI grep-enforced on literal class name.
- **SAFE-02:** UAT in `uat/` is manual, human-only. Agent must never run `uat/` scripts. Phase 55 UAT (if any) happens via Flo manually.
- **Method Object pattern:** All new service use cases use `_VerbNounPipeline` inheriting from `_Pipeline`. Phase 55 does NOT create a new pipeline — it extends existing `_EditTaskPipeline`. New `DomainLogic` method uses mutable `self` state per existing precedent (not applicable since `process_note_action` is a pure function on `DomainLogic`).
- **Model taxonomy:** `NoteAction` lives in `contracts/shared/actions.py` (follows TagAction/MoveAction placement). Ends with recognized suffix `"Action"` → passes `CONTRACT_SUFFIXES` check.
- **Output schema regression:** After any model that affects tool output, run `uv run pytest tests/test_output_schema.py -x -q`. `EditTaskCommand` change affects `edit_tasks` inputSchema — MUST run this test. `EditTaskResult` is unchanged so outputSchema side is safe, but running the full suite is cheap and mandatory per project CLAUDE.md.
- **"the real Bridge" in comments:** CI greps for literal `RealBridge` outside test scaffolding. Phase 55 adds no bridge-related comments; N/A.
- **Contracts are pure data** (memory `feedback_contracts-are-pure-data`): No `model_serializer` or transformation logic in `contracts/`. `NoteAction` is purely field definitions + one validator — compliant.
- **UAT is human-initiated only** (memory `feedback_uat-human-initiated-only`): Phase 55 planning does not autonomously invoke UAT regression or touch real OmniFocus.

## Security Domain

Not applicable — `security_enforcement: false` in `.planning/config.json` per session-start state. Phase 55 is a contract/service refactor with no authentication, authorization, cryptography, or external I/O changes. Input validation (NoteAction) uses standard Pydantic patterns — already covered by existing `ValidationReformatterMiddleware`.

## Sources

### Primary (HIGH confidence)
- **CONTEXT.md** (`.planning/phases/55-notes-graduation/55-CONTEXT.md`) — 16 locked decisions (D-01 through D-16), canonical refs, code context, specifics. [Read in session.]
- **MILESTONE-v1.4.md** §Notes Graduation (`.research/updated-spec/MILESTONE-v1.4.md:169-196`) — primary spec. [Read in session.]
- **Codebase direct read (VERIFIED):**
  - `src/omnifocus_operator/contracts/shared/actions.py:36-63` — TagAction template
  - `src/omnifocus_operator/contracts/shared/actions.py:66-98` — MoveAction (field_validator precedent for null rejection with custom message)
  - `src/omnifocus_operator/contracts/shared/actions.py:101` — `__all__` export list
  - `src/omnifocus_operator/contracts/use_cases/edit/tasks.py:19` — NOTE_EDIT_COMMAND import
  - `src/omnifocus_operator/contracts/use_cases/edit/tasks.py:41-53` — EditTaskActions current shape
  - `src/omnifocus_operator/contracts/use_cases/edit/tasks.py:75` — EditTaskCommand.note field (to be removed)
  - `src/omnifocus_operator/contracts/use_cases/edit/tasks.py:127-142` — EditTaskRepoPayload (unchanged)
  - `src/omnifocus_operator/contracts/base.py:51-77` — Patch, PatchOrClear, UNSET, is_set, unset_to_none
  - `src/omnifocus_operator/agent_messages/errors.py:44-48` — TAG_REPLACE_WITH_ADD_REMOVE, TAG_NO_OPERATION (NOTE error precedent)
  - `src/omnifocus_operator/agent_messages/warnings.py:27-59` — MOVE_ALREADY_AT_POSITION, LIFECYCLE_ALREADY_IN_STATE, TAGS_ALREADY_MATCH, TAG_ALREADY_ON_TASK, TAG_NOT_ON_TASK (no-op warning precedent)
  - `src/omnifocus_operator/agent_messages/descriptions.py:115-121, 179-183, 333-337, 353` — TAG_ACTION_DOC/ADD/REMOVE/REPLACE, NOTE_EDIT_COMMAND, NOTE_ADD_COMMAND, EDIT_TASK_ACTIONS_DOC
  - `src/omnifocus_operator/agent_messages/descriptions.py:655-692` — EDIT_TASKS_TOOL_DOC (update target)
  - `src/omnifocus_operator/service/domain.py:474-495` — normalize_clear_intents (dead branch at 484-485)
  - `src/omnifocus_operator/service/domain.py:499-529` — process_lifecycle (shape template)
  - `src/omnifocus_operator/service/domain.py:971-1097` — detect_early_return and _all_fields_match (no-op pattern for how payload fields_set interacts with task state)
  - `src/omnifocus_operator/service/service.py:664-981` — _EditTaskPipeline full sequence
  - `src/omnifocus_operator/service/service.py:713-722` — _resolve_actions (extension point)
  - `src/omnifocus_operator/service/service.py:944-964` — _build_payload (warning aggregation)
  - `src/omnifocus_operator/service/payload.py:62-98` — PayloadBuilder.build_edit (line 77 is the `_add_if_set(..., "note", ...)` call)
  - `src/omnifocus_operator/server/handlers.py:156-157` — edit_tasks handler signature (uses `EditTaskCommand` directly; FastMCP regenerates schema)
  - `tests/test_descriptions.py:127-201` — AST enforcement (inline-description and inline-docstring checks)
  - `tests/test_descriptions.py:118-125` — constant-referenced-in-consumer check
  - `tests/test_output_schema.py:536-616` — naming convention enforcement (CONTRACT_SUFFIXES, CONTRACTS_EXEMPT)
  - `tests/test_output_schema.py:676-683` — EditTaskCommand schema no-date-time-format assertion
  - `tests/test_service_domain.py:649-665` — existing note-related normalize_clear_intents tests (to delete per D-14)
  - `tests/test_service.py:644-654, 644-672, 962-972, 1202-1223, 1235-1245, 1259-1282` — existing EDIT note tests (Pass 1 rewrite targets)
  - `tests/test_service_payload.py:113-133, 231-239` — build_edit note tests (rewrite targets)
  - `tests/test_contracts_type_aliases.py:93` — PatchOrClear[str] test using note (rewrite target)
  - `bridge/tests/handleEditTask.test.js:178-186` — bridge `note: null` / `note: string` contract (confirmed unchanged)
- **docs/architecture.md §Field graduation** (lines 707-742) — canonical pattern doc; `note` explicitly named as next graduation example.
- **docs/architecture.md §Agent-facing messages** (lines 743-753) — warning wording conventions.
- **.planning/config.json** — workflow settings (nyquist_validation enabled, security_enforcement disabled, commit_docs enabled, granularity coarse).

### Secondary (MEDIUM confidence)
- None — all claims verified directly in codebase. No web searches needed; this is a self-contained refactor.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no external libraries needed; all primitives verified in session.
- Architecture patterns: HIGH — TagAction, MoveAction, and process_lifecycle are direct read-in-session templates with exact line numbers.
- Migration surface: HIGH — every `note=` occurrence was grep'd and classified.
- Pitfalls: MEDIUM — synthesized from reading code + architectural constraints; not yet seen in practice for this phase but analogous pitfalls documented from prior graduations.
- Validation architecture: HIGH — existing test infrastructure mapped; Wave 0 gaps enumerated.

**Research date:** 2026-04-16
**Valid until:** 2026-05-16 (30 days — codebase is stable, Phase 54 just shipped 2026-04-15)
