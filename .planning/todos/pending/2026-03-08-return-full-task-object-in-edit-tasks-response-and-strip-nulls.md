---
created: 2026-03-08T11:51:37.290Z
title: Consider returning full task object in edit_tasks response and stripping nulls
area: service
priority: high
files:
  - src/omnifocus_operator/service/
  - src/omnifocus_operator/models/
---

## Problem

Currently `edit_tasks` returns a minimal response (`success`, `id`, `name`, `warnings`). During UAT, nearly every edit was followed by a `get_task` call to verify the result. In real agent usage this would happen ~20-30% of the time (e.g., checking effective field inheritance after a move, or chaining dependent edits). This doubles round-trips unnecessarily.

## Solution

- Return the full task object in the `edit_tasks` response, matching what `get_task` returns (common REST pattern — GitHub, Stripe, Notion all return full resource on PATCH)
- Consider stripping null fields from the edit response to reduce token count:
  - A typical task has ~8-10 null fields that carry no information
  - Omitting nulls could cut response size by ~40%
  - Current: ~42 tokens → Full with nulls: ~180 tokens → Full without nulls: ~110 tokens
- For `get_task`, keep all fields (including nulls) since the caller explicitly wants the full picture
- Null-stripping is most valuable on `edit_tasks` where the caller just wants confirmation + updated state
