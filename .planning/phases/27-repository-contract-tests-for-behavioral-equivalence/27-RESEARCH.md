# Phase 27: Bridge contract tests (golden master) - Research

**Researched:** 2026-03-21
**Domain:** Golden master testing pattern, bridge behavioral equivalence
**Confidence:** HIGH

## Summary

This phase creates a golden master capture script (`uat/capture_golden_master.py`) and CI contract tests that prove InMemoryBridge behaves identically to RealBridge. The capture script is human-run, guided, and interactive -- it creates test entities in OmniFocus via RealBridge, records the raw `send_command()` responses and filtered `get_all` snapshots, then writes them as JSON fixture files. CI contract tests replay the same operations against InMemoryBridge and assert structural equivalence after normalizing dynamic fields.

**Critical architectural detail:** RealBridge returns bridge-format dicts (with `status`, `taskStatus`, `project`/`parent` as string IDs), while InMemoryBridge returns post-adapted format (with `urgency`/`availability`, `parent` as dict/None). The normalization layer must account for this format difference -- either by adapting RealBridge output before storing the golden master, or by adapting at comparison time. Adapting before storage (applying `adapt_snapshot` to captured data) is the cleaner approach because it makes golden master files match what tests see downstream.

**Primary recommendation:** Apply `adapt_snapshot()` to RealBridge `get_all` output during capture, so golden master files are in the same format InMemoryBridge produces. Write/response comparisons (add_task/edit_task returns) are already format-aligned ({id, name}).

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Full write cycle -- golden master covers pragmatically exhaustive `add_task` variations, `edit_task` variations (field updates, tag add/remove, lifecycle, move), with `get_all` captured between each operation to track state transitions
- **D-02:** One-click capture -- single `uv run python uat/capture_golden_master.py` command
- **D-03:** Interactive guided flow -- explains upfront, step-by-step manual setup with verification, confirms before executing
- **D-04:** Uses RealBridge (Python class) via existing bridge.js IPC mechanism
- **D-05:** Manual prerequisites -- script guides user to create projects/tags needed for scenarios
- **D-06:** After each manual step, script double-checks that the created entity is found and correct
- **D-07:** Script confirms with user before running the actual capture scenarios
- **D-08:** Never modify existing tasks -- only modify things the script created
- **D-09:** Privacy-safe golden master -- `get_all` reads entire database but only stores test-created data (filtered by known IDs)
- **D-10:** Ephemeral test data -- consolidated under single deletable root at end
- **D-11:** If something fails mid-capture, script clearly reports what was created and where
- **D-12:** `get_all` captured after each write operation, filtered to only test-created entities
- **D-13:** Write responses are sparse ({id, name}), real verification value is in intermediate `get_all` snapshots
- **D-14:** Bridge-level testing -- golden master captures raw dict responses from `RealBridge.send_command()`, CI verifies `InMemoryBridge.send_command()` matches
- **D-15:** Structural match -- exclude dynamic fields (id, url, added, modified), exact match on everything else
- **D-16:** `normalize_for_comparison()` helper strips dynamic fields before diffing
- **D-17:** Filtering mechanism -- script tracks which IDs it created and which projects/tags the user created, filters `get_all` to only those IDs
- **D-18:** Repetition rules excluded -- next milestone, golden master regenerated then
- **D-19:** Golden master files stored as multiple JSON files in a folder, ordered incrementally by scenario number
- **D-20:** Standing project requirement (GOLD-01) -- any phase modifying bridge operations must re-capture and add coverage

### Claude's Discretion
- How edit_task sub-behaviors are organized in the scenario sequence (combined or separate)
- Exact filtering implementation for `get_all`
- Exact normalization implementation
- CI contract test organization (parametrized, separate test functions, etc.)
- How to consolidate test data at end of capture for single-deletion cleanup

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-13 | Golden master of expected bridge behavior captured from RealBridge via UAT and committed to the repo | Capture script design, scenario coverage, fixture format, filtering mechanism |
| INFRA-14 | CI contract tests verify InMemoryBridge output matches the committed golden master | Contract test pattern, normalization helper, parametrized test structure |

</phase_requirements>

## Architecture Patterns

### Format Gap Between RealBridge and InMemoryBridge

The single most important technical detail for this phase:

