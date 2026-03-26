# Phase 29: Dependency Swap & Imports - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-26
**Phase:** 29-dependency-swap-imports
**Areas discussed:** Progress reporting vs batch limit

---

## Progress Reporting vs Batch Limit

| Option | Description | Selected |
|--------|-------------|----------|
| Add it anyway | Code is ready when batch limit lifts — trivial, harmless, serves as reminder | ✓ |
| Defer PROG-01/PROG-02 | Wait until batch limit is actually lifted | |

**User's choice:** Add it anyway
**Notes:** User wants it in place now so it's not forgotten later. Acknowledged it's trivial with batch-limit-1 but fine as scaffolding.

---

## Skip Assessment

Most gray areas were pre-resolved by the FastMCP v3 spike experiments (`.research/deep-dives/fastmcp-spike/FINDINGS.md`). The only genuine ambiguity was progress reporting with the current batch limit of 1. All other decisions (import paths, `ToolAnnotations` source, `ctx.lifespan_context` shorthand, documentation scope) were already locked by the spike findings.

## Claude's Discretion

- Exact placement of `report_progress` calls within the handler
- Whether to add `log_tool_call` for progress events

## Deferred Ideas

None — discussion stayed within phase scope.
