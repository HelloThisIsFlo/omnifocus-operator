# Phase 47: Cross-Path Equivalence & Breaking Changes - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-08
**Phase:** 47-cross-path-equivalence-breaking-changes
**Areas discussed:** Breaking change interception, Defer hint mechanism, Cross-path test design, Tool description updates, AvailabilityFilter design, Lifecycle shortcut naming

---

## Breaking Change Interception

| Option | Description | Selected |
|--------|-------------|----------|
| model_validator(mode="before") | Raw dict inspection in ListTasksQuery to catch deprecated inputs | |
| Middleware pattern-matching | Augment ValidationReformatterMiddleware to detect specific errors | |
| **No interception needed** | Project is pre-release, no users, no backward compatibility concern | **Discarded entirely** |

**User's choice:** Area was discarded. User pointed out the project is unreleased with zero external users. The urgency filter never existed as a parameter. No migration paths needed -- just make changes directly.

**Notes:** This was a false premise. The "breaking changes" framing in the milestone spec doesn't apply to a pre-release project. Saved as memory for future phases.

---

## Defer Hint Mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| domain.py detection | Detect in DomainLogic.resolve_date_filters(), same pattern as "soon" fallback | **Selected** |
| resolve_dates.py detection | Detect in the pure resolver, surface via return value | |

**User's choice:** domain.py detection (recommended)
**Notes:** Follows established "soon" fallback pattern. Keeps the pure resolver pure.

---

## Cross-Path Test Design

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit effective_* fields | Neutral dict has both direct and effective keys per date dimension | **Selected** |
| Implicit sync + inheritance tasks | Most tasks auto-sync, special "inherited" tasks have explicit effective_* | |

**User's choice:** Explicit effective_* fields (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Representative coverage | Due with all forms + each other field with one representative form | **Selected** |
| Exhaustive | All 7 fields x all filter forms | |

**User's choice:** Representative coverage (recommended)
**Notes:** Resolution logic is shared. Real risk is adapter bugs and column mapping, not resolver correctness.

---

## Tool Description Updates

**User's choice:** Adapt to codebase conventions, not verbatim from milestone spec.
**Notes:** User emphasized the descriptions.py philosophy: per-field descriptions teach semantics, tool-level covers cross-cutting. Rich schema means per-field carries most weight. Tool-level description has character limit (enforced by test). Key cross-cutting concerns: effective/inherited values, availability vs defer, lifecycle expansion.

---

## AvailabilityFilter Design (emerged during discussion)

| Option | Description | Selected |
|--------|-------------|----------|
| Keep COMPLETED/DROPPED in enum | Two paths to lifecycle inclusion (availability + date filter) | |
| Remove COMPLETED/DROPPED | One canonical path via date filters only | **Selected** |

**User's choice:** Remove COMPLETED/DROPPED.

**Reasoning path:**

The dilemma: `availability: ["completed"]` is immediately intuitive — zero mental model needed. But having TWO paths to lifecycle inclusion (availability enum + date filter shortcut) creates a worse problem: agents don't know which to use, and combining them (`availability: ["completed"], completed: {last: "1w"}`) is redundant.

Arguments for keeping:
- Intuitive: "show me completed tasks" -> `availability: ["completed"]`, done.
- Separation of concerns: "include these states" (availability) vs "when did it happen" (date filter) are conceptually different questions.
- "Show everything" scenario: without ALL, you need three separate things (omit availability + `completed: "all"` + `dropped: "all"`) instead of one.

Arguments for removing (the winning side):
- **One canonical path eliminates confusion.** When both `availability: ["completed"]` and `completed: "all"` exist, agents will be confused about which to use, and no description text fully resolves this.
- **Semantic correctness.** AVAILABLE/BLOCKED answer "can I act on this?" (workability state). COMPLETED/DROPPED answer "is this still alive?" (lifecycle state). They're fundamentally different concepts mixed into one enum.
- **The auto-include mechanism is elegant.** Using `completed: "all"` or `completed: {last: "1w"}` auto-includes completed tasks — the agent never has to think about availability when dealing with lifecycle states.
- **The "show everything" edge case is rare.** That's what `get_all` is for. In a task manager, "show me everything" is almost never what someone actually wants.

