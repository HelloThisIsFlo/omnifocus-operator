"""AllEntities model -- aggregates all OmniFocus entity collections.

Container for the complete set of OmniFocus entities returned by
any repository implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnifocus_operator.models.base import OmniFocusBaseModel

if TYPE_CHECKING:
    from omnifocus_operator.models.folder import Folder
    from omnifocus_operator.models.perspective import Perspective
    from omnifocus_operator.models.project import Project
    from omnifocus_operator.models.tag import Tag
    from omnifocus_operator.models.task import Task


class AllEntities(OmniFocusBaseModel):
    """All OmniFocus entities from a repository.

    Aggregates all five entity collection lists: tasks, projects,
    tags, folders, and perspectives.
    """

    tasks: list[Task]
    projects: list[Project]
    tags: list[Tag]
    folders: list[Folder]
    perspectives: list[Perspective]
