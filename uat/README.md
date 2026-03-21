# UAT -- User Acceptance Testing

This directory contains **human-only** test scripts for validating OmniFocus Operator against a live OmniFocus database.

## Safety Posture

- **Agents must NEVER execute these scripts.** UAT scripts interact with your real OmniFocus data.
- **CI never runs these.** The `uat/` directory is excluded from pytest discovery via `testpaths = ["tests"]` in `pyproject.toml`.
- **SAFE-01/SAFE-02 enforcement.** The CI pipeline greps `tests/` for `RealBridge` references. UAT scripts live outside `tests/` by design.

## Scripts

### `test_read_only.py` (Phase 8)

A read-only validation script that connects to real OmniFocus via `RealBridge`, calls `dump_all`, and validates the response parses into a `AllEntities`.

**Prerequisites:**

1. OmniFocus 4 must be running on macOS.
2. The bridge script must be installed in OmniFocus (see project README).

**Usage:**

```bash
uv run python uat/test_read_only.py
```

**What it does:**

- Creates a `RealBridge` instance pointed at the default IPC directory.
- Sends a `dump_all` command to OmniFocus.
- Validates the raw response via `AllEntities.model_validate()`.
- Prints entity counts (tasks, projects, tags, folders, perspectives).
- Exits 0 on success, 1 on failure.

### `capture_golden_master.py` (Phase 27)

An interactive guided script that captures golden master fixtures from RealBridge for contract tests. Records how OmniFocus actually behaves for 17 add/edit scenarios, writes fixture JSON files to `tests/golden/`.

**Prerequisites:**

1. OmniFocus 4 must be running on macOS.
2. The bridge script must be installed in OmniFocus.

**Usage:**

```bash
uv run python uat/capture_golden_master.py
```

**What it does:**

- Guides you to create a test project (`GM-TestProject`) and two tags (`GM-Tag1`, `GM-Tag2`).
- Verifies each entity exists via the bridge before proceeding.
- Runs 17 scenarios covering add_task and edit_task operations (name, note, flagged, dates, tags, lifecycle, move).
- Writes golden master JSON files to `tests/golden/` (1 initial state + 17 scenario files).
- Consolidates all test tasks under `GM-TestProject` for single-deletion cleanup.

**Cleanup after capture:**

- Delete the project `GM-TestProject` in OmniFocus (this deletes all test tasks too).
- Delete tags `GM-Tag1` and `GM-Tag2`.

**Re-capture:** Run again any time bridge operations change. The script overwrites existing fixture files. Per GOLD-01, any phase modifying bridge operations must re-capture.

## Future Vision

Write-operation UAT scripts will use a sandboxed OmniFocus database to avoid modifying real data. Each script will document its data expectations and cleanup steps.
