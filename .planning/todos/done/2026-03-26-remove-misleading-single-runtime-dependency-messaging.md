---
created: 2026-03-26T12:38:16.213Z
title: Remove misleading single runtime dependency messaging
area: docs
files:
  - README.md:8
  - README.md:54
  - README.md:121
  - docs/index.html:1852
---

## Problem

The "single runtime dependency" claim is technically true (one direct dep in pyproject.toml) but misleading — `fastmcp>=3.1.1` pulls in a significant transitive dependency tree (mcp, pydantic, etc.). It's not a huge selling point and overstates the minimalism of the project.

Appears in:
- README.md badge (`deps-1`)
- README.md feature bullets (2 mentions)
- docs/index.html landing page (1 mention)

## Solution

Remove "single runtime dependency" as a selling point entirely from both README.md and docs/index.html. Don't replace with alternative wording — just drop it.
