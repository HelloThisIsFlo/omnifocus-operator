# Phase 41: Write Pipeline -- $inbox in Add/Edit - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Agents can explicitly target inbox in all write operations using `$inbox`, with clear errors for invalid null usage. Build on the Phase 40 resolver (already wired) to handle `$inbox` through the add/edit pipelines, eliminate `PatchOrNone`, and make null errors educational.

</domain>

<decisions>
## Implementation Decisions

### PatchOrNone Elimination (MODL-09, MODL-10)
- **D-01:** Delete `PatchOrNone` type alias from `contracts/base.py` entirely
- **D-02:** `TagAction.replace` switches to `PatchOrClear[list[str]]` — `null` = "clear all tags" was always a clear operation, never "domain meaning." Zero behavioral change; `domain.py` None→[] normalization stays as-is
- **D-03:** `MoveAction.beginning` and `MoveAction.ending` change from `PatchOrNone[str]` to `Patch[str]` — null is no longer accepted

### Null Rejection — MoveAction (WRIT-06, WRIT-07)
- **D-04:** `@field_validator("beginning", "ending", mode="before")` on `MoveAction` intercepts null before Pydantic's type validation
- **D-05:** Validator raises `ValueError` with educational error template from `errors.py` (see D-12 for message wording)
- **D-06:** Error flows through existing `ValidationReformatterMiddleware` — no new error handling infrastructure needed. Follows same pattern as `FrequencyAddSpec._validate_interval` and `_normalize_day_codes`

### AddTaskCommand Parent (WRIT-01, WRIT-02, WRIT-03 revised)
- **D-07:** `AddTaskCommand.parent` changes from `str | None = None` to `Patch[str] = UNSET`
- **D-08:** Schema becomes `{"type": "string"}`, optional, no null in type union — agents see a clean contract
- **D-09:** Omitted parent (UNSET) → creates task in inbox (existing behavior, WRIT-02)
- **D-10:** `parent: "$inbox"` → `resolve_container` returns None → inbox (WRIT-01). Works already via Phase 40 resolver
- **D-11:** `parent: null` → **error, not warning.** Requirement WRIT-03 revised: null is rejected with educational error (see D-13 for message). Rationale: the schema is the documentation — `$inbox` exists as a safety net for agents that see it in responses, not as a primary API. No need for a warning pathway when the schema makes the correct path obvious
- **D-11a:** Field description stays as-is: `"Project or task to place this task under. Omit for inbox."` — don't advertise `$inbox`; agents that encounter it in responses can use it, but omitting is the idiomatic path

### Null Rejection — AddTaskCommand (WRIT-03 revised)
- **D-12:** Same `@field_validator("parent", mode="before")` pattern as MoveAction — intercept null, raise educational error from `errors.py`
- **D-13:** Needs service-layer handling: when `parent` is UNSET, skip resolution and leave parent as None in the bridge payload (inbox). When `parent` is a string, resolve via `resolve_container`

### Error Message Wording
- **D-14:** `MOVE_NULL_CONTAINER`: `"{field} cannot be null. To move a task to the inbox, use '$inbox'. To move into a project or task, provide its name or ID."`
- **D-15:** `ADD_PARENT_NULL`: `"parent cannot be null. Omit the field to create a task in the inbox, or provide a project/task name or ID."`
- **D-16a:** `MOVE_NULL_ANCHOR`: `"{field} cannot be null. before/after positions require a task reference (name or ID). To move into a container, use 'beginning' or 'ending' instead."`

### MoveAction Descriptions (updated)
- **D-20:** `MOVE_ACTION_DOC` simplified: `"Specify where to move a task. Exactly one key must be set."`
- **D-21:** Per-field descriptions added (currently bare fields with no description):
  - `MOVE_BEGINNING`: `"Container to move into (project name/ID, task name/ID, or '$inbox'). Task is placed at the beginning of the container."`
  - `MOVE_ENDING`: `"Container to move into (project name/ID, task name/ID, or '$inbox'). Task is placed at the end of the container."`
  - `MOVE_BEFORE`: `"Sibling task to position relative to (task name/ID). Parent container is inferred."`
  - `MOVE_AFTER`: `"Sibling task to position relative to (task name/ID). Parent container is inferred."`

### before/after Container Detection (WRIT-08)
- **D-16:** Already solved by Phase 40 refactor — cross-type mismatch detection in `_resolve` (lines 94-104 of resolve.py) catches project IDs/names passed to `before`/`after`
- **D-17:** `EntityTypeMismatchError` → domain catches and formats with `ENTITY_TYPE_MISMATCH_ANCHOR`: `"'{value}' is a {resolved_type}. Anchor positions (before/after) require a task reference. To move into {value}, use 'ending' or 'beginning' instead."`
- **D-18:** No additional work needed for WRIT-08 beyond what Phase 40 already delivers
- **D-18a:** `before`/`after` null rejection: add `@field_validator("before", "after", mode="before")` with `MOVE_NULL_ANCHOR` error (same pattern as beginning/ending)

