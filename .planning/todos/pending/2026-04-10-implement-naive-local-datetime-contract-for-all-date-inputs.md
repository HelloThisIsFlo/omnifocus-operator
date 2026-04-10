---
created: "2026-04-10T20:00:28.312Z"
title: Implement naive-local datetime contract for all date inputs
area: contracts
files:
  - src/omnifocus_operator/service/
  - src/omnifocus_operator/contracts/use_cases/
  - src/omnifocus_operator/agent_messages/descriptions.py
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

### 1. Read side — every `now` timestamp must use local timezone

Anywhere the service layer creates a "current time" reference for date filter resolution, it must use local timezone instead of UTC. All downstream calculations (midnight truncation, "today"/"this week" boundaries, date-only bound expansion) inherit from `now` — so fixing `now` fixes everything downstream. The CF epoch math in `query_builder.py` works unchanged because tz-aware subtraction handles the offset correctly.

Audit the entire service layer for `datetime.now(UTC)` or any UTC-anchored timestamp used as a date filter reference.

### 2. Write side — naive-preferred contract, aware-accepted

Replace `AwareDatetime` with `str` and a format validator on all date fields in the write contracts (add and edit). This changes the JSON Schema from `format: "date-time"` (RFC 3339, timezone mandatory) to plain `type: "string"` — removing the signal that tells agents to send timezone info.

The normalization logic in the payload builder should handle:
- **Naive input** → pass through as-is (already local)
- **Aware input** → convert to local, strip tzinfo (convenience for when agents copy dates from other APIs like calendars)
- **Date-only input** → apply `DefaultDueTime`/`DefaultStartTime` from OmniFocus settings (future, can defer)

Update examples and descriptions to show naive local time as the default.

### 3. Unify read-side filter inputs

The `before`/`after` fields in `DateFilter` already accept `str`. There's a defensive fix (WR-01) that inherits `now.tzinfo` when a parsed datetime is naive — once `now` is local, this becomes the correct behavior by design rather than a workaround. Verify consistency across the resolver and the contract's ordering check.

### 4. Document in architecture.md

Add a section explaining the naive-local principle alongside the existing design philosophy sections. Key points:
- OmniFocus stores naive local time, server is co-located → local is the only frame that makes sense
- The API should feel like OmniFocus itself — you say "5pm", it stores 5pm
- Agents spend their reasoning on the user's problem, not on API mechanics
- `format: "date-time"` (RFC 3339) requires timezone by spec → we use `str` to avoid contradicting our naive-preferred contract
- Aware inputs accepted as convenience (e.g., copying from calendar APIs) — server converts silently
