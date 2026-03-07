---
phase: quick-2
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  # Collapsed packages (delete dirs, create modules)
  - src/omnifocus_operator/server.py
  - src/omnifocus_operator/service.py
  - src/omnifocus_operator/repository.py
  # Renamed files in models/
  - src/omnifocus_operator/models/__init__.py
  - src/omnifocus_operator/models/base.py
  - src/omnifocus_operator/models/common.py
  - src/omnifocus_operator/models/enums.py
  - src/omnifocus_operator/models/snapshot.py
  - src/omnifocus_operator/models/folder.py
  - src/omnifocus_operator/models/perspective.py
  - src/omnifocus_operator/models/project.py
  - src/omnifocus_operator/models/tag.py
  - src/omnifocus_operator/models/task.py
  # Renamed files in bridge/
  - src/omnifocus_operator/bridge/__init__.py
  - src/omnifocus_operator/bridge/protocol.py
  - src/omnifocus_operator/bridge/errors.py
  - src/omnifocus_operator/bridge/factory.py
  - src/omnifocus_operator/bridge/in_memory.py
  - src/omnifocus_operator/bridge/simulator.py
  - src/omnifocus_operator/bridge/real.py
  # Renamed files in simulator/
  - src/omnifocus_operator/simulator/__main__.py
  - src/omnifocus_operator/simulator/data.py
autonomous: true
must_haves:
  truths:
    - "All existing tests pass without modification"
    - "External import paths unchanged (e.g. from omnifocus_operator.server import create_server)"
    - "No files with _ prefix remain (except __init__.py, __main__.py)"
    - "server/, service/, repository/ directories replaced by single .py modules"
  artifacts:
    - path: "src/omnifocus_operator/server.py"
      provides: "Collapsed server module"
    - path: "src/omnifocus_operator/service.py"
      provides: "Collapsed service module"
    - path: "src/omnifocus_operator/repository.py"
      provides: "Collapsed repository module"
    - path: "src/omnifocus_operator/models/base.py"
      provides: "Renamed from _base.py"
    - path: "src/omnifocus_operator/bridge/protocol.py"
      provides: "Renamed from _protocol.py"
  key_links:
    - from: "all src files"
      to: "internal imports"
      via: "from omnifocus_operator.{pkg}.{module}"
      pattern: "from omnifocus_operator\\."
---

<objective>
Simplify file layout by dropping _ prefixes on internal modules and collapsing single-file packages into plain modules.

Purpose: Reduce 29 files to 23, eliminate unnecessary _ prefix convention, improve fuzzy-finding and navigation.
Output: Cleaned-up src/omnifocus_operator/ with no behavioral changes.
</objective>

