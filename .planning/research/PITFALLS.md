# Domain Pitfalls

**Domain:** System location namespace, tagged union discriminators, name-based resolution, rich references, and breaking model changes on an existing Pydantic v2 MCP server
**Researched:** 2026-04-05
**System context:** OmniFocus Operator v1.3.1 milestone

## Critical Pitfalls

Mistakes that cause rewrites, data corruption, or cascading test failures.

---

### Pitfall 1: Tagged Object Parent Wrapper Serialization With `exclude_defaults`

**What goes wrong:** The tagged object pattern for `parent` (`{"project": {...}}` or `{"task": {...}}`) requires a wrapper model with two optional fields (project and task), where exactly one is set. If the wrapper uses `default=None` for both fields and any serialization path uses `exclude_defaults=True`, the populated field survives but there are subtle interactions:
- A parent-level `exclude_defaults` could strip the wrapper itself if it equals some default
- `@field_serializer` or `@model_serializer` on the wrapper could erase the JSON Schema structure (known prior issue, caught by `test_output_schema.py`)

**Why it happens:** The project already hit this with `Literal` discriminators on the Frequency model (line 193 of `repetition_rule.py`: `type: str  # required, NO default -- survives exclude_defaults`). The tagged object pattern avoids the `Literal` default problem but the wrapper model itself needs careful defaults.

**Consequences:** Parent field silently disappears from serialized output, or JSON Schema doesn't reflect the union correctly. Output schema tests may pass (schema is valid) while runtime serialization is wrong.

**Prevention:**
- `parent` field on `Task` must NOT have a default. Typed as the wrapper, never optional, never defaulted. The spec says "never null, never absent" -- enforce in the type system.
- Do NOT use `exclude_defaults=True` on the `Task.model_dump()` path. The existing codebase doesn't (it uses `exclude_unset` on write payloads, `exclude_defaults` only on the Frequency `@field_serializer`). Keep it that way.
- Do NOT add `@model_serializer` to the wrapper -- project has a known rule: contracts are pure data, no transformation logic.
- Add a dedicated serialization test: serialize a Task with a project parent and a task parent, assert the JSON includes `{"project": {...}}` / `{"task": {...}}` structure.

**Detection:** Output schema regression test (`test_output_schema.py`) catches schema-level issues. Add content-level serialization assertions specifically for the parent wrapper.

---

### Pitfall 2: `model_rebuild()` Namespace Missing New Types

**What goes wrong:** `models/__init__.py` has an explicit `_ns` dict and `model_rebuild()` calls for forward reference resolution. When adding `ProjectRef`, `TaskRef`, `FolderRef`, and the parent wrapper model, forgetting to add them to `_ns` causes `PydanticUndefinedAnnotation` -- but only when the model is used for schema generation or validation, not at import time.

**Why it happens:** The namespace dict is manually maintained (15 entries currently). No automated check ensures all model types are present.

**Consequences:** Runtime crash on first tool call that touches the affected model. Tests constructing models directly (bypassing `__init__`) pass fine; integration tests fail.

**Prevention:**
- Add new types to `_ns` in the same commit that defines them.
- Add `model_rebuild()` calls for any new models with forward references.
- Remove `ParentRef` from `_ns`, `model_rebuild()`, and `__all__` when deleting it -- leftover references cause `ImportError`.
- Smoke check: `uv run python -c "from omnifocus_operator.models import Task; print(Task.model_json_schema())"` after model changes.

**Detection:** `test_output_schema.py` exercises full schema generation for all tools.

---

### Pitfall 3: Breaking Change Ordering -- Removing `inInbox` Before Adding `project`

**What goes wrong:** If `inInbox` is removed from the Task model before the `project` field is added and populated, there's a window where inbox status is undetectable in task output. Cross-path equivalence tests fail because the bridge path still emits `inInbox` but the model can't accept it.

**Why it happens:** Natural refactoring instinct: "remove the old thing, then add the new thing." But the old thing is load-bearing until the new thing replaces it.

**Consequences:** Broken intermediate state. Tests between phases are red. An agent reading task output has no way to determine if a task is in the inbox.

**Prevention:**
- Add `project` field FIRST (alongside `inInbox`), verify it works, THEN remove `inInbox`.
- Or do both in a single atomic change: add `project`, remove `inInbox`, update all mappers and tests simultaneously.
- Never ship a state where inbox status is unrepresented.

