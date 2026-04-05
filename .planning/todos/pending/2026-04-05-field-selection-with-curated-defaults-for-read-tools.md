---
created: 2026-04-05T22:00:21.806Z
title: Field selection with curated defaults for read tools
area: service
milestone: v1.4
files:
  - .research/updated-spec/MILESTONE-v1.4.md
---

## Problem

Read tool responses are very large — a single project can be 40+ fields, most irrelevant. `get_all` with 50+ projects burns thousands of tokens on unused data.

## Solution

Mapped to **Milestone v1.4**. `fields` parameter on all read tools, with a curated default set (not "return everything"). See MILESTONE-v1.4.md for full spec and open questions.
