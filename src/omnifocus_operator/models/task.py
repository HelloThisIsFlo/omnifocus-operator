"""Task model -- represents a single OmniFocus task."""

from __future__ import annotations

from typing import Any

from pydantic import AwareDatetime, Field, field_serializer

from omnifocus_operator.agent_messages.descriptions import (
    INHERITED_COMPLETION_DATE,
    INHERITED_DEFER_DATE,
    INHERITED_DROP_DATE,
    INHERITED_DUE_DATE,
    INHERITED_FLAGGED,
    INHERITED_PLANNED_DATE,
    ORDER_FIELD,
    TASK_DOC,
    TASK_PROJECT_DESC,
)
from omnifocus_operator.models.common import ActionableEntity, ParentRef, ProjectRef


class Task(ActionableEntity):
    __doc__ = TASK_DOC

    # Ordering (read-only, populated by HybridRepository CTE)
    order: str | None = Field(default=None, description=ORDER_FIELD)

    # Inherited fields (task-only -- projects cannot inherit)
    inherited_flagged: bool = Field(default=False, description=INHERITED_FLAGGED)
    inherited_due_date: AwareDatetime | None = Field(
        default=None,
        description=INHERITED_DUE_DATE,
    )
    inherited_defer_date: AwareDatetime | None = Field(
        default=None,
        description=INHERITED_DEFER_DATE,
    )
    inherited_planned_date: AwareDatetime | None = Field(
        default=None,
        description=INHERITED_PLANNED_DATE,
    )
    inherited_drop_date: AwareDatetime | None = Field(
        default=None,
        description=INHERITED_DROP_DATE,
    )
    inherited_completion_date: AwareDatetime | None = Field(
        default=None,
        description=INHERITED_COMPLETION_DATE,
    )

    # Parent reference (tagged wrapper: project or task)
    parent: ParentRef

    # Containing project (at any nesting depth, or $inbox)
    project: ProjectRef = Field(description=TASK_PROJECT_DESC)

    @field_serializer("parent")
    def _serialize_parent(self, parent: ParentRef, _info: Any) -> dict[str, Any]:
        return parent.model_dump(exclude_none=True, by_alias=True)
