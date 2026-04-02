---
created: 2026-04-01T22:37:13.626Z
title: Clarify repetition schedule and repeat mode edge cases
area: docs
files:
  - docs/omnifocus-concepts.md
  - src/omnifocus_operator/agent_messages/descriptions.py
---

## Problem

The three `schedule` enum values (`regularly`, `regularly_with_catch_up`, `from_completion`) have documented semantics for simple intervals (e.g., "every 3 days"), but the behavior when combined with specific day-of-week patterns (e.g., "every Wednesday and Friday") is unclear:

- How does `from_completion` differ from `regularly_with_catch_up` when the frequency includes `onDays`?
- What happens when the anchor date field (`basedOn`) is not set on the task? Likely falls back to creation date, but needs verification.

Both `docs/omnifocus-concepts.md` and the agent-facing descriptions in `descriptions.py` have WIP flags marking these gaps.

## Solution

0. BEFORE ANYTHING: Read the deep research: `.research/deep-dives/repetition-modes/deep-research.md`
1. ~~Test the edge cases directly in OmniFocus (manual experimentation)~~
2. ~~Update `docs/omnifocus-concepts.md` — remove WIP flags and add clarified behavior~~
3. ~~Update `SCHEDULE_DOC` in `descriptions.py` — remove WIP tag and finalize per-value descriptions~~

Items 1-3 done (eec6241): schedule section rewritten with progressive scenarios + Excalidraw diagram, SCHEDULE_DOC tightened. Schedule WIP flag removed.

**Still open:** What happens when the `basedOn` anchor date field is not set on the task? WIP flag remains in `docs/omnifocus-concepts.md`.
