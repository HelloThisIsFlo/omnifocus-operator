# Phase 53: Response Shaping - Research

**Researched:** 2026-04-14
**Domain:** Server-layer response transformation (stripping, renaming, projection)
**Confidence:** HIGH

## Summary

Phase 53 delivers four response-shaping features as one coherent layer: universal stripping (null/empty/falsy removal), inherited field rename (`effective*` -> `inherited*`), field selection (`include`/`only`), and count-only mode (`limit: 0`). All of this ships in a new `server/` package, with `server/projection.py` owning the transformation logic. The service layer is untouched -- it continues returning full Pydantic models.

The rename is a mechanical codebase-wide find-and-replace affecting models, mappers, service, tests, golden master JSON, and description constants. The stripping and projection are new code, localized to `server/projection.py`. The `include`/`only` parameters are added to `ListTasksQuery` and `ListProjectsQuery` contracts. Count-only mode requires no code changes -- `limit: 0` already passes through naturally.

**Primary recommendation:** Sequence as rename-first (unblocks everything), then server restructure, then stripping/projection, then field selection contracts and wiring, then description updates. The rename touches the most files but is entirely mechanical.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Full Python rename `effective_*` -> `inherited_*` at model level. `to_camel` alias generator produces `inheritedDueDate` etc. automatically. No serialization alias tricks.
- **D-02:** Moderate split: `server.py` -> `server/` package with `__init__.py`, `handlers.py`, `lifespan.py`, `projection.py`.
- **D-03:** Entity-level stripping after serialization. Stripped values: `null`, `[]`, `""`, `false`, `"none"`. Never stripped: `availability`. No stripping on write results.
- **D-04:** Field group definitions in `config.py`. Groups: `notes`, `metadata`, `hierarchy`, `time`, `review` (projects only), `*`.
- **D-04b:** Separate `include` Literal types per tool -- `TaskFieldGroup` and `ProjectFieldGroup`.
- **D-05:** Valid `only` field names = union of all field groups. Enforcement test for bidirectional sync. Invalid `only` -> warning. Invalid `include` -> validation error with educational message. Case-insensitive `only` matching.
- **D-06:** `include` + `only` conflict -> warning with `only` taking precedence (overrides original spec "validation error").
- **D-07:** Strip then project. Clean entity first, then select fields.
- **D-08:** `limit: 0` passes through naturally. No special-casing. Update `LIMIT_DESC`.
- **D-09:** Explicit per handler, not middleware. Different tools apply different transforms.
- **D-10:** `include` groups documented in tool description. `only` documented in Field description only.
- **D-11:** Verbatim description text agreed for `INCLUDE_FIELD_DESC`, `ONLY_FIELD_DESC`, `INHERITED_FIELD_DESC`, `LIMIT_DESC`, `_STRIPPING_NOTE`.
- **D-11b:** Draft tool descriptions for `list_tasks` and `list_projects` exist in CONTEXT.md specifics section.

### Claude's Discretion
- Exact stripping function implementation (recursive dict walk, or key-by-key check)
- Whether `strip_entity` and `shape_list_response` are separate functions or composed from primitives
- Test organization for stripping/projection (unit tests on functions vs integration tests through tools)
- Exact wording of `get_*` tool descriptions (follow existing `descriptions.py` patterns, update `effective*` -> `inherited*`)
- Fragment extraction opportunities beyond `_STRIPPING_NOTE`

