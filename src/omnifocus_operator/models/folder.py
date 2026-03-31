"""Folder model -- represents a single OmniFocus folder.

Maps to the flattenedFolders.map() output in the bridge script.
Folder has 2 own fields + inherited from OmniFocusEntity.
"""

from __future__ import annotations

from omnifocus_operator.models.common import OmniFocusEntity
from omnifocus_operator.models.enums import FolderAvailability


class Folder(OmniFocusEntity):
    """A single OmniFocus folder with all fields.

    Inherits id, name, url, added, modified from OmniFocusEntity.
    """

    availability: FolderAvailability  # Folder availability (available/dropped)
    parent: str | None = None
