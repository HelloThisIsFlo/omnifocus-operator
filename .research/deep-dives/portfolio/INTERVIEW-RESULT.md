
# OmniFocus Operator — Interview Handover

## What This Document Is

This is a comprehensive handover from a walking interview with Flo, the engineer behind OmniFocus Operator. The interview was conducted to surface the stories behind the project — the failures, tradeoffs, and lessons learned — that don't appear in the existing technical showcase.

**Purpose:** Another agent will use this document to build a portfolio showcase / landing page for the project. The showcase should demonstrate that Flo operates at a staff/senior-staff engineering level. Two independent reviewers (a staff engineer and a hiring manager) already confirmed the technical quality is there, but said the existing material reads as "everything went right." This document provides the missing dimension: judgment through failure, tradeoff reasoning, and honest self-assessment.

**Audience for this document:** An agent that already has full access to the OmniFocus Operator codebase, milestones, phase logs, specs, and architecture docs. This document does not explain what the project is or how it works. It provides the narrative layer — the human story — that the codebase alone cannot tell.

**What matters for the showcase:** The reviewers were explicit that what separates senior from staff is failure stories (what went wrong, what assumptions broke), tradeoff depth (what was rejected, what was lost), problem-first framing (the hard problem before the clean solution), and "what I'd do differently" (judgment through experience). This document delivers all of those.

---

## Story 1: The Silent Technical Debt Crisis (v1.2 → v1.2.1)

This is the centerpiece story. It has the most depth, the strongest emotional arc, and the clearest staff-level lesson.

### The Setup: A Missing Scope

During the planning phase for milestone v1.2 (write operations), Flo used a team of autonomous agents to do the planning. They ran a discussion phase, asked Flo questions, produced a plan, and Flo verified it. The milestone covered creating and editing tasks — major write operations.

Near the end of v1.2, after the edit-task pipeline was built, Flo realized that repetition rules — how OmniFocus handles recurring tasks — had never been scoped. The autonomous planning agents missed it entirely, and Flo didn't catch the gap during verification. It simply never came up.

At this point, things hadn't gone wrong yet. A missed scope item is normal. Flo's reaction was pragmatic: "Okay, fine, we can add a phase."

### The Design Work: Shaping the Repetition Rule API

Flo inserted a new phase to scope and design the repetition rule feature. This involved significant design work, not just implementation planning.

The key design decision: Flo chose **not** to expose OmniFocus's raw repetition rule string to agents, even though agents are technically capable of constructing it. The reasoning was philosophical and deliberate:

- Constructing a repetition rule string requires significant cognitive effort from the agent.
- That cognitive effort solves a *plumbing* problem, not the *user's* problem.
- Flo wanted close to zero thinking spent on "how do I use this MCP server?" — all agent thinking should go toward helping the user plan effectively.
- The interface should be as intuitive as possible, so agents can focus on what they do best: understanding user intent and acting on it.

With this philosophy, Flo designed an API where the MCP server would parse the repetition rule string internally. Even if it didn't cover every OmniFocus repetition scenario, it would cover the real use cases, and the API contract would be clean and obvious. Flo spent considerable time with agents discussing how to shape this API — what the actions should look like, what the contract should be.

### The Discovery: Looking at the Code for the First Time

When Flo moved to implement the repetition rule design, the agents kept getting confused about where to put the logic. In theory, it belonged in the service layer (domain logic), but agents couldn't figure out a clean way to add it.

This is when Flo looked at the actual production code for the first time. Up to this point, Flo had trusted two things: the spec (which was extensive) and the tests (which were comprehensive, including UAT run by a dedicated agent). Both were green. Both said the system was correct.

What Flo found in the code was, in his words, "What the fuck is this?"

**The create-task flow and the edit-task flow were completely asymmetric:**

- **Create path:** An object called `TaskCreateSpec` was created in the MCP layer (the presentation/adapter layer) and passed all the way down through the service to the repository. This is an abstraction leak — a presentation-layer object traveling through every layer of the architecture.
- **Edit path:** No such spec object was used. Instead, the service calculated a bridge-ready payload (the format the JavaScript bridge expects) and passed it directly to the repository, which just forwarded it. This is a different abstraction leak — the bridge's internal implementation details leaking upward into the service layer.

