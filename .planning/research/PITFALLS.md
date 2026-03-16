# Domain Pitfalls

**Domain:** Service layer refactoring, write pipeline unification, Pydantic model reorganization in an existing MCP server with 534 tests
**Researched:** 2026-03-16
**Confidence:** HIGH (codebase analysis + Pydantic v2 docs + known GitHub issues)

## Critical Pitfalls

### Pitfall 1: `extra="forbid"` on WriteModel Base Rejects the `_Unset` Sentinel

**What goes wrong:**
Adding `extra="forbid"` to write models causes Pydantic to reject the `_Unset` sentinel as an "extra" field type in union-typed fields. The current `_Unset` class uses `is_instance_schema` in its core schema -- Pydantic treats `_Unset` in a `str | None | _Unset` union as a valid branch, but if `extra="forbid"` is set on a *parent class* that doesn't know about `_Unset`, config inheritance can produce unexpected validation errors.

**Why it happens:**
Pydantic v2 merges `model_config` from parent to child. If `WriteModel(OmniFocusBaseModel)` sets `extra="forbid"`, ALL write models inherit it -- including `TaskEditSpec` whose fields default to `UNSET`. The interaction between `extra="forbid"` and custom sentinel types in union annotations is not well-tested in Pydantic v2. Known issues: [pydantic#9768](https://github.com/pydantic/pydantic/issues/9768), [pydantic#9992](https://github.com/pydantic/pydantic/issues/9992).

**Consequences:**
- `TaskEditSpec.model_validate({"id": "abc"})` may reject valid input
- All 180+ edit_task tests break simultaneously
- Subtle: may work in unit tests but fail when MCP server deserializes JSON (different validation path)

**Prevention:**
- Add `extra="forbid"` ONLY to `TaskCreateSpec` and `TaskEditSpec` directly, NOT to a shared base class
- Write a focused test: construct every write model with `extra="forbid"` + UNSET defaults + one extra field, verify the extra field is rejected and UNSET defaults pass
- Test both `model_validate(dict)` and `model_validate_json(json_string)` paths -- they can differ
- Do NOT add `extra="forbid"` to `ActionsSpec`, `MoveToSpec`, or `TagActionSpec` via inheritance -- set it per-class if needed

**Detection:**
- ValidationError mentioning `extra_forbidden` in write model tests
- Tests pass locally but MCP tool calls fail (JSON vs dict validation difference)

**Phase to address:** First task in milestone -- validate the `extra="forbid"` + sentinel interaction before any other refactoring

---

### Pitfall 2: `model_rebuild()` Ordering Breaks When Models Move Between Modules

**What goes wrong:**
`models/__init__.py` has a carefully ordered `model_rebuild()` call sequence with a shared `_types_namespace`. Moving write models to a submodule or splitting the models package disrupts this ordering, causing `PydanticUndefinedAnnotation` at import time.

**Why it happens:**
The current `__init__.py` rebuilds 15 models in dependency order: `ParentRef` -> `RepetitionRule` -> `ActionableEntity` -> ... -> `TaskEditSpec` -> `MoveToSpec`. This works because all types are imported into one namespace before any rebuild. If write models move to `models/write/validation.py` or similar, the import order changes and `_types_namespace` may be incomplete when `model_rebuild()` runs.

**Consequences:**
- `ImportError` / `PydanticUndefinedAnnotation` on server startup
- All 534 tests fail simultaneously (import-time crash)
- Error messages are cryptic: "type 'AwareDatetime' is not defined" even though it's imported

**Prevention:**
- Keep ALL `model_rebuild()` calls in `models/__init__.py` regardless of where model classes live
- If extracting service submodules, they should import from `models` (the package), not from individual model files
- Test: `python -c "from omnifocus_operator.models import TaskEditSpec"` must work in isolation
- Do NOT move `model_rebuild()` into submodules -- centralize it

**Detection:**
- `ImportError` when running any test
- "not fully defined" Pydantic errors at import time
- Works in IDE (lazy loading) but fails in pytest (eager import)

**Phase to address:** Any task that reorganizes model files or import paths

---

### Pitfall 3: Circular Imports When Extracting Validation/Domain Logic from Service

**What goes wrong:**
Extracting validation logic into `service/validation.py` creates a circular import: `validation.py` needs write models, write models need base models, service needs validation, and the extracted module needs to call back into service for `_resolve_parent()` or `_resolve_tags()`.

**Why it happens:**
The current `service.py` is a monolith that freely calls its own private methods. Extraction creates cross-module dependencies. The resolution methods (`_resolve_parent`, `_resolve_tags`) need the repository, which the validator doesn't own. Python's import system fails on circular imports at module-body scope (works with function-scope imports but that's a code smell).

**Consequences:**
- `ImportError: cannot import name 'X' from partially initialized module`
- Temptation to use function-level imports everywhere (hides the dependency problem)
- Over-decomposition: 5 tiny modules all importing each other defeats the purpose

**Prevention:**
- **Dependency direction rule:** `service.py` (orchestrator) imports from extracted modules, never the reverse
- Extracted modules should be *pure functions* or *stateless classes* that receive their dependencies as arguments:
  ```python
  # Good: validation takes data, returns result
  def validate_edit_spec(spec: TaskEditSpec, current_task: Task) -> list[str]:

  # Bad: validation calls back into service
  class EditValidator:
      def __init__(self, service: OperatorService):  # circular
  ```
- The service stays the orchestrator: it calls `validate()`, then `resolve()`, then `convert()`, then `delegate()`
- Use `TYPE_CHECKING` imports for type annotations in extracted modules, runtime imports only for actual values

**Detection:**
- `ImportError` at startup
- Needing to add `from __future__ import annotations` to fix a circular import (symptom, not cure)
- An extracted module that imports `OperatorService`

**Phase to address:** Service decomposition task -- establish dependency direction before writing code

---

### Pitfall 4: InMemoryBridge Removal Breaks 100+ Test Imports

**What goes wrong:**
Removing `InMemoryBridge` from `bridge/__init__.py` exports causes `ImportError` in every test file that does `from omnifocus_operator.bridge import InMemoryBridge`. The test suite goes from 534 passing to 100+ import errors.

**Why it happens:**
`InMemoryBridge` is exported from `bridge/__init__.py` and used extensively in tests via this public path. The plan to "remove from public surface" and "update test imports to use direct module paths" sounds simple but affects:
- `tests/test_service.py` (line 19: `from omnifocus_operator.bridge import ... InMemoryBridge`)
- `tests/test_bridge.py`
- `tests/test_simulator_bridge.py`
- `tests/test_repository_factory.py`
- `tests/conftest.py` (if any fixtures use it)
- Any other test importing from `omnifocus_operator.bridge`

**Consequences:**
- Mass import failure if done in one step
- If moved to `tests/` directory, the module path changes entirely
- CI fails on every test, blocking all other work

**Prevention:**
- **Two-commit approach:**
  1. First commit: Update ALL test imports from `from omnifocus_operator.bridge import InMemoryBridge` to `from omnifocus_operator.bridge.in_memory import InMemoryBridge`. Run full test suite. Commit.
  2. Second commit: Remove from `bridge/__init__.py` exports. Remove factory branch. Run full test suite. Commit.
- Do NOT combine with the physical file move (`src/` -> `tests/`). That's a third step.
- Use `grep -r "InMemoryBridge" tests/` to find every import before starting
- Keep the file at `bridge/in_memory.py` (don't move to tests/) -- it's fine in src/ as an internal module, just not re-exported

**Detection:**
- Mass `ImportError` when running tests after export removal
- CI red on every test file

**Phase to address:** Dedicated task, done independently from other changes

---

## Moderate Pitfalls

### Pitfall 5: Write Interface Unification Silently Changes Payload Shape

**What goes wrong:**
Unifying the service-repository write interface changes who builds the bridge payload. Currently `edit_task` service builds a `dict[str, Any]` and repository passes it through. If refactored so repository does the serialization (like `add_task`), subtle key differences break the bridge: `estimatedMinutes` vs `estimated_minutes`, `dueDate` vs `due_date`.

**Why it happens:**
`add_task` uses `spec.model_dump(by_alias=True)` (produces camelCase). `edit_task` builds the dict field-by-field with hardcoded camelCase keys. Unification means picking one approach and using it everywhere, but the two paths handle edge cases differently:
- `add_task`: `exclude_none=True` drops None fields
- `edit_task`: `None` means "clear the field" (intentionally included)
- Date fields: `add_task` serializes via Pydantic's JSON mode, `edit_task` calls `.isoformat()` manually

**Prevention:**
- Write a bridge payload contract test: given the same input, both paths must produce identical bridge payloads
- Enumerate the differences before coding: `exclude_none` behavior, date serialization format, key naming, `tags` -> `tagIds` swap
- The test should assert on the exact dict passed to `bridge.send_command()`
- Keep the InMemoryBridge call-tracking (`bridge.calls`) to verify payloads in tests

**Detection:**
- UAT: task created/edited but fields wrong (dates shifted, fields missing)
- Bridge.js errors about unexpected keys

### Pitfall 6: Over-Decomposing the Service Layer

**What goes wrong:**
Service gets split into 6+ modules (`validation.py`, `domain.py`, `conversion.py`, `resolution.py`, `lifecycle.py`, `tags.py`). Each is 30-50 lines. Reading a single write flow requires opening 5 files. New contributors can't follow the code path.

**Why it happens:**
Refactoring enthusiasm. Each "concern" looks like it deserves its own file. But the entire `edit_task` method is ~100 lines of linear orchestration -- extracting each step into its own module adds indirection without proportional benefit.

**Prevention:**
- **Rule of thumb:** Extract when a module has >1 consumer or >100 lines of self-contained logic
- The milestone spec says "validation, domain logic, format conversion" -- that's 3 modules maximum plus the orchestrator
- Start with extracting format conversion (purely mechanical, no dependencies on service state) and see if the service is readable before extracting more
- If an extracted function is called from exactly one place and is <20 lines, inline it

**Detection:**
- Service method becomes: `validate(); resolve(); convert(); delegate()` -- four one-liners calling other modules
- A file with fewer than 3 functions
- Import list at the top of `service.py` is longer than the method bodies

### Pitfall 7: Test Fragility from Overly Specific Assertions After Refactoring

**What goes wrong:**
After refactoring, tests that assert on internal implementation details (method call order, specific dict keys in payload, exact warning messages) break even though behavior is unchanged. Developer spends more time fixing tests than refactoring code.

**Why it happens:**
Current tests are well-written (test behavior via InMemoryRepository) but some tests in `test_service.py` check specific warning message strings, payload dict shapes, and call patterns. These are correct now but become fragile when the internal structure changes.

**Prevention:**
- Before refactoring, identify which tests assert on behavior (keep) vs implementation (may need updating)
- Behavioral tests: "edit_task with unknown task raises ValueError" -- survives any refactoring
- Implementation tests: "payload dict has key 'estimatedMinutes'" -- breaks if serialization moves
- For payload tests, consider testing at the bridge boundary (what did `bridge.send_command` receive?) rather than at intermediate points
- Run the full test suite after each atomic change, not just at the end

**Detection:**
- Tests fail with "expected 'estimatedMinutes' in payload" after moving serialization to a different layer
- Warning message tests fail after rewording

### Pitfall 8: `_Unset` Sentinel Serialization Leaks into Bridge Payloads

**What goes wrong:**
During write interface unification, using `model_dump()` on `TaskEditSpec` includes UNSET sentinel values in the serialized output. These get sent to the bridge as `{"name": <_Unset instance>}`, which bridge.js can't deserialize.

**Why it happens:**
`TaskEditSpec` has fields defaulting to `UNSET`. Pydantic's `model_dump()` includes them by default. The current code avoids this by building the payload field-by-field with `isinstance(value, _Unset)` checks. If the unification replaces this with `model_dump()`, UNSET values leak through.

**Prevention:**
- If using `model_dump()`, add a custom serializer or post-processing step that strips UNSET values
- Or: use `model_dump(exclude_unset=True)` -- but verify this actually excludes fields with UNSET *defaults* (Pydantic's "unset" means "not provided during validation," not "has sentinel default")
- Better: keep the explicit field-by-field approach for edit models. `model_dump()` works for create models (no sentinels)
- Test: serialize a TaskEditSpec with only `id` set, verify the payload contains exactly `{"id": "..."}` and nothing else

**Detection:**
- Bridge.js errors about unexpected field types
- JSON serialization errors: "Object of type _Unset is not JSON serializable"

### Pitfall 9: `@_ensures_write_through` Decorator Signature Lost During Refactoring

**What goes wrong:**
Moving or wrapping `_ensures_write_through` during repository refactoring breaks its `functools.wraps` behavior or the `self._db_path` attribute access. The decorator silently stops waiting for SQLite confirmation, and read-after-write tests pass by coincidence (InMemoryRepository doesn't use the decorator).

**Why it happens:**
The decorator uses Python 3.12's `[F: Callable[..., Any]]` syntax and accesses `self._db_path` on the decorated method's instance. If the method moves to a different class or the decorator is applied to a method whose `self` doesn't have `_db_path`, it fails silently or raises AttributeError. Since InMemoryRepository doesn't use the decorator, all unit tests pass -- only UAT catches the break.

**Prevention:**
- Do NOT move the decorator between classes without verifying `self._db_path` availability
- Add a type annotation or runtime check: `assert hasattr(self, '_db_path')` in the wrapper
- If unifying the write interface changes where `add_task`/`edit_task` live, verify the decorator still applies correctly
- The decorator is load-bearing for consistency -- treat it as a safety boundary, not refactoring target

**Detection:**
- UAT: write then immediate read returns stale data
- No unit test catches this because InMemoryRepository bypasses the decorator

## Minor Pitfalls

### Pitfall 10: Alias Generator Mismatch When Extracting Format Conversion

**What goes wrong:**
Extracted format conversion module hardcodes camelCase keys (e.g., `"estimatedMinutes"`) instead of using Pydantic's `to_camel` alias generator. If a field name changes or a new field is added, the hardcoded mapping and the Pydantic alias diverge.

**Prevention:**
- Use `model_dump(by_alias=True)` where possible instead of manual key mapping
- For edit payloads where manual construction is necessary, derive the camelCase key from the model field's alias: `TaskEditSpec.model_fields["estimated_minutes"].alias`
- Or maintain a single mapping dict that both the format converter and tests reference

### Pitfall 11: `model_json_schema` Overrides on Write Models Break After Reorganization

**What goes wrong:**
Every write model has a `model_json_schema` override that strips `_Unset` from the JSON schema. If models are reorganized and a new write model forgets this override, MCP tool descriptions expose `_Unset` as a valid type to agents.

**Prevention:**
- If creating a `WriteModel` base, include the `model_json_schema` override there
- Add a parametrized test: for every write model class, call `model_json_schema()` and assert `_Unset` doesn't appear
- Consider a `__init_subclass__` hook that auto-applies the override

### Pitfall 12: Repository Protocol Out of Sync After Write Interface Changes

**What goes wrong:**
`Repository` protocol defines `edit_task(self, payload: dict[str, Any]) -> dict[str, Any]`. If the unification changes this signature (e.g., to accept `TaskEditSpec`), `InMemoryRepository` and `HybridRepository` must update simultaneously. Missing one causes `TypeError` at runtime, not at import time (structural typing doesn't catch signature mismatches until the method is called).

**Prevention:**
- Update all 3 implementations (`InMemoryRepository`, `BridgeRepository` via `HybridRepository`, and the protocol) in the same commit
- Add a `isinstance(repo, Repository)` assertion in conftest.py or a dedicated test to catch protocol violations eagerly
- `mypy --strict` catches protocol mismatches if running -- verify it's in CI

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| `extra="forbid"` on write models | Sentinel interaction (#1) | Test UNSET + forbid together before applying broadly |
| Service decomposition | Circular imports (#3), over-decomposition (#6) | Establish dependency direction; extract max 3 modules |
| Write interface unification | Payload shape change (#5), UNSET serialization leak (#8) | Bridge payload contract tests; keep explicit field-by-field for edits |
| InMemoryBridge removal | Mass import breakage (#4) | Two-step: update imports first, remove exports second |
| Model file reorganization | model_rebuild ordering (#2), schema override loss (#11) | Keep model_rebuild centralized; test JSON schema output |
| Repository protocol changes | Silent signature mismatch (#12) | Update all implementations + protocol in one commit |
| Decorator handling | Write-through decorator break (#9) | Do not move decorator; verify self._db_path in UAT |

## Recommended Ordering

Based on pitfall dependencies:

1. **`extra="forbid"`** -- smallest scope, validates Pydantic interaction, informs all other changes
2. **InMemoryBridge cleanup** -- independent, reduces noise in later diffs
3. **Write interface unification** -- core refactoring, must happen before service decomposition (cleaner interface to decompose around)
4. **Service decomposition** -- depends on unified interface; extract format conversion first, then validation

## Sources

- [Pydantic v2 extra config inheritance issue #9768](https://github.com/pydantic/pydantic/issues/9768) -- config merging behavior in multiple inheritance
- [Pydantic model_config MRO issue #9992](https://github.com/pydantic/pydantic/issues/9992) -- config doesn't respect MRO
- [Pydantic sentinel serialization discussion #9943](https://github.com/pydantic/pydantic/discussions/9943) -- custom sentinel serialization failures
- [Pydantic model_rebuild issue #7618](https://github.com/pydantic/pydantic/issues/7618) -- model_rebuild failure with forward references
- [Pydantic forward annotations docs](https://docs.pydantic.dev/latest/concepts/forward_annotations/) -- model_rebuild and TYPE_CHECKING patterns
- [Pydantic v2.12 MISSING sentinel](https://pydantic.dev/articles/pydantic-v2-12-release) -- official sentinel alternative (experimental)
- [Circular imports in Python architecture](https://dev.to/vivekjami/circular-imports-in-python-the-architecture-killer-that-breaks-production-539j) -- dependency direction patterns
- [functools.wraps signature preservation](https://hynek.me/articles/decorators/) -- decorator pitfalls with type signatures
- Codebase analysis: `service.py` (637 lines), `models/write.py` (318 lines), `models/__init__.py` (115 lines with 15 model_rebuild calls), `repository/protocol.py`, `bridge/__init__.py` exports, `tests/test_service.py` (2000+ lines)

---
*Pitfalls research for: v1.2.1 Architectural Cleanup*
*Researched: 2026-03-16*
