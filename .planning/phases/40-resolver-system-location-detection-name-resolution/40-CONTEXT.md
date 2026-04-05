# Phase 40: Resolver -- System Location Detection & Name Resolution - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Agents can pass entity names or `$`-prefixed system locations to any write field, with clear error messages for ambiguous or invalid inputs. Build the resolver cascade, wire it into all write-side call sites, rename lookup methods for clarity, and unify tag name resolution into the same pattern.

</domain>

<decisions>
## Implementation Decisions

### Resolution Cascade
- **D-01:** Three-step cascade: `$`-prefix detection → case-insensitive substring name match → ID fallback
- **D-02:** `$`-prefix always short-circuits first -- before any name or ID lookup (NRES-06). Reserved globally across all entity types (containers, anchors, tags)
- **D-03:** Substring matching requires exactly one match. Multiple matches → ambiguity error (NRES-04). Zero matches → error with fuzzy suggestions (NRES-05)
- **D-04:** Unrecognized `$`-prefixed value → error listing valid system locations (SLOC-03). Educational message advising to use ID if the entity name happens to start with `$`

### Resolver API Shape
- **D-05:** Private `_EntityType` enum with values: `PROJECT`, `TASK`, `TAG`
- **D-06:** Private `_resolve(value, *, accept: list[_EntityType], entities?: ...) -> str` -- the full cascade implementation. Accepts optional pre-fetched entity list for batch resolution (avoids N redundant fetches for tags)
- **D-07:** Public `resolve_container(value: str) -> str` -- passes `[PROJECT, TASK]` to `_resolve`. Used by `parent` (add_tasks), `beginning`/`ending` (edit_tasks)
- **D-08:** Public `resolve_anchor(value: str) -> str` -- passes `[TASK]` to `_resolve`. Used by `before`/`after` (edit_tasks)
- **D-09:** Public `resolve_tags(names: list[str]) -> list[str]` -- unified into same cascade. Pre-fetches all tags once, delegates per name to `_resolve` with `[TAG]`
- **D-10:** Rename existing entity-fetching methods: `resolve_task` → `lookup_task`, `resolve_project` → `lookup_project`, `resolve_tag` → `lookup_tag`. These are ID-based lookups returning full entities -- semantically distinct from the resolution cascade
- **D-11:** Shared fuzzy suggestion utility extracted from domain.py into a shared module. Used by both resolver (write-side errors) and domain (read-side filter "did you mean?" warnings)

### Error Messages
- **D-12:** Ambiguous matches (NRES-04): ID + name pairs format -- `"Ambiguous {entity_type} '{name}': {id} ({name}), {id} ({name})."` Retires existing `AMBIGUOUS_ENTITY` template (ID-only). Consistent with read-side `FILTER_MULTI_MATCH` pattern
- **D-13:** Zero matches (NRES-05): Always include fuzzy suggestions -- `"Not found: '{name}'. Did you mean: {name} ({id}), {name} ({id})?"` Uses shared fuzzy utility with existing config constants (`FUZZY_MATCH_MAX_SUGGESTIONS=3`, `FUZZY_MATCH_CUTOFF=0.6`)
- **D-14:** Invalid system location (SLOC-03): `"Unknown system location '{value}'. Valid system locations: {valid_locations}."` Dynamic `{valid_locations}` placeholder for future extensibility
- **D-15:** `$` reserved globally: educational error when `$`-prefix is used on any entity type (including tags) -- explains the reservation and advises using ID for entities whose names happen to start with `$`

### Error/Warning Architecture (unchanged boundary)
- **D-19:** Resolver raises errors (write-side, hard failures: not found, ambiguous, invalid $-prefix). Domain generates warnings (business logic: no-ops, "did you mean?" on read-side filters). This boundary is unchanged by Phase 40 -- all new failure modes are errors in the resolver, not warnings in domain
- **D-20:** `resolve_*` methods return `str` (ID) -- write pipeline needs IDs for bridge payloads. `lookup_*` methods return full entities (`Task`, `Project`, `Tag`) -- edit pipeline needs the entity object for no-op detection and current-state comparison. These are distinct concerns, hence the rename

### Scope Boundary
- **D-16:** Phase 40 builds AND wires the resolver. All 5 write fields (`parent`, `beginning`, `ending`, `before`, `after`) accept entity names end-to-end. SC-3 is testable behaviorally, not just via unit tests
- **D-17:** Phase 41 inherits a fully-wired resolver and focuses on: `$inbox`-specific pipeline behavior, `PatchOrNone` elimination, and null error handling
- **D-18:** Tag name resolution moves from exact case-insensitive match to substring match as part of resolver unification (NRES-08)

