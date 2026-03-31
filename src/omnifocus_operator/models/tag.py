"""Tag model -- represents a single OmniFocus tag.

Maps to the flattenedTags.map() output in the bridge script.
Tag has 3 own fields + inherited from OmniFocusEntity.
"""

from __future__ import annotations

from omnifocus_operator.models.common import OmniFocusEntity
from omnifocus_operator.models.enums import TagAvailability


class Tag(OmniFocusEntity):
    """A single OmniFocus tag with all fields.

    Inherits id, name, url, added, modified from OmniFocusEntity.
    """

    availability: TagAvailability  # Tag availability (available/blocked/dropped)
    children_are_mutually_exclusive: bool
    parent: str | None = None
