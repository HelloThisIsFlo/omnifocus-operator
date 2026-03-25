# Portfolio Leverage — Research Findings

How to use OmniFocus Operator as a portfolio piece for staff/team-lead roles.

## Strategic Goal

**Shift the power dynamic.** Make technical credibility self-evident so interviews focus on leadership, communication, and team dynamics — Flo's actual differentiator.

The portfolio's job is NOT to get the job. It's to **take technical doubt off the table** so the conversation moves to what matters: how you lead, communicate, prioritize, and build teams.

---

## What the Research Says

### 1. At Staff+ Level, Portfolios Are About Judgment — Not Code

Every source converges: staff engineer hiring evaluates **systems thinking, influence, and decision quality** — not coding speed or algorithmic ability. Code quality is assumed; what differentiates is *why* you made the choices you made.

Key signals staff rubrics evaluate (Google L6, Meta E6, Stripe L4, Shopify):
- Architectural judgment — do you think in layers, boundaries, and evolution?
- Communication — can you explain trade-offs clearly and succinctly?
- Scope — does your influence extend beyond your immediate work?
- Ambiguity tolerance — can you operate without clear direction?
- Failure awareness — do you think about what could go wrong?

**Implication:** The portfolio should showcase *decisions and trade-offs*, not features. ADRs, architecture docs, and testing rationale are higher signal than feature demos.

### 2. One Deeply Documented Project Beats Many Shallow Ones

A Reddit hiring manager: *"We don't require senior-level engineers to produce a portfolio, but if they have one we generally just throw out all the other applicants."*

Gergely Orosz's cautionary tale: he had a side project with 200K daily users. During his job search, "barely anyone asked or cared about them." The project itself matters less than the **narrative around it** and how easily a hiring manager can consume it.

The winning pattern: one project with ADRs + architecture docs + testing rationale + case study + ARCHITECTURE.md — all pointing at the same codebase. This creates overwhelming signal of engineering maturity.

**Implication:** OmniFocus Operator is the right vehicle. Don't dilute with other projects. Go deep, not wide.

### 3. The AI Narrative Needs Careful Framing

The discourse is bifurcated:
- **Positive:** Staff+ engineers lead AI adoption (63.5% per Pragmatic Engineer). Augment Code now explicitly evaluates "Agent Leverage" in hiring. Anthropic hires generalists because implementation is commoditized.
- **Negative:** "Vibe coding" concerns — AI code has 1.7x more issues, 2.74x more security vulnerabilities (CodeRabbit). Experienced devs were 19% *slower* with AI tools but *perceived* themselves 20% faster (METR).

**The winning frame:** "I used AI as a force multiplier while maintaining architectural control, comprehensive testing, and code quality." The test suite + architecture decisions are the proof. The distinguishing signal: can you explain every design decision? Do you have tests that prove the system works?

**What NOT to say:** "I built this in 3 weeks" without context reads as vibe coding.
**What TO say:** "I directed the architecture, maintained quality standards, and used AI to accelerate implementation — 668 tests, 98% coverage, golden master behavioral equivalence."

### 4. Portfolios Shift the Conversation, Not the Decision

The data:
- 86% of hiring managers visit a portfolio link if provided
- 71% say it impacts their decision
- 30% higher callback rate for portfolio-focused applications
- BUT: recruiters spend 5-10 seconds scanning before deciding to look deeper

A portfolio is most powerful when it **gives the interviewer something to ask about** — shifting conversation from abstract algorithm puzzles to "tell me about this design decision." This is exactly the strategy: take technical credibility off the table, redirect to leadership.

### 5. Non-Goals and Failures Signal More Than Successes

What you chose *not* to do and what went wrong are the highest-signal content. Google's design doc format explicitly includes a "non-goals" section. Charity Majors: writing about failures demonstrates more maturity than polished success stories.

**Implication:** Include "what I'd do differently" and scope decisions (what was deliberately left out) in the portfolio. Example: "v1.6 Production Hardening is intentionally scope-TBD — I won't build hypothetical hardening, only what real usage demands."

---

## Format & Medium Recommendations

### The Meta-Strategy: Progressive Disclosure + The Quiet Reveal

Layer content so different time budgets all get value. The key structural decision: **lead with the architecture, reveal the timeline late.**

The reader should be thinking "this is a serious engineering effort" for several minutes before they discover it was one person in three weeks. That dissonance is the holy shit moment — and because they drew the conclusion themselves, it doesn't feel like a boast. It feels like their discovery.

**Don't claim "I can match a team of five." Show the output, show the timeline. The reader does the math.**

