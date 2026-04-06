# Phase 42: Read Output Restructure - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-06
**Phase:** 42-read-output-restructure
**Areas discussed:** Tagged parent model, Enrichment strategy, Tool descriptions, ParentRef removal

---

## Tagged Parent Model

| Option | Description | Selected |
|--------|-------------|----------|
| Wrapper model | Single ParentRef with project/task optional fields + exactly-one validator. MoveAction pattern. | |
| Two wrapper types | ProjectParent + TaskParent as discriminated union. Type-safe but more models. | |
| Custom serializer | Keep ProjectRef \| TaskRef internally, wrap during serialization. Violates "contracts are pure data." | |

**User's choice:** Locked by milestone spec (DL-12) — wrapper model with exactly-one validator is prescribed. Not a gray area.
**Notes:** Milestone spec explicitly rejected alternatives (a)-(c). Tagged object pattern already proven in MoveAction.

### Naming

| Option | Description | Selected |
|--------|-------------|----------|
| ParentRef (reuse) | Same semantic concept, new structure. Old deleted in same phase. Stays in *Ref family. | ✓ |
| TaggedParent | Describes the pattern. But "Tagged" collides with OmniFocus Tags concept. | |
| ParentContainer | Emphasizes container semantics. But "container" overloaded in move context. | |

**User's choice:** ParentRef (reuse)
**Notes:** Old ParentRef is deleted in the same phase, freeing the name. Consistent with TagRef, ProjectRef, FolderRef family.

### Docstring

| Option | Description | Selected |
|--------|-------------|----------|
| MoveAction pattern | "Direct parent of this task. Exactly one key present: 'project' or 'task', each with {id, name}." $inbox on inner field. | ✓ |

**User's choice:** MoveAction pattern — same "exactly one key" phrasing, $inbox on project field description.

---

## Enrichment Strategy

### Lookup strategy for single-entity reads

| Option | Description | Selected |
|--------|-------------|----------|
| Targeted queries | Follow _read_task() pattern: query only the one name needed per entity. | ✓ |
| Full lookups always | Reuse _build_* functions even for single reads. Simpler but fetches more data. | |
| Claude's discretion | Let executor decide per-method. | |

**User's choice:** Targeted queries
**Notes:** Consistent with existing _read_task() which builds minimal ad-hoc lookups.

### Mapper helper split

| Option | Description | Selected |
|--------|-------------|----------|
| Two functions | Replace _build_parent_ref with _build_tagged_parent() and _build_project_ref(). | |
| Inline in mapper | Build both fields directly inside _map_task_row. | |
| Claude's discretion | Let executor decide based on code clarity. | ✓ |

**User's choice:** Claude's discretion

---

## Tool Descriptions

### Format evolution (chat discussion, no AskUserQuestion)

User provided detailed feedback on description format through iterative chat:

1. **No line breaks within field lists** — agents can parse flowing text
2. **Line breaks only between sections** — separate description, fields, notable fields
3. **Notable field explanations below fields** — format: `fieldName: explanation`, one per line
4. **Remove "The response uses camelCase field names."** — agents figure it out
5. **Rename "Key fields" to "Fields"** (or "Fields per task") — they're all fields
6. **Move inline explanations (nextTask, mutuallyExclusive) to notable fields section** — don't mix type info and explanations
7. **Effective fields** — brief note in notable section, not inline annotation

All 7 tool description constants drafted verbatim in CONTEXT.md. User approved format via iterative refinement.

**Notes:** User emphasized these must be included VERBATIM in the plan — executor must use exact wording, not paraphrase.

---

## ParentRef Removal

### Bridge_only in_inbox filtering

| Option | Description | Selected |
|--------|-------------|----------|
| Use project.id | Filter becomes t.project.id == SYSTEM_LOCATIONS["inbox"].id. Uses new field. | ✓ |
| Claude's discretion | Any approach maintaining cross-path equivalence. | |

**User's choice:** Use project.id
**Notes:** User corrected constant reference from `SYSTEM_LOCATION_INBOX` to `SYSTEM_LOCATIONS["inbox"].id` (updated in Phase 39/40).

### Inbox hierarchy semantics

User flagged important distinction: bridge `inInbox` only marks root inbox tasks, while `project.id == "$inbox"` covers full hierarchy. User believes this is correct behavior per milestone spec but noted golden master should confirm. If wrong, fix in follow-up.

---

## Claude's Discretion

- Mapper helper split (build_tagged_parent vs inline)
- Bridge adapter cross-entity enrichment architecture
- models/__init__.py wiring details
- Test organization
- Whether adapter strips inInbox explicitly or relies on model ignoring extras

## Deferred Ideas

- *(D-19 placeholder resolved — see update session below)*

---

## Update Session: Field-Level Descriptions (2026-04-06)

Finalized D-19 placeholder into D-19 through D-26. All fields changing from scalar (ID string) to rich `{id, name}` reference objects.

| Constant | New Description | Notes |
|----------|----------------|-------|
| NEXT_TASK | "First available (unblocked) task in this project." | Drops "ID of", drops "if any" (nullability from schema) |
| FOLDER_PARENT_DESC | "Parent folder in the folder hierarchy." | Drops "ID", drops "or null" |
| PROJECT_FOLDER_DESC (new) | "Folder containing this project." | Previously bare field |
| TAG_PARENT_DESC (new) | "Parent tag in the tag hierarchy." | Previously bare field |
| TASK_PROJECT_DESC (new) | "Project for this task, even for subtasks." | New field. User refined from "The task's project" to noun-phrase form for consistency |
| PARENT_REF_DOC | "Direct parent of this task. Exactly one key present: 'project' or 'task'." | Dropped {id, name} detail (visible from schema) and $inbox mention (self-documenting in data) |
| PARENT_REF_PROJECT_FIELD (new) | "Parent project." | $inbox dropped — self-explanatory when agents see the data |
| PARENT_REF_TASK_FIELD (new) | "Parent task, when this is a subtask." | — |

**Key user decisions:**
- No $inbox mentions in output-side descriptions — only relevant on filter descriptions (Phase 43)
- All descriptions verbatim — executor must use exact wording
