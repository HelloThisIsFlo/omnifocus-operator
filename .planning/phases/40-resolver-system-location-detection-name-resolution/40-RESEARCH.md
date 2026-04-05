# Phase 40: Resolver -- System Location Detection & Name Resolution - Research

**Researched:** 2026-04-05
**Domain:** Write-side input resolution (system locations, name-to-ID cascade, error messages)
**Confidence:** HIGH

## Summary

Phase 40 transforms the existing `Resolver` class from ID-only validation to a full resolution cascade: `$`-prefix system locations, case-insensitive substring name matching, and ID fallback. The codebase already has all building blocks -- `_match_by_name`, `suggest_close_matches`, `resolve_filter` (read-side cascade), and system location constants from Phase 39. The work is: build `_resolve` as the single cascade implementation, add semantic wrapper methods, extract fuzzy matching to a shared module, wire into all 5 write fields, and rename existing lookup methods.

No external dependencies. No new libraries. Pure Python refactoring and feature work within existing patterns.

**Primary recommendation:** Build bottom-up: shared fuzzy utility, `_EntityType` enum, `_resolve` cascade, public wrappers, error templates, then wire call sites. Test each layer independently.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Three-step cascade: `$`-prefix detection -> case-insensitive substring name match -> ID fallback
- **D-02:** `$`-prefix always short-circuits first -- before any name or ID lookup (NRES-06). Reserved globally across all entity types
- **D-03:** Substring matching requires exactly one match. Multiple matches -> ambiguity error (NRES-04). Zero matches -> error with fuzzy suggestions (NRES-05)
- **D-04:** Unrecognized `$`-prefixed value -> error listing valid system locations (SLOC-03). Educational message advising to use ID if entity name starts with `$`
- **D-05:** Private `_EntityType` enum with values: `PROJECT`, `TASK`, `TAG`
- **D-06:** Private `_resolve(value, *, accept: list[_EntityType], entities?: ...) -> str` -- the full cascade implementation
- **D-07:** Public `resolve_container(value: str) -> str` -- passes `[PROJECT, TASK]` to `_resolve`. Used by `parent`, `beginning`/`ending`
- **D-08:** Public `resolve_anchor(value: str) -> str` -- passes `[TASK]` to `_resolve`. Used by `before`/`after`
- **D-09:** Public `resolve_tags(names: list[str]) -> list[str]` -- unified into same cascade. Pre-fetches all tags once
- **D-10:** Rename: `resolve_task` -> `lookup_task`, `resolve_project` -> `lookup_project`, `resolve_tag` -> `lookup_tag`
- **D-11:** Shared fuzzy suggestion utility extracted from `domain.py` into a shared module
- **D-12:** Ambiguous matches: ID + name pairs format, retires `AMBIGUOUS_ENTITY` template
- **D-13:** Zero matches: always include fuzzy suggestions with shared utility
- **D-14:** Invalid system location: `"Unknown system location '{value}'. Valid system locations: {valid_locations}."`
- **D-15:** `$` reserved globally: educational error for any `$`-prefixed entity type
- **D-16:** Phase 40 builds AND wires the resolver. All 5 write fields accept entity names end-to-end
- **D-17:** Phase 41 inherits fully-wired resolver, focuses on `$inbox` pipeline behavior
- **D-18:** Tag name resolution moves from exact case-insensitive match to substring match
- **D-19:** Resolver raises errors (write-side). Domain generates warnings (read-side). Boundary unchanged
- **D-20:** `resolve_*` returns `str` (ID). `lookup_*` returns full entity. Distinct concerns, hence rename

### Claude's Discretion
- `_EntityType` enum location: private to `resolve.py` or shared -- executor decides based on import needs
- Exact naming of shared fuzzy utility module (e.g., `fuzzy.py`, `matching.py`)
- Whether `_resolve` accepts pre-fetched entities via parameter or uses internal caching for batch calls
- Filter methods (`resolve_filter`, `resolve_filter_list`, `find_unresolved`) -- left unchanged, may rename if trivial

