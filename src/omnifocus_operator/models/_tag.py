"""Tag model -- represents a single OmniFocus tag.

Maps to the flattenedTags.map() output in the bridge script.
Tag has 9 total fields.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnifocus_operator.models._base import OmniFocusEntity

if TYPE_CHECKING:
    from pydantic import AwareDatetime

    from omnifocus_operator.models._enums import EntityStatus


class Tag(OmniFocusEntity):
    """A single OmniFocus tag with all bridge fields.

    Inherits id and name from OmniFocusEntity.
    """

    added: AwareDatetime | None = None
    modified: AwareDatetime | None = None
    active: bool
    effective_active: bool
    status: EntityStatus | None = None
    allows_next_action: bool
    parent: str | None = None
