# Phase 28: Expand golden master coverage and normalize lifecycle date fields - Research

**Researched:** 2026-03-22
**Domain:** Test infrastructure (golden master contract tests, InMemoryBridge behavioral parity)
**Confidence:** HIGH

## Summary

This phase expands the golden master from 20 to ~42 scenarios, reorganizes fixtures into numbered subfolders, graduates 9 fields from VOLATILE/UNCOMPUTED to verified, and adds ancestor-chain inheritance to InMemoryBridge. All work is internal test infrastructure -- no MCP tool changes, no behavioral changes.

The codebase is well-understood: the capture script, contract test, normalization module, and InMemoryBridge are all relatively small files with clear patterns. The primary risk is OmniFocus behavioral surprises during capture (e.g., anchor-based move responses, inheritance edge cases for deep nesting). Plan 2 (interactive triage) exists specifically to handle this.

**Primary recommendation:** Structure Plan 1 as three sequential waves: (1) subfolder reorganization + contract test discovery update, (2) capture script rewrite with all ~42 scenarios, (3) normalization changes (field graduation + presence-check). Keep each wave independently committable.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Full reorganization into numbered subfolders: `01-add/`, `02-edit/`, `03-move/`, `04-tags/`, `05-lifecycle/`, `06-combined/`, `07-inheritance/`. Alphabetical sort = execution order.
- **D-02:** Scenarios within each folder numbered sequentially (01, 02, ...).
- **D-03:** Full re-capture of ALL scenarios (existing 20 renumbered + new + inheritance = ~42 total). Clean slate.
- **D-04:** Manual setup extended with `GM-TestProject2` and `GM-TestProject-Dated` (3 projects total).
- **D-05:** Anchor tasks created by earlier add/ scenarios, reused by 03-move/ via ID tracking.
- **D-06:** Projects and tags persist across captures.
- **D-07:** All tasks consolidated under `GM-Cleanup` inbox task at end.
- **D-08 through D-13:** Field graduation plan (completionDate, dropDate, effective* fields, repetitionRule). Status/taskStatus remain UNCOMPUTED.
- **D-14 through D-16:** InMemoryBridge gets `_compute_effective_field()` helper (~15 lines) and `effectiveFlagged` boolean OR variant.
- **D-17 through D-19:** Plan 1 = agent work (script + infra + normalization), human checkpoint for capture, Plan 2 = interactive triage session.

### Claude's Discretion
- Exact fixture JSON structure (fields, metadata per scenario)
- Contract test parametrization approach (subfolder discovery/iteration)
- How much capture script to reuse vs rewrite
- Whether inheritance helper is standalone method or integrated into handlers
- Grouping of InMemoryBridge fixes (per category or per fix)

### Deferred Ideas (OUT OF SCOPE)
- Status field graduation (status, taskStatus remain UNCOMPUTED)
- Milestone closure (handled separately)

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GOLD-01 | Scenarios reorganized into numbered subfolders with ~43 scenarios | Subfolder layout defined in D-01/D-02, scenario list in CONTEXT.md. Contract test discovers via `sorted(SNAPSHOTS_DIR.iterdir())` then `sorted(subfolder.glob("*.json"))`. |
| GOLD-02 | Capture script rewritten for new folder structure with extended prerequisites | 3 projects + 2 tags in setup. Script rewritten with ~42 scenario defs across 7 categories. ID tracking extended for anchor-based moves. |
| GOLD-03 | Contract tests discover and replay in subfolder sort order without manifest | Current `_load_scenarios()` uses `sorted(glob("scenario_*.json"))`. Replace with recursive subfolder discovery: `sorted(SNAPSHOTS_DIR.iterdir())` for folders, `sorted(folder.glob("*.json"))` for scenarios within. |
| NORM-01 | completionDate/dropDate verified via presence-check normalization | Move from VOLATILE to presence-check: non-null values normalized to `"<set>"` sentinel in `normalize_for_comparison()`. |
| NORM-02 | effectiveCompletionDate/effectiveDropDate via presence-check | Same sentinel pattern as NORM-01. Remove from UNCOMPUTED_TASK_FIELDS. |
| NORM-03 | effectiveFlagged/effectiveDueDate/effectiveDeferDate/effectivePlannedDate via exact match | Remove from UNCOMPUTED_TASK_FIELDS. InMemoryBridge computes via `_compute_effective_field()` ancestor chain walk. |
| NORM-04 | repetitionRule verified via exact match (null) | Remove from UNCOMPUTED_TASK_FIELDS. All tasks have null; InMemoryBridge returns null. Catches accidental non-null regressions. |

