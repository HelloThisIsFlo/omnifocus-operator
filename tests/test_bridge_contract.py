"""CI contract tests: verify InMemoryBridge matches golden master from the real Bridge.

Golden master fixtures are captured by uat/capture_golden_master.py (human-run).
These tests replay the same operations against InMemoryBridge and assert structural
equivalence after normalizing dynamic fields.

If golden master files don't exist (user hasn't run capture yet), tests skip
with a clear message.

Usage:
    uv run pytest tests/test_bridge_contract.py -x -v
"""

from __future__ import annotations

import asyncio
import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from tests.doubles import InMemoryBridge
from tests.golden_master.normalize import (
    filter_to_known_ids,
    normalize_response,
    normalize_state,
)

SNAPSHOTS_DIR = Path(__file__).parent / "golden_master" / "snapshots"
INITIAL_STATE_FILE = SNAPSHOTS_DIR / "initial_state.json"

SKIP_MSG = "Golden master not captured yet. Run: uv run python uat/capture_golden_master.py"


# ---------------------------------------------------------------------------
# Scenario result from replay
# ---------------------------------------------------------------------------


@dataclass
class ScenarioResult:
    """Result of replaying one scenario against InMemoryBridge."""

    label: str
    description: str
    passed: bool
    error: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_initial_state() -> dict[str, Any]:
    if not INITIAL_STATE_FILE.exists():
        pytest.skip(SKIP_MSG)
    return json.loads(INITIAL_STATE_FILE.read_text(encoding="utf-8"))


def _load_scenarios() -> list[dict[str, Any]]:
    """Load scenarios from numbered subfolders or flat files (backward-compatible)."""
    # Try subfolder format first (Phase 28+)
    scenarios: list[dict[str, Any]] = []
    for subfolder in sorted(SNAPSHOTS_DIR.iterdir()):
        if subfolder.is_dir():
            for f in sorted(subfolder.glob("*.json")):
                scenarios.append(json.loads(f.read_text(encoding="utf-8")))
    if scenarios:
        return scenarios
    # Fall back to flat format (Phase 27)
    files = sorted(SNAPSHOTS_DIR.glob("scenario_*.json"))
    if not files:
        pytest.skip(SKIP_MSG)
    return [json.loads(f.read_text(encoding="utf-8")) for f in files]


def _seed_bridge(initial_state: dict[str, Any]) -> InMemoryBridge:
    """Seed InMemoryBridge from initial state (raw format from capture script)."""
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
    known_project_ids = {p["id"] for p in initial_state.get("projects", []) if "id" in p}
    known_tag_ids = {t["id"] for t in initial_state.get("tags", []) if "id" in t}
    known_task_ids: set[str] = set()
    return known_task_ids, known_project_ids, known_tag_ids


def _remap_ids(params: dict[str, Any], id_map: dict[str, str]) -> dict[str, Any]:
    """Replace golden master task IDs in params with InMemoryBridge IDs."""
    if not id_map:
        return params
    remapped = dict(params)
    if "id" in remapped and remapped["id"] in id_map:
        remapped["id"] = id_map[remapped["id"]]
    if "parent" in remapped and remapped["parent"] in id_map:
        remapped["parent"] = id_map[remapped["parent"]]
    if "moveTo" in remapped and isinstance(remapped["moveTo"], dict):
        mt = dict(remapped["moveTo"])
        cid = mt.get("containerId")
        if cid in id_map:
            mt["containerId"] = id_map[cid]
        # Anchor-based moves (before/after positioning)
        aid = mt.get("anchorId")
        if aid in id_map:
            mt["anchorId"] = id_map[aid]
        remapped["moveTo"] = mt
    return remapped


def _remap_state_ids(state: dict[str, Any], id_map: dict[str, str]) -> dict[str, Any]:
    """Remap golden master IDs in state_after to InMemoryBridge IDs.

    Task parent/project fields reference entity IDs that differ between
    OmniFocus and InMemoryBridge. The id_map (built during replay) maps
    golden master task IDs to their InMemoryBridge equivalents.
    """
    remapped = copy.deepcopy(state)
    for task in remapped.get("tasks", []):
        if task.get("parent") in id_map:
            task["parent"] = id_map[task["parent"]]
        if task.get("project") in id_map:
            task["project"] = id_map[task["project"]]
    return remapped


