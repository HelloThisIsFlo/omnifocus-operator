# Phase 34: Contracts and Query Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 34-contracts-and-query-foundation
**Areas discussed:** ListResult shape, Filter default location, Protocol extension, Query builder scope, Query field naming, Method signature shape, Non-paginated ListResult, Query module organization, Perspectives signature, Count-only requests, Completed/dropped exclusion (→ availability filter), Query builder return type, Tool signatures review

---

## ListResult Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal: items + total_count | Matches success criteria verbatim, no redundant state | |
| Extended: has_more + offset/limit echo | Convenience flag + pagination echo for debugging | |
| User proposal: items + total + hasMore | Renamed total_count → total, added hasMore, no offset/limit echo | ✓ |

**User's choice:** Custom — `items`, `total`, `hasMore`. No offset/limit echo because agent already knows what it sent. Uniform across all 5 list tools including non-paginated ones.
**Notes:** User initially proposed including offset/limit but then reconsidered: "I'm actually wondering if we need to include offset and limit in the response, because the agent asks for this, so they already know this." For non-paginated entities, agreed to uniform shape (total=len(items), hasMore=false) rather than raw lists.

---

## Filter Default Location

| Option | Description | Selected |
|--------|-------------|----------|
| Pydantic field defaults on QueryModel | Safe-by-default at construction, self-describing | |
| Service-layer injection | Preserves agent intent vs system policy distinction | |
| Split: defaults on model, expansion in service | Defaults = contract concern (model), shorthand expansion = domain concern (service) | ✓ |

**User's choice:** Split approach — two concerns, two locations.
**Notes:** User identified the key insight: "the default I feel I want to do on the model, but the shorthand I feel I want to do on the domain." This led to the split: Pydantic defaults on the model (e.g., `status = ["remaining"]`), shorthand expansion in the service (e.g., `["remaining"]` → `["active", "on_hold"]`), repository receives concrete values only. Later evolved when availability replaced status (no shorthands needed, but the split principle remains for tag name → ID resolution).

---

## Protocol Extension

| Option | Description | Selected |
|--------|-------------|----------|
| Extend existing protocols | Add list_* to Repository/Service in protocols.py | ✓ |
| Separate query protocols | New QueryRepository/QueryService for incremental adoption | |

**User's choice:** Extend existing protocols.
**Notes:** Structure Over Discipline principle — incomplete implementations are type errors.

---

## Query Builder Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Inline in hybrid.py | Strict YAGNI, extract later | |
| Standalone repository/query_builder.py | Pure functions, v1.3.2 extends without touching hybrid.py | ✓ |

**User's choice:** Standalone module.
**Notes:** v1.3.2 is the next planned milestone with a written spec naming this module.

---

## Query Field Naming

| Option | Description | Selected |
|--------|-------------|----------|
| Agent-friendly (project, tags) | Natural for LLMs, service resolves names → IDs | ✓ |
| Implementation names (project_id, tag_ids) | Explicit but breaks agent-first design | |

**User's choice:** Agent-friendly names.

---

## Method Signature Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Flat → Query object | Server takes flat params, wraps into query, passes to service | ✓ |
| Query object everywhere | Agent must nest params inside query: {...} | |
| Flat params everywhere | No query model, 10+ optional params on protocol | |

**User's choice:** Flat at server, query object at protocol.

---

## Query Module Organization

| Option | Description | Selected |
|--------|-------------|----------|
| contracts/base.py | Next to CommandModel, QueryModel | |
| contracts/common.py | Next to TagAction, MoveAction | |
| contracts/use_cases/list_entities.py | All query models + ListResult in one use-case file | ✓ |

**User's choice:** `list_entities.py` in `use_cases/`.
**Notes:** Led to broader refactoring discussion. User proposed renaming `contracts/common.py` → `contracts/shared/actions.py` and moving `repetition_rule.py` from `use_cases/` to `contracts/shared/`. Principle: every file in `use_cases/` should be an actual use case. User executed this refactor during the session — all 1113 tests pass.

---

## Perspectives Signature

| Option | Description | Selected |
|--------|-------------|----------|
| No query model | list_perspectives() with no params, YAGNI | ✓ |
| Empty query model | ListPerspectivesQuery with zero fields for uniformity | |

**User's choice:** No query model.

---

## Count-Only Requests

| Option | Description | Selected |
|--------|-------------|----------|
| limit=0 valid | Returns {items: [], total: N, hasMore: ...} | ✓ |
| limit must be >= 1 | Use limit=1 for near-count, simpler validation | |

**User's choice:** limit=0 is valid as count-only.

---

## Completed/Dropped Exclusion (evolved into Availability Filter)

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit include_completed flag | Self-documenting opt-in on query model | |
| Implicit service behavior | Auto-exclude when no availability filter | |
| Availability list filter with default | Default ["available", "blocked"] excludes completed/dropped naturally | ✓ |

**User's choice:** Uniform availability list filter everywhere.
**Notes:** This was the most significant discussion. User asked to review existing Availability enums, then proposed: "maybe we could keep things simple and maybe not have a shorthand and then just have a list of availability." This replaced the spec's project `status` filter with shorthands. Entity-specific defaults use each entity's own availability enum values. No shorthands, no separate flags — just concrete enum values in a list.

---

## Query Builder Return Type

| Option | Description | Selected |
|--------|-------------|----------|
| NamedTuple | Self-documenting, lightweight | |
| Plain tuple | Minimal, Pythonic | |
| Claude's discretion | Implementation detail, only consumed by HybridRepository | ✓ |

**User's choice:** "That is an implementation detail, because anyway that's only going to be used by the hybrid repo."

---

## Tool Signatures Review

User reviewed all 5 tool signatures and provided feedback:
- `inbox` → `in_inbox` (matches Task model field name)
- `has_children` dropped (no agent use case identified → TASK-05 deferred)
- All other params approved as presented

---

## Claude's Discretion

- Query builder return type (NamedTuple, tuple, dataclass)
- Internal organization of query_builder.py
- Exact `hasMore` computation formula

## Deferred Ideas

- has_children filter (TASK-05) — no use case
- Status shorthands — replaced by concrete availability values
- Standalone count tools — limit=0 covers the use case
