# Architecture: Repetition Rule Write Support Integration

**Domain:** OmniFocus MCP Server -- repetition rule read/write for existing three-layer architecture
**Researched:** 2026-03-27
**Confidence:** HIGH -- based entirely on codebase analysis, no external dependencies

## Executive Summary

Repetition rule support integrates cleanly into the existing architecture. The key insight is that repetition sits at the boundary between two domains: the agent-facing structured model (8 frequency types, 3 root-level fields) and OmniFocus's internal RRULE format (4 bridge parameters). Two standalone utility functions (`parse_rrule`, `build_rrule`) bridge these domains, living in a new `rrule/` package under the models layer.

The read model is a breaking change (replacing `RepetitionRule` with structured fields), but the write model slots into existing patterns: `PatchOrClear[RepetitionRuleSpec]` on commands, bridge payload carries flat RRULE + metadata fields, partial update merge logic lives in `DomainLogic`.

## Recommended Architecture

### New Package: `src/omnifocus_operator/rrule/`

Standalone RRULE parse/build utilities. Belongs at the same level as `models/` and `contracts/` -- NOT inside `service/` or `repository/`. Rationale:

- Both read paths (SQLite adapter in `repository/hybrid.py` and bridge adapter in `bridge/adapter.py`) need `parse_rrule`
- The write path (`service/domain.py` or `service/payload.py`) needs `build_rrule`
- Putting it in service would create a reverse dependency (repository importing from service)
- Putting it in models would bloat a data-definition package with parsing logic
- Standalone package keeps it testable in isolation with no import entanglements

```
src/omnifocus_operator/
├── rrule/                          # NEW PACKAGE
│   ├── __init__.py                 # Re-exports parse_rrule, build_rrule
│   ├── parser.py                   # parse_rrule(str) -> FrequencySpec
│   └── builder.py                  # build_rrule(FrequencySpec) -> str
├── models/
│   ├── common.py                   # MODIFIED: RepetitionRule -> structured fields
│   └── enums.py                    # MODIFIED: ScheduleType gains 3rd value, new enums
├── contracts/
│   ├── common.py                   # NEW ADDITION: RepetitionRuleEndAction
│   └── use_cases/
│       ├── add_task.py             # MODIFIED: gains repetition_rule field
│       └── edit_task.py            # MODIFIED: gains repetition_rule field
├── service/
│   ├── domain.py                   # MODIFIED: repetition merge/validation logic
│   └── payload.py                  # MODIFIED: repetition -> RRULE for bridge
├── repository/
│   └── hybrid.py                   # MODIFIED: _build_repetition_rule calls parse_rrule
├── bridge/
│   └── adapter.py                  # MODIFIED: _adapt_repetition_rule calls parse_rrule
└── tests/doubles/
    └── bridge.py                   # MODIFIED: InMemoryBridge handles repetition writes
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `rrule/parser.py` | RRULE string -> `FrequencySpec` Pydantic model | Called by `hybrid.py`, `adapter.py` |
| `rrule/builder.py` | `FrequencySpec` -> RRULE string | Called by `payload.py` |
| `models/common.py` | New `RepetitionRule` with structured fields (read model) | Consumed by `Task`, `Project` via `ActionableEntity` |
| `contracts/.../edit_task.py` | `repetition_rule: PatchOrClear[RepetitionRuleSpec]` on command/payload | Agent -> service boundary |
| `contracts/.../add_task.py` | `repetition_rule: RepetitionRuleSpec | None` on command/payload | Agent -> service boundary |
| `service/domain.py` | Merge logic, validation, no-op detection for repetition | Reads current task state, calls `build_rrule` |
| `service/payload.py` | Converts structured spec -> flat bridge fields via `build_rrule` | Produces repo payload |
| `bridge/adapter.py` | Converts bridge RRULE + metadata -> structured fields via `parse_rrule` | Bridge read path |
| `repository/hybrid.py` | Converts SQLite RRULE + columns -> structured fields via `parse_rrule` | SQLite read path |

## Data Flow: Complete Paths

### Read Path (SQLite -- primary)

```
SQLite row
  ├── repetitionRuleString: "FREQ=WEEKLY;BYDAY=MO,WE"
  ├── repetitionScheduleTypeString: "fixed"
  ├── repetitionAnchorDateKey: "dateDue"
  └── catchUpAutomatically: 1

  → hybrid.py::_build_repetition_rule()
    ├── Calls parse_rrule("FREQ=WEEKLY;BYDAY=MO,WE") -> FrequencySpec(type="weekly", onDays=["MO","WE"])
    ├── Maps schedule_type: "fixed" + catchUp=True -> "regularly_with_catch_up"
    ├── Maps anchor_date_key: "dateDue" -> "due_date"
    └── Returns structured dict matching new RepetitionRule model

  → Pydantic validation -> RepetitionRule with:
    ├── frequency: FrequencySpec(type="weekly", interval=1, on_days=["MO","WE"])
    ├── schedule: "regularly_with_catch_up"
    ├── based_on: "due_date"
    └── end: None
