---
created: 2026-03-20T12:13:19.817Z
title: Add repository contract tests for behavioral equivalence
area: testing
files:
  - src/omnifocus_operator/repository/in_memory.py
  - tests/test_service_resolve.py
  - tests/test_service_domain.py
---

## Problem

InMemoryRepository and RealBridge (via bridge.js) are tested independently — automated tests use InMemory, UAT uses Real. There's no formal guarantee they behave the same. If they diverge, automated tests pass but production breaks.

Phase 26 will merge InMemoryRepository with InMemoryBridge, making this the natural moment to formalize the contract.

## Solution

Create a shared repository contract test suite:
- Define behavioral scenarios as data (not implementation tests): "after add_task(name='X'), get_task returns it", "tags resolve case-insensitively", etc.
- Run programmatically against InMemoryRepository/InMemoryBridge in CI
- Generate equivalent UAT steps for manual verification against RealBridge
- When both pass the same scenarios, behavioral equivalence is proven for those scenarios

Timing: Phase 26+ (when InMemoryRepo merges with InMemoryBridge)

Context: Surfaced during Phase 22 UAT — the test strategy review showed each module has its own test approach (stubs, real InMemory, pure), but nothing formally ties InMemory behavior to Real behavior.
