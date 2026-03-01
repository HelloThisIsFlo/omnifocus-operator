"""Perspective model -- represents a single OmniFocus perspective.

Maps to the perspectives.map() output in the bridge script.
Perspective has 3 total fields.

Note: Perspective extends OmniFocusBaseModel (not OmniFocusEntity)
because builtin perspectives have id=null.
"""

from __future__ import annotations

from omnifocus_operator.models._base import OmniFocusBaseModel


class Perspective(OmniFocusBaseModel):
    """A single OmniFocus perspective with all bridge fields.

    Uses OmniFocusBaseModel (not OmniFocusEntity) because builtin
    perspectives have null id values.
    """

    id: str | None
    name: str
    builtin: bool
