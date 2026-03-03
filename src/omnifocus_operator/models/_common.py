"""Common standalone models used as nested types in Task and Project.

These models represent nested objects in the bridge JSON output:
- RepetitionRule: from bridge rr() function
- ReviewInterval: from bridge ri() function
"""

from __future__ import annotations

from omnifocus_operator.models._base import OmniFocusBaseModel


class RepetitionRule(OmniFocusBaseModel):
    """Repetition rule for recurring tasks and projects.

    # TEMPORARY: This model is incomplete. OmniFocus exposes 4 fields on
    # RepetitionRule (ruleString, scheduleType, fixedInterval, unit) but we
    # only capture 2 here with scheduleType optional. A follow-up phase will
    # redesign this model based on .research/Deep Dives/Repetition Rule/.
    # See: .planning/debug/repetition-rule-validation-failure.md
    """

    rule_string: str
    schedule_type: str | None = None


class ReviewInterval(OmniFocusBaseModel):
    """Review interval for project review scheduling.

    Serializes to: {"steps": N, "unit": "..."}
    """

    steps: int
    unit: str
