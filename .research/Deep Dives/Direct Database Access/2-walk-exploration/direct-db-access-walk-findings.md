# Direct Database Access — Walk Conversation Findings & Decisions

**Date:** 2026-03-06
**Context:** Walk conversation reviewing the deep-dive research into direct OmniFocus database access. This document captures all findings, architectural decisions, and open items so they can be handed off to the Claude Code instance working on the OmniFocus Operator codebase.

---

## Decision: SQLite Cache as Primary Read Path

After reviewing both options (XML bundle vs SQLite cache), the decision is to use **SQLite as the primary read path**, not XML.

### Why SQLite over XML

The original research doc recommended XML for stability. After further analysis, SQLite wins for two reasons:

1. **Independent status flags come for free.** The SQLite cache has pre-computed `blocked`, `blockedByFutureStartDate`, `overdue`, `dueSoon`, and `effectiveFlagged` as independent boolean columns. These are computed by OmniFocus itself. With XML, we'd need to reimplement OmniFocus's blocking logic (sequential ordering, parent chain walking, defer date evaluation) — which was the exact risk we wanted to avoid.

2. **Schema stability is better than it looks.** The research doc flagged SQLite path instability as the main risk. Deeper investigation reveals that the *schema* has been stable across every major version since OF1. An Omni Group staff member confirmed during the OF2 launch (2014) that "the sqlite cache moved to a new location, but its format shouldn't have changed, and the queries still work once you have the correct path." The same SQL queries (referencing `task`, `projectInfo`, `context`, `folder`, `blocked`, `blockedByFutureStartDate`, `effectiveActive`, etc.) have worked from OF1 through OF4. Only the path changes — and that's manageable.

### Path change history

| Version | Year | Path Change |
|---------|------|-------------|
| OF1 | 2008 | `~/Library/Caches/.../OmniFocusDatabase2` |
| OF2 | 2014 | `~/Library/Containers/com.omnigroup.OmniFocus2/Data/Library/Caches/.../OmniFocusDatabase2` |
| OF3 | 2018 | `~/Library/Containers/com.omnigroup.OmniFocus3/.../OmniFocus Caches/` |
| OF3.5 | ~2020 | `~/Library/Group Containers/34YW5XSRB7.com.omnigroup.OmniFocus/...OmniFocus3/...` (mid-cycle surprise!) |
| OF4 | 2023 | `~/Library/Group Containers/34YW5XSRB7.com.omnigroup.OmniFocus/...OmniFocus4/...` |

Every breakage reported in the community was a path change, never a schema change.

---

## The Two Axes: Urgency & Availability

The bridge's `taskStatus` enum has a fundamental design flaw: it's a single-winner enum. A task is Overdue OR Blocked, never both. In reality, **173 tasks in the database are both blocked AND overdue**. The single enum misleads agents.

The correct model has two independent axes:

- **Urgency axis**: `overdue`, `due_soon` — how time-sensitive is this?
- **Availability axis**: `blocked`, `blocked_by_future_start_date` — can this actually be worked on?

The SQLite cache provides these as independent columns, computed by OmniFocus itself. No reimplementation needed. **The service layer code that was attempting to replicate OmniFocus's blocking/overdue logic can be deleted.**

### Pydantic model additions (non-breaking)

```python
blocked: bool = False
blocked_by_future_start_date: bool = False
overdue: bool = False
due_soon: bool = False
```

These complement (not replace) the existing `status: TaskStatus` enum.

---

## Architecture: Bridge Swap + Fallback with Degraded Mode

### Primary path: SQLite bridge

Replace the current bridge's read path with a new `SQLiteBridge` (or similar) that reads directly from the SQLite cache. This should implement the same interface as `RealBridge`. The existing architecture was designed for exactly this swap.

- Full experience: both urgency and availability axes populated natively
- ~11ms reads (vs 1-3s bridge IPC)
- OmniFocus does NOT need to be running for reads

### Fallback path: JS bridge (or XML) in degraded mode

If the SQLite database is not found (e.g., OmniFocus version change moved the path), fall back to the JS bridge or XML parser with **reduced data quality**:

- **Urgency axis**: likely still works (overdue/due_soon are date comparisons — need to validate, see TODO below)
- **Availability axis**: returns `None`/unknown — honest about what it can't guarantee
- **Service layer**: aware of which mode it's in, can communicate "availability data may be incomplete" to the agent

**Why not feature parity in fallback?** Reimplementing OmniFocus's blocking logic carries divergence risk. Better to be honest about reduced quality than to silently give wrong answers.

### Write path: JS bridge (unchanged)

