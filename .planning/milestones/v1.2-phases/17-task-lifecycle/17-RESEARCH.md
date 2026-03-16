# Phase 17: Task Lifecycle - Research

**Researched:** 2026-03-11
**Domain:** OmniJS lifecycle APIs (markComplete, drop) + service/bridge integration
**Confidence:** HIGH

## Summary

Phase 17 replaces the lifecycle fail-fast guard (line ~202-206 of service.py) with actual complete/drop logic. The implementation touches 4 layers: model type narrowing, service lifecycle logic, bridge.js handler additions, and InMemoryRepository state mutation. All OmniJS APIs are verified from the bridge spec research.

The scope is well-constrained: two lifecycle actions (`complete`, `drop`), no-op detection, cross-state warnings, and repeating task warnings. No new MCP tools -- lifecycle is a sub-operation of `edit_tasks`. CONTEXT.md locked all major decisions; Claude's discretion is limited to implementation details.

**Primary recommendation:** Implement bottom-up (model -> bridge -> repository -> service -> tests) to keep each layer independently testable.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Two lifecycle values: `"complete"` and `"drop"` -- imperative verbs (commands, not state descriptions)
- `"reopen"` deferred entirely -- `markIncomplete()` is too niche
- `lifecycle` field type changes from `str` to a constrained type (Literal or enum)
- Always call `drop(false)` regardless of task type
- Non-repeating task: permanently dropped, no special warning
- Repeating task: skips this occurrence only, warning: "Repeating task -- this occurrence was skipped"
- `"complete"` on repeating task: warning: "Repeating task -- this occurrence completed, next occurrence created"
- `"drop"` on repeating task: warning: "Repeating task -- this occurrence was skipped"
- Detection via `repetition_rule` field on task snapshot, checked before bridge call
- No-op detection: check task availability before calling bridge; skip bridge call if already in target state
- No-op warning format: "Task is already complete -- nothing changed. Omit actions.lifecycle to skip"
- Cross-state transitions allowed (complete a dropped task, drop a completed task) with warning
- Cross-state warning: "Task was already [prior state] -- lifecycle action applied, task is now [new state]. Confirm with user that this was intended"
- Warnings can stack (e.g., cross-state + repeating task)
- New bridge.js handler for lifecycle actions within `handleEditTask`
- Bridge receives: `{ lifecycle: "complete" | "drop" }` in the edit payload
- Bridge calls `task.markComplete()` or `task.drop(false)` accordingly
- No new bridge command -- lifecycle is part of edit_task

### Claude's Discretion
- Exact bridge payload shape for lifecycle (inline with existing edit payload vs separate field)
- Whether lifecycle enum is a Python `Literal["complete", "drop"]` or a dedicated `LifecycleAction` enum
- Exact warning message wording (principles above, but final copy is flexible)
- How to structure the service layer lifecycle logic (inline in edit_task vs helper method)
- Test organization for lifecycle tests

### Deferred Ideas (OUT OF SCOPE)
- `"reopen"` / `"reactivate"` lifecycle action
- `"skip"` as explicit value for repeating tasks
- `delete_tasks` tool (v1.4)
- Repeating task "drop all occurrences"
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| LIFE-01 | Agent can mark a task as complete via edit_tasks | Bridge `task.markComplete()`, service lifecycle logic, model type constraint |
| LIFE-02 | Agent can drop a task via edit_tasks | Bridge `task.drop(false)`, same service path with different action |
| LIFE-03 | Agent can reactivate a completed task via edit_tasks | **DEFERRED per CONTEXT.md** -- `reopen` not implemented. LIFE-03 satisfied by documenting the deferral |
| LIFE-04 | Lifecycle interface design resolved via research spike | Resolved in CONTEXT.md: `Literal["complete", "drop"]` on ActionsSpec.lifecycle |
| LIFE-05 | Edge cases documented: repeating tasks, dropped task reactivation | Repeating task warnings decided; cross-state transitions allowed with warnings |
</phase_requirements>

## Standard Stack

No new libraries. All implementation uses existing project dependencies.

### Core (existing)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.x | Model type narrowing (`Literal` for lifecycle) | Already used for all models |
| mcp | >=1.26.0 | MCP server (no change) | Single runtime dep |

### Supporting
- `typing.Literal["complete", "drop"]` -- preferred over dedicated enum (2 values only, matches existing `_Unset` pattern)

## Architecture Patterns

### Pattern 1: Lifecycle as inline payload field
**What:** `lifecycle` is a key in the same `payload: dict` passed to `repository.edit_task`, alongside field changes, tag ops, and moveTo.
**When to use:** Always -- lifecycle is part of edit_task, not a separate operation.
**Example:**
```python
# Service builds payload
payload = {"id": spec.id, "lifecycle": "complete"}
# Bridge receives and dispatches
if (params.hasOwnProperty("lifecycle")) {
    if (params.lifecycle === "complete") task.markComplete();
    else if (params.lifecycle === "drop") task.drop(false);
}
```

