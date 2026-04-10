# Phase 49: Implement naive-local datetime contract for all date inputs - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace UTC-anchored timestamps with naive-local datetime throughout write contracts, filter resolution, and service layer — making the API match OmniFocus's naive-local storage model. The principle: "OmniFocus thinks in local time, so should the API."

Three scopes:
1. **Read side** — `datetime.now(UTC)` → `datetime.now(local)` in service layer for all date filter resolution
2. **Write side** — `AwareDatetime` → `str` + format validator on all date fields in add/edit contracts; normalization in domain layer
3. **Read-side filters** — `_DateBound` type unified to `str` (same as write side), `_reject_naive_datetime` removed

This phase does NOT implement the OmniFocus settings API for default times (separate todo). Date-only inputs use midnight local as interim default.

</domain>

<decisions>
## Implementation Decisions

### Naive-preferred, aware-accepted contract (all date inputs)
- **D-01:** Naive-local is the preferred format for ALL date inputs across the entire API — write-side fields (add/edit) AND read-side filter bounds (before/after). Aware datetimes (with timezone offset) are accepted as a convenience and silently converted to local time.
- **D-01b:** This overrides Phase 48's `_reject_naive_datetime` BeforeValidator on `_DateBound`. Phase 48 was designed before the timezone deep-dive; the todo's design document (based on 430-task empirical evidence) supersedes all prior timezone decisions.
- **D-01c:** The `_reject_naive_datetime` validator and its error message constant are dead code after this phase — remove them.

### Write-side type: `str` (not `AwareDatetime`, not `NaiveDatetime`, not `datetime`)
- **D-07:** All write-side date fields (`dueDate`, `deferDate`, `plannedDate`) change from `AwareDatetime` to `str` on both `AddTaskCommand` and `EditTaskCommand`. This drops `format: "date-time"` from JSON Schema, removing the signal that tells agents to include timezone.
- **D-07b:** Read-side `_DateBound` in `AbsoluteRangeFilter` also changes to `str` (from `Literal["now"] | AwareDatetime | date`). Same rationale: no `format: "date-time"` anywhere in the API.
- **D-07c:** `PatchOrClear[AwareDatetime]` on edit fields becomes `PatchOrClear[str]`.

### Date-only write handling: intercept and apply midnight local
- **D-02:** When an agent sends a date-only string (e.g., `"2026-07-15"`) to a write-side date field, intercept before it reaches the bridge and append `T00:00:00` (midnight local).
- **D-02b:** This avoids the JS bridge quirk where `new Date("2026-07-15")` parses as UTC midnight (ECMA-262 spec), which during BST stores 1am local instead of midnight local.
- **D-02c:** Clean upgrade path for the settings API todo: swap hardcoded `T00:00:00` with `DefaultDueTime`/`DefaultDeferTime` from OmniFocus preferences. Same code path, same interception point.
- **D-02d:** Applies to `dueDate`, `deferDate`, `plannedDate` on both add and edit.

### Centralized local timezone helper
- **D-03:** A dedicated named function (e.g., `local_now()` or `get_local_tz()`) encapsulates the local timezone choice. All call sites use this function — no inline `datetime.now(ZoneInfo("localtime"))` scattered through the codebase.
- **D-03b:** The function's docstring/comment explains the rationale: OmniFocus stores naive local time, server is co-located, deep-dive proved the formula across 430 tasks in both BST and GMT.
- **D-03c:** Even if the function body is trivial, it exists to capture the architectural decision as a "named concept" — future maintainers see deliberate choice, not something that looks like a bug.

### Agent-facing example and description framing
- **D-04:** `DATE_EXAMPLE` changes from `"2026-03-15T17:00:00Z"` to `"2026-03-15T17:00:00"` — naive local, no timezone suffix. Agents see this in JSON Schema `examples` and copy the pattern.
- **D-05:** Each write tool's doc (`ADD_TASKS_TOOL_DOC`, `EDIT_TASKS_TOOL_DOC`) gets a brief inline note at the top framing dates as local time. Something like: "All dates are local time. Timezone offsets also accepted and converted to local." No secondary example, no elaboration — keep it minimal.
- **D-05b:** Inline per tool (not a shared constant). Matches existing `descriptions.py` pattern where each tool's doc is self-contained.