| Aspect | RealBridge `get_all` output | InMemoryBridge `get_all` output |
|--------|----------------------------|--------------------------------|
| Task status | `"status": "Available"` | `"urgency": "none", "availability": "available"` |
| Project status | `"status": "Active", "taskStatus": "Available"` | `"urgency": "none", "availability": "available"` |
| Tag status | `"status": "Active"` | `"availability": "available"` |
| Folder status | `"status": "Active"` | `"availability": "available"` |
| Task parent | `"project": "id", "parent": "id"` (string IDs) | `"parent": {"type": "project", "id": "...", "name": "..."} or null` |
| Dead fields | Present (`active`, `effectiveActive`, etc.) | Absent |

**Resolution:** Apply `adapt_snapshot()` to RealBridge `get_all` output during capture. This transforms the bridge-format into the model-format that InMemoryBridge already produces. The golden master files then represent the canonical "what the system should produce" format.

**Write responses are already aligned:** Both bridges return `{id: str, name: str}` for add_task and edit_task.

### Recommended File Structure

```
tests/
  golden/                        # Golden master fixture directory
    README.md                    # Documents what's here and how to regenerate
    scenario_01_add_inbox.json   # First scenario
    scenario_02_add_parent.json  # Second scenario
    ...
  test_bridge_contract.py        # CI contract tests
uat/
  capture_golden_master.py       # Interactive capture script
```

### Golden Master Fixture Format

Each scenario file captures one operation and its resulting state:

```json
{
  "scenario": "01_add_inbox_task",
  "description": "Create a basic task in inbox with no optional fields",
  "operation": "add_task",
  "params": {
    "name": "GM-InboxTask"
  },
  "response": {
    "name": "GM-InboxTask"
  },
  "state_after": {
    "tasks": [
      {
        "name": "GM-InboxTask",
        "note": "",
        "urgency": "none",
        "availability": "available",
        "flagged": false,
        "effectiveFlagged": false,
        "dueDate": null,
        "deferDate": null,
        "inInbox": true,
        "parent": null,
        "tags": [],
        "hasChildren": false,
        "estimatedMinutes": null
      }
    ],
    "projects": [],
    "tags": []
  }
}
```

Key properties:
- `response` has `id` stripped (dynamic)
- `state_after` is filtered to test-created entities only, with dynamic fields stripped
- Each file is self-contained -- includes the operation that produced this state

### Dynamic Fields to Strip (D-15)

For tasks:
- `id` -- generated by OmniFocus, different per run
- `url` -- contains the ID
- `added` -- timestamp of creation
- `modified` -- timestamp of last modification
- `effectiveDueDate`, `effectiveDeferDate`, `effectiveCompletionDate`, `effectivePlannedDate`, `effectiveDropDate` -- computed by OmniFocus, may differ from set values
- `repetitionRule` -- excluded per D-18

For write responses:
- `id` -- generated by OmniFocus

### Normalization Helper

```python
# Conceptual shape -- exact implementation at Claude's discretion

DYNAMIC_TASK_FIELDS = {
    "id", "url", "added", "modified",
    "effectiveDueDate", "effectiveDeferDate",
    "effectiveCompletionDate", "effectivePlannedDate",
    "effectiveDropDate", "repetitionRule",
}

DYNAMIC_PROJECT_FIELDS = {"id", "url", "added", "modified", ...}
DYNAMIC_TAG_FIELDS = {"id", "url", "added", "modified"}

def normalize_for_comparison(data: dict, entity_type: str) -> dict:
    """Strip dynamic fields from an entity dict for comparison."""
    fields = DYNAMIC_FIELDS_BY_TYPE[entity_type]
    return {k: v for k, v in data.items() if k not in fields}
```

### Contract Test Pattern

```python
# tests/test_bridge_contract.py
import json
import pytest
from pathlib import Path
from tests.doubles import InMemoryBridge
from tests.conftest import make_snapshot_dict, make_project_dict, make_tag_dict

GOLDEN_DIR = Path(__file__).parent / "golden"

def load_scenarios() -> list[dict]:
    """Load all golden master scenario files in order."""
    files = sorted(GOLDEN_DIR.glob("scenario_*.json"))
    return [json.loads(f.read_text()) for f in files]

class TestBridgeContract:
    """Verify InMemoryBridge matches golden master from RealBridge."""

    async def test_all_scenarios_match(self):
        """Replay all golden master scenarios against InMemoryBridge."""
        # Seed bridge with same initial state the capture had
        bridge = InMemoryBridge(data=initial_state())

        for scenario in load_scenarios():
            response = await bridge.send_command(
                scenario["operation"],
                scenario["params"],
            )

            # Compare write response (strip dynamic)
            normalized_response = normalize_response(response)
            assert normalized_response == scenario["response"]

            # Compare state snapshot (strip dynamic)
            state = await bridge.send_command("get_all")
            filtered = filter_to_known_ids(state)
            normalized = normalize_state(filtered)
            assert normalized == scenario["state_after"]
```

