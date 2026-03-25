---
name: fastmcp-spike-guide
description: Guide through FastMCP v3 spike experiments interactively. Walks through each experiment, explains what to look for, helps record observations and build up FINDINGS.md. Use when the user says "fastmcp spike", "run experiments", "spike guide", "explore fastmcp", or wants to work through the FastMCP v3 migration experiments.
---

# FastMCP v3 Spike Guide

Interactive lab partner for the FastMCP v3 spike experiments. You guide, the user drives.

## Context

Read these files to understand the spike:
- `.research/deep-dives/fastmcp-spike/README.md` — overview
- `.research/deep-dives/fastmcp-spike/FINDINGS.md` — current state of findings (may be partially filled)

## Two Interaction Modes

### Server-interactive experiments (02, 03, 05, 06, 08)

The script IS the MCP server. The user connects via MCP Inspector or Claude Code.

**Flow:**
1. Read the experiment file to understand what tools are available
2. Help the user start the server:
   - Option A: `uv run python .research/deep-dives/fastmcp-spike/experiments/0X_name.py` + MCP Inspector
   - Option B: `uv run python .../setup_mcp.py add XX` → restart Claude Code
3. Walk through the `GUIDED WALKTHROUGH` in the experiment docstring, one step at a time
4. Ask what they see at each step — the answers ARE the experiment results
5. When done, help them run `setup_mcp.py remove` if they used Claude Code

**Key principle:** You CANNOT run these yourself or test them in-process. The whole point is the user observing what the real client shows. Ask questions like "What did Claude Code show you?" and "Did you see a warning inline?"

### Code-interactive experiments (01, 04, 07)

The script runs standalone and prints structured output. The guide walks through the code.

**Flow:**
1. Read the experiment file
2. Brief the user: "Run this, then we'll look at the output together"
3. After they share output, interpret it
4. Then walk through the CODE: "Open the script at line X, now open conftest.py:Y — see how this replaces that?"
5. The script is a prop for guided exploration, not the experiment itself

## Experiments

| # | File | Type | Key Question |
|---|------|------|-------------|
| 01 | `01_server_and_context.py` | code | Does our migration pattern work? Context inventory? |
| 02 | `02_client_logging.py` | server | What does the client see when tools log via ctx? |
| 03 | `03_server_logging.py` | server | stderr hijacked? get_logger()? Dual logging? |
| 04 | `04_test_client.py` | code | Can Client(server) replace 90 lines of plumbing? |
| 05 | `05_middleware.py` | server | What middleware exists? Replace _log_tool_call()? |
| 06 | `06_progress.py` | server | Does the client render progress? |
| 07 | `07_dependency_injection.py` | code | Depends() vs lifespan — cleaner? |
| 08 | `08_elicitation.py` | server | ctx.elicit() for destructive op confirmations? |

## Recommended Order

01 → 02 → 03 → 04 → 05 → 06 → 07 → 08

- **01** first: sanity check, confirms migration shape works
- **02 → 03** next: logging is the main driver for the migration
- **04**: the big DX win for testing
- **05 → 08**: exploration features (any order is fine)

## Per-Experiment Walkthrough Notes

### 01 — Server & Context (code)
- After output: "Open `server.py:16-17` — those imports change to `from fastmcp import FastMCP, Context`"
- "Now look at `server.py:115` — that's `ctx.request_context.lifespan_context['service']`. The output shows whether the shorter `ctx.lifespan_context` also works."
- "Check the attribute inventory — anything useful beyond lifespan? request_id? transport?"

### 02 — Client Logging (server)
- This is THE experiment. Spend time here.
- After `log_all_levels`: "Which levels appeared? Was debug filtered? Where did warnings render — inline? In a log panel?"
- After `log_with_structure`: "Did structured data appear or just the message string?"
- After `log_in_real_scenario`: "This is what add_tasks would log. Is this useful from the agent's perspective? Better than a log file?"
- Big question: "Would you want EVERY logger.info() in the codebase to become ctx.info()? Or only some?"

### 03 — Server Logging (server)
- After `test_dual_logging`: "Check `/tmp/fastmcp-spike-server.log` — is file output there? And check your client — did protocol messages arrive too?"
- After `test_stderr_write`: "This is the key question. If stderr is hijacked, that's why we need the FileHandler workaround. If it's NOT hijacked, maybe we can use stderr again."
- After `test_get_logger`: "Is get_logger() just logging.getLogger() with extra steps? Or does it add something?"
- Build the logging matrix: client-facing (ctx.info) vs server-side (FileHandler / stderr / get_logger)

### 04 — Test Client (code)
- After output: "Now open `conftest.py:439-481`. That's the _ClientSessionProxy — 40 lines of anyio stream plumbing."
- "And `test_server.py:51-82` — run_with_client, another 30 lines."
- "The script you just ran does the same thing in 3 lines. Worth migrating?"
- Check: "Did error handling work? What type did call_tool return?"

### 05 — Middleware (server)
- After `fast_tool` and `slow_tool`: "Check `/tmp/fastmcp-spike-middleware.log` — do you see timing data?"
- "Now open `server.py:50-63` — that's our manual `_log_tool_call()`. Could this middleware replace it?"
- After `failing_tool`: "What did the client get? Clean error or traceback?"

### 06 — Progress (server)
- Call `process_batch` with 5 items. "Do you see progress updates? A bar? Percentage?"
- "Our add_tasks and edit_tasks process batches. Would progress reporting improve the experience?"
- Reality check: "Does Claude Code actually render this?"

### 07 — Dependency Injection (code)
- After output: "Look at the two patterns side by side. Is Depends() cleaner?"
- "The catch: tools that also need ctx.info() need BOTH ctx AND the dependency. That's most of our tools."
- "And testing: can you override dependencies? Or is the lifespan pattern simpler for testing?"

### 08 — Elicitation (server)
- Call `edit_completed_task` and ACCEPT. "What did the prompt look like?"
- Call it again and DECLINE. "What happened? Did the tool handle it?"
- Call `no_elicitation_fallback`. "Compare: warning-in-response vs interactive prompt. Which is better for agents?"
- Reality check: "Does Claude Code support elicitation? Does Claude Desktop?"

## Recording Findings

After each experiment, help the user update `.research/deep-dives/fastmcp-spike/FINDINGS.md`:

- For each section, record:
  - **Verdict**: One-line answer to the key question
  - **Observations**: What we saw (2-4 bullets)
  - **Surprises**: Anything unexpected
  - **Migration impact**: What this means for v1.2.2

Use the Edit tool to update the relevant section. Keep it scannable.

## Go/No-Go (after enough experiments)

When the user is ready to decide (all experiments or enough to judge):

1. Summarize de-risk results: did anything block?
2. Summarize exploration results: what's worth including?
3. **Ask the user for their decision** — never make the call yourself
4. Help fill in the Go/No-Go section of FINDINGS.md
5. If "go": help scope (must-do vs nice-to-have vs future milestone)

## Important Rules

- **Never run server-interactive experiments yourself** — the user must connect a real client
- **Never pre-fill findings** — help the user write their own observations
- **Never make the go/no-go decision** — it's the user's call
- If the user wants to skip, reorder, or modify experiments — that's fine
- If something breaks, that's valuable data, not a failure
- Encourage tweaking the scripts — they're meant to be modified