Writes continue to go through the JS bridge. No alternative:

- OmniFocus must validate and process mutations
- Undo support requires OmniFocus
- Sync to other devices requires OmniFocus
- Writing to XML or SQLite directly could corrupt the database

---

## MCP Pattern: Graceful Degradation via Error-Serving Mode

A new pattern discovered during this conversation, applicable to MCP servers generally.

### The problem

With traditional apps, "fail fast" means crash with a clear error. But MCP servers aren't started by users — they're started by agents/hosts (Claude Desktop, Claude Code, etc.). If the server crashes at startup:

- There's no terminal the user is watching
- Logs require debug mode
- The failure is silent and mysterious

### The pattern

Instead of crashing, spawn a **degraded-mode server** where every tool endpoint returns the same clear, actionable error message:

> "SQLite database not found at [expected path]. OmniFocus may have updated to a new version — check that the path exists and restart the server."

### Why it works

- The agent is your real user in MCP — communicate failures *to the agent*
- Agent surfaces the error on its very first tool call — no mystery
- User gets a clear, actionable message without digging through logs
- Server is technically "healthy" from the host's perspective (no restart loops)

### Generalizes to

Any MCP failure mode: missing dependencies, auth expired, service unavailable, database moved. Don't crash, communicate.

---

## Cache Staleness After Writes: Non-Issue (Pending Confirmation)

### The concern

After writing via the JS bridge, how quickly does OmniFocus update the SQLite cache? If it's lazy, reads from SQLite could return stale data.

### What we found

An official **Omni Group engineering blog post** describes the architecture:

- OmniFocus catches insert/update/delete notifications and does a **two-phase commit between XML and SQLite**
- The cache is updated as part of the same operation that writes to XML — it's transactional, not lazy
- On startup, OmniFocus builds a validation dictionary from the XML transaction log, checks it against SQLite metadata, and if they don't match, **rebuilds the entire SQLite cache**

Community evidence supports this: every reported case of "cache stopped updating" was a path change (like OF3.5 moving to Group Containers), never the cache becoming stale while OmniFocus was running.

**Conclusion:** The SQLite cache is almost certainly current by the time the bridge call returns. This is scenario 1 (immediate) or very-fast scenario 2 (batched within milliseconds).

---

## TODO: Tests & Validation Before Implementation

### 1. Cache update timing test (5 minutes)

Write a task via the JS bridge, then immediately poll the SQLite file and check if the new task appears. Confirms whether the two-phase commit means "instant" or "a few seconds."

```bash
# Pseudocode
1. Record SQLite mtime
2. Write task via bridge
3. Poll SQLite mtime / query for new task
4. Measure delay
```

### 2. Validate overdue/due_soon priority in bridge enum

Confirm that in the bridge's single-winner `taskStatus` enum, overdue/due_soon take priority over blocked. If true, fallback mode preserves ~90% of the use case (urgency axis guaranteed even without SQLite). Either way fallback mode is the plan — this just determines how complete it is.

### 3. Benchmark SQLite reads

Quick benchmark of SQLite read performance on the real database. The research says ~11ms. Confirm this holds, and check if it's fast enough to skip caching entirely (the existing cache infrastructure can be left in place but may not be needed).

---

## Prior Art (for reference)

All existing community tools use the XML path, not SQLite:

| Project | Language | Status | Notes |
|---------|----------|--------|-------|
| rubyfocus | Ruby | Unmaintained | Most complete .ofocus parser, handles delta merging |
| focus | Kotlin/JVM | Active | CLI + library, perspective-like filtering |
| ofocus-format | Docs | Reference | Reverse-engineered format spec |
| pyomni | Python | Older | Basic task manipulation |

No production-quality Python library exists for OF4. Our PoC is arguably the most complete Python implementation. However, since we're going SQLite, the XML parser becomes fallback-only and doesn't need to be production-grade.

---

## Summary of Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary read path | SQLite cache | Pre-computed status flags, ~11ms, no logic reimplementation |
| Fallback read path | JS bridge or XML, degraded mode | Honest about reduced quality, urgency axis likely preserved |
| Write path | JS bridge (unchanged) | Only safe option, OmniFocus must process mutations |
| Status model | Two independent axes (urgency + availability) | Fixes the "overdue masks blocked" problem (173 affected tasks) |
| Startup failure handling | Error-serving mode (not crash) | Agent is the real user, communicate failures via tool responses |
| Service layer blocking logic | DELETE IT | SQLite provides this natively, no reimplementation needed |
| Caching | Likely unnecessary at 11ms, but keep infrastructure | Can remove later if confirmed unnecessary |
