---
created: 2026-04-06T21:35:48.526Z
title: Extend golden master to capture SQLite path output
area: testing
files:
  - tests/golden_master/
  - src/omnifocus_operator/repository/hybrid/hybrid.py
---

## Problem

Golden master snapshots only capture the bridge path (OmniJS → RealBridge). The production read path goes through the SQLite/hybrid mapper, which is a completely different code path. Bugs in the hybrid mapper that only manifest against real OmniFocus data (e.g. the shared task/project table quirks) are invisible to the golden master.

Phase 42 UAT surfaced two such bugs — parent type misclassification and nextTask self-reference — that all 1598 tests passed on but broke against the real database. The bridge path handled these correctly (confirmed by unchanged golden master), but the SQLite mapper didn't.

Cross-path equivalence tests exist but use clean fixture data that doesn't reproduce OmniFocus data quirks. The golden master runs against real data but only covers one of the two paths.

## Solution

**Option B: Copy the OmniFocus SQLite database file during golden master capture.**

During capture, snapshot the SQLite database alongside the bridge output. During replay, point the hybrid repository at the captured file and compare its output against the expected snapshots.

The golden master already uses synthetic test entities (GM-TestProject, etc.) with filtered queries, so data sensitivity and size are non-issues — the infrastructure for data isolation already exists.

This gives both code paths golden master coverage against the same real data. Cross-path divergence becomes a test failure rather than a UAT surprise.