### Claude's Discretion
- `_EntityType` enum: private to resolve.py or in a shared location -- executor decides based on import needs
- Exact naming of the shared fuzzy utility module (e.g., `fuzzy.py`, `matching.py`, or similar)
- Whether `_resolve` accepts pre-fetched entities via parameter or uses an internal caching strategy for batch calls
- Filter methods (`resolve_filter`, `resolve_filter_list`, `find_unresolved`) -- left unchanged, but executor may rename for consistency if the rename is trivial

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture
- `docs/architecture.md` -- Write pipeline diagram, Method Object pattern, "Dumb Bridge, Smart Python" principle, service layer responsibilities
- `docs/structure-over-discipline.md` -- Design philosophy: path of least resistance must lead to correct outcome. Directly informed the API design (no two-tier API where callers choose wrong method)
- `docs/model-taxonomy.md` -- Model naming conventions, boundary split principle

### Existing resolver
- `src/omnifocus_operator/service/resolve.py` -- Current Resolver class: `resolve_parent`, `resolve_task`, `resolve_project`, `resolve_tag`, `resolve_tags`, `_match_by_name`, filter methods
- `src/omnifocus_operator/service/domain.py` -- `suggest_close_matches` (fuzzy, to be extracted), `_process_container_move` (calls `resolve_parent`), `_process_anchor_move` (anchor resolution)
- `src/omnifocus_operator/service/service.py` -- Pipeline classes: `_AddTaskPipeline._resolve_parent()`, `_EditTaskPipeline` steps that call resolver

### Error messages and config
- `src/omnifocus_operator/agent_messages/errors.py` -- All error templates. `AMBIGUOUS_ENTITY` to be retired and replaced
- `src/omnifocus_operator/config.py` -- `SYSTEM_LOCATION_PREFIX`, `SYSTEM_LOCATION_INBOX`, `FUZZY_MATCH_MAX_SUGGESTIONS`, `FUZZY_MATCH_CUTOFF`

### Prior phase
- `.planning/phases/39-foundation-constants-reference-models/39-CONTEXT.md` -- D-03: Phase 40 MUST import constants from config.py, not hardcode values

### Requirements
- `.planning/REQUIREMENTS.md` -- SLOC-02, SLOC-03, NRES-01 through NRES-06, NRES-08 (tag substring matching) mapped to this phase

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_match_by_name` in `resolve.py`: existing name matching logic -- will be superseded by `_resolve` but informs the pattern
- `suggest_close_matches` in `domain.py`: fuzzy suggestion logic using `difflib.get_close_matches` -- to be extracted to shared utility
- `resolve_filter` / `resolve_filter_list`: read-side cascade (ID → substring) -- unchanged but informed the write-side cascade design
- `SYSTEM_LOCATION_PREFIX`, `SYSTEM_LOCATION_INBOX`, `INBOX_DISPLAY_NAME` in `config.py`: constants from Phase 39, ready to import

### Established Patterns
- Pipeline steps call resolver methods by name (`_resolve_parent`, `_resolve_tags`) -- wiring update is renaming call targets
- Error templates in `errors.py` use `{placeholder}` + `.format()` -- new error templates follow same pattern
- Agent-first error design: errors educate and guide toward correct usage

### Integration Points
- `_AddTaskPipeline._resolve_parent()` in `service.py:447-450` -- update to call `resolve_container`
- `_process_container_move()` in `domain.py:593` -- update to call `resolve_container`
- `_process_anchor_move()` in `domain.py` -- update to call `resolve_anchor`
- `_EditTaskPipeline._verify_task_exists()` in `service.py` -- update to call `lookup_task`

</code_context>

<specifics>
## Specific Ideas

- Error for `$`-reserved names should be educational: explain the reservation and advise "if your entity name starts with $, refer to it by ID"
- Ambiguous match format must use `id (name)` pairs, consistent with the more recent `FILTER_MULTI_MATCH` pattern -- not the older ID-only `AMBIGUOUS_ENTITY` pattern
- `resolve_tags` must pre-fetch all tags once for the batch, not N individual fetches
- The `_resolve` private method is the single source of truth for the cascade -- public methods are thin semantic wrappers

</specifics>

<deferred>
## Deferred Ideas

- StrEnum for system locations -- revisit when SLOC-F01 lands (additional system locations like `$forecast`, `$flagged`)
- Filter method rename (`resolve_filter` → something more consistent) -- low priority, read-side unchanged
- `resolve_tags` could eventually accept `$`-prefixed system tags if system tags are introduced in future milestones

</deferred>

---

*Phase: 40-resolver-system-location-detection-name-resolution*
*Context gathered: 2026-04-05*