The decisive factor: having two paths to the same result is a worse UX problem than `completed: "all"` being slightly less intuitive than `availability: ["completed"]`. One path, well-documented, beats two paths no matter how individually clear each one is.

**Follow-up: ALL -> REMAINING rename**

| Option | Description | Selected |
|--------|-------------|----------|
| Remove ALL entirely | No shorthand for the default set | |
| Rename ALL to REMAINING | Semantic shorthand for available + blocked, borrowed from OmniFocus UI | **Selected** |

**User's choice:** Rename to REMAINING. Default when omitted. Warning for redundant combos.

**Reasoning:** "Remaining" is the term OmniFocus uses in its own UI for the combination of available + on-hold (which maps to available + blocked in our model). Using the same vocabulary aligns the API with the application it wraps. REMAINING as the default means omitting the availability filter = "show me active tasks" — the most common intent.

---

## Lifecycle Shortcut Naming (emerged during discussion)

| Option | Description | Selected |
|--------|-------------|----------|
| "any" (current) | "completed: any" -- slightly awkward English | |
| "all" | "completed: all" -- reads as "all completed tasks" | **Selected** |
| true (boolean) | "completed: true" -- familiar pattern but opposite semantics from flagged: true | Considered, deferred |

**User's choice:** "all" for now. Boolean could be revisited later -- "all" is one string to change.

**Reasoning path:**

"any" works logically (completed when? any time) but reads awkwardly in English — "show any completed tasks" isn't how people say it.

"all" reads naturally: `completed: "all"` -> "all completed tasks regardless of date." The value answers the implicit question "which completed tasks?" and "all of them" is a natural answer. Clean gradient: "all" (broad) -> "today" (narrow) -> `{last: "1w"}` (custom range).

`true` (boolean) was tempting because it mirrors `flagged: true` — the most familiar filter pattern. But the parallel is a trap: `flagged: true` RESTRICTS to flagged tasks only. `completed: true` would EXPAND by including completed tasks. Same syntax, opposite semantics. An agent that learned `flagged: true` = "only these" would expect `completed: true` = "only completed" — but the intent is usually "include completed alongside available tasks." This mismatch would cause real confusion.

Decision: "all" for now. If boolean proves more intuitive in practice, "all" is a single string constant to change — low switching cost.

---

## Lifecycle Expansion Semantics (emerged during discussion)

**The "reverse" insight:** Every other filter in `list_tasks` restricts results — more filters = fewer results. But completed/dropped filters EXPAND results by adding lifecycle states that are excluded by default. This is the opposite of AND-logic intuition.

**Why it's unavoidable:** Completed tasks are excluded by default (the availability gate defaults to [AVAILABLE, BLOCKED]). The completed date filter MUST open this gate — otherwise `completed: {last: "1w"}` would always return empty results (available tasks have NULL completion dates, completed tasks are gated out by availability). The expansion is mechanically necessary, not a design choice.

**Decision: document it, don't warn about it.** The expansion behavior should be explained clearly in the per-field description ("Includes completed tasks in results, excluded by default") and in the tool-level cross-cutting note ("completed/dropped filters include those lifecycle states in results. All other filters only restrict."). No runtime warning is needed when agents combine availability + completed — the description makes the behavior obvious, and the combination is always valid (auto-include adds COMPLETED to whatever availability the agent specified).

---

## Redundant Availability Warnings (emerged during discussion)

**Decision:** Add warnings for redundant availability combinations:
- `["available", "remaining"]` -> "remaining already includes available"
- `["blocked", "remaining"]` -> "remaining already includes blocked"

**Reasoning:** Same philosophy as existing warnings throughout the codebase — educational guidance that helps agents learn the API. Not errors (the query still works), just hints that simplify future calls.

---

## Claude's Discretion

- Cross-path test class organization and parametrization
- Internal REMAINING expansion implementation
- Warning message wording for redundant availability combos
- Whether LIST_PROJECTS_TOOL_DOC also gets the effective-date note

## Deferred Ideas

- count_tasks lifecycle expansion semantics
- "Only completed" filter (no active tasks)
- Boolean shortcut for completed/dropped (revisit later)