<execution_context>
@/Users/flo/.claude/get-shit-done/workflows/execute-plan.md
@/Users/flo/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/todos/pending/2026-03-02-review-package-structure-and-underscore-convention.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Drop _ prefixes on all internal modules</name>
  <files>
    src/omnifocus_operator/models/base.py
    src/omnifocus_operator/models/common.py
    src/omnifocus_operator/models/enums.py
    src/omnifocus_operator/models/snapshot.py
    src/omnifocus_operator/models/folder.py
    src/omnifocus_operator/models/perspective.py
    src/omnifocus_operator/models/project.py
    src/omnifocus_operator/models/tag.py
    src/omnifocus_operator/models/task.py
    src/omnifocus_operator/models/__init__.py
    src/omnifocus_operator/bridge/protocol.py
    src/omnifocus_operator/bridge/errors.py
    src/omnifocus_operator/bridge/factory.py
    src/omnifocus_operator/bridge/in_memory.py
    src/omnifocus_operator/bridge/simulator.py
    src/omnifocus_operator/bridge/real.py
    src/omnifocus_operator/bridge/__init__.py
    src/omnifocus_operator/simulator/data.py
    src/omnifocus_operator/simulator/__main__.py
  </files>
  <action>
    Use `git mv` to rename all _-prefixed files to drop the prefix:

    **models/ package** (9 renames):
    - `_base.py` -> `base.py`, `_common.py` -> `common.py`, `_enums.py` -> `enums.py`
    - `_snapshot.py` -> `snapshot.py`, `_folder.py` -> `folder.py`, `_perspective.py` -> `perspective.py`
    - `_project.py` -> `project.py`, `_tag.py` -> `tag.py`, `_task.py` -> `task.py`

    **bridge/ package** (6 renames):
    - `_protocol.py` -> `protocol.py`, `_errors.py` -> `errors.py`, `_factory.py` -> `factory.py`
    - `_in_memory.py` -> `in_memory.py`, `_simulator.py` -> `simulator.py`, `_real.py` -> `real.py`

    **simulator/ package** (1 rename):
    - `_data.py` -> `data.py`

    Then update ALL internal imports in these files AND their `__init__.py` files. Every occurrence of `omnifocus_operator.models._base` becomes `omnifocus_operator.models.base`, etc. The pattern is mechanical: strip the `._` to `.` in the module name portion of every import path.

    Specific import updates needed (exhaustive list):
    - `models/__init__.py`: 8 import lines referencing `._base`, `._common`, `._enums`, `._folder`, `._perspective`, `._project`, `._snapshot`, `._tag`, `._task`
    - `models/base.py` (was _base.py): TYPE_CHECKING import of `._common` -> `.common`
    - `models/common.py` (was _common.py): import of `._base` -> `.base`, TYPE_CHECKING of `._enums` -> `.enums`
    - `models/folder.py`: `._base` -> `.base`, TYPE_CHECKING `._enums` -> `.enums`
    - `models/perspective.py`: `._base` -> `.base`
    - `models/project.py`: `._base` -> `.base`, TYPE_CHECKING `._common` -> `.common`, `._enums` -> `.enums`
    - `models/snapshot.py`: `._base` -> `.base`, TYPE_CHECKING `._folder` -> `.folder`, `._perspective` -> `.perspective`, `._project` -> `.project`, `._tag` -> `.tag`, `._task` -> `.task`
    - `models/tag.py`: `._base` -> `.base`, TYPE_CHECKING `._enums` -> `.enums`
    - `models/task.py`: `._base` -> `.base`, TYPE_CHECKING `._enums` -> `.enums`
    - `bridge/__init__.py`: 5 import lines referencing `._errors`, `._factory`, `._in_memory`, `._protocol`, `._real`, `._simulator`
    - `bridge/factory.py`: `._in_memory` -> `.in_memory`, `._protocol` -> `.protocol`, `._real` -> `.real`, `._simulator` -> `.simulator`
    - `bridge/real.py`: `._errors` -> `.errors`
    - `bridge/simulator.py`: `._real` -> `.real`
    - `simulator/__main__.py`: `._data` -> `.data`

    Do NOT touch any imports that use the package-level path (e.g. `from omnifocus_operator.bridge import ...`) -- those are already correct and don't reference underscore modules.
  </action>
  <verify>
    <automated>cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && python -c "from omnifocus_operator.models import Task, Project, Tag, Folder, Perspective, DatabaseSnapshot; from omnifocus_operator.bridge import Bridge, InMemoryBridge, RealBridge, SimulatorBridge, create_bridge; print('All imports OK')" && ! find src/omnifocus_operator -name "_*.py" ! -name "__*" | grep -q . && echo "No underscore files remain"</automated>
  </verify>
  <done>All 16 files renamed (no _ prefix), all internal imports updated, no _-prefixed files remain (excluding __init__.py/__main__.py)</done>
</task>

