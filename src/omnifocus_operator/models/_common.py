"""Common standalone models used as nested types in Task and Project.

These models represent nested objects in the bridge JSON output:
- RepetitionRule: from bridge rr() function
- ReviewInterval: from bridge ri() function
"""

from __future__ import annotations

from omnifocus_operator.models._base import OmniFocusBaseModel


class RepetitionRule(OmniFocusBaseModel):
    """Repetition rule for recurring tasks and projects.

    Serializes to: {"ruleString": "...", "scheduleType": "..."}
    """

    rule_string: str
    schedule_type: str


class ReviewInterval(OmniFocusBaseModel):
    """Review interval for project review scheduling.

    Serializes to: {"steps": N, "unit": "..."}
    """

    steps: int
    unit: str
