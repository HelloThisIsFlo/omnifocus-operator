# Milestone v1.5 -- Production Hardening

## Goal

Reliability and polish. No new tools -- the full 18-tool API surface is complete from v1.4. This milestone makes the server robust enough for daily use without supervision.

## What to Build

### Retry Logic for Bridge Timeouts
- Configurable retry count and backoff for bridge operations
- Clear error messages when retries are exhausted
- Distinguish between "OmniFocus not running" and "OmniFocus slow to respond"

### OmniFocus Launch Detection
- Detect whether OmniFocus is running before attempting bridge operations
- Provide actionable error if not running (for write operations that need it)
- Note: reads via SQLite don't need OmniFocus running (already handled in v1.1)

### Crash Recovery
- Handle partial write failures gracefully
- Clean up orphaned IPC files from crashed processes (basic version exists from v1.0 -- extend if needed)
- Ensure server can recover from unexpected states without restart

### Serial Execution Guarantee for Bridge Calls
- Investigate whether the bridge or OmniFocus enforces serial execution of osascript calls
- If not guaranteed, add a bridge-level lock/queue to enforce ordering
- Formalize as a documented invariant: "Concurrent edit_tasks calls are processed in the order received"
- Critical for dependent moves (e.g., "move C under A, then move B before C")

See: `2026-03-08-investigate-and-enforce-serial-execution-guarantee-for-bridge-calls.md`

### Idempotency
- Define idempotency guarantees for write operations
- Handle duplicate requests gracefully (e.g., agent retries after timeout)

### Startup Validation
- Validate OmniFocus installation and configuration on server startup
- Check SQLite database accessibility
- Verify bridge script compatibility
- Report issues via error-serving mode (already exists -- extend with specific checks)

### App Nap Investigation
- Investigate macOS App Nap impact on OmniFocus responsiveness
- Determine if App Nap causes bridge timeouts
- Implement mitigation if needed (e.g., NSProcessInfo assertions)

### Configurable Timeout
- Note: basic timeout may already exist from v1.0 (10s hardcoded). Evaluate whether it needs to be configurable or if the current value is sufficient.

## Unknowns

Scope is intentionally light. When we get here, evaluate:
- Which of these items have become pain points in daily use?
- Are there new issues discovered during v1.2-v1.4 that need hardening?
- What's the actual failure rate of bridge operations?

Prioritize based on real-world usage data, not hypothetical concerns.

## Key Acceptance Criteria

- Server recovers gracefully from OmniFocus crashes/restarts
- Bridge timeouts produce actionable error messages with retry information
- Server can run a full daily review session without manual intervention
- No new tools -- same 18-tool API surface as v1.4

## Tools After This Milestone

Eighteen (unchanged from v1.4).