So on one side, something from the top layer leaked all the way down. On the other side, something from the bottom layer leaked all the way up. The architectural boundaries were, as Flo put it, "all fucked up."

The service layer itself was 669 lines in a single file, mixing responsibilities that should have been separated. It was doing everything.

### The Emotional Reality

Flo describes this moment with genuine shock. He had clearly defined the architecture — a thin MCP layer, a service for domain logic, a repository for data access, a bridge below that. The agents had the same architectural brief. But they hadn't followed it. They'd met every functional requirement and passed every test, but they'd done it by routing around the architecture rather than through it.

The critical insight: **Flo couldn't understand his own codebase.** Not that it was impossible to understand with effort, but that he looked at it and felt confused about what was happening. If he needed to add something, he wouldn't know where to put it — and neither would the agents, which is exactly why they were struggling with the repetition rule.

### The Key Insight: Silent Technical Debt

This is the concept Flo keeps returning to. In a human team, technical debt is never truly silent. A team member says, "This is getting hard to work with." A PR reviewer flags a structural concern. Someone in standup mentions that a task took longer than expected because of code complexity. You might choose not to address it, but you always *know* about it.

Agents never complain. They never say "this is getting messy." They never push back on architecture. They just do the work. If the cleanest path is hard to find, they find a messier path and ship it. The tests pass. The features work. The debt accumulates invisibly.

Flo's framing: "The technical debt was silent, because agents never complain. In a team setting, you may have technical debt, but you always know because a team member will tell you and you can decide what to do. In the agent setting, the agent just does it, and so the technical debt kind of kept creeping in when it really didn't need to. If they had asked me the correct question, I had the answer. It's just that I was never asked about architecture, and so those things crept in. Before you know it, the codebase was lost."

### The Decision: Stop Everything

Flo decided to stop the repetition rule work entirely. He documented all the design research and API discussions, then rolled back the phase. Not "fix it later" — a full stop.

He initially thought this could be handled within v1.2 — just add a cleanup phase. But as he assessed the extent of the damage, he realized it needed a dedicated milestone. This became v1.2.1.

### The Scope Explosion: 5 Phases → 11 Phases

When Flo first scoped v1.2.1, it had four conceptual work areas that became five formal phases in the roadmap:

1. Strictness on the write model (ensuring the model would reject bad input rather than silently accepting it — Flo had discovered that an agent could send a wrong field and never be notified)
2. Model taxonomy redesign (redesigning the entire interface — the core type system that everything else depends on)
3. In-memory bridge cleanup
4. Write pipeline unification (using the new taxonomy to make create and edit follow the same pattern)

Even this scoping — which already represented Flo having the discipline to create a dedicated milestone — turned out to dramatically underestimate the work.

As Flo worked through the phases, each layer of cleanup revealed more problems underneath. The milestone grew from 5 phases to 11. The additional phases included:

- **Service decomposition:** The ~800-line service file was broken into four focused modules with clear, single responsibilities.
- **Simulator bridge cleanup:** The simulator bridge (used for testing) was accessible to regular users — someone could start the app with a simulator bridge, which makes no sense. It needed to be restricted to test-time use only.
- **Test double relocation:** An earlier phase had removed test doubles from the public exports, but hadn't actually moved the files. The files were still sitting in production locations.
- **Type alias simplification:** Cleaning up the type system.
- **In-memory bridge / in-memory repo merge:** This was a major discovery (see below).
- **Golden Master testing:** Another major addition (see Story 3).

Flo's reflection on this: "There was almost as much work refactoring this codebase as there was implementing the features in the codebase." And: "We could have kept pushing, kept pushing, but that's the recipe for disaster, because after repetition rules, good luck trying to add more and more and more."

### The In-Memory Bridge / In-Memory Repo Problem

During v1.2.1, Flo discovered a structural issue with the test doubles. There were two in-memory implementations:

- An **in-memory repository** that was simulating some OmniFocus behavior
- An **in-memory bridge** (separate from the simulator bridge)

