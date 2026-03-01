"""DatabaseSnapshot model -- aggregates all OmniFocus entity collections.

Represents the complete output of the bridge script, containing
lists of all entity types.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnifocus_operator.models._base import OmniFocusBaseModel

if TYPE_CHECKING:
    from omnifocus_operator.models._folder import Folder
    from omnifocus_operator.models._perspective import Perspective
    from omnifocus_operator.models._project import Project
    from omnifocus_operator.models._tag import Tag
    from omnifocus_operator.models._task import Task


class DatabaseSnapshot(OmniFocusBaseModel):
    """Complete snapshot of OmniFocus database from bridge script.

    Aggregates all five entity collection lists produced by the
    bridge script's JSON output.
    """

    tasks: list[Task]
    projects: list[Project]
    tags: list[Tag]
    folders: list[Folder]
    perspectives: list[Perspective]