### Deferred Ideas (OUT OF SCOPE)
- StrEnum for system locations -- revisit when SLOC-F01 lands
- Filter method rename (`resolve_filter` -> something more consistent)
- `resolve_tags` accepting `$`-prefixed system tags

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SLOC-02 | Resolver detects `$`-prefixed strings and routes to system location lookup before ID/name resolution | `_resolve` cascade step 1: check `value.startswith(SYSTEM_LOCATION_PREFIX)`. Constants already in `config.py` |
| SLOC-03 | Unrecognized system location returns error listing valid system locations | New error template `INVALID_SYSTEM_LOCATION` with dynamic `{valid_locations}` placeholder |
| NRES-01 | `add_tasks` `parent` accepts project/task names (case-insensitive substring) | `resolve_container` wired into `_AddTaskPipeline._resolve_parent()` |
| NRES-02 | `edit_tasks` `beginning`/`ending` accept container names | `resolve_container` wired into `_process_container_move()` in `domain.py` |
| NRES-03 | `edit_tasks` `before`/`after` accept task names | `resolve_anchor` wired into `_process_anchor_move()` in `domain.py` |
| NRES-04 | Multiple name matches -> error listing all matches with IDs | `_resolve` raises with new `AMBIGUOUS_NAME_MATCH` template (ID + name pairs) |
| NRES-05 | Zero name matches -> helpful error | `_resolve` raises with `NAME_NOT_FOUND` template including fuzzy suggestions |
| NRES-06 | `$`-prefixed strings never enter name resolution | `_resolve` short-circuits on `$` prefix before any name/ID lookup |
| NRES-08 | Tag name resolution uses case-insensitive substring matching | `resolve_tags` delegates to `_resolve` which uses substring, not exact match |

</phase_requirements>

## Standard Stack

### Core
No new libraries. All work uses existing stdlib and project dependencies.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `difflib` | stdlib | Fuzzy matching via `get_close_matches` | Already used in `domain.py`, extracting to shared module |
| `enum` | stdlib | `_EntityType` enum | Standard Python enum, already used elsewhere in project |

### Supporting
No new dependencies needed.

## Architecture Patterns

### Recommended Module Structure
```
src/omnifocus_operator/
├── service/
│   ├── resolve.py          # Resolver class (modified: cascade + renames)
│   ├── domain.py           # DomainLogic (modified: fuzzy extraction, call site updates)
│   ├── service.py          # Pipelines (modified: wiring updates)
│   └── fuzzy.py            # NEW: shared fuzzy suggestion utility
├── agent_messages/
│   └── errors.py           # Modified: new error templates, retire AMBIGUOUS_ENTITY
└── config.py               # Already has SYSTEM_LOCATION_* constants
```

### Pattern 1: Resolution Cascade (the core algorithm)
**What:** Three-step resolution for any write-field value
**When to use:** Every write field that accepts entity references (`parent`, `beginning`, `ending`, `before`, `after`, tag names)

```python
# Pseudocode for _resolve
async def _resolve(self, value: str, *, accept: list[_EntityType], entities: Sequence[_HasIdAndName] | None = None) -> str:
    # Step 1: $ prefix -> system location
    if value.startswith(SYSTEM_LOCATION_PREFIX):
        return self._resolve_system_location(value)

    # Step 2: Substring name match (fetch entities if not provided)
    if entities is None:
        entities = await self._fetch_entities(accept)
    lower = value.lower()
    matches = [e for e in entities if lower in e.name.lower()]
    if len(matches) == 1:
        return matches[0].id
    if len(matches) > 1:
        raise ValueError(...)  # ambiguity error with ID+name pairs

    # Step 3: ID fallback
    id_match = next((e for e in entities if e.id == value), None)
    if id_match:
        return id_match.id

    # No match at all -> error with fuzzy suggestions
    raise ValueError(...)
```
[VERIFIED: codebase analysis of existing `_match_by_name`, `resolve_filter`, and `resolve_parent`]

