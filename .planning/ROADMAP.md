# Roadmap: OmniFocus Operator

## Milestones

- ✅ **v1.0 Foundation** — Phases 1-9 (shipped 2026-03-07)
- ✅ **v1.1 HUGE Performance Upgrade** — Phases 10-13 (shipped 2026-03-07)
- ✅ **v1.2 Writes & Lookups** — Phases 14-17 (shipped 2026-03-16)
- ✅ **v1.2.1 Architectural Cleanup** — Phases 18-28 (shipped 2026-03-23)
- ✅ **v1.2.2 FastMCP v3 Migration** — Phases 29-31 (shipped 2026-03-26)
- 🚧 **v1.2.3 Repetition Rule Write Support** — Phases 32-33 (in progress)

## Phases

<details>
<summary>✅ v1.0 Foundation (Phases 1-9) — SHIPPED 2026-03-07</summary>

- [x] Phase 1: Project Scaffolding (1/1 plans)
- [x] Phase 2: Data Models (2/2 plans)
- [x] Phase 3: Bridge Protocol and InMemoryBridge (1/1 plans)
- [x] Phase 4: Repository and Snapshot Management (1/1 plans)
- [x] Phase 5: Service Layer and MCP Server (3/3 plans)
- [x] Phase 6: File IPC Engine (3/3 plans)
- [x] Phase 7: SimulatorBridge and Mock Simulator (2/2 plans)
- [x] Phase 8: RealBridge and End-to-End Validation (2/2 plans)
- [x] Phase 8.1: JS Bridge Script and IPC Overhaul (3/4 plans -- 08.1-04 skipped)
- [x] Phase 8.2: Model Alignment with BRIDGE-SPEC (3/3 plans)
- [x] Phase 9: Error-Serving Degraded Mode (1/1 plans)

</details>

<details>
<summary>✅ v1.1 HUGE Performance Upgrade (Phases 10-13) — SHIPPED 2026-03-07</summary>

- [x] Phase 10: Model Overhaul (4/4 plans) — completed 2026-03-07
- [x] Phase 11: DataSource Protocol (3/3 plans) — completed 2026-03-07
- [x] Phase 12: SQLite Reader (2/2 plans) — completed 2026-03-07
- [x] Phase 13: Fallback and Integration (2/2 plans) — completed 2026-03-07

</details>

<details>
<summary>✅ v1.2 Writes & Lookups (Phases 14-17) — SHIPPED 2026-03-16</summary>

- [x] Phase 14: Model Refactor & Lookups (2/2 plans) — completed 2026-03-07
- [x] Phase 15: Write Pipeline & Task Creation (4/4 plans) — completed 2026-03-08
- [x] Phase 16: Task Editing (6/6 plans) — completed 2026-03-09
- [x] Phase 16.1: Actions Grouping (3/3 plans) — completed 2026-03-09
- [x] Phase 16.2: Bridge Tag Simplification (3/3 plans) — completed 2026-03-10
- [x] Phase 17: Task Lifecycle (3/3 plans) — completed 2026-03-12

</details>

<details>
<summary>✅ v1.2.1 Architectural Cleanup (Phases 18-28) — SHIPPED 2026-03-23</summary>

- [x] Phase 18: Write Model Strictness (2/2 plans) — completed 2026-03-16
- [x] Phase 19: InMemoryBridge Export Cleanup (1/1 plans) — completed 2026-03-17
- [x] Phase 20: Model Taxonomy (2/2 plans) — completed 2026-03-18
- [x] Phase 21: Write Pipeline Unification (2/2 plans) — completed 2026-03-19
- [x] Phase 22: Service Decomposition (4/4 plans) — completed 2026-03-20
- [x] Phase 23: SimulatorBridge and Factory Cleanup (1/1 plans) — completed 2026-03-20
- [x] Phase 24: Test Double Relocation (1/1 plans) — completed 2026-03-20
- [x] Phase 25: Patch/PatchOrClear Type Aliases (1/1 plans) — completed 2026-03-20
- [x] Phase 26: Replace InMemoryRepository (5/5 plans) — completed 2026-03-21
- [x] Phase 27: Bridge Contract Tests (4/4 plans) — completed 2026-03-22
- [x] Phase 28: Golden Master Expansion (4/4 plans) — completed 2026-03-23

