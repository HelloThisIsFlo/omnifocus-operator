# Phase 49: Implement naive-local datetime contract for all date inputs - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-10
**Phase:** 49-implement-naive-local-datetime-contract-for-all-date-inputs
**Areas discussed:** Read-side _DateBound reversal, Date-only writes without default time, Agent-facing example & description framing, Read-side filter consistency, Normalization placement

---

## Read-side _DateBound reversal

| Option | Description | Selected |
|--------|-------------|----------|
| Unify: accept naive on read side too | Drop _reject_naive_datetime, accept naive datetimes on filter bounds. Uniform contract everywhere. | |
| Keep aware-only on read side | Write side accepts naive, read side keeps requiring timezone. Preserves Phase 48's educational error. | |

**User's choice:** Unify — but clarified context first. Phase 48 was written before the timezone deep-dive. The todo's design document completely overrides Phase 48 decisions. Naive is the contract everywhere. Aware inputs still accepted as convenience.
**Notes:** User emphasized: "any decision in the todo completely overrides everything that's been done before." The deep-dive empirically proved naive-local across 430 tasks. No ambiguity.

---

## Date-only writes without default time

| Option | Description | Selected |
|--------|-------------|----------|
| Accept with warning | Accept date-only, pass to bridge, warn about UTC midnight quirk | |
| Reject with educational error | Reject date-only on write side until settings API todo | |
| Intercept and apply midnight local | Convert date-only to midnight local before bridge | ✓ |

**User's choice:** Intercept and apply midnight local
**Notes:** User's reasoning: "It sets us up for success when we implement the next todo. The only difference is now we hard-code it to midnight, and then we just have to update it with the user preference." Clean upgrade path — same code path, same interception point, swap midnight for DefaultDueTime later.

---

## Agent-facing example & description framing

| Option | Description | Selected |
|--------|-------------|----------|
| "2026-03-15T17:00:00" (naive) | Single naive example, no timezone. Directly teaches the contract. | ✓ |
| Naive primary, aware secondary | Show both formats with naive as main. | |

**User's choice:** Single naive example

| Option | Description | Selected |
|--------|-------------|----------|
| Top of each write tool's doc (inline) | Self-contained per tool. Matches descriptions.py pattern. | ✓ |
| Shared constant referenced by both | DRY but thin abstraction for ~1 sentence. | |

**User's choice:** Inline per tool
**Notes:** User added: "in the tool description, we can add a note saying time zones are also accepted. Just a simple note like this, no example, nothing." Keep it minimal.

---

## Read-side filter _DateBound type

| Option | Description | Selected |
|--------|-------------|----------|
| Use str everywhere | No format: "date-time" anywhere in API. Uniform with write side. | ✓ |
| Keep typed (datetime) on read side | Structural type checking but inconsistent JSON Schema signal. | |

**User's choice:** Yes, use str everywhere

---

## Normalization placement

| Option | Description | Selected |
|--------|-------------|----------|
| Service pipeline (payload builder) | Todo pointed here. Mechanical assembly. | |
| Contract validator | Parse + normalize at input boundary. Adds transformation to contracts. | |
| Domain layer (domain.py) | Product decision: "use local time" is our choice, not universal. | ✓ |

**User's choice:** Domain layer (domain.py)
**Notes:** User said: "In the domain, because this is a domain decision, please read the architecture document to understand why." Referenced the litmus test in architecture.md: "Would another OmniFocus tool make this same choice?" — another tool might require UTC. Using local time is this product's specific choice.

---

## Read-side filter consistency

| Option | Description | Selected |
|--------|-------------|----------|
| Mechanical fix (UTC → local) | Resolver already handles date-only → midnight. Just change anchor. | ✓ |

**User's choice:** Mechanical fix — but with a named function and comment
**Notes:** User wanted the timezone choice captured in a dedicated function with explanatory comment, not scattered as one-liners. "Even if this function just returns the time zone and does nothing, it captures this comment."

---

## Claude's Discretion

- Internal naming of local timezone helper
- Format validation approach in contract validators
- AbsoluteRangeFilter bounds comparison adaptation
- CF epoch math adaptation in query_builder.py
- Test migration approach
- Exact tool description wording

## Deferred Ideas

- OmniFocus settings API for DefaultDueTime/DefaultDeferTime (separate todo, depends on Phase 49)
- Date filters for list_projects (different capability)
