---
created: 2026-03-30T11:01:13.131Z
title: Reorganize test suite into unit/integration/golden-master folders
area: testing
files:
  - tests/test_hybrid_repository.py
  - tests/test_service.py
  - tests/test_server.py
  - tests/conftest.py
  - CLAUDE.md
---

## Problem

The test suite is a flat directory of 27 files. The largest file (`test_hybrid_repository.py`, 2754 lines) is painful for agents — they have to read the whole thing to find the relevant section. There's no structural separation between fast unit tests and slower integration tests, so you can't easily run just the fast ones during development.

## Solution

### 1. Create three top-level test folders

```
tests/
├── conftest.py                          # shared factories (make_task_dict, etc.)
├── doubles/                             # stays here, shared across all types
├── unit/
│   ├── conftest.py                      # docstring: "Unit tests — fast, deterministic, no external dependencies."
│   ├── repository/
│   │   ├── conftest.py                  # hybrid_db, hybrid_repo fixtures + helpers (create_test_db, _minimal_task, etc.)
│   │   ├── test_hybrid_read_fields.py
│   │   ├── test_hybrid_list.py
│   │   ├── test_hybrid_writes.py
│   │   ├── test_hybrid_freshness.py
│   │   ├── test_hybrid_encoding.py
│   │   ├── test_hybrid_protocol.py
│   │   ├── test_bridge.py
│   │   ├── test_bridge_repository.py    # was test_repository.py
│   │   ├── test_query_builder.py
│   │   └── test_factory.py              # was test_repository_factory.py
│   ├── service/
│   │   ├── conftest.py
│   │   ├── test_add_task.py             # split from test_service.py
│   │   ├── test_edit_task.py            # split from test_service.py
│   │   ├── test_domain.py              # was test_service_domain.py
│   │   ├── test_payload.py             # was test_service_payload.py
│   │   ├── test_resolve.py             # was test_service_resolve.py
│   │   └── test_validation.py          # was test_validation_repetition.py
│   ├── bridge/
│   │   ├── test_adapter.py
│   │   ├── test_ipc_engine.py
│   │   └── test_stateful_bridge.py
│   ├── models/
│   │   ├── test_models.py
│   │   ├── test_contracts_repetition_rule.py
│   │   ├── test_contracts_type_aliases.py
│   │   └── test_list_contracts.py
│   ├── rrule/
│   │   ├── test_rrule.py
│   │   └── test_schedule_inverse.py
│   ├── test_middleware.py
│   └── test_warnings.py
├── integration/
│   ├── conftest.py                      # server/client fixture chain; docstring: "Integration tests — full stack, cross-layer."
│   ├── test_server.py
│   ├── test_output_schema.py
│   ├── test_smoke.py
│   └── test_simulator.py               # was test_simulator_integration.py
└── golden_master/                       # already exists, gains test_bridge_contract.py
    ├── test_bridge_contract.py          # moved from tests/ root
    ├── normalize.py
    ├── snapshots/
    └── README.md
```

### 2. Classification rule

- **Unit** — fast, deterministic, no real external dependencies. SQLite in `tmp_path` is fine (it's a controlled fixture, not a real external dependency). Mirrors source package hierarchy under `src/omnifocus_operator/`.
- **Integration** — spins up real infrastructure that could fail for environmental reasons. FastMCP server/client lifecycle, simulator processes, cross-layer schema validation.
- **Golden master** — replays operations against InMemoryBridge, compared to snapshots captured from real OmniFocus by a human.

### 3. Split large files

**`test_hybrid_repository.py` (2754 lines) → 6 files under `unit/repository/`:**

| New file | Classes to move |
|---|---|
| `test_hybrid_protocol.py` | TestProtocol, TestReadAllEntities, TestConnectionSemantics |
| `test_hybrid_read_fields.py` | TestTaskBasicFields, TestTaskTimestamps, TestTaskStatus, TestTaskTags, TestTaskRepetition, TestTaskNotes, TestTaskRelationships, TestProjectFields, TestTagFields, TestFolderFields, TestPerspective |
| `test_hybrid_list.py` | TestListTasksBasic, TestListProjectsBasic, TestListTasks, TestListProjects, TestListTags, TestListFolders, TestListPerspectives, TestListPerformance |
| `test_hybrid_writes.py` | TestAddTask, TestGetTask, TestGetProject, TestGetTag |
| `test_hybrid_freshness.py` | TestFreshness, TestEdgeCases |
| `test_hybrid_encoding.py` | TestPlainTextNoteEncoding, TestLocalDatetimeParsing |

Shared helpers (`create_test_db`, `_minimal_task`, `_minimal_project`, `_minimal_tag`, `_minimal_folder`, `_make_note_xml`, `_make_perspective_plist`, CF epoch constants, `hybrid_db`/`hybrid_repo` fixtures) move to `unit/repository/conftest.py`.

**`test_service.py` (2228 lines) → 2-3 files under `unit/service/`:**

| New file | Classes to move |
|---|---|
| `test_add_task.py` | TestAddTask, TestAddTaskRepetitionRule |
| `test_edit_task.py` | TestEditTask, TestEditTaskRepetitionRule, TestAnchorDateWarning |
| `test_error_handling.py` | TestErrorOperatorService, TestConstantMtimeSource (or merge into conftest) |

### 4. Add to CLAUDE.md

Add this section after "## Service Layer Convention":

```markdown
## Test Organization

- `tests/unit/` — fast, deterministic, no real external dependencies. SQLite in `tmp_path` counts as a controlled fixture. Mirrors source package hierarchy.
- `tests/integration/` — full stack (FastMCP server/client, simulator, cross-layer schema validation). Flat structure.
- `tests/golden_master/` — replays against InMemoryBridge compared to snapshots from real OmniFocus.
- Each subfolder's `conftest.py` has a docstring stating its classification rule.
```

### 5. Update pyproject.toml

Ensure pytest discovery covers the new subdirectories (it should by default, but verify `testpaths` config).

### 6. Execution notes

- Use `git mv` for all file moves to preserve history.
- Update all import paths in moved files and conftest fixtures.
- Run full test suite after each major move to catch broken imports.
- Do NOT change any test logic — this is a pure reorganization.
