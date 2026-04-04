---
created: 2026-04-04T13:49:52.656Z
title: Make inbox a first-class value instead of null overloading
area: general
files: []
---

## Problem

`null` is overloaded to mean "inbox" in multiple contexts: `actions.move` (null = move to inbox), `project` field on tasks (null = in inbox), `inInbox` filter, and `project: null` in queries. This creates confusion — in most other fields, null means "clear this value" (patch semantics), but for inbox it means a specific destination. The mental model bends in inconsistent ways.

## Solution

Design effort: introduce an explicit inbox value (e.g. string `"inbox"` or sentinel) to replace null-as-inbox across the API surface — move destination, project field, query filters. This is a breaking change that needs careful design discussion. The current behavior is defensible but confusing.
