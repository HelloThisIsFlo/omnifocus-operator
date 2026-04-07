# Phase 39: Foundation -- Constants & Reference Models - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Define system location constants (`$inbox`) and new typed reference models (`ProjectRef`, `TaskRef`, `FolderRef`) that all subsequent phases in v1.3.1 import. Zero-impact phase: no existing code is modified, no existing behavior changes.

</domain>

<decisions>
## Implementation Decisions

### System Location Constants
- **D-01:** Plain string constants in `config.py`, not a StrEnum or structured type
- **D-02:** Verbose naming matching existing config.py style:
  ```python
  # -- System locations ----------------------------------------------------------
  SYSTEM_LOCATION_PREFIX: str = "$"
  SYSTEM_LOCATION_INBOX: str = "$inbox"
  INBOX_DISPLAY_NAME: str = "Inbox"
  ```
- **D-03:** Phase 39 only *defines* these constants. No existing inbox logic (`in_inbox`, `inInbox` checks) is updated. Phases 40 and 42 MUST import from config.py rather than hardcoding `"$inbox"` or `"Inbox"`

### Reference Model Structure
- **D-04:** `ProjectRef`, `TaskRef`, `FolderRef` all live in `models/common.py` alongside `TagRef`
- **D-05:** Each inherits `OmniFocusBaseModel` directly -- no shared `EntityRef` base class (Pydantic flattens inheritance in JSON Schema, so a base adds a concept with zero schema benefit)
- **D-06:** Each has `id: str` and `name: str` fields, matching `TagRef` shape exactly
- **D-07:** Description constants in `descriptions.py` (verbatim):
  ```python
  PROJECT_REF_DOC = 'Reference to a project with id and name. The system inbox uses id="$inbox", name="Inbox".'
  TASK_REF_DOC = "Reference to a task with id and name."
  FOLDER_REF_DOC = "Reference to a folder with id and name."
  ```

### ParentRef Coexistence
- **D-08:** Pure coexistence -- new Ref models are added alongside ParentRef with zero changes to ParentRef or its consumers. Phase 42 owns ParentRef removal (MODL-08)

### Output Schema Testing
- **D-09:** No new schema tests in Phase 39. New Refs don't appear in tool output until Phase 42 wires them into Task. The existing `test_tool_output_validates_against_schema` covers them automatically at that point

### Claude's Discretion
- `models/__init__.py` wiring: follow TagRef pattern (import from common, `_ns` dict entry, `__all__` entry). Skip `model_rebuild()` since `(id, name)` has no forward references -- but add if executor judges it safer

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Model conventions
- `docs/model-taxonomy.md` -- Core value objects: no suffix, `models/`, inherits `OmniFocusBaseModel`. Agent-facing models use `__doc__ = CONSTANT`

### Existing patterns to follow
- `src/omnifocus_operator/models/common.py` -- TagRef and ParentRef as reference patterns
- `src/omnifocus_operator/models/__init__.py` -- Re-export, `_ns` dict, `model_rebuild()` pattern
- `src/omnifocus_operator/agent_messages/descriptions.py` -- `TAG_REF_DOC` and `PARENT_REF_DOC` as docstring constant patterns
- `src/omnifocus_operator/config.py` -- Existing constant style (verbose names, type annotations)

### Requirements
- `.planning/REQUIREMENTS.md` -- SLOC-01, MODL-01, MODL-02, MODL-03 mapped to this phase

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `TagRef(OmniFocusBaseModel)` in `models/common.py`: exact pattern for new Ref models (id, name, `__doc__` from descriptions.py)
- `config.py`: 3 existing constants with verbose names and type annotations

### Established Patterns
- Agent-facing model docstrings: `__doc__ = CONSTANT` from `descriptions.py` (enforcement test verifies)
- `models/__init__.py` re-exports all models, maintains `_ns` dict for forward ref resolution, `__all__` for public API
- Output schema tests in `test_output_schema.py`: integration-style, validates serialized tool output against MCP outputSchema

### Integration Points
- `config.py` is imported by service layer (resolver, domain logic) -- new constants will be importable immediately
- `models/common.py` classes are re-exported via `models/__init__.py` -- new Refs will be importable from `omnifocus_operator.models`

</code_context>

<specifics>
## Specific Ideas

- Description constants locked in verbatim (see D-07) -- executor must use exact strings
- Constant names locked in verbatim (see D-02) -- executor must use exact names
- Phases 40 and 42 must import constants from config.py, not hardcode values

</specifics>

<deferred>
## Deferred Ideas

- StrEnum for system locations -- revisit when SLOC-F01 lands (additional system locations like `$forecast`, `$flagged`)
- Standalone `model_json_schema()` smoke tests -- new test pattern not established; integration tests in Phase 42 cover schema validation naturally
- ParentRef deprecation signals -- roadmap is the deprecation signal; Phase 42 handles removal

</deferred>

---

*Phase: 39-foundation-constants-reference-models*
*Context gathered: 2026-04-05*