**Detection:** Cross-path equivalence tests fail if bridge path emits `inInbox` but model lacks it.

---

### Pitfall 4: Test Helper Cascade -- `make_model_task_dict` Hardcodes 26 Fields

**What goes wrong:** `make_model_task_dict()` in `tests/conftest.py` hardcodes `"inInbox": True` and `"parent": None`. After model changes:
- `inInbox` key must be removed
- `parent` must change from `None` to the tagged object format
- A new `project` key must be added

Every test using this factory without overriding these fields gets invalid data.

**Why it happens:** The factory centralizes defaults (good for consistency), but model changes have blast radius proportional to test suite size (1,528 tests).

**Consequences:** Mass test failures. The fix is mechanical but easy to get wrong -- the default parent/project values must be internally consistent (inbox task defaults need both `parent` and `project` pointing to `$inbox`).

**Prevention:**
- Update `make_model_task_dict()` atomically with the model change. Default inbox task: `"parent": {"project": {"id": "$inbox", "name": "Inbox"}}`, `"project": {"id": "$inbox", "name": "Inbox"}`, no `inInbox` key.
- Grep for `"inInbox"` across ALL test files -- tests constructing task dicts directly (not via factory) need updating.
- Grep for `"parent": None` in tests -- all need the new format.
- Update `make_model_project_dict`, `make_model_tag_dict`, `make_model_folder_dict` for rich reference changes simultaneously.

**Detection:** `uv run pytest` surfaces all failures immediately. No silent breakage -- this is loud and obvious.

---

## Moderate Pitfalls

---

### Pitfall 5: `$inbox` Leaking Through to Bridge Payloads

**What goes wrong:** `$inbox` is a service-layer concept. The OmniJS bridge has no concept of system locations -- it expects tasks with no parent to land in the inbox. If `$inbox` leaks into the bridge payload (e.g., `parent: "$inbox"` in the write command), the bridge tries to find a project with ID `$inbox` and fails.

**Why it happens:** The service layer should translate `$inbox` to "no parent" before building the bridge payload. If the resolution path misses a code path (add_tasks vs edit_tasks vs move actions), `$inbox` reaches the bridge.

**Consequences:** Bridge error: "Project not found: $inbox." Task creation/edit fails.

**Prevention:**
- PayloadBuilder must translate `$inbox` to `None`/omitted in the RepoPayload before repository.
- Test: `add_tasks` with `parent: "$inbox"` produces a bridge payload with no parent field.
- Test: `edit_tasks` with `ending: "$inbox"` produces correct inbox-targeting move command.
- Defense in depth: assert in bridge write mixin that no payload value starts with `$`.

---

### Pitfall 6: `PatchOrNone` Removal Leaves Dangling Imports

**What goes wrong:** `PatchOrNone` is used in `MoveAction` (lines 61-62 of `actions.py`). After changing `beginning`/`ending` to `Patch[str]`, the import becomes unused. If `PatchOrNone` is removed from `contracts/base.py` but some other file still imports it, that file breaks.

**Prevention:**
- Grep for `PatchOrNone` across the entire codebase before removing.
- Remove the import from `actions.py` in the same change that changes the field types.
- Remove from `contracts/base.py.__all__` in the same change.

**Detection:** `uv run ruff check` and `uv run mypy` catch unused imports and missing symbols.

---

### Pitfall 7: Rich References Break Golden Master Contract Tests

**What goes wrong:** Golden master fixtures contain captured RealBridge output with bare ID strings for `Project.folder`, `Project.next_task`, `Tag.parent`, `Folder.parent`. After changing these to `{id, name}` objects, the golden master validation fails because fixtures have the old format.

**Why it happens:** Golden master tests compare InMemoryBridge output against captured snapshots. Old snapshots with `"folder": "aBcDeFg"` won't validate against the new `FolderRef` type.

**Consequences:** All golden master tests fail (43 scenarios across 7 categories).

**Prevention:**
- Per GOLD-01: any phase modifying bridge operations must re-capture the golden master. Plan UAT re-capture as part of this milestone.
- Update `InMemoryBridge` to produce enriched references.
- Update bridge adapter (`adapter.py`) in the bridge-only path to emit `{id, name}` dicts instead of bare strings.
- Golden master re-capture is human-only (project feedback). Plan the UAT step explicitly in the phase.

