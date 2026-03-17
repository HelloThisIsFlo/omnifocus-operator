# Quick Task 260317-j2x: Fix F-6: Echo invalid lifecycle value in error message - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Task Boundary

Fix F-6: Echo invalid lifecycle value in error message. When `edit_tasks` receives an invalid `actions.lifecycle` value, the error should echo back the invalid value instead of showing a generic Pydantic message.

</domain>

<decisions>
## Implementation Decisions

### Error message format
- Use "Invalid lifecycle action '{value}' — must be 'complete' or 'drop'" format
- Includes both the invalid value AND the allowed values

### Scope
- Lifecycle field only — it's the only agent-facing Literal field in the write models
- No generic Literal handler needed (YAGNI)

</decisions>

<specifics>
## Specific Ideas

- Verification: `edit_tasks` with `lifecycle: "reopen"` should return error containing "reopen" and NOT contain "type=", "input_value", or "pydantic"
- The error message string/template should live in `warnings.py` (project convention: all user-facing messages centralized there)
- The fix is wired in the error sanitization loop in `server.py` (edit_tasks handler, ~line 280)

</specifics>
