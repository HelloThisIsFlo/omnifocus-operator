"""Folder model -- represents a single OmniFocus folder.

Maps to the flattenedFolders.map() output in the bridge script.
Folder has 8 total fields.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnifocus_operator.models._base import OmniFocusEntity

if TYPE_CHECKING:
    from pydantic import AwareDatetime

    from omnifocus_operator.models._enums import EntityStatus


class Folder(OmniFocusEntity):
    """A single OmniFocus folder with all bridge fields.

    Inherits id and name from OmniFocusEntity.
    """

    added: AwareDatetime | None = None
    modified: AwareDatetime | None = None
    active: bool
    effective_active: bool
    status: EntityStatus | None = None
    parent: str | None = None
