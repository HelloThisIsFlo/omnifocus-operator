---
created: 2026-04-04T13:49:52.656Z
title: Improve ambiguous tag error message with resolution guidance
area: service
files:
  - src/omnifocus_operator/service/service.py
---

## Problem

The server detects ambiguous tags on write with: "Ambiguous tag '{name}': multiple matches ({ids})" but doesn't tell the caller what to do about it.

## Solution

Append guidance to the error message, e.g.: "Ambiguous tag 'TestDupe': multiple matches (oLiUifI8iQQ, b6zXVEYMtF6). For ambiguous tags, specify by ID instead of name." Tells the caller exactly how to resolve the issue.