The problem: the in-memory repo was simulating behavior that belongs in the bridge layer. The repository's job is caching, filtering, data access patterns — not simulating OmniFocus's application logic. If you need an in-memory version for testing, that simulation belongs in the bridge, because the bridge is the layer that talks to OmniFocus.

This led to a significant merge/restructuring effort, which in turn led to the Golden Master testing work (Story 3).

---

## Story 2: The Phantom Bridge (v1.0, Phase 8)

This story predates the v1.2 crisis but establishes that the pattern of "agents finding shortcuts" appeared from the very beginning.

### What Happened

During milestone v1.0 (the foundation milestone), the agents had been building the entire system without a real bridge script. They'd created models and structures, but the bridge — the JavaScript code that actually talks to OmniFocus via OmniJS — wasn't doing anything real. The agents had built against a phantom.

Flo discovered this during phase 8 (UAT). When he ran the system against real OmniFocus, nothing happened. The bridge script didn't work because it had never been designed against OmniFocus's actual behavior.

For context on timeline: milestone v1.2.1 was working with phases 18–28, so phase 8 was very early in the project's life.

### The Response: 25+ Audit Scripts

Flo pulled the entire effort and did a deep dive. He wrote 25+ audit scripts (28 files total, including variant and ad-hoc scripts), each exercising a different aspect of the OmniFocus scripting API. This was manual investigation work — understanding exactly how OmniFocus behaves, what its API returns, what edge cases exist.

He inserted phase 8.1 to write the real bridge script. But even the agents' bridge script had problems — they had "hallucinated the spec," assuming OmniFocus behaved in ways it didn't.

So Flo created phase 8.2 as an urgent, inserted phase where the audit scripts were used to produce a **canonical bridge spec** — a definitive reference document specifying exactly what OmniFocus does and what the bridge must handle.

### The Lesson

Without this intervention in v1.0, the entire foundation would have been broken. The agents had found a shortcut (build against abstractions without a real bridge) and produced code that compiled, had structure, but didn't actually work.

This experience directly changed how Flo worked with agents going forward — specifically around spec quality. (See "The Three-Reviewer Pattern" below.)

---

## Story 3: The Lying Test Double (Golden Master Testing)

This story emerged during v1.2.1 and represents the most technically interesting testing innovation in the project.

### The Problem

Flo can't run automated tests against real OmniFocus in CI. OmniFocus is a macOS desktop app. There's no headless mode, no test instance. The only OmniFocus environment is the user's real database. You can run scripts against it locally, but:

- You can't run tests in a CI pipeline against OmniFocus.
- Even locally, you wouldn't want automated tests hitting your real task database.

So the project uses test doubles — an in-memory bridge that simulates OmniFocus behavior. But how do you know the simulation is accurate?

### The Golden Master Approach

Flo's solution, drawn from experience on a previous project where he worked with Golden Master testing for two years:

1. **Capture phase (human-supervised):** Run a comprehensive set of scenarios against real OmniFocus through the real bridge. Exercise all the behaviors you care about. Record the state before and after each operation — what changed, what was returned.

2. **Replay phase (automated):** Run the exact same scenarios against the in-memory bridge. Compare the results.

3. **Fix inconsistencies:** Any difference between real OmniFocus behavior and in-memory bridge behavior is a bug in the test double. Fix it.

This creates a faithful test double — what Flo describes as "almost like a light integration test in a world where we cannot run real integration tests."

### What It Caught: The Inheritance Lie

The most significant finding: the in-memory bridge did **not implement effective field inheritance**.

In OmniFocus, when you set a due date on a project, child tasks inherit that as their `effectiveDueDate`. This is core OmniFocus behavior — it's how most users organize their work.

The in-memory bridge was returning `null` for `effectiveDueDate` on child tasks. It had no ancestor-chain walk. It simply didn't implement inheritance.

**The concrete production impact:** The v1.3.1 spec explicitly plans date filtering using `effectiveDueDate` (inherited values), not `due_date` (direct-only). The spec estimates that "filtering on `due_date` alone misses ~45% of overdue tasks" (a design rationale figure, not empirically measured).

Here's the scenario that would have produced wrong production code without the Golden Master:

