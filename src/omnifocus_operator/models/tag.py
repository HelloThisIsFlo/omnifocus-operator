"""Tag model -- represents a single OmniFocus tag."""

from __future__ import annotations

from pydantic import Field

from omnifocus_operator.agent_messages.descriptions import (
    CHILDREN_ARE_MUTUALLY_EXCLUSIVE,
    TAG_DOC,
    TAG_PARENT_DESC,
)
from omnifocus_operator.models.common import OmniFocusEntity, TagRef
from omnifocus_operator.models.enums import TagAvailability


class Tag(OmniFocusEntity):
    __doc__ = TAG_DOC

    availability: TagAvailability  # Tag availability (available/blocked/dropped)
    children_are_mutually_exclusive: bool = Field(
        description=CHILDREN_ARE_MUTUALLY_EXCLUSIVE,
    )
    parent: TagRef | None = Field(default=None, description=TAG_PARENT_DESC)