</phase_requirements>

## Architecture Patterns

### Current Snapshot Layout (being replaced)
```
tests/golden_master/snapshots/
  initial_state.json
  scenario_01_add_inbox_task.json
  scenario_02_add_task_with_parent.json
  ...
  scenario_20_combined_edit.json
```

### New Subfolder Layout (D-01/D-02)
```
tests/golden_master/snapshots/
  initial_state.json
  01-add/
    01_inbox_task.json
    02_with_parent.json
    03_all_fields.json
    04_with_tags.json
    05_parent_and_tags.json
    06_max_payload.json
  02-edit/
    01_rename.json
    ...
    11_set_clear_planned_date.json
  03-move/
    01_to_project_ending.json
    ...
    07_task_as_parent.json
  04-tags/
    01_add_tags.json
    ...
    05_remove_absent_tag.json
  05-lifecycle/
    01_complete.json
    ...
    04_clear_defer_date_available.json
  06-combined/
    01_fields_and_move.json
    02_fields_and_lifecycle.json
    03_subtask_add_and_move_out.json
  07-inheritance/
    01_effective_due_date.json
    ...
    05_deep_nesting.json
```

### Pattern 1: Subfolder Discovery in Contract Test
**What:** Replace flat `glob("scenario_*.json")` with two-level directory walk
**When:** Contract test parametrization and replay
**Example:**
```python
# Source: derived from current _load_scenarios() pattern
def _load_scenarios() -> list[dict[str, Any]]:
    """Load scenarios from numbered subfolders in sort order."""
    files = sorted(SNAPSHOTS_DIR.glob("scenario_*.json"))  # old flat format
    if not files:
        # Try subfolder format
        scenarios: list[dict[str, Any]] = []
        for subfolder in sorted(SNAPSHOTS_DIR.iterdir()):
            if subfolder.is_dir():
                for f in sorted(subfolder.glob("*.json")):
                    scenarios.append(json.loads(f.read_text(encoding="utf-8")))
        if not scenarios:
            pytest.skip(SKIP_MSG)
        return scenarios
    return [json.loads(f.read_text(encoding="utf-8")) for f in files]
```

### Pattern 2: Presence-Check Normalization
**What:** Replace strip-field with sentinel normalization for timestamp fields
**When:** Fields where null-vs-non-null is deterministic but exact value isn't
**Example:**
```python
# Source: derived from normalize.py pattern + todo description
PRESENCE_CHECK_FIELDS: dict[str, set[str]] = {
    "task": {"completionDate", "dropDate", "effectiveCompletionDate", "effectiveDropDate"},
}

def normalize_for_comparison(entity: dict[str, Any], entity_type: str) -> dict[str, Any]:
    fields_to_strip = _DYNAMIC_FIELDS_BY_TYPE.get(entity_type, set())
    presence_fields = PRESENCE_CHECK_FIELDS.get(entity_type, set())
    result = {}
    for k, v in entity.items():
        if k in fields_to_strip:
            continue
        if k in presence_fields:
            result[k] = "<set>" if v is not None else None
        else:
            result[k] = v
    return result
```

