# Requirements: OmniFocus Operator

**Defined:** 2026-03-27
**Core Value:** Reliable, simple, debuggable access to OmniFocus data for AI agents -- executive function infrastructure that works at 7:30am.

## v1.2.3 Requirements

Repetition Rule Write Support. Structured fields replace raw RRULE strings on both read and write paths. No new tools.

### Read Model (READ)

- [x] **READ-01**: RepetitionRule read model exposes structured frequency fields (type, interval, onDays, etc.) instead of ruleString
- [x] **READ-02**: All 9 frequency types correctly parsed from RRULE strings (minutely, hourly, daily, weekly, weekly_on_days, monthly, monthly_day_of_week, monthly_day_in_month, yearly)
- [x] **READ-03**: Both SQLite and bridge read paths share a single rrule module for parsing (no duplicated logic)
- [x] **READ-04**: parse_rrule and build_rrule round-trip correctly for all frequency types

### Creation — add_tasks (ADD)

- [x] **ADD-01**: Create task with repetition rule using structured fields (frequency with type, schedule, basedOn all required)
- [x] **ADD-02**: All 9 frequency types supported for creation
- [x] **ADD-03**: Interval > 1 supported (e.g., every 2 weeks, every 3 months)
- [x] **ADD-04**: Weekly frequency supports onDays field with day codes (MO-SU), case-insensitive input normalized to uppercase
- [x] **ADD-05**: Weekly frequency without onDays repeats every N weeks from basedOn date
- [x] **ADD-06**: monthly_day_of_week supports on field with ordinal/day (e.g., {"second": "tuesday"}), case-insensitive input normalized to lowercase. Valid ordinals: first/second/third/fourth/fifth/last. Valid days: monday-sunday plus weekday/weekend_day
- [x] **ADD-07**: monthly_day_in_month supports onDates field (1-31, -1 for last day)
- [x] **ADD-08**: monthly_day_in_month with empty/omitted onDates triggers warning suggesting plain monthly type
- [ ] **ADD-09**: All 3 schedule values work: regularly, regularly_with_catch_up, from_completion
- [ ] **ADD-10**: All 3 basedOn values work: due_date, defer_date, planned_date
- [ ] **ADD-11**: End by date supported
- [ ] **ADD-12**: End by occurrences supported
- [x] **ADD-13**: No end (omitted) creates open-ended repetition
- [x] **ADD-14**: Interval defaults to 1 when omitted

### Editing — edit_tasks (EDIT)

- [x] **EDIT-01**: Set repetition rule on non-repeating task (full rule required: frequency with type, schedule, basedOn)
- [x] **EDIT-02**: Remove repetition rule (repetitionRule: null)
- [x] **EDIT-03**: Omitting repetitionRule entirely = no change (UNSET semantics)
- [ ] **EDIT-04**: Change schedule without resending frequency or other root fields
- [ ] **EDIT-05**: Change basedOn without resending frequency or other root fields
- [x] **EDIT-06**: Add end condition to task with no end
- [x] **EDIT-07**: Remove end condition from task that has one
- [ ] **EDIT-08**: Change end type (date → occurrences, occurrences → date)
- [ ] **EDIT-09**: Same-type frequency update merges — omitted fields preserved from existing rule
- [ ] **EDIT-10**: Change frequency interval on same type (other frequency fields preserved)
- [ ] **EDIT-11**: Change onDays on weekly task (other frequency fields preserved)
- [ ] **EDIT-12**: Change on field on monthly_day_of_week task (other frequency fields preserved)
- [x] **EDIT-13**: Change frequency type — full replacement of frequency object required
- [x] **EDIT-14**: Type change with incomplete frequency → clear error
- [x] **EDIT-15**: No existing rule + partial update → clear error
- [ ] **EDIT-16**: No-op detection with educational warning (same rule sent back)

### Validation (VALID)

- [x] **VALID-01**: Pydantic rejects invalid structures: missing required fields, bad enum values, end with != 1 key
- [x] **VALID-02**: Type-specific constraints: reject fields that don't belong to frequency type (e.g., onDays on daily), valid ranges (interval >= 1, valid day codes MO-SU, valid ordinals first/second/third/fourth/fifth/last, dayOfMonth -1 to 31 excluding 0, end.occurrences >= 1)
- [x] **VALID-03**: Educational error messages consistent with existing agent_messages patterns
- [ ] **VALID-04**: Tool descriptions document schema clearly enough for an LLM to construct valid repetition rules
- [x] **VALID-05**: End date in the past triggers warning (same style as existing "completed task" warnings)

## Deferred

- Task reactivation (markIncomplete) -- OmniJS API unreliable (existing deferral from v1.2)
- Repetition rules on projects -- OmniFocus supports this but tasks only for v1.2.3

## Out of Scope

| Feature | Reason |
|---------|--------|
| Raw RRULE string exposure | Replaced by structured fields -- agents never see RRULE |
| Project repetition writes | Scope is tasks only; deferred to v1.4.3 |
| Per-occurrence editing | OmniFocus limitation |
| Natural language parsing | Agent's job, not the server's |
| RRULE passthrough | Defeats the structured model |
| Cross-type field inference | Ambiguous intent -- fail loudly instead |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| READ-01 | Phase 32 | Complete |
| READ-02 | Phase 32 | Complete |
| READ-03 | Phase 32 | Complete |
| READ-04 | Phase 32 | Complete |
| ADD-01 | Phase 33 | Complete |
| ADD-02 | Phase 33 | Complete |
| ADD-03 | Phase 33 | Complete |
| ADD-04 | Phase 33 | Complete |
| ADD-05 | Phase 33 | Complete |
| ADD-06 | Phase 33 | Complete |
| ADD-07 | Phase 33 | Complete |
| ADD-08 | Phase 33 | Complete |
| ADD-09 | Phase 33 | Pending |
| ADD-10 | Phase 33 | Pending |
| ADD-11 | Phase 33 | Pending |
| ADD-12 | Phase 33 | Pending |
| ADD-13 | Phase 33 | Complete |
| ADD-14 | Phase 33 | Complete |
| EDIT-01 | Phase 33 | Complete |
| EDIT-02 | Phase 33 | Complete |
| EDIT-03 | Phase 33 | Complete |
| EDIT-04 | Phase 33 | Pending |
| EDIT-05 | Phase 33 | Pending |
| EDIT-06 | Phase 33 | Complete |
| EDIT-07 | Phase 33 | Complete |
| EDIT-08 | Phase 33 | Pending |
| EDIT-09 | Phase 33 | Pending |
| EDIT-10 | Phase 33 | Pending |
| EDIT-11 | Phase 33 | Pending |
| EDIT-12 | Phase 33 | Pending |
| EDIT-13 | Phase 33 | Complete |
| EDIT-14 | Phase 33 | Complete |
| EDIT-15 | Phase 33 | Complete |
| EDIT-16 | Phase 33 | Pending |
| VALID-01 | Phase 33 | Complete |
| VALID-02 | Phase 33 | Complete |
| VALID-03 | Phase 33 | Complete |
| VALID-04 | Phase 33 | Pending |
| VALID-05 | Phase 33 | Complete |

**Coverage:**
- v1.2.3 requirements: 39 total
- Mapped to phases: 39
- Unmapped: 0

---
*Requirements defined: 2026-03-27*
*Last updated: 2026-03-27 after gap analysis — added VALID-05, expanded ADD-06/VALID-02, removed minutely/hourly write deferral*
