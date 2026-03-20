# Quick Task 260319-tlz: Make bridge protocol explicitly implemented by all bridges - Context

**Gathered:** 2026-03-19
**Status:** Ready for planning

<domain>
## Task Boundary

Make the `Bridge` protocol from `contracts/protocols.py` explicitly implemented by all bridge classes. Currently they satisfy it via structural typing only.

</domain>

<decisions>
## Implementation Decisions

### SimulatorBridge handling
- Explicit `Bridge` on both `RealBridge` and `SimulatorBridge` (not just inherited)
- Rationale: grep-friendly inventory of all implementors

### @runtime_checkable consistency
- Add `@runtime_checkable` to all three protocols (`Bridge`, `Service`) — `Repository` already has it
- No `isinstance` checks exist today; this is for consistency and future availability

### Scope confirmation
- `Service` and `Repository` protocols are already explicitly implemented by their classes
- Only the three bridge classes need changes: `InMemoryBridge`, `RealBridge`, `SimulatorBridge`

</decisions>

<specifics>
## Specific Ideas

- Update RealBridge docstring to remove "no inheritance" note (it will now inherit)

</specifics>