| Layer | Time | Format | Content |
|-------|------|--------|---------|
| **Glance** | 30 sec | Landing page hero | Name, pitch, 5 metric badges, architecture thumbnail |
| **Scan** | 2-5 min | Case study page | Problem → Constraints → Approach → Outcome |
| **Explore** | 10-30 min | ADRs + testing deep dive | Decision rationale, golden master explanation |
| **Verify** | 30+ min | The repo itself | Code, git history, planning docs |

The "AI conductor" story lives in the case study page — but toward the end, after the architecture has already established credibility. The structure is:
1. Here's a hard problem (no API, desktop app bridging)
2. Here's how it's solved (three-layer architecture, golden master testing)
3. Here are the decisions and trade-offs (ADRs)
4. *quiet reveal:* Here's the timeline and how I work (AI conductor section)
5. Reader's internal reaction: "Wait... one person? Three weeks? With THIS quality?"

### Priority Stack (Effort vs Impact)

| Priority | What | Why | Effort |
|----------|------|-----|--------|
| **1** | Case study page (progressive disclosure) | The backbone. 30s→5min experience. | 1-2 days |
| **2** | 5-8 ADRs on key decisions | Shows "why" thinking. Maps to interview questions. | 1-2 days |
| **3** | Testing strategy visual | Golden master diagram + metrics. Strongest staff-level signal. | 2-4 hours |
| **4** | Interactive C4 architecture diagrams | Click-to-explore. Visual polish. | 1 day |
| **5** | CodeTour in repo | Bonus for repo explorers. | 1-2 hours |
| *(opt)* | Video walkthrough | Deprioritized — communication skill demonstrated in interview, not video. Existing conference talk on blog already covers "can present." High effort, low marginal value. | 2-3 hours |

Items 1-4 together: ~3-4 days. Covers the 30s → 30min experience.

### Format Details

**Case Study Page:**
Structure: Problem → Constraints → Approach → Outcome → Lessons.
Mirrors consulting firm case studies and Ashby's "past projects deep dive" interview format. 2 pages, right density, most likely to be fully read.

**ADRs (Architecture Decision Records):**
Showcase-worthy decisions:
- "Dumb Bridge, Smart Python" (architecture invariant)
- Patch semantics with UNSET sentinel (API design)
- Method Object pipeline pattern (code organization)
- Golden master behavioral equivalence testing (test strategy)
- Three-way field distinction: omit/null/value (domain modeling)
- SQLite WAL-based caching over OmniJS bridge (performance)
- Service decomposition boundaries (architecture)
- Test double structural isolation (safety)

Format: MADR template (Status, Context, Decision, Consequences). 1-2 pages each. Scannable. Self-contained.

**Video Walkthrough:**
5-8 minutes. Structure:
1. 1 min: problem and constraints (no API, desktop app bridging)
2. 3 min: architecture walkthrough with diagrams visible
3. 2 min: testing strategy (golden master, the ratchet)
4. 1 min: what I learned / what I'd do differently

This directly demonstrates communication skill — the #1 staff-level evaluation criterion.

**Testing Strategy Visual:**
- Diagram: "Same command → two implementations → compare → if different, test fails"
- Metrics callout: 668 tests, 98% coverage, 42 golden master scenarios, zero mocks of external deps
- One annotated test showing the golden master in action
- The VOLATILE/UNCOMPUTED/PRESENCE_CHECK taxonomy as a concept card

**C4 Architecture Diagrams:**
Structurizr DSL checked into repo, rendered on site. Four zoom levels:
- Context: Agent ↔ MCP Server ↔ OmniFocus
- Container: Server → Service → Repository → Bridge/SQLite
- Component: Service internals (validate, resolve, domain, payload)
- Code: Key patterns (UNSET sentinel, Method Object pipeline)

### Tools

- **Structurizr** or **IcePanel** for C4 diagrams
- **Log4Brains** or **adr-viewer** for ADR navigation
- **Loom** for video recording
- **Docusaurus** or extend existing GitHub Pages for the site
- Existing landing page at `hellothisisflo.github.io/omnifocus-operator` is a solid foundation

---

## The AI Conductor Narrative

### The Framing: Not "AI-Assisted" — AI Conductor

Flo's own framing is stronger than anything the research suggested: **AI Conductor**. Not "I use AI tools." Not "AI-assisted development." An AI conductor orchestrates teams of agents like a general directing an army. The leverage effect (French: *décuple*) — you move a little in the right direction, and the army moves a lot.