### Normalization placement: domain.py (product decision)
- **D-06:** Aware→local normalization lives in `domain.py` because "use local time" is a product decision. Per `docs/architecture.md` litmus test: "Would another OmniFocus tool make this same choice?" — No, another tool might require UTC. This is our choice → domain.
- **D-06b:** Contract layer: `str` + format validator (validates SYNTAX only — is it a parseable date/datetime string?). No transformation logic in contracts (per project convention: contracts are pure data).
- **D-06c:** Domain layer: parses the string, detects format (naive/aware/date-only), normalizes aware→local, strips tzinfo → produces naive local datetime. This is the semantic interpretation.
- **D-06d:** Payload builder: receives the ready-to-use value from domain, no additional transformation.

### Claude's Discretion
- Internal naming of the local timezone helper function (`local_now()`, `get_local_tz()`, or similar)
- Exact format validation regex/parsing approach in the contract validator
- Whether to extract a shared date-string validator or duplicate per field
- How `_validate_bounds` in AbsoluteRangeFilter adapts to `str` inputs (parse-before-compare)
- Test file organization and migration approach
- Exact wording of the tool-level description note
- Where the `local_now()` helper lives (config.py, service utility, or new module)
- How the CF epoch math in `query_builder.py` adapts (resolved bounds may need tz-aware local for correct subtraction against UTC epoch)

### Folded Todos
- **Implement naive-local datetime contract for all date inputs** (`.planning/todos/pending/2026-04-10-implement-naive-local-datetime-contract-for-all-date-inputs.md`) — this IS the phase. The todo is the primary design document with the complete scenario matrix and empirical evidence from the timezone deep-dive.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design document (PRIMARY)
- `.planning/todos/pending/2026-04-10-implement-naive-local-datetime-contract-for-all-date-inputs.md` — Complete design: principle, read/write/filter changes, scenario matrix (W1-W6, R1-R8, E1-E3), format normalization table, date-only handling. THIS CONTEXT.md captures discussion decisions that refine or override the todo.

### Deep-dive evidence (CRITICAL)
- `.research/deep-dives/timezone-behavior/RESULTS.md` — Empirical proof across 430 tasks: floating naive local storage, conversion formula, format normalization table, date-only quirk
- `.research/deep-dives/timezone-behavior/03-create-readback/FINDINGS.md` — Create-and-readback proof for every input format (naive, UTC, offset, date-only)

### Architecture (normalization placement)
- `docs/architecture.md` §"Product Decisions vs Plumbing" — litmus test for domain.py placement. The aware→local normalization is a product decision.
- `docs/architecture.md` §"Write Pipeline" — data flow: Agent → Server → Service → Repository → Bridge

### Source files (in scope)
- `src/omnifocus_operator/service/service.py:389,481` — `datetime.now(UTC)` occurrences to change to local
- `src/omnifocus_operator/service/domain.py` — Add naive-local normalization logic (product decision)
- `src/omnifocus_operator/service/resolve_dates.py` — Resolver uses `now` parameter; verify local-anchored behavior
- `src/omnifocus_operator/contracts/use_cases/add/tasks.py:55-69` — `AwareDatetime` → `str` on AddTaskCommand
- `src/omnifocus_operator/contracts/use_cases/edit/tasks.py:72-86` — `PatchOrClear[AwareDatetime]` → `PatchOrClear[str]` on EditTaskCommand
- `src/omnifocus_operator/contracts/use_cases/list/_date_filter.py:26-38` — Remove `_reject_naive_datetime`, change `_DateBound` to `str`
- `src/omnifocus_operator/agent_messages/descriptions.py:35` — `DATE_EXAMPLE` change + tool doc updates
- `src/omnifocus_operator/repository/hybrid/query_builder.py:9-14` — CF epoch math may need adaptation for local-anchored bounds

