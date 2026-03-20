# Quick Task 260320-k6u: Centralize agent-facing messages into messages/ package - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Task Boundary

Create an `agent_messages/` package under `src/omnifocus_operator/` that centralizes all agent-facing warnings AND error messages. Internal errors (fail-fast, bridge safety, factory errors) stay inline — only messages that AI agents see belong here.

Agent-facing messages are first-class citizens in this project. The package name and structure must convey that clearly.

</domain>

<decisions>
## Implementation Decisions

### Package Name
- Use `agent_messages/` (not `messages/`) — explicit intent, zero ambiguity about scope

### Duplicate Handling
- Use the same constant for duplicated messages (e.g., one `TASK_NOT_FOUND` for both server.py and resolve.py)
- TODO for later: centralizing lookup paths so "task not found" is thrown from one place (service calling resolve internally)

### Naming Convention
- Claude's Discretion — will use flat descriptive UPPER_SNAKE_CASE (TASK_NOT_FOUND, AMBIGUOUS_TAG, etc.) since ~17 constants don't need prefix taxonomy

### Validation Errors Scope
- Include Pydantic validator error strings from contracts/common.py — agents see these when sending malformed requests, same audience

### Scope Boundary
- **IN scope:** Any string an AI agent receives as a warning or error in tool responses
- **OUT of scope:** Internal errors (RuntimeError in factory, bridge safety guards, adapter init failures) — agents never see these

</decisions>

<specifics>
## Specific Ideas

- Move existing `warnings.py` into `agent_messages/warnings.py`
- Create `agent_messages/errors.py` for the ~17 error constants
- `agent_messages/__init__.py` re-exports everything for flat access
- Add AST-based test enforcement for errors (same pattern as existing `test_warnings.py`)
- Update all import sites (~5-6 for warnings, ~6 for errors, 3 for validators)

</specifics>

<canonical_refs>
## Canonical References

- Todo: `.planning/todos/pending/2026-03-20-centralize-agent-facing-messages-into-messages-package.md`
- Existing enforcement: `tests/test_warnings.py` (AST-based scan pattern to replicate for errors)

</canonical_refs>
