# Feature Research

**Domain:** MCP server foundation for OmniFocus automation (Milestone 1)
**Researched:** 2026-03-01
**Confidence:** HIGH

## Feature Landscape

This research focuses specifically on Milestone 1 (Foundation). The question is: what features must the first working MCP server have to prove the architecture and establish a solid base for Milestones 2-5?

The existing OmniFocus MCP ecosystem (3+ servers on GitHub) validates the overall concept but also reveals what separates solid foundations from brittle ones. Most competitors use AppleScript or raw JXA via `osascript` -- none use file-based IPC with in-memory snapshots, which is this project's key architectural bet.

### Table Stakes (Must Work On Day One)

Features that must exist for the foundation to prove the architecture. Missing any of these means the pipeline is not validated.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Single MCP tool (`list_all`) returning full database | Proves the entire pipeline end-to-end: MCP registration, service call, repository access, bridge communication, Pydantic serialization | MEDIUM | One tool that exercises every layer. The tool itself is simple; the value is in the infrastructure it proves. |
| Three-layer architecture (MCP -> Service -> Repository) | Separation of concerns required for M2+ to add filtering without rewrites. Service layer is a passthrough in M1 but must exist. | MEDIUM | Thin service layer with a comment explaining why it is thin. Must be injectable/testable from day one. |
| Bridge interface with pluggable implementations | Dependency injection is the core testability mechanism. No hardcoded mocks in server or service code. | LOW | Abstract interface: `send_command(operation, params) -> response`. InMemoryBridge is the M1 primary implementation. |
| InMemoryBridge returning test data | Development and testing without OmniFocus running. Returns realistic data from memory on `dump_all`. | LOW | Python-only, no file I/O. Injected at startup. This is the bridge used for all unit/integration tests. |
| Pydantic models derived from bridge script shape | Typed data contracts between layers. All fields from the bridge dump represented. snake_case with camelCase aliases. | MEDIUM | Task, Project, Tag, Folder, Perspective models. Schema source is `operatorBridgeScript.js` -- do not invent fields. |
| Database snapshot (load once, serve from memory) | Performance foundation. ~1.5MB snapshot is trivially held in memory. No re-querying bridge on every MCP call. | LOW | First call triggers bridge dump. Subsequent calls return cached snapshot. |
| File-based IPC with atomic writes | The production communication path to OmniFocus. `.tmp` -> rename pattern prevents partial reads on both sides. | HIGH | Shared by SimulatorBridge and RealBridge. UUID request IDs, request/response directories, atomic file operations. This is the hardest M1 feature. |
| RealBridge triggering OmniFocus via URL scheme | The actual production trigger: `omnifocus:///omnijs-run?script=...&arg=...`. Without this, the server cannot talk to real OmniFocus. | MEDIUM | Differs from SimulatorBridge only in the URL scheme trigger. Can be one class with optional trigger hook or two classes with shared base. |
| Mock simulator as standalone script | Proves IPC mechanics without requiring OmniFocus. Watches request directory, responds with test data. | MEDIUM | Separate Python process (not part of the server). Handles `dump` and `ping` operations. |
| Snapshot freshness via `.ofocus` mtime check | Cache invalidation strategy. Without this, the server would serve stale data forever or re-dump on every call. | LOW | `stat()` the `.ofocus` package directory. Unchanged mtime = serve cached. Changed mtime = fresh dump. |
| Deduplication lock for parallel dump prevention | Multiple concurrent MCP calls must not each trigger their own bridge dump. asyncio Lock ensures one dump at a time. | LOW | First caller acquires lock and dumps. Others wait and use the fresh cache. Standard asyncio pattern. |
| Timeout handling with clear error messages | OmniFocus might not be running, or the bridge script might hang. 10s hardcoded timeout with descriptive error. | LOW | "OmniFocus did not respond within 10s -- is it running?" Clear, actionable message for the user. |
| Configurable IPC directory | The sandbox path must be overridable for dev/test. Hardcoding to OmniFocus's container path makes testing impossible. | LOW | Default: `~/Library/Containers/com.omnigroup.OmniFocus4/Data/Documents/omnifocus-operator/`. Override via config. |
| Proper MCP error handling (isError flag) | MCP spec distinguishes protocol errors from tool execution errors. Tool errors must use `isError: true` so LLMs can self-correct. | LOW | Protocol errors (unknown tool, malformed request) handled by SDK. Tool execution errors (OmniFocus timeout, parse failure) need explicit `isError: true` responses. |
| stdio transport | Claude Desktop and Claude Code both use stdio transport for local MCP servers. This is the standard for local-process servers. | LOW | FastMCP handles this. `mcp.run(transport="stdio")`. |