The exact organization (one big sequential test vs parametrized per-scenario) is at Claude's discretion per CONTEXT.md. A sequential test is natural here because state accumulates across scenarios.

### Capture Script Architecture

```
uat/capture_golden_master.py

Phase 1: Introduction
  - Print banner, explain what will happen
  - Explain prerequisites (OmniFocus running)

Phase 2: Manual Setup (interactive)
  - Guide user to create test project(s) and tag(s) in OmniFocus
  - After each creation, verify via get_all that entity exists
  - Record project/tag IDs from verification

Phase 3: Confirmation
  - Show scenario list, ask user to confirm before proceeding

Phase 4: Capture (automated, sequential)
  For each scenario:
    1. send_command(operation, params) -> record response
    2. send_command("get_all") -> adapt_snapshot -> filter to known IDs -> record state
    3. Normalize (strip dynamic fields)
    4. Write scenario JSON file

Phase 5: Consolidation
  - Move all test-created tasks under a single parent for easy deletion
  - Report what was created and where
  - Tell user to delete the consolidation parent

Phase 6: Error handling
  - If any step fails, report what was created and where
  - User can always clean up manually
```

### ID Tracking and Filtering (D-17)

The capture script maintains two sets of IDs:

1. **User-created IDs:** Projects and tags the user creates during setup. Discovered via `get_all` after user confirms creation.
2. **Script-created IDs:** Task IDs from `add_task` responses. Accumulated during capture.

Filtering `get_all` output:
```python
def filter_to_known_ids(raw: dict, known_task_ids: set, known_project_ids: set, known_tag_ids: set) -> dict:
    return {
        "tasks": [t for t in raw["tasks"] if t["id"] in known_task_ids],
        "projects": [p for p in raw["projects"] if p["id"] in known_project_ids],
        "tags": [g for g in raw["tags"] if g["id"] in known_tag_ids],
    }
```

### Cleanup Consolidation (D-10)

At the end of capture, consolidate all test tasks under a single parent project:
1. Create a cleanup project (e.g., "DELETE-AFTER-GOLDEN-MASTER") or use `edit_task` + `moveTo` to move everything under one existing test project
2. Tell the user: "Delete the project 'DELETE-AFTER-GOLDEN-MASTER' to clean up all test data"

Alternative: move all test tasks under the test project the user created during setup. Either way, one deletion cleans everything.

## Scenario Coverage Design (D-01)

Based on the bridge operations and InMemoryBridge handlers:

### add_task scenarios
1. **Basic inbox task** -- name only, no parent, no optional fields
2. **Task with parent (project)** -- name + parent pointing to a project
3. **Task with all fields** -- name, parent, flagged, dueDate, deferDate, plannedDate, estimatedMinutes, note
4. **Task with tags** -- name + tagIds (requires tags to exist)

### edit_task scenarios
5. **Edit name** -- change task name
6. **Edit note** -- set note on a task
7. **Edit flagged** -- set flagged=true, verify effectiveFlagged syncs
8. **Edit dates** -- set dueDate, deferDate, plannedDate
9. **Clear dates** -- set dueDate=null, verify cleared
10. **Edit estimatedMinutes** -- set and clear
11. **Add tags** -- addTagIds to a task
12. **Remove tags** -- removeTagIds from a task
13. **Replace tags** -- remove + add in single operation
14. **Lifecycle complete** -- lifecycle="complete", verify availability="completed"
15. **Lifecycle drop** -- lifecycle="drop", verify availability="dropped"
16. **Move to project** -- moveTo with containerId pointing to project
17. **Move to inbox** -- moveTo with containerId=null

### Observation
Each scenario builds on accumulated state. The contract test replays them in order, so InMemoryBridge state accumulates the same way.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bridge output adaptation | Custom format translation in golden master | `adapt_snapshot()` from `bridge.adapter` | Already handles all entity type transformations, battle-tested |
| Test factories | New fixture builders | `make_snapshot_dict()`, `make_task_dict()`, etc. from `tests/conftest.py` | Consistent with rest of test suite |
| JSON comparison | Custom diff logic | Standard `==` after normalization | Dict equality is sufficient after stripping dynamic fields |
| RealBridge creation | Custom bridge setup | `RealBridge(ipc_dir=DEFAULT_IPC_DIR)` pattern from existing UAT | Already proven in `uat/test_read_only.py` |

## Common Pitfalls

