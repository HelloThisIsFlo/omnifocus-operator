# Phase 53: Response Shaping - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-14
**Phase:** 53-response-shaping
**Areas discussed:** Inherited rename strategy, Server package scope, Stripping implementation, Field group location, Stripping vs projection ordering, Write result stripping, include+only conflict, Stripping with only, get_* stripping, only field validation, limit: 0 layer, get_all and stripping, Response shaping application pattern, Tool description updates

---

## 1. effective* → inherited* Rename Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Full Python rename | Rename effective_* → inherited_* at model level. to_camel handles camelCase output. Touches every reference (tests, service, repo, mappers). | ✓ |
| Serialization alias only | Keep effective_* in Python, use Field(serialization_alias=...) for JSON output. Less churn but Python name doesn't match what agents see. | |

**User's choice:** Full Python rename
**Notes:** Clean rename, no naming disconnect. Pre-release so no migration concern.

---

## 2. server.py → server/ Package Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal split | server/__init__.py keeps handlers + lifespan. Add server/projection.py for new logic only. | |
| Moderate split | Split handlers, lifespan, and projection into separate files. __init__.py becomes just create_server(). | ✓ |
| Tool-type split | server/read_tools.py, server/write_tools.py, etc. Overkill for 11 tools. | |

**User's choice:** Moderate split
**Notes:** Clean file boundaries while keeping tool handlers together (they're cohesive).

---

## 3. Stripping Implementation Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Entity-level stripping | Strip each entity dict individually before assembling the response. Envelope fields structurally outside scope. | ✓ |
| Post-serialization dict walk | Strip entire response dict recursively with envelope field allowlist. | |

**User's choice:** Entity-level stripping
**Notes:** User confirmed during clarification. Projection layer extracts items from ListResult, strips each entity dict. Service returns ListResult with full models unchanged.

---

## 4. Field Group Definition Location

| Option | Description | Selected |
|--------|-------------|----------|
| config.py (per spec) | Centralized constants file. One place to look for all tunable definitions. | ✓ |
| server/projection.py | Co-located with only consumer. Definition near usage. | |

**User's choice:** config.py
**Notes:** User was 50-50. Argued: field groups are pure data (like SYSTEM_LOCATIONS), and "when I want to change it, I go to config." Projection.py is for understanding how groups get applied, not what they contain.

---

## 5. include + only Conflict Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Validation error (per spec) | Force agent to choose. Educational error message. | |
| Warning + only wins | Apply only, ignore include, add educational warning. Agent still gets results. | ✓ |

**User's choice:** Warning + only wins
**Notes:** **MILESTONE SPEC CHANGE.** User's argument: error wastes a full round trip. Warning teaches equally well but agent still gets results. The warning is not silent — it explicitly says include was ignored because only was provided. Cheaper failure mode: warning costs a few redundant tokens, error costs a whole round trip. Consistent with existing ["all", "available"] → warning pattern.

---

## 6. Stripping with only (explicitly-requested fields)

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, strip everywhere | Stripping is universal, no exceptions. Agent knows its field list — absence is unambiguous. | ✓ |
| No, keep nulls with only | Explicitly-requested fields show null rather than being omitted. Consistent shape. | |

**User's choice:** Strip everywhere
**Notes:** User agreed. Wants `only` field description to make clear: (1) takes precedence over include, (2) stripping still applies.

---

## 7. get_* Stripping

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, strip on get_* | Universal stripping, no exceptions. Reduces noise from ~25 fields to ~10-15 meaningful ones. | ✓ |
| No, full entity on get_* | Show everything including nulls for detailed inspection. | |

**User's choice:** Strip on get_*
**Notes:** User initially hesitated — worried about discoverability of inherited fields. Self-resolved: tool descriptions document available fields, so agents know what could be there. If inherited_due_date is absent, it means no inherited due date.

---

## 8. Write Result Stripping

No formal question — emerged during discussion.

**User's choice:** No stripping on write results
**Notes:** Only entity types (Task, Project, Tag, Folder, Perspective) go through stripping. Write results (AddTaskResult, EditTaskResult) returned as-is. User confirmed: "just to make everything consistent, we only strip task, project, tag, folder."

---

## 9. only Field Validation Source

| Option | Description | Selected |
|--------|-------------|----------|
| Derive from field groups | Valid fields = union of all groups. Already defined in config.py. No drift risk. | ✓ |
| Explicit constant per entity | TASK_ALL_FIELDS = {...} in config.py. Manual sync required. | |
| Introspect Pydantic model | Task.model_fields at startup. Always in sync but couples projection to model. | |

**User's choice:** Derive from field groups
**Notes:** User added: "we should have a test that inspects the model to make sure all model fields are included in exactly one field group." Bidirectional enforcement test guarantees groups and model fields stay in sync.

---

## 10. limit: 0 Implementation Layer

No formal question — analyzed and presented.

**User's choice:** Pass through naturally
**Notes:** No ge=1 constraint exists on limit. SQL LIMIT 0 is valid. Count query still runs. No special-casing needed at any layer.

---

## 11. Response Shaping Application Pattern (get_all + general)

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit per handler | Each handler calls strip/project functions directly. Visible, debuggable. | ✓ |
| Stripping middleware | Middleware intercepts all results, detects entity types, strips automatically. | |

**User's choice:** Explicit per handler
**Notes:** User initially excited about middleware ("I really like the idea!"). After discussing the sequencing problem (middleware doesn't have include/only params) and detection problem (middleware needs to know which tools return entities), settled on explicit per handler. Different tools clearly apply different transforms.

---

## 12. Tool Description Updates

| Option | Description | Selected |
|--------|-------------|----------|
| Brief tip in tool desc, detail in Field descriptions | Tool descriptions get 1-2 lines. JSON Schema Field descriptions carry full detail. | ✓ |
| Full detail in tool description | List all fields, groups, behavior in tool description. Longer but all in one place. | |

**User's choice:** Brief tip in tool desc, detail in Field descriptions
**Notes:** Follows existing pattern — tool descriptions scannable, Field-level docs carry precision.

---

## 13. Description Text Refinements (follow-up discussion)

No formal question — extended discussion with iterative feedback on proposed description text.

**Decisions made:**

1. **Separate include types per tool** — `TaskFieldGroup` and `ProjectFieldGroup` as separate Literal types. Projects have `"review"`, tasks don't. Two separate query model fields, not a shared type. The Field description is shared (one constant).

2. **`include` in tool description, `only` in Field description only** — `include` is complex (groups, contents) and benefits from being in the tool description alongside group listings. `only` is straightforward — Field description suffices. Same pattern as repetition rule examples in edit_tasks tool description vs simpler fields.

3. **`INCLUDE_FIELD_DESC`** — succinct: "Add field groups to the response, on top of defaults. See tool description for available groups."

4. **`ONLY_FIELD_DESC`** — refined wording:
   - Removed camelCase mention (agents always see camelCase, never tempted to use Python names)
   - Changed "takes precedence" to "mutually exclusive with include"
   - Reworded use case: "Use case: targeted high-volume queries (prefer include for most use cases)."
   - Kept stripping note, removed "absent field means not set" (already in tool description)

5. **`INHERITED_FIELD_DESC`** — one shared constant for all 6 fields. Uses "entity" everywhere (not "task" for some).

6. **`LIMIT_DESC`** — "Tip: pass 0 for count only" framing.

7. **Case-insensitive matching on `only`** — do it for resilience, don't document to agents.

8. **Reusable fragments** — use `_STRIPPING_NOTE`, `_DATE_INPUT_NOTE`, and other fragments wherever there's reuse opportunity. Extract aggressively — easier to maintain.

9. **Draft tool descriptions** — user provided full drafts for `list_tasks` and `list_projects` descriptions. These are the target output structure (groups as one-liners, defaults listed, count-only tip, inherited explanation, etc.).

---

## Claude's Discretion

- Exact stripping function implementation (recursive dict walk vs key-by-key)
- Whether strip_entity and shape_list_response are separate functions or composed
- Test organization for stripping/projection
- Exact wording of `get_*` tool descriptions (update effective* → inherited*, add stripping note)
- Fragment extraction opportunities beyond `_STRIPPING_NOTE`

## Deferred Ideas

None — discussion stayed within phase scope.
