"""Tag model -- represents a single OmniFocus tag."""

from __future__ import annotations

from omnifocus_operator.models.common import OmniFocusEntity
from omnifocus_operator.models.enums import TagAvailability


class Tag(OmniFocusEntity):
    """A single OmniFocus tag with all fields."""

    availability: TagAvailability  # Tag availability (available/blocked/dropped)
    children_are_mutually_exclusive: bool
    parent: str | None = None
