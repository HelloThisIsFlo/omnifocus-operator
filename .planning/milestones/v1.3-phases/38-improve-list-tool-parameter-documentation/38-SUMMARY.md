# Phase 38 Summary: Improve list tool parameter documentation

**Status:** Complete (no formal GSD pipeline)
**Commits:** 48a676e, b091287
**Dates:** 2026-04-04 to 2026-04-05

## Why no PLAN.md, VERIFICATION.md, or formal process?

This phase was pure documentation — string changes to `Field(description=...)` constants
and tool docstrings. The work was done as a collaborative phrasing session between the
developer and Claude, where exact wording was discussed and iterated on directly. There
was no code logic to plan, verify, or validate — only prose to get right.

The GSD pipeline (planner, executor, verifier) adds value for implementation phases.
For a phase that's entirely "pick the right words," the discussion IS the process.

## What was done

- Added `Field(description=...)` to 12 bare query model parameters across all 5 list tools
- Reworked 5 list tool descriptions to focus on output fields (since outputSchema isn't visible to agents)
- Updated 3 availability enum docstrings
- Added folder hierarchy note to `list_folders` tool description
- Added tag hierarchy note to `list_tags` tool description (matching folders pattern)
- Fixed tag parent field description: "tag name" → "tag ID" (was incorrect)
- Added perspectives built-in caveat (`PERSPECTIVES_BUILTIN_NOTE` with TODO(v1.5))
- Fixed Unicode `\u2264` → ASCII `<=` in estimatedMinutesMax description
- Added Tool Descriptions acceptance criteria to MILESTONE-v1.3.1.md (list_tasks hierarchy note deferred to v1.3.1 where parent/project fields change)

## Deferred to v1.3.1

- list_tasks hierarchy explanation (parent vs project) — v1.3.1 changes these fields, so the description should be written then