### Pattern 2: Thin Semantic Wrappers
**What:** Public methods that constrain entity types for the cascade
**When to use:** Each write-field context has different valid entity types

```python
async def resolve_container(self, value: str) -> str:
    return await self._resolve(value, accept=[_EntityType.PROJECT, _EntityType.TASK])

async def resolve_anchor(self, value: str) -> str:
    return await self._resolve(value, accept=[_EntityType.TASK])

async def resolve_tags(self, names: list[str]) -> list[str]:
    entities = await self._fetch_all_tags()  # pre-fetch once
    return [await self._resolve(n, accept=[_EntityType.TAG], entities=entities) for n in names]
```
[VERIFIED: D-07, D-08, D-09 from CONTEXT.md]

### Pattern 3: Method Object Wiring
**What:** Pipeline steps call resolver methods by name -- wiring is updating call targets
**Current call sites to update:**

| Location | Current Call | New Call |
|----------|-------------|----------|
| `service.py:450` | `self._resolver.resolve_parent(...)` | `self._resolver.resolve_container(...)` |
| `domain.py:593` | `self._resolver.resolve_parent(...)` | `self._resolver.resolve_container(...)` |
| `domain.py:609` | `self._resolver.resolve_task(anchor_id)` | `self._resolver.resolve_anchor(anchor_id)` |
| `service.py:551` | `self._resolver.resolve_task(...)` | `self._resolver.lookup_task(...)` |
| `service.py:112` | `self._resolver.resolve_task(...)` | `self._resolver.lookup_task(...)` |
| `service.py:117` | `self._resolver.resolve_project(...)` | `self._resolver.lookup_project(...)` |
| `service.py:122` | `self._resolver.resolve_tag(...)` | `self._resolver.lookup_tag(...)` |

[VERIFIED: grep of all `resolve_task`, `resolve_project`, `resolve_tag`, `resolve_parent` calls in service.py and domain.py]

### Anti-Patterns to Avoid
- **Two-tier API where callers choose wrong method:** Per `docs/structure-over-discipline.md`, the path of least resistance must lead to correct outcome. `resolve_container` and `resolve_anchor` must be the only way to resolve write-field values -- no backdoor that skips the cascade
- **N+1 fetches for tag resolution:** `resolve_tags` MUST pre-fetch all tags once, then pass to `_resolve` per name. Never one fetch per tag
- **Hardcoding `$inbox`:** Use `SYSTEM_LOCATION_PREFIX` and `SYSTEM_LOCATION_INBOX` from `config.py` per Phase 39 D-03

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fuzzy matching | Custom Levenshtein or similarity | `difflib.get_close_matches` | Already proven in codebase, handles edge cases |
| System location registry | Ad-hoc if/elif chain | Dict mapping `$inbox` -> ID (extensible) | D-14 requires dynamic `{valid_locations}` for future extensibility |

## Common Pitfalls

### Pitfall 1: Substring Matching Returning Too Many Results
**What goes wrong:** Common substrings (e.g., "a", "the") match nearly everything
**Why it happens:** Substring is more permissive than exact match
**How to avoid:** This is by design -- multiple matches produce an error (D-03). The error message lists all candidates with IDs. Agent refines by using ID
**Warning signs:** If tests don't cover the ambiguity error path for short substrings

### Pitfall 2: Entity Fetching for Container Resolution
**What goes wrong:** `resolve_container` needs both projects AND tasks, but there's no single repo method returning both
**Why it happens:** Repository protocol has `get_all()` which returns `AllEntities` with both `.tasks` and `.projects`
**How to avoid:** Use `repo.get_all()` to fetch once, concatenate `.projects` + `.tasks` into entity list. Already used in `domain.py` for cycle detection
**Warning signs:** Separate `list_projects` + `list_tasks` calls (unnecessary overhead, pagination issues)

