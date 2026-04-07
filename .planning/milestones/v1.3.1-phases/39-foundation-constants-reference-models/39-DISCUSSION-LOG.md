# Phase 39: Foundation -- Constants & Reference Models - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-05
**Phase:** 39-Foundation -- Constants & Reference Models
**Areas discussed:** System location constant design, Reference model structure, ParentRef coexistence, Description constants, Output schema testing, Constants naming convention, __init__.py wiring, $inbox usage scope

---

## System Location Constant Design

| Option | Description | Selected |
|--------|-------------|----------|
| Plain string constants in config.py | SYSTEM_LOCATION_PREFIX, SYSTEM_LOCATION_INBOX, INBOX_DISPLAY_NAME -- matches existing style | :heavy_check_mark: |
| StrEnum in config.py | class SystemLocation(StrEnum): INBOX = "$inbox" -- exhaustive dispatch | |

**User's choice:** Plain string constants
**Notes:** Upgrade to StrEnum when SLOC-F01 lands (future system locations). For 1 member, plain constants are sufficient.

---

## Reference Model Structure

| Option | Description | Selected |
|--------|-------------|----------|
| In common.py, no shared base | Each inherits OmniFocusBaseModel directly alongside TagRef | :heavy_check_mark: |
| New refs.py with EntityRef base | Dedicated file, shared base class | |

**User's choice:** In common.py, no shared base
**Notes:** User asked to review model-taxonomy.md first. After review, confirmed taxonomy aligns: core value objects in models/, OmniFocusBaseModel base, no suffix.

---

## ParentRef Coexistence

| Option | Description | Selected |
|--------|-------------|----------|
| Pure coexistence | Add new Refs, don't touch ParentRef at all | :heavy_check_mark: |
| Add deprecation comment | # Deprecated comment on ParentRef class | |

**User's choice:** Pure coexistence
**Notes:** User asked for clarity on Phase 39 vs 42 split. After explanation (39 = define vocabulary, 42 = rewrite grammar), agreed Phase 42 has enough context via roadmap MODL-08.

---

## Description Constants

| Option | Description | Selected |
|--------|-------------|----------|
| One-liner (TagRef-parallel) | "Reference to a project with id and name." | :heavy_check_mark: |
| Empty string for simple models | "" with comment "Schema is self-explanatory" | |
| Contextual multi-line | Explain where each Ref appears in the schema | |
| Middle ground | What it is, not where it appears. $inbox context on ProjectRef only | |

**User's choice:** One-liner for all three, with $inbox context on ProjectRef
**Notes:** Initially considered empty strings for TaskRef/FolderRef, but after noting zero empty docstrings exist in descriptions.py, chose to maintain the convention. Exact strings locked in verbatim in CONTEXT.md D-07.

---

## Output Schema Testing

| Option | Description | Selected |
|--------|-------------|----------|
| No new tests in Phase 39 | Defer to Phase 42 integration tests | :heavy_check_mark: |
| Standalone model_json_schema() smoke test | New test pattern, 3 lines per model | |

**User's choice:** Defer to Phase 42
**Notes:** Current test architecture is integration-only (serialize + validate against MCP outputSchema). No standalone model schema tests exist. Adding a new pattern for trivial (id, name) models is unnecessary scaffolding.

---

## Constants Naming Convention

| Option | Description | Selected |
|--------|-------------|----------|
| Verbose/explicit | SYSTEM_LOCATION_PREFIX, SYSTEM_LOCATION_INBOX, INBOX_DISPLAY_NAME | :heavy_check_mark: |
| Shorter names | SYS_LOC_PREFIX, INBOX_ID, INBOX_NAME | |

**User's choice:** Verbose/explicit
**Notes:** Matches existing config.py style (DEFAULT_LIST_LIMIT, FUZZY_MATCH_MAX_SUGGESTIONS). No abbreviations.

---

## __init__.py Wiring

| Option | Description | Selected |
|--------|-------------|----------|
| Follow TagRef pattern exactly | Import, _ns entry, __all__. No model_rebuild() | :heavy_check_mark: |
| Add model_rebuild() anyway | Belt-and-suspenders consistency | |

**User's choice:** "You decide" -- Claude's discretion
**Notes:** TagRef pattern is the reference. No forward references on (id, name) models.

---

## $inbox Usage Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Define only, no updates | Constants exist but nothing imports them yet | :heavy_check_mark: |
| Also update hardcoded strings | Replace existing "inbox" references with constants | |

**User's choice:** Define only
**Notes:** User concerned about unused constants. Guarantee: Phases 40 (resolver) and 42 (task output) structurally require these constants -- they're core requirements (SLOC-02, SLOC-03, MODL-05). Noted in CONTEXT.md that downstream phases must import from config.

---

## Claude's Discretion

- `models/__init__.py` wiring details (model_rebuild yes/no)

## Deferred Ideas

- StrEnum migration when SLOC-F01 lands
- Standalone model schema smoke tests
- ParentRef deprecation annotations
