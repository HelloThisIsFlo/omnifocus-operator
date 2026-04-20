# 09-task-property-surface/ (pending human capture)

Empty until the human runs `uv run python uat/capture_golden_master.py`.

Scenarios are already declared in `uat/capture_golden_master.py`
(`_build_scenarios()`, `09-task-property-surface/` block — 8 scenarios).
Running the capture script writes one `*.json` fixture per scenario into
this folder; the bridge contract test (`tests/test_bridge_contract.py`)
discovers them automatically via `sorted(SNAPSHOTS_DIR.iterdir())`.

Until fixtures are captured, the test suite skips the new scenarios
cleanly — same skip-when-absent contract the other numbered subfolders
followed before their first capture.

See `../README.md` for the overall capture/replay workflow and
`../../README.md` for the normalization categories.