### Pitfall 3: Rename Breaks External Test Assertions
**What goes wrong:** Renaming `resolve_task` -> `lookup_task` breaks tests that assert on method names or mock those methods
**Why it happens:** Tests in `test_service_resolve.py`, `test_service.py`, `test_service_domain.py` all reference these methods
**How to avoid:** Systematic find-and-replace across all test files, not just production code. Run full test suite after rename
**Warning signs:** Tests pass individually but fail as suite due to import/mock mismatches

### Pitfall 4: `$`-Prefix Check Must Be First
**What goes wrong:** If substring matching runs before `$` check, `$inbox` might match an entity named "inbox" via substring
**Why it happens:** Cascade order matters
**How to avoid:** `_resolve` step 1 is ALWAYS `$` prefix check, short-circuiting to system location logic before any name/ID work (D-02)
**Warning signs:** Test that passes `$inbox` through name matching and gets unexpected result

### Pitfall 5: `_process_container_move` Accepts `None` for Inbox
**What goes wrong:** Currently `_process_container_move` handles `container_id: str | None` where `None` means inbox. After wiring `resolve_container`, the semantics change
**Why it happens:** Phase 41 owns `$inbox` pipeline behavior (D-17). Phase 40 only wires the resolver for non-None values
**How to avoid:** Keep the `None` path in `_process_container_move` unchanged. Only pass non-None values through `resolve_container`. Phase 41 will handle `$inbox` -> `None` mapping
**Warning signs:** Breaking existing inbox-via-None behavior

## Code Examples

### Current `_match_by_name` (being superseded)
```python
# Source: src/omnifocus_operator/service/resolve.py:116-131
def _match_by_name(self, name: str, entities: Sequence[_HasIdAndName], entity_type: str) -> str:
    matches = [e for e in entities if e.name.lower() == name.lower()]  # EXACT match
    if len(matches) == 1:
        return matches[0].id
    if len(matches) > 1:
        ids = ", ".join(m.id for m in matches)
        msg = AMBIGUOUS_ENTITY.format(entity_type=entity_type, name=name, ids=ids)
        raise ValueError(msg)
    # No name match -- try as ID fallback
    id_match = next((e for e in entities if e.id == name), None)
    if id_match is not None:
        return id_match.id
    msg = TAG_NOT_FOUND.format(name=name)
    raise ValueError(msg)
```
Key difference from new `_resolve`: exact match -> substring match, and `$`-prefix step added before.

### Current `suggest_close_matches` (being extracted)
```python
# Source: src/omnifocus_operator/service/domain.py:124-132
def suggest_close_matches(self, value: str, entity_names: list[str],
    n: int = FUZZY_MATCH_MAX_SUGGESTIONS, cutoff: float = FUZZY_MATCH_CUTOFF) -> list[str]:
    return difflib.get_close_matches(value, entity_names, n=n, cutoff=cutoff)
```
Extract to standalone function in shared module. `DomainLogic.suggest_close_matches` becomes a delegation to the shared function.

