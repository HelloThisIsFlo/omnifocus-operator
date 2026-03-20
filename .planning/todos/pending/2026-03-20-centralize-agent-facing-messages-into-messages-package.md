---
created: 2026-03-20T13:27:25.867Z
title: Centralize agent-facing messages into messages/ package
area: service
files:
  - src/omnifocus_operator/warnings.py
  - src/omnifocus_operator/contracts/common.py
  - src/omnifocus_operator/service/resolve.py
  - src/omnifocus_operator/service/domain.py
  - src/omnifocus_operator/service/service.py
  - src/omnifocus_operator/server.py
  - tests/test_warnings.py
---

## Problem

Agent-facing messages (warnings and errors) are the "communication surface" between the MCP server and AI agents. Warnings are centralized in `warnings.py` with test enforcement, but error messages are inline strings scattered across server.py, service/, resolve.py, domain.py, and contracts/common.py. Also, `warnings` shadows the Python stdlib module name.

17 agent-facing error messages identified. Some are duplicated across modules (e.g., "Task not found" in both server.py and service.py).

## Solution

Create a `messages/` package:

```
src/omnifocus_operator/messages/
    __init__.py    # re-exports everything (flat access for consumers)
    warnings.py    # existing warning constants, moved from omnifocus_operator/warnings.py
    errors.py      # new: 15-17 error message constants
```

Steps:
1. Create `messages/` package, move `warnings.py` into it
2. Add `errors.py` with all agent-facing error constants (lookups, resolution, validation, business rules, payload validation from contracts/common.py)
3. `__init__.py` re-exports all constants — consumers use `from omnifocus_operator.messages import X`
4. Update all import sites (~5-6 files for warnings, ~6 files for errors)
5. Add `test_errors.py` with same AST-based enforcement pattern as `test_warnings.py`
6. Update `test_warnings.py` scan paths

Internal errors (factory, adapter, bridge safety) stay inline — agents never see them.

Key design decision: `__init__.py` re-exports everything. The file split (warnings.py vs errors.py) is for the maintainer. The flat import is for the consumer. No name collisions expected with descriptive UPPER_SNAKE_CASE naming.