### Differentiators (Nice-to-Have Polish for M1)

Features that would be nice but are not required to prove the architecture. Can be added late in M1 or early in M2.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Structured output schema on `list_all` | MCP 2025-11-25 spec supports `outputSchema` for tools. Declaring the output schema lets clients validate responses and gives LLMs better type information. | LOW | Pydantic models can auto-generate JSON Schema. Worth doing if the SDK supports it cleanly, but the tool works without it. |
| MCP Resources for live snapshots | Expose inbox count, task stats, or database summary as MCP Resources (read-only data endpoints). Competitors do this. | MEDIUM | Useful for agent context loading, but `list_all` already returns everything. Resources are a convenience, not a necessity for M1. |
| Tool annotations (readOnlyHint, idempotentHint) | MCP spec allows tools to declare behavioral metadata. `list_all` is read-only and idempotent -- declaring this helps clients make trust decisions. | LOW | Nice metadata but no functional impact. Add if trivial. |
| Structured logging to stderr | MCP spec says servers MUST NOT write to stdout (it corrupts JSON-RPC). Structured logging to stderr helps debugging without breaking the protocol. | LOW | Python logging to stderr. Should happen naturally if logging is set up correctly. Borderline table-stakes for production debugging. |
| Health check / ping operation | A lightweight bridge operation that confirms OmniFocus is responsive without triggering a full dump. | LOW | The simulator already handles `ping`. Adding this to RealBridge is trivial. Useful for diagnostics but not for proving architecture. |
| Progress reporting for slow dumps | MCP supports progress notifications for long-running operations. A full dump of ~2,400 tasks might take a few seconds. | MEDIUM | Nice UX but the dump is fast enough (~1-2s) that progress reporting adds complexity without much value in M1. |

### Anti-Features (Do NOT Build in M1)

Features that seem useful but would be premature, harmful, or out of scope for the foundation milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Filtering logic in M1 | Filtering belongs in the service layer (M2). Adding it now muddies the "is the pipeline working?" validation goal. The service layer is intentionally a passthrough in M1. | Return the full snapshot via `list_all`. Filtering is M2's entire purpose. |
| Multiple MCP tools | M1 proves the architecture with one tool. Adding `list_tasks`, `get_task`, etc. in M1 means testing N tools instead of validating one pipeline. | Ship `list_all` only. M2 adds `list_tasks`. M3 adds entity browsing tools. |
| MCP Prompts | Pre-built prompt templates (daily review, inbox triage) are workflow-specific. The server is deliberately workflow-agnostic -- workflow lives in the agent. | Never build prompts in this server. The agent defines its own workflows. |
| Custom exception hierarchy | Premature abstraction. Real error patterns have not emerged yet. Standard Python exceptions are sufficient for M1. | Use built-in exceptions. Refine when error patterns become clear in M2-M3. |
| Retry logic / circuit breakers | Production hardening is a future milestone concern. In M1, if the bridge fails, fail loudly with a clear message. | Simple timeout with descriptive error. Retry and resilience patterns come later. |
| Write operations | Task creation, editing, deletion are M5. Building writes in M1 means the entire write pipeline (patch semantics, validation, bridge write commands) gets mixed into foundation validation. | M1 is read-only. Writes are the final milestone. |
| TaskPaper output format | An alternative output format adds complexity without proving anything new about the architecture. | JSON only in M1. TaskPaper is a future milestone if ever. |
| WebSocket / SSE transport | Local MCP servers use stdio. Network transports are for remote servers, which this is not. | stdio only. This server runs on the same machine as OmniFocus. |
| Real-time file watching | Watching the `.ofocus` directory for changes and proactively refreshing is over-engineering. Mtime check on read is simpler and sufficient. | Check mtime on every read. Lazy invalidation, not proactive. |
| AppleScript bridge (like competitors) | The file-based IPC approach is already proven and benchmarked. AppleScript is synchronous, blocks the calling process, and has poor error handling. Competitors use it because it is simple -- not because it is good. | File-based IPC via OmniJS URL scheme. This is the project's architectural differentiator. |
| Partial snapshot invalidation | The database is ~1.5MB. Full replacement is simpler and faster than tracking which entities changed. Partial invalidation adds complexity with no performance benefit at this scale. | Full snapshot replacement on mtime change. No partial updates. |
| Configurable timeout | 10s hardcoded is fine for M1. Making it configurable is premature -- the right default has not been validated yet. | Hardcode 10s. Make configurable later if needed. |

## Feature Dependencies

