# Phase 33: Write Model, Validation & Bridge - Research

**Researched:** 2026-03-28
**Domain:** Pydantic write models, service-layer validation, OmniJS bridge extension, tool documentation
**Confidence:** HIGH

## Summary

Phase 33 extends the existing `add_tasks` and `edit_tasks` write pipeline with repetition rule support. The codebase already has every building block: `build_rrule()` converts Frequency models to RRULE strings, `derive_schedule()` maps schedule types (needing a trivial inverse), the Method Object pipeline pattern is battle-tested in both `_AddTaskPipeline` and `_EditTaskPipeline`, and the `UNSET`/`Patch`/`PatchOrClear` sentinel system handles three-way patch semantics throughout. The bridge already reads repetition rules via the `rr()` function with `rst()` and `adk()` enum resolvers -- writes need the inverse direction.

The work is high-confidence because every pattern needed already exists in the codebase. No new libraries, no new architectural concepts. The primary complexity is the edit-path frequency merge logic (same-type preserves omitted fields, different-type requires full replacement) and ensuring comprehensive validation catches all invalid inputs before they reach the bridge.

**Primary recommendation:** Layer the implementation bottom-up: contracts/specs first, then validation, then service pipeline steps, then bridge JS, then tool descriptions. Each layer is independently testable.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Nested wrapper approach. `EditTaskCommand` gets `repetition_rule: PatchOrClear[RepetitionRuleEditSpec] = UNSET`. The spec has inner `Patch` fields so root-level fields (schedule, basedOn, end) are independently patchable. `null` clears the whole rule. `UNSET` means no change.
- **D-02:** Frequency merge is a service-layer concern. `type` is required on every frequency update (Pydantic discriminated union requires it). Service compares submitted type vs existing type: same -> merge, different -> require full frequency. No existing rule + partial update -> error. Design for evolution toward Phase 33.1 flat frequency model.
- **D-03:** Two dedicated spec models in `contracts/`: `RepetitionRuleAddSpec(CommandModel)` (all fields required, end optional, `extra="forbid"`) and `RepetitionRuleEditSpec(CommandModel)` (Patch/PatchOrClear fields for independent updates).
- **D-04:** Noun-first naming: `RepetitionRuleAddSpec` / `RepetitionRuleEditSpec`. Add a comment explaining this convention.
- **D-05:** Both specs embed the `Frequency` union for now. Accepted gap: Frequency is `OmniFocusBaseModel` not `CommandModel`. Phase 33.1 fixes this.
- **D-06:** `AddTaskCommand` embeds `RepetitionRuleAddSpec | None = None`. `EditTaskCommand` embeds `PatchOrClear[RepetitionRuleEditSpec] = UNSET`.
- **D-07:** 4-field bridge format: `{ruleString, scheduleType, anchorDateKey, catchUpAutomatically}`. Symmetric with read path.
- **D-08:** Bridge constructs `new Task.RepetitionRule(ruleString, null, scheduleType, anchorDateKey, catchUpAutomatically)`. Second param always `null`. Needs reverse enum lookups.
- **D-09:** Clearing: `task.repetitionRule = null`. Dates remain unchanged.
- **D-10:** All RepetitionRule properties are read-only. Modification = construct new + assign.
- **D-11:** Error catalog: type change with incomplete frequency, no existing rule + partial update, invalid structures, cross-type fields.
- **D-12:** Warning catalog: end date in past, monthly_day_in_month with empty onDates, no-op same rule, setting repetition on completed/dropped task.
- **D-13:** monthly_day_in_month with empty onDates normalizes to plain monthly + warning.
- **D-14:** Full inline documentation in tool docstrings (inputSchema is opaque).
- **D-15:** Hierarchical format: each frequency type shows complete shape on one line.
- **D-16:** 2-3 examples per tool.
- **D-17:** Different language for add vs edit (omit vs null-to-clear).
- Tool description templates provided in CONTEXT.md -- use as starting point.

### Claude's Discretion

