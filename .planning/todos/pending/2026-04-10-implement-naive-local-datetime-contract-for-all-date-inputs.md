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

> [!warning] Don't use `NaiveDatetime`
>
> Pydantic's `NaiveDatetime`, `AwareDatetime`, and plain `datetime` all produce **identical** JSON Schema: `format: "date-time"`. Verified empirically. Only `str` drops the format constraint.
>
> Why `format: "date-time"` is wrong for us: it references RFC 3339 (section 5.6), which **requires** a timezone offset. An agent reading this schema is told "you must send a timezone" — the opposite of what we want. Clients that pre-validate against JSON Schema (e.g., Claude Desktop co-work mode) may even reject naive datetimes before they reach the server. `NaiveDatetime` looks like the right answer but produces the wrong schema.

The normalization logic in the payload builder should handle:
- **Naive input** → pass through as-is (already local)
- **Aware input** → convert to local, strip tzinfo (convenience for when agents copy dates from other APIs like calendars)
- **Date-only input** → apply `DefaultDueTime`/`DefaultStartTime` from OmniFocus settings (future, can defer)

Update examples and descriptions to show naive local time as the default. Consider also adding a global note in the tool-level description (not just per-field) framing all dates as local time — so the agent gets the principle before reading individual fields.

### 3. Unify read-side filter inputs

The `before`/`after` fields in `DateFilter` already accept `str`. There's a defensive fix (WR-01) that inherits `now.tzinfo` when a parsed datetime is naive — once `now` is local, this becomes the correct behavior by design rather than a workaround. Verify consistency across the resolver and the contract's ordering check.

### 4. Document in architecture.md

Add a section explaining the naive-local principle alongside the existing design philosophy sections. Key points:
- OmniFocus stores naive local time, server is co-located → local is the only frame that makes sense
- The API should feel like OmniFocus itself — you say "5pm", it stores 5pm
- Agents spend their reasoning on the user's problem, not on API mechanics
- `format: "date-time"` (RFC 3339) requires timezone by spec → we use `str` to avoid contradicting our naive-preferred contract
- Aware inputs accepted as convenience (e.g., copying from calendar APIs) — server converts silently

## Scenario matrix

All examples assume user is in BST (UTC+1). OmniFocus default due time is 19:00.

### Write side — add_tasks / edit_tasks

**W1. User says "due tomorrow at 5pm" — agent sends naive (the common case)**
- Input: `"dueDate": "2026-07-16T17:00:00"`
- Current: **REJECTED** — `AwareDatetime` requires timezone
- Target: accepted → bridge `new Date("...T17:00:00")` → JS treats as local → OmniFocus stores `17:00` ✅

**W2. User says "due tomorrow at 5pm" — agent sends UTC**
- Input: `"dueDate": "2026-07-16T16:00:00Z"`
- Current: accepted → bridge `new Date("...T16:00:00Z")` → local = 17:00 BST → stored `17:00` ✅
- Target: accepted → server converts 16:00Z → 17:00 local → bridge gets naive → stored `17:00` ✅

**W3. User says "due tomorrow at 5pm" — agent sends explicit offset**
- Input: `"dueDate": "2026-07-16T17:00:00+01:00"`
- Current: accepted → stored `17:00` ✅
- Target: accepted → server converts to naive local → stored `17:00` ✅

**W4. User says "due July 15" — agent sends date-only**
- Input: `"dueDate": "2026-07-15"`
- Current: **REJECTED** — `AwareDatetime` can't parse date-only
- Target: accepted → ideally apply `DefaultDueTime` (19:00) → stored `19:00` on July 15
  - Default-time application can be deferred to a later todo

**W5. Agent copies date from a calendar API (aware UTC input)**
- Input: `"dueDate": "2026-07-15T16:00:00Z"` (agent passes through without thinking)
- Current: accepted → stored `17:00` BST ✅
- Target: accepted → server converts 16:00Z → 17:00 local → stored `17:00` ✅
- Key: agent didn't need to know the user's timezone in either case, but in the current system the agent was lucky — it already had a Z timestamp. Without it, the agent would need to add one.

