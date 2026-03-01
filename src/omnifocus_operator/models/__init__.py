"""OmniFocus data models -- Pydantic v2 models for all OmniFocus entities.

Public API for the models package. All model classes and enums are
re-exported here for convenient importing.
"""

from omnifocus_operator.models._base import (
    ActionableEntity,
    OmniFocusBaseModel,
    OmniFocusEntity,
)
from omnifocus_operator.models._common import RepetitionRule, ReviewInterval
from omnifocus_operator.models._enums import EntityStatus, TaskStatus

# Resolve forward references now that all modules are imported.
# ActionableEntity uses TYPE_CHECKING import for RepetitionRule to avoid
# circular import (_base -> _common -> _base). Rebuild resolves the
# string annotation to the actual class.
ActionableEntity.model_rebuild()

__all__ = [
    "ActionableEntity",
    "EntityStatus",
    "OmniFocusBaseModel",
    "OmniFocusEntity",
    "RepetitionRule",
    "ReviewInterval",
    "TaskStatus",
]
