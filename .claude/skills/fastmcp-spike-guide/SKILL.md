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

## Experiments

There are 9 experiments in `.research/deep-dives/fastmcp-spike/experiments/`. Each is a standalone Python script.

| # | File | Category | Key Question |
|---|------|----------|-------------|
| 01 | `01_minimal_server.py` | de-risk | Does our lifespan/tool/ToolAnnotations pattern work? |
| 02 | `02_client_logging.py` | de-risk | How does ctx.info()/warning() work? What does the client see? |
| 03 | `03_server_logging.py` | de-risk | get_logger() vs FileHandler vs stderr — what goes where? |
| 04 | `04_test_client.py` | de-risk | Can Client(server) replace 90 lines of stream plumbing? |
| 05 | `05_middleware.py` | explore | What middleware exists? Could it replace _log_tool_call()? |
| 06 | `06_context_access.py` | de-risk | ctx.lifespan_context vs ctx.request_context — which works? |
| 07 | `07_progress.py` | explore | Does report_progress() work for batch operations? |
| 08 | `08_dependency_injection.py` | explore | Depends() vs lifespan pattern — cleaner? |
| 09 | `09_elicitation.py` | explore | ctx.elicit() for destructive op confirmations? |

## Flow

### Phase 1: Pick an experiment

1. Read `FINDINGS.md` to see what's already been explored
2. Present the experiment table, highlighting which are done vs remaining
3. **Recommended order**: 01 → 06 → 02 → 03 → 04 → 05 → 07 → 08 → 09
   - Start with 01 (basic migration shape) and 06 (context access) — these are blockers
   - Then logging (02, 03) — the main driver
   - Then test client (04) — the big DX win
   - Exploration experiments (05, 07, 08, 09) in any order
4. Let the user pick. If they ask "what's next?", recommend based on the order above

### Phase 2: Run the experiment

1. Read the experiment file to refresh on what it does
2. Brief the user on what to look for — 3-4 bullet points, conversational
3. Tell them the command: `uv run python .research/deep-dives/fastmcp-spike/experiments/0X_*.py`
4. **Do NOT run it yourself.** The user runs it and shares the output.
5. If the script has errors:
   - Help debug and fix the script
   - The experiments are meant to be tweaked — encourage the user to modify them
   - If an API doesn't work as expected, that IS a finding

### Phase 3: Interpret results

After the user shares output:

1. **Highlight surprises** — anything that differs from what we expected based on FastMCP docs
2. **Answer the experiment's key question** — give a clear verdict
3. **Connect to the migration** — what does this mean for v1.2.2?
4. **Suggest follow-up tweaks** — "Try changing X to see if Y also works"
5. Ask the user for their take before recording

### Phase 4: Record findings

Help the user update `.research/deep-dives/fastmcp-spike/FINDINGS.md`:

- For each experiment section, record:
  - **Verdict**: One-line answer to the key question
  - **Observations**: What we saw (2-4 bullets)
  - **Surprises**: Anything unexpected
  - **Migration impact**: What this means for v1.2.2

Use the Edit tool to update the relevant section in FINDINGS.md. Keep it scannable — bullets over prose.

### Phase 5: Go/No-Go (after all experiments)

When all experiments are done (or enough to decide):

1. Summarize the de-risk experiments: did anything block the migration?
2. Summarize the exploration experiments: what's worth including?
3. **Ask the user for their decision** — do NOT make the call yourself
4. Help them fill in the Go/No-Go section of FINDINGS.md
5. If "go": help scope the migration (must-do vs nice-to-have vs future)

## Tone

- Lab partner, not lecturer
- "Here's what I'd watch for..." not "You should test..."
- Celebrate interesting findings, especially surprises
- If something doesn't work, that's valuable data, not a failure
- Keep it conversational — this is exploration, not a test suite

## Important Rules

- **Never run experiments yourself** — the user runs them
- **Never pre-fill findings** — help the user write their own
- **Never make the go/no-go decision** — it's the user's call
- If the user wants to skip experiments or go out of order, that's fine
- If the user wants to modify an experiment script, encourage it
- If the user discovers something not covered by the 9 experiments, roll with it
