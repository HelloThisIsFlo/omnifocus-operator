# Phase 25: Patch/PatchOrClear Type Aliases - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-20
**Phase:** 25-patch-patchorclear-type-aliases-for-command-models
**Areas discussed:** Semantic boundary, changed_fields() depth, Migration scope

---

## Semantic Boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Keep raw unions on MoveAction | PatchOrClear only where None genuinely means "clear". MoveAction stays `str \| None \| _Unset` with docstring | |
| PatchOrClear everywhere | Uniform aliases on all nullable-unset fields. Comments where None has domain meaning | |
| New PatchOrNone[T] alias | Third alias for domain-meaningful None. Accurate naming, adds vocabulary for 2 fields | ✓ |

**User's choice:** PatchOrNone[T]
**Notes:** User's reasoning: "I will 100% forget why I didn't migrate it, and I will migrate it very soon." A named alias makes the intent unforgettable — raw unions with comments will eventually lose the comment or get "fixed" by a refactor. DDD instinct: if a concept exists in the domain, it deserves a name. User asked Claude to challenge this choice; Claude acknowledged the "only 2 fields" tradeoff but agreed the self-documenting benefit justifies it.

---

## changed_fields() Depth

| Option | Description | Selected |
|--------|-------------|----------|
| Flat dict, coexist with is_set() | Nested models returned as-is. is_set() stays for TypeGuard narrowing. Each tool has one job | ✓ |
| Flat dict, migrate iteration loops | Also update payload.py's _add_if_set to use changed_fields(). Mixed patterns | |
| Recursive expand | Nested CommandModels recursively expanded to dicts. High risk | |

**User's choice:** Flat, coexist with is_set()
**Notes:** User initially needed clarification on what changed_fields() is and how it differs from is_set(). After concrete code examples, understood that: (1) changed_fields() is on CommandModel base class so all models get it automatically including nested ones, (2) flat is the right shape because the service pipeline is layered — each module handles its own level, (3) primary value is triangulation testing — tests assert via changed_fields(), production operates via is_set(), catching missing field handlers.

---

## Migration Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Model layer only (contracts/) | 4 files. Zero service code touched. Clean phase boundary | ✓ |
| Model layer + payload.py | Also update PayloadBuilder. Partial migration | |
| Full service migration | Update all is_set() consumers. Scope creep | |

**User's choice:** Model layer only
**Notes:** User initially wanted "update everything to the new standard" but asked why Claude recommended contracts-only. Key insight: changed_fields() returns dict[str, Any] (no type info), so service code that calls .isoformat() or does type-specific work needs is_set() TypeGuard for mypy narrowing. They coexist permanently — different tools for different jobs. User accepted after understanding this isn't a temporary state.

---

## Claude's Discretion

- Export surface decisions for new aliases
- Comment wording for PatchOrClear vs PatchOrNone explanation
- Test structure for schema identity verification
- Whether add_task.py needs changes (no _Unset fields currently)

## Deferred Ideas

- Service-layer adoption of changed_fields() — evaluate per-module when natural consumers arise (Phase 26 InMemoryBridge is first candidate)