```
[Bridge Interface]
    |
    +-- requires --> [Pydantic Models] (bridge returns data that models parse)
    |
    +-- requires --> [IPC Protocol] (SimulatorBridge/RealBridge need file-based IPC)
    |                    |
    |                    +-- requires --> [Configurable IPC Directory]
    |                    |
    |                    +-- requires --> [Atomic File Writes]
    |
    +-- enables --> [InMemoryBridge] (implements the interface for testing)
    |
    +-- enables --> [SimulatorBridge] (implements the interface + IPC)
    |                    |
    |                    +-- requires --> [Mock Simulator Script]
    |
    +-- enables --> [RealBridge] (implements the interface + IPC + URL trigger)

[Database Snapshot]
    |
    +-- requires --> [Bridge Interface] (snapshot loads from bridge)
    |
    +-- requires --> [Pydantic Models] (snapshot is typed model instances)
    |
    +-- enables --> [Snapshot Freshness] (mtime check gates re-loading)
    |
    +-- enables --> [Deduplication Lock] (prevents parallel loads)

[MCP Server / list_all tool]
    |
    +-- requires --> [Service Layer] (calls service, not repository directly)
    |                    |
    |                    +-- requires --> [Repository + Snapshot]
    |
    +-- requires --> [stdio Transport]
    |
    +-- requires --> [Error Handling] (isError flag for tool failures)
```

### Dependency Notes

- **Pydantic Models are foundational:** Both the bridge interface and the snapshot depend on having typed models. Build models first, derived directly from `operatorBridgeScript.js` output shape.
- **Bridge interface before implementations:** Define the abstract interface, then implement InMemoryBridge (simplest), then SimulatorBridge + IPC, then RealBridge.
- **IPC is the riskiest dependency:** File-based IPC with atomic writes, directory polling, and timeout handling is the most complex M1 feature. It should be implemented and tested with the mock simulator before attempting real OmniFocus communication.
- **Mock simulator enables IPC testing:** The simulator must exist before SimulatorBridge can be validated. Build it early.
- **Service layer is a passthrough but must exist:** The three-layer architecture is a structural requirement even though the service layer does nothing in M1. Skipping it means refactoring in M2.

## MVP Definition

### Launch With (M1 Complete)

Minimum features to declare the foundation milestone done.

- [ ] `list_all` MCP tool returning full structured database -- proves the entire pipeline
- [ ] Three-layer architecture with injectable bridge -- proves testability and separation
- [ ] InMemoryBridge for unit/integration testing -- enables development without OmniFocus
- [ ] Pydantic models matching bridge script output -- typed data contracts
- [ ] Database snapshot with mtime-based freshness -- performance and cache invalidation
- [ ] File-based IPC with atomic writes -- production communication path
- [ ] SimulatorBridge + mock simulator script -- IPC validation without OmniFocus
- [ ] RealBridge with URL scheme trigger -- actual OmniFocus communication
- [ ] Deduplication lock -- prevents dump storms
- [ ] Timeout handling with clear errors -- graceful failure when OmniFocus is unavailable

### Add After Validation (M1 Polish / Early M2)

Features to add once the core pipeline works.

- [ ] Tool annotations (readOnlyHint) -- when the Python SDK makes this straightforward
- [ ] Structured output schema -- when Pydantic-to-outputSchema integration is clean
- [ ] Structured logging to stderr -- when debugging real IPC issues reveals the need
- [ ] Health check / ping via bridge -- when diagnostics become a workflow need

### Future Consideration (M2+)

Features that are entirely out of M1 scope.

- [ ] Filtering and search (M2) -- service layer intelligence
- [ ] Entity browsing and lookups (M3) -- multiple read tools
- [ ] Perspective switching and field selection (M4) -- UI interaction
- [ ] Write operations (M5) -- task/project creation and editing
- [ ] MCP Resources -- if agent context loading patterns emerge

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| `list_all` MCP tool | HIGH | MEDIUM | P1 |
| Three-layer architecture | HIGH | MEDIUM | P1 |
| Pydantic models from bridge shape | HIGH | MEDIUM | P1 |
| Bridge interface + InMemoryBridge | HIGH | LOW | P1 |
| Database snapshot + mtime freshness | HIGH | LOW | P1 |
| File-based IPC + atomic writes | HIGH | HIGH | P1 |
| Mock simulator script | HIGH | MEDIUM | P1 |
| RealBridge + URL scheme trigger | HIGH | MEDIUM | P1 |
| Deduplication lock | MEDIUM | LOW | P1 |
| Timeout handling | MEDIUM | LOW | P1 |
| Configurable IPC directory | MEDIUM | LOW | P1 |
| Error handling (isError flag) | MEDIUM | LOW | P1 |
| stdio transport | HIGH | LOW | P1 |
| Tool annotations | LOW | LOW | P2 |
| Structured output schema | LOW | LOW | P2 |
| Health check / ping | LOW | LOW | P2 |
| Structured logging | MEDIUM | LOW | P2 |