**W6. Agent sends naive for a non-local time (agent error)**
- Scenario: calendar gives `16:00Z`, agent strips Z without converting, sends `"2026-07-15T16:00:00"`
- Current: **REJECTED** — `AwareDatetime` catches it (but for the wrong reason — it rejects the lack of TZ, not the wrong time)
- Target: accepted as `16:00` local → stored `16:00` (off by 1h). This is an agent error — the contract says "local time." The old contract couldn't prevent this either if the agent sent `"16:00:00Z"` thinking it was local.

### Read side — date filters (list_tasks)

**R1. "Show me tasks due today" — shorthand**
- Input: `{due: "today"}`
- Current: "today" = midnight UTC to midnight UTC. A task due at 00:30 BST (= 23:30 UTC prev day) is **EXCLUDED** — it's "yesterday" in UTC ❌
- Target: "today" = midnight local to midnight local → task at 00:30 BST included ✅

**R2. "Tasks due after July 15" — date-only absolute**
- Input: `{due: {after: "2026-07-15"}}`
- Current: bound = midnight UTC July 15. Task due 00:30 BST July 15 (= 23:30 UTC July 14) **EXCLUDED** ❌
- Target: bound = midnight BST July 15 (= 23:00 UTC July 14) → task at 00:30 BST included ✅

**R3. "Tasks due before 5pm today" — naive datetime in filter**
- Input: `{due: {before: "2026-07-15T17:00:00"}}`
- Current: WR-01 attaches UTC tzinfo → bound = 17:00 **UTC** (= 18:00 BST). A task due at 17:30 BST (= 16:30 UTC) passes the filter even though it's after 5pm local ❌
- Target: inherits local tzinfo → bound = 17:00 **BST** (= 16:00 UTC). Task at 17:30 BST correctly excluded ✅

**R4. "Tasks due after midnight" — aware datetime in filter**
- Input: `{due: {after: "2026-07-15T00:00:00+01:00"}}`
- Current: works correctly — `fromisoformat` preserves offset ✅
- Target: same behavior, no change ✅

**R5. "Tasks due this week"**
- Input: `{due: {this: "w"}}`
- Current: week boundaries computed from UTC midnight → off by ±offset at week start/end
- Target: week boundaries computed from local midnight ✅

**R6. "Tasks due in the last 7 days"**
- Input: `{due: {last: "7d"}}`
- Current: start = midnight UTC 7 days ago → tasks near midnight local may be misclassified
- Target: start = midnight local 7 days ago ✅

**R7. "Overdue tasks"**
- Input: `{due: "overdue"}`
- Current: `before = now(UTC)` — correct moment regardless of representation ✅
- Target: `before = now(local)` — same absolute moment, different tzinfo. **No behavior change** ✅

**R8. "Due soon"**
- Input: `{due: "soon"}`
- Current: threshold from UTC `now`. Calendar-aligned mode snaps to UTC midnight.
- Target: threshold from local `now`. Calendar-aligned snaps to local midnight ✅

### Edge cases

**E1. DST transition day — "tasks due today" on spring-forward**
- Input: `{due: "today"}` on March 29 (clocks go 01:00 → 02:00)
- Current: 24h window (UTC doesn't have DST) — may include/exclude tasks incorrectly near boundary
- Target: "today" = midnight local to midnight local = 23h window. Correct — matches how OmniFocus and humans think about "today" on DST transition days.

**E2. Task due exactly at midnight local**
- Task due `00:00:00` BST July 15 (= 23:00 UTC July 14)
- Filter: `{due: {after: "2026-07-15"}}` (inclusive, `>=`)
- Current: bound = 00:00 UTC July 15. Task at 23:00 UTC July 14 **EXCLUDED** ❌
- Target: bound = 00:00 BST July 15 = 23:00 UTC July 14. Task at 23:00 UTC July 14 **INCLUDED** (exactly on boundary, `>=`) ✅

**E3. `"now"` keyword**
- Input: `{due: {before: "now"}}` or `{due: {after: "now"}}`
- Current: returns `now(UTC)` — correct absolute moment ✅
- Target: returns `now(local)` — same absolute moment. **No behavior change** ✅
