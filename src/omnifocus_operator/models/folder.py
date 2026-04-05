"""Folder model -- represents a single OmniFocus folder.

Maps to the flattenedFolders.map() output in the bridge script.
Folder has 2 own fields + inherited from OmniFocusEntity.
"""

from __future__ import annotations

from pydantic import Field

from omnifocus_operator.agent_messages.descriptions import FOLDER_DOC, FOLDER_PARENT_DESC
from omnifocus_operator.models.common import OmniFocusEntity
from omnifocus_operator.models.enums import FolderAvailability


class Folder(OmniFocusEntity):
    __doc__ = FOLDER_DOC

    availability: FolderAvailability  # Folder availability (available/dropped)
    parent: str | None = Field(default=None, description=FOLDER_PARENT_DESC)
