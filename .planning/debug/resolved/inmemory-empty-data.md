---
status: resolved
trigger: "UAT gap: InMemoryBridge returns empty collections when used via MCP server"
created: 2026-03-02T00:00:00Z
updated: 2026-03-02T15:30:00Z
---

## Current Focus

hypothesis: InMemoryBridge is intentionally a pure test double with no default data; the factory seeds it with empty lists by design
test: traced full call path from create_bridge -> InMemoryBridge -> send_command -> DatabaseSnapshot
expecting: confirmed - empty by design, not a bug
next_action: document fix direction

## Symptoms

expected: list_all returns tasks/projects/tags/folders/perspectives with real-looking sample data
actual: list_all returns empty arrays for all five collections
errors: none (no crash, valid response, just empty)
reproduction: Set OMNIFOCUS_BRIDGE=inmemory, connect Claude, call list_all tool
started: always (by design)

## Eliminated

- hypothesis: bridge send_command crashes or errors
  evidence: it returns successfully - the data dict is just empty because factory passes empty lists
  timestamp: 2026-03-02

- hypothesis: repository/service loses data in transit
  evidence: data flows through unmodified - repository calls send_command("dump_all"), gets back the dict, Pydantic validates it; empty lists validate fine
  timestamp: 2026-03-02

## Evidence

- timestamp: 2026-03-02
  checked: src/omnifocus_operator/bridge/_factory.py lines 38-47
  found: |
    factory hardcodes empty lists:
      return InMemoryBridge(
          data={
              "tasks": [],
              "projects": [],
              "tags": [],
              "folders": [],
              "perspectives": [],
          }
      )
  implication: InMemoryBridge always returns this exact dict on every send_command call

- timestamp: 2026-03-02
  checked: src/omnifocus_operator/bridge/_in_memory.py lines 49-58
  found: |
    send_command always returns self._data unchanged regardless of operation:
      async def send_command(self, operation, params=None) -> dict:
          self._calls.append(BridgeCall(operation=operation, params=params))
          if self._error is not None:
              raise self._error
          return self._data
  implication: InMemoryBridge is designed as a pure test double - no routing by operation, no sample data

- timestamp: 2026-03-02
  checked: src/omnifocus_operator/repository/_repository.py line 84
  found: |
    repository calls: raw = await self._bridge.send_command("dump_all")
    then: snapshot = DatabaseSnapshot.model_validate(raw)
  implication: bridge must return a dict with tasks/projects/tags/folders/perspectives keys; InMemoryBridge returns these keys but all are empty

- timestamp: 2026-03-02
  checked: src/omnifocus_operator/models/_base.py
  found: |
    OmniFocusBaseModel uses alias_generator=to_camel with validate_by_alias=True.
    This means Pydantic outputs camelCase field names when serializing (e.g. completedByChildren, dueDate, inInbox).
  implication: the camelCase output test WOULD work correctly IF there was data to inspect - the mechanism is already in place

- timestamp: 2026-03-02
  checked: src/omnifocus_operator/models/_task.py, _project.py (inferred from base model)
  found: |
    Task has multi-word fields: in_inbox, effective_active, assigned_container, completed_by_children, etc.
    These become inInbox, effectiveActive, assignedContainer, completedByChildren in JSON output.
  implication: Test 4 (camelCase) can only be verified if the response contains at least one task with multi-word field names visible

## Resolution

root_cause: |
  The factory (create_bridge in _factory.py) intentionally seeds InMemoryBridge with empty lists
  for all five collections. InMemoryBridge is a pure test double with no built-in sample data.
  It returns whatever dict is passed to its constructor verbatim on every send_command() call.
  There is no bug in the data flow - empty lists validate fine as DatabaseSnapshot,
  producing {"tasks": [], "projects": [], "tags": [], "folders": [], "perspectives": []}
  which makes it impossible to observe camelCase field names on actual entity objects.

fix: |
  Two viable approaches:

  OPTION A (Recommended) - Seed sample data in the factory:
    Change create_bridge("inmemory") in _factory.py to pass realistic sample data with
    at least one item per collection. Sample items should include multi-word fields
    (e.g. in_inbox, completed_by_children) so camelCase output (inInbox, completedByChildren)
    is verifiable. The InMemoryBridge class itself does not need to change.

  OPTION B - Separate "demo" bridge type:
    Add a new case "demo" in the factory that seeds rich sample data. Keep "inmemory" empty
    for unit tests. UAT instructions would say OMNIFOCUS_BRIDGE=demo.

  OPTION A is simpler - the factory is the right seeding point, not the class itself.
  No new classes needed. The fix is localised to a single file: _factory.py.

verification: not yet applied
files_changed: []

## What Needs to Change

file: src/omnifocus_operator/bridge/_factory.py
change: |
  Replace empty lists in the InMemoryBridge constructor call with realistic sample
  data containing at least:
  - 1 Task with multi-word fields populated (in_inbox=True, effective_active=True,
    completed_by_children=False, assigned_container=None, etc.)
  - 1 Project with multi-word fields (completed_by_children, has_children, etc.)
  - 1 Tag (just id + name)
  - 1 Folder (just id + name)
  - 1 Perspective (just id + name)

  The sample data dict keys must match what Pydantic expects from the bridge:
  EITHER snake_case (because validate_by_name=True on OmniFocusBaseModel)
  OR camelCase (because validate_by_alias=True).
  Snake_case is clearer for hardcoded Python data.

  Required fields for Task (non-optional, no default):
    id, name, note, completed, completed_by_children, flagged, effective_flagged,
    sequential, has_children, should_use_floating_time_zone, active, effective_active,
    status (TaskStatus enum value), in_inbox

  Required fields for Project: similar set minus task-specific fields
  Required fields for Tag: id, name
  Required fields for Folder: id, name
  Required fields for Perspective: id, name (check _perspective.py)

note: |
  The camelCase serialization mechanism (alias_generator=to_camel on OmniFocusBaseModel)
  is already correctly implemented. Test 4 only fails because there is no data to
  observe it on. No changes needed to model serialization code.
