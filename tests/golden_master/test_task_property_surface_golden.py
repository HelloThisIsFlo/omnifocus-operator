"""Golden master test for the Phase 56 task property surface read shape.

Compares the serialized ``list_tasks`` response for a fully-populated task
(all five new derived flags + the expanded ``hierarchy`` include group)
against a committed baseline JSON.

Capture / refresh of the baseline is HUMAN-ONLY per project CLAUDE.md:

> "Golden master snapshots are human-only — agents create test infra,
>  never capture/refresh snapshots"

This file contains ONLY the comparison + opt-in capture infrastructure.
When the baseline is missing, the comparison test skips cleanly and points
at ``tests/golden_master/snapshots/README.md`` for the capture procedure.
An agent or CI run that leaves ``GOLDEN_MASTER_CAPTURE`` unset will ALWAYS
skip (missing baseline path) — no accidental baseline capture possible.

An invariant test locks the opt-in contract: the env var MUST be unset
during regular pytest runs. If an agent sets it, the invariant test fails
loudly and the capture branch stays untriggered.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

_BASELINE = Path(__file__).parent / "snapshots" / "task_property_surface_baseline.json"
_CAPTURE_ENV_VAR = "GOLDEN_MASTER_CAPTURE"
_VOLATILE_KEYS = frozenset({"id", "url", "added", "modified"})
_NORMALIZED_SENTINEL = "<normalized>"


def _normalize_for_comparison(payload: Any) -> Any:
    """Strip volatile fields (IDs, URLs, timestamps) so snapshots are stable.

    Mirrors the presence-check sentinel pattern from
    ``tests/golden_master/normalize.py`` but applied recursively without
    entity-type dispatch: any key named ``id`` / ``url`` / ``added`` /
    ``modified`` at any nesting depth is replaced with
    ``"<normalized>"``. Simple and deterministic — the baseline is a
    shape contract, not a timing-dependent contract.
    """
    if isinstance(payload, dict):
        return {
            key: _NORMALIZED_SENTINEL
            if key in _VOLATILE_KEYS and value is not None
            else _normalize_for_comparison(value)
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [_normalize_for_comparison(item) for item in payload]
    return payload


def _post_56_06_write_surface_present() -> bool:
    """Feature-detect post-56-06 AddTaskCommand fields (same gate as 56-07 Task 2)."""
    from omnifocus_operator.contracts.use_cases.add.tasks import (  # noqa: PLC0415
        AddTaskCommand,
    )

    fields = AddTaskCommand.model_fields
    return "completes_with_children" in fields and "type" in fields


async def _build_current_snapshot(service: Any, add_cmd_type: Any) -> dict[str, Any]:
    """Produce the current serialized payload for the golden-master compare.

    One task exercising all five new derived flags + hierarchy include:
    - completes_with_children=False -> dependsOnChildren surfaces (with
      children present, depends_on_children becomes True; without, False)
    - type=SEQUENTIAL -> isSequential surfaces
    - note present -> hasNote surfaces
    """
    await service.add_task(
        add_cmd_type(
            name="Golden Task",
            note="A note so hasNote=true",
            completes_with_children=False,
            type=__import__(
                "omnifocus_operator.models.enums",
                fromlist=["TaskType"],
            ).TaskType.SEQUENTIAL,
        )
    )

    from omnifocus_operator.contracts.use_cases.list.tasks import (  # noqa: PLC0415
        ListTasksQuery,
    )

    result = await service.list_tasks(
        ListTasksQuery(search="Golden Task", include=["hierarchy"]),
    )
    items = [item.model_dump(by_alias=True) for item in result.items]
    return {"items": items, "total": result.total}


class TestTaskPropertySurfaceGoldenMaster:
    """Phase 56 read-shape golden-master scaffolding (compare + opt-in capture)."""

    def test_golden_master_capture_mode_is_opt_in(self) -> None:
        """``GOLDEN_MASTER_CAPTURE`` MUST NOT be set during regular pytest runs.

        Agents and CI must leave it unset. This invariant test locks the
        opt-in contract — if it flips on, the capture branch would run and
        potentially overwrite a baseline silently. Explicit assertion
        makes that path visible to humans and blocks it from automation.
        """
        assert os.environ.get(_CAPTURE_ENV_VAR) is None, (
            f"{_CAPTURE_ENV_VAR} is set — if you're an agent or CI run, UNSET IT. "
            f"Capture/refresh is human-only per project CLAUDE.md feedback "
            f"('Golden master snapshots are human-only'). See "
            f"tests/golden_master/snapshots/README.md for the manual procedure."
        )

    @pytest.mark.asyncio
    async def test_task_property_surface_matches_golden_baseline(self, service: Any) -> None:
        """Compare serialized list_tasks payload against the committed baseline.

        Skips cleanly when the baseline file is absent — capture is
        human-only, so the default state for a fresh worktree (or any
        automated run) is the skip branch. When a human runs the capture
        procedure documented in tests/golden_master/snapshots/README.md,
        the baseline appears and this test starts comparing.
        """
        if not _post_56_06_write_surface_present():
            pytest.skip(
                "Post-56-06 AddTaskCommand surface (completes_with_children + "
                "type) not yet present. Golden master scaffolding waits for "
                "56-06 to land before the comparison becomes meaningful."
            )

        from omnifocus_operator.contracts.use_cases.add.tasks import (  # noqa: PLC0415
            AddTaskCommand,
        )

        current = await _build_current_snapshot(service, AddTaskCommand)
        normalized_current = _normalize_for_comparison(current)

        if os.environ.get(_CAPTURE_ENV_VAR):
            # Opt-in capture branch — gated behind the env var. Agents and
            # CI must leave it unset (locked by the invariant test above).
            _BASELINE.parent.mkdir(parents=True, exist_ok=True)
            _BASELINE.write_text(
                json.dumps(normalized_current, indent=2, sort_keys=True) + "\n",
            )
            pytest.skip(
                f"Captured baseline to {_BASELINE}. Unset {_CAPTURE_ENV_VAR} to run the comparison."
            )

        if not _BASELINE.exists():
            pytest.skip(
                f"Golden master baseline not captured: {_BASELINE}. "
                f"To capture, follow the human-only procedure documented in "
                f"tests/golden_master/snapshots/README.md. Agents MUST NOT "
                f"auto-capture per project CLAUDE.md feedback."
            )

        baseline = json.loads(_BASELINE.read_text())
        assert normalized_current == baseline, (
            "Golden master mismatch for the Phase 56 task property surface. "
            "If the shape change is INTENTIONAL (new field, rename, etc.), "
            "regenerate the baseline via the human-only capture procedure "
            "documented in tests/golden_master/snapshots/README.md. "
            "If UNINTENTIONAL, the diff above flags a regression to fix in code."
        )
