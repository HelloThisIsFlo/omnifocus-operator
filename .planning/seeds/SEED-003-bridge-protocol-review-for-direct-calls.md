---
id: SEED-003
status: dormant
planted: 2026-03-21
planted_during: v1.2.1 phase 27 (Repository Contract Tests for Behavioral Equivalence)
trigger_when: when features require service→bridge direct calls bypassing the repository
scope: Small
---

# SEED-003: Review Bridge protocol for direct service→bridge calls

## Why This Matters

Currently all bridge communication is mediated by the repository layer:

```
Service → Repository → Bridge
```

The repository handles format transformations (`adapt_snapshot`), response validation
(Pydantic `model_validate`), caching, and write-through semantics. The Bridge protocol
(`send_command → dict[str, Any]`) works well because the repo always sits in front of it.

When features introduce a direct service→bridge path (bypassing the repo), questions arise:
- Where do format transformations live? (`adapt_snapshot` is currently repo-level)
- Who validates response shapes?
- Does the service need its own thin adapter, or can it consume raw bridge dicts?
- Should `_validate_response` (currently inside `RealBridge`) be surfaced as a shared utility?

This came out of the SEED-002 investigation (unified bridge response envelope), which
concluded the envelope is not needed but identified this as the real future concern.

## When to Surface

**Trigger:** When any milestone introduces features that call the bridge directly
from the service layer, bypassing the repository.

Surface conditions:
- Perspective operations (v1.5 spec: `read_view`, `set_perspective`, `get_perspective`)
- Any future feature where the service talks to the bridge without repo mediation
- Any discussion about adding a new data path that doesn't fit the current Service→Repo→Bridge chain

## Scope Estimate

**Small** — Likely a quick review and possibly a thin adapter or helper extraction.
The bridge protocol itself is simple; the question is about where to put the
consuming/transformation logic for the new data path.

## Breadcrumbs

Related code and decisions from SEED-002 investigation:

- `src/omnifocus_operator/contracts/protocols.py` — Bridge protocol (`send_command → dict[str, Any]`)
- `src/omnifocus_operator/bridge/real.py` — `_validate_response` strips OmniJS `{success, data/error}` envelope
- `src/omnifocus_operator/bridge/adapter.py` — `adapt_snapshot` transforms bridge format → model shape
- `src/omnifocus_operator/repository/bridge_write_mixin.py` — shared bridge-sending logic (serialize + send)
- `src/omnifocus_operator/repository/bridge.py` — BridgeRepository: all reads go through bridge via `get_all`
- `src/omnifocus_operator/repository/hybrid.py` — HybridRepository: reads via SQLite, writes via bridge
- `.planning/seeds/SEED-002-unified-bridge-response-envelope.md` — parent investigation (closed)

## Notes

- The OmniJS bridge already has a consistent `{success, data/error}` envelope at the transport level
- `RealBridge._validate_response` strips this before Python consumers see it
- The `dict[str, Any]` return type from `send_command` is appropriate for the serialization boundary
- Type safety belongs at the consumer (Pydantic `model_validate`, typed results), not the transport
- v1.5 spec mentions `read_view` returns tasks in same format as `get_all` — may need `adapt_snapshot` or equivalent