### Deferred Ideas (OUT OF SCOPE)
- Batch processing response shape (Phase 54)
- Notes graduation (Phase 55)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STRIP-01 | All tool responses strip null, [], "", false, "none" from entity fields | D-03: entity-level stripping in `server/projection.py`. Strip after `model_dump(by_alias=True)`. Values to strip: `None`, `[]`, `""`, `False`, `"none"` |
| STRIP-02 | availability field never stripped | D-03: explicit exception in strip function. `availability` key excluded from strip logic |
| STRIP-03 | Result envelope fields (hasMore, total, status) never stripped | D-03: stripping applies to entity dicts only, not envelope. Envelope fields are structurally separate |
| RENAME-01 | effective* fields renamed to inherited* across all tools (6 fields) | D-01: Python-level rename on `ActionableEntity` and `Task`. `to_camel` alias generator auto-produces `inheritedDueDate` etc. Mechanical find-replace across ~226 files |
| FSEL-01 | Agent can use `include` on list_tasks/list_projects to add groups to defaults | D-04/D-04b: new `include` parameter on query models. `TaskFieldGroup` and `ProjectFieldGroup` Literal types |
| FSEL-02 | Default fields defined per entity type | D-04: default field sets in `config.py`. Task defaults: id, name, availability, order, project, dueDate, inheritedDueDate, deferDate, inheritedDeferDate, plannedDate, inheritedPlannedDate, flagged, inheritedFlagged, urgency, tags. Projects additionally: folder |
| FSEL-03 | Available groups: notes, metadata, hierarchy, time, * (tasks); +review (projects) | D-04/D-04b: separate Literal types enforce this |
| FSEL-04 | Invalid include group names -> validation error | D-05: `@field_validator` on `include` field with educational error message |
| FSEL-05 | Agent can use `only` for individual field selection (id always included) | D-05: `only` parameter on query models. Projection adds `id` unconditionally |
| FSEL-06 | include and only mutually exclusive -> providing both produces warning (D-06 override) | D-06: warning with `only` taking precedence, not validation error |
| FSEL-07 | Invalid only field names -> warning in response | D-05: case-insensitive matching, unrecognized names added to warnings list |
| FSEL-08 | include: ["*"] returns all fields | D-04: `*` group means union of all groups |
| FSEL-09 | get_task/project/tag/get_all return full stripped entities (no field selection) | D-09: get_* tools call `strip_entity()`, no projection |
| FSEL-10 | Group definitions centralized in config.py | D-04: pure data constants in `config.py` |
| FSEL-11 | Projection is post-filter, pre-serialization | D-07/D-12: service returns full models, server strips then projects |
| FSEL-12 | Service layer returns full Pydantic models; projection is server-layer concern | D-09/D-12: explicit per-handler calls in `server/handlers.py` |
| FSEL-13 | server.py becomes server/ package | D-02: `server/__init__.py`, `handlers.py`, `lifespan.py`, `projection.py` |
| COUNT-01 | limit: 0 returns count-only {items: [], total: N, hasMore: total > 0} | D-08: already valid -- no `ge=1` constraint on `limit`. Update `LIMIT_DESC` constant |
</phase_requirements>

## Standard Stack

No new dependencies. This phase is pure refactoring and feature additions within existing stack.

### Core (already in project)
| Library | Version | Purpose | Note |
|---------|---------|---------|------|
| pydantic | 2.x (project dep) | Model validation, serialization | `model_dump(by_alias=True)` for camelCase output |
| fastmcp | project dep | MCP server framework | Tool registration, middleware |
| pydantic-settings | project dep | Settings management | `config.py` constants |

No `npm install` or `pip install` needed. [VERIFIED: existing pyproject.toml]

## Architecture Patterns

### Server Package Structure (D-02)
```
src/omnifocus_operator/server/
    __init__.py          # create_server() + exports
    handlers.py          # all 11 tool handlers (moved from server.py)
    lifespan.py          # app_lifespan context manager
    projection.py        # strip_entity(), shape_list_response(), etc.
```

