---
created: "2026-04-10T20:00:28.312Z"
title: Implement naive-local datetime contract for all date inputs
area: contracts
files:
  - src/omnifocus_operator/service/service.py:389
  - src/omnifocus_operator/service/service.py:485
  - src/omnifocus_operator/contracts/use_cases/add/tasks.py:55-69
  - src/omnifocus_operator/contracts/use_cases/edit/tasks.py:72-86
  - src/omnifocus_operator/contracts/use_cases/list/_date_filter.py:52-69
  - src/omnifocus_operator/service/payload.py:47-52
  - src/omnifocus_operator/service/resolve_dates.py:215-246
  - src/omnifocus_operator/agent_messages/descriptions.py:35
  - docs/architecture.md
---

## Problem

The API sends contradictory timezone signals and forces agents to do unnecessary timezone math.

- **Write side**: `AwareDatetime` requires timezone → JSON Schema emits `format: "date-time"` (RFC 3339, timezone mandatory). Agent must know the user's timezone to convert "5pm" to `"17:00:00+01:00"` or `"16:00:00Z"`.
- **Read side**: `now = datetime.now(UTC)` makes all date filter boundaries (midnight, "today", "this week") align with UTC, not local time. A task due at 00:30 local is misclassified at day boundaries.
- OmniFocus stores **everything** as naive local time (proven across 430 tasks, both BST and GMT — see `.research/deep-dives/timezone-behavior/RESULTS.md`). The server runs on the same Mac. Timezone awareness in the API adds complexity with zero benefit.

Supersedes the completed todo `2026-04-09-design-timezone-consistency-policy-for-date-filter-inputs.md` — all design questions answered by the timezone deep-dive.

## Solution

**Principle: "OmniFocus thinks in local time, so should the API."**

Agents should never think about timezone — just like OmniFocus users don't. Send the time as the user expressed it.

### 1. Read side — local `now`

Change `datetime.now(UTC)` → `datetime.now().astimezone()` in:
- `service.py:389` (list tasks pipeline)
- `service.py:485` (review due date)

All downstream calculations (`_midnight()`, `_resolve_this()`, date-only bounds) then use local midnight/day boundaries. The CF epoch math in `query_builder.py` works unchanged — tz-aware subtraction handles it.

### 2. Write side — `str` instead of `AwareDatetime`

Change `AwareDatetime` → `str` with a format validator in:
- `add/tasks.py` (AddTaskAction)
- `edit/tasks.py` (EditTaskAction)

This drops `format: "date-time"` from the JSON Schema. The agent sees `type: "string"` with description and examples guiding naive local time. No RFC 3339 signal.

Normalize in `payload.py` (~5 lines):
- **Naive input** → pass through as-is (already local)
- **Aware input** → convert to local, strip tzinfo (convenience for calendar copy-paste)
- **Date-only input** → apply `DefaultDueTime`/`DefaultStartTime` from OmniFocus settings (future, can defer)

### 3. Unify read-side filter inputs

The `before`/`after` fields in `DateFilter` already accept `str`. The WR-01 defensive fix (inheriting `now.tzinfo` for naive inputs) becomes the correct behavior once `now` is local — no longer a workaround.

### 4. Document in architecture.md

Add a section explaining the naive-local principle alongside the existing "show more" design philosophy. Key points:
- OmniFocus stores naive local time, server is co-located → local is the only frame that makes sense
- The API should feel like OmniFocus itself — you say "5pm", it stores 5pm
- Agents spend their reasoning on the user's problem, not on API mechanics
- `format: "date-time"` (RFC 3339) requires timezone by spec, so we use `str` to avoid contradicting our naive-preferred contract
- Aware inputs accepted as convenience (e.g., copying from calendar APIs) — server converts silently

### Files affected

| File | Change |
|------|--------|
| `service.py:389, 485` | `datetime.now(UTC)` → `datetime.now().astimezone()` |
| `add/tasks.py` | `AwareDatetime` → `str` + validator |
| `edit/tasks.py` | `AwareDatetime` → `str` + validator |
| `payload.py` | `.isoformat()` → normalize function (~5 lines) |
| `descriptions.py` | Example `"2026-03-15T17:00:00Z"` → `"2026-03-15T17:00:00"` |
| `_date_filter.py` | Verify validator + ordering check consistency |
| `resolve_dates.py` | WR-01 fix stays, now correct by design |
| `docs/architecture.md` | New "Naive-local datetime" design principle section |
| Tests | Update contract validation tests, update `NOW` fixture |
