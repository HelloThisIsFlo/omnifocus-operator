"""OmniFocus data models -- Pydantic v2 models for all OmniFocus entities.

Public API for the models package. All model classes and enums are
re-exported here for convenient importing.
"""

from pydantic import AwareDatetime

from omnifocus_operator.models._base import (
    ActionableEntity,
    OmniFocusBaseModel,
    OmniFocusEntity,
)
from omnifocus_operator.models._common import RepetitionRule, ReviewInterval, TagRef
from omnifocus_operator.models._enums import (
    AnchorDateKey,
    FolderStatus,
    ProjectStatus,
    ScheduleType,
    TagStatus,
    TaskStatus,
)
from omnifocus_operator.models._folder import Folder
from omnifocus_operator.models._perspective import Perspective
from omnifocus_operator.models._project import Project
from omnifocus_operator.models._snapshot import DatabaseSnapshot
from omnifocus_operator.models._tag import Tag
from omnifocus_operator.models._task import Task

# Resolve forward references now that all modules are imported.
# Entity modules use TYPE_CHECKING imports for ruff TC compliance.
# model_rebuild() with _types_namespace provides the actual types at
# schema-build time so Pydantic can resolve string annotations.
#
# Order matters: base classes first, then subclasses, then aggregators.
_ns: dict[str, type] = {
    "AwareDatetime": AwareDatetime,
    "RepetitionRule": RepetitionRule,
    "ReviewInterval": ReviewInterval,
    "TagRef": TagRef,
    "ProjectStatus": ProjectStatus,
    "TagStatus": TagStatus,
    "FolderStatus": FolderStatus,
    "ScheduleType": ScheduleType,
    "AnchorDateKey": AnchorDateKey,
    "TaskStatus": TaskStatus,
    "Task": Task,
    "Project": Project,
    "Tag": Tag,
    "Folder": Folder,
    "Perspective": Perspective,
}
RepetitionRule.model_rebuild(_types_namespace=_ns)
ActionableEntity.model_rebuild(_types_namespace=_ns)
Task.model_rebuild(_types_namespace=_ns)
Project.model_rebuild(_types_namespace=_ns)
Tag.model_rebuild(_types_namespace=_ns)
Folder.model_rebuild(_types_namespace=_ns)
DatabaseSnapshot.model_rebuild(_types_namespace=_ns)

__all__ = [
    "ActionableEntity",
    "AnchorDateKey",
    "DatabaseSnapshot",
    "Folder",
    "FolderStatus",
    "OmniFocusBaseModel",
    "OmniFocusEntity",
    "Perspective",
    "Project",
    "ProjectStatus",
    "RepetitionRule",
    "ReviewInterval",
    "ScheduleType",
    "Tag",
    "TagRef",
    "TagStatus",
    "Task",
    "TaskStatus",
]
