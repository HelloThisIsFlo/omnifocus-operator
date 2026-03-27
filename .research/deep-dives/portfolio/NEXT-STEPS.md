# Portfolio Showcase — Next Steps

## TOMORROW: Walk + Interview

**Plan your walk early.** Take the baby, open Claude mobile app, paste the interviewer prompt, and do the project retrospective interview while walking. This is the #1 priority — it produces the failure stories and tradeoff content that both reviewers flagged as the gap between senior and staff.

Ask Claude here to generate the interviewer prompt before you head out.

---

## Where We Left Off

The CODEBASE-SHOWCASE has been through 3 rounds of edits and 2 rounds of reviewer feedback. It's solid but both reviewers (staff engineer + hiring manager) pegged it at senior-not-staff. The remaining gap isn't code quality — it's **judgment through shipping**. The showcase reads as "everything went right" when staff-level credibility comes from "here's what went wrong and how I recovered."

## The #1 Priority: The Failure Story

You have a powerful story that both reviewers independently asked for. Here it is:

**v1.2 → v1.2.1: The Architectural Cleanup**

During v1.2, the repetition rule was scope creep. AI agents kept shipping features fast, but you realized you'd lost understanding of parts of your own codebase. The speed-without-oversight pattern had created architectural debt — not broken code, but code you couldn't fully navigate or explain.

You stopped feature work and created v1.2.1 — a full refactoring milestone. Not because tests were failing, but because *you* couldn't reason about the system anymore. That's the hardest kind of tech debt to catch: everything works, but the human understanding has eroded.

**Why this story matters for staff level:**
- It's about judgment, not code — you recognized a systemic problem that tests couldn't catch
- It's about the AI conductor role — the army was marching fast, but the general lost the map
- The punchline is a design principle: **speed without understanding is debt**
- You didn't hypothetically regret it — you actually went back and fixed it (v1.2.1 IS "what I did differently")

**Secondary failure stories:**
- OmniJS `removeTags(array)` was flaky — sometimes works, sometimes doesn't. Led to the "remove one at a time in a loop" workaround in bridge.js. Crazy to debug. Shows the kind of platform quirks you can't anticipate.
- Agents made assumptions about OmniFocus behavior despite instructions not to. Led to the 27 OmniJS audit scripts — empirical verification because you couldn't trust assumptions.

## Other Improvements (Lower Priority)

### Problem-First Framing
The hiring manager said: "The headline isn't 'what problem does this solve' — it's 'look at these design patterns.'" The showcase should open with the constraint (no API, desktop app bridging, agents as users) and frame everything after as a response to that challenge. The product landing page sells the product; the portfolio showcase sells the engineer.

### Deep Tradeoffs
Pick 2-3 decisions and show alternatives rejected + what was lost. Example: "SQLite for reads vs bridge-only. Gained 30x performance + blocked detection. Lost simplicity (two mapping paths that must produce identical output). Accepted because [reason]." Research exists in `.research/` — can throw agents at it to surface the pre-architecture tradeoff analysis.

### "What I'd Do Differently" → "What I DID Do Differently"
Reframe: not hypothetical regrets but actual corrections. v1.2.1 is the proof. This is stronger than "I wish I had..." — it's "I noticed, stopped, and fixed it."

### Scaling — Don't Apologize
Single user, single local database, local OmniFocus. That's the domain. Pagination and field selection are coming (v1.3-v1.4). Don't frame as a limitation — frame as scope-appropriate architecture. The reviewers who flagged this were applying cloud-service expectations to a desktop tool.

## My Thoughts on Approach

The failure story is the single highest-impact addition. If you add nothing else, add that. Here's how I'd suggest structuring it:

**New section in the showcase — "Lessons from Shipping" or "What Went Wrong"**
- The v1.2 scope creep story (2-3 paragraphs)
- The OmniJS flakiness story (1 paragraph)
- The agent assumption story (1 paragraph)
- Close with the principle: "The conductor must stay hands-on on architecture"

This section would go between the current Section 9 (AI Conductor) and Section 10 (Taste & Restraint). It bridges "here's how I work with AI" and "here's what I chose not to build" — the failure story explains WHY you have the restraint.

For the problem-first framing, I'd suggest reworking the opening paragraph of Section 1 — or even adding a brief "Section 0" that sets the scene before diving into architecture. But this is a smaller change.

## When You Come Back

**Start with an interview, not a blank page.** Instead of "tell me the failure story," use an interviewer format — Claude asks questions, you answer naturally, and the stories come out through conversation. Much less daunting than writing from scratch.

Two options:
1. **In-session interview** — Claude acts as a book-author/journalist doing a deep project retrospective. Asks targeted questions, follows threads, captures the raw material. Then we shape it into showcase content.
2. **Separate interviewer agent** — A skill or prompt pasted into a fresh session so the main context stays clean. The interviewer has no codebase context (on purpose) — forces you to explain from scratch, which produces better writing.

Either way, the interview should cover:
1. The v1.2 → v1.2.1 story (scope creep, lost understanding, cleanup milestone)
2. OmniJS surprises (flaky removeTags, agent assumptions vs reality)
3. Key tradeoffs (SQLite vs bridge, IPC vs AppleScript, what you researched before deciding)
4. What the project taught you about working with AI agents

After the interview, we extract the best material and add it to the showcase.
