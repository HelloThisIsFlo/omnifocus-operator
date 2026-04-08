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

**User's choice:** Remove COMPLETED/DROPPED. One path is less confusing than two, even though availability: ["completed"] is more intuitive in isolation.

**Follow-up: ALL rename**

| Option | Description | Selected |
|--------|-------------|----------|
| Remove ALL entirely | No shorthand for the default set | |
| Rename ALL to REMAINING | Semantic shorthand for available + blocked, borrowed from OmniFocus UI | **Selected** |

**User's choice:** Rename to REMAINING. Default when omitted. Warning for redundant combos.

---

## Lifecycle Shortcut Naming (emerged during discussion)

| Option | Description | Selected |
|--------|-------------|----------|
| "any" (current) | "completed: any" -- slightly awkward English | |
| "all" | "completed: all" -- reads as "all completed tasks" | **Selected** |
| true (boolean) | "completed: true" -- familiar pattern but opposite semantics from flagged: true | Considered, deferred |

**User's choice:** "all" for now. Boolean could be revisited later -- "all" is one string to change.
**Notes:** The flagged: true parallel is misleading (flagged restricts, completed expands). "all" avoids this trap while reading naturally.

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
