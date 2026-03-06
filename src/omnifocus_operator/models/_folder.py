"""Folder model -- represents a single OmniFocus folder.

Maps to the flattenedFolders.map() output in the bridge script.
Folder has 2 own fields + inherited from OmniFocusEntity.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnifocus_operator.models._base import OmniFocusEntity

if TYPE_CHECKING:
    from omnifocus_operator.models._enums import FolderStatus


class Folder(OmniFocusEntity):
    """A single OmniFocus folder with all bridge fields.

    Inherits id, name, url, added, modified, active, effective_active
    from OmniFocusEntity.
    """

    status: FolderStatus  # Lifecycle status (Active/Dropped)
    parent: str | None = None
