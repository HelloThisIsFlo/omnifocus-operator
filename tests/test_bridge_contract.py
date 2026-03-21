"""CI contract tests: verify InMemoryBridge matches golden master from RealBridge.

Golden master fixtures are captured by uat/capture_golden_master.py (human-run).
These tests replay the same operations against InMemoryBridge and assert structural
equivalence after normalizing dynamic fields.

If golden master files don't exist (user hasn't run capture yet), tests skip
with a clear message.

Usage:
    uv run pytest tests/test_bridge_contract.py -x -v
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.doubles import InMemoryBridge
from tests.golden.normalize import (
    filter_to_known_ids,
    normalize_response,
    normalize_state,
)

GOLDEN_DIR = Path(__file__).parent / "golden"
INITIAL_STATE_FILE = GOLDEN_DIR / "initial_state.json"

SKIP_MSG = "Golden master not captured yet. Run: uv run python uat/capture_golden_master.py"


def load_initial_state() -> dict[str, Any]:
    """Load initial_state.json or skip if not captured yet."""
    if not INITIAL_STATE_FILE.exists():
        pytest.skip(SKIP_MSG)
    return json.loads(INITIAL_STATE_FILE.read_text(encoding="utf-8"))


def load_scenarios() -> list[dict[str, Any]]:
    """Load all scenario_*.json files in order."""
    files = sorted(GOLDEN_DIR.glob("scenario_*.json"))
    if not files:
        pytest.skip(SKIP_MSG)
    return [json.loads(f.read_text(encoding="utf-8")) for f in files]


def _seed_bridge(initial_state: dict[str, Any]) -> InMemoryBridge:
    """Create InMemoryBridge seeded with golden master initial state.

    The initial state contains normalized projects and tags (dynamic fields
    stripped). We reconstruct minimal dicts suitable for InMemoryBridge seeding.
    """
    return InMemoryBridge(
        data={
            "tasks": list(initial_state.get("tasks", [])),
            "projects": list(initial_state.get("projects", [])),
            "tags": list(initial_state.get("tags", [])),
            "folders": [],
            "perspectives": [],
        }
    )


def _extract_known_ids(
    initial_state: dict[str, Any],
) -> tuple[set[str], set[str], set[str]]:
    """Extract known IDs from initial state for filtering."""
    known_project_ids = {p["id"] for p in initial_state.get("projects", []) if "id" in p}
    known_tag_ids = {t["id"] for t in initial_state.get("tags", []) if "id" in t}
    # No tasks in initial state (they are created by scenarios)
    known_task_ids: set[str] = set()
    return known_task_ids, known_project_ids, known_tag_ids


class TestBridgeContract:
    """Verify InMemoryBridge matches golden master from RealBridge."""

    @pytest.mark.asyncio
    async def test_all_scenarios_match_golden_master(self) -> None:
        """Replay all golden master scenarios against InMemoryBridge.

        State accumulates across scenarios -- this mirrors how the capture
        script recorded them sequentially against RealBridge.
        """
        initial_state = load_initial_state()
        scenarios = load_scenarios()

        bridge = _seed_bridge(initial_state)
        known_task_ids, known_project_ids, known_tag_ids = _extract_known_ids(initial_state)

        for scenario in scenarios:
            label = scenario["scenario"]
            operation = scenario["operation"]
            params = scenario["params"]

            # Execute the operation
            response = await bridge.send_command(operation, params)

            # Track new task IDs from add_task responses
            if operation == "add_task":
                known_task_ids.add(response["id"])

            # Verify response matches golden master
            actual_response = normalize_response(response)
            assert actual_response == scenario["response"], f"Response mismatch in scenario {label}"

            # Verify state matches golden master
            state = await bridge.send_command("get_all")
            filtered = filter_to_known_ids(state, known_task_ids, known_project_ids, known_tag_ids)
            actual_state = normalize_state(filtered)
            assert actual_state == scenario["state_after"], f"State mismatch in scenario {label}"

    @pytest.mark.asyncio
    async def test_golden_master_files_exist(self) -> None:
        """Smoke test: verify golden master files are present.

        Skips with a clear message if files haven't been captured yet,
        so CI doesn't fail on a fresh clone but the test is visible.
        """
        if not INITIAL_STATE_FILE.exists():
            pytest.skip(SKIP_MSG)

        scenario_files = sorted(GOLDEN_DIR.glob("scenario_*.json"))
        if not scenario_files:
            pytest.skip(SKIP_MSG)

        assert INITIAL_STATE_FILE.exists(), "initial_state.json missing"
        assert len(scenario_files) >= 1, "No scenario files found"