**Priority key:**
- P1: Must have for M1 completion (architecture proof)
- P2: Should have, add when convenient during M1 or early M2
- P3: Nice to have, future milestone

## Competitor Feature Analysis

Three existing OmniFocus MCP servers inform what the ecosystem expects and where this project differentiates.

| Feature | themotionmachine/OmniFocus-MCP | jqlts1/omnifocus-mcp-enhanced | vitalyrodnenko/OmnifocusMCP | Our Approach |
|---------|------|------|------|------|
| Language | TypeScript/Node.js | TypeScript/Node.js | Rust/Python/TypeScript | Python with MCP SDK |
| Bridge mechanism | AppleScript | AppleScript | JXA via osascript | File-based IPC via OmniJS URL scheme |
| Tool count | 11 | 17 | 45 | 1 in M1, 18 at full build |
| Resources | Yes (inbox, today, flagged, stats) | No | Yes (inbox, forecast, projects) | Not in M1. Evaluate later. |
| Prompts | No | No | Yes (daily review, weekly review) | Never. Workflow lives in the agent. |
| Filtering | Per-tool (query_omnifocus) | Built-in perspective tools | Per-tool with sorting | In-memory filtering in M2 via service layer |
| Subtask support | Via parentTaskName | Full hierarchy with visual tree | Full CRUD | Flat list in M1. Hierarchy via parent IDs. |
| Write operations | add, edit, remove, batch | add, edit, remove, move | Full CRUD (23 task tools) | M5 only |
| Custom perspectives | list + view | Native API access | List only | M4 |
| Error handling | Basic | Basic | Destructive action confirmations | isError flag, clear timeout messages |
| Testability | None documented | None documented | None documented | Pluggable bridge: InMemory, Simulator, Real |
| Snapshot architecture | None (queries per call) | None (queries per call) | None (queries per call) | Full in-memory snapshot with mtime freshness |

**Key differentiators of this project vs competitors:**
1. **Pluggable bridge architecture** -- no competitor has documented testability. This project has three bridge implementations (InMemory, Simulator, Real) with dependency injection.
2. **In-memory snapshot with lazy invalidation** -- competitors query OmniFocus on every tool call. This project loads once, serves from memory, re-loads only when `.ofocus` changes.
3. **File-based IPC** -- competitors use AppleScript or JXA via osascript (synchronous, blocking). This project uses async file-based IPC through OmniFocus's own automation URL scheme.
4. **Workflow-agnostic** -- one competitor ships prompts for daily/weekly review. This project deliberately keeps workflow logic in the agent.

## Sources

- [MCP Specification 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25) -- HIGH confidence, authoritative protocol spec
- [MCP Tools Specification](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) -- HIGH confidence, tool capabilities including annotations, outputSchema, error handling
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) -- HIGH confidence, official Python SDK with FastMCP
- [FastMCP (jlowin)](https://github.com/jlowin/fastmcp) -- MEDIUM confidence, actively maintained FastMCP fork with advanced features
- [Build an MCP Server guide](https://modelcontextprotocol.io/docs/develop/build-server) -- HIGH confidence, official tutorial
- [themotionmachine/OmniFocus-MCP](https://github.com/themotionmachine/OmniFocus-MCP) -- MEDIUM confidence, competitor analysis
- [jqlts1/omnifocus-mcp-enhanced](https://github.com/jqlts1/omnifocus-mcp-enhanced) -- MEDIUM confidence, competitor analysis
- [vitalyrodnenko/OmnifocusMCP](https://github.com/vitalyrodnenko/OmnifocusMCP) -- MEDIUM confidence, competitor analysis
- [MCP Server Best Practices 2026](https://www.cdata.com/blog/mcp-server-best-practices-2026) -- LOW confidence, general guidance
- [MCPcat Error Handling Guide](https://mcpcat.io/guides/error-handling-custom-mcp-servers/) -- MEDIUM confidence, error handling patterns
- Project specs: `.research/PROJECT-BRIEF.md`, `.research/MILESTONE-1.md`, `.planning/PROJECT.md` -- HIGH confidence, project-internal

---
*Feature research for: MCP server foundation (Milestone 1) -- OmniFocus Operator*
*Researched: 2026-03-01*