def _restrict_to_expected_keys(
    expected_state: dict[str, Any], actual_state: dict[str, Any]
) -> dict[str, Any]:
    """Restrict actual state entities to only keys present in expected state.

    Backward-compatible: when fields graduate from VOLATILE/UNCOMPUTED, the
    golden master (captured before graduation) won't have those fields.  The
    InMemoryBridge output will.  Rather than failing on the extra fields, we
    restrict comparison to the intersection.  Once re-captured, the golden
    master includes all fields and this is a no-op.
    """
    result: dict[str, Any] = {}
    for entity_type in ("tasks", "projects", "tags"):
        exp_list = expected_state.get(entity_type, [])
        act_list = actual_state.get(entity_type, [])
        # Build name->expected_keys lookup
        exp_keys_by_name = {e.get("name", ""): set(e.keys()) for e in exp_list}
        restricted: list[dict[str, Any]] = []
        for entity in act_list:
            name = entity.get("name", "")
            if name in exp_keys_by_name:
                allowed = exp_keys_by_name[name]
                restricted.append({k: v for k, v in entity.items() if k in allowed})
            else:
                restricted.append(entity)
        result[entity_type] = restricted
    return result


def _diff_dicts(expected: dict[str, Any], actual: dict[str, Any]) -> str:
    lines: list[str] = []
    all_keys = sorted(set(expected) | set(actual))
    for key in all_keys:
        exp_val = expected.get(key, "<missing>")
        act_val = actual.get(key, "<missing>")
        if exp_val != act_val:
            lines.append(f"  {key}:")
            lines.append(f"    expected: {exp_val}")
            lines.append(f"    actual:   {act_val}")
    return "\n".join(lines) if lines else "  (no differences found)"


def _diff_state(expected: dict[str, Any], actual: dict[str, Any]) -> str:
    lines: list[str] = []
    for entity_type in ("tasks", "projects", "tags"):
        exp_list = expected.get(entity_type, [])
        act_list = actual.get(entity_type, [])
        if exp_list == act_list:
            continue
        lines.append(f"\n  {entity_type}:")
        exp_by_name = {e.get("name", f"<unnamed-{i}>"): e for i, e in enumerate(exp_list)}
        act_by_name = {e.get("name", f"<unnamed-{i}>"): e for i, e in enumerate(act_list)}
        all_names = sorted(set(exp_by_name) | set(act_by_name))
        for name in all_names:
            exp_entity = exp_by_name.get(name)
            act_entity = act_by_name.get(name)
            if exp_entity is None:
                lines.append(f"    {name}: UNEXPECTED (not in golden master)")
                continue
            if act_entity is None:
                lines.append(f"    {name}: MISSING (expected but not produced)")
                continue
            if exp_entity == act_entity:
                continue
            lines.append(f"    {name}:")
            for key in sorted(set(exp_entity) | set(act_entity)):
                exp_val = exp_entity.get(key, "<missing>")
                act_val = act_entity.get(key, "<missing>")
                if exp_val != act_val:
                    lines.append(f"      {key}:")
                    lines.append(f"        expected: {exp_val}")
                    lines.append(f"        actual:   {act_val}")
    return "\n".join(lines) if lines else "  (no differences found)"


# ---------------------------------------------------------------------------
# Replay engine — runs once, stores per-scenario results
# ---------------------------------------------------------------------------

_replay_results: dict[str, ScenarioResult] | None = None