- RRULE builder inverse functions (Schedule -> scheduleType/catchUp, BasedOn -> anchorDateKey)
- Service pipeline step ordering and internal merge algorithm
- Bridge JS reverse enum lookup implementation
- Test structure and organization
- Exact warning/error message wording (existing agent_messages/ patterns as style guide)
- Whether to keep `interval: N` in description or refine

### Deferred Ideas (OUT OF SCOPE)

- Phase 33.1: Flat Frequency Model (type-optional edits, interval serialization fix, model hierarchy simplification)
- Typed inputSchema for write tools (opaque dict stays for now)
- Old test names referencing FrequencySpec

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ADD-01 | Create task with repetition rule (frequency+schedule+basedOn required) | RepetitionRuleAddSpec model with required fields; AddTaskPipeline step; bridge handleAddTask extension |
| ADD-02 | All 9 frequency types supported for creation | Frequency discriminated union already exists; build_rrule() handles all 9 |
| ADD-03 | Interval > 1 supported | _FrequencyBase.interval field; build_rrule() INTERVAL param |
| ADD-04 | Weekly onDays with case-insensitive normalization | WeeklyOnDaysFrequency.on_days; validation normalizes to uppercase |
| ADD-05 | Weekly without onDays repeats from basedOn date | WeeklyFrequency (bare) produces FREQ=WEEKLY only |
| ADD-06 | monthly_day_of_week on field with ordinal/day | MonthlyDayOfWeekFrequency.on dict; builder _build_byday_positional() |
| ADD-07 | monthly_day_in_month onDates field | MonthlyDayInMonthFrequency.on_dates; builder BYMONTHDAY generation |
| ADD-08 | monthly_day_in_month empty onDates -> warning | Service normalize+warn pattern (D-13) |
| ADD-09 | All 3 schedule values work | Schedule enum; inverse derive_schedule maps to (scheduleType, catchUp) |
| ADD-10 | All 3 basedOn values work | BasedOn enum; inverse maps to anchorDateKey string |
| ADD-11 | End by date supported | EndByDate model; build_rrule() UNTIL param |
| ADD-12 | End by occurrences supported | EndByOccurrences model; build_rrule() COUNT param |
| ADD-13 | No end (omitted) = open-ended | end optional field defaults None |
| ADD-14 | Interval defaults to 1 when omitted | _FrequencyBase.interval default=1 |
| EDIT-01 | Set repetition rule on non-repeating task (full rule required) | EditTaskPipeline detects no existing rule, validates all fields present |
| EDIT-02 | Remove repetition rule (null) | PatchOrClear[...] = null -> bridge `task.repetitionRule = null` |
| EDIT-03 | Omitting repetitionRule = no change (UNSET) | PatchOrClear default=UNSET, is_set() gate |
| EDIT-04 | Change schedule without resending frequency | RepetitionRuleEditSpec: schedule as Patch, frequency as Patch |
| EDIT-05 | Change basedOn without resending frequency | Same independent patchability |
| EDIT-06 | Add end condition | end as PatchOrClear on EditSpec |
| EDIT-07 | Remove end condition (null) | PatchOrClear null semantics |
| EDIT-08 | Change end type | Full replacement of end field |
| EDIT-09 | Same-type frequency merge | Service compares type, preserves omitted fields from existing |
| EDIT-10 | Change interval on same type | Merge: only interval changes, other fields preserved |
| EDIT-11 | Change onDays on weekly | Merge: on_days changes, interval preserved |
| EDIT-12 | Change on field on monthly_day_of_week | Merge: on changes, interval preserved |
| EDIT-13 | Change frequency type = full replacement | Service requires complete frequency for type change |
| EDIT-14 | Type change with incomplete frequency -> error | Service validation with educational error message |
| EDIT-15 | No existing rule + partial update -> error | Service checks task.repetition_rule is not None |
| EDIT-16 | No-op detection with warning | DomainLogic.detect_early_return extension |
| VALID-01 | Pydantic rejects invalid structures | CommandModel extra="forbid"; Pydantic discriminator validation |
| VALID-02 | Type-specific constraints | Custom validator: cross-type field rejection, range checks |
| VALID-03 | Educational error messages | agent_messages/errors.py constants following existing patterns |
| VALID-04 | Tool descriptions document schema | Inline docstrings per D-14/D-15/D-16/D-17 templates |
| VALID-05 | End date in past -> warning | DomainLogic warning check, agent_messages/warnings.py constant |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **SAFE-01/02**: No automated tests touch the real Bridge. InMemoryBridge or SimulatorBridge only. Use `the real Bridge` in prose, never the class name.
- **Service Layer Convention**: Method Object pattern -- `_VerbNounPipeline` inheriting `_Pipeline`. Mutable state on `self` is fine.
- **Model Conventions**: Read `docs/architecture.md` naming taxonomy before creating models. `models/` = no write-side suffixes. `contracts/` = must use suffix. After modifying tool output models, run `test_output_schema.py`.
- **UAT Guidelines**: Feature phases focus on user-observable behavior (does the feature work from agent's perspective).
- `test_output_schema.py` must pass after any model change in tool output.

## Architecture Patterns

### Existing Layer Topology (extend, don't restructure)

```
Agent JSON
  |
server.py          -- ValidationError handling, tool docstrings
  |
contracts/         -- AddTaskCommand, EditTaskCommand (+ new RepetitionRuleAddSpec, RepetitionRuleEditSpec)
  |
service/service.py -- _AddTaskPipeline, _EditTaskPipeline (+ new repetition rule steps)
  |
service/validate.py    -- Pure input validation (+ repetition rule validators)
service/domain.py      -- Business rules, warnings (+ repetition rule domain logic)
service/payload.py     -- PayloadBuilder (+ repetition rule serialization)
  |
contracts/             -- AddTaskRepoPayload, EditTaskRepoPayload (+ repetition_rule field)
  |
repository/            -- model_dump(by_alias=True, exclude_unset=True) -> bridge
  |
bridge/bridge.js       -- handleAddTask, handleEditTask (+ RepetitionRule construction/clearing)
```

### New Contract Models

**RepetitionRuleAddSpec** (in `contracts/use_cases/` or `contracts/`):
- Inherits `CommandModel` (`extra="forbid"`)
- Fields: `frequency: Frequency` (required), `schedule: Schedule` (required), `based_on: BasedOn` (required), `end: EndCondition | None = None`
- Reuses read-side types: `Frequency` union, `Schedule`/`BasedOn` enums, `EndCondition` union

**RepetitionRuleEditSpec** (same location):
- Inherits `CommandModel` (`extra="forbid"`)
- Fields: `frequency: Patch[Frequency] = UNSET`, `schedule: Patch[Schedule] = UNSET`, `based_on: Patch[BasedOn] = UNSET`, `end: PatchOrClear[EndCondition] = UNSET`

### Pipeline Extension Points

**_AddTaskPipeline.execute()** -- add step after `_resolve_tags()`:
```python
async def execute(self, command):
    self._validate()
    await self._resolve_parent()
    await self._resolve_tags()
    self._validate_repetition_rule()   # NEW
    self._build_payload()
    return await self._delegate()
```

**_EditTaskPipeline.execute()** -- add step after `_check_completed_status()`:
```python
async def execute(self, command):
    await self._verify_task_exists()
    self._validate_and_normalize()
    self._resolve_actions()
    self._apply_lifecycle()
    self._check_completed_status()
    await self._apply_repetition_rule()  # NEW (needs self._task for existing rule)
    await self._apply_tag_diff()
    await self._apply_move()
    self._build_payload()
    ...
```

### Bridge Payload Format

The bridge receives a flat dict. Repetition rule adds one key for add, and one key with clear/set semantics for edit:

**Add payload** (via model_dump):
```json
{
  "name": "...",
  "repetitionRule": {
    "ruleString": "FREQ=DAILY;INTERVAL=3",
    "scheduleType": "Regularly",
    "anchorDateKey": "DueDate",
    "catchUpAutomatically": false
  }
}
```

**Edit payload** -- set:
```json
{
  "id": "...",
  "repetitionRule": { ...same shape... }
}
```

**Edit payload** -- clear:
```json
{
  "id": "...",
  "repetitionRule": null
}
```

### Schedule/BasedOn Inverse Mappings

`derive_schedule()` is the forward mapping (read path). Write path needs:

```python
def schedule_to_bridge(schedule: Schedule) -> tuple[str, bool]:
    """Inverse of derive_schedule: Schedule -> (scheduleType, catchUpAutomatically)."""
    if schedule == Schedule.FROM_COMPLETION:
        return ("FromCompletion", False)
    if schedule == Schedule.REGULARLY_WITH_CATCH_UP:
        return ("Regularly", True)
    return ("Regularly", False)

def based_on_to_bridge(based_on: BasedOn) -> str:
    """BasedOn enum -> OmniJS anchorDateKey string."""
    return {
        BasedOn.DUE_DATE: "DueDate",
        BasedOn.DEFER_DATE: "DeferDate",
        BasedOn.PLANNED_DATE: "PlannedDate",
    }[based_on]
```

### Bridge JS Reverse Enum Lookups

Existing `rst()` and `adk()` are forward (OmniJS enum -> string). Write path needs reverse:

```javascript
function reverseRst(s) {
    if (s === "Regularly") return Task.RepetitionScheduleType.Regularly;
    if (s === "FromCompletion") return Task.RepetitionScheduleType.FromCompletion;
    throw new Error("Unknown scheduleType string: " + s);
}

function reverseAdk(s) {
    if (s === "DueDate") return Task.AnchorDateKey.DueDate;
    if (s === "DeferDate") return Task.AnchorDateKey.DeferDate;
    if (s === "PlannedDate") return Task.AnchorDateKey.PlannedDate;
    throw new Error("Unknown anchorDateKey string: " + s);
}
```

### Anti-Patterns to Avoid

- **Never push merge logic to Pydantic validators**: Frequency merge is a service concern (D-02). Pydantic validates structure; service applies domain rules.
- **Never mutate existing RepetitionRule on bridge**: OmniJS properties are read-only (D-10). Always construct new.
- **Never reuse read-model classes in command fields directly**: Phase 33 accepts the Frequency gap (D-05), but RepetitionRuleAddSpec/EditSpec must be `CommandModel` subclasses.
- **Never add `repetitionRule` to `exclude_unset=True` special-case logic**: The existing `model_dump(by_alias=True, exclude_unset=True)` pattern in `BridgeWriteMixin._send_to_bridge()` handles it automatically.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RRULE string generation | Custom string concatenation | `build_rrule(frequency, end)` | Already implemented, round-trip validated |
| Schedule forward mapping | Manual if/else | `derive_schedule()` in `rrule/schedule.py` | Single source of truth, already tested |
| Discriminated union validation | Manual type checking | Pydantic `Field(discriminator="type")` | Already defined in `models/repetition_rule.py` |
| Three-way patch semantics | Custom sentinel pattern | `UNSET`/`Patch[T]`/`PatchOrClear[T]` from `contracts/base.py` | Battle-tested on dates, note, estimatedMinutes |
| Bridge payload serialization | Manual dict building | `model_dump(by_alias=True, exclude_unset=True)` via `BridgeWriteMixin` | Repository layer handles this generically |

## Common Pitfalls

### Pitfall 1: Frequency Union Serialization in Nested CommandModel

**What goes wrong:** When a `CommandModel` (extra="forbid") embeds the read-side `Frequency` union (which is `OmniFocusBaseModel`, no extra="forbid"), Pydantic may let extra fields through on the Frequency object because the inner model doesn't forbid them.
**Why it happens:** Phase 33 D-05 acknowledges this gap. The discriminated union provides structural validation (type field selects the right subclass), but cross-type fields won't be rejected by Pydantic alone.
**How to avoid:** Add explicit service-layer validation for cross-type fields (e.g., `onDays` on `daily`). This is already the plan per D-02 and VALID-02.
**Warning signs:** Tests pass validation that should fail. An agent sends `{type: "daily", onDays: ["MO"]}` and it silently drops `onDays`.

### Pitfall 2: Edit Merge When Task Has No Existing Rule

**What goes wrong:** Agent sends `{repetitionRule: {schedule: "from_completion"}}` to a task with no existing rule. Service tries to merge with `None` and crashes or silently creates an incomplete rule.
**Why it happens:** Partial update assumes there's an existing rule to merge with.
**How to avoid:** Explicit check: if `task.repetition_rule is None` and the edit spec doesn't provide a complete rule (frequency + schedule + basedOn), raise ValueError with educational error (EDIT-15).
**Warning signs:** No test covering "partial update on non-repeating task."

### Pitfall 3: PatchOrClear[RepetitionRuleEditSpec] Deserialization

**What goes wrong:** Pydantic sees `repetitionRule: {}` (empty object) and might validate it as a valid EditSpec with all UNSET fields, when the agent probably meant something else.
**Why it happens:** All fields on EditSpec default to UNSET, so an empty object is technically valid.
**How to avoid:** The service layer should detect "all UNSET" on the EditSpec and treat it as a no-op (or raise a "no changes specified" warning). This follows the existing `_is_empty_edit()` pattern.
**Warning signs:** Missing test for empty `{}` repetition rule edit.

### Pitfall 4: Bridge enum string mismatch

**What goes wrong:** Python sends `"Regularly"` as scheduleType but the JS reverse lookup expects a different casing or format.
**Why it happens:** The forward resolver `rst()` returns `"Regularly"` and `"FromCompletion"`. The reverse must match these exact strings.
**How to avoid:** Use the same string constants that `rst()` and `adk()` return. The Python side maps Schedule/BasedOn enums to these bridge strings.
**Warning signs:** Bridge throws "Unknown scheduleType string" errors during UAT.

### Pitfall 5: model_dump exclude_unset Interaction with Nested Specs

**What goes wrong:** When serializing `EditTaskRepoPayload` with `exclude_unset=True`, if `repetition_rule` is set but its inner fields use UNSET, the nested dict might include UNSET sentinel values.
**Why it happens:** `exclude_unset=True` only excludes fields not in `model_fields_set` -- UNSET values that were explicitly set (as defaults) still appear.
**How to avoid:** The service layer must fully resolve the EditSpec into a flat bridge-format dict (ruleString, scheduleType, anchorDateKey, catchUpAutomatically) or `None`. The RepoPayload gets the final resolved dict, not the raw EditSpec.
**Warning signs:** Bridge receives Python object representations instead of JSON-serializable values.

### Pitfall 6: InMemoryBridge Needs Repetition Rule Write Support

**What goes wrong:** Tests pass at the service level but InMemoryBridge's `_handle_add_task()` and `_handle_edit_task()` don't handle the new `repetitionRule` payload field, so integration tests silently ignore repetition rules.
**Why it happens:** InMemoryBridge has explicit field handling -- new fields aren't automatically supported.
**How to avoid:** Extend `_handle_add_task()` to store `repetitionRule` dict on the task. Extend `_handle_edit_task()` to set/clear/update `repetitionRule`.
**Warning signs:** Service tests pass but simulator/integration tests don't verify the repetition rule was actually set.

## Code Examples

### AddTaskRepoPayload with Repetition Rule

```python
# Source: Existing pattern in contracts/use_cases/add_task.py
class AddTaskRepoPayload(CommandModel):
    name: str
    parent: str | None = None
    tag_ids: list[str] | None = None
    # ... existing fields ...
    repetition_rule: RepetitionRuleRepoPayload | None = None  # NEW
```

The repo payload uses a bridge-ready format (ruleString, scheduleType, etc.), not the agent-facing spec:

```python
class RepetitionRuleRepoPayload(CommandModel):
    """Bridge-ready repetition rule -- fully resolved, no Patch/UNSET."""
    rule_string: str          # serializes as ruleString
    schedule_type: str        # serializes as scheduleType ("Regularly" / "FromCompletion")
    anchor_date_key: str      # serializes as anchorDateKey ("DueDate" / "DeferDate" / "PlannedDate")
    catch_up_automatically: bool  # serializes as catchUpAutomatically
```

### PayloadBuilder Extension

```python
# Source: Existing pattern in service/payload.py
def build_add(self, command, resolved_tag_ids):
    kwargs = {"name": command.name}
    # ... existing field handling ...
    if command.repetition_rule is not None:
        kwargs["repetition_rule"] = self._build_repetition_rule_payload(
            command.repetition_rule
        )
    return AddTaskRepoPayload.model_validate(kwargs)

def _build_repetition_rule_payload(self, spec):
    """Convert RepetitionRuleAddSpec -> RepetitionRuleRepoPayload."""
    rule_string = build_rrule(spec.frequency, spec.end)
    schedule_type, catch_up = schedule_to_bridge(spec.schedule)
    anchor_date_key = based_on_to_bridge(spec.based_on)
    return RepetitionRuleRepoPayload(
        rule_string=rule_string,
        schedule_type=schedule_type,
        anchor_date_key=anchor_date_key,
        catch_up_automatically=catch_up,
    )
```

### Bridge JS RepetitionRule Construction

```javascript
// Source: OmniJS API guide, lines 38-47
if (params.hasOwnProperty("repetitionRule")) {
    if (params.repetitionRule === null) {
        task.repetitionRule = null;
    } else {
        var rr = params.repetitionRule;
        task.repetitionRule = new Task.RepetitionRule(
            rr.ruleString,
            null,  // deprecated method param
            reverseRst(rr.scheduleType),
            reverseAdk(rr.anchorDateKey),
            rr.catchUpAutomatically
        );
    }
}
```

### Service Edit Merge Logic (Conceptual)

```python
def _apply_repetition_rule(self):
    """Merge agent's edit spec with existing rule, validate, prepare bridge payload."""
    spec = self._command.repetition_rule
    if not is_set(spec):
        self._repetition_rule_payload = None  # UNSET -> no change
        return

    if spec is None:
        self._repetition_rule_payload = None  # Clear sentinel
        self._repetition_rule_clear = True
        return

    existing = self._task.repetition_rule  # RepetitionRule | None

    # Resolve each field: use spec value if set, else existing, else error
    frequency = self._resolve_frequency(spec, existing)
    schedule = spec.schedule if is_set(spec.schedule) else (existing.schedule if existing else None)
    based_on = spec.based_on if is_set(spec.based_on) else (existing.based_on if existing else None)
    end = self._resolve_end(spec, existing)

    # Validate completeness
    if frequency is None or schedule is None or based_on is None:
        raise ValueError("...")  # Educational error per EDIT-15

    # Build bridge payload
    self._repetition_rule_payload = ...
```

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.x + pytest-asyncio 1.3+ |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_service.py -x -q` |
| Full suite command | `uv run pytest -x -q` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ADD-01 | Create task with repetition rule | unit (service) | `uv run pytest tests/test_service.py -x -q -k "add_task and repetition"` | Wave 0 |
| ADD-02 | All 9 frequency types on creation | unit (service) | `uv run pytest tests/test_service.py -x -q -k "add_task and frequency_type"` | Wave 0 |
| ADD-03 | Interval > 1 | unit (service) | `uv run pytest tests/test_service.py -x -q -k "interval"` | Wave 0 |
| ADD-04 | onDays case normalization | unit (validate) | `uv run pytest tests/test_service.py -x -q -k "on_days"` | Wave 0 |
| ADD-05 | Weekly bare (no onDays) | unit (service) | `uv run pytest tests/test_service.py -x -q -k "weekly_bare"` | Wave 0 |
| ADD-06 | monthly_day_of_week on field | unit (service) | `uv run pytest tests/test_service.py -x -q -k "day_of_week"` | Wave 0 |
| ADD-07 | monthly_day_in_month onDates | unit (service) | `uv run pytest tests/test_service.py -x -q -k "day_in_month"` | Wave 0 |
| ADD-08 | Empty onDates -> warning | unit (domain) | `uv run pytest tests/test_service_domain.py -x -q -k "empty_on_dates"` | Wave 0 |
| ADD-09 | All 3 schedule values | unit (service) | `uv run pytest tests/test_service.py -x -q -k "schedule_value"` | Wave 0 |
| ADD-10 | All 3 basedOn values | unit (service) | `uv run pytest tests/test_service.py -x -q -k "based_on_value"` | Wave 0 |
| ADD-11 | End by date | unit (service) | `uv run pytest tests/test_service.py -x -q -k "end_date"` | Wave 0 |
| ADD-12 | End by occurrences | unit (service) | `uv run pytest tests/test_service.py -x -q -k "end_occurrences"` | Wave 0 |
| ADD-13 | No end = open-ended | unit (service) | `uv run pytest tests/test_service.py -x -q -k "no_end"` | Wave 0 |
| ADD-14 | Interval defaults to 1 | unit (contracts) | `uv run pytest tests/test_service.py -x -q -k "interval_default"` | Wave 0 |
| EDIT-01 | Set rule on non-repeating task | unit (service) | `uv run pytest tests/test_service.py -x -q -k "edit and set_rule"` | Wave 0 |
| EDIT-02 | Remove repetition rule (null) | unit (service) | `uv run pytest tests/test_service.py -x -q -k "edit and clear_rule"` | Wave 0 |
| EDIT-03 | UNSET = no change | unit (service) | `uv run pytest tests/test_service.py -x -q -k "edit and unset"` | Wave 0 |
| EDIT-04 | Change schedule only | unit (service) | `uv run pytest tests/test_service.py -x -q -k "edit and schedule_only"` | Wave 0 |
| EDIT-05 | Change basedOn only | unit (service) | `uv run pytest tests/test_service.py -x -q -k "edit and based_on_only"` | Wave 0 |
| EDIT-06 | Add end condition | unit (service) | `uv run pytest tests/test_service.py -x -q -k "edit and add_end"` | Wave 0 |
| EDIT-07 | Remove end condition | unit (service) | `uv run pytest tests/test_service.py -x -q -k "edit and remove_end"` | Wave 0 |
| EDIT-08 | Change end type | unit (service) | `uv run pytest tests/test_service.py -x -q -k "edit and change_end_type"` | Wave 0 |
| EDIT-09 | Same-type merge | unit (service) | `uv run pytest tests/test_service.py -x -q -k "edit and same_type_merge"` | Wave 0 |
| EDIT-10 | Change interval same type | unit (service) | `uv run pytest tests/test_service.py -x -q -k "edit and change_interval"` | Wave 0 |
| EDIT-11 | Change onDays | unit (service) | `uv run pytest tests/test_service.py -x -q -k "edit and change_on_days"` | Wave 0 |
| EDIT-12 | Change on field | unit (service) | `uv run pytest tests/test_service.py -x -q -k "edit and change_on_field"` | Wave 0 |
| EDIT-13 | Type change = full replacement | unit (service) | `uv run pytest tests/test_service.py -x -q -k "edit and type_change"` | Wave 0 |
| EDIT-14 | Type change incomplete -> error | unit (service) | `uv run pytest tests/test_service.py -x -q -k "edit and type_change_error"` | Wave 0 |
| EDIT-15 | No existing rule + partial -> error | unit (service) | `uv run pytest tests/test_service.py -x -q -k "edit and no_existing_rule"` | Wave 0 |
| EDIT-16 | No-op detection | unit (domain) | `uv run pytest tests/test_service_domain.py -x -q -k "repetition_noop"` | Wave 0 |
| VALID-01 | Pydantic rejects invalid structures | unit (contracts) | `uv run pytest tests/test_service.py -x -q -k "validation and invalid"` | Wave 0 |
| VALID-02 | Type-specific constraints | unit (validate) | `uv run pytest tests/test_service.py -x -q -k "cross_type"` | Wave 0 |
| VALID-03 | Educational error messages | unit (server) | `uv run pytest tests/test_server.py -x -q -k "repetition and error"` | Wave 0 |
| VALID-04 | Tool descriptions document schema | manual-only | Visual inspection of docstrings | N/A |
| VALID-05 | End date in past -> warning | unit (domain) | `uv run pytest tests/test_service_domain.py -x -q -k "end_date_past"` | Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_service.py tests/test_service_domain.py tests/test_service_payload.py -x -q`
- **Per wave merge:** `uv run pytest -x -q`
- **Phase gate:** Full suite green + `uv run pytest tests/test_output_schema.py -x -q` before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] Tests for `RepetitionRuleAddSpec` and `RepetitionRuleEditSpec` validation (new contract models)
- [ ] Tests for repetition rule validation functions (new in `service/validate.py`)
- [ ] Tests for repetition rule domain logic (warnings, merge, no-op) in `test_service_domain.py`
- [ ] Tests for repetition rule payload building in `test_service_payload.py`
- [ ] Tests for repetition rule in add_task and edit_task service tests in `test_service.py`
- [ ] Tests for bridge payload format verification (what InMemoryBridge receives)
- [ ] Tests for server-level validation error handling (repetition rule ValidationError formatting)
- [ ] InMemoryBridge needs `repetitionRule` handling in `_handle_add_task()` and `_handle_edit_task()`

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Raw RRULE string exposure | Structured Frequency union | Phase 32 (v1.2.3) | Agents never see RRULE strings |
| 4-field flat read model | Parsed structured RepetitionRule | Phase 32 | Clean API for agents |
| Manual input validation | Pydantic `extra="forbid"` + discriminated union | v1.2 | Catches typos at boundary |

