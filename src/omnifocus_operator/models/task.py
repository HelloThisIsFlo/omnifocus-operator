"""Task model -- represents a single OmniFocus task."""

from __future__ import annotations

from typing import Any

from pydantic import AwareDatetime, Field, field_serializer

from omnifocus_operator.agent_messages.descriptions import (
    DEPENDS_ON_CHILDREN_DESC,
    INHERITED_COMPLETION_DATE,
    INHERITED_DEFER_DATE,
    INHERITED_DROP_DATE,
    INHERITED_DUE_DATE,
    INHERITED_FLAGGED,
    INHERITED_PLANNED_DATE,
    IS_SEQUENTIAL_DESC,
    ORDER_FIELD,
    TASK_DOC,
    TASK_PROJECT_DESC,
    TASK_TYPE_DESC,
)
from omnifocus_operator.models.common import ActionableEntity, ParentRef, ProjectRef
from omnifocus_operator.models.enums import TaskType


class Task(ActionableEntity):
    __doc__ = TASK_DOC

    # Ordering (read-only, populated by HybridRepository CTE)
    order: str | None = Field(default=None, description=ORDER_FIELD)

    # Per-type enum (parallel | sequential) -- HIER-01 / HIER-05.
    # Required: every task is one or the other; repository materialises from
    # the underlying `Task.sequential` (0/1) column. No default at the model
    # layer; the service layer's add_tasks pipeline resolves the create-time
    # default from `OFMTaskDefaultSequential` (Phase 56-05).
    type: TaskType = Field(description=TASK_TYPE_DESC)

    # Derived presence flags (FLAG-04 / FLAG-05, task-only).
    # Populated by `DomainLogic.enrich_task_presence_flags` on every read
    # pipeline (get_all, get_task, list_tasks). Defaults are `False` so the
    # model stays safe if enrichment is somehow bypassed -- neither flag
    # triggers agent action on its own. Projects DO NOT carry these fields.
    is_sequential: bool = Field(default=False, description=IS_SEQUENTIAL_DESC)
    depends_on_children: bool = Field(default=False, description=DEPENDS_ON_CHILDREN_DESC)

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
