---
created: 2026-04-04T13:49:52.656Z
title: Add disambiguation warnings for ambiguous entity names
area: server
files:
  - src/omnifocus_operator/service/service.py
---

## Problem

When names/paths are used for referenced entities and multiple entities share the same name (e.g. two "TestDupe" tags), there's no way to know from the response that ambiguity exists.

## Solution

Use the existing `warnings` field in the response to flag ambiguity. Normal responses stay clean with names/paths. When ambiguity exists, the warning provides the IDs needed to disambiguate, e.g.: "Tag name 'TestDupe' is ambiguous -- found IDs oLiUifI8iQQ and b6zXVEYMtF6."
