"""Tag model -- represents a single OmniFocus tag.

Maps to the flattenedTags.map() output in the bridge script.
Tag has 4 own fields + inherited from OmniFocusEntity.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnifocus_operator.models._base import OmniFocusEntity

if TYPE_CHECKING:
    from omnifocus_operator.models._enums import TagStatus


class Tag(OmniFocusEntity):
    """A single OmniFocus tag with all bridge fields.

    Inherits id, name, url, added, modified, active, effective_active
    from OmniFocusEntity.
    """

    status: TagStatus  # Lifecycle status (Active/OnHold/Dropped)
    allows_next_action: bool
    children_are_mutually_exclusive: bool
    parent: str | None = None
