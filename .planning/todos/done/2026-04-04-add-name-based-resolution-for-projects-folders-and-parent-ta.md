---
created: 2026-04-04T19:06:53.110Z
title: Add name-based resolution for projects, folders, and parent tasks on writes
area: service
files:
  - src/omnifocus_operator/service/resolve.py
  - src/omnifocus_operator/service/service.py
---

## Problem

Currently only tags support name-based resolution on writes (via `resolve_tags` / `_match_tag` in `resolve.py`). Projects, folders, and parent tasks must be referenced by ID. This means agents need to look up IDs before creating/editing tasks — an extra round-trip that the tag resolution pattern already solves.

## Solution

Extend the write-side name-based resolution to all referenced entity types:
- `parent` field (currently ID-only via `resolve_parent`) → resolve by name with case-insensitive exact match, same cascade as tags: name match → ambiguous error → ID fallback → not found
- `project` field → same pattern
- `folder` field → same pattern (where applicable)

Reuse the generic `_match_by_name` method being built in quick task 260404-rxq. Each resolver method fetches only its own entity type (e.g., `list_projects(limit=None)`) rather than `get_all()`.

On ambiguity, raise the generic `AMBIGUOUS_ENTITY` error with "specify by ID instead of name" guidance (also being introduced in 260404-rxq).

## Resolution

Covered by **Milestone v1.3.1 — Inbox as First-Class Value**, section "Name-Based Resolution for Entity References". Bundled per decision DL-13. See `.research/updated-spec/MILESTONE-v1.3.1.md`.
