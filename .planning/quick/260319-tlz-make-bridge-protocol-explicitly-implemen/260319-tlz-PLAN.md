---
phase: quick-260319-tlz
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/omnifocus_operator/contracts/protocols.py
  - src/omnifocus_operator/bridge/in_memory.py
  - src/omnifocus_operator/bridge/real.py
  - src/omnifocus_operator/bridge/simulator.py
autonomous: true
requirements: [QUICK-260319-tlz]

must_haves:
  truths:
    - "All three bridge classes explicitly implement the Bridge protocol"
    - "All three protocols (Service, Repository, Bridge) have @runtime_checkable"
    - "RealBridge docstring no longer says 'no inheritance'"
  artifacts:
    - path: "src/omnifocus_operator/contracts/protocols.py"
      provides: "@runtime_checkable on Bridge and Service protocols"
      contains: "@runtime_checkable"
    - path: "src/omnifocus_operator/bridge/in_memory.py"
      provides: "InMemoryBridge(Bridge) explicit implementation"
      contains: "class InMemoryBridge(Bridge)"
    - path: "src/omnifocus_operator/bridge/real.py"
      provides: "RealBridge(Bridge) explicit implementation"
      contains: "class RealBridge(Bridge)"
    - path: "src/omnifocus_operator/bridge/simulator.py"
      provides: "SimulatorBridge(RealBridge, Bridge) explicit implementation"
      contains: "class SimulatorBridge(RealBridge, Bridge)"
  key_links:
    - from: "src/omnifocus_operator/bridge/in_memory.py"
      to: "src/omnifocus_operator/contracts/protocols.py"
      via: "import and explicit subclass"
      pattern: "from omnifocus_operator.contracts.protocols import Bridge"
    - from: "src/omnifocus_operator/bridge/real.py"
      to: "src/omnifocus_operator/contracts/protocols.py"
      via: "import and explicit subclass"
      pattern: "from omnifocus_operator.contracts.protocols import Bridge"
---

<objective>
Make the `Bridge` protocol from `contracts/protocols.py` explicitly implemented by all bridge classes (`InMemoryBridge`, `RealBridge`, `SimulatorBridge`). Add `@runtime_checkable` to `Bridge` and `Service` protocols for consistency with `Repository`.

Purpose: Grep-friendly inventory of all protocol implementors. Currently bridges satisfy `Bridge` via structural typing only -- making it explicit matches the pattern already used by `Service` and `Repository` implementations.
Output: Four modified files; all existing tests pass.
</objective>

<execution_context>
@/Users/flo/.claude/get-shit-done/workflows/execute-plan.md
@/Users/flo/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/omnifocus_operator/contracts/protocols.py
@src/omnifocus_operator/bridge/in_memory.py
@src/omnifocus_operator/bridge/real.py
@src/omnifocus_operator/bridge/simulator.py

<interfaces>
<!-- Current protocol definition (protocols.py) -->
From src/omnifocus_operator/contracts/protocols.py:
```python
class Service(Protocol):                    # NO @runtime_checkable
class Repository(Protocol):                 # HAS @runtime_checkable
class Bridge(Protocol):                     # NO @runtime_checkable
    async def send_command(self, operation: str, params: dict[str, Any] | None = None) -> dict[str, Any]: ...
```

<!-- Current bridge class signatures -->
From src/omnifocus_operator/bridge/in_memory.py:
```python
class InMemoryBridge:                       # structural only — no Bridge base
```

From src/omnifocus_operator/bridge/real.py:
```python
class RealBridge:                           # structural only — docstring says "no inheritance"
```

From src/omnifocus_operator/bridge/simulator.py:
```python
class SimulatorBridge(RealBridge):          # inherits RealBridge only
```

<!-- Existing pattern to follow (Repository implementors) -->
From src/omnifocus_operator/repository/in_memory.py:
```python
from omnifocus_operator.contracts.protocols import Repository
class InMemoryRepository(Repository):
```

