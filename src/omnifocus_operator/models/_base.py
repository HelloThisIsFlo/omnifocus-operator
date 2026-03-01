"""Base model hierarchy for OmniFocus entities.

Inheritance chain:
    OmniFocusBaseModel  -- ConfigDict with camelCase aliases
    +-- OmniFocusEntity -- id + name (Tag, Folder inherit directly)
        +-- ActionableEntity -- shared dates, flags, status (Task, Project inherit)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import AwareDatetime, BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

if TYPE_CHECKING:
    from omnifocus_operator.models._common import RepetitionRule


class OmniFocusBaseModel(BaseModel):
    """Base model for all OmniFocus entities.

    Configures camelCase alias generation for JSON serialization
    and allows construction using either snake_case (Python) or
    camelCase (bridge JSON) field names.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
    )


class OmniFocusEntity(OmniFocusBaseModel):
    """Entity with identity fields shared by all OmniFocus object types."""

    id: str
    name: str


class ActionableEntity(OmniFocusEntity):
    """Shared fields for Task and Project (dates, flags, relationships).

    Fields here are present on BOTH tasks and projects in the bridge script output.
    Entity-specific fields (e.g. inInbox for Task, folder for Project) live on
    the concrete model classes.
    """

    # Lifecycle
    note: str
    completed: bool
    completed_by_children: bool

    # Flags
    flagged: bool
    effective_flagged: bool
    sequential: bool

    # Dates (all optional, timezone-aware)
    due_date: AwareDatetime | None = None
    defer_date: AwareDatetime | None = None
    effective_due_date: AwareDatetime | None = None
    effective_defer_date: AwareDatetime | None = None
    completion_date: AwareDatetime | None = None
    effective_completion_date: AwareDatetime | None = None
    planned_date: AwareDatetime | None = None
    effective_planned_date: AwareDatetime | None = None
    drop_date: AwareDatetime | None = None
    effective_drop_date: AwareDatetime | None = None

    # Metadata
    estimated_minutes: float | None = None
    has_children: bool
    should_use_floating_time_zone: bool

    # Relationships
    tags: list[str] = []  # Tag names, not IDs (bridge maps g.name)
    repetition_rule: RepetitionRule | None = None
