---
created: 2026-03-31T21:22:38.974Z
title: Sweep agent-facing schema descriptions and tool documentation
area: server
files:
  - src/omnifocus_operator/server.py
  - src/omnifocus_operator/contracts/
  - src/omnifocus_operator/models/
---

## Problem

During 36.1 UAT, several documentation gaps surfaced that affect agent experience:

1. **Internal docstrings leaking into schema** — Models like `FrequencyCreateSpec` expose implementation notes ("Same field shapes as Frequency, with extra='forbid' from CommandModel") as `description` in the JSON Schema. Every model docstring Pydantic serializes needs to be agent-useful or absent.
2. **Partial repetitionRule on task with no existing rule** — Tool description says "omitted root fields preserved" but doesn't clarify what happens when there's nothing to preserve. Add guidance: "When creating a new rule (task has none), all three root fields required."
3. **Tag name vs ID resolution undocumented** — Tool description says "tag names or tag IDs" but doesn't state resolution priority. Document: ID match takes priority over name match.
4. **Date timezone behavior undocumented** — Tool descriptions say "ISO 8601" but don't specify whether naive datetimes are accepted or how they're interpreted.

## Solution

- Full sweep of all model docstrings that appear in inputSchema — rewrite to be agent-facing or remove
- Update tool descriptions for repetitionRule, tags, and date fields
- Scope: models in `models/` and `contracts/` that appear in tool schemas, plus tool docstrings in `server.py`