<task type="auto">
  <name>Task 2: Collapse single-file packages into modules</name>
  <files>
    src/omnifocus_operator/server.py
    src/omnifocus_operator/service.py
    src/omnifocus_operator/repository.py
  </files>
  <action>
    Collapse three single-file packages into plain modules. For each:

    **server/ -> server.py:**
    1. Read `server/_server.py` content (the actual implementation, ~100 lines)
    2. The `__init__.py` just re-exports `create_server` -- that re-export is unnecessary when it's a module
    3. Create `server.py` at package level with the content of `_server.py`. Keep its docstring but update it to match the `__init__.py` module docstring style. Add `__all__ = ["create_server"]` at module level.
    4. Delete `server/` directory entirely (both `__init__.py` and `_server.py`)

    **service/ -> service.py:**
    1. Read `service/_service.py` content (~50 lines)
    2. Create `service.py` at package level with that content. Add `__all__ = ["ErrorOperatorService", "OperatorService"]`.
    3. Delete `service/` directory entirely

    **repository/ -> repository.py:**
    1. Read both `repository/_mtime.py` and `repository/_repository.py`
    2. Create `repository.py` at package level combining both files: mtime classes first (MtimeSource protocol, FileMtimeSource, ConstantMtimeSource), then OmniFocusRepository. Merge imports (deduplicate). Add `__all__ = ["ConstantMtimeSource", "FileMtimeSource", "MtimeSource", "OmniFocusRepository"]`.
    3. Delete `repository/` directory entirely

    **Import updates in collapsed files:**
    - `server.py`: Update any internal imports that referenced `omnifocus_operator.repository._mtime` or `omnifocus_operator.repository._repository` to just `omnifocus_operator.repository` (these are now in the same module).
    - `service.py`: Update `omnifocus_operator.models._snapshot` -> `omnifocus_operator.models.snapshot`, `omnifocus_operator.repository._repository` -> `omnifocus_operator.repository`
    - `repository.py`: Internal references between _mtime and _repository are now in the same file -- remove cross-imports, use direct references. Update `omnifocus_operator.models._snapshot` -> `omnifocus_operator.models.snapshot`, `omnifocus_operator.bridge._protocol` -> `omnifocus_operator.bridge.protocol`.

    **Import updates in OTHER files that referenced underscore submodules:**
    - `server.py` (the new collapsed one) has a lazy import of `omnifocus_operator.bridge._real` -> change to `omnifocus_operator.bridge.real`

    **Critical:** External import paths like `from omnifocus_operator.server import create_server` continue to work because Python resolves `omnifocus_operator.server` to the module file `server.py` the same way it resolved the package `server/__init__.py`.

    Use `git rm -r` for directory cleanup to preserve git history awareness.
  </action>
  <verify>
    <automated>cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && python -c "from omnifocus_operator.server import create_server; from omnifocus_operator.service import OperatorService, ErrorOperatorService; from omnifocus_operator.repository import OmniFocusRepository, FileMtimeSource, ConstantMtimeSource, MtimeSource; print('All collapsed imports OK')" && ! test -d src/omnifocus_operator/server && ! test -d src/omnifocus_operator/service && ! test -d src/omnifocus_operator/repository && echo "All directories removed"</automated>
  </verify>
  <done>server/, service/, repository/ directories replaced by server.py, service.py, repository.py. All exports preserved. No directory remains.</done>
</task>

<task type="auto">
  <name>Task 3: Run full test suite and verify clean state</name>
  <files></files>
  <action>
    Run the full test suite to confirm zero regressions. Also run mypy and ruff to ensure type checking and linting pass. If any test fails, diagnose and fix the import issue (it will be a missed import update).

    Commands:
    1. `uv run pytest` -- all tests must pass
    2. `uv run mypy src/` -- type checking must pass
    3. `uv run ruff check src/` -- linting must pass

    Fix any failures. Failures will be missed import updates -- the fix is always mechanical (update the import path).

    Note: Do NOT modify test files. If a test file has an import like `from omnifocus_operator.models._base import ...`, that import goes through the package's `__init__.py` or the now-renamed module. Since we kept `__init__.py` re-exports for models/ and bridge/, and external paths are unchanged, tests should not need changes. If a test directly imports an underscore path, flag it but do not modify -- the constraint says no test file changes.
  </action>
  <verify>
    <automated>cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && uv run pytest -x -q 2>&1 | tail -5</automated>
  </verify>
  <done>Full test suite passes green, mypy clean, ruff clean. File count reduced from 29 to 23.</done>
</task>

</tasks>

<verification>
- `find src/omnifocus_operator -name "_*.py" ! -name "__*"` returns nothing
- `test -d src/omnifocus_operator/server` is false (collapsed)
- `test -d src/omnifocus_operator/service` is false (collapsed)
- `test -d src/omnifocus_operator/repository` is false (collapsed)
- `uv run pytest` passes all tests
- `from omnifocus_operator.server import create_server` works
- `from omnifocus_operator.models import Task` works
- `from omnifocus_operator.bridge import Bridge` works
</verification>

<success_criteria>
- 29 source files reduced to 23
- No _-prefixed files remain (excluding __init__.py, __main__.py)
- server/, service/, repository/ are plain .py modules, not directories
- All tests pass without modification
- All external import paths unchanged
</success_criteria>

<output>
After completion, create `.planning/quick/2-simplify-file-layout-drop-prefixes-colla/2-SUMMARY.md`
</output>
