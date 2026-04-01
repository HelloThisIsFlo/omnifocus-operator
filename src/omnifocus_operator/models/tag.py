"""Tag model -- represents a single OmniFocus tag."""

from __future__ import annotations

from pydantic import Field

from omnifocus_operator.models.common import OmniFocusEntity
from omnifocus_operator.models.enums import TagAvailability


class Tag(OmniFocusEntity):
    """A single OmniFocus tag with all fields."""

    availability: TagAvailability  # Tag availability (available/blocked/dropped)
    children_are_mutually_exclusive: bool = Field(
        description="When true, child tags behave like radio buttons "
        "-- assigning one removes siblings.",
    )
    parent: str | None = None
