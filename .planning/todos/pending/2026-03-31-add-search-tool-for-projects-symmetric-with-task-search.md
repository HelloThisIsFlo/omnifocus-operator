---
created: 2026-03-31T11:38:02.879Z
title: Add search tool for projects symmetric with task search
area: server
files:
  - src/omnifocus_operator/service/service.py
  - src/omnifocus_operator/server.py
---

## Problem

Tasks have search/filter capability but projects don't have an equivalent dedicated search tool. While agents can use `list_projects`, a search tool would provide symmetry and make project lookup more discoverable for agents.

## Solution

Add a project search capability at the server layer, leveraging the existing resolution cascade and substring matching infrastructure from Phase 35.2. Scope for v1.3+ when list/search tools are being wired.
