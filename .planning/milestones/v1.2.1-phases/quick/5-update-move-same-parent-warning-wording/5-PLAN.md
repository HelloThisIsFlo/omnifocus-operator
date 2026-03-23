# Quick Task 5: Update move same-parent warning wording

## Task 1: Update warning string

- **files:** `src/omnifocus_operator/service.py`
- **action:** Replace the old warning text with clearer wording
- **verify:** `uv run python -m pytest tests/test_service.py -k "move" -x -q`
- **done:** Warning updated, tests pass