### Companion todo (deferred dependency)
- `.planning/todos/pending/2026-04-10-use-omnifocus-settings-api-for-date-preferences-and-due-soon.md` — DefaultDueTime/DefaultDeferTime from OmniFocus settings. Not in scope for Phase 49. Phase 49 hardcodes midnight local for date-only; this todo upgrades to user preferences.

### Phase 48 output (predecessor — partially reversed)
- `.planning/phases/48-refactor-datefilter-into-discriminated-union-with-typed-date/48-CONTEXT.md` — Phase 48 established the discriminated union structure (kept) and `_reject_naive_datetime` (removed by Phase 49)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Discriminated union structure from Phase 48 (`ThisPeriodFilter | LastPeriodFilter | NextPeriodFilter | AbsoluteRangeFilter`) — kept intact, only the bound types change
- `_to_naive()` helper in `_date_filter.py` — may become dead code if bounds are `str` instead of `AwareDatetime`
- `ValidationReformatterMiddleware` — reformats Pydantic errors for agent consumption
- `resolve_dates.py` date arithmetic — unchanged in logic, `now` parameter just arrives as local instead of UTC

### Established Patterns
- `contracts are pure data` — no `model_serializer` or transformation logic in contracts. Validators check syntax only.
- Product decisions in `domain.py` — the litmus test ("Would another OmniFocus tool make this same choice?")
- `AwareDatetime` used throughout read-side models (output) — NOT changing. Only input contracts change.
- `agent_messages/descriptions.py` centralized with AST enforcement — all description changes go here

### Integration Points
- `service.py:389` — `self._now = datetime.now(UTC)` in ListTasksPipeline → change to local
- `service.py:481` — `datetime.now(UTC)` in ListProjectsPipeline → change to local
- `domain.py` — add datetime normalization logic (parse string, detect format, normalize aware→local)
- `payload.py` — receives normalized datetime from domain, formats for bridge
- `query_builder.py:_CF_EPOCH` — UTC-anchored epoch. Resolved bounds must be compatible for subtraction.
- `_date_filter.py:_DateBound` — type changes from `Literal["now"] | AwareDatetime | date` to `Literal["now"] | str`
- `_date_filter.py:_validate_bounds` — must adapt to `str` inputs (parse before comparing)

</code_context>

<specifics>
## Specific Ideas

### The todo IS the design document
The todo was written after a multi-day timezone deep-dive that empirically tested 430 tasks across BST and GMT. It includes a complete scenario matrix (W1-W6 for writes, R1-R8 for reads, E1-E3 for edge cases). The todo's decisions override all prior phase decisions on timezone handling.

### Phase 48's structural work is preserved
Phase 48's discriminated union for DateFilter is kept. Only the TYPES within the union change (AwareDatetime → str on bounds). The routing logic, union dispatch, and model structure are unaffected.

### Action item: backfill roadmap artifacts
Phase 49 was added retroactively to the milestone. Before or after implementation, backfill:
- REQUIREMENTS.md — add requirement IDs for Phase 49
- ROADMAP.md — fill in Goal, Requirements, Success Criteria for Phase 49
- STATE.md — update phase count and progress tracking

</specifics>

<deferred>
## Deferred Ideas

### Reviewed Todos (not folded)
- **Use OmniFocus settings API for date preferences and due-soon threshold** — Depends on Phase 49. Upgrades date-only handling from midnight local to user's DefaultDueTime/DefaultDeferTime. Separate scope.
- **Add date filters to list_projects** — Different capability (new feature). Reuses v1.3.2 infrastructure after it's stable.

</deferred>

---

*Phase: 49-implement-naive-local-datetime-contract-for-all-date-inputs*
*Context gathered: 2026-04-10*
