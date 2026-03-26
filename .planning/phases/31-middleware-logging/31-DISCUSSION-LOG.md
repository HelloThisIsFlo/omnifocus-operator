# Phase 31: Middleware & Logging - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-26
**Phase:** 31-middleware-logging
**Areas discussed:** Per-tool debug logs, Argument logging, Middleware file location, Log file management, Log level configuration, Startup banner

---

## Per-tool Debug Logs

| Option | Description | Selected |
|--------|-------------|----------|
| Keep response-shape lines | Remove log_tool_call() (MW covers entry). Keep response-specific debug lines (task counts, names, warnings) | ✓ |
| Remove all | Handlers become minimal — just service call + return | |
| You decide | Claude's discretion | |

**User's choice:** Keep response-shape lines
**Notes:** User asked to see concrete log output and code examples before deciding. After seeing that MW handles entry/exit and the debug lines carry response-shape info MW can't see (task counts, warnings), chose to keep them. Also triggered extended discussion about logger hierarchy — how middleware and server can share the same logger via injection.

---

## Logger Hierarchy (emerged from debug logs discussion)

**User's choice:** Use `__name__` convention for all loggers. One root logger in `__main__.py` with two handlers. Middleware receives server's logger via injection (not its own `__name__`).
**Notes:** User asked "where does the logger come from?" and "how does it know?" — led to discovery of Python's logging module singleton/registry pattern. User was previously unaware that `logging.getLogger()` is a global registry with dot-separated hierarchy inheritance. Decided middleware should use injected logger so log lines show `[omnifocus_operator.server]` consistently.

---

## Argument Logging

| Option | Description | Selected |
|--------|-------------|----------|
| Full args at INFO | Log all arguments at INFO level. Revisit if batch sizes grow. | ✓ |
| Args at DEBUG only | INFO shows just tool name + timing. Full args only at DEBUG. | |
| You decide | Claude's discretion | |

**User's choice:** Full args at INFO
**Notes:** Straightforward — batch limit is 1, payloads are small.

---

## Middleware File Location

| Option | Description | Selected |
|--------|-------------|----------|
| New middleware.py | Dedicated file alongside server.py. Logger injected. Clean home for future middleware. | ✓ |
| Inline in server.py | Keep everything MCP-layer in one file. | |
| You decide | Claude's discretion | |

**User's choice:** New middleware.py
**Notes:** User later reinforced that since it's a separate file, the middleware must use injected logger (not `__name__`) to keep log lines under `omnifocus_operator.server`.

---

## Log File Management

| Option | Description | Selected |
|--------|-------------|----------|
| RotatingFileHandler | Size-based rotation: 5MB max, 3 backups (~15MB ceiling). | ✓ |
| Simple FileHandler | Append forever. Grows unbounded. | |
| You decide | Claude's discretion | |

**User's choice:** RotatingFileHandler
**Notes:** Straightforward choice.

---

## Log Level Configuration

| Option | Description | Selected |
|--------|-------------|----------|
| Same level, env var controlled | Both handlers use OMNIFOCUS_LOG_LEVEL (default INFO). One knob. | ✓ |
| Split: stderr=INFO, file=DEBUG | stderr clean, file captures everything. | |
| You decide | Claude's discretion | |

**User's choice:** Same level, env var controlled
**Notes:** Straightforward — one knob preferred.

---

## Startup Banner

| Option | Description | Selected |
|--------|-------------|----------|
| Clean INFO message | Professional log.info() message. | |
| Keep the rockets | Local dev tool, personality is fine. | |
| Remove entirely | FastMCP's own banner is sufficient. | ✓ |

**User's choice:** Remove entirely — FastMCP banner is sufficient
**Notes:** User tested and confirmed FastMCP v3 already prints a startup banner after the Phase 29 migration. No need for a custom one.

---

## FileHandler Comment (emerged from final review)

**User's choice:** Add a comment next to the FileHandler explaining why it exists (Claude Code swallows stderr during tool calls) with a link to `anthropics/claude-code#29035`. Once that issue is resolved, the FileHandler may become redundant.
**Notes:** User specifically requested this as a future-proofing measure.

---

## Claude's Discretion

- Log format strings (timestamp format, level padding)
- Middleware entry/exit log style (`>>>` / `<<<` or alternative)

## Deferred Ideas

None — discussion stayed within phase scope
