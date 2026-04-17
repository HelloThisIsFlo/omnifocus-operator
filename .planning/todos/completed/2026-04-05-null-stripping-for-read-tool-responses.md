---
created: 2026-04-05T22:00:21.806Z
title: Null-stripping for read tool responses
area: service
milestone: v1.4
files:
  - .research/updated-spec/MILESTONE-v1.4.md
---

## Problem

A typical task has ~8-10 null fields (`dueDate`, `deferDate`, `completionDate`, etc.) that carry no information but cost tokens. Compounds across bulk reads.

## Solution

Mapped to **Milestone v1.4**. Omit null fields from responses by default. Orthogonal to field selection — they compound. See MILESTONE-v1.4.md for full spec and open questions.
