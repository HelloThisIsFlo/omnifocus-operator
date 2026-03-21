---
id: SEED-004
status: dormant
planted: 2026-03-21
planted_during: v1.2.1 Phase 27 (repository-contract-tests-for-behavioral-equivalence)
trigger_when: v1.3+ architecture — when adapter reliability matters for new read tools
scope: Medium
---

# SEED-004: Adapter silent no-op violates fail-fast

## Why This Matters

`_adapt_task()` in `adapter.py` (line 153) uses `"status" not in raw` as a guard
to skip the entire function — including `_adapt_parent_ref`, `_adapt_repetition_rule`,
and dead field removal. This conflates "status conversion" with "all adaptation steps."

**The real bug:** `availability` and `urgency` are adapter-invented concepts. The real
OmniFocus bridge returns `status`. InMemoryBridge returns `availability`/`urgency`
directly (skipping the raw bridge format), which makes the adapter silently skip all
conversions — including parent normalization. This caused a bug where changing
InMemoryBridge's parent representation leaked through to the service layer undetected.

The adapter should either fail loudly on unexpected data shapes or make individual
conversion steps idempotent.

## When to Surface

**Trigger:** Starting v1.3 or later, where new read tools depend on adapter reliability

This seed should be presented during `/gsd:new-milestone` when the milestone
scope matches any of these conditions:
- Adding new read tools or query capabilities that flow through the adapter
- Refactoring the bridge/adapter contract or data shape
- Improving test double fidelity or InMemoryBridge accuracy

## Scope Estimate

**Medium** — Needs a phase: rethink the adapter guard logic, update InMemoryBridge
to either pass through the adapter or match its output contract, add regression tests
that catch silent no-op skips.

## Breadcrumbs

Related code and decisions found in the current codebase:

- `src/omnifocus_operator/bridge/adapter.py` — `_adapt_task()` (line 153), `_adapt_parent_ref()`, `_adapt_repetition_rule()`
- `tests/doubles/bridge.py` — InMemoryBridge returns adapted-shape data, bypassing the adapter
- `tests/golden/normalize.py` — golden master normalization (related to data shape expectations)
- `tests/test_bridge_contract.py` — bridge behavioral equivalence tests (Phase 27)

## Notes

Discovered during Phase 27 (repository contract tests for behavioral equivalence).
The root cause is coupling-through-control-flow: `_adapt_parent_ref` has no logical
dependency on the `status` field, but is gated behind the `status` presence check.
Two viable fix strategies:

1. **Fail-fast**: Raise if data has neither `status` nor a known "already adapted" marker
2. **Idempotent steps**: Each sub-conversion checks its own precondition independently
   (e.g., `_adapt_parent_ref` checks if `parent` is already a dict)

Option 2 is more robust — it doesn't require a coordination sentinel and handles
partial adaptation gracefully.
