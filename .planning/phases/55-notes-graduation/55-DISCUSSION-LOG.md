# Phase 55: Notes Graduation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 55-notes-graduation
**Areas discussed:** NoteAction shape & exclusivity, No-op warning semantics, Whitespace-only existing note (mostly closed by spec), Tool description & migration messaging, Implementation architecture (E: composition location, F: dead-code cleanup, G: description constants, H: test migration)

---

## Area 1: NoteAction shape & exclusivity

| Option | Description | Selected |
|--------|-------------|----------|
| Full TagAction parity | append XOR replace. At least one operation required. Two new educational errors. Mirrors TagAction exactly. | ✓ |
| Exclusive, empty action OK | append XOR replace, but `{actions: {note: {}}}` passes silently (no-op at action level). | |
| Allow both with defined order | `{append, replace}` legal — replace then append. No codebase precedent. | |

**User's choice:** Full TagAction parity
**Notes:** User initially paused the question to ask that the milestone spec be read first. After reading MILESTONE-v1.4.md in full, the question was reformulated acknowledging what the spec closes vs leaves open. User accepted the recommended option on reformulation.

---

## Area 2: No-op warning semantics

| Option | Description | Selected |
|--------|-------------|----------|
| All three (N1+N2+N3), N4 out | Full setter-no-op parity: empty append, identical-content replace, clear-already-empty. N4 (duplicate append) not detected. | ✓ |
| Only empty append (N1) | Only N1 detected; replace always hits bridge (idempotent). | |
| Silent no-ops everywhere | Detect to skip bridge, but no warnings. Breaks codebase pattern. | |
| No detection — always call bridge | Zero service-side no-op logic. | |

**User's choice:** All three (N1+N2+N3), N4 out
**Notes:** Matches the established setter no-op pattern from `architecture.md` §724 and existing `MOVE_ALREADY_AT_POSITION` / `LIFECYCLE_ALREADY_IN_STATE` warnings. N4 (semantic duplicate-append detection) excluded because append's contract is concatenation, not deduplication.

---

## Area 3: Whitespace-only existing note

**Status:** Mostly closed by milestone spec (lines 193-194). Presented as clarification rather than decision. No AskUserQuestion call needed.

- Spec locks: "Append on empty/whitespace-only note → set directly (no leading separator)"
- Spec locks: "Whitespace-only existing note treated as empty (strip and check)"
- Implication captured in CONTEXT.md D-08/D-09: strip-and-check rule applies uniformly to both no-op detection and append-composition logic.

---

## Area 4: Tool description & migration messaging

| Option | Description | Selected |
|--------|-------------|----------|
| Standard, no migration framing | Document actions.note matter-of-factly like tags/move/lifecycle. No "was top-level before" hint. | ✓ |
| Light discoverability hint | One line in edit_tasks description: "Note edits go through actions.note (append / replace)." | |
| Explicit breaking-change call-out | Dedicated "Breaking change" or "Note:" block. Contradicts pre-release/no-compat stance. | |

**User's choice:** Standard, no migration framing
**Notes:** Consistent with the pre-release + no-compat prior decision (memory: `project_pre-release-no-compat.md`). No external agents exist to migrate. Description avoids dated framing that would feel stale after v1.4 ships.

---

## Area E: Composition logic location

| Option | Description | Selected |
|--------|-------------|----------|
| New DomainLogic method | `process_note_action(command, task) → (new_note_or_UNSET, should_skip_bridge, warnings)`. Parallels `process_lifecycle`. | ✓ |
| Extend normalize_clear_intents | Conflates null→empty normalization with composition + no-op detection. | |
| Put composition in PayloadBuilder | Breaks "PayloadBuilder stays pure construction" prior decision. | |

**User's choice:** New DomainLogic method

---

## Area F: Dead-code cleanup

| Option | Description | Selected |
|--------|-------------|----------|
| Remove in this phase | Ship cleanup alongside the feature making the branch dead. Keeps domain layer honest. | ✓ |
| Leave it, address in cleanup pass later | Smaller diff per phase, but cleanup might never happen. | |

**User's choice:** Remove in this phase
**Notes:** The `command.note is None` branch in `DomainLogic.normalize_clear_intents` (`service/domain.py:484-485`) becomes unreachable after NOTE-01 removes the top-level `note` field from `EditTaskCommand`.

---

## Area G: Description constants strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Delete + new family | Mirror TagAction constants: NOTE_ACTION_DOC, NOTE_ACTION_APPEND, NOTE_ACTION_REPLACE. | ✓ |
| Rename to NOTE_ACTION_REPLACE | Repurpose existing constant. Smaller diff, but old text was written for top-level setter. | |

**User's choice:** Delete + new family

---

## Area H: Test migration strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Mechanical rewrite, then coverage review | Two-pass: preserve existing coverage first, then add new append/exclusivity/no-op tests. | ✓ |
| Delete old + write fresh | Risk losing edge cases the old tests encoded. | |
| Add alongside, delete later | Lowest risk but biggest test-code churn. | |

**User's choice:** Mechanical rewrite, then coverage review

---

## Claude's Discretion

- Exact names and wording of new warning/error constants (`NOTE_APPEND_EMPTY`, `NOTE_REPLACE_ALREADY_CONTENT`, `NOTE_ALREADY_EMPTY`, plus the two validation errors)
- Whether `process_note_action` returns a 3-tuple, NamedTuple, or small dataclass
- Internal helper decomposition inside `process_note_action` (single method vs split `_detect_note_no_op` + `_compose_note`)
- Test file organization (single `test_note_action.py` vs split across contract/service)
- Exact wording of `EditTaskActions.__doc__` update to list note alongside tags/move/lifecycle

## Deferred Ideas

- Note metadata (created-at, modified-at)
- Rich text / formatted notes
- Note templates / macros
- Clipboard-style append with deduplication (N4 explicitly out)
- Cross-item note references in a batch