### Requirement Update
- **D-19:** WRIT-03 in REQUIREMENTS.md must be updated from "creates task in inbox + warning" to "returns error (null not accepted in parent field)"

### Claude's Discretion
- Pipeline step ordering within `_AddTaskPipeline` for the UNSET-aware parent handling
- Test organization for new null-rejection validators
- Whether the three null-rejection field validators (container, anchor, parent) share a helper or are inline

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & patterns
- `docs/architecture.md` — Write pipeline diagram, Method Object pattern, validation layers (contract vs service), middleware error reformatting
- `docs/model-taxonomy.md` — Patch/PatchOrClear/PatchOrNone type alias semantics, contract model conventions
- `docs/structure-over-discipline.md` — Design philosophy: schema = documentation, correct path = only path

### Contract layer (modification targets)
- `src/omnifocus_operator/contracts/base.py` — `Patch`, `PatchOrClear`, `PatchOrNone` (to delete), `UNSET`, `is_set`
- `src/omnifocus_operator/contracts/shared/actions.py` — `MoveAction` (beginning/ending type change), `TagAction` (replace type change)
- `src/omnifocus_operator/contracts/use_cases/add/tasks.py` — `AddTaskCommand.parent` (type change to `Patch[str]`)

### Service layer (pipeline adjustments)
- `src/omnifocus_operator/service/service.py` — `_AddTaskPipeline._resolve_parent()` must handle UNSET vs string
- `src/omnifocus_operator/service/domain.py` — `_process_container_move()` and `_process_anchor_move()` — null no longer reaches these
- `src/omnifocus_operator/service/resolve.py` — `resolve_container()` returns None for `$inbox`, unchanged

### Error messages
- `src/omnifocus_operator/agent_messages/errors.py` — New templates: `MOVE_NULL_CONTAINER`, `ADD_PARENT_NULL`
- `src/omnifocus_operator/middleware.py` — `ValidationReformatterMiddleware` passes through model validator messages

### Existing validators (pattern to follow)
- `src/omnifocus_operator/contracts/use_cases/edit/repetition_rule.py` — `@field_validator(mode="before")` examples: `_validate_interval`, `_normalize_day_codes`, `_validate_on_dates`

### Prior phases
- `.planning/phases/39-foundation-constants-reference-models/39-CONTEXT.md` — System location constants in config.py
- `.planning/phases/40-resolver-system-location-detection-name-resolution/40-CONTEXT.md` — Resolver cascade, resolve_container returns None for $inbox

### Requirements
- `.planning/REQUIREMENTS.md` — WRIT-01 through WRIT-08, MODL-09, MODL-10 mapped to this phase

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `resolve_container("$inbox")` → returns `None` (inbox = no parent in bridge payload) — works as-is for WRIT-01, WRIT-04, WRIT-05
- `_resolve` with cross-type mismatch detection (lines 94-104) — already catches container in before/after (WRIT-08)
- `ValidationReformatterMiddleware` — catches Pydantic ValidationError, extracts `e["msg"]` for model validators, reformats as ToolError
- `@field_validator(mode="before")` pattern in FrequencyAddSpec — established precedent for intercepting values before type validation

### Established Patterns
- Error templates in `errors.py` use `{placeholder}` + `.format()` — new templates follow same pattern
- `_AddTaskPipeline` uses Method Object pattern — steps like `_resolve_parent`, `_build_payload` modify pipeline state
- `is_set()` guard for UNSET detection — already used throughout edit pipeline, now needed in add pipeline for parent

### Integration Points
- `_AddTaskPipeline._resolve_parent()` in service.py — must change from `if command.parent` to `if is_set(command.parent)`
- `MoveAction._exactly_one_key` validator — counts UNSET fields, unaffected by type change (Patch[str] still uses UNSET)
- `domain.py _normalize_null_semantics()` — currently converts `ending: None → inbox`. After Phase 41, null never reaches domain; this code path for move becomes dead (should be cleaned up or guarded)

</code_context>

<specifics>
## Specific Ideas

- Field description for `AddTaskCommand.parent` stays as-is: don't advertise `$inbox` — agents that see it in responses can use it, but omitting parent is the idiomatic path to inbox
- Error messages should be educational and suggest the correct action (same agent-first philosophy as all existing errors)
- `PatchOrNone` deletion is a clean removal — only two consumers, both migrating to existing type aliases

</specifics>

<deferred>
## Deferred Ideas

- `$inbox` in field descriptions — revisit if agents consistently fail to discover the `$inbox` syntax. For now, schema clarity + existing description is sufficient
- Additional system locations (`$forecast`, `$flagged`) — tracked as SLOC-F01, future milestone
- Dead code cleanup in `_normalize_null_semantics` for move-to-inbox path — may be cleaned in Phase 41 or left for a future housekeeping pass

</deferred>

---

*Phase: 41-write-pipeline-inbox-in-add-edit*
*Context gathered: 2026-04-06*
