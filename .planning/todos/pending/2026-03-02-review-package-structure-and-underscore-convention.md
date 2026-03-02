---
created: 2026-03-02T12:22:28.614Z
title: Review package structure and underscore convention
area: general
files:
  - src/omnifocus_operator/
---

## Problem

The package layout feels bloated with many nested folders (bridge/, models/, repository/, service/, server/) each containing `__init__.py` + underscore-prefixed private modules (`_protocol.py`, `_repository.py`, `_mtime.py`, `_service.py`, `_server.py`, etc.). This pattern is uncommon in typical Python projects and may be over-engineered for the current codebase size.

This is a static/structural concern — it doesn't affect functionality. Worth reviewing before the milestone ends, once more code is in place and the full shape of the project is clearer. May decide to keep the current structure, simplify it, or find a middle ground.

## Solution

TBD — Options to consider:

1. **Keep as-is** if the structure proves its value as the codebase grows
2. **Flatten** some packages (e.g., single-module packages that don't need a folder)
3. **Drop underscore prefix convention** if the `__init__.py` re-export pattern doesn't justify the complexity
4. Consider inserting a phase before milestone end to do a clean restructure