```

### Read Path (Bridge -- fallback)

```
Bridge JSON (raw bridge format):
  repetitionRule: {
    ruleString: "FREQ=WEEKLY;BYDAY=MO,WE",
    scheduleType: "Regularly",         # PascalCase from OmniJS
    anchorDateKey: "DueDate",          # PascalCase from OmniJS
    catchUpAutomatically: true
  }

  → adapter.py::_adapt_repetition_rule()
    ├── Calls parse_rrule() on ruleString -> FrequencySpec
    ├── Maps scheduleType + catchUp -> schedule enum
    ├── Maps anchorDateKey -> basedOn enum
    ├── Restructures to new shape IN-PLACE
    └── Result matches new RepetitionRule model for Pydantic
```

### Write Path (edit_tasks -- partial update)

```
Agent sends:
  { "repetitionRule": { "frequency": { "type": "weekly", "onDays": ["MO","FR"] } } }

  → server.py: Pydantic validates -> EditTaskCommand
    ├── repetition_rule: RepetitionRuleSpec (structured, not UNSET, not None)

  → service.py::_EditTaskPipeline
    ├── _verify_task_exists() -> fetches current Task (has existing repetition_rule)
    ├── _process_repetition() [NEW STEP]
    │   ├── DomainLogic.process_repetition(spec, current_task)
    │   │   ├── Current task HAS rule -> merge mode
    │   │   │   ├── Same type ("weekly") -> merge: onDays=["MO","FR"] replaces old, interval preserved
    │   │   │   ├── Root fields (schedule, basedOn, end) not in spec -> preserve from existing
    │   │   │   └── Returns merged RepetitionRuleSpec + build_rrule(merged.frequency) -> RRULE string
    │   │   ├── Current task has NO rule -> error: "provide complete rule"
    │   │   └── Type CHANGE -> error if frequency fields incomplete
    │   └── Returns (rrule_string, schedule, based_on, catch_up, warnings)

  → payload.py::PayloadBuilder.build_edit()
    ├── Receives repetition fields from domain result
    ├── Adds to EditTaskRepoPayload:
    │   ├── rule_string: str
    │   ├── schedule_type: str  (bridge format: "Regularly"/"FromCompletion")
    │   ├── anchor_date_key: str (bridge format: "DueDate"/"DeferDate"/"PlannedDate")
    │   └── catch_up_automatically: bool

  → BridgeWriteMixin._send_to_bridge("edit_task", payload)
    ├── model_dump(by_alias=True, exclude_unset=True)
    ├── Sends: { ruleString, scheduleType, anchorDateKey, catchUpAutomatically }
    └── Bridge.js creates new Task.RepetitionRule(...) and assigns
```

### Write Path (edit_tasks -- clear)

```
Agent sends:
  { "repetitionRule": null }

  → EditTaskCommand.repetition_rule = None (PatchOrClear: None means "clear")

  → DomainLogic: null -> set bridge repetition to null
  → Payload: repetition_rule_clear: true (or equivalent signal)
  → Bridge: task.repetitionRule = null
```

### Write Path (add_tasks -- create with rule)

```
Agent sends:
  { "name": "Weekly standup",
    "repetitionRule": {
      "frequency": { "type": "weekly", "onDays": ["MO"] },
      "schedule": "regularly_with_catch_up",
      "basedOn": "due_date"
    }
  }

  → AddTaskCommand: validates all required fields present
  → PayloadBuilder: build_rrule(frequency) -> "FREQ=WEEKLY;BYDAY=MO"
  → AddTaskRepoPayload gains: ruleString, scheduleType, anchorDateKey, catchUpAutomatically
  → Bridge creates task AND assigns repetition rule in one step
```

## Model Taxonomy Changes

### Read Model (models/common.py)

Current `RepetitionRule`:
```python
class RepetitionRule(OmniFocusBaseModel):
    rule_string: str
    schedule_type: ScheduleType
    anchor_date_key: AnchorDateKey
    catch_up_automatically: bool