## Open Questions

1. **RepoPayload Model Location**
   - What we know: `RepetitionRuleRepoPayload` (bridge-ready format) needs a home. Existing repo payloads live in `contracts/use_cases/add_task.py` and `edit_task.py`.
   - What's unclear: Should the bridge-format payload model be a shared model (used by both add and edit repo payloads), or embedded separately in each?
   - Recommendation: Shared model in a common contracts file or inline in the use case files. The shape is identical for both add and edit. Claude's discretion.

2. **Where to Place Inverse Mapping Functions**
   - What we know: `derive_schedule()` lives in `rrule/schedule.py`. The inverse (`schedule_to_bridge()` and `based_on_to_bridge()`) is conceptually similar.
   - What's unclear: Same file? New file in `rrule/`? In `service/payload.py`?
   - Recommendation: Same `rrule/schedule.py` file for schedule inverse (keeps forward/inverse together). `based_on_to_bridge()` could go there too or in payload.py. Claude's discretion.

3. **Edit No-Op Detection Scope**
   - What we know: Existing `_all_fields_match()` in `domain.py` compares payload fields against task state. Adding repetition rule comparison requires comparing the full rule structure.
   - What's unclear: How deep should no-op detection go? Compare RRULE string? Compare all 4 bridge fields? Compare the structured model?
   - Recommendation: Compare at the bridge-payload level (ruleString + scheduleType + anchorDateKey + catchUpAutomatically). If all 4 match the existing rule's equivalent values, it's a no-op. This is straightforward and matches the level at which the bridge operates.

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `contracts/base.py` (UNSET/Patch/PatchOrClear patterns)
- Codebase inspection: `service/service.py` (_AddTaskPipeline, _EditTaskPipeline method objects)
- Codebase inspection: `bridge/bridge.js` (handleAddTask, handleEditTask, enum resolvers)
- Codebase inspection: `rrule/builder.py` (build_rrule implementation)
- Codebase inspection: `rrule/schedule.py` (derive_schedule forward mapping)
- Codebase inspection: `models/repetition_rule.py` (Frequency union, EndCondition, RepetitionRule)
- Codebase inspection: `repository/bridge_write_mixin.py` (model_dump serialization pattern)
- OmniJS guide: `.research/deep-dives/repetition-rule/repetition-rule-guide.md` (constructor signature, read-only properties, clearing)
- Architecture docs: `docs/architecture.md` (naming taxonomy, write pipeline, model conventions)

### Secondary (MEDIUM confidence)
- `.research/updated-spec/MILESTONE-v1.2.3.md` (validation layers, partial update lifecycle)

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all existing libraries
- Architecture: HIGH -- extends existing patterns with no new concepts
- Pitfalls: HIGH -- all identified from direct codebase inspection and prior phase experience

**Research date:** 2026-03-28
**Valid until:** indefinite (architecture is stable, no external dependency changes)
