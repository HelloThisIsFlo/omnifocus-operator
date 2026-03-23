# Phase 25: Patch/PatchOrClear Type Aliases - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Command model field annotations use `Patch[T]`, `PatchOrClear[T]`, and `PatchOrNone[T]` type aliases to make patch semantics self-documenting. `changed_fields()` helper added to `CommandModel` base class. Pure readability change with identical JSON schema output. No behavioral changes, no service-layer modifications.

</domain>

<decisions>
## Implementation Decisions

### Type alias definitions
- **D-01:** Three aliases defined in `contracts/base.py` using `TypeVar + Union` approach (the only approach that produces clean JSON schema + passes mypy — validated in `.research/deep-dives/simplify-sentinel-pattern/FINDINGS.md`)
- **D-02:** `Patch[T]` = `Union[T, _Unset]` — for value-only patchable fields (field can be set or omitted, cannot be cleared)
- **D-03:** `PatchOrClear[T]` = `Union[T, None, _Unset]` — for clearable fields where `None` means "clear the value"
- **D-04:** `PatchOrNone[T]` = `Union[T, None, _Unset]` — for fields where `None` carries domain meaning (not "clear"). Same Union as PatchOrClear, different semantic signal
- **D-05:** Brief comment in `base.py` explaining why `PatchOrClear` and `PatchOrNone` both exist despite being the same Union — prevents future "cleanup" that merges them

### Semantic boundary for alias usage
- **D-06:** `PatchOrClear[T]` used where `None` genuinely means "clear the field" — EditTaskCommand's `note`, `due_date`, `defer_date`, `planned_date`, `estimated_minutes`
- **D-07:** `PatchOrNone[T]` used where `None` carries domain meaning — MoveAction's `beginning` (None = inbox), `ending` (None = inbox); TagAction's `replace` (None = clear all tags, but this is a domain operation not a field-clear)
- **D-08:** `Patch[T]` used for value-only fields — EditTaskCommand's `name`, `flagged`; EditTaskActions' `tags`, `move`, `lifecycle`; TagAction's `add`, `remove`; MoveAction's `before`, `after`

### changed_fields() helper
- **D-09:** Method on `CommandModel` base class — all command models (EditTaskCommand, EditTaskActions, TagAction, MoveAction, repo payloads) inherit it automatically
- **D-10:** Flat implementation — nested CommandModel values returned as model instances, not recursively expanded to dicts
- **D-11:** Returns `dict[str, Any]` of all fields whose value is not `_Unset`
- **D-12:** Coexists with `is_set()` permanently — different tools for different jobs. `is_set()` = per-field type-safe branching (TypeGuard). `changed_fields()` = iterate all set fields as data (testing, logging, generic processing)
- **D-13:** Primary consumer in Phase 25 is tests — triangulation pattern: tests assert via `changed_fields()`, production code operates via `is_set()`. If a new field is added to a command model but not handled in service code, the test catches the mismatch

### Migration scope
- **D-14:** Model layer only — 4 files in `contracts/`: `base.py`, `common.py`, `use_cases/edit_task.py`, `use_cases/add_task.py`
- **D-15:** Service code untouched — `is_set()` remains the correct tool for service-layer per-field type-specific branching
- **D-16:** `changed_fields()` available for future phases (Phase 26 InMemoryBridge will use it for generic field application)

### Claude's Discretion
- Export surface: whether `Patch`, `PatchOrClear`, `PatchOrNone` are exported from `contracts/__init__.py`
- Exact wording of the comment explaining `PatchOrClear` vs `PatchOrNone`
- Test structure and assertion patterns for schema identity verification
- Whether `add_task.py` needs any annotation changes (no `_Unset` fields currently — verify)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Type alias research (validated approach)
- `.research/deep-dives/simplify-sentinel-pattern/FINDINGS.md` — Full investigation of all alias approaches. §"Approach 2 (TypeVar + Union) — THE WINNER" is the implementation spec. §"changed_fields() helper" has the implementation
- `.research/deep-dives/simplify-sentinel-pattern/02_typevar_union.py` — Working proof of the TypeVar+Union approach
- `.research/deep-dives/simplify-sentinel-pattern/10_cross_module_test.py` — Full model hierarchy test mirroring real codebase

### Current models to migrate
- `src/omnifocus_operator/contracts/base.py` — CommandModel, _Unset, UNSET, is_set (aliases and changed_fields() go here)
- `src/omnifocus_operator/contracts/common.py` — TagAction, MoveAction (field annotations change)
- `src/omnifocus_operator/contracts/use_cases/edit_task.py` — EditTaskCommand, EditTaskActions (field annotations change)
- `src/omnifocus_operator/contracts/use_cases/add_task.py` — AddTaskCommand (verify: no _Unset fields currently)

### Requirements
- `.planning/REQUIREMENTS.md` — TYPE-01 through TYPE-04 definitions

### Todo (originated this phase)
- `.planning/todos/pending/2026-03-18-add-patch-and-patchorclear-type-aliases-to-command-models.md`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_Unset` sentinel + `UNSET` singleton (`contracts/base.py`): Unchanged — aliases wrap it, don't replace it
- `is_set()` TypeGuard (`contracts/base.py`): Unchanged — coexists with `changed_fields()`
- `CommandModel` base class (`contracts/base.py`): `changed_fields()` added here, inherited by all command models

### Established Patterns
- `TypeVar + Union` validated by research — Pydantic resolves `Patch[str]` to `Union[str, _Unset]` at model creation time, identical JSON schema
- `from __future__ import annotations` used in all contracts/ files — string eval compatible with the alias approach
- `model_rebuild()` in `contracts/__init__.py` for forward references — verified compatible in research (`09_forward_refs_and_rebuild.py`)

### Integration Points
- `contracts/__init__.py`: May need to re-export new aliases and trigger model_rebuild after alias definitions
- `contracts/common.py`: TagAction and MoveAction field annotations change
- `contracts/use_cases/edit_task.py`: EditTaskCommand and EditTaskActions field annotations change
- Service layer (`service/payload.py`, `service/domain.py`): NOT touched — continue importing `is_set` as before

</code_context>

<specifics>
## Specific Ideas

- Three aliases not two: `PatchOrNone[T]` exists because raw unions would inevitably get "cleaned up" by a future refactor that doesn't understand MoveAction's None=inbox semantics. A named alias makes the intent unforgettable
- Triangulation testing pattern: tests use `changed_fields()` to verify which fields are set, production uses `is_set()` for type-safe branching — two independent proofs of the same truth catches missing field handlers

</specifics>

<deferred>
## Deferred Ideas

- **Service-layer adoption of `changed_fields()`** — Phase 26's InMemoryBridge is the first natural consumer. Payload.py's `_add_if_set` loops could also migrate, but partial migration (dates still need `is_set()` for `.isoformat()`) would leave mixed patterns. Evaluate per-module when the need arises.

</deferred>

---

*Phase: 25-patch-patchorclear-type-aliases-for-command-models*
*Context gathered: 2026-03-20*
