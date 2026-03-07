"""Folder model -- represents a single OmniFocus folder.

Maps to the flattenedFolders.map() output in the bridge script.
Folder has 2 own fields + inherited from OmniFocusEntity.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnifocus_operator.models.base import OmniFocusEntity

if TYPE_CHECKING:
    from omnifocus_operator.models.enums import FolderAvailability


class Folder(OmniFocusEntity):
    """A single OmniFocus folder with all fields.

    Inherits id, name, url, added, modified from OmniFocusEntity.
    """

    availability: FolderAvailability  # Folder availability (available/dropped)
    parent: str | None = None