From src/omnifocus_operator/service/service.py:
```python
from omnifocus_operator.contracts.protocols import Service
class OperatorService(Service):  # explicitly implements Service protocol
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add @runtime_checkable to Bridge and Service protocols</name>
  <files>src/omnifocus_operator/contracts/protocols.py</files>
  <action>
Add `@runtime_checkable` decorator to the `Bridge` class (line 62) and the `Service` class (line 29). `Repository` already has it (line 45-46). After this change, all three protocols will consistently have `@runtime_checkable`.

No other changes to this file.
  </action>
  <verify>
    <automated>uv run python -c "from omnifocus_operator.contracts.protocols import Bridge, Service, Repository; assert hasattr(Bridge, '__protocol_attrs__'); assert hasattr(Service, '__protocol_attrs__'); print('All protocols runtime_checkable')"</automated>
  </verify>
  <done>All three protocols (`Service`, `Repository`, `Bridge`) have `@runtime_checkable` decorator</done>
</task>

<task type="auto">
  <name>Task 2: Make all bridge classes explicitly implement Bridge</name>
  <files>src/omnifocus_operator/bridge/in_memory.py, src/omnifocus_operator/bridge/real.py, src/omnifocus_operator/bridge/simulator.py</files>
  <action>
**in_memory.py:**
- Add import: `from omnifocus_operator.contracts.protocols import Bridge`
- Change class signature: `class InMemoryBridge(Bridge):` (was `class InMemoryBridge:`)
- No other changes needed -- already has the correct `send_command` signature

**real.py:**
- Add import: `from omnifocus_operator.contracts.protocols import Bridge`
- Change class signature: `class RealBridge(Bridge):` (was `class RealBridge:`)
- Update docstring (line 107-113): remove the phrase "Satisfies the ``Bridge`` protocol via structural typing -- no inheritance." and replace with something like "Explicitly implements the ``Bridge`` protocol." Keep the rest of the docstring intact.

**simulator.py:**
- Add import: `from omnifocus_operator.contracts.protocols import Bridge`
- Change class signature: `class SimulatorBridge(RealBridge, Bridge):` (was `class SimulatorBridge(RealBridge):`)
  - Per user decision: explicit `Bridge` on both `RealBridge` and `SimulatorBridge`, not just inherited. Grep-friendly.
- No docstring changes needed

After all changes, run the full test suite to confirm nothing breaks.
  </action>
  <verify>
    <automated>uv run python -m pytest tests/ -x -q 2>&1 | tail -5</automated>
  </verify>
  <done>All three bridge classes explicitly list `Bridge` in their class signature. Full test suite passes. `grep -rn "class.*Bridge.*Bridge" src/` returns all three bridge files.</done>
</task>

</tasks>

<verification>
- `uv run python -m pytest tests/ -x -q` -- full test suite passes
- `uv run python -m mypy src/omnifocus_operator/bridge/ src/omnifocus_operator/contracts/protocols.py --strict` -- no type errors
- `grep -rn "class.*Bridge" src/omnifocus_operator/bridge/` shows explicit `(Bridge)` in all three class definitions
- `grep -rn "@runtime_checkable" src/omnifocus_operator/contracts/protocols.py` shows three occurrences
</verification>

<success_criteria>
- All three bridge classes (`InMemoryBridge`, `RealBridge`, `SimulatorBridge`) explicitly implement `Bridge` in their class signature
- All three protocols (`Service`, `Repository`, `Bridge`) have `@runtime_checkable`
- RealBridge docstring updated (no "no inheritance" note)
- Full test suite (579 tests) passes with no regressions
- mypy passes with no new errors
</success_criteria>

<output>
After completion, create `.planning/quick/260319-tlz-make-bridge-protocol-explicitly-implemen/260319-tlz-SUMMARY.md`
</output>
