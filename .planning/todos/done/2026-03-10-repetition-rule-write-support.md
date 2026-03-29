---
created: 2026-03-10T00:00:00.000Z
title: "Repetition rule write support: structured fields, not RRULE strings"
area: api-design
priority: high
files:
  - src/omnifocus_operator/models/
  - src/omnifocus_operator/service/
  - src/omnifocus_operator/bridge/bridge.js
  - docs/architecture.md
---

## Problem

Repetition rules are read-only and exposed as raw RRULE strings (e.g. "FREQ=WEEKLY;BYDAY=MO,WE,FR"). Agents can't set, modify, or clear repetition rules. The RRULE string format is opaque and undiscoverable.

## Solution

Add repetition rule support to both `edit_tasks` and `add_tasks`, and restructure the read model to use decomposed structured fields instead of the raw RRULE string.

### Key Decision: Structured Fields

- Agents see structured fields (freq, interval, byday, etc.), never RRULE strings
- Read and write use the same shape — read a rule, modify a field, send it back
- RRULE string is an internal serialization detail between service and bridge
- Validation is server-side via a zero-dep parser/builder (~100 lines)
- Already documented in `docs/architecture.md` under "Repetition Rule: Structured Fields, Not RRULE Strings"

### RepetitionRule Model (shared read/write)

- `freq`: "daily" | "weekly" | "monthly" | "yearly" (required)
- `interval`: int | None (every N, default 1)
- `byday`: list[str] | None (day codes: "MO", "TU", etc.)
- `bymonthday`: int | None (1-31 or negative for last-day)
- `bysetpos`: int | None (nth weekday, requires byday)
- `count`: int | None (repeat N times) — mutually exclusive with `until` (RFC 5545)
- `until`: str | None (repeat until date)
- `schedule_type`: "regularly" | "from_completion" (required)
- `anchor_date_key`: "due_date" | "defer_date" | "planned_date" (default "due_date")
- `catch_up_automatically`: bool (default true)

### Placement

- **Edit**: top-level clearable field (idempotent setter, NOT inside actions block). UNSET = no change, null = clear, {...} = set/replace.
- **Create**: optional field, defaults to None.
- **Read**: breaking change — `rule_string` replaced with structured fields.

### Bridge.js

Bridge receives RRULE string (built server-side) + scheduleType, anchorDateKey, catchUpAutomatically. JS constructs `new Task.RepetitionRule(...)` or assigns null to clear. RepetitionRule is immutable in OmniJS — always construct new.

### Research Spike (completed)

- `.research/deep-dives/rrule-validator/` — parser + builder (~200 lines), 79 tests, zero deps
- `.research/deep-dives/repetition-rule/repetition-rule-guide.md` — full OmniJS API reference
- Code is directly portable to production (use existing enums from models/enums.py)

## Scope

~2 plans:
1. Read model change — decompose rule_string into structured fields, parser to production, adapter/SQLite mapping, read-side tests
2. Write model + bridge + service — RepetitionRuleSpec on edit/create specs, builder, bridge handler, validation, write-side tests

## Dependencies

- Depends on Phase 16 (edit_tasks exists)
- No dependency on Phase 16.2 (bridge tag simplification) or Phase 17 (lifecycle)

## Target

Future milestone — after filtering infrastructure (v1.3) ships. Original "Phase 18" target was overtaken by v1.2.1 architectural cleanup.