```

New `RepetitionRule` (breaking change):
```python
class RepetitionRule(OmniFocusBaseModel):
    """Read model: structured repetition rule on Task/Project."""
    frequency: FrequencySpec          # Discriminated union by type
    schedule: Schedule                # "regularly" | "regularly_with_catch_up" | "from_completion"
    based_on: BasedOn                 # "due_date" | "defer_date" | "planned_date"
    end: RepetitionEnd | None = None  # {"date": ...} or {"occurrences": N} or None
```

`FrequencySpec` is a discriminated union (Pydantic `Discriminator` on `type` field). Eight concrete types, all sharing `type: Literal[...]` and `interval: int = 1`.

### Command Models (contracts/)

**EditTaskCommand** gains:
```python
repetition_rule: PatchOrClear[RepetitionRuleSpec] = UNSET
```
- UNSET = no change (omitted)
- None = clear repetition rule
- RepetitionRuleSpec = set/modify

**AddTaskCommand** gains:
```python
repetition_rule: RepetitionRuleSpec | None = None
```
- None = no repetition (default)
- RepetitionRuleSpec = create with rule

`RepetitionRuleSpec` is the write-side model -- all root fields optional (for partial updates on edit), but frequency.type always required when frequency is provided.

### RepoPayload Models

**EditTaskRepoPayload** gains:
```python
# Flat fields matching bridge.js expectations (camelCase via alias)
rule_string: str | None = None
schedule_type: str | None = None          # Bridge-format: "Regularly", "FromCompletion"
anchor_date_key: str | None = None        # Bridge-format: "DueDate", etc.
catch_up_automatically: bool | None = None
clear_repetition_rule: bool | None = None # Signal to set task.repetitionRule = null
```

**AddTaskRepoPayload** gains same fields (minus clear).

Flat rather than nested because the bridge expects flat parameters, and the repo payload is bridge-ready by design.

### Enum Changes (models/enums.py)

**Existing `ScheduleType`** -- RETIRE or repurpose. Currently has 2 values (`regularly`, `from_completion`). The new agent-facing model uses 3 values.

**New enums** (or Literal types):
```python
class Schedule(StrEnum):
    """Agent-facing schedule type (3 values)."""
    REGULARLY = "regularly"
    REGULARLY_WITH_CATCH_UP = "regularly_with_catch_up"
    FROM_COMPLETION = "from_completion"

class BasedOn(StrEnum):
    """Agent-facing anchor date (renamed from AnchorDateKey)."""
    DUE_DATE = "due_date"
    DEFER_DATE = "defer_date"
    PLANNED_DATE = "planned_date"
```

`BasedOn` is functionally identical to `AnchorDateKey` but renamed for agent ergonomics. The old `AnchorDateKey` can stay as an internal alias or be retired.

### Mapping: Schedule <-> Bridge Format

| Agent `schedule` value | Bridge `scheduleType` | Bridge `catchUpAutomatically` |
|------------------------|----------------------|-------------------------------|
| `regularly` | `Regularly` | `false` |
| `regularly_with_catch_up` | `Regularly` | `true` |
| `from_completion` | `FromCompletion` | `false` (ignored by OmniFocus) |

| Agent `basedOn` value | Bridge `anchorDateKey` | SQLite `repetitionAnchorDateKey` |
|----------------------|----------------------|----------------------------------|
| `due_date` | `DueDate` | `dateDue` |
| `defer_date` | `DeferDate` | `dateToStart` |
| `planned_date` | `PlannedDate` | `datePlanned` |

### Mapping: Schedule <-> SQLite Format

| SQLite `repetitionScheduleTypeString` | SQLite `catchUpAutomatically` | Agent `schedule` |
|---------------------------------------|-------------------------------|------------------|
| `fixed` | 1 | `regularly_with_catch_up` |
| `fixed` | 0 | `regularly` |
| `from-assigned` | 1 | `regularly_with_catch_up` |
| `from-assigned` | 0 | `regularly` |
| `due-after-completion` | any | `from_completion` |
| `start-after-completion` | any | `from_completion` |
| `from-completion` | any | `from_completion` |

Note: the existing `_SCHEDULE_TYPE_MAP` in `hybrid.py` already handles the SQLite string variants but currently maps to the 2-value `ScheduleType`. Needs expansion to factor in `catchUpAutomatically`.

## Partial Update Merge Logic

### Where It Lives: `service/domain.py::DomainLogic`

New method: `process_repetition(spec, current_task) -> (merged_spec, warnings)`

Follows the same pattern as `compute_tag_diff` and `process_move`:
- Receives the command-layer spec and current task state
- Returns domain results the orchestrator can merge into the payload
- Handles all merge/validation/no-op logic

### Merge Rules

1. **`repetition_rule: UNSET`** (field omitted) -> no change, skip processing
2. **`repetition_rule: None`** (explicit null) -> clear repetition rule
3. **`repetition_rule: RepetitionRuleSpec`** with task having NO existing rule:
   - All required fields must be present: frequency (with type), schedule, basedOn
   - Missing required fields -> ValueError with educational message
4. **`repetition_rule: RepetitionRuleSpec`** with task having existing rule:
   - Root fields: independently updatable. Omitted = preserve from existing
   - Frequency omitted entirely -> preserve existing frequency
   - Frequency provided, same type -> merge: omitted fields preserved
   - Frequency provided, different type -> full replacement: all type-specific fields required
5. **No-op detection**: merged result identical to current -> warning, skip bridge call

### Integration in _EditTaskPipeline

New step `_process_repetition()` added between `_apply_move` and `_build_payload`:

```python
class _EditTaskPipeline(_Pipeline):
    async def execute(self, command: EditTaskCommand) -> EditTaskResult:
        await self._verify_task_exists()
        self._validate_and_normalize()
        self._resolve_actions()
        self._apply_lifecycle()
        self._check_completed_status()
        await self._apply_tag_diff()
        await self._apply_move()
        self._process_repetition()     # NEW -- synchronous, no async needed
        self._build_payload()

        if (early := self._detect_noop()) is not None:
            return early
        return await self._delegate()