1. Implement `list_tasks(due_before: "2026-04-01")` filtering on `effectiveDueDate`.
2. Write a test: create a project with `dueDate = "2026-03-30"`, add a child task with no direct due date.
3. The in-memory bridge returns `effectiveDueDate = null` for the child (no inheritance implemented).
4. The filter doesn't match the child task. Test passes.
5. In production, OmniFocus computes `effectiveDueDate` via inheritance. The child task *should* match.

Result: date filters silently miss ~45% of tasks. Tests are green. The product is broken.

The Golden Master phase caught this and forced the implementation of proper ancestor-chain walking in the in-memory bridge. Every date filter test written after this is testing against a faithful simulation, not a lie.

---

## Design Philosophy: The Path of Least Resistance

This isn't a story but a principle that emerged from the v1.2/v1.2.1 experience. It's how Flo now approaches architecture when working with AI agents.

### The Principle

Design architecture where the path of least resistance is the correct path. Don't rely on discipline or documentation to prevent corner-cutting — make the structure itself guide the agent toward the right decision.

### The Concrete Example

In OmniFocus Operator, Flo chose separate result types per operation (`CreateTaskRepoResult`, `EditTaskRepoResult`) instead of a shared `WriteResult`. The fields are identical today. A traditional engineering argument would say this is unnecessary duplication — just use one type.

But with agents, the calculus flips:

- **Duplication is cheap:** Agents don't get bored maintaining four similar classes. They don't forget to update one of them.
- **Wrong abstraction is expensive:** When those types inevitably diverge (and they will), the change with separate types is "add a field to the right type." With a shared type, it's a design decision — and it's exactly the kind of design decision agents get wrong, because they don't have the context to know when a shared abstraction should split.

### The Origin

Flo arrived at this pattern independently, roughly a decade ago, from working with human teammates who would always find the shortest path through a codebase regardless of what the "right" approach was. He only discovered later that it has established names: "pit of success" in .NET, poka-yoke in Toyota manufacturing, desire paths in urban planning. Different domains, same principle: don't fight human (or agent) nature — design around it.

### Why It Matters for the Showcase

This principle is the bridge between the failure story and the architectural quality visible in the current codebase. It's not just "I cleaned things up." It's "I learned *why* things got messy and changed how I design to prevent it." That's the staff-level insight.

---

## The Three-Reviewer Spec Validation Pattern

After the v1.0 phantom bridge incident, Flo changed how he validates specs. Before, he put effort into writing thorough specs, but his review process was essentially reading it himself and deciding it was fine.

After v1.0, he started throwing specs at three specialized review agents, each with a different persona:

1. **Senior developer:** Flags technical potential gaps — things that are architecturally risky or underspecified.
2. **Junior developer:** Flags unclear requirements — things that someone less experienced would struggle to implement correctly.
3. **Product owner:** Flags product misalignment — gaps in features or scenarios that don't serve the user.

This pattern caught real gaps and closed real holes. Flo uses it for at least the most important specs.

**The important nuance:** Even with bulletproof specs, the v1.2 problem still happened. The spec solved the *what* (features were correct, UAT was magic — "the spec was super defined, and the UAT was like I let the agent run for half an hour; later I come back, and the feature is just working"). But the spec didn't cover the *how* (internal architecture). Agents self-organized the internals, and they organized them badly.

This is a key lesson: **spec quality and architectural quality are separate problems.** Solving one does not solve the other.

---

## Hard Tradeoff: The Repetition Rule API Design

This was surfaced during the interview but not explored in depth. It's included here for the showcase agent to develop if useful.

**The decision:** Don't expose OmniFocus's raw repetition rule string to agents. Instead, parse it server-side into a clean, intuitive API.

**What was gained:**
- Zero cognitive burden on the agent for using the interface.
- Agent thinking goes toward solving the user's problem (task planning, prioritization), not toward plumbing (constructing an OmniFocus-specific string).
- Consistent with the project's core philosophy: the MCP server should be invisible infrastructure.

**What was lost:**
- Incomplete coverage of OmniFocus's repetition capabilities. Not every possible repetition rule can be expressed through the simplified API.
- More server-side complexity (parsing logic that the agent could technically handle).