### Pattern 1: Entity Stripping
**What:** Post-serialization removal of null/empty/falsy values from entity dicts
**When:** Every read tool response (get_*, list_*, get_all)
**Pipeline:** `Pydantic model` -> `model_dump(by_alias=True)` -> `strip_entity(dict)` -> returned to agent
```python
# server/projection.py
NEVER_STRIP = {"availability"}
STRIP_VALUES = {None, [], "", False, "none"}

def strip_entity(entity: dict[str, Any]) -> dict[str, Any]:
    return {
        k: v for k, v in entity.items()
        if k in NEVER_STRIP or v not in STRIP_VALUES
    }
```
[ASSUMED — implementation detail, D-03 is locked but exact code is Claude's discretion]

### Pattern 2: Field Projection (include/only)
**What:** After stripping, select only requested fields from entity dicts
**When:** `list_tasks` and `list_projects` only
**Pipeline:** `strip_entity(dict)` -> `project_fields(dict, include, only)` -> returned
```python
def shape_list_response(
    result: ListResult[T],
    include: list[str] | None,
    only: list[str] | None,
    entity_type: str,  # "task" or "project"
) -> dict[str, Any]:
    # 1. Serialize items
    # 2. Strip each entity
    # 3. Project fields (if include or only specified)
    # 4. Reassemble envelope
    ...
```
[ASSUMED — implementation detail, Claude's discretion]

### Pattern 3: Per-Handler Shaping (D-09)
**What:** Each tool handler explicitly calls the appropriate shaping function
**Why:** Different tools need different transforms -- no one-size-fits-all middleware

| Tool | Shaping |
|------|---------|
| `get_task`, `get_project`, `get_tag` | `strip_entity()` |
| `get_all` | `strip_all_entities()` (strip each entity in each collection) |
| `list_tasks`, `list_projects` | `shape_list_response()` (strip + project + envelope) |
| `list_tags`, `list_folders`, `list_perspectives` | strip items only (no field selection) |
| `add_tasks`, `edit_tasks` | return as-is (no shaping) |

### Pattern 4: Inherited Field Rename (D-01)
**What:** Full Python rename at model level, alias generator handles camelCase automatically
**Scope:** `ActionableEntity.effective_*` -> `inherited_*` (5 fields), `Task.effective_completion_date` -> `inherited_completion_date` (1 field)
**Fields:**
- `effective_flagged` -> `inherited_flagged`
- `effective_due_date` -> `inherited_due_date`
- `effective_defer_date` -> `inherited_defer_date`
- `effective_planned_date` -> `inherited_planned_date`
- `effective_drop_date` -> `inherited_drop_date`
- `effective_completion_date` -> `inherited_completion_date` (Task-only)

### Anti-Patterns to Avoid
- **Middleware for projection:** D-09 explicitly chose per-handler over middleware. Different tools have different shaping needs. Don't try to unify into a single middleware.
- **Stripping write results:** D-03 says no stripping on `AddTaskResult`/`EditTaskResult`. These are result envelopes, not entities.
- **Projection in service layer:** D-09/FSEL-12 says service returns full models. Projection is a server-layer presentation concern.
- **Alias-based rename:** D-01 chose full Python rename, not serialization aliases. The `to_camel` alias generator on `OmniFocusBaseModel` handles the camelCase output automatically.

## Rename Scope Inventory

### Source Files (7 files)
| File | What Changes |
|------|-------------|
| `models/common.py` (ActionableEntity) | 5 field names: `effective_flagged`, `effective_due_date`, `effective_defer_date`, `effective_planned_date`, `effective_drop_date` |
| `models/task.py` | 1 field: `effective_completion_date` |
| `agent_messages/descriptions.py` | 6 constants: `EFFECTIVE_FLAGGED` -> `INHERITED_FLAGGED`, etc. |
| `repository/hybrid/hybrid.py` | ~12 occurrences in mapper dicts |
| `repository/bridge_only/bridge_only.py` | ~7 occurrences in field maps and filter logic |
| `service/domain.py` | References to `effective_dates` dict (local variable, NOT the model field -- may keep name) |
| `service/service.py` | References to `effective_dates` dict (local variable) |

### Test Files (11 files, ~157 occurrences of `effective_`)
| File | Occurrences | Nature |
|------|-------------|--------|
| `tests/conftest.py` | ~31 | Factory dicts (`effectiveFlagged`, `effectiveDueDate`, etc.) |
| `tests/doubles/bridge.py` | ~16-19 | InMemoryBridge internal state |
| `tests/test_cross_path_equivalence.py` | ~100+15 | Heavy assertion on field names |
| `tests/test_hybrid_repository.py` | ~15+13 | Mapper output assertions |
| `tests/test_models.py` | ~12+3 | Model field assertions |
| `tests/test_service.py` | ~7+2 | Service pipeline output |
| `tests/test_list_pipelines.py` | ~1+49 | Query field mappings |
| `tests/test_server.py` | ~2+3 | Integration assertions |
| `tests/test_adapter.py` | ~13 | Bridge adapter mappings |
| `tests/test_stateful_bridge.py` | ~1 | Bridge output |
| `tests/test_query_builder.py` | ~9 | SQL column references |

### Golden Master JSON (all snapshots)
- ~21,665 total occurrences of `effective*` camelCase keys across all JSON snapshot files
- These are bridge-format golden master data -- they use `effectiveFlagged`, `effectiveDueDate`, etc.
- **Critical insight:** Golden master snapshots are captured from the real Bridge (raw bridge format). The `effective*` keys in JSON are the **bridge output** format, not the model field names. The bridge.js script produces `effectiveFlagged` etc.
- **Decision needed:** Golden master JSON files use **bridge format** (pre-adapter). The adapter transforms bridge output into model format. If the adapter now maps `effectiveFlagged` -> `inherited_flagged` instead of `effective_flagged`, the golden master JSON keys themselves do NOT change -- only the adapter mapping target changes.
- `normalize.py` PRESENCE_CHECK fields reference `effectiveCompletionDate`, `effectiveDropDate` -- these are bridge-format keys and do NOT change.

[VERIFIED: read golden_master/normalize.py and snapshot JSON files]

### Other Files
- `bridge/bridge.js` -- OmniJS bridge script outputs `effectiveFlagged`, `effectiveDueDate`, etc. These are OmniFocus API field names and do NOT change.
- `docs/` -- architecture docs reference `effective*` in prose. Update to `inherited*`.
- `simulator/data.py` -- fixture data with `effectiveFlagged` etc. (bridge format, adapter handles).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| camelCase aliases | Manual alias mapping | `to_camel` alias generator (already on `OmniFocusBaseModel`) | Automatic from Python `inherited_due_date` -> `inheritedDueDate` |
| Field validation for `include` | Custom parsing | Pydantic `Literal` type + `@field_validator` | Pydantic rejects invalid Literal values automatically; custom validator adds educational message |
| Dict serialization | Manual field-by-field serialization | `model_dump(by_alias=True)` | Standard Pydantic serialization path, already used throughout |

## Common Pitfalls

### Pitfall 1: Golden Master Bridge-Format vs Model-Format Confusion
**What goes wrong:** Renaming `effective*` in golden master JSON files when they use bridge format (pre-adapter)
**Why it happens:** Golden master snapshots capture raw Bridge output. The adapter transforms bridge -> model. The bridge.js script uses OmniFocus API field names (`effectiveFlagged`).
**How to avoid:** Only rename in adapter targets (Python side), not in bridge-format JSON or bridge.js. Golden master JSON keys stay as `effectiveFlagged` etc.
**Warning signs:** Test failures in golden master comparison tests after changing JSON files

### Pitfall 2: Test Factory camelCase Keys
**What goes wrong:** Forgetting to rename camelCase keys in `conftest.py` factories
**Why it happens:** `make_model_task_dict()` uses camelCase keys matching the alias output: `effectiveFlagged`. After rename, the model field is `inherited_flagged`, and `to_camel` produces `inheritedFlagged`. So `make_model_task_dict()` keys must change to `inheritedFlagged`.
**How to avoid:** Rename all `effective*` keys in `make_model_*` factories (model-format). Bridge-format factories (`make_task_dict()`) keep `effective*` keys.
**Warning signs:** Pydantic validation errors in tests -- unrecognized field `effectiveFlagged`

### Pitfall 3: `model_dump` vs Dict-in-Handler Return Type
**What goes wrong:** Server handlers currently return Pydantic models. After adding stripping, they must return dicts. FastMCP may serialize differently.
**Why it happens:** FastMCP uses `pydantic_core.to_jsonable_python(value)` for serialization. When the handler returns a Pydantic model, FastMCP serializes it using the model's schema. When returning a dict, it serializes as plain JSON.
**How to avoid:** Test that dict returns produce the same wire format as model returns (minus stripped fields). The `test_output_schema.py` tests validate against outputSchema -- ensure they still pass.
**Warning signs:** `test_output_schema.py` failures, client-side schema validation errors

### Pitfall 4: `outputSchema` Drift After Projection
**What goes wrong:** MCP clients may validate response against `outputSchema`. After projection, some fields are missing, which could fail validation.
**Why it happens:** FastMCP advertises `outputSchema` based on the return type annotation. If the handler declares `-> ListResult[Task]` but returns a stripped/projected dict, the schema and data diverge.
**How to avoid:** This is explicitly accepted per D-09 context: "MCP clients strip outputSchema anyway; available fields documented in tool description." Return `dict[str, Any]` from handlers after shaping, not typed models. Update return type annotations accordingly. OR use `content=[]` TextContent approach to bypass outputSchema entirely.
**Warning signs:** Claude Desktop showing schema validation errors for stripped fields

### Pitfall 5: Description Byte Limit (2048 bytes)
**What goes wrong:** Updated tool descriptions exceed Claude Code's 2048-byte limit and get silently truncated
**Why it happens:** Adding `include` group documentation, stripping note, and inherited field explanation to tool descriptions
**How to avoid:** Existing `test_tool_descriptions_within_client_byte_limit` test in `test_descriptions.py` catches this. Run after every description change.
**Warning signs:** Test failure in `TestToolDescriptionEnforcement`

### Pitfall 6: Service Layer `effective_` Local Variables
**What goes wrong:** Renaming local variables that happen to use `effective_` prefix but aren't model fields
**Why it happens:** `service.py` has `effective_dates = {...}` and `effective_type = ...` which are local variables, not model field references
**How to avoid:** Only rename model field references (`.effective_flagged`, `["effective_due_date"]`). Leave local variable names that use `effective_` as a generic English word.
**Warning signs:** Unnecessary changes to service internals that don't relate to the model rename

### Pitfall 7: AST Enforcement Test for server.py Path
**What goes wrong:** `test_descriptions.py` hardcodes `_SERVER_PATH = _SRC_ROOT / "server.py"`. After restructure to `server/`, this path is wrong.
**Why it happens:** The AST test scans `server.py` for `@mcp.tool()` decorators. After restructure, tools are in `server/handlers.py`.
**How to avoid:** Update `_SERVER_PATH` to point to `server/handlers.py`. Also update `_CONSUMER_MODULES` list to import from the new location.
**Warning signs:** `TestToolDescriptionEnforcement` tests fail or skip silently

## Code Examples

### Current model_dump output (camelCase aliases)
```python
# Source: verified via live python execution
task.model_dump(by_alias=True)
# Keys: id, name, url, added, modified, urgency, availability, note,
#   flagged, effectiveFlagged, dueDate, deferDate, plannedDate,
#   completionDate, dropDate, effectiveDueDate, effectiveDeferDate,
#   effectivePlannedDate, effectiveDropDate, estimatedMinutes,
#   hasChildren, tags, repetitionRule, order, effectiveCompletionDate,
#   parent, project
```
[VERIFIED: ran `model_dump(by_alias=True)` on Task instance]

### After rename, aliases auto-generate
```python
# After rename: effective_flagged -> inherited_flagged
# to_camel("inherited_flagged") -> "inheritedFlagged" (automatic)
# No alias configuration needed
```
[VERIFIED: `to_camel` alias generator behavior from `pydantic.alias_generators`]

### Stripping example
```python
# Input (after model_dump):
{"id": "t1", "name": "Buy milk", "availability": "available",
 "flagged": False, "inheritedFlagged": False,
 "dueDate": None, "deferDate": None, "tags": [],
 "note": "", "urgency": "none", "hasChildren": False, ...}

# After strip_entity():
{"id": "t1", "name": "Buy milk", "availability": "available"}
# flagged=False, tags=[], note="", urgency="none", dueDate=None all stripped
# availability kept (never stripped)
```

### Projection example
```python
# Default fields (no include, no only):
{"id": "t1", "name": "Buy milk", "availability": "available",
 "dueDate": "2026-04-15T17:00:00Z", "project": {"id": "p1", "name": "Shopping"}}

# include: ["notes"]  -> adds note group to defaults
{"id": "t1", "name": "Buy milk", "availability": "available",
 "dueDate": "2026-04-15T17:00:00Z", "project": {"id": "p1", "name": "Shopping"},
 "note": "Check prices first"}

# only: ["project", "dueDate"]  -> exactly those fields + id
{"id": "t1", "project": {"id": "p1", "name": "Shopping"},
 "dueDate": "2026-04-15T17:00:00Z"}
```

## Field Group Definitions (for config.py)

Based on D-04, D-04b, and the draft tool descriptions:

### Task Fields
```python
TASK_DEFAULT_FIELDS = {
    "id", "name", "availability", "order", "project",
    "dueDate", "inheritedDueDate", "deferDate", "inheritedDeferDate",
    "plannedDate", "inheritedPlannedDate",
    "flagged", "inheritedFlagged", "urgency", "tags",
}

TASK_FIELD_GROUPS = {
    "notes": {"note"},
    "metadata": {"added", "modified", "completionDate", "dropDate",
                 "inheritedCompletionDate", "inheritedDropDate", "url"},
    "hierarchy": {"parent", "hasChildren"},
    "time": {"estimatedMinutes", "repetitionRule"},
}
```

### Project Fields
```python
PROJECT_DEFAULT_FIELDS = TASK_DEFAULT_FIELDS | {"folder"} - {"order", "project"}
# Projects don't have order or project (they ARE projects)
# Projects additionally have folder in defaults

PROJECT_FIELD_GROUPS = {
    **TASK_FIELD_GROUPS,
    "review": {"nextReviewDate", "reviewInterval", "lastReviewDate", "nextTask"},
}
```

**Note:** Field names in group definitions use **camelCase** (alias names) because they operate on `model_dump(by_alias=True)` output dicts. [VERIFIED: model_dump produces camelCase keys]

**Important detail:** Task has `order` and `project` in defaults. Project has `folder` in defaults but NOT `order` (projects don't have order) and NOT `project` (self-referential). The exact default sets must be verified against the draft tool descriptions in CONTEXT.md.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `effective*` field names | `inherited*` field names | This phase | Clearer semantics for agents |
| Full entity payloads | Stripped + projected | This phase | Token savings, agent control |
| Single `server.py` module | `server/` package | This phase | Separation of concerns |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (via `uv run pytest`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STRIP-01 | Entity fields stripped of null/[]/""/ false/"none" | unit | `uv run pytest tests/test_projection.py::TestStripping -x` | Wave 0 |
| STRIP-02 | availability never stripped | unit | `uv run pytest tests/test_projection.py::TestStripping::test_availability_never_stripped -x` | Wave 0 |
| STRIP-03 | Envelope fields never stripped | unit | `uv run pytest tests/test_projection.py::TestStripping::test_envelope_fields_preserved -x` | Wave 0 |
| RENAME-01 | effective* -> inherited* in all output | integration | `uv run pytest tests/test_models.py tests/test_server.py -x -q` | Existing (update) |
| FSEL-01 | include adds groups to defaults | unit | `uv run pytest tests/test_projection.py::TestFieldSelection -x` | Wave 0 |
| FSEL-02 | Default fields correct per entity | unit | `uv run pytest tests/test_projection.py::TestFieldSelection::test_default_fields -x` | Wave 0 |
| FSEL-03 | Available groups per tool | unit | `uv run pytest tests/test_projection.py::TestFieldSelection::test_include_groups -x` | Wave 0 |
| FSEL-04 | Invalid include -> validation error | unit | `uv run pytest tests/test_list_contracts.py -x -q -k include` | Wave 0 |
| FSEL-05 | only returns exact fields + id | unit | `uv run pytest tests/test_projection.py::TestFieldSelection::test_only -x` | Wave 0 |
| FSEL-06 | include+only -> warning, only wins | unit | `uv run pytest tests/test_projection.py::TestFieldSelection::test_include_only_conflict -x` | Wave 0 |
| FSEL-07 | Invalid only -> warning | unit | `uv run pytest tests/test_projection.py::TestFieldSelection::test_invalid_only_warning -x` | Wave 0 |
| FSEL-08 | include: ["*"] returns all | unit | `uv run pytest tests/test_projection.py::TestFieldSelection::test_include_star -x` | Wave 0 |
| FSEL-09 | get_* returns full stripped entities | integration | `uv run pytest tests/test_server.py -x -q -k "get_task or get_project"` | Existing (update) |
| FSEL-10 | Groups in config.py | structural | `uv run pytest tests/test_projection.py::TestFieldGroupSync -x` | Wave 0 |
| FSEL-11 | Projection is post-filter | integration | `uv run pytest tests/test_server.py -x -q -k list_tasks` | Existing (update) |
| FSEL-12 | Service returns full models | architecture | Verified by existing service tests (no changes to service) | Existing |
| FSEL-13 | server/ package structure | structural | `uv run pytest tests/test_server.py -x -q` (imports from new location) | Existing (update) |
| COUNT-01 | limit: 0 -> count-only | integration | `uv run pytest tests/test_server.py -x -q -k "limit_0 or count_only"` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_projection.py` -- covers STRIP-01, STRIP-02, STRIP-03, FSEL-01 through FSEL-08, FSEL-10
- [ ] Enforcement test for field group <-> model field bidirectional sync (FSEL-10)
- [ ] `include`/`only` contract validation tests in `test_list_contracts.py` (FSEL-04, FSEL-06, FSEL-07)
- [ ] Count-only mode integration test (COUNT-01)

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | FastMCP handles dict returns from handlers the same as model returns (just without schema validation) | Pitfall 3 | Handlers may need TextContent wrapping instead of raw dict returns |
| A2 | `model_dump(by_alias=True)` produces all camelCase keys needed for field group matching | Field Group Definitions | Group field names may need to match Python names instead of aliases |
| A3 | Golden master JSON snapshots use bridge format and don't need `effective` -> `inherited` rename | Pitfall 1 | If golden master uses model format, all JSON files need updating |
| A4 | Service-layer local variables named `effective_*` don't need renaming | Pitfall 6 | Over-renaming could break service internals |
| A5 | `test_output_schema.py` will need handler return type annotation updates but not fundamental changes | Pitfall 4 | Schema tests may need significant rework if handlers change return types |

## Open Questions

1. **Handler return type after shaping**
   - What we know: Currently handlers return typed models (`-> Task`, `-> ListResult[Task]`). After shaping, they return dicts.
   - What's unclear: How FastMCP handles `-> dict[str, Any]` return types vs typed models. Does it still generate useful outputSchema?
   - Recommendation: Test with one handler first. If FastMCP can't generate schema from dict return, either (a) keep model return type and let FastMCP serialize, then post-process, or (b) return TextContent with JSON string.

2. **Bridge-format factories vs model-format factories**
   - What we know: `conftest.py` has both `make_task_dict()` (bridge format) and `make_model_task_dict()` (model format). Bridge format uses OmniFocus API field names (`effectiveFlagged`).
   - What's unclear: Whether bridge-format factories need renaming or only model-format ones.
   - Recommendation: Only model-format factories need renaming (`make_model_task_dict` keys change from `effectiveFlagged` -> `inheritedFlagged`). Bridge-format factories stay unchanged (they match bridge.js output).

3. **Description byte budget**
   - What we know: Tool descriptions have a 2048-byte limit. Current `LIST_TASKS_TOOL_DOC` is ~1200 bytes. The draft description in CONTEXT.md is significantly longer.
   - What's unclear: Whether the draft description fits within 2048 bytes.
   - Recommendation: Measure draft description byte count early. If over limit, use reusable fragments and compress.

## Project Constraints (from CLAUDE.md)

- **SAFE-01/02:** All tests use `InMemoryBridge` or `SimulatorBridge`. No automated tests touch the real Bridge.
- **Model conventions:** Before creating new models, read `docs/model-taxonomy.md`. After modifying models in tool output, run `uv run pytest tests/test_output_schema.py -x -q`.
- **Service layer convention:** Method Object pattern for use cases. Read delegations stay inline.
- **Description enforcement:** All agent-facing text in `descriptions.py`. AST enforcement tests catch inline strings.
- **Contracts are pure data:** No `model_serializer` or transformation logic in contracts/.

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `server.py`, `config.py`, `models/common.py`, `models/task.py`, `models/project.py`
- Codebase inspection: `agent_messages/descriptions.py`, `middleware.py`, `contracts/use_cases/list/`
- Codebase inspection: `tests/conftest.py`, `tests/test_output_schema.py`, `tests/test_descriptions.py`
- Codebase inspection: `tests/golden_master/normalize.py`, golden master JSON snapshots
- Live Python execution: `model_dump(by_alias=True)` output verification
- Live test count: 2041 tests collected

### Secondary (MEDIUM confidence)
- Field count verification via grep: ~157 occurrences of `effective_` in test files, ~21,665 camelCase occurrences across project

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, pure internal changes
- Architecture: HIGH -- all patterns locked in CONTEXT.md decisions
- Pitfalls: HIGH -- verified through codebase inspection, golden master analysis
- Rename scope: HIGH -- comprehensive grep analysis of all occurrences

**Research date:** 2026-04-14
**Valid until:** 2026-05-14 (stable internal patterns)
