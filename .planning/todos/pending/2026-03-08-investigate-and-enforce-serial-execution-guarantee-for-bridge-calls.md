---
created: 2026-03-08T11:51:37.290Z
title: Investigate and enforce serial execution guarantee for bridge calls
area: bridge
priority: medium
files:
  - src/omnifocus_operator/bridge/
  - src/omnifocus_operator/bridge/real_bridge.py
---

## Problem

Parallel `edit_tasks` calls were observed to execute in the order received, even with an artificial 3-second delay injected into the bridge. This is critical for correctness — dependent moves (e.g., "move C under A, then move B before C") produce correct results only if execution order matches call order.

Currently works in practice, but unclear if this is a hard guarantee or incidental behavior (e.g., OmniFocus serializing osascript calls internally).

### Example of why this matters

Three parallel calls:
1. `move T1-C → child of T1-A`
2. `move T1-B → before T1-C` (expects C to be under A)
3. `move T3-A → after T1-C` (also expects C to be under A)

If call 2 runs before call 1, T1-B goes before T1-C at the original level (siblings), then T1-C moves under T1-A alone — they split. During UAT, this scenario was tested with 3 independent groups and a 3s delay. All 3 groups produced correct results, suggesting serial execution. But we need to confirm this is a guarantee, not luck.

## Solution

- Investigate whether the bridge or OmniFocus enforces serial execution of osascript calls
- If not guaranteed, add a bridge-level lock/queue to enforce ordering
- Formalize as a documented invariant: "Concurrent edit_tasks calls are processed in the order received"