---

### Pitfall 8: `before`/`after` Name Resolution Resolves to Wrong Entity Type

**What goes wrong:** `before` and `after` accept sibling **task** IDs only. If name resolution is added to these fields without scoping, `before: "Work"` where "Work" is a project name resolves to a project ID. The bridge then tries to position a task before a project -- nonsensical.

**Prevention:**
- Name resolution for `before`/`after` must search tasks only, not projects.
- Name resolution for `beginning`/`ending` must search containers (projects + task groups + `$inbox`).
- Separate resolver methods: `resolve_sibling_task(name)` vs `resolve_container(name)`.
- The improved error message ("before expects a sibling task, not a container") should fire AFTER name resolution, so if a name resolves to a project, the error is immediate and targeted.

---

### Pitfall 9: `list_tasks` Project Filter + `$inbox` -- Two SQL Code Paths

**What goes wrong:** The `project` filter currently resolves names to project IDs and passes to the SQL query builder. Adding `$inbox` support means a branch: `$inbox` -> use `inInbox = 1` SQL condition, real project -> use `containingProjectInfo = ?`. If branching happens in the query builder instead of the service, it violates "IDs-only at repo boundary."

**Prevention:**
- Handle `$inbox` in the service layer's filter resolution. When `project: "$inbox"` is detected, set `in_inbox: True` on the RepoQuery and clear the project filter. Don't pass `$inbox` as a project ID to the repo.
- Contradictory filter detection (`project: "$inbox"` + `inInbox: false`) belongs in service layer, before repo query construction.
- Cross-path equivalence tests must cover `project: "$inbox"`.

---

### Pitfall 10: Contradictory Filter Detection Scope Creep

**What goes wrong:** The spec defines one explicit contradiction (`project: "$inbox"` + `inInbox: false`) and one empty-set warning (`inInbox: true` + `project: "Work"`). But there are more potential contradictions: `availability: "completed"` with default exclusion active, or `project: "X"` + `inInbox: true` (which the spec addresses). If contradictory filter detection is implemented ad-hoc per combination, it becomes a maintenance burden.

**Prevention:**
- Implement the exact contradictions listed in the spec. Don't try to build a general-purpose contradiction engine.
- The `inInbox: true` + `project: "Work"` case returns results + warning (empty set), not an error. This is explicitly specified.
- `project: "$inbox"` + `inInbox: false` returns an error. This is explicitly specified.
- Don't add unspecified contradictions. If something feels contradictory but isn't in the spec, leave it as valid (AND composition with potentially empty results).

---

### Pitfall 11: Resolver Precedence -- Double Resolution of Already-Resolved IDs

**What goes wrong:** If name resolution is called on a value that was already resolved to an ID in a previous step, and that ID doesn't substring-match any entity name, the resolution fails with "no matches found" instead of treating it as a valid ID.

**Why it happens:** The three-step precedence handles this correctly IF step 2 (exact ID match) runs before step 3 (name match). But if a code path calls a resolver method that only does name matching (skipping the ID check), a valid ID fails.

**Prevention:**
- Every resolver entry point must implement the full three-step cascade: `$` prefix -> ID match -> name match.
- Never call a name-only resolver on user input. Always go through the full cascade.
- The existing `resolve_filter()` (line 135 of resolve.py) already does ID-then-name. New write-side resolution must follow the same pattern.

---

## Minor Pitfalls

---

### Pitfall 12: JSON Schema for Tagged Object Union -- Overly Permissive

**What goes wrong:** The tagged object wrapper (two optional fields, exactly one set) generates a JSON Schema where both fields are optional. Pydantic won't auto-generate `oneOf` or `minProperties: 1`. The schema allows `{}` (no fields set) and `{"project": {...}, "task": {...}}` (both set), even though the validator rejects these at runtime.

**Prevention:**
- Accept Pydantic's generated schema. The `@model_validator` enforces "exactly one" at runtime.
- Don't try to customize JSON Schema generation with schema overrides -- adds complexity for minimal benefit.
- Verify output schema test still validates serialized output against the generated schema.
- If agents construct invalid payloads (both fields or neither), the error message from the validator is the mitigation.

---

### Pitfall 13: `list_projects` Inbox Warning -- Substring Match Logic Duplication

