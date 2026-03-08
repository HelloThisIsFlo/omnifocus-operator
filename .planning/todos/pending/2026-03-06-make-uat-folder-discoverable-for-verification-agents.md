---
created: 2026-03-06T18:22:21.118Z
title: Make UAT folder discoverable for verification agents
area: docs
priority: low
files:
  - uat/
---

## Problem

The `uat/` directory contains manual UAT scripts (e.g., `test_read_only.py`) but is not documented anywhere that GSD verification agents (`/gsd:verify-work`) would find it. During a debug session, even the project owner didn't know it existed until pointed out.

Verification agents need to know UAT scripts exist so they can direct users to run them as part of phase verification.

## Solution

Document `uat/` in an appropriate planning document or project-level file so that:
- `/gsd:verify-work` can reference UAT scripts by path
- Phase verification knows to include manual UAT steps

Exact location TBD — could be CLAUDE.md, a planning doc, or the README.
