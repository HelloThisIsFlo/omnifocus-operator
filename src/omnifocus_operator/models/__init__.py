"""OmniFocus data models -- Pydantic v2 models for all OmniFocus entities.

Public API for the models package. All model classes and enums are
re-exported here for convenient importing.
"""

from pydantic import AwareDatetime

from omnifocus_operator.models.base import OmniFocusBaseModel
from omnifocus_operator.models.common import (
    ActionableEntity,
    FolderRef,
    OmniFocusEntity,
    ParentRef,
    ProjectRef,
    ReviewInterval,
    TagRef,
    TaskRef,
)
from omnifocus_operator.models.enums import (
    Availability,
    BasedOn,
    FolderAvailability,
    ProjectType,
    Schedule,
    TagAvailability,
    TaskType,
    Urgency,
)
from omnifocus_operator.models.folder import Folder
from omnifocus_operator.models.perspective import Perspective
from omnifocus_operator.models.project import Project
from omnifocus_operator.models.repetition_rule import RepetitionRule
from omnifocus_operator.models.snapshot import AllEntities
from omnifocus_operator.models.tag import Tag
from omnifocus_operator.models.task import Task

# Resolve forward references now that all modules are imported.
# Entity modules use TYPE_CHECKING imports for ruff TC compliance.
# model_rebuild() with _types_namespace provides the actual types at
# schema-build time so Pydantic can resolve string annotations.
#
# Order matters: base classes first, then subclasses, then aggregators.
_ns: dict[str, type] = {
    "AwareDatetime": AwareDatetime,
    "FolderRef": FolderRef,
    "ParentRef": ParentRef,
    "ProjectRef": ProjectRef,
    "RepetitionRule": RepetitionRule,
    "ReviewInterval": ReviewInterval,
    "TagRef": TagRef,
    "TaskRef": TaskRef,
    "Urgency": Urgency,
    "Availability": Availability,
    "TagAvailability": TagAvailability,
    "FolderAvailability": FolderAvailability,
    "Schedule": Schedule,
    "BasedOn": BasedOn,
    "TaskType": TaskType,
    "ProjectType": ProjectType,
    "Task": Task,
    "Project": Project,
    "Tag": Tag,
    "Folder": Folder,
    "Perspective": Perspective,
}
ParentRef.model_rebuild(_types_namespace=_ns)
RepetitionRule.model_rebuild(_types_namespace=_ns)
ActionableEntity.model_rebuild(_types_namespace=_ns)
Task.model_rebuild(_types_namespace=_ns)
Project.model_rebuild(_types_namespace=_ns)
Tag.model_rebuild(_types_namespace=_ns)
Folder.model_rebuild(_types_namespace=_ns)
AllEntities.model_rebuild(_types_namespace=_ns)

__all__ = [
    "ActionableEntity",
    "AllEntities",
    "Availability",
    "BasedOn",
    "Folder",
    "FolderAvailability",
    "FolderRef",
    "OmniFocusBaseModel",
    "OmniFocusEntity",
    "ParentRef",
    "Perspective",
    "Project",
    "ProjectRef",
    "ProjectType",
    "RepetitionRule",
    "ReviewInterval",
    "Schedule",
    "Tag",
    "TagAvailability",
    "TagRef",
    "Task",
    "TaskRef",
    "TaskType",
    "Urgency",
]