</details>

<details>
<summary>✅ v1.2.2 FastMCP v3 Migration (Phases 29-31) — SHIPPED 2026-03-26</summary>

- [x] Phase 29: Dependency Swap & Imports (2/2 plans) — completed 2026-03-26
- [x] Phase 30: Test Client Migration (2/2 plans) — completed 2026-03-26
- [x] Phase 31: Middleware & Logging (2/2 plans) — completed 2026-03-26

</details>

### v1.2.3 Repetition Rule Write Support (In Progress)

**Milestone Goal:** Enable agents to set, modify, and remove repetition rules on tasks via structured fields -- symmetric read/write model, no raw RRULE strings exposed. No new tools.

- [x] **Phase 32: Read Model Rewrite** - Structured frequency fields replace ruleString on both read paths (completed 2026-03-28)
- [x] **Phase 32.1: Output Schema Validation Gap** - Add schema-vs-data validation tests ensuring serialized output conforms to advertised outputSchema (INSERTED) (completed 2026-03-28)
- [x] **Phase 33: Write Model, Validation & Bridge** - add_tasks and edit_tasks support repetition rules with partial updates, type-change detection, and educational errors (completed 2026-03-28)

## Phase Details

### Phase 32: Read Model Rewrite
**Goal**: Agents receive structured repetition rule data (frequency type, interval, schedule, basedOn, end) instead of raw RRULE strings from all read tools
**Depends on**: Phase 31 (v1.2.2 complete)
**Requirements**: READ-01, READ-02, READ-03, READ-04
**Success Criteria** (what must be TRUE):
  1. `get_all`, `get_task`, `get_project` return `repetitionRule` with structured `frequency` (type discriminator + type-specific fields), `schedule`, `basedOn`, and `end` fields -- no `ruleString` visible to agents
  2. All 9 frequency types (minutely, hourly, daily, weekly, weekly_on_days, monthly, monthly_day_of_week, monthly_day_in_month, yearly) parse correctly from real OmniFocus data
  3. Both SQLite and bridge read paths produce identical structured output for the same task (single `rrule/` module, no duplicated parsing logic)
  4. `parse_rrule` and `build_rrule` round-trip correctly -- parse a string, build it back, parse again, get the same structured result
**Plans:** 2/2 plans complete
Plans:
- [x] 32-01-PLAN.md — RRULE parser/builder module + Pydantic frequency models
- [x] 32-02-PLAN.md — Model swap, read path wiring, test updates

### Phase 32.1: Output Schema Validation Gap (INSERTED)
**Goal**: Add systemic test safeguards ensuring serialized tool output validates against MCP outputSchema, model naming conventions are programmatically enforced, and future agents have clear rules to follow
**Depends on**: Phase 32 (serializer fix in commit db4bcb0)
**Success Criteria** (what must be TRUE):
  1. For every MCP tool (get_all, get_task, get_project, get_tag, add_tasks, edit_tasks), serialized output from realistic fixtures validates against the tool's outputSchema using a JSON Schema validator (not Pydantic) -- the same validation MCP clients perform
  2. Test fixtures include tasks with repetitionRule set to actual Frequency values (at minimum DailyFrequency, WeeklyFrequency (bare), WeeklyOnDaysFrequency with onDays, MonthlyDayOfWeekFrequency with on, MonthlyDayInMonthFrequency with onDates) and both EndCondition variants (EndByDate, EndByOccurrences)
  3. A regression guard asserts that no union type branch in tool outputs degrades to `{"type": "object", "additionalProperties": true}` -- catches future @model_serializer additions
  4. A naming convention test enforces that models/ has no write-side suffixes and contracts/ uses recognized suffixes -- per docs/architecture.md taxonomy
  5. CLAUDE.md contains rules directing agents to read the naming taxonomy before creating models and to run schema tests after modifying output models