```

`_process_repetition` is synchronous because:
- No resolution needed (no tag/parent name lookup)
- Current task is already fetched in `_verify_task_exists()`
- `parse_rrule` and `build_rrule` are pure functions

### Integration in _AddTaskPipeline

Simpler: no merge logic, just validate completeness and build:

```python
class _AddTaskPipeline(_Pipeline):
    async def execute(self, command: AddTaskCommand) -> AddTaskResult:
        self._validate()
        await self._resolve_parent()
        await self._resolve_tags()
        self._process_repetition()     # NEW -- validate + build RRULE
        self._build_payload()
        return await self._delegate()
```

## No-Op Detection Impact

The existing `_all_fields_match` in `DomainLogic` needs extension to compare repetition rules. Since the repo payload will carry flat RRULE fields, comparison should be done at the structured level before flattening -- or the current task's structured `RepetitionRule` is compared against the merged `RepetitionRuleSpec`.

Add to `_all_fields_match`:
```python
if "rule_string" in fields_set:
    # Compare existing structured rule against merged spec
    # This catches "agent sent the same rule that already exists"
    return False  # Conservative: if repetition fields are set, always send
```

Conservative approach recommended for v1: if any repetition field is set in the payload, skip no-op detection for repetition. Full structural comparison can come later.

## InMemoryBridge Changes

The `_handle_edit_task` method needs to handle repetition write params:

```python
# In _handle_edit_task:
if "ruleString" in params:
    task["repetitionRule"] = {
        "ruleString": params["ruleString"],
        "scheduleType": params.get("scheduleType"),
        "anchorDateKey": params.get("anchorDateKey"),
        "catchUpAutomatically": params.get("catchUpAutomatically", False),
    }
if params.get("clearRepetitionRule"):
    task["repetitionRule"] = None