### Pattern 3: Ancestor-Chain Inheritance (InMemoryBridge)
**What:** Walk task parent chain to find first non-null value for effective fields
**When:** Computing effectiveDueDate, effectiveDeferDate, effectivePlannedDate, effectiveFlagged
**Example:**
```python
# Source: modeled on existing _find_containing_project_raw pattern
def _compute_effective_field(self, task: dict[str, Any], field: str) -> Any:
    """Walk ancestor chain (parent tasks -> project), return first non-null value."""
    if task.get(field) is not None:
        return task[field]
    task_index = {t["id"]: t for t in self._tasks}
    project_index = {p["id"]: p for p in self._projects}
    current_id = task.get("parent")
    visited: set[str] = set()
    while current_id is not None and current_id not in visited:
        visited.add(current_id)
        if current_id in project_index:
            return project_index[current_id].get(field)
        parent_task = task_index.get(current_id)
        if parent_task is None:
            return None
        if parent_task.get(field) is not None:
            return parent_task[field]
        current_id = parent_task.get("parent")
    return None

def _compute_effective_flagged(self, task: dict[str, Any]) -> bool:
    """Boolean OR: true if task or any ancestor is flagged."""
    if task.get("flagged", False):
        return True
    task_index = {t["id"]: t for t in self._tasks}
    project_index = {p["id"]: p for p in self._projects}
    current_id = task.get("parent")
    visited: set[str] = set()
    while current_id is not None and current_id not in visited:
        visited.add(current_id)
        if current_id in project_index:
            return project_index[current_id].get("flagged", False)
        parent_task = task_index.get(current_id)
        if parent_task is None:
            return False
        if parent_task.get("flagged", False):
            return True
        current_id = parent_task.get("parent")
    return False
```

### Pattern 4: Capture Script Scenario with Setup and ID Tracking
**What:** Scenarios that need a task created first (setup_operation), then the main operation
**When:** Any edit/move/lifecycle scenario that needs a target task
**Current implementation in capture script:**
```python
# Source: uat/capture_golden_master.py (existing followup pattern)
{
    "scenario": "15_lifecycle_drop",
    "operation": "add_task",          # setup: create the task
    "params": {"name": "GM-DropTarget"},
    "capture_id_as": "drop_target",
    "followup": {
        "operation": "edit_task",     # main: drop it
        "params_fn": lambda: {"id": TASK_IDS["drop_target"], "lifecycle": "drop"},
    },
}
```
The new script needs to extend this pattern for anchor-based moves where `anchorId` references a previously-created task.

### Anti-Patterns to Avoid
- **Manifest files for ordering:** Filesystem sort order is the manifest (D-01). No JSON/YAML manifest file.
- **Incremental fixture addition:** D-03 mandates full re-capture. Don't try to add new fixtures alongside old ones.
- **Normalizing `status`/`taskStatus`:** These remain UNCOMPUTED (D-13). Don't graduate them.
- **Computing effective fields in normalize.py:** Normalization strips/sentinelizes. Effective field computation belongs in InMemoryBridge, not the normalizer.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fixture ordering | Manifest file or config | Filesystem sort (`sorted(iterdir())`) | D-01: numbered prefixes encode order. Adding a manifest is redundant state. |
| Presence-check comparison | Custom diff logic | Sentinel normalization (`"<set>"`) + existing `==` comparison | Reuse existing normalize/compare pipeline. The sentinel transforms the problem into exact-match. |
| Parent chain walk | New traversal abstraction | Extend existing `_find_containing_project_raw` pattern | Same loop shape -- walk parent refs, check task_index then project_index. |

## Common Pitfalls

### Pitfall 1: ID Remapping for Anchor Moves
**What goes wrong:** Anchor-based moves (`before`/`after`) reference task IDs that differ between golden master and InMemoryBridge. `_remap_ids()` currently handles `id`, `parent`, and `moveTo.containerId` but NOT `moveTo.anchorId`.
**Why it happens:** Phase 27 only had container-based moves.
**How to avoid:** Extend `_remap_ids()` to also check `moveTo.anchorId` in `id_map`.
**Warning signs:** Anchor move scenarios fail with "task not found" in contract tests.

### Pitfall 2: Scenario Ordering Dependencies
**What goes wrong:** Inheritance scenarios (07-*) need tasks under `GM-TestProject-Dated`. If capture script doesn't create the right parent relationships BEFORE the inheritance scenarios, the effective fields won't inherit.
**Why it happens:** The dated project must be set up with dueDate/deferDate/flagged BEFORE tasks are added under it. But it's a manual setup entity (D-04), so the setup phase must verify its field values.
**How to avoid:** Verify `GM-TestProject-Dated` has correct dueDate, deferDate, flagged=true in the manual setup phase. Provide clear instructions.
**Warning signs:** effectiveDueDate/effectiveDeferDate show as null in inheritance scenario fixtures.