**What goes wrong:** The spec says: if a name filter on `list_projects` would have matched "Inbox", emit a warning. This requires the same case-insensitive substring logic the resolver uses, applied against the constant "Inbox".

**Prevention:**
- Use the same substring matching helper the resolver uses. Don't rewrite the logic.
- The warning is only for `list_projects` with a name filter. No warning for other tools.
- The constant "Inbox" should come from `config.py` (alongside `$inbox` and `$` prefix).

---

### Pitfall 14: `ParentRef` Removal From Re-exports and Forward References

**What goes wrong:** `ParentRef` is exported from `models/__init__.py`, `models/common.py`, `__all__`, `_ns` namespace dict, and `model_rebuild()`. Removing it requires updating all sites. Leftover references cause `ImportError` at import time.

**Prevention:**
- Grep for `ParentRef` across entire codebase (src + tests + conftest).
- Remove from `_ns`, `model_rebuild()`, `__all__`, and all import statements atomically.
- The bridge adapter (`adapter.py`) has `_adapt_parent_ref()` function that builds `ParentRef` dicts -- this must be updated to build the new tagged object format.

---

### Pitfall 15: `get_project("$inbox")` Error vs Resolution

**What goes wrong:** If the resolver's `resolve_project()` method gains `$` prefix handling that returns a special inbox result, `get_project("$inbox")` might succeed with fabricated data instead of returning the specified error.

**Prevention:**
- The `$inbox` check in `get_project` should happen BEFORE the resolver is called. It's a tool-level guard, not a resolver concern.
- The error message is specified: "Inbox is a system location, not a project. Use `list_tasks` with `project: '$inbox'` or `inInbox: true`."
- The resolver's system location handling returns an ID, not a full entity. `get_project` needs the entity. So the guard is naturally at a different level.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Model changes (ProjectRef, TaskRef, FolderRef, parent wrapper) | P2 (model_rebuild namespace), P4 (test helper cascade), P14 (ParentRef removal) | Update `__init__.py` namespace, `make_model_task_dict`, and all import sites atomically |
| `$inbox` system location | P5 (bridge leakage), P9 (two SQL code paths) | Service layer translates `$inbox` before repo boundary; cross-path tests cover `$inbox` filter |
| Parent field tagged object | P1 (serialization with exclude_defaults), P12 (JSON Schema permissiveness) | No defaults on parent field; dedicated serialization test; accept Pydantic's permissive schema |
| Name resolution on writes | P8 (wrong entity type for before/after), P11 (double resolution) | Separate resolver methods per entity type; full three-step cascade on every entry point |
| Breaking changes (inInbox removal, PatchOrNone elimination) | P3 (ordering), P6 (dangling imports) | Add-before-remove ordering; grep for removed symbols before deleting |
| Rich references on output models | P7 (golden master breakage) | Plan UAT re-capture; update InMemoryBridge and bridge adapter simultaneously |
| Output schema regression | P1 (parent wrapper), P4 (test helpers) | Run `test_output_schema.py` after every model change; update test factories first |
| Filter changes (`project: "$inbox"`) | P9 (two code paths), P10 (contradictory filter scope) | Handle `$inbox` in service layer; implement only specified contradictions |
| `get_project("$inbox")` | P15 (error vs resolution) | Tool-level guard before resolver; error message from spec |

---

## Sources

- Codebase: `models/__init__.py` (model_rebuild pattern, 15-entry namespace dict), `contracts/base.py` (PatchOrNone definition), `models/repetition_rule.py` L193 (exclude_defaults lesson), `repository/hybrid/hybrid.py` (_build_parent_ref implementation), `tests/conftest.py` (make_model_task_dict with 26 hardcoded fields), `contracts/shared/actions.py` (MoveAction using PatchOrNone), `service/resolve.py` (existing resolver cascade)
- Milestone spec: `.research/updated-spec/MILESTONE-v1.3.1.md` (DL-12 tagged object rationale, DL-2 $ prefix rationale, all acceptance criteria)
- Project constraints: GOLD-01 (golden master re-capture), SAFE-01/02 (no automated RealBridge), project feedback (contracts are pure data, golden master human-only)
- Pydantic v2 behavior: `exclude_defaults=True` strips fields with default values (HIGH confidence -- verified in codebase via Frequency.type comment on L193)