**Plans**: 3/3 plans complete
Plans:
- [x] 32.1-01-PLAN.md -- Schema-vs-data validation tests, union regression guard, naming convention enforcement
- [x] 32.1-02-PLAN.md -- Extract derive_schedule to rrule/schedule.py, fix from_completion crash
- [x] 32.1-03-PLAN.md -- WeeklyFrequency split: bare weekly + WeeklyOnDaysFrequency

### Phase 33: Write Model, Validation & Bridge
**Goal**: Agents can create tasks with repetition rules, partially update existing rules (merge within type, clear, change type), and receive educational errors for invalid input -- all through existing `add_tasks` and `edit_tasks` tools
**Depends on**: Phase 32
**Requirements**: ADD-01, ADD-02, ADD-03, ADD-04, ADD-05, ADD-06, ADD-07, ADD-08, ADD-09, ADD-10, ADD-11, ADD-12, ADD-13, ADD-14, EDIT-01, EDIT-02, EDIT-03, EDIT-04, EDIT-05, EDIT-06, EDIT-07, EDIT-08, EDIT-09, EDIT-10, EDIT-11, EDIT-12, EDIT-13, EDIT-14, EDIT-15, EDIT-16, VALID-01, VALID-02, VALID-03, VALID-04, VALID-05
**Success Criteria** (what must be TRUE):
  1. Agent can create a task with a repetition rule by providing `frequency` (with type), `schedule`, and `basedOn` in `add_tasks` -- the task appears in OmniFocus with the correct recurrence
  2. Agent can partially update a repeating task's rule (change interval, change schedule, change basedOn, add/remove end condition) without re-sending the entire rule -- omitted frequency fields are preserved from the existing rule when the type doesn't change
  3. Agent can clear a repetition rule by sending `repetitionRule: null` and can change frequency type by providing a complete new frequency object -- type change with incomplete frequency produces a clear error explaining what's needed
  4. Invalid input (bad enum values, cross-type fields like `onDays` on daily, out-of-range values) is rejected with educational error messages consistent with existing `agent_messages` patterns
  5. Tool descriptions for `add_tasks` and `edit_tasks` document the repetition rule schema clearly enough for an LLM to construct valid rules without external documentation
**Plans**: 5 plans
Plans:
- [x] 33-01-PLAN.md — Contracts (specs, repo payload), inverse mappings, validation functions, agent messages
- [x] 33-02-PLAN.md — Service pipeline (payload builder, domain logic, pipeline steps, InMemoryBridge)
- [x] 33-03-PLAN.md — Bridge JS, tool descriptions, server error handling, output schema validation
- [x] 33-04-PLAN.md — Gap closure: remove scaffolding, dead code, extract validate.py inline strings
- [ ] 33-05-PLAN.md — Gap closure: fix multi-value BYMONTHDAY + no-op warning suppression

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-9 | v1.0 | 22/23 | Complete | 2026-03-07 |
| 10-13 | v1.1 | 11/11 | Complete | 2026-03-07 |
| 14-17 | v1.2 | 21/21 | Complete | 2026-03-16 |
| 18-28 | v1.2.1 | 27/27 | Complete | 2026-03-23 |
| 29-31 | v1.2.2 | 6/6 | Complete | 2026-03-26 |
| 32. Read Model Rewrite | v1.2.3 | 2/2 | Complete    | 2026-03-28 |
| 32.1 Output Schema Validation Gap | v1.2.3 | 3/3 | Complete    | 2026-03-28 |
| 33. Write Model, Validation & Bridge | v1.2.3 | 4/5 | In Progress | |