def _replay_all() -> dict[str, ScenarioResult]:
    """Replay all scenarios against InMemoryBridge. Cached after first call."""
    global _replay_results
    if _replay_results is not None:
        return _replay_results

    initial_state = _load_initial_state()
    scenarios = _load_scenarios()
    bridge = _seed_bridge(initial_state)
    known_task_ids, known_project_ids, known_tag_ids = _extract_known_ids(initial_state)
    id_map: dict[str, str] = {}
    results: dict[str, ScenarioResult] = {}

    # State accumulates — must run sequentially. If one scenario errors,
    # all subsequent scenarios are marked as blocked.
    blocked_after: str | None = None

    for scenario in scenarios:
        label = scenario["scenario"]
        desc = scenario.get("description", "")

        if blocked_after is not None:
            results[label] = ScenarioResult(
                label=label,
                description=desc,
                passed=False,
                error=f"Blocked — scenario {blocked_after} failed first",
            )
            continue

        try:
            golden_ids = scenario.get("created_ids", [])

            # Setup step for followup scenarios
            if "setup_operation" in scenario:
                setup_params = _remap_ids(scenario["setup_params"], id_map)
                setup_response = asyncio.run(
                    bridge.send_command(scenario["setup_operation"], setup_params)
                )
                if scenario["setup_operation"] == "add_task":
                    known_task_ids.add(setup_response["id"])
                    if golden_ids:
                        id_map[golden_ids[0]] = setup_response["id"]

            operation = scenario["operation"]
            params = _remap_ids(scenario["params"], id_map)

            response = asyncio.run(bridge.send_command(operation, params))
            if operation == "add_task" and "setup_operation" not in scenario:
                known_task_ids.add(response["id"])
                if golden_ids:
                    id_map[golden_ids[0]] = response["id"]
            elif operation == "add_task" and "setup_operation" in scenario:
                # Both setup and main are add_task (e.g., flagged_chain:
                # setup creates parent, main creates child). Track the
                # child's ID at golden_ids[1].
                known_task_ids.add(response["id"])
                if len(golden_ids) > 1:
                    id_map[golden_ids[1]] = response["id"]

            # Check response
            actual_response = normalize_response(response)
            if actual_response != scenario["response"]:
                results[label] = ScenarioResult(
                    label=label,
                    description=desc,
                    passed=False,
                    error=f"Response mismatch:\n"
                    f"{_diff_dicts(scenario['response'], actual_response)}",
                )
                blocked_after = label
                continue

            # Check state
            state = asyncio.run(bridge.send_command("get_all"))
            filtered = filter_to_known_ids(
                state,
                known_task_ids,
                known_project_ids,
                known_tag_ids,
            )
            actual_state = normalize_state(filtered)
            expected_raw = _remap_state_ids(scenario["state_after"], id_map)
            expected_state = normalize_state(expected_raw)
            # Restrict to keys present in expected (backward-compat for field graduation)
            actual_state = _restrict_to_expected_keys(expected_state, actual_state)
            if actual_state != expected_state:
                results[label] = ScenarioResult(
                    label=label,
                    description=desc,
                    passed=False,
                    error=f"State mismatch:\n{_diff_state(expected_state, actual_state)}",
                )
                blocked_after = label
                continue

            results[label] = ScenarioResult(
                label=label,
                description=desc,
                passed=True,
            )

        except Exception as exc:
            results[label] = ScenarioResult(
                label=label,
                description=desc,
                passed=False,
                error=(
                    f"{type(exc).__name__}: {exc}\n"
                    f"Operation: {scenario.get('operation')}\n"
                    f"Params: {scenario.get('params')}"
                ),
            )
            blocked_after = label

    _replay_results = results
    return results


def _get_scenario_ids() -> list[str]:
    """Get scenario IDs for parametrize. Returns empty list if not captured."""
    if not INITIAL_STATE_FILE.exists():
        return []
    # Try subfolder format first (Phase 28+)
    ids: list[str] = []
    for subfolder in sorted(SNAPSHOTS_DIR.iterdir()):
        if subfolder.is_dir():
            for f in sorted(subfolder.glob("*.json")):
                data = json.loads(f.read_text(encoding="utf-8"))
                ids.append(data["scenario"])
    if ids:
        return ids
    # Fall back to flat format (Phase 27)
    files = sorted(SNAPSHOTS_DIR.glob("scenario_*.json"))
    if not files:
        return []
    return [json.loads(f.read_text(encoding="utf-8"))["scenario"] for f in files]


# ---------------------------------------------------------------------------
# Tests — one per scenario
# ---------------------------------------------------------------------------


_scenario_ids = _get_scenario_ids()


@pytest.mark.filterwarnings("ignore::ResourceWarning")
@pytest.mark.skipif(not _scenario_ids, reason=SKIP_MSG)
class TestBridgeContract:
    """Verify InMemoryBridge matches golden master from the real Bridge."""

    @pytest.mark.parametrize("scenario_id", _scenario_ids)
    def test_scenario(self, scenario_id: str) -> None:
        results = _replay_all()
        result = results[scenario_id]
        if not result.passed:
            pytest.fail(f"{result.description}\n\n{result.error}")
