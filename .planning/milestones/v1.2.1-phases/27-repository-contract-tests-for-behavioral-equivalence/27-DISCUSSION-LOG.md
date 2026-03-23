# Phase 27: Bridge contract tests (golden master) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-21
**Phase:** 27-repository-contract-tests-for-behavioral-equivalence
**Areas discussed:** Scenario coverage, Capture workflow & cleanup, Equivalence granularity

---

## Scenario Coverage

| Option | Description | Selected |
|--------|-------------|----------|
| Full write cycle (Recommended) | get_all shape + add_task read-back + edit_task read-back (fields, tags, lifecycle, move). 4-5 scenarios. Verifies the actual Phase 26 deliverable. | ✓ |
| Read-only baseline | Just get_all snapshot shape. Simpler but doesn't verify write handler equivalence at all. | |

**User's choice:** Full write cycle
**Notes:** User confirmed multiple add_task/edit_task variations with get_all captured between each operation. One-click capture — single command runs everything. The write responses are sparse ({id, name}), so get_all between each step is what provides the real verification value.

---

## Capture Workflow & Cleanup

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated test project (Recommended) | Create tasks in a clearly-named project. No cleanup needed — contained, identifiable, reusable for future re-captures. ~5 tasks permanent footprint. | |
| Write-then-delete | Create test tasks, capture golden master output, then manually delete them. Clean DB but manual cleanup step every time you re-capture. | |

**User's choice:** Hybrid — ephemeral test project (not long-living). Create during capture, user deletes after.
**Notes:** User refined this significantly:
- Script should be interactive and explain what it does before doing it
- Manual setup is step-by-step with verification after each step
- Uses RealBridge (Python class) via existing bridge.js — no new OmniJS scripts
- Never modify existing tasks, never store personal data in golden master
- Test data may be in multiple locations during capture but consolidated at end for single-deletion cleanup
- Golden master refreshed infrequently (when new features are added)
- User initially said "never read existing tasks" but corrected to "never store existing tasks" — get_all reads everything but golden master filters to test-created data only

---

## Equivalence Granularity

| Option | Description | Selected |
|--------|-------------|----------|
| Structural match (Recommended) | Exclude dynamic fields (id, url, added, modified), then exact match on everything else. Catches regressions in all stable fields. normalize_for_comparison() helper handles the exclusion. | ✓ |
| Behavioral match | Assert key invariants only ('task appears', 'tag present'). Less fragile but misses field-level regressions in computed fields like effectiveFlagged, inInbox. | |

**User's choice:** Structural match
**Notes:** None — straightforward selection.

---

## Additional Discussion: Bridge-level vs Repository-level

Major correction raised by user during summary review:

**Original framing (from INFRA-13/14):** Golden master at repository level (BridgeRepository output, Pydantic models)
**Corrected framing:** Golden master at bridge level (InMemoryBridge.send_command() output, raw dicts)

**User's rationale:** InMemoryBridge is the thing replicating OmniFocus behavior. BridgeRepository is just a Python abstraction on top — unit-testable separately. The golden master should capture what RealBridge.send_command() returns and verify InMemoryBridge.send_command() matches. Pure dict-to-dict comparison.

**Action taken:** Updated INFRA-13, INFRA-14, and ROADMAP success criteria SC-1 and SC-3 to say "bridge behavior" and "InMemoryBridge output" instead of "repository behavior" and "BridgeRepository output".

---

## Coverage Level & Exclusions (Assumption Review Session)

**Date:** 2026-03-21 (second session)

Discussed during `/gsd:list-phase-assumptions 27` — Claude surfaced assumptions, user refined:

- **Coverage level:** Pragmatically exhaustive. Every distinct behavior path (individual field edits, tag add/remove, lifecycle, move) but not combinatorial. If a bug only shows when exactly three specific fields change simultaneously, that's an accepted gap.
- **Repetition rules:** Explicitly excluded. Next milestone implements them; golden master gets regenerated then.
- **File format:** Multiple JSON files in a folder, ordered incrementally. Not one monolithic file — easier to maintain and debug.
- **Behavioral mismatch:** User clarified this is the whole point of the phase, not a risk. If InMemoryBridge differs from RealBridge, that's the signal we want.
- **Filtering performance:** Not a concern. ~3,000 tasks filtered in memory is milliseconds.

---

## Future-proofing: Golden Master Maintenance

User raised: how do we ensure future phases update the golden master when adding bridge operations?

| Option | Description | Selected |
|--------|-------------|----------|
| CLAUDE.md rule | Lightweight mention in project instructions | |
| PROJECT.md constraint (GOLD-01) | Named constraint like SAFE-01/02, picked up during phase planning | ✓ |
| CI guardrail | Harder to enforce for manual capture step | |

**User's choice:** PROJECT.md constraint (GOLD-01)
**Notes:** Slots into existing requirements system. Gets picked up naturally during phase planning like SAFE-01/02 do.

---

## Claude's Discretion

- How edit_task sub-behaviors are organized in the scenario sequence
- Exact filtering implementation for get_all
- Exact normalization implementation
- CI contract test organization
- How to consolidate test data at end of capture

## Deferred Ideas

- Repetition rule coverage — deferred to next milestone when repetition rules are implemented