### Pitfall 1: Format Mismatch Between Bridges
**What goes wrong:** RealBridge returns `status`-based format, InMemoryBridge returns `urgency`/`availability`-based format. Direct comparison fails on every entity.
**Why it happens:** The adapter (`adapt_snapshot`) runs in BridgeRepository, not in the bridge itself.
**How to avoid:** Apply `adapt_snapshot()` to RealBridge `get_all` output during golden master capture. Golden master files store adapted format.
**Warning signs:** Every `get_all` comparison fails with key mismatches (`status` vs `urgency`/`availability`).

### Pitfall 2: Parent Format Mismatch
**What goes wrong:** RealBridge returns `"project": "id-string", "parent": "id-string"` as separate fields. InMemoryBridge returns `"parent": {"type": "project", "id": "...", "name": "..."}` or `null`.
**Why it happens:** The adapter's `_adapt_parent_ref()` merges project/parent into unified parent dict.
**How to avoid:** `adapt_snapshot()` handles this transformation. Same fix as Pitfall 1.
**Warning signs:** Parent-related assertions fail, InMemoryBridge has `parent` as dict while golden master has it as string.

### Pitfall 3: effectiveFlagged on InMemoryBridge
**What goes wrong:** InMemoryBridge sets `effectiveFlagged = flagged` directly. RealBridge (OmniFocus) computes effectiveFlagged based on inheritance (parent project flagged propagates down).
**Why it happens:** InMemoryBridge is a simplified simulation without inheritance.
**How to avoid:** For golden master scenarios, don't test inherited flag scenarios (no parent with flagged=true and child checking effectiveFlagged). Only test direct flagged setting.
**Warning signs:** effectiveFlagged differs when a task is under a flagged project.

### Pitfall 4: Tag Names in InMemoryBridge
**What goes wrong:** InMemoryBridge's `_handle_edit_task` sets tag name = tag ID when adding tags (`task["tags"].append({"id": tid, "name": tid})`). RealBridge returns actual tag names from OmniFocus.
**Why it happens:** InMemoryBridge doesn't resolve tag names from its internal tag store.
**How to avoid:** This is a real behavioral gap that the golden master should surface. The normalization may need to handle tag names specially, or this should be documented as a known limitation / something to fix in InMemoryBridge.
**Warning signs:** Tag names in `get_all` differ between golden master and InMemoryBridge output.

### Pitfall 5: PYTEST_CURRENT_TEST Guard
**What goes wrong:** Trying to instantiate RealBridge in a test file fails because `PYTEST_CURRENT_TEST` is set.
**Why it happens:** SAFE-01 guard in `RealBridge.__init__`.
**How to avoid:** The capture script is a UAT script in `uat/`, not a pytest test. It runs via `uv run python uat/capture_golden_master.py`, not pytest. The CI contract tests only use InMemoryBridge.
**Warning signs:** RuntimeError about PYTEST_CURRENT_TEST when running capture.

### Pitfall 6: OmniFocus Computed Fields
**What goes wrong:** Fields like `effectiveDueDate` are computed by OmniFocus based on inheritance. InMemoryBridge doesn't simulate inheritance, so these values may differ.
**How to avoid:** Strip all `effective*` fields in normalization (already in dynamic fields list per D-15). Only compare directly-set values.
**Warning signs:** Effective date fields mismatch.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x with pytest-asyncio |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_bridge_contract.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-13 | Golden master captured from RealBridge | manual (UAT) | `uv run python uat/capture_golden_master.py` | No -- Wave 0 |
| INFRA-14 | CI contract tests verify InMemoryBridge matches golden master | unit | `uv run pytest tests/test_bridge_contract.py -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_bridge_contract.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/golden/` directory -- golden master fixture files (created by capture script)
- [ ] `tests/test_bridge_contract.py` -- CI contract tests
- [ ] `uat/capture_golden_master.py` -- interactive capture script

## Code Examples

### Capture Script Entry Point Pattern (from existing UAT)
```python
# Source: uat/test_read_only.py
from omnifocus_operator.bridge._real import DEFAULT_IPC_DIR, RealBridge

bridge = RealBridge(ipc_dir=DEFAULT_IPC_DIR)
raw = await bridge.send_command("get_all")
```

### Applying adapt_snapshot to RealBridge Output
```python
# Source: src/omnifocus_operator/repository/bridge.py (line 136)
from omnifocus_operator.bridge.adapter import adapt_snapshot

raw = await bridge.send_command("get_all")
adapt_snapshot(raw)  # Mutates in-place: status -> urgency/availability, parent ref unification
```