### Pattern 2: Pre-bridge state checking
**What:** Read task snapshot (`task.availability`, `task.repetition_rule`) before bridge call to detect no-ops, cross-state, and repeating tasks.
**When to use:** Always -- matches existing patterns for field no-op detection, tag diff computation, and cycle detection.
**Example flow:**
```
1. Get task snapshot (already done at service.py line ~143)
2. Read task.availability -> determine if no-op or cross-state
3. Read task.repetition_rule -> determine if repeating task warning needed
4. If no-op: return early with warning
5. If proceeding: add lifecycle to payload, collect warnings
6. Delegate to repository
```

### Pattern 3: Warning stacking
**What:** Multiple warnings can accumulate (existing completed/dropped warning + lifecycle cross-state + repeating task).
**When to use:** When lifecycle interacts with existing status warnings.
**Key insight:** The existing "this task is completed/dropped" warning (line ~156-161) needs coordination with lifecycle logic:
- If lifecycle="complete" on an already-completed task: that's a no-op, not a status warning
- If editing fields + lifecycle on a completed task: status warning still applies to the field changes
- Lifecycle should be processed BEFORE the existing status warning to avoid contradictory messages

### Anti-Patterns to Avoid
- **Separate bridge command for lifecycle:** Don't create a new `complete_task` or `drop_task` operation. Lifecycle is part of edit_task.
- **Lifecycle after no-op detection:** Don't let the generic no-op detection at step 7 interfere with lifecycle. Lifecycle has its own no-op check.
- **Bridge-side state checking:** Don't check availability in bridge.js. All intelligence lives in Python service layer.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Lifecycle type validation | Custom string validation | `Literal["complete", "drop"]` on ActionsSpec | Pydantic validates automatically |
| Repeating task detection | Bridge-side check | `task.repetition_rule is not None` on snapshot | Decision logic stays in Python |

## Common Pitfalls

### Pitfall 1: Lifecycle + existing status warning conflict
**What goes wrong:** The existing warning at line ~156-161 warns "this task is completed/dropped" for any edit. If lifecycle="complete" on a completed task, you'd get both "task is completed" warning AND "already complete, nothing changed" no-op.
**Why it happens:** Status warning runs before lifecycle logic.
**How to avoid:** Either:
- (a) Move lifecycle processing before the status warning, suppress status warning when lifecycle handles the state
- (b) Extract lifecycle processing to a helper that returns (should_proceed, warnings) and adjust the status warning accordingly
**Warning signs:** Duplicate or contradictory warnings in test output.

### Pitfall 2: Lifecycle + field changes in same call
**What goes wrong:** Agent sends `{id, name: "New Name", actions: {lifecycle: "complete"}}`. Both field change AND lifecycle should apply.
**Why it happens:** No-op detection only checks field changes, not lifecycle.
**How to avoid:** Lifecycle adds `lifecycle` key to payload. The `len(payload) == 1` empty-edit check (step 6) will see payload has keys beyond "id", so it won't short-circuit. The no-op detection (step 7) should skip lifecycle key in field comparisons.

### Pitfall 3: InMemoryRepository must mutate availability
**What goes wrong:** Tests pass at service level but InMemoryRepository doesn't update `task.availability` after lifecycle action, so subsequent reads show stale state.
**Why it happens:** InMemoryRepository.edit_task currently doesn't know about lifecycle.
**How to avoid:** Add lifecycle handling to InMemoryRepository.edit_task:
- `lifecycle: "complete"` -> set `task.availability = Availability.COMPLETED`
- `lifecycle: "drop"` -> set `task.availability = Availability.DROPPED`

### Pitfall 4: No-op detection must exclude lifecycle key
**What goes wrong:** Generic no-op detection (step 7) sees `lifecycle` in payload, tries to compare against `field_comparisons` dict, either crashes or falsely reports no-op.
**How to avoid:** Add `"lifecycle"` to the skip set in no-op detection, or handle lifecycle no-op separately before the generic check.

## Code Examples

### Model change: ActionsSpec.lifecycle type narrowing
```python
# Current (service.py line 199):
lifecycle: str | _Unset = UNSET

# New:
lifecycle: Literal["complete", "drop"] | _Unset = UNSET
```
Pydantic will reject invalid values automatically with a clean error.

### Bridge.js: lifecycle handling in handleEditTask
```javascript
// After movement handling, before return
if (params.hasOwnProperty("lifecycle")) {
    if (params.lifecycle === "complete") {
        task.markComplete();
    } else if (params.lifecycle === "drop") {
        task.drop(false);
    }
}
```
**Source:** OmniJS API from `.research/deep-dives/omni-automation-api/FINDINGS.md`

