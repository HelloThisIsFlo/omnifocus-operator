# Phase 27: Bridge contract tests (golden master) - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Golden master pattern proves behavioral equivalence between InMemoryBridge and RealBridge at the Bridge protocol level (`send_command() → dict`). UAT captures what OmniFocus actually does via RealBridge, CI verifies InMemoryBridge produces matching output. No new tools, no behavioral changes — pure test infrastructure.

</domain>

<decisions>
## Implementation Decisions

### Scenario coverage
- **D-01:** Full write cycle — golden master covers pragmatically exhaustive `add_task` variations, `edit_task` variations (field updates, tag add/remove, lifecycle, move), with `get_all` captured between each operation to track state transitions. Every distinct behavior path is covered; combinatorial explosion is not.
- **D-02:** One-click capture — single `uv run python uat/capture_golden_master.py` command runs all scenarios and writes all fixture files
- **D-18:** Repetition rules excluded — next milestone implements repetition rules; golden master gets regenerated at that point to include them
- **D-19:** Golden master files stored as multiple JSON files in a folder, ordered incrementally by scenario number. Easier to maintain and debug than one monolithic file.

### Capture workflow
- **D-03:** Interactive guided flow — script explains what it does upfront, step-by-step manual setup with verification after each step, confirms with user before executing the capture
- **D-04:** Uses RealBridge (Python class) — communicates with OmniFocus via existing bridge.js IPC mechanism. No new OmniJS scripts. Each `send_command()` goes through the existing bridge
- **D-05:** Manual prerequisites — script guides user to create projects/tags needed for scenarios (e.g., "Please create a project named 'X'. Press Enter when done."), then verifies each one exists via bridge before proceeding
- **D-06:** After each manual step, script double-checks that the created entity is found and correct
- **D-07:** Script confirms with user before running the actual capture scenarios

### Data safety
- **D-08:** Never modify existing tasks — only modify things the script created
- **D-09:** Privacy-safe golden master — `get_all` necessarily reads the entire database, but the golden master only stores test-created data (filtered by known IDs). Public repo = no personal task names
- **D-10:** Ephemeral test data — during capture, test data may exist in multiple locations (inbox, different projects, moved around). At the end, script consolidates everything under a single deletable root so user can delete one thing to clean up
- **D-11:** If something fails mid-capture, script clearly reports what was created and where so the user can clean up

### State snapshots
- **D-12:** `get_all` captured after each write operation, filtered to only test-created entities. Golden master is a sequence of (operation → sparse response → filtered state snapshot) tuples
- **D-13:** The write responses are sparse (`{id, name}`), so the real verification value is in the intermediate `get_all` snapshots showing how state changes after each operation

### Equivalence granularity
- **D-14:** Bridge-level testing — golden master captures raw dict responses from `RealBridge.send_command()`, CI verifies `InMemoryBridge.send_command()` matches. No BridgeRepository or Pydantic in the comparison path
- **D-15:** Structural match — exclude dynamic fields (`id`, `url`, `added`, `modified`), exact match on everything else
- **D-16:** `normalize_for_comparison()` helper strips dynamic fields before diffing golden master vs InMemoryBridge output
- **D-17:** Filtering mechanism — script tracks which IDs it created (from `add_task` responses) and which projects/tags the user created (from verification step), filters `get_all` to only those IDs

### Future-proofing
- **D-20:** Standing project requirement (GOLD-01): any phase that adds or modifies bridge operations must re-capture the golden master and add contract test coverage for the new behavior. Added to PROJECT.md constraints.

### Claude's Discretion
- How edit_task sub-behaviors are organized in the scenario sequence (combined or separate)
- Exact filtering implementation for `get_all`
- Exact normalization implementation
- CI contract test organization (parametrized, separate test functions, etc.)
- How to consolidate test data at end of capture for single-deletion cleanup

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — INFRA-13 (golden master captured from RealBridge), INFRA-14 (CI contract tests verify InMemoryBridge matches)

### Bridge protocol
- `src/omnifocus_operator/contracts/protocols.py` — Bridge protocol: `send_command(operation, params) -> dict`
- `src/omnifocus_operator/bridge/real.py` — RealBridge implementation (file-based IPC via bridge.js)

### InMemoryBridge (the thing being verified)
- `tests/doubles/bridge.py` — Stateful InMemoryBridge with `_handle_add_task`, `_handle_edit_task`, `_handle_get_all`

### Existing UAT patterns
- `uat/test_read_only.py` — Existing UAT pattern: creates RealBridge, runs operations, validates output
- `uat/README.md` — UAT safety posture (human-only, never CI/agent)

### Prior phase decisions
- `.planning/phases/26-replace-inmemoryrepository-with-stateful-inmemorybridge/26-CONTEXT.md` — D-05 (full behavioral parity), D-10 (Phase 27 validates parity claim)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `RealBridge` (`src/omnifocus_operator/bridge/real.py`): The capture script creates an instance and calls `send_command()` — no new bridge code needed
- `make_task_dict()` / `make_snapshot_dict()` (`tests/conftest.py`): Could inform how golden master fixtures are structured
- `BridgeCall` dataclass (`tests/doubles/bridge.py`): Records operation + params — similar structure to golden master scenarios

### Established Patterns
- UAT scripts in `uat/` are standalone Python scripts, human-run, using `RealBridge` directly
- `InMemoryBridge.send_command()` dispatches to `_handle_get_all`, `_handle_add_task`, `_handle_edit_task` — exact same operations the golden master captures
- Bridge protocol is pure dict-in/dict-out — comparison is straightforward

### Integration Points
- `uat/capture_golden_master.py` — new capture script
- `tests/golden/` (or similar) — golden master fixture files
- `tests/test_bridge_contract.py` (or similar) — CI contract tests comparing InMemoryBridge against golden master

</code_context>

<specifics>
## Specific Ideas

- User wants the capture to feel like a guided walkthrough: "step 1, step 2, verify, confirm, go"
- The golden master is refreshed infrequently — only when new features are added (every few weeks/days)
- Everything consolidated at end for one-delete cleanup — even if during capture tasks are scattered across inbox/projects

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 27-repository-contract-tests-for-behavioral-equivalence*
*Context gathered: 2026-03-21*