### InMemoryBridge Seeding Pattern (for contract tests)
```python
# Source: tests/conftest.py (bridge fixture)
from tests.doubles import InMemoryBridge
from tests.conftest import make_snapshot_dict, make_project_dict, make_tag_dict

# Seed with the same projects/tags the capture script's manual setup created
bridge = InMemoryBridge(data={
    "tasks": [],
    "projects": [make_project_dict(id="gm-proj", name="GM-TestProject")],
    "tags": [make_tag_dict(id="gm-tag-1", name="GM-Tag1"), make_tag_dict(id="gm-tag-2", name="GM-Tag2")],
    "folders": [],
    "perspectives": [],
})
```

### moveTo Params Shape (from bridge.js)
```python
# Source: src/omnifocus_operator/bridge/bridge.js (handleEditTask, line 291-313)
# The bridge receives moveTo as: {position, containerId?, anchorId?}
# But InMemoryBridge receives it as: {containerId} (simplified)
# This is a known gap -- InMemoryBridge's _handle_edit_task only processes containerId
```

### Interactive Input Pattern (for capture script)
```python
# Standard Python input() for guided walkthrough
input("\nPlease create a project named 'GM-TestProject' in OmniFocus.\nPress Enter when done...")

# Verify via bridge
raw = await bridge.send_command("get_all")
adapt_snapshot(raw)
projects = [p for p in raw["projects"] if p["name"] == "GM-TestProject"]
if not projects:
    print("ERROR: Project 'GM-TestProject' not found. Please try again.")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| InMemoryRepository (model-level simulation) | InMemoryBridge (dict-level simulation) | Phase 26 (2026-03-21) | Bridge-level testing is now possible |
| No behavioral equivalence proof | Golden master + contract tests | Phase 27 (this phase) | Confidence that test double matches reality |

## Open Questions

1. **moveTo Simplification in InMemoryBridge**
   - What we know: InMemoryBridge's `_handle_edit_task` only reads `moveTo.containerId`. RealBridge (via bridge.js) uses `moveTo.position` and `moveTo.anchorId` for before/after positioning.
   - What's unclear: Should the golden master test all 5 move modes, or only the subset InMemoryBridge supports (beginning/ending to container/inbox)?
   - Recommendation: Test only `containerId`-based moves (to project, to inbox). The golden master proves behavioral equivalence for what InMemoryBridge simulates. Before/after positioning can be added when InMemoryBridge supports it.

2. **Tag Name Resolution Gap**
   - What we know: InMemoryBridge uses tag ID as name when adding tags via edit_task. RealBridge returns actual tag names from OmniFocus.
   - What's unclear: Should this be fixed in InMemoryBridge before golden master capture, or should normalization strip tag names?
   - Recommendation: Fix InMemoryBridge to resolve tag names from its internal `_tags` list (3-line fix). This is a real behavioral gap the golden master should catch, and fixing it makes InMemoryBridge more faithful.

3. **Initial State Seeding for Contract Tests**
   - What we know: The capture script starts with user-created projects/tags. The CI test must seed InMemoryBridge with equivalent initial state.
   - What's unclear: How to store and load the initial state. Should it be a separate fixture file or inline in the test?
   - Recommendation: Store as `tests/golden/initial_state.json` alongside scenario files. The capture script writes it after manual setup verification. Contract test loads and uses it to seed InMemoryBridge.

## Sources

### Primary (HIGH confidence)
- `src/omnifocus_operator/bridge/bridge.js` -- bridge operations, response shapes, field lists
- `src/omnifocus_operator/bridge/adapter.py` -- format transformation between bridge and model
- `tests/doubles/bridge.py` -- InMemoryBridge implementation, handlers, format
- `src/omnifocus_operator/bridge/real.py` -- RealBridge implementation, SAFE-01 guard
- `uat/test_read_only.py` -- existing UAT pattern for RealBridge usage
- `tests/conftest.py` -- factory functions, fixture composition pattern

### Secondary (MEDIUM confidence)
- `tests/test_stateful_bridge.py` -- InMemoryBridge behavioral tests (Phase 26)
- `.planning/phases/26-replace-inmemoryrepository-with-stateful-inmemorybridge/26-CONTEXT.md` -- Phase 26 decisions on InMemoryBridge design

## Metadata

**Confidence breakdown:**
- Architecture: HIGH -- well-understood codebase, clear bridge protocol, format gap identified and resolved
- Pitfalls: HIGH -- all based on direct code inspection of both bridge implementations
- Scenario coverage: HIGH -- derived from bridge.js operations and InMemoryBridge handlers

**Research date:** 2026-03-21
**Valid until:** 2026-04-21 (stable internal infrastructure, no external deps)