```

Similarly for `_handle_add_task`.

## Golden Master Impact

Per GOLD-01: this milestone adds/modifies bridge operations for repetition rules. Golden master must be re-captured and new contract test scenarios added for:
- Task with repetition rule (all 8 frequency types if possible via real OmniFocus)
- Edit task: set repetition rule
- Edit task: modify repetition rule
- Edit task: clear repetition rule
- Add task with repetition rule

## Suggested Build Order

### Phase 1: Read Model Rewrite (foundation -- no write path yet)

1. **`rrule/parser.py`** + tests -- `parse_rrule(str) -> FrequencySpec`
   - Port from `.research/deep-dives/rrule-validator/rrule_validator.py` (directly portable)
   - Return Pydantic `FrequencySpec` models instead of dataclass
   - 79 existing tests from research spike as starting point

2. **New models** -- `FrequencySpec` discriminated union, new `RepetitionRule`, new enums
   - `Schedule` (3 values), `BasedOn` (3 values)
   - `FrequencySpec` hierarchy (8 types)
   - `RepetitionEnd` model (date or occurrences)
   - New `RepetitionRule` with structured fields

3. **SQLite read path** -- modify `hybrid.py::_build_repetition_rule`
   - Call `parse_rrule` on `repetitionRuleString`
   - Map schedule_type + catchUp -> `Schedule` enum
   - Map anchor_date_key -> `BasedOn` enum
   - Return dict matching new `RepetitionRule` shape

4. **Bridge read path** -- modify `adapter.py::_adapt_repetition_rule`
   - Same transformation but from bridge format (PascalCase)
   - Call `parse_rrule` on ruleString
   - Result is new-shape dict for Pydantic validation

5. **Tests**: model tests, parser tests, adapter/hybrid integration tests

### Phase 2: Write Model + Bridge + Service

1. **`rrule/builder.py`** + tests -- `build_rrule(FrequencySpec) -> str`
   - Port from research spike
   - Round-trip validation: `parse_rrule(build_rrule(spec)) == spec`

2. **Command models** -- `RepetitionRuleSpec` on `EditTaskCommand` and `AddTaskCommand`
   - Write-side model with all-optional root fields
   - `PatchOrClear[RepetitionRuleSpec]` on edit, `RepetitionRuleSpec | None` on add
   - Pydantic validators for type-specific constraints

3. **RepoPayload models** -- flat RRULE fields on `EditTaskRepoPayload` and `AddTaskRepoPayload`

4. **`service/domain.py`** -- `process_repetition()` merge logic
   - Merge rules implementation
   - No-op detection extension
   - Educational warnings

5. **`service/payload.py`** -- `build_edit`/`build_add` gain repetition field handling
   - Call `build_rrule` for the RRULE string
   - Map `Schedule` -> bridge scheduleType + catchUp
   - Map `BasedOn` -> bridge anchorDateKey

6. **`_EditTaskPipeline`** + **`_AddTaskPipeline`** -- wire `_process_repetition` step

7. **InMemoryBridge** -- handle repetition params in `_handle_edit_task` and `_handle_add_task`

8. **Bridge.js** -- handle repetition params in edit_task and add_task commands

9. **Golden master** -- re-capture and add contract test scenarios

10. **Server tool descriptions** -- update docstrings for `add_tasks` and `edit_tasks`

### Why This Order

- Phase 1 is independently shippable and testable -- read model works end-to-end
- Parser is needed by both read paths, so it must come first
- Builder is only needed by write path, so it can wait for Phase 2
- Command models depend on having the structured types from Phase 1
- Domain merge logic depends on both parser (to read current state) and builder (to produce output)
- InMemoryBridge and bridge.js are last because they're mechanical -- just accepting the params the service layer sends

## Anti-Patterns to Avoid

### Don't put RRULE logic in the bridge
The bridge is a relay. RRULE parsing/building is Python business logic. Bridge receives pre-built RRULE strings.

### Don't duplicate mapping logic
The schedule/basedOn enum mappings between agent format, bridge format, and SQLite format should have exactly one mapping table per direction. Current codebase already has this pattern (`_SCHEDULE_TYPE_MAP`, `_ANCHOR_DATE_MAP`). Extend, don't duplicate.

### Don't use model inheritance for frequency types
Use Pydantic discriminated unions (`Discriminator` on the `type` field), not a class hierarchy. Each frequency type is a standalone model with `type: Literal["weekly"]` etc. Keeps the JSON schema clean for LLM tool descriptions.

### Don't store structured fields in the repo payload
The repo payload is bridge-ready. Bridge expects flat `(ruleString, scheduleType, anchorDateKey, catchUpAutomatically)`. The structured -> flat conversion happens in `PayloadBuilder`, not later.

### Don't skip parse_rrule on the read path
Even though the SQLite row has the RRULE string, it still needs parsing into structured `FrequencySpec`. Don't return the raw string -- the whole point is structured fields in the read model.

## Sources

- Codebase analysis: all files listed in Component Boundaries table
- `.research/deep-dives/rrule-validator/rrule_validator.py` -- working parser/builder prototype (79 tests)
- `.research/deep-dives/repetition-rule/repetition-rule-guide.md` -- OmniJS API reference
- `docs/architecture.md` lines 480-658 -- pre-designed target architecture
- `.research/updated-spec/MILESTONE-v1.2.3.md` -- milestone specification
