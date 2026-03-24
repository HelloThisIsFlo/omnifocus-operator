# FastMCP v3 Spike

Pre-migration exploration before committing to milestone v1.2.2.

## Why

Milestone v1.2.2 proposes migrating from `mcp.server.fastmcp` (bundled) to standalone `fastmcp>=3`. The main driver is protocol-level logging (`ctx.info()` instead of our file-based workaround), but FastMCP v3 brings much more: middleware, a test client, dependency injection, progress reporting, and elicitation.

This spike validates the migration path and explores what's worth using.

## How to Run

```bash
# Install (already in dev deps)
uv sync

# Run any experiment
uv run python .research/deep-dives/fastmcp-spike/experiments/01_minimal_server.py

# Or use the guide skill for a structured walkthrough
# /fastmcp-spike
```

## Experiments

| # | Name | Category | Question |
|---|------|----------|----------|
| 01 | Minimal Server | de-risk | Does our lifespan/tool pattern work with v3? |
| 02 | Client Logging | de-risk | How does ctx.info()/warning()/error() work? |
| 03 | Server Logging | de-risk | get_logger() vs FileHandler vs stderr? |
| 04 | Test Client | de-risk | Can Client(server) replace 90 lines of plumbing? |
| 05 | Middleware | explore | What middleware exists? Replace _log_tool_call()? |
| 06 | Context Access | de-risk | ctx.lifespan_context vs ctx.request_context? |
| 07 | Progress | explore | Does report_progress() work for batches? |
| 08 | Dependency Injection | explore | Depends() vs lifespan pattern? |
| 09 | Elicitation | explore | ctx.elicit() for "are you sure?" prompts? |

## Findings

See [FINDINGS.md](FINDINGS.md) — built up during exploration.
