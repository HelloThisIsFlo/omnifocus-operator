# Phase 40: Resolver -- System Location Detection & Name Resolution - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-05
**Phase:** 40-resolver-system-location-detection-name-resolution
**Mode:** discuss (--analyze)
**Areas discussed:** Resolution cascade, Resolver API shape, Error messages, Scope boundary

---

## Resolution Cascade

| Option | Description | Selected |
|--------|-------------|----------|
| Exact match only | Case-insensitive exact match + ID fallback (current `_match_by_name` pattern) | |
| Substring match | Case-insensitive substring, single-match required or error. Consistent with read-side | ✓ |
| Exact → substring cascade | Try exact first, fall through to substring on miss. Two-phase approach | |

**User's choice:** Substring match
**Notes:** User confirmed $-prefix must always short-circuit first. Exact→substring cascade "sounds clever but would cause more problems than actually help" — two ambiguity surfaces add confusion. Substring satisfies NRES-01 literally and is consistent with read-side.

---

## Resolver API Shape

This area had extensive discussion across multiple rounds. The initial framing (option 1: generic `resolve_entity` vs option 2: extend existing methods) evolved significantly after the user brought in `docs/structure-over-discipline.md` and `docs/architecture.md`.

### Round 1: Initial framing

| Option | Description | Selected |
|--------|-------------|----------|
| Generic `resolve_entity(value, entity_type)` + delete old methods | One new public method, old resolution methods deleted | |
| Extend existing methods + shared private helper | `resolve_parent` gains cascade, new `resolve_anchor` added, shared `_resolve_value` underneath | |

**Notes:** User referenced `docs/structure-over-discipline.md` — "make the structure guide toward the right choice." Initial analysis favored extending existing methods (path of least resistance = right path). User then proposed: "why not `resolve_entity` and just delete the old methods?"

### Round 2: Delete vs extend

| Option | Description | Selected |
|--------|-------------|----------|
| `resolve_entity()` + delete old methods | Structurally impossible to skip cascade | |
| Extend existing + private helper | Familiar names, callers don't change | |

**Notes:** User saw merit in both. Shifted focus to understanding the error/warning flow across resolver and domain before committing to API shape.

### Round 3: Lookup vs resolve distinction

Through discussion, the two responsibilities of the Resolver class were identified:
- **Resolution** (ambiguous input → ID): `resolve_parent`, `resolve_tags`
- **Lookup** (known ID → entity): `resolve_task`, `resolve_project`, `resolve_tag`

User proposed renaming lookup methods: `resolve_task` → `lookup_task`, etc. "If they return the full entity, let's call them `lookup`."

### Round 4: Final design — list-of-enum approach

| Option | Description | Selected |
|--------|-------------|----------|
| `resolve_container` + `resolve_anchor` with `_EntityType` enum | Public methods are semantic wrappers, private `_resolve` accepts list of entity types | ✓ |

**User's choice:** `resolve_container(value) -> str` passes `[PROJECT, TASK]`, `resolve_anchor(value) -> str` passes `[TASK]`. Private `_resolve(value, accept: list[_EntityType]) -> str` implements the full cascade.

User also decided to unify `resolve_tags` into the same pattern: "those refactoring 'later' often means never." Tags gain substring matching as a side effect — user called this "a wonderful side effect."

---

## Error Messages

### Ambiguous matches (NRES-04)

| Option | Description | Selected |
|--------|-------------|----------|
| IDs only (current `AMBIGUOUS_ENTITY`) | Compact but agent needs second lookup | |
| ID + name pairs | Agent sees everything in one error, consistent with `FILTER_MULTI_MATCH` | ✓ |

**User's choice:** ID + name pairs
**Notes:** "Much, much better." Asked whether existing `AMBIGUOUS_ENTITY` would also be updated — yes, it's retired by this migration since `_match_by_name` is replaced.

### Zero matches (NRES-05)

| Option | Description | Selected |
|--------|-------------|----------|
| Always include fuzzy suggestions | Uses shared utility, agent recovers in one round-trip | ✓ |
| Plain not-found only | Simpler but agent retries blind | |

**User's choice:** Always include suggestions

### Invalid system location (SLOC-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Dynamic `{valid_locations}` placeholder | Future-extensible, formatted at call site | ✓ |

**User's choice:** Dynamic placeholder

### $-prefix reserved globally

| Option | Description | Selected |
|--------|-------------|----------|
| Reserved globally (all entity types including tags) | Consistent, no surprises, educational error | ✓ |
| Only for containers/anchors | More permissive but inconsistent | |

**User's choice:** Reserved globally
**Notes:** "Not because we need it for tags, but for consistency and no surprises." Error message should advise using ID if entity name happens to start with `$`.

---

## Scope Boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Resolver built + wired | Phase 40 delivers full cascade AND updates call sites. SC-3 testable end-to-end | ✓ |
| Resolver built only | Phase 40 builds methods but doesn't wire. SC-3 unit-test only | |

**User's choice:** Built + wired
**Notes:** User was "a little bit worried about the scope" but accepted the recommendation that it keeps Phase 41 narrow.

---

## Claude's Discretion

- `_EntityType` enum placement (resolve.py or shared)
- Shared fuzzy utility module naming
- `_resolve` pre-fetch strategy (parameter vs caching)
- Filter method rename (low priority, deferred)

## Deferred Ideas

- StrEnum for system locations — future milestone (SLOC-F01)
- Filter method rename for consistency — low priority
- System tags ($-prefixed) — future if ever needed