### Error Template Patterns
```python
# Source: src/omnifocus_operator/agent_messages/errors.py
# Existing pattern -- all templates use {placeholder} + .format()
AMBIGUOUS_ENTITY = (
    "Ambiguous {entity_type} '{name}': multiple matches ({ids}). "
    "For ambiguous {entity_type}s, specify by ID instead of name."
)
# New templates follow same pattern:
# AMBIGUOUS_NAME_MATCH -- replaces AMBIGUOUS_ENTITY, uses id (name) pairs
# NAME_NOT_FOUND -- zero matches with fuzzy suggestions
# INVALID_SYSTEM_LOCATION -- unrecognized $ prefix
# RESERVED_PREFIX -- educational: $ is reserved, use ID
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pyproject.toml` (pytest section) |
| Quick run command | `uv run pytest tests/test_service_resolve.py -x -q` |
| Full suite command | `uv run pytest -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SLOC-02 | `$inbox` in write field resolves without name/ID lookup | unit | `uv run pytest tests/test_service_resolve.py -x -q -k system_location` | Partial (constants only in `test_system_locations.py`) -- Wave 0 needed for cascade tests |
| SLOC-03 | `$trash` returns error listing valid locations | unit | `uv run pytest tests/test_service_resolve.py -x -q -k invalid_system_location` | Wave 0 |
| NRES-01 | `add_tasks` parent accepts names | integration | `uv run pytest tests/test_service.py -x -q -k add_task_name_resolution` | Wave 0 |
| NRES-02 | `edit_tasks` beginning/ending accept names | integration | `uv run pytest tests/test_service.py -x -q -k edit_task_move_name` | Wave 0 |
| NRES-03 | `edit_tasks` before/after accept task names | integration | `uv run pytest tests/test_service.py -x -q -k edit_task_anchor_name` | Wave 0 |
| NRES-04 | Multiple name matches -> error with IDs | unit | `uv run pytest tests/test_service_resolve.py -x -q -k ambiguous` | Exists but needs update for new format |
| NRES-05 | Zero name matches -> helpful error | unit | `uv run pytest tests/test_service_resolve.py -x -q -k not_found` | Exists but needs update for fuzzy suggestions |
| NRES-06 | `$`-prefixed strings never enter name resolution | unit | `uv run pytest tests/test_service_resolve.py -x -q -k dollar_prefix` | Wave 0 |
| NRES-08 | Tag name resolution uses substring matching | unit | `uv run pytest tests/test_service_resolve.py -x -q -k tag_substring` | Wave 0 (existing tests use exact match) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_service_resolve.py tests/test_service.py tests/test_service_domain.py -x -q`
- **Per wave merge:** `uv run pytest -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] Tests for `_resolve` cascade (system location, substring match, ID fallback)
- [ ] Tests for `resolve_container` and `resolve_anchor` wrappers
- [ ] Tests for new error templates (ambiguous with names, zero match with fuzzy, invalid system location, reserved prefix)
- [ ] Integration tests for end-to-end name resolution through `add_task` and `edit_task` pipelines
- [ ] Tests for tag substring matching (replacing exact match behavior)
- [ ] Update existing ambiguous/not-found tests for new error message format

## Security Domain

Not applicable for this phase. No authentication, session management, cryptography, or user-facing input beyond entity names (already validated). All inputs come through the MCP protocol layer which handles basic validation.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `repo.get_all()` is efficient enough for container resolution (fetching all entities to search by name) | Architecture Patterns | If get_all is expensive, may need `list_projects` + `list_tasks` instead -- but get_all is already used for cycle detection, so perf is acceptable |

All other claims verified against codebase.

## Open Questions

1. **Entity fetching strategy for `_resolve`**
   - What we know: `get_all()` returns all entities, used for cycle detection already. `list_tags` used for tag resolution currently
   - What's unclear: Whether to use `get_all()` for container resolution or `list_projects` + `list_tasks` separately
   - Recommendation: Use `get_all()` -- simpler, already proven, and the data is cached by the hybrid repository

## Sources

### Primary (HIGH confidence)
- `src/omnifocus_operator/service/resolve.py` -- current Resolver implementation, all methods analyzed
- `src/omnifocus_operator/service/domain.py` -- `suggest_close_matches`, `_process_container_move`, `_process_anchor_move`
- `src/omnifocus_operator/service/service.py` -- all pipeline call sites for resolver methods
- `src/omnifocus_operator/agent_messages/errors.py` -- current error templates
- `src/omnifocus_operator/config.py` -- system location constants
- `tests/test_service_resolve.py` -- 35 existing tests, all passing
- `.planning/phases/40-resolver-system-location-detection-name-resolution/40-CONTEXT.md` -- all locked decisions

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, pure Python
- Architecture: HIGH -- all building blocks exist, pattern is clear from read-side cascade and existing `_match_by_name`
- Pitfalls: HIGH -- identified from direct codebase analysis of call sites and test files

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (stable domain, internal architecture)
