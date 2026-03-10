---
created: 2026-03-10T21:39:05.547Z
title: Remove InMemoryBridge from production exports and factory
area: bridge
files:
  - src/omnifocus_operator/bridge/factory.py
  - src/omnifocus_operator/bridge/__init__.py
  - src/omnifocus_operator/repository/factory.py
  - tests/test_bridge.py
  - tests/test_service.py
---

## Problem

`InMemoryBridge` is a test-only double (call tracking, error simulation, hardcoded data) but it lives in production code and is registered as a bridge factory option (`"inmemory"`). There's no real-world use case for it — it exists purely for testing. Its presence in the factory and public exports blurs the boundary between production and test code.

## Solution

Two-step cleanup:

1. **Remove from public surface** — drop `InMemoryBridge` / `BridgeCall` from `bridge/__init__.py` exports, remove the `"inmemory"` branch from the bridge factory, and update repository factory accordingly. The file stays in `src/` so direct imports (`from omnifocus_operator.bridge.in_memory import ...`) still work. Update test imports to use direct module paths.

2. **Move file to tests/** (separate follow-up) — physically relocate `in_memory.py` out of `src/` into the test tree.
