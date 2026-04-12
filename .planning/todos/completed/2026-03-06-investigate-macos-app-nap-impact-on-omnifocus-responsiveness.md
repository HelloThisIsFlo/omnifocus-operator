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

## Investigation (2026-04-12)

**Confirmed**: App Nap is the cause. Activity Monitor shows OmniFocus entering App Nap when backgrounded.

### Findings

- App Nap **throttles** OmniFocus CPU, it doesn't block it entirely
- Lightweight writes (`add_task`) complete quickly even when napped
- Heavy reads (`get_all`) take 10-20s under throttling — exceeded the old 10s timeout
- Apple Events (`osascript -e 'tell application id ... to id'`) wake the process enough to respond, but **don't help URL scheme processing** — different macOS subsystems (AE framework vs Launch Services)
- OmniJS runtime has no Foundation access (`NSProcessInfo` = undefined, `ObjC` = undefined) — cannot call `beginActivity()` from inside the bridge script
- `open -a OmniFocus` would wake from App Nap but steals focus — UX non-starter

### Resolution

Two complementary mitigations:

1. **Default timeout increased from 10s → 30s** (`a44f8265`) — accommodates throttled operations while still failing fast on genuine hangs
2. **Documented `defaults write` fix** (`def06243`) — `defaults write com.omnigroup.OmniFocus4 NSAppSleepDisabled -bool YES` disables App Nap for OmniFocus entirely. One-time, persists across reboots. Documented in `docs/configuration.md`.

Both verified working in bridge-only mode with OmniFocus backgrounded.

## Target Milestone

v1.6 Production Hardening. See `.research/updated-spec/MILESTONE-v1.6.md`, section "App Nap Investigation".
