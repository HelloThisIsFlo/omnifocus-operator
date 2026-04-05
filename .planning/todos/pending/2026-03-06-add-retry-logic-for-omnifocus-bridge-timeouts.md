---
created: 2026-03-06T18:22:21.118Z
title: Add retry logic for OmniFocus bridge timeouts
area: bridge
priority: low
files:
  - src/omnifocus_operator/bridge/_real.py:140-158
  - src/omnifocus_operator/bridge/_errors.py:31-39
---

## Problem

OmniFocus sometimes doesn't respond to the URL scheme trigger (`open -g omnifocus:///omnijs-run?...`) with no error message. The bridge times out silently after the configured timeout (default 10s via `OMNIFOCUS_BRIDGE_TIMEOUT`).

Currently there is no retry — a single timeout = immediate failure. This is a potential reliability improvement for flaky responses.

## Solution

Consider adding a configurable retry (e.g., 1 automatic retry on timeout before giving up). Keep it simple — this is a "nice to have" improvement, not urgent. May never be needed if the root cause turns out to be App Nap (see related investigation todo).

## Target Milestone

v1.6 Production Hardening. See `.research/updated-spec/MILESTONE-v1.6.md`, section "Retry Logic for Bridge Timeouts".
