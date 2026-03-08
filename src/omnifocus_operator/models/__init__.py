"""OmniFocus data models -- Pydantic v2 models for all OmniFocus entities.

Public API for the models package. All model classes and enums are
re-exported here for convenient importing.
"""

from pydantic import AwareDatetime

from omnifocus_operator.models.base import (
    ActionableEntity,
    OmniFocusBaseModel,
    OmniFocusEntity,
)
from omnifocus_operator.models.common import ParentRef, RepetitionRule, ReviewInterval, TagRef
from omnifocus_operator.models.enums import (
    AnchorDateKey,
    Availability,
    FolderAvailability,
    ScheduleType,
    TagAvailability,
    Urgency,
)
from omnifocus_operator.models.folder import Folder
from omnifocus_operator.models.perspective import Perspective
from omnifocus_operator.models.project import Project
from omnifocus_operator.models.snapshot import AllEntities
from omnifocus_operator.models.tag import Tag
from omnifocus_operator.models.task import Task
from omnifocus_operator.models.write import (
    UNSET,
    MoveToSpec,
    TaskCreateResult,
    TaskCreateSpec,
    TaskEditResult,
    TaskEditSpec,
)

# Resolve forward references now that all modules are imported.
# Entity modules use TYPE_CHECKING imports for ruff TC compliance.
# model_rebuild() with _types_namespace provides the actual types at
# schema-build time so Pydantic can resolve string annotations.
#
# Order matters: base classes first, then subclasses, then aggregators.
_ns: dict[str, type] = {
    "AwareDatetime": AwareDatetime,
    "ParentRef": ParentRef,
    "RepetitionRule": RepetitionRule,
    "ReviewInterval": ReviewInterval,
    "TagRef": TagRef,
    "Urgency": Urgency,
    "Availability": Availability,
    "TagAvailability": TagAvailability,
    "FolderAvailability": FolderAvailability,
    "ScheduleType": ScheduleType,
    "AnchorDateKey": AnchorDateKey,
    "Task": Task,
    "Project": Project,
    "Tag": Tag,
    "Folder": Folder,
    "Perspective": Perspective,
    "TaskCreateSpec": TaskCreateSpec,
    "TaskCreateResult": TaskCreateResult,
    "TaskEditSpec": TaskEditSpec,
    "TaskEditResult": TaskEditResult,
    "MoveToSpec": MoveToSpec,
}
ParentRef.model_rebuild(_types_namespace=_ns)
RepetitionRule.model_rebuild(_types_namespace=_ns)
ActionableEntity.model_rebuild(_types_namespace=_ns)
Task.model_rebuild(_types_namespace=_ns)
Project.model_rebuild(_types_namespace=_ns)
Tag.model_rebuild(_types_namespace=_ns)
Folder.model_rebuild(_types_namespace=_ns)
AllEntities.model_rebuild(_types_namespace=_ns)
TaskCreateSpec.model_rebuild(_types_namespace=_ns)
TaskCreateResult.model_rebuild(_types_namespace=_ns)
TaskEditSpec.model_rebuild(_types_namespace=_ns)
TaskEditResult.model_rebuild(_types_namespace=_ns)
MoveToSpec.model_rebuild(_types_namespace=_ns)

__all__ = [
    "UNSET",
    "ActionableEntity",
    "AllEntities",
    "AnchorDateKey",
    "Availability",
    "Folder",
    "FolderAvailability",
    "MoveToSpec",
    "OmniFocusBaseModel",
    "OmniFocusEntity",
    "ParentRef",
    "Perspective",
    "Project",
    "RepetitionRule",
    "ReviewInterval",
    "ScheduleType",
    "Tag",
    "TagAvailability",
    "TagRef",
    "Task",
    "TaskCreateResult",
    "TaskCreateSpec",
    "TaskEditResult",
    "TaskEditSpec",
    "Urgency",
]