### Service: lifecycle logic (helper method approach)
```python
async def _process_lifecycle(
    self,
    lifecycle_action: str,
    task: Task,
) -> tuple[bool, list[str]]:
    """Process lifecycle action. Returns (should_call_bridge, warnings)."""
    warnings: list[str] = []
    target_availability = {
        "complete": Availability.COMPLETED,
        "drop": Availability.DROPPED,
    }[lifecycle_action]

    # No-op: already in target state
    if task.availability == target_availability:
        action_word = "complete" if lifecycle_action == "complete" else "dropped"
        warnings.append(
            f"Task is already {action_word} -- nothing changed. "
            "Omit actions.lifecycle to skip"
        )
        return False, warnings

    # Cross-state: completing a dropped task or dropping a completed task
    if task.availability in (Availability.COMPLETED, Availability.DROPPED):
        prior = task.availability.value
        new = target_availability.value
        warnings.append(
            f"Task was already {prior} -- lifecycle action applied, "
            f"task is now {new}. Confirm with user that this was intended"
        )

    # Repeating task warnings
    if task.repetition_rule is not None:
        if lifecycle_action == "complete":
            warnings.append(
                "Repeating task -- this occurrence completed, "
                "next occurrence created"
            )
        else:  # drop
            warnings.append(
                "Repeating task -- this occurrence was skipped"
            )

    return True, warnings
```

### InMemoryRepository: lifecycle handling
```python
# In edit_task, after moveTo handling:
lifecycle = payload.get("lifecycle")
if lifecycle == "complete":
    task.availability = Availability.COMPLETED
elif lifecycle == "drop":
    task.availability = Availability.DROPPED
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `lifecycle: str` (reserved) | `lifecycle: Literal["complete", "drop"]` | Phase 17 | Type-safe validation |
| Lifecycle fail-fast rejection | Actual lifecycle processing | Phase 17 | Agents can complete/drop tasks |

## Open Questions

1. **Lifecycle + existing status warning interaction**
   - What we know: Current code warns on any edit to completed/dropped tasks (line ~156). Lifecycle no-op should suppress this.
   - What's unclear: Exact ordering -- should lifecycle run before or after the status warning?
   - Recommendation: Process lifecycle first. If lifecycle is a no-op (already in target state), include the no-op warning but skip the generic status warning. If lifecycle changes state, the status warning is irrelevant (task was just transitioned intentionally). If only field changes (no lifecycle), keep status warning as-is.

2. **Lifecycle + field no-op interaction**
   - What we know: If agent sends `{id, lifecycle: "complete"}` with no field changes, the empty-edit check (step 6) should NOT trigger because lifecycle is present.
   - Recommendation: Check for lifecycle presence when determining if edit is empty. A lifecycle action alone is not an "empty edit."

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | pyproject.toml |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LIFE-01 | Complete a task via edit_tasks | unit (service + server) | `uv run pytest tests/test_service.py -x -k lifecycle_complete` | Wave 0 |
| LIFE-02 | Drop a task via edit_tasks | unit (service + server) | `uv run pytest tests/test_service.py -x -k lifecycle_drop` | Wave 0 |
| LIFE-03 | Reactivate (DEFERRED) | n/a | n/a | n/a -- deferred |
| LIFE-04 | Interface design resolved | unit (model validation) | `uv run pytest tests/test_models.py -x -k lifecycle` | Wave 0 |
| LIFE-05 | Edge cases: repeating, cross-state, no-op | unit (service) | `uv run pytest tests/test_service.py -x -k "lifecycle and (repeat or noop or cross)"` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- None -- existing test infrastructure covers all phase requirements. New tests will be added to existing test files (`test_service.py`, `test_server.py`, `test_models.py`, `test_bridge.test.js`).

## Sources

### Primary (HIGH confidence)
- **Project codebase** -- `service.py`, `models/write.py`, `bridge/bridge.js`, `repository/in_memory.py` (direct reads)
- **`.research/deep-dives/omni-automation-api/FINDINGS.md`** -- OmniJS API: `task.markComplete()`, `task.drop(false)`, `task.markIncomplete()`
- **`.research/deep-dives/omnifocus-api-ground-truth/BRIDGE-SPEC.md`** -- Bridge contract specification

### Secondary (MEDIUM confidence)
- **CONTEXT.md** -- User decisions from discuss-phase session (all locked decisions verified against codebase)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all existing patterns
- Architecture: HIGH -- follows established edit_task patterns exactly
- Pitfalls: HIGH -- identified from direct code analysis of interaction points

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable -- no external dependencies)
