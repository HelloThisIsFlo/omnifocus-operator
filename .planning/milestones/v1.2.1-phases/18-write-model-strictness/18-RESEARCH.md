# Phase 18: Write Model Strictness - Research

**Researched:** 2026-03-16
**Domain:** Pydantic v2 model configuration, validation strictness, warning string consolidation
**Confidence:** HIGH

## Summary

This phase adds `extra="forbid"` to all write-side Pydantic models so unknown fields raise `ValidationError` instead of being silently ignored. The core mechanism is straightforward and well-supported by Pydantic v2. A new `WriteModel` base class inherits from `OmniFocusBaseModel` and adds only `extra="forbid"` -- Pydantic v2 merges `ConfigDict` from parent to child, so alias generation and validation settings are preserved automatically.

The `_Unset` sentinel works correctly with `extra="forbid"` out of the box -- verified experimentally with Pydantic 2.12.5 (the project's version). No changes to the sentinel are needed. The main complication is that the server.py error handler currently loses field names (it joins `msg` strings, which say "Extra inputs are not permitted" without naming the field). This needs improvement to include `loc` data.

**Primary recommendation:** Create `WriteModel(OmniFocusBaseModel)` with `ConfigDict(extra="forbid")`, re-parent all write specs, improve server error formatting to include field names, consolidate all warning strings into a single file.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- New `WriteModel` base class with `model_config = ConfigDict(extra="forbid")`
- `WriteModel` lives in `write.py` (not `base.py`) -- keeps write concerns together
- All write specs inherit from `WriteModel` instead of `OmniFocusBaseModel`
- Strict (extra="forbid"): TaskCreateSpec, TaskEditSpec, MoveToSpec, TagActionSpec, ActionsSpec, and any write-side sub-models
- Strict for writes: RepetitionRuleSpec (shared model in common.py) -- needs write-side variant or restructuring so reads stay permissive
- Permissive (unchanged): All read models (Task, Project, Tag, Folder), result models (TaskCreateResult, TaskEditResult), common read-side models
- Rule: if it accepts agent input, it's strict. If it's server output or from OmniFocus, it's permissive
- Follow existing project conventions for error experience -- agent-first, self-explanatory, no exposed internals
- Extract ALL warning strings across the codebase into a single file (e.g., `warnings.py`)
- Each warning referenced as a constant from that file
- UNSET sentinel must continue supporting three-way patch semantics (omitted / null / value)

### Claude's Discretion
- Exact file name and structure for consolidated warnings
- Whether RepetitionRuleSpec needs a write-side copy or can be restructured in-place
- Technical approach to making sentinel work with forbid (if any changes needed)
- Error message wording (within existing convention)

### Deferred Ideas (OUT OF SCOPE)
None
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| STRCT-01 | Write models reject unknown fields with clear errors (`extra="forbid"`) | `WriteModel` base class with `ConfigDict(extra="forbid")` -- verified working with Pydantic 2.12.5. Server error handler needs update to include field names from `loc`. |
| STRCT-02 | Read models remain permissive (`extra="ignore"`) | Read models inherit from `OmniFocusBaseModel` which has no `extra` setting (Pydantic default = ignore). No changes needed. |
| STRCT-03 | `_Unset` sentinel works correctly with `extra="forbid"` | Verified experimentally: `_Unset` sentinel defaults work perfectly with `extra="forbid"`. UNSET fields are not treated as "extra" because they are declared fields with defaults. No sentinel changes needed. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.12.5 | Model validation, `ConfigDict(extra="forbid")` | Already the project's model layer. `extra="forbid"` is a first-class config option. |

### Supporting
No additional libraries needed. This is purely a Pydantic configuration change.

## Architecture Patterns

### WriteModel Base Class

**What:** New base class in `write.py` that inherits from `OmniFocusBaseModel` and adds `extra="forbid"`.

**Key finding:** Pydantic v2 merges `ConfigDict` from parent to child. A child that only specifies `ConfigDict(extra="forbid")` automatically inherits `alias_generator`, `validate_by_name`, `validate_by_alias` from the parent. Verified experimentally.

```python
# In write.py -- this is all that's needed
class WriteModel(OmniFocusBaseModel):
    """Base model for write operations. Rejects unknown fields."""
    model_config = ConfigDict(extra="forbid")
```

**Models to re-parent** (change `OmniFocusBaseModel` to `WriteModel`):
- `TaskCreateSpec`
- `TaskEditSpec`
- `MoveToSpec`
- `TagActionSpec`
- `ActionsSpec`

**Models to leave on `OmniFocusBaseModel`** (permissive):
- `TaskCreateResult`
- `TaskEditResult`
- All read models (Task, Project, Tag, Folder, etc.)
- All common models (TagRef, ParentRef, RepetitionRule, ReviewInterval)

### RepetitionRuleSpec Decision

**Current state:** `RepetitionRule` in `common.py` is read-only. There is NO `RepetitionRuleSpec` in write.py. Write models do not currently reference `RepetitionRule` at all.

**Recommendation:** Do nothing for RepetitionRuleSpec in this phase. It does not exist yet as a write model. When repetition rule write support is added (v1.2.3 per the research), the write-side spec should be created inheriting from `WriteModel`. No restructuring of the read-side `RepetitionRule` is needed now.

**Confidence:** HIGH -- verified by grepping for `RepetitionRuleSpec` (does not exist) and `RepetitionRule` imports in write.py (none).

### Warning String Consolidation

**Current state:** 14 `warnings.append()` calls and 1 inline warning list in `service.py`. Warnings fall into these categories:

| Category | Count | Example |
|----------|-------|---------|
| Status warnings (editing completed/dropped task) | 1 | "This task is {status} -- your changes were applied..." |
| No-op detection | 2 | "No changes specified...", "No changes detected..." |
| Lifecycle no-ops | 2 | "Task is already {state_word}...", "Task was already {prior_state}..." |
| Lifecycle info | 2 | "Repeating task -- this occurrence completed...", "Repeating task -- this occurrence was skipped..." |
| Move warnings | 1 | "Task is already in this container..." |
| Tag no-ops | 5 | "Tags already match...", "Tag '{display}' is already on...", "Tag '{display}' is not on..." |

**Recommended structure:**

```python
# src/omnifocus_operator/warnings.py

# --- Edit: Status ---
EDIT_COMPLETED_TASK = (
    "This task is {status} -- your changes were applied, "
    "but please confirm with the user that they intended to edit a {status} task."
)

# --- Edit: No-op ---
EDIT_NO_CHANGES_SPECIFIED = (
    "No changes specified -- if you intended to change fields, "
    "include them in the request"
)
EDIT_NO_CHANGES_DETECTED = (
    "No changes detected -- the task already has these values. "
    "If you don't want to change a field, omit it from the request."
)

# ... etc
```

**Key design points:**
- Use f-string templates with `.format()` for parameterized warnings (status, field names, etc.)
- Group by domain (edit/lifecycle/tags/move)
- Constants are `UPPER_SNAKE_CASE`
- Some warnings are templates (contain `{status}`, `{display}`), others are literal strings

### Server Error Handler Improvement

**Current code** (server.py lines 211-215, 269-273):
```python
messages = "; ".join(e["msg"] for e in exc.errors() if "_Unset" not in e["msg"])
raise ValueError(messages or "Invalid input") from None
```

**Problem:** For `extra_forbidden` errors, `msg` is the generic "Extra inputs are not permitted" -- the field name is in `loc`, not `msg`. Current code loses field names.

**Recommended fix:**
```python
# For extra_forbidden errors, include the field name from loc
messages = []
for e in exc.errors():
    if "_Unset" in e["msg"]:
        continue
    if e["type"] == "extra_forbidden":
        field = ".".join(str(l) for l in e["loc"])
        messages.append(f"Unknown field '{field}'")
    else:
        messages.append(e["msg"])
raise ValueError("; ".join(messages) or "Invalid input") from None
```

This produces agent-friendly messages like: `"Unknown field 'bogusField'; Unknown field 'xyz'"` instead of `"Extra inputs are not permitted; Extra inputs are not permitted"`.

### model_rebuild() in __init__.py

The `models/__init__.py` calls `model_rebuild()` on all write models. After re-parenting to `WriteModel`, the same rebuild calls work unchanged -- `model_rebuild()` doesn't care about `extra` config.

### Test Impact

**Test that MUST change:** `tests/test_service.py::TestAddTask::test_unknown_fields_ignored` (line 417-433)
- Currently asserts unknown fields are silently ignored
- Must be updated to assert `ValidationError` is raised for unknown fields
- This is the ONLY existing test that asserts the old behavior

**New tests needed:**
- Write models reject unknown fields (TaskCreateSpec, TaskEditSpec, MoveToSpec, TagActionSpec, ActionsSpec)
- Read models still accept unknown fields
- `_Unset` defaults still work with `extra="forbid"`
- Server error handler includes field names in error message
- Warning constants match their usage in service.py (no stale constants)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Field rejection | Custom field validator | `ConfigDict(extra="forbid")` | Pydantic handles it natively with proper error types |
| Error field extraction | String parsing | `ValidationError.errors()` `loc` tuple | Structured access to field names is already in the error object |
| Config inheritance | Duplicate all ConfigDict keys | Single `extra="forbid"` addition | Pydantic merges ConfigDict automatically |

## Common Pitfalls

### Pitfall 1: Forgetting to re-parent sub-models
**What goes wrong:** If `MoveToSpec` stays on `OmniFocusBaseModel` but `TaskEditSpec` moves to `WriteModel`, unknown fields in nested `moveTo` JSON will be silently ignored.
**How to avoid:** All 5 write specs must be re-parented: TaskCreateSpec, TaskEditSpec, MoveToSpec, TagActionSpec, ActionsSpec.
**Warning signs:** Tests pass but nested unknown fields don't raise errors.

### Pitfall 2: Making result models strict
**What goes wrong:** `TaskCreateResult` and `TaskEditResult` with `extra="forbid"` would break if OmniFocus ever returns unexpected fields.
**How to avoid:** Result models stay on `OmniFocusBaseModel` (permissive). Only agent-input models get `WriteModel`.
**Rule:** If it accepts agent input, strict. If it's server output, permissive.

### Pitfall 3: Server error handler losing field names
**What goes wrong:** The `extra_forbidden` error type puts the field name in `loc`, not `msg`. The current handler joins only `msg` values, producing "Extra inputs are not permitted" without naming the offending field.
**How to avoid:** Check `e["type"] == "extra_forbidden"` and extract field name from `e["loc"]`.

### Pitfall 4: Warning template strings with .format() vs f-strings
**What goes wrong:** If warnings use f-strings at definition time, the variables aren't available. If they use `.format()`, missing keys cause `KeyError`.
**How to avoid:** Define templates as plain strings with `{placeholder}` syntax. Call `.format(key=value)` at the call site. Type-check that all format keys are provided.

### Pitfall 5: Breaking camelCase alias support
**What goes wrong:** Agents send `dueDate` (camelCase). If `extra="forbid"` doesn't recognize aliases, it rejects valid input.
**Verified safe:** Pydantic 2.12.5 with `validate_by_alias=True` correctly accepts both `dueDate` and `due_date` under `extra="forbid"`. Verified experimentally.

## Code Examples

### WriteModel base class (verified pattern)
```python
# Source: experimental verification against Pydantic 2.12.5
from pydantic import ConfigDict
from omnifocus_operator.models.base import OmniFocusBaseModel

class WriteModel(OmniFocusBaseModel):
    """Base for write models. Rejects unknown fields at validation time."""
    model_config = ConfigDict(extra="forbid")
```

### Re-parenting a write spec
```python
# Before:
class TaskCreateSpec(OmniFocusBaseModel):
    name: str
    ...

# After:
class TaskCreateSpec(WriteModel):
    name: str
    ...
```

### Improved error handler in server.py
```python
# Source: experimental verification of ValidationError structure
except ValidationError as exc:
    messages = []
    for e in exc.errors():
        if "_Unset" in e["msg"]:
            continue
        if e["type"] == "extra_forbidden":
            field = ".".join(str(l) for l in e["loc"])
            messages.append(f"Unknown field '{field}'")
        else:
            messages.append(e["msg"])
    raise ValueError("; ".join(messages) or "Invalid input") from None
```

### Warning constant pattern
```python
# Template warning (parameterized)
EDIT_COMPLETED_TASK = (
    "This task is {status} -- your changes were applied, "
    "but please confirm with the user that they intended to edit a {status} task."
)

# Usage:
warnings.append(EDIT_COMPLETED_TASK.format(status=status))

# Literal warning (no parameters)
EDIT_NO_CHANGES_SPECIFIED = (
    "No changes specified -- if you intended to change fields, "
    "include them in the request"
)

# Usage:
warnings.append(EDIT_NO_CHANGES_SPECIFIED)
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x + pytest-asyncio 1.3.x |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run python -m pytest tests/test_models.py tests/test_service.py -x -q --no-header --tb=short` |
| Full suite command | `uv run python -m pytest` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STRCT-01 | Write models reject unknown fields | unit | `uv run python -m pytest tests/test_models.py -x -q -k "extra_forbid or unknown_field"` | Partially (test_unknown_fields_ignored exists but asserts OLD behavior) |
| STRCT-02 | Read models remain permissive | unit | `uv run python -m pytest tests/test_models.py -x -q -k "read_model_permissive"` | No (new test) |
| STRCT-03 | _Unset sentinel works with extra=forbid | unit | `uv run python -m pytest tests/test_models.py -x -q -k "unset_with_forbid"` | No (new test) |

### Sampling Rate
- **Per task commit:** `uv run python -m pytest tests/test_models.py tests/test_service.py -x -q --no-header --tb=short`
- **Per wave merge:** `uv run python -m pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] Update `tests/test_service.py::TestAddTask::test_unknown_fields_ignored` to assert ValidationError instead of silent ignore
- [ ] New tests for all 5 write models rejecting unknown fields
- [ ] New test for read models remaining permissive
- [ ] New test for _Unset sentinel round-trip with extra=forbid
- [ ] New test for server error handler including field names

## Sources

### Primary (HIGH confidence)
- Pydantic 2.12.5 (project's installed version) -- experimental verification of `extra="forbid"`, `ConfigDict` inheritance, `_Unset` sentinel compatibility, alias handling
- Project source code -- `models/base.py`, `models/write.py`, `models/common.py`, `service.py`, `server.py`, `models/__init__.py`

### Secondary (MEDIUM confidence)
- Pydantic docs on `ConfigDict(extra="forbid")` -- well-documented stable feature since Pydantic v2.0

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- single library (Pydantic), already in use, feature verified experimentally
- Architecture: HIGH -- `ConfigDict` inheritance verified, `_Unset` compatibility verified, all edge cases tested
- Pitfalls: HIGH -- each pitfall verified against actual code and Pydantic behavior

**Research date:** 2026-03-16
**Valid until:** 2026-04-16 (stable Pydantic feature, no expected changes)