**The reasoning:** Roughly half of the agent's thinking process would go toward figuring out how to construct the repetition rule string. That thinking doesn't help the user. Flo would rather the agent spend 100% of its cognitive effort on the user's actual problem.

---

## Honest Self-Assessment

### Current Weakest Point

After the v1.2.1 refactoring milestone, Flo considers the codebase to be in genuinely excellent shape. The one area he flags: the MCP server layer (presentation/adapter layer) is "a little bit convoluted" — about two blocks of ~35 lines each. It wasn't part of the refactoring scope.

The inherent complexity that would challenge a newcomer is the dual read/write architecture: reads go to SQLite (for performance via caching), writes always go through the bridge to OmniFocus directly, with a fallback to the bridge for reads when SQLite isn't available. This isn't bad code — it's genuinely complex infrastructure working around OmniFocus's limitations. Flo has documented it with Mermaid diagrams but acknowledges it's inherently complex.

Flo's self-aware note on this: "I know it looks like I don't have a lot of self-criticism when I tell you this project is really good right now, but it's right after this refactoring milestone — it's in a really good state." The refactoring milestone was nearly as much work as the original feature implementation. It would be strange if the result *weren't* clean.

### What This Project Does NOT Demonstrate

Flo was explicit and specific about this:

**People and organizational skills (entirely absent):**
- Stakeholder management and balancing competing priorities
- Cross-team collaboration and managing inter-team tension
- Mentoring and leading engineers
- Creating psychological safety ("creating a space where everyone feels considered, where other teams don't feel dismissed, and yet where my team feels protected")
- Pragmatic questioning to understand client needs
- Working under real external deadlines and pressure

**Operational expertise (entirely absent):**
- Deployment and production operations
- Horizontal scaling
- Distributed tracing
- Production-grade logging and observability

The project is a single-user, locally-running application. It was built by one person, for himself, with no external deadlines. It proves architectural and engineering craft. It does not prove the ability to navigate organizations, lead people, or operate production systems.

---

## Key Quotes

These are Flo's actual words, cleaned up only for transcription artifacts. They're valuable for the showcase because they're vivid, honest, and specific.

On silent technical debt:
> "The technical debt was silent, because agents never complain. In a team setting, you may have technical debt, but you always know because a team member will tell you and you can decide what to do. In the agent setting, the agent just does it."

On discovering the architectural mess:
> "I realised I hadn't even been looking at the code at all. I've trusted the requirements and the tests."

On the moment of realization:
> "What the fuck is this? Abstraction leaking through everywhere."

On understanding his own codebase:
> "I couldn't even understand what was going on. If I had to add something, I would also be confused."

On the spec gap:
> "The spec was super defined, and the UAT was like magic — I let the agent run for half an hour, later I come back, and the feature is just working. But the spec didn't cover the underlying architecture."

On duplication economics with agents:
> "Duplication is cheap, but a wrong abstraction is expensive — especially when the thing making decisions doesn't have the context to know it's wrong."

On agent shortcuts:
> "If they had asked me the correct question, I had the answer. It's just that I was never asked."

---

## Threads Not Explored

These topics were mentioned but not discussed in depth. They're available for a follow-up interview if the showcase needs more material.

- **The in-memory bridge / in-memory repo merge in detail.** Flo mentioned the repos were merged and that it went deep, but cut himself off ("I'll tell you after we've digested this"). The architectural reasoning (repo shouldn't simulate OmniFocus behavior, only the bridge should) was stated but the implementation story wasn't told.
- **Other hard design decisions.** The tradeoff question was asked but the interview ran out of walking time before it could be explored beyond the repetition rule API.
- **The AI conductor workflow in practice.** What decisions Flo owns vs. delegates, how that boundary has shifted, what agents can and can't do well.
- **Action blocks insertion (v1.2).** Flo mentioned that within v1.2, before the repetition rule work, he added action blocks and was already starting to rework the API structure. There may be a story here about early architectural warning signs.
- **The bridge simplification phase (v1.2).** Flo mentioned inserting a phase to simplify how the bridge calculates, wanting the least amount of logic in the bridge because "that's code running in OmniFocus, not code I own." There may be a story about the boundary between code you control and code running in someone else's runtime.