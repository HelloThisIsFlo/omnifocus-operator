---
created: 2026-03-06T18:22:21.118Z
title: Investigate macOS App Nap impact on OmniFocus responsiveness
area: bridge
priority: low
files:
  - src/omnifocus_operator/bridge/_real.py:158
---

## Problem

During a debug session (2026-03-06), we observed that OmniFocus may stop processing URL scheme automation requests when it has been in the background for a while. The bridge hangs indefinitely — no error, no timeout response. Clicking the OmniFocus window (bringing it to foreground) immediately unblocks all pending requests.

Hypothesis: macOS App Nap throttles OmniFocus when it's not the foreground app, preventing it from processing incoming URL scheme commands.

This has only been observed once. It may be a non-issue, a fluke, or a real reliability problem — needs investigation.

## Solution

Investigation steps:
1. Reproduce: run a bridge request after OmniFocus has been backgrounded for 10+ minutes
2. Check if `open -a OmniFocus` preflight before each bridge request prevents hangs
3. Look into macOS App Nap (`NSProcessInfo.processInfo.beginActivity()`) as root cause
4. If confirmed, add a lightweight wake command in `_trigger_omnifocus()` as preflight

May conclude this is not worth fixing. The goal is to confirm or rule out the behavior.
