"""Base model with camelCase alias configuration.

OmniFocusBaseModel is the root of the model hierarchy. It lives alone
in this module (no internal imports) so that every other model module
can import it without circular dependencies.

Entity base classes (OmniFocusEntity, ActionableEntity) live in common.py.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


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
