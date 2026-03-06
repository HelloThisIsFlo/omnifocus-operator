"""Perspective model -- represents a single OmniFocus perspective.

Maps to the perspectives.map() output in the bridge script.
Perspective has 2 stored fields + 1 computed field.

Note: Perspective extends OmniFocusBaseModel (not OmniFocusEntity)
because builtin perspectives have id=null and lack lifecycle fields.
"""

from __future__ import annotations

from pydantic import computed_field

from omnifocus_operator.models._base import OmniFocusBaseModel


class Perspective(OmniFocusBaseModel):
    """A single OmniFocus perspective.

    Uses OmniFocusBaseModel (not OmniFocusEntity) because builtin
    perspectives have null id values and lack lifecycle fields.
    """

    id: str | None
    name: str

    @computed_field  # type: ignore[prop-decorator]
    @property
    def builtin(self) -> bool:
        """Built-in perspectives have no id (None)."""
        return self.id is None
