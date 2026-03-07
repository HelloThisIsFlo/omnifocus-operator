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

## Future Vision

Write-operation UAT scripts will use a sandboxed OmniFocus database to avoid modifying real data. Each script will document its data expectations and cleanup steps.