**Why this framing works:**
- Avoids the negative ("I'm NOT a vibe coder") — leads with the positive
- Positions orchestration as a **first-class skill**, not a footnote
- Maps directly to what Augment Code now evaluates: "Agent Leverage"
- Maps to the "Coder to Orchestrator" thesis (Nicholas Zakas, 2026)
- The proof is the codebase: too coherent, too well-reasoned to be vibe-coded. The decisions are clearly human-directed.

**The two-part value proposition:**
1. **World-class architecture** — the codebase demonstrates 10-12 years of engineering craft
2. **AI conductor skill** — the ability to achieve 6-9 months of team output in 2-3 weeks by orchestrating AI agents with clear architectural vision

These are complementary: the architecture is excellent *because* the conductor knows exactly where to point the orchestra. An army without a plan achieves chaos. An army with a general who's spent a decade learning strategy achieves this codebase.

**The proof chain:**
- 668 tests, 98% coverage → quality wasn't sacrificed
- Golden master behavioral equivalence → test doubles are faithful, not faked
- Clean typed boundaries → architecture is coherent, not emergent-from-prompts
- ADRs/milestone contexts → every decision has a documented *why*
- v1.2.1 architectural cleanup → the human directed a full internal refactoring milestone that an AI left to itself would never prioritize

**What to include in portfolio:** A section on "How I work" — not defensive, matter-of-fact. "Here's my workflow. Here's what I own (architecture, testing strategy, trade-offs, quality gate). Here's what I orchestrate (implementation execution via agent teams). Here's the result (a codebase that would take a 4-5 person team 6-9 months)."

---

## Relationship to Existing Assets

### Already Built
- **Product landing page** — live at `hellothisisflo.github.io/omnifocus-operator`. Well-designed, current for v1.2. Sells the *product*.
- **README** — condensed marketing copy. Quick start, features, roadmap.
- **Architecture docs** — `docs/architecture.md` with Mermaid diagrams. Technical reference.
- **SEED-006** — planned marketing refresh after v1.3.1 (update features, benchmarks, comparison tables).

### The Gap
The existing assets sell the **product**. Nothing currently sells the **engineer**. The portfolio milestone fills this gap:
- Case study = "here's how I think"
- ADRs = "here's why I chose this"
- Video = "here's how I communicate"
- Testing visual = "here's my quality standard"
- C4 diagrams = "here's how I structure systems"

These complement the product landing page. They can live on the same site (separate section/path) or a separate portfolio site that links to the project.

---

## Key Sources

### Staff Engineer Literature
- Will Larson — [staffeng.com](https://staffeng.com/) (promotion packets, archetypes, interview processes)
- Tanya Reilly — *The Staff Engineer's Path*
- Julia Evans — [Brag Documents](https://jvns.ca/blog/brag-documents/)
- Mike McQuaid — [What is a Staff-Plus Engineer?](https://mikemcquaid.com/what-is-a-staff-plus-principal-engineer/)

### Hiring & Portfolio Research
- Gergely Orosz — [Pragmatic Engineer](https://newsletter.pragmaticengineer.com/) (side projects, AI tooling survey, Stripe culture)
- Dan Luu — [Hiring and the Market for Lemons](https://danluu.com/hiring-lemons/)
- Ashby — [Past Projects Deep Dive](https://www.ashbyhq.com/resources/engineer-past-projects-deep-dive)
- Holloway Guide — [Early Signals in Technical Hiring](https://www.holloway.com/g/technical-recruiting-hiring/sections/early-signals)

### AI-Assisted Development
- Augment Code — [How We Hire AI-Native Engineers](https://www.augmentcode.com/blog/how-we-hire-ai-native-engineers-now)
- Nicholas Zakas — [From Coder to Orchestrator](https://humanwhocodes.com/blog/2026/01/coder-orchestrator-future-software-engineering/)
- Addy Osmani — [Vibe Coding Is Not an Excuse](https://addyo.substack.com/p/vibe-coding-is-not-an-excuse-for)

### Architecture Documentation
- matklad — [ARCHITECTURE.md](https://matklad.github.io/2021/02/06/ARCHITECTURE.md.html)
- C4 Model — [c4model.com](https://c4model.com/)
- ADR — [adr.github.io](https://adr.github.io/)

### Tools
- [Structurizr](https://structurizr.com/) — C4 diagrams as code
- [Log4Brains](https://github.com/thomvaill/log4brains) — ADR site generator
- [Loom](https://www.loom.com/) — Video walkthroughs
- [CodeTour](https://github.com/microsoft/codetour) — VS Code guided tours

### Format Design
- Nielsen Norman Group — [Progressive Disclosure](https://www.nngroup.com/articles/progressive-disclosure/)
- Google — [Design Docs at Google](https://www.industrialempathy.com/posts/design-docs-at-google/)
