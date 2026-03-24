# FastMCP v3 Spike

Pre-migration exploration before committing to milestone v1.2.2.

## Setup

```bash
uv sync --group spike
```

## Experiments

Two kinds: **server-interactive** (you connect a client) and **code-interactive** (you run and read output).

| # | Name | Type | Question |
|---|------|------|----------|
| 01 | Server & Context | code | Does our migration pattern work? Context inventory? |
| 02 | Client Logging | **server** | What does the client see when tools log via ctx? |
| 03 | Server Logging | **server** | stderr hijacked? get_logger()? Dual logging? |
| 04 | Test Client | code | Can Client(server) replace 90 lines of plumbing? |
| 05 | Middleware | **server** | What middleware exists? Replace _log_tool_call()? |
| 07 | Progress | **server** | Does the client render progress? |
| 08 | Dependency Injection | code | Depends() vs lifespan — cleaner? |
| 09 | Elicitation | **server** | ctx.elicit() for "are you sure?" prompts? |

### Running code-interactive experiments

```bash
uv run python .research/deep-dives/fastmcp-spike/experiments/01_server_and_context.py
```

### Running server-interactive experiments

```bash
# Option A — MCP Inspector
uv run python .research/deep-dives/fastmcp-spike/experiments/02_client_logging.py
# Then in another terminal: npx @modelcontextprotocol/inspector

# Option B — Claude Code
uv run python .research/deep-dives/fastmcp-spike/experiments/setup_mcp.py add 02
# Restart Claude Code, test, then:
uv run python .research/deep-dives/fastmcp-spike/experiments/setup_mcp.py remove
```

### Guided walkthrough

Use the spike guide skill for a structured walkthrough:
```
/fastmcp-spike-guide
```

## Findings

See [FINDINGS.md](FINDINGS.md) — built up during exploration.
