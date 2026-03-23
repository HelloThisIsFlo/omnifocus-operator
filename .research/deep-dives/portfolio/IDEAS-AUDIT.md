# Ideas & Decisions Audit

Catalog of every notable decision in OmniFocus Operator, tagged by origin — which ideas were mine, which came from AI, and which emerged from the collaboration.

**Legend:**
- 🙋⭐ = Mine AND high-impact (shaped the project's character)
- 🙋 = Mine (my idea/decision)
- 🤖 = AI's idea/suggestion
- 🤝 = Collaborative (emerged from discussion)
- ⚙️ = GSD framework (tooling convention)
- ✅ = Obvious / standard practice
- 🥷 = External (borrowed from another project)
- ❓ = Don't remember

---

## Architecture & System Design

1. **[🙋⭐]** **Three-layer architecture** (MCP Server → Service → Repository → Bridge) — the fundamental layering choice
2. **[🙋⭐]** **"Dumb bridge, smart Python"** — keeping bridge.js minimal (~400 lines), all logic in Python (~5000 lines), because OmniJS freezes the UI *(fought for this)*
3. **[🥷]** **File-based IPC with atomic writes** — tmp-then-rename pattern (`os.replace()`) for bridge communication *(from another OmniFocus MCP project)*
4. **[🙋]** **Dispatch string format** — `<uuid>::::<operation>` for IPC request identification
5. **[🙋]** **Full snapshot in memory** — no partial invalidation, because DB is small (~1.5MB)
6. **[🙋]** **Lazy cache population** — no eager startup hydration; first tool call triggers bridge dump
7. **[🙋⭐]** **Error-serving degraded mode (ErrorOperatorService)** — server stays alive when startup fails, serves diagnostic errors as tool responses instead of crashing *(very proud — agent-first thinking)*
8. **[🙋]** **`ErrorOperatorService` via `__getattr__` interception** — raises startup error on any attribute access
9. **[🙋]** **Repository protocol with structural typing** (`typing.Protocol`) — swappable implementations without inheritance
10. **[🙋]** **HybridRepository naming** (not SQLiteRepository) — named for future intent (reads SQLite, writes via Bridge)
11. **[🤖]** **Fresh SQLite connection per read** — `?mode=ro`, because WAL readers see stale snapshots if connections are reused
12. **[🤝]** **WAL-based freshness detection** — poll WAL file mtime (nanosecond precision) after writes, 50ms poll / 2s timeout
13. **[🙋]** **No automatic SQLite-to-bridge failover** — explicit `OMNIFOCUS_REPOSITORY=bridge` env var, because silent failover hides broken state
14. **[🙋]** **bridge/ and repository/ as peer packages** — bridge is general-purpose OmniFocus communication, not just a data source
15. **[🤝]** **Bridge.js loaded via `importlib.resources`** — one-time load at init, no filesystem path coupling
16. **[🙋]** **SimulatorBridge inherits RealBridge** — override only `_trigger_omnifocus`, share IPC mechanics
17. **[🤖]** **Deferred imports in server.py** — enables graceful degradation (import errors don't crash the server)
18. **[🤖]** **MCP server uses lifespan for dependency injection** — clean startup/shutdown, single-pass initialization
19. **[🤝]** **Configuration via environment variables** — `OMNIFOCUS_SQLITE_PATH`, `OMNIFOCUS_REPOSITORY`, `OMNIFOCUS_BRIDGE`
20. **[🙋⭐]** **Service decomposition** — monolithic 669-line `service.py` → 5-module `service/` package (orchestrator, domain, resolve, payload, validate) *(drove this strongly)*
21. **[🙋⭐]** **Method Object pattern for write operations** — every use case gets `_VerbNounPipeline` class, created/executed/discarded in single call *(fought for this, got pushback from AI)*
22. **[🙋]** **Mutable state on `self` in pipelines** — safe because pipeline is ephemeral (single-call lifecycle)
23. **[🤖]** **Read operations as one-liner pass-throughs** — not pipelines, because they don't need orchestration
24. **[🙋⭐]** **Write pipeline unification** — add_task and edit_task follow identical patterns at every boundary
25. **[🙋]** **`BridgeWriteMixin`** — extracts shared `_send_to_bridge()` from write operations
26. **[🙋⭐]** **Write-through guarantee via decorator** — `@_ensures_write_through` ensures WAL mtime advanced before returning
27. **[🤖]** **Orphan IPC file cleanup** — `sweep_orphaned_files()` at server startup
28. **[🤖]** **SQLite database auto-discovery** — finds OmniFocus DB path automatically via known locations
29. **[🤖]** **Async-safe I/O** — all blocking operations wrapped in `asyncio.to_thread()` (IPC writes, WAL polling, SQLite reads)

## Type System & Domain Modeling

30. **[🤖]** **UNSET sentinel class** — custom singleton for "field not provided" with `__bool__` returning False
31. **[🤖]** **UNSET Pydantic integration** — `__get_pydantic_core_schema__` using `is_instance_schema` so UNSET validates but doesn't appear in JSON schema
32. **[🙋]** **`Patch[T]` type alias** — `Union[T, _Unset]` for set-or-omit (cannot clear)
33. **[🙋]** **`PatchOrClear[T]` type alias** — `Union[T, None, _Unset]` for set, clear, or omit
34. **[🙋]** **`PatchOrNone[T]` type alias** — same union as PatchOrClear but different name because None is meaningful data (e.g., inbox) *(naming is mine)*
35. **[🙋]** **Three aliases with identical implementation** — different names for identical unions because semantics differ
36. **[🙋]** **`is_set()` TypeGuard** — runtime check: `not isinstance(value, _Unset)`
37. **[🤖]** **`changed_fields()` on CommandModel** — returns only explicitly-set fields for patch operations
38. **[🙋⭐]** **Four-layer type flow** — Command → RepoPayload → RepoResult → Result, with named types at each boundary
39. **[🙋⭐]** **Two-axis status model** — OmniFocus has a single status enum; I decomposed it into two independent axes: urgency (time pressure) and availability (work readiness) *(big one)*
40. **[🙋⭐]** **Axes as separate fields, not a new enum** — a task can be "overdue AND blocked" simultaneously; a combined enum would lose that independence
41. **[🤖]** **Python adapter for bridge-to-model mapping** — dict lookup tables, in-place mutation
42. **[🤖]** **Mapping tables over conditionals** — `_TASK_STATUS_MAP` dict instead of if/elif chains
43. **[🙋]** **ParentRef unified model** — `{ type: "project"|"task", id, name } | null`, replacing separate project/parent fields
44. **[🤝]** **Inbox as first-class location** — `None` in parent/move context means inbox, not "nothing"
45. **[🙋⭐]** **"Key IS the position" moveTo design** — `{"ending": "parentId"}` where the key is the semantic position
46. **[🤝]** **Exactly-one-key validation on MoveToSpec** — Pydantic validator ensures illegal states unrepresentable
47. **[🙋⭐]** **Actions block separation** — idempotent field setters (top-level) vs stateful operations (actions block: tags, move, lifecycle)
48. **[🙋]** **Reserved slots in actions block** — lifecycle slot reserved during Phase 16.1, filled in Phase 17
49. **[🤝]** **Diff-based tag computation in Python** — `_compute_tag_diff()`, ~4 lines replacing ~45 lines JavaScript *(my idea, AI implementation)*
50. **[🤝]** **TagAction with three modes** (add/remove/replace) — mutual exclusivity validator
51. **[🙋]** **Lifecycle via `Literal["complete", "drop"]`** — no reactivation because OmniJS `markIncomplete()` unreliable
52. **[🤝]** **`drop(false)` universally** — single code path for both non-repeating (permanent) and repeating (skip occurrence)
53. **[🙋]** **RepetitionRule as structured fields** — 4 fields, not RRULE strings, empirically verified from 27 OmniJS audit scripts
54. **[🤖]** **camelCase serialization aliases** — Python snake_case internally, camelCase in JSON
55. **[🤖]** **`populate_by_name` for test ergonomics** — tests use snake_case, agents see camelCase
56. **[🤝]** **`extra="forbid"` on write models** — catches agent typos (e.g., `duedate` vs `dueDate`)
57. **[🤝]** **`extra="ignore"` on read models** — forward compatibility for new bridge fields
58. **[🤖]** **`TYPE_CHECKING` + `model_rebuild()`** — resolves circular references without runtime issues
59. **[🙋]** **Fail-fast on unknown enum values** — Pydantic ValidationError with valid values listed
60. **[🤝]** **Per-entity status resolvers in bridge.js** — tasks/projects/tags have different status semantics
61. **[🥷]** **Effective fields modeling** — `effectiveDueDate`, `effectiveFlagged` alongside direct fields *(from OmniFocus itself)*
62. **[✅]** **Estimated minutes (not hours/duration)** — domain choice for time estimation
63. **[🙋]** **Per-item results in write responses** — array API with single-item constraint, future-proofed for batch *(scope decision)*
64. **[🙋]** **Batch limit = 1 with clear error message** — expand later when demand justifies *(scope decision)*
65. **[🤖]** **Project-first parent resolution** — try `get_project` before `get_task` (intentional order)
66. **[🤝]** **Cycle detection in move validation** — prevents circular parent references *(my idea, AI implementation)*

## Testing & Quality

67. **[🙋⭐]** **Golden master contract testing** — 42+ scenarios captured from live OmniFocus, replayed against InMemoryBridge in CI
68. **[🤝]** **Three-tier normalization** — VOLATILE (random every run) / UNCOMPUTED (not yet implemented) / PRESENCE_CHECK (null vs non-null matters, timestamp doesn't) *(motivation 100% mine, solution collaborative)*
69. **[🤖]** **The ratchet mechanism** — remove field from UNCOMPUTED → tests auto-tighten with zero changes
70. **[🙋]** **`"<set>"` presence-check sentinel** — normalize time-dependent fields to verify presence without timestamp matching
71. **[🙋]** **InMemoryBridge as stateful test double** — maintains mutable state, handles add/edit, not just a stub *(my idea, agent implemented)*
72. **[🙋]** **InMemoryBridge stores raw camelCase dicts** — matches real bridge format, tests exercise same adapter path *(my idea, agent implemented)*
73. **[🙋]** **Ancestor-chain inheritance in InMemoryBridge** — walks project→task hierarchy for effective fields *(my idea, agent implemented)*
74. **[🤖]** **BridgeCall recording** — call tracking dataclass on test double for assertion
75. **[🤝]** **Error injection** — `set_error()`/`clear_error()` on InMemoryBridge for fault testing
76. **[🤝]** **WAL path simulation in InMemoryBridge** — updates mtime for cache invalidation tests
77. **[🙋]** **StubBridge extraction** — separate canned-response double for tests needing predictable output
78. **[🤖]** **SAFE-01: Runtime guard on RealBridge.__init__** — checks `PYTEST_CURRENT_TEST`, refuses instantiation
79. **[🤖]** **`type(self) is RealBridge` check** — allows SimulatorBridge subclass to bypass guard
80. **[🤖]** **Meta-test scanning for guard removal** — test scans all test files for code that would circumvent SAFE-01
81. **[🤖]** **CI grep for `RealBridge` in test files** — second enforcement layer
82. **[🤖]** **SAFE-02: uat/ excluded from pytest discovery** — manual UAT scripts never run by CI
83. **[🙋]** **Marker-driven fixture composition** — `@pytest.mark.snapshot()` triggers auto-wiring fixture chain
84. **[🙋]** **Fixture chain** — bridge → repo → service → server wired by conftest
85. **[🤖]** **AST-based message enforcement** — test_warnings.py uses AST parsing to verify all agent messages come from centralized constants
86. **[🤖]** **Negative import tests** — verify test doubles don't leak into production code
87. **[🤖]** **Memory stream E2E testing** — server tests use in-process memory streams, no real sockets
88. **[🙋]** **Four testing layers** — unit / integration / service / E2E, each catching different failure modes
89. **[⚙️]** **Green tests at every commit during refactoring** — 177→313→527→690 tests, never broke
90. **[🤝]** **No-op detection testing** — scenarios where "nothing changed" produce appropriate warnings
91. **[⚙️]** **2.3:1 test-to-production ratio** — 11,464 test LOC vs 4,912 production LOC
92. **[⚙️]** **Zero TODO/FIXME/HACK in production code** *(GSD handles TODOs well)*
93. **[❓]** **Strict mypy with 3 justified `type: ignore`** in production
94. **[🤖]** **`exclude_unset=True` standardization** for patch models (not `exclude_none`, which would lose null=clear semantics)
95. **[🤖]** **Adapter idempotency** — making adapter safe to run on already-transformed data

## Planning & Methodology

96. **[🙋⭐]** **Spec-before-code** — milestone specs written before implementation begins
97. **[🙋⭐]** **Six features deliberately rejected** (DISCARDED-IDEAS.md) — each with rationale
98. **[🙋⭐]** **Six deep dives before architecture finalized** — structured research in `.research/deep-dives/`
99. **[🙋⭐]** **27 OmniJS audit scripts as specification source** — ground truth for bridge behavior
100. **[🙋⭐]** **Contract-first planning** — plans specify behavioral truths, not implementation steps
101. **[⚙️]** **Decimal phase insertion** (8.1, 8.2, 16.1, 16.2) — clean mid-milestone discovery handling
102. **[🙋]** **Bottom-up dependency ordering** — models → bridge → repo → service → MCP
103. **[⚙️]** **Incremental migration over big-bang** — green tests at every commit during model overhaul
104. **[✅]** **Convention decisions wait until patterns emerge** — defer naming choices until after implementation *(happened organically)*
105. **[❓]** **Only plan what's needed** — don't plan nice-to-have plans (plan 08.1-04 cut)
106. **[🙋]** **Clean break over backward compatibility** — no aliases/deprecation at alpha stage, reserve v2.0 *(project not published yet, no backward compat needed)*
107. **[⚙️]** **Quick tasks as separate queue** — 7 quick tasks handled during v1.2.1 without derailing roadmap
108. **[🙋]** **Gap closure as intentional feature** — Phases 26-28 grew through UAT-driven discovery *(my initiative to expand in that direction)*
109. **[🙋]** **Deferred items explicitly captured** — every phase documents what didn't fit scope
110. **[🤝]** **Dependency ordering for refactoring phases** — strictness → relocation → taxonomy → unification
111. **[⚙️]** **Seed system for future ideas** — `.planning/seeds/` with trigger conditions
112. **[🙋⭐]** **Different UAT for refactoring vs features** — refactoring UAT = developer experience, feature UAT = user behavior
113. **[🤝]** **Version strategy** — v1.x series for features, v2.0 reserved for workflow logic

## Agent & Developer Experience

114. **[🙋⭐]** **Warnings over errors** — domain logic returns warnings for valid-but-surprising transitions, only errors for genuine invariant violations
115. **[🙋⭐]** **Educational warning messages** — teach agents correct usage through response feedback
116. **[🙋⭐]** **Error messages that teach** — include what went wrong, why it matters, how to fix, what the tradeoff is
117. **[🙋]** **Centralized agent messages** — `agent_messages/` package, single source of truth for all agent-facing strings
118. **[✅]** **Parameterized message constants** — `{placeholder}` format strings, not inline f-strings
119. **[🙋⭐]** **Agent-first design philosophy** — agents are intelligent, should see domain surprises before acting
120. **[🙋⭐]** **Package structure navigable by `ls`** — no utils/, no helpers/, every package has clear purpose
121. **[🙋⭐]** **Architecture doc with Mermaid diagrams** — 647 lines, sequence diagrams, decision trees, known quirks
122. **[🙋⭐]** **Naming that encodes architecture** — AddTaskCommand/AddTaskRepoPayload/AddTaskResult tells you the layer
123. **[🤝]** **CQRS-inspired naming** — Command vs RepoPayload vs Result suffix system
124. **[✅]** **Method length discipline** — most methods 10-20 lines, consistent structure
125. **[🤖]** **`TEMPORARY_simulate_write()`** — deliberately ugly name to ensure cleanup
126. **[🙋]** **Known OmniJS quirks documented** — 4 documented in architecture.md (removeTags unreliable, null-note rejection, opaque enums, same-container moves)
127. **[🤖]** **Single runtime dependency** (`mcp>=1.26.0`) — no logging frameworks, no config libraries, no ORM
128. **[✅]** **No custom exception hierarchy** — standard Python exceptions, refine when patterns emerge

## Scope & Restraint

129. **[🙋]** **No task reactivation** — OmniJS API unreliable, deliberately excluded
130. **[🙋]** **No tag writes** — out of scope for v1.2
131. **[🙋]** **No folder writes** — out of scope
132. **[🙋]** **No undo/dry-run** — explicitly rejected
133. **[❓]** **No summary/lightweight mode** — deferred to v1.4 field selection
134. **[❓]** **No task deletion** — deferred to v1.4
135. **[🤝]** **No position field for add_tasks** — deferred, focus on inbox creation
136. **[🙋]** **No repetition rule writes** — deferred, golden master ready for when implemented
137. **[🤝]** **No mutually exclusive tag enforcement at server level** — UI sufficient for agent guidance
138. **[🙋]** **No automatic failover** — explicit env var over silent degradation
139. **[🙋]** **Workflow-agnostic server** — exposes primitives, not opinions about task management
140. **[🙋]** **No eager cache population** — lazy, on first tool call
141. **[🤖]** **`_Unset` leading underscore** — marks internal/sentinel, alternatives considered and rejected

## Agent Role Design (AI Conductor)

142. **[🙋⭐]** **Agent roles with deliberate knowledge boundaries** — different tasks need different epistemological profiles: naive (UAT regression — forbidden from reading source), thorough (ground truth audit — forbidden from skipping edge cases), skeptical (coverage audit — respects layer boundaries). What the agent is forbidden from knowing is the design decision.
143. **[🙋⭐]** **Agent constraints as the feature** — a UAT agent that reads source will work around bugs instead of surfacing them. The constraint IS the value.
144. **[🙋⭐]** **Domain expertise encoded into reusable skill prompts** — not one-off session instructions, but persistent roles invokable across sessions. Five custom skills built for this project.
145. **[🙋]** **Warnings as the agent's learning signal** — agent-facing warnings are designed so that an AI tester evaluating them with "beginner's mind" would take the correct action. The warning text IS the test.

---

**Total: 145 items**