### Pitfall 3: Effective Field Timing in InMemoryBridge
**What goes wrong:** `_handle_add_task` sets `effectiveFlagged` from `params.get("flagged", False)` directly, ignoring parent's flag state. After this phase, it needs to check the ancestor chain too.
**Why it happens:** Current InMemoryBridge only computes effective fields for the task itself, not inherited from parent.
**How to avoid:** Call `_compute_effective_flagged()` and `_compute_effective_field()` in both `_handle_add_task` (after parent is set) and `_handle_edit_task` (after move or field change).
**Warning signs:** Tasks under flagged projects show `effectiveFlagged: false`.

### Pitfall 4: Normalization Must Apply to Both Golden Master and InMemoryBridge State
**What goes wrong:** `normalize_for_comparison()` is called on `state_after` (golden master side) but also on `filter_to_known_ids(state)` (InMemoryBridge side). The presence-check sentinel must produce the same result regardless of which side's timestamp differs.
**Why it happens:** Both sides go through `normalize_state()` which calls `normalize_for_comparison()`. This is correct by design -- just verify both paths exercise the same normalization.
**How to avoid:** No special action needed -- the architecture already normalizes both sides symmetrically. Just verify the presence-check fields are NOT in VOLATILE (so they aren't stripped before sentinelization).
**Warning signs:** Asymmetric handling: one side strips, the other sentinelizes.

### Pitfall 5: Contract Test Backward Compatibility During Transition
**What goes wrong:** Between Plan 1 (rewrite infra) and the human checkpoint (capture), the golden master directory has the OLD flat layout but the NEW contract test expects subfolders.
**Why it happens:** Plan 1 updates the contract test discovery logic before new fixtures exist.
**How to avoid:** Make `_load_scenarios()` handle BOTH formats: try subfolder first, fall back to flat `scenario_*.json`. Or: have the discovery skip gracefully when subfolders don't exist yet (`pytest.skip`).
**Warning signs:** Contract tests fail or error after Plan 1 commits but before human re-capture.

### Pitfall 6: `_remap_state_ids` Missing Project ID Remapping for New Projects
**What goes wrong:** Scenarios involving `GM-TestProject2` or `GM-TestProject-Dated` have project IDs in state_after that differ from InMemoryBridge seed data. Currently, `_remap_state_ids` only remaps task parent/project fields using `id_map`, but `id_map` is only populated from `add_task` responses.
**Why it happens:** Projects are seeded (from initial_state.json), so their IDs are consistent -- initial_state contains the real project IDs, and InMemoryBridge is seeded with those same IDs. This pitfall does NOT apply because projects are pre-seeded, not created during scenarios.
**How to avoid:** Verify that initial_state.json includes all 3 projects. No id_map remapping needed for project IDs.

### Pitfall 7: Deep Nesting Inheritance (Scenario 07-05)
**What goes wrong:** The `_compute_effective_field` walks parent chain, but at each step it checks the `parent` field. For a 3-4 level deep chain (project -> task -> subtask -> sub-subtask), every intermediate level must have its `parent` set correctly by `_handle_add_task`.
**Why it happens:** The chain walk relies on `task.get("parent")` returning the immediate parent ID. If any link is wrong, the chain breaks.
**How to avoid:** Verify with a simple unit test: seed a project, add task under it, add subtask under task, add sub-subtask under subtask. Check that the sub-subtask inherits from the project.
**Warning signs:** Effective fields are correct at depth 1 but null at depth 3+.

## Code Examples

### Moving completionDate/dropDate from VOLATILE to Presence-Check

```python
# Source: tests/golden_master/normalize.py (current)
# BEFORE: fields in VOLATILE_TASK_FIELDS (stripped entirely)
VOLATILE_TASK_FIELDS: set[str] = {
    "id", "url", "added", "modified",
    "completionDate",  # REMOVE
    "dropDate",        # REMOVE
}

# AFTER: fields handled by presence-check normalization
VOLATILE_TASK_FIELDS: set[str] = {
    "id", "url", "added", "modified",
}

PRESENCE_CHECK_TASK_FIELDS: set[str] = {
    "completionDate", "dropDate",
    "effectiveCompletionDate", "effectiveDropDate",
}
```

### Graduating Fields from UNCOMPUTED

```python
# Source: tests/golden_master/normalize.py (current)
# BEFORE
UNCOMPUTED_TASK_FIELDS: set[str] = {
    "status",
    "effectiveDueDate",
    "effectiveDeferDate",
    "effectiveCompletionDate",
    "effectivePlannedDate",
    "effectiveDropDate",
    "repetitionRule",
}

# AFTER (D-08 through D-13)
UNCOMPUTED_TASK_FIELDS: set[str] = {
    "status",  # intentionally out of scope
}
```

### Extended `_remap_ids` for Anchor Moves

```python
# Source: tests/test_bridge_contract.py (extend existing function)
def _remap_ids(params: dict[str, Any], id_map: dict[str, str]) -> dict[str, Any]:
    if not id_map:
        return params
    remapped = dict(params)
    if "id" in remapped and remapped["id"] in id_map:
        remapped["id"] = id_map[remapped["id"]]
    if "parent" in remapped and remapped["parent"] in id_map:
        remapped["parent"] = id_map[remapped["parent"]]
    if "moveTo" in remapped and isinstance(remapped["moveTo"], dict):
        mt = remapped["moveTo"]
        # Container-based moves
        cid = mt.get("containerId")
        if cid in id_map:
            mt = {**mt, "containerId": id_map[cid]}
        # Anchor-based moves (NEW)
        aid = mt.get("anchorId")
        if aid in id_map:
            mt = {**mt, "anchorId": id_map[aid]}
        remapped["moveTo"] = mt
    return remapped
```

## Key Technical Details

### Bridge moveTo Wire Format
The bridge.js expects this shape for moveTo:
- Container moves: `{"position": "beginning"|"ending", "containerId": "<id>"|null}`
- Anchor moves: `{"position": "before"|"after", "anchorId": "<taskId>"}`

InMemoryBridge currently ignores `position` entirely -- it just reads `containerId` and sets parent/project. For contract test purposes, anchor moves and beginning/ending moves need to at minimum set the correct parent/project. Task ordering within a container is NOT tracked by InMemoryBridge (and the golden master normalizes by sorting entities by name), so position correctness beyond parent assignment is not verified.

### Fields Being Graduated (Summary)

| Field | From | To | Mechanism |
|-------|------|----|-----------|
| completionDate | VOLATILE (stripped) | Presence-check (`"<set>"` / null) | Sentinel normalization |
| dropDate | VOLATILE (stripped) | Presence-check | Sentinel normalization |
| effectiveCompletionDate | UNCOMPUTED (stripped) | Presence-check | Sentinel normalization |
| effectiveDropDate | UNCOMPUTED (stripped) | Presence-check | Sentinel normalization |
| effectiveFlagged | UNCOMPUTED (stripped) | Exact match | Boolean OR ancestor walk |
| effectiveDueDate | UNCOMPUTED (stripped) | Exact match | Ancestor chain first-non-null |
| effectiveDeferDate | UNCOMPUTED (stripped) | Exact match | Ancestor chain first-non-null |
| effectivePlannedDate | UNCOMPUTED (stripped) | Exact match | Ancestor chain first-non-null |
| repetitionRule | UNCOMPUTED (stripped) | Exact match | Both sides return null |

### InMemoryBridge Position Handling
Current InMemoryBridge ignores `moveTo.position` entirely. For anchor moves (`before`/`after`), the bridge needs to:
1. Look up the anchor task
2. Set parent/project to match the anchor's parent/project
3. Ordering is not tracked (state comparison sorts by name)

For `beginning` moves, behavior is identical to `ending` -- parent/project assignment is the same regardless of position within the container. State comparison sorts by name so ordering is invisible.

### Scenario Count Verification
CONTEXT.md lists 41 scenarios:
- 01-add: 6
- 02-edit: 11
- 03-move: 7
- 04-tags: 5
- 05-lifecycle: 4
- 06-combined: 3
- 07-inheritance: 5
**Total: 41** (+ initial_state = 42 files)

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_bridge_contract.py -x -v` |
| Full suite command | `uv run pytest` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GOLD-01 | Subfolder discovery + 41 scenarios | integration | `uv run pytest tests/test_bridge_contract.py -x -v` | Exists (updated in phase) |
| GOLD-02 | Capture script runs all scenarios | manual-only | Human runs `uv run python uat/capture_golden_master.py` | Exists (rewritten in phase) |
| GOLD-03 | No manifest needed, sort order works | integration | `uv run pytest tests/test_bridge_contract.py -x -v` | Exists (updated in phase) |
| NORM-01 | completionDate/dropDate presence-check | integration | `uv run pytest tests/test_bridge_contract.py -x -v -k "lifecycle"` | Exists (verified by scenarios 05-01, 05-02) |
| NORM-02 | effective completion/drop presence-check | integration | `uv run pytest tests/test_bridge_contract.py -x -v` | Exists |
| NORM-03 | Effective fields exact match via inheritance | integration | `uv run pytest tests/test_bridge_contract.py -x -v -k "inheritance"` | Exists (scenarios 07-*) |
| NORM-04 | repetitionRule exact match | integration | `uv run pytest tests/test_bridge_contract.py -x -v` | Exists (all scenarios verify this implicitly) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_bridge_contract.py -x -v`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
None -- existing test infrastructure covers all phase requirements. The contract test file exists and will be updated in-phase. No new test framework or config needed.

## Open Questions

1. **Anchor move parent/project resolution**
   - What we know: For `before`/`after` moves, OmniFocus moves the task to be a sibling of the anchor. The anchor's parent becomes the moved task's parent.
   - What's unclear: Does InMemoryBridge need to explicitly look up the anchor task's parent, or is this already handled? (Answer: it's NOT handled -- InMemoryBridge only reads `containerId`, not `anchorId`. New code needed.)
   - Recommendation: Add anchor resolution in `_handle_edit_task`: look up anchor task, use its parent/project for the moved task.

2. **`effectiveCompletionDate` / `effectiveDropDate` inheritance semantics**
   - What we know: OmniFocus sets these on completed/dropped tasks.
   - What's unclear: Do subtasks of completed tasks inherit `effectiveCompletionDate`? Or is it only set directly?
   - Recommendation: Start with presence-check normalization (D-08/D-09) which sidesteps the question. If inheritance scenarios reveal a pattern, document it in Plan 2 triage.

3. **Deep nesting performance**
   - What we know: `_compute_effective_field` walks the chain with a visited set (cycle protection).
   - What's unclear: With 40+ tasks in InMemoryBridge state, is the per-task index rebuild a concern?
   - Recommendation: At this scale (< 50 tasks), it's negligible. If ever a concern, cache the index.

## Project Constraints (from CLAUDE.md)

- **SAFE-01/02**: No automated test or agent may touch RealBridge. Capture script is human-run only. CI contract tests use InMemoryBridge exclusively.
- **Service Layer Convention**: Method Object pattern for use cases. Not directly relevant to this phase (no service changes).
- **UAT Guidelines**: Refactoring phases focus on developer experience. This is test infrastructure -- UAT should verify the golden master makes sense, not "does it still work."
- In comments/docstrings, write `the real Bridge` not `RealBridge` (CI grep check).

## Sources

### Primary (HIGH confidence)
- `tests/golden_master/normalize.py` -- current VOLATILE/UNCOMPUTED field sets, normalization functions
- `tests/test_bridge_contract.py` -- current contract test structure, replay engine, ID remapping
- `uat/capture_golden_master.py` -- current capture script (20 scenarios, followup pattern)
- `tests/doubles/bridge.py` -- InMemoryBridge handlers, parent chain walking
- `tests/conftest.py` -- `make_task_dict()` field inventory (26 bridge fields)
- `src/omnifocus_operator/bridge/bridge.js` lines 290-313 -- moveTo handling for all 4 positions
- `.planning/phases/28-*/28-CONTEXT.md` -- all locked decisions D-01 through D-19

### Secondary (MEDIUM confidence)
- Golden master fixture files (scenario_14, 15, 16) -- verified field shapes and presence of completionDate/dropDate in real output

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- pure Python, pytest, JSON fixtures. No new dependencies.
- Architecture: HIGH -- extending well-understood patterns (parent chain walk, normalization, capture script).
- Pitfalls: HIGH -- identified from direct code inspection of existing infrastructure.

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (stable internal infrastructure, no external dependency churn)
