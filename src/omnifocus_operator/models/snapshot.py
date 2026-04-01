"""AllEntities model -- aggregates all OmniFocus entity collections.

Container for the complete set of OmniFocus entities returned by
any repository implementation.
"""

from __future__ import annotations

from omnifocus_operator.agent_messages.descriptions import ALL_ENTITIES_DOC
from omnifocus_operator.models.base import OmniFocusBaseModel
from omnifocus_operator.models.folder import Folder
from omnifocus_operator.models.perspective import Perspective
from omnifocus_operator.models.project import Project
from omnifocus_operator.models.tag import Tag
from omnifocus_operator.models.task import Task


class AllEntities(OmniFocusBaseModel):
    __doc__ = ALL_ENTITIES_DOC

    tasks: list[Task]
    projects: list[Project]
    tags: list[Tag]
    folders: list[Folder]
    perspectives: list[Perspective]
