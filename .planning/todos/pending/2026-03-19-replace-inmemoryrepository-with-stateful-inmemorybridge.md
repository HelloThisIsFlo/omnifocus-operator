---
created: 2026-03-19T19:05:35.785Z
title: Replace InMemoryRepository with stateful InMemoryBridge
area: repository
files:
  - src/omnifocus_operator/repository/in_memory.py
  - src/omnifocus_operator/bridge/in_memory.py
  - src/omnifocus_operator/repository/bridge.py
---

## Problem

`InMemoryRepository` bypasses the entire serialization boundary. Its `edit_task` has ~80 lines of business logic simulating OmniFocus behavior (tag diffing, lifecycle, moveTo, camelCase→snake_case mapping). This simulation can drift from reality — if someone changes `by_alias=True` in `BridgeWriteMixin` or renames a model alias, all tests pass (InMemoryRepository doesn't serialize) but production breaks.

## Solution

Make `InMemoryBridge` stateful so tests can use `BridgeRepository + InMemoryBridge` instead of `InMemoryRepository`:

1. InMemoryBridge maintains mutable task/project/tag collections as camelCase dicts
2. `send_command("get_all")` returns the full state
3. `send_command("add_task", params)` adds to state, returns `{id, name}`
4. `send_command("edit_task", params)` mutates state, returns `{id, name}`
5. Provide a fake MtimeSource (incrementing counter after each write)
6. Tests construct `BridgeRepository(bridge=InMemoryBridge(...), mtime_source=FakeMtime())`

This exercises the real serialization path (`BridgeWriteMixin`), real cache invalidation, and real snapshot parsing (`AllEntities.model_validate()`). The simulation logic moves to InMemoryBridge but works in camelCase — matching what OmniFocus actually receives.
